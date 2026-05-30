import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, pstdev


BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


INTERVAL_BARS_PER_DAY = {
    "1min": 1440,
    "5min": 288,
    "15min": 96,
    "30min": 48,
    "1hour": 24,
}
BATCH_SIZE = 2000


def _parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Fetch crypto market-cap leaders and warm the NoobTrade intraday cache "
            "from OKX spot candles. The default raw storage interval is 15 minutes; "
            "higher intervals can be aggregated from these rows later."
        )
    )
    parser.add_argument("--limit", type=int, default=50, help="Number of market-cap leaders to sync.")
    parser.add_argument("--years", type=int, default=10, help="Lookback target. Assets with shorter OKX history start at their first candle.")
    parser.add_argument("--interval", default="15min", choices=("1min", "5min", "15min", "30min", "1hour"))
    parser.add_argument("--symbols", help="Comma-separated crypto symbols. Overrides the market-cap top list.")
    parser.add_argument("--window-sizes", default="20,30,60")
    parser.add_argument("--max-bars", type=int, help="Testing throttle for the number of candles per symbol.")
    parser.add_argument("--skip-windows", action="store_true", help="Only write intraday prices and indicators.")
    parser.add_argument("--database-url", help="Override DATABASE_URL before importing Flask app, useful for Render Postgres.")
    parser.add_argument("--app-database-url", help="Override APP_DATABASE_URL before importing Flask app.")
    return parser.parse_args()


def _parse_csv(raw_value, coerce=str):
    values = []
    for item in str(raw_value or "").split(","):
        cleaned = item.strip()
        if not cleaned:
            continue
        values.append(coerce(cleaned))
    return values


def _symbol_assets(raw_symbols):
    symbols = _parse_csv(raw_symbols, lambda value: value.upper())
    return [
        {
            "symbol": symbol,
            "name": f"{symbol} Crypto",
            "category": "Manual OKX sync",
        }
        for symbol in symbols
    ]


def _okx_sync_assets(market_data_service, limit):
    requested_limit = max(1, int(limit or 50))
    candidate_limit = min(250, max(requested_limit * 4, requested_limit))
    candidates = market_data_service.get_top_crypto_assets(limit=candidate_limit)
    if not candidates:
        return []

    try:
        market_data_service.market_api.get_okx_spot_inst_ids()
    except Exception as error:
        print(
            {
                "status": "warning",
                "message": "OKX instrument list unavailable; trying market-cap candidates directly.",
                "detail": str(error)[:180],
            },
            flush=True,
        )
        return candidates[:requested_limit]

    assets = []
    skipped = []
    for asset in candidates:
        symbol = str(asset.get("symbol") or "").upper().strip()
        if not symbol:
            continue
        if market_data_service.market_api.has_okx_spot_pair(symbol):
            assets.append(asset)
            if len(assets) >= requested_limit:
                break
        else:
            skipped.append(symbol)

    if skipped:
        print(
            {
                "status": "filtered",
                "message": "Skipped market-cap assets without an OKX USDT spot pair.",
                "symbols": skipped[:40],
                "skippedCount": len(skipped),
            },
            flush=True,
        )

    return assets


def _parse_bar_time(value):
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _to_float(value, default=0.0):
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value, default=0):
    try:
        if value is None:
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _insert_helper(db):
    dialect_name = db.engine.dialect.name
    if dialect_name == "postgresql":
        from sqlalchemy.dialects.postgresql import insert

        return insert
    if dialect_name == "sqlite":
        from sqlalchemy.dialects.sqlite import insert

        return insert
    raise RuntimeError(f"Unsupported database dialect for intraday upsert: {dialect_name}")


def _execute_upsert(db, model, rows, conflict_columns, update_columns):
    if not rows:
        return

    insert = _insert_helper(db)

    for start in range(0, len(rows), BATCH_SIZE):
        batch = rows[start:start + BATCH_SIZE]
        statement = insert(model).values(batch)
        excluded = statement.excluded
        statement = statement.on_conflict_do_update(
            index_elements=conflict_columns,
            set_={column: getattr(excluded, column) for column in update_columns},
        )
        db.session.execute(statement)
        db.session.commit()


