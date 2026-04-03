import json
import os
import sqlite3
import sys
from pathlib import Path

from sqlalchemy import text


BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


SYNC_TABLES = ("daily_prices", "daily_indicators", "pattern_windows")


def _normalize_database_url(raw_url):
    if not raw_url:
        raise RuntimeError("DATABASE_URL is required and must point to PostgreSQL.")

    normalized = raw_url.strip()
    if normalized.startswith("postgres://"):
        normalized = normalized.replace("postgres://", "postgresql+psycopg://", 1)
    elif normalized.startswith("postgresql://"):
        normalized = normalized.replace("postgresql://", "postgresql+psycopg://", 1)

    if not normalized.startswith("postgresql+psycopg://"):
        raise RuntimeError("DATABASE_URL must use a PostgreSQL connection string.")

    return normalized


def _sqlite_path():
    configured_path = os.getenv("SQLITE_SOURCE_PATH", str(BACKEND_DIR / "noobtrade_local.db"))
    return Path(configured_path).expanduser().resolve()


def _fetch_source_symbols(connection):
    cursor = connection.execute(
        """
        SELECT id, symbol, company_name, sector, industry, exchange, market_cap, is_active
        FROM symbols
        ORDER BY symbol
        """
    )
    columns = [column[0] for column in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _fetch_table_rows(connection, table_name, symbol_ids):
    if not symbol_ids:
        return []

    placeholders = ",".join("?" for _ in symbol_ids)
    cursor = connection.execute(
        f"SELECT * FROM {table_name} WHERE symbol_id IN ({placeholders})",
        tuple(symbol_ids),
    )
    columns = [column[0] for column in cursor.description]
    rows = [dict(zip(columns, row)) for row in cursor.fetchall()]

    if table_name == "pattern_windows":
        for row in rows:
            feature_vector = row.get("feature_vector")
            if isinstance(feature_vector, str) and feature_vector.strip():
                try:
                    row["feature_vector"] = json.loads(feature_vector)
                except json.JSONDecodeError:
                    row["feature_vector"] = None

    return rows


def _upsert_symbols(db, symbol_rows):
    source_to_target = {}

    for row in symbol_rows:
        params = {
            "symbol": row["symbol"],
            "company_name": row.get("company_name"),
            "sector": row.get("sector"),
            "industry": row.get("industry"),
            "exchange": row.get("exchange"),
            "market_cap": row.get("market_cap"),
            "is_active": bool(row.get("is_active", 1)),
        }
        result = db.session.execute(
            text(
                """
                INSERT INTO symbols (symbol, company_name, sector, industry, exchange, market_cap, is_active)
                VALUES (:symbol, :company_name, :sector, :industry, :exchange, :market_cap, :is_active)
                ON CONFLICT (symbol) DO UPDATE
                SET company_name = EXCLUDED.company_name,
                    sector = EXCLUDED.sector,
                    industry = EXCLUDED.industry,
                    exchange = EXCLUDED.exchange,
                    market_cap = EXCLUDED.market_cap,
                    is_active = EXCLUDED.is_active,
                    updated_at = NOW()
                RETURNING id
                """
            ),
            params,
        )
        source_to_target[row["id"]] = result.scalar_one()

    db.session.commit()
    return source_to_target


def _sync_daily_prices(db, rows, symbol_map):
    for row in rows:
        db.session.execute(
            text(
                """
                INSERT INTO daily_prices (
                    symbol_id, trade_date, open, high, low, close, adjusted_close, volume, source
                ) VALUES (
                    :symbol_id, :trade_date, :open, :high, :low, :close, :adjusted_close, :volume, :source
                )
                ON CONFLICT (symbol_id, trade_date) DO UPDATE
                SET open = EXCLUDED.open,
                    high = EXCLUDED.high,
                    low = EXCLUDED.low,
                    close = EXCLUDED.close,
                    adjusted_close = EXCLUDED.adjusted_close,
                    volume = EXCLUDED.volume,
                    source = EXCLUDED.source
                """
            ),
            {
                "symbol_id": symbol_map[row["symbol_id"]],
                "trade_date": row["trade_date"],
                "open": row["open"],
                "high": row["high"],
                "low": row["low"],
                "close": row["close"],
                "adjusted_close": row.get("adjusted_close"),
                "volume": row.get("volume"),
                "source": row.get("source") or "duke_api",
            },
        )


def _sync_daily_indicators(db, rows, symbol_map):
    sql = text(
        """
        INSERT INTO daily_indicators (
            symbol_id, trade_date, ma_5, ma_10, ma_20, ma_60, ema_5, ema_10, ema_12, ema_20, ema_26, ema_60,
            macd, macd_signal, macd_hist, rsi_14, boll_mid, boll_upper, boll_lower,
            kdj_k, kdj_d, kdj_j, vol_ma_5, vol_ma_20, oi, pbv
        ) VALUES (
            :symbol_id, :trade_date, :ma_5, :ma_10, :ma_20, :ma_60, :ema_5, :ema_10, :ema_12, :ema_20, :ema_26, :ema_60,
            :macd, :macd_signal, :macd_hist, :rsi_14, :boll_mid, :boll_upper, :boll_lower,
            :kdj_k, :kdj_d, :kdj_j, :vol_ma_5, :vol_ma_20, :oi, :pbv
        )
        ON CONFLICT (symbol_id, trade_date) DO UPDATE
        SET ma_5 = EXCLUDED.ma_5,
            ma_10 = EXCLUDED.ma_10,
            ma_20 = EXCLUDED.ma_20,
            ma_60 = EXCLUDED.ma_60,
            ema_5 = EXCLUDED.ema_5,
            ema_10 = EXCLUDED.ema_10,
            ema_12 = EXCLUDED.ema_12,
            ema_20 = EXCLUDED.ema_20,
            ema_26 = EXCLUDED.ema_26,
            ema_60 = EXCLUDED.ema_60,
            macd = EXCLUDED.macd,
            macd_signal = EXCLUDED.macd_signal,
            macd_hist = EXCLUDED.macd_hist,
            rsi_14 = EXCLUDED.rsi_14,
            boll_mid = EXCLUDED.boll_mid,
            boll_upper = EXCLUDED.boll_upper,
            boll_lower = EXCLUDED.boll_lower,
            kdj_k = EXCLUDED.kdj_k,
            kdj_d = EXCLUDED.kdj_d,
            kdj_j = EXCLUDED.kdj_j,
            vol_ma_5 = EXCLUDED.vol_ma_5,
            vol_ma_20 = EXCLUDED.vol_ma_20,
            oi = EXCLUDED.oi,
            pbv = EXCLUDED.pbv
        """
    )

    for row in rows:
        params = dict(row)
        params["symbol_id"] = symbol_map[row["symbol_id"]]
        params.pop("id", None)
        params.pop("created_at", None)
        db.session.execute(sql, params)


def _sync_pattern_windows(db, rows, symbol_map):
    sql = text(
        """
        INSERT INTO pattern_windows (
            symbol_id, timeframe, window_size, start_date, end_date,
            return_pct, avg_return, max_drawdown, volatility, probability_score,
            ma_slope, ema_slope, macd_trend, rsi_avg, rsi_min, rsi_max,
            volume_change_ratio, feature_vector
        ) VALUES (
            :symbol_id, :timeframe, :window_size, :start_date, :end_date,
            :return_pct, :avg_return, :max_drawdown, :volatility, :probability_score,
            :ma_slope, :ema_slope, :macd_trend, :rsi_avg, :rsi_min, :rsi_max,
            :volume_change_ratio, CAST(:feature_vector AS JSONB)
        )
        ON CONFLICT (symbol_id, timeframe, window_size, end_date) DO UPDATE
        SET start_date = EXCLUDED.start_date,
            return_pct = EXCLUDED.return_pct,
            avg_return = EXCLUDED.avg_return,
            max_drawdown = EXCLUDED.max_drawdown,
            volatility = EXCLUDED.volatility,
            probability_score = EXCLUDED.probability_score,
            ma_slope = EXCLUDED.ma_slope,
            ema_slope = EXCLUDED.ema_slope,
            macd_trend = EXCLUDED.macd_trend,
            rsi_avg = EXCLUDED.rsi_avg,
            rsi_min = EXCLUDED.rsi_min,
            rsi_max = EXCLUDED.rsi_max,
            volume_change_ratio = EXCLUDED.volume_change_ratio,
            feature_vector = EXCLUDED.feature_vector
        """
    )

    for row in rows:
        params = dict(row)
        params["symbol_id"] = symbol_map[row["symbol_id"]]
        params["feature_vector"] = json.dumps(row.get("feature_vector") or {})
        params.pop("id", None)
        params.pop("created_at", None)
        db.session.execute(sql, params)


def main():
    sqlite_path = _sqlite_path()
    if not sqlite_path.exists():
        raise RuntimeError(f"SQLite source database not found: {sqlite_path}")

    os.environ["DATABASE_URL"] = _normalize_database_url(os.getenv("DATABASE_URL", ""))
    os.environ.setdefault("FLASK_DEBUG", "false")
    os.environ.setdefault("MARKET_DATA_TOKEN", "")
    os.environ.setdefault("USE_MOCK_FALLBACK", "true")

    from app import app
    from extensions import db

    with sqlite3.connect(sqlite_path) as sqlite_connection:
        sqlite_connection.row_factory = sqlite3.Row
        symbol_rows = _fetch_source_symbols(sqlite_connection)
        source_symbol_ids = [row["id"] for row in symbol_rows]
        table_rows = {table_name: _fetch_table_rows(sqlite_connection, table_name, source_symbol_ids) for table_name in SYNC_TABLES}

    with app.app_context():
        db.create_all()
        symbol_map = _upsert_symbols(db, symbol_rows)
        _sync_daily_prices(db, table_rows["daily_prices"], symbol_map)
        _sync_daily_indicators(db, table_rows["daily_indicators"], symbol_map)
        _sync_pattern_windows(db, table_rows["pattern_windows"], symbol_map)
        db.session.commit()

        summary = {
            "database_url": app.config["SQLALCHEMY_DATABASE_URI"],
            "symbols": len(symbol_rows),
            "daily_prices": len(table_rows["daily_prices"]),
            "daily_indicators": len(table_rows["daily_indicators"]),
            "pattern_windows": len(table_rows["pattern_windows"]),
            "synced_symbols": [row["symbol"] for row in symbol_rows],
        }

    print(summary)


if __name__ == "__main__":
    main()
