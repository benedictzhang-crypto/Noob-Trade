from flask import Blueprint, current_app, jsonify, request
from sqlalchemy.engine.url import make_url

from models.market_data import DailyPrice, PatternWindow, Symbol
from services.market_data_service import MarketDataService
from services.persistence_service import PersistenceService

stock_blueprint = Blueprint("stock", __name__, url_prefix="/api")

PRIVATE_RESPONSE_KEYS = {
    "_currentWindow",
    "_skipCacheWrite",
    "featureVector",
    "scoreBreakdown",
    "quantScore",
    "quantMaxScore",
    "quantFullMaxScore",
    "quantSelectedPercent",
    "baseHistoricalProbability",
    "weightPenalty",
    "fitRatio",
}


def _trim_trade_response_payload(payload):
    if not isinstance(payload, dict):
        return payload

    chart_data = payload.get("chartData")
    if isinstance(chart_data, dict) and "history" in chart_data:
        trimmed_chart_data = dict(chart_data)
        trimmed_chart_data.pop("history", None)
        payload["chartData"] = trimmed_chart_data

    return payload


def _sanitize_response_payload(value):
    if isinstance(value, dict):
        return {
            key: _sanitize_response_payload(item)
            for key, item in value.items()
            if key not in PRIVATE_RESPONSE_KEYS
        }

    if isinstance(value, list):
        return [_sanitize_response_payload(item) for item in value]

    return value


def _to_float(value, default=0.0):
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _to_int(value, default=0):
    try:
        if value is None:
            return default
        return int(value)
    except Exception:
        return default


def _build_live_search_payload(market_data_service: MarketDataService, symbol: str, interval: str, lookback: int, indicators: list[str]):
    symbol_code = str(symbol or "").upper().strip()
    prices_payload = market_data_service.market_api.get_daily_prices(symbol_code, limit=120)
    prices = prices_payload.get("data", []) if isinstance(prices_payload, dict) else []
    if len(prices) < 2:
        raise ValueError("No price data returned from market API.")

    daily_candles = market_data_service._build_daily_candles(prices)
    latest = daily_candles[-1]
    previous = daily_candles[-2]

    high_values = [_to_float(item.get("high"), _to_float(item.get("close"))) for item in daily_candles]
    low_values = [_to_float(item.get("low"), _to_float(item.get("close"))) for item in daily_candles]
    current_price = round(_to_float(latest.get("close")), 2)

    return {
        "dataSource": "live",
        "request": {
            "symbol": symbol_code,
            "interval": interval,
            "lookback": lookback,
            "indicators": indicators,
        },
        "stock": {
            "symbol": symbol_code,
            "companyName": symbol_code,
            "sector": "Live API",
            "industry": "Live API",
            "currentPrice": current_price,
            "previousClose": round(_to_float(previous.get("close")), 2),
            "open": round(_to_float(latest.get("open")), 2),
            "volume": _to_int(latest.get("volume")),
            "week52High": round(max(high_values), 2),
            "week52Low": round(min(low_values), 2),
        },
        "patternAnalysis": {
            "lookbackWindow": lookback,
            "selectedIndicators": indicators,
            "probabilityOfIncrease": None,
            "probabilityOfDecrease": None,
            "avgReturn": None,
            "maxDrawdown": None,
            "matchedPatternsCount": 0,
            "matchedHistoricalPatterns": [],
            "quantConfidence": None,
            "signalClassification": "Search loads live market data only. Generate to score.",
            "futureFiveDayProbabilities": {"up": [], "down": []},
            "recommendedSellPrice": round(current_price * 1.012, 2),
            "recommendedSellDate": None,
            "stopLossPrice": round(current_price * 0.974, 2),
            "highFitHistoricalPaths": [],
        },
        "chartData": {
            "series": market_data_service._build_interval_series(daily_candles, prices),
        },
    }


@stock_blueprint.route("/health", methods=["GET"])
def health_check():
    """Small health endpoint for local frontend checks."""
    database_url = current_app.config.get("SQLALCHEMY_DATABASE_URI", "")
    app_bind = (current_app.config.get("SQLALCHEMY_BINDS") or {}).get("app", "")

    def _backend_label(raw_url):
        if not raw_url:
            return "unknown"
        try:
            drivername = make_url(raw_url).drivername
        except Exception:
            return "unknown"
        if drivername.startswith("postgresql"):
            return "postgres"
        if drivername.startswith("sqlite"):
            return "sqlite"
        return drivername

    return jsonify(
        {
            "status": "ok",
            "message": "Backend is running",
            "environment": str(current_app.config.get("ENVIRONMENT", "development")),
            "storageBackend": _backend_label(database_url),
            "authStorageBackend": _backend_label(app_bind or database_url),
        }
    )