def _normalize_candles(raw_candles):
    candles_by_time = {}
    for candle in raw_candles:
        bar_time = _parse_bar_time(candle.get("date"))
        candles_by_time[bar_time] = {
            "trade_date": bar_time,
            "bar_time": bar_time,
            "open": _to_float(candle.get("open"), _to_float(candle.get("close"))),
            "high": _to_float(candle.get("high"), _to_float(candle.get("close"))),
            "low": _to_float(candle.get("low"), _to_float(candle.get("close"))),
            "close": _to_float(candle.get("close")),
            "volume": _to_float(candle.get("volume", 0)),
        }

    return [candles_by_time[key] for key in sorted(candles_by_time)]


def _sma(values, period):
    if len(values) < period:
        return None
    return round(mean(values[-period:]), 6)


def _ema(values, period, previous):
    if len(values) < period:
        return None
    if previous is None:
        return round(mean(values[-period:]), 6)
    multiplier = 2 / (period + 1)
    return round(((values[-1] - previous) * multiplier) + previous, 6)


def _rsi(closes, period=14):
    if len(closes) <= period:
        return None
    gains = []
    losses = []
    for index in range(len(closes) - period, len(closes)):
        change = closes[index] - closes[index - 1]
        gains.append(max(change, 0))
        losses.append(abs(min(change, 0)))
    average_gain = mean(gains)
    average_loss = mean(losses)
    if average_loss == 0:
        return 100.0
    rs = average_gain / average_loss
    return round(100 - (100 / (1 + rs)), 4)


def _boll(closes, period=20):
    if len(closes) < period:
        return {"mid": None, "upper": None, "lower": None}
    window = closes[-period:]
    mid = mean(window)
    deviation = pstdev(window)
    return {
        "mid": round(mid, 6),
        "upper": round(mid + (2 * deviation), 6),
        "lower": round(mid - (2 * deviation), 6),
    }


def _kdj(highs, lows, closes, period=9):
    if len(closes) < period:
        return {"k": None, "d": None, "j": None}
    recent_high = max(highs[-period:])
    recent_low = min(lows[-period:])
    current_close = closes[-1]
    if recent_high == recent_low:
        rsv = 50.0
    else:
        rsv = ((current_close - recent_low) / (recent_high - recent_low)) * 100
    k_value = round((2 / 3) * 50 + (1 / 3) * rsv, 4)
    d_value = round((2 / 3) * 50 + (1 / 3) * k_value, 4)
    return {"k": k_value, "d": d_value, "j": round((3 * k_value) - (2 * d_value), 4)}


def _indicator_rows(symbol_id, interval, candles):
    closes = []
    highs = []
    lows = []
    volumes = []
    ema_state = {5: None, 10: None, 12: None, 20: None, 26: None, 60: None}
    macd_values = []
    macd_signal = None
    obv = 0.0
    oi = 0.0
    previous_close = None
    rows = []

    for candle in candles:
        close = candle["close"]
        volume = candle["volume"]
        closes.append(close)
        highs.append(candle["high"])
        lows.append(candle["low"])
        volumes.append(volume)

        for period in ema_state:
            ema_state[period] = _ema(closes, period, ema_state[period])

        macd_line = None
        if ema_state[12] is not None and ema_state[26] is not None:
            macd_line = round(ema_state[12] - ema_state[26], 6)
            macd_values.append(macd_line)
            macd_signal = _ema(macd_values, 9, macd_signal)

        if previous_close is not None:
            if close > previous_close:
                obv += volume
            elif close < previous_close:
                obv -= volume
        oi += volume * (0.35 if previous_close is None or close >= previous_close else -0.35)
        previous_close = close

        boll = _boll(closes)
        kdj = _kdj(highs, lows, closes)

        rows.append(
            {
                "symbol_id": symbol_id,
                "interval": interval,
                "bar_time": candle["bar_time"],
                "ma_5": _sma(closes, 5),
                "ma_10": _sma(closes, 10),
                "ma_20": _sma(closes, 20),
                "ma_60": _sma(closes, 60),
                "ema_5": ema_state[5],
                "ema_10": ema_state[10],
                "ema_12": ema_state[12],
                "ema_20": ema_state[20],
                "ema_26": ema_state[26],
                "ema_60": ema_state[60],
                "macd": macd_line,
                "macd_signal": macd_signal,
                "macd_hist": round(macd_line - macd_signal, 6) if macd_line is not None and macd_signal is not None else None,
                "rsi_14": _rsi(closes),
                "boll_mid": boll["mid"],
                "boll_upper": boll["upper"],
                "boll_lower": boll["lower"],
                "kdj_k": kdj["k"],
                "kdj_d": kdj["d"],
                "kdj_j": kdj["j"],
                "vol_ma_5": _sma(volumes, 5),
                "vol_ma_20": _sma(volumes, 20),
                "oi": round(oi, 6),
                "pbv": round(obv, 6),
            }
        )

    return rows


