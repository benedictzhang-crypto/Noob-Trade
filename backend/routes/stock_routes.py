from flask import Blueprint, current_app, jsonify, request

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


@stock_blueprint.route("/health", methods=["GET"])
def health_check():
    """Small health endpoint for local frontend checks."""
    return jsonify(
        {
            "status": "ok",
            "message": "Backend is running"
        }
    )


@stock_blueprint.route("/stock/<symbol>", methods=["GET"])
def get_stock(symbol):
    """Return stock details and persist the generated analysis run."""
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

    market_data_service = MarketDataService(current_app.config)
    persistence_service = PersistenceService()

    try:
        response_data = market_data_service.get_stock_pattern_analysis(
            symbol=symbol,
            interval=interval,
            lookback_window=lookback,
            raw_indicators=raw_indicators,
            default_indicators=current_app.config["DEFAULT_INDICATORS"],
            compact_response=compact_response,
        )

        if response_data.get("dataSource") == "live" and response_data.get("_currentWindow"):
            try:
                response_data = persistence_service.apply_cached_match_preview(response_data)
            except Exception as error:
                current_app.logger.warning("Could not apply indicator-aware cached preview: %s", error)

        should_persist = current_app.config.get("PERSIST_ANALYSIS_RUNS", False) or persist_analysis

        if not prefetch_only and should_persist:
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