@stock_blueprint.route("/stock/<symbol>", methods=["GET"])
def get_stock(symbol):
    """Return stock details and persist the generated analysis run."""
    is_production = str(current_app.config.get("ENVIRONMENT", "")).lower() == "production"
    lookback = request.args.get(
        "lookback",
        default=current_app.config["DEFAULT_LOOKBACK"],
        type=int
    )
    interval = request.args.get(
        "interval",
        default=current_app.config["DEFAULT_INTERVAL"],
        type=str
    )
    raw_indicators = request.args.get("indicators", default="")
    prefetch_only = request.args.get("prefetch", default=0, type=int) == 1
    persist_analysis = request.args.get("persist", default=0, type=int) == 1
    compact_response = request.args.get("compact", default=0, type=int) == 1
    analysis_mode = request.args.get("analysis", default="full", type=str).strip().lower()
    if analysis_mode == "summary":
        analysis_mode = "search"
    if analysis_mode not in {"full", "search"}:
        analysis_mode = "full"
    indicators = [item for item in (raw_indicators.split(",") if raw_indicators else current_app.config["DEFAULT_INDICATORS"]) if item]

    if is_production:
        # In production, keep explicit compact/prefetch requests lightweight,
        # but allow normal interactive searches to return chart data again.
        compact_response = compact_response or prefetch_only
        prefetch_only = False
        persist_analysis = False
        if analysis_mode == "search":
            market_data_service = MarketDataService(current_app.config)
            try:
                return jsonify(_sanitize_response_payload(_build_live_search_payload(market_data_service, symbol, interval, lookback, indicators)))
            except Exception as error:
                current_app.logger.exception("Production live search failed for %s", symbol)
                return jsonify(
                    {
                        "status": "error",
                        "message": str(error),
                        "symbol": symbol.upper(),
                        "interval": interval,
                        "lookback": lookback,
                    }
                ), 500

    market_data_service = MarketDataService(current_app.config)
    persistence_service = None

    try:
        response_data = market_data_service.get_stock_pattern_analysis(
            symbol=symbol,
            interval=interval,
            lookback_window=lookback,
            raw_indicators=raw_indicators,
            default_indicators=current_app.config["DEFAULT_INDICATORS"],
            compact_response=compact_response,
            analysis_mode=analysis_mode,
        )
        response_data = _trim_trade_response_payload(response_data)

        if not is_production and response_data.get("dataSource") == "live" and response_data.get("_currentWindow"):
            persistence_service = persistence_service or PersistenceService()
            try:
                response_data = persistence_service.apply_cached_match_preview(response_data)
            except Exception as error:
                current_app.logger.warning("Could not apply indicator-aware cached preview: %s", error)

        should_persist = (current_app.config.get("PERSIST_ANALYSIS_RUNS", False) or persist_analysis) and not is_production

        if not prefetch_only and should_persist:
            persistence_service = persistence_service or PersistenceService()
            try:
                response_data = persistence_service.save_analysis_run(response_data)
            except Exception as error:
                # Keep API responses available even if the database is not ready yet.
                current_app.logger.warning("Could not persist analysis run: %s", error)

        return jsonify(_sanitize_response_payload(response_data))
    except Exception as error:
        current_app.logger.exception("Stock analysis failed for %s", symbol)
        return jsonify(
            {
                "status": "error",
                "message": str(error),
                "symbol": symbol.upper(),
                "interval": interval,
                "lookback": lookback,
            }
        ), 500


@stock_blueprint.route("/market-news", methods=["GET"])
def get_market_news():
    symbol = request.args.get("symbol", default="", type=str).strip()
    limit = request.args.get("limit", default=5, type=int)

    market_data_service = MarketDataService(current_app.config)
    news_items = market_data_service.get_market_news(symbol=symbol, limit=max(1, min(limit, 10)))

    return jsonify(
        {
            "status": "ok",
            "symbol": symbol.upper() if symbol else None,
            "items": news_items,
        }
    )


@stock_blueprint.route("/pro-signal/<symbol>", methods=["POST"])
def get_pro_signal(symbol):
    payload = request.get_json(silent=True) or {}
    interval = str(payload.get("interval") or "daily")
    lookback = int(payload.get("lookback") or current_app.config["DEFAULT_LOOKBACK"])
    current_price = payload.get("currentPrice")
    raw_indicators = payload.get("indicators") or current_app.config["DEFAULT_INDICATORS"]

    market_data_service = MarketDataService(current_app.config)

    try:
        response_data = market_data_service.get_cached_pro_signal(
            symbol=symbol,
            interval=interval,
            lookback_window=lookback,
            current_price=current_price,
            indicators=raw_indicators if isinstance(raw_indicators, list) else raw_indicators.split(","),
        )
        return jsonify(response_data)
    except Exception as error:
        current_app.logger.exception("Pro signal failed for %s", symbol)
        return jsonify(
            {
                "status": "error",
                "message": str(error),
                "symbol": symbol.upper(),
                "interval": interval,
                "lookback": lookback,
            }
        ), 500