def _window_rows(symbol_id, interval, candles, window_sizes, source, persistence_service):
    rows = []
    for window_size in window_sizes:
        if len(candles) < window_size:
            continue
        for end_index in range(window_size, len(candles) + 1):
            window = candles[end_index - window_size:end_index]
            summary = persistence_service._build_window_summary(window)
            rows.append(
                {
                    "symbol_id": symbol_id,
                    "interval": interval,
                    "window_size": window_size,
                    "start_time": window[0]["bar_time"],
                    "end_time": window[-1]["bar_time"],
                    "return_pct": summary["return_pct"],
                    "avg_return": summary["avg_return"],
                    "max_drawdown": summary["max_drawdown"],
                    "volatility": summary["volatility"],
                    "probability_score": summary["probability_score"],
                    "ma_slope": summary["ma_slope"],
                    "ema_slope": summary["ema_slope"],
                    "macd_trend": summary["macd_trend"],
                    "rsi_avg": summary["rsi_avg"],
                    "rsi_min": summary["rsi_min"],
                    "rsi_max": summary["rsi_max"],
                    "volume_change_ratio": summary["volume_change_ratio"],
                    "feature_vector": summary["feature_vector"],
                    "source": source,
                }
            )
    return rows


def main():
    args = _parse_args()

    if args.database_url:
        os.environ["DATABASE_URL"] = args.database_url
    if args.app_database_url:
        os.environ["APP_DATABASE_URL"] = args.app_database_url

    os.environ.setdefault("MARKET_DATA_PROVIDER", "auto")
    os.environ.setdefault("ENABLE_DEMO_FALLBACK", "true")
    os.environ.setdefault("ENABLE_DEMO_FALLBACK_ALL_SYMBOLS", "true")
    os.environ.setdefault("USE_MOCK_FALLBACK", "true")

    from app import app
    from extensions import db
    from models.market_data import IntradayIndicator, IntradayPatternWindow, IntradayPrice
    from services.crypto_market_data_service import CryptoMarketDataService
    from services.persistence_service import PersistenceService

    window_sizes = tuple(_parse_csv(args.window_sizes, int))
    bars_per_day = INTERVAL_BARS_PER_DAY[args.interval]
    requested_bars = args.max_bars or max((args.years * 366 * bars_per_day), max(window_sizes or (60,)) + 20)

    with app.app_context():
        db.create_all()
        market_data_service = CryptoMarketDataService(app.config)
        persistence_service = PersistenceService()
        assets = _symbol_assets(args.symbols) if args.symbols else _okx_sync_assets(market_data_service, args.limit)
        assets = assets[: max(1, int(args.limit or 50))]
        results = []

        for index, asset in enumerate(assets, start=1):
            symbol = str(asset.get("symbol") or "").upper().strip()
            if not symbol:
                continue

            source = "okx_spot"
            try:
                payload = market_data_service.market_api.get_intraday_prices(
                    symbol,
                    args.interval,
                    limit=requested_bars,
                )
                raw_candles = payload.get("data", []) if isinstance(payload, dict) else []
                source_symbol = (payload.get("meta") or {}).get("symbol") if isinstance(payload, dict) else None
                if source_symbol:
                    source = f"okx:{source_symbol}"
                candles = _normalize_candles(raw_candles)
                if not candles:
                    raise RuntimeError(f"No OKX {args.interval} candles returned.")

                stock_data = {
                    "symbol": symbol,
                    "companyName": asset.get("name") or f"{symbol} Crypto",
                    "sector": "Crypto",
                    "industry": asset.get("category") or "OKX Spot",
                    "exchange": "OKX",
                    "marketCap": asset.get("market_cap"),
                }
                symbol_record = persistence_service._upsert_symbol(stock_data)
                db.session.commit()

                price_rows = [
                    {
                        "symbol_id": symbol_record.id,
                        "interval": args.interval,
                        "bar_time": candle["bar_time"],
                        "open": candle["open"],
                        "high": candle["high"],
                        "low": candle["low"],
                        "close": candle["close"],
                        "volume": _to_int(candle["volume"]),
                        "source": source,
                    }
                    for candle in candles
                ]
                _execute_upsert(
                    db,
                    IntradayPrice,
                    price_rows,
                    ["symbol_id", "interval", "bar_time"],
                    ["open", "high", "low", "close", "volume", "source"],
                )

                indicators = _indicator_rows(symbol_record.id, args.interval, candles)
                _execute_upsert(
                    db,
                    IntradayIndicator,
                    indicators,
                    ["symbol_id", "interval", "bar_time"],
                    [
                        "ma_5",
                        "ma_10",
                        "ma_20",
                        "ma_60",
                        "ema_5",
                        "ema_10",
                        "ema_12",
                        "ema_20",
                        "ema_26",
                        "ema_60",
                        "macd",
                        "macd_signal",
                        "macd_hist",
                        "rsi_14",
                        "boll_mid",
                        "boll_upper",
                        "boll_lower",
                        "kdj_k",
                        "kdj_d",
                        "kdj_j",
                        "vol_ma_5",
                        "vol_ma_20",
                        "oi",
                        "pbv",
                    ],
                )

                windows_written = 0
                if not args.skip_windows:
                    windows = _window_rows(
                        symbol_record.id,
                        args.interval,
                        candles,
                        window_sizes,
                        source,
                        persistence_service,
                    )
                    windows_written = len(windows)
                    _execute_upsert(
                        db,
                        IntradayPatternWindow,
                        windows,
                        ["symbol_id", "interval", "window_size", "end_time"],
                        [
                            "start_time",
                            "return_pct",
                            "avg_return",
                            "max_drawdown",
                            "volatility",
                            "probability_score",
                            "ma_slope",
                            "ema_slope",
                            "macd_trend",
                            "rsi_avg",
                            "rsi_min",
                            "rsi_max",
                            "volume_change_ratio",
                            "feature_vector",
                            "source",
                        ],
                    )

                result = {
                    "status": "synced",
                    "index": index,
                    "total": len(assets),
                    "symbol": symbol,
                    "interval": args.interval,
                    "source": source,
                    "bars": len(candles),
                    "firstBar": candles[0]["bar_time"].isoformat(),
                    "lastBar": candles[-1]["bar_time"].isoformat(),
                    "indicatorRows": len(indicators),
                    "patternWindows": windows_written,
                    "requestedBars": requested_bars,
                }
                results.append(result)
                print(result, flush=True)
            except Exception as error:
                db.session.rollback()
                result = {
                    "status": "failed",
                    "index": index,
                    "total": len(assets),
                    "symbol": symbol,
                    "interval": args.interval,
                    "source": "okx_spot",
                    "message": str(error)[:220],
                }
                results.append(result)
                print(result, flush=True)
            finally:
                db.session.remove()

        synced_count = len([item for item in results if item.get("status") == "synced"])
        failed_count = len([item for item in results if item.get("status") == "failed"])
        summary = {
            "database": app.config["SQLALCHEMY_DATABASE_URI"],
            "requestedAssets": len(assets),
            "syncedAssets": synced_count,
            "failedAssets": failed_count,
            "interval": args.interval,
            "yearsTarget": args.years,
            "requestedBarsPerAsset": requested_bars,
            "windowSizes": window_sizes,
            "sourcePolicy": "OKX spot candles only; starts at each asset's first available OKX candle.",
        }
        print(summary, flush=True)

        if failed_count and synced_count == 0:
            raise RuntimeError("No crypto assets were synced from OKX.")


if __name__ == "__main__":
    main()
