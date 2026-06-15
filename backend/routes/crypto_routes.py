from flask import Blueprint, current_app, jsonify, request

from services.crypto_market_data_service import CryptoMarketDataService
from services.mock_market_data_service import parse_indicators


crypto_blueprint = Blueprint("crypto", __name__, url_prefix="/api")

PRIVATE_RESPONSE_KEYS = {
    "_currentWindow",
    "_skipCacheWrite",
    "featureVector",
    "scoreBreakdown",
    "quantScore",
    "quantMaxScore",
    "quantFullMaxScore",
    "quantSelectedPercent",
    "quantConfidence",
    "baseHistoricalProbability",
    "weightPenalty",
    "fitRatio",
    "lookbackWindow",
    "windowSize",
    "regime",
    "diversityKey",
    "strategyProfile",
    "sourceVariantId",
}


def _crypto_market_data_service():
    return CryptoMarketDataService(current_app.config)


def _persistence_service():
    from services.persistence_service import PersistenceService

    return PersistenceService()


def _normalize_crypto_symbol(symbol):
    return CryptoMarketDataService(current_app.config)._normalize_symbol_code(symbol)


def _sanitize_response_payload(value):
    if isinstance(value, dict):
        sanitized = {}
        for key, item in value.items():
            if key in PRIVATE_RESPONSE_KEYS:
                continue
            if key == "dataSource":
                sanitized[key] = _public_data_source(item)
                continue
            if key == "marketDataProvider":
                sanitized[key] = "Market data"
                continue
            if key == "exchange" and str(item).lower() in {"okx"}:
                sanitized[key] = "Digital Asset"
                continue
            if key == "industry" and str(item).lower() in {"pattern store", "no-key market data"}:
                sanitized[key] = "Digital Asset"
                continue
            sanitized[key] = _sanitize_response_payload(item)
        return sanitized

    if isinstance(value, list):
        return [_sanitize_response_payload(item) for item in value]

    return value


def _public_data_source(value):
    normalized = str(value or "").strip().lower()
    if normalized in {"mock", "demo", "crypto-mock", "crypto-demo"}:
        return "demo"
    return "live"


def _trim_trade_response_payload(payload):
    if not isinstance(payload, dict):
        return payload

    chart_data = payload.get("chartData")
    if isinstance(chart_data, dict) and "history" in chart_data:
        trimmed_chart_data = dict(chart_data)
        trimmed_chart_data.pop("history", None)
        payload["chartData"] = trimmed_chart_data

    return payload


def _public_crypto_error_message(error, symbol):
    raw_message = str(error or "")
    symbol_code = str(symbol or "This crypto").upper()
    technical_tokens = (
        "HTTPSConnectionPool",
        "ConnectTimeoutError",
        "ReadTimeout",
        "Max retries exceeded",
        "www.okx.com",
        "api.coingecko.com",
        "requests.exceptions",
    )
    if any(token.lower() in raw_message.lower() for token in technical_tokens):
        return f"{symbol_code} crypto market data connection timed out. Please try again in a moment."
    if raw_message:
        return raw_message[:240]
    return f"{symbol_code} crypto data is not accessible right now."


def _empty_crypto_search_analysis(indicators, current_price):
    return {
        "lookbackWindow": current_app.config["DEFAULT_LOOKBACK"],
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
        "recommendedSellPrice": round(current_price * 1.012, 8) if current_price else None,
        "recommendedSellDate": None,
        "stopLossPrice": round(current_price * 0.974, 8) if current_price else None,
        "highFitHistoricalPaths": [],
    }


def _build_crypto_live_search_payload(market_data_service, symbol, interval, indicators):
    response_data = market_data_service.get_stock_chart_data(
        symbol=symbol,
        chart_interval=interval,
    )
    stock = response_data.setdefault("stock", {})
    current_price = _to_float(stock.get("currentPrice"))
    stock["sector"] = "Crypto"
    stock["industry"] = "Digital Asset"
    request_payload = response_data.setdefault("request", {})
    request_payload["interval"] = interval
    request_payload["indicators"] = indicators
    response_data["patternAnalysis"] = _empty_crypto_search_analysis(indicators, current_price)
    return response_data


def _to_float(value, default=0.0):
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


@crypto_blueprint.route("/crypto/<symbol>", methods=["GET"])
def get_crypto(symbol):
    symbol = _normalize_crypto_symbol(symbol)
    is_production = str(current_app.config.get("ENVIRONMENT", "")).lower() == "production"
    lookback = request.args.get(
        "lookback",
        default=current_app.config["DEFAULT_LOOKBACK"],
        type=int,
    )
    interval = request.args.get(
        "interval",
        default=current_app.config["DEFAULT_INTERVAL"],
        type=str,
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

    if is_production:
        compact_response = compact_response or prefetch_only
        prefetch_only = False
        persist_analysis = False

    market_data_service = _crypto_market_data_service()
    persistence_service = None

    if analysis_mode == "search":
        indicators = parse_indicators(raw_indicators, current_app.config["DEFAULT_INDICATORS"])
        try:
            response_data = _build_crypto_live_search_payload(
                market_data_service=market_data_service,
                symbol=symbol,
                interval=interval,
                indicators=indicators,
            )
            return jsonify(_sanitize_response_payload(_trim_trade_response_payload(response_data)))
        except Exception as error:
            current_app.logger.exception("Crypto live search failed for %s", symbol)
            return jsonify(
                {
                    "status": "error",
                    "message": _public_crypto_error_message(error, symbol),
                    "symbol": symbol.upper(),
                    "interval": interval,
                    "lookback": lookback,
                }
            ), 500

    try:
        response_data = market_data_service.get_crypto_pattern_analysis(
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
            persistence_service = persistence_service or _persistence_service()
            try:
                response_data = persistence_service.apply_cached_match_preview(response_data)
            except Exception as error:
                current_app.logger.warning("Could not apply crypto cached preview: %s", error)

        should_persist = (current_app.config.get("PERSIST_ANALYSIS_RUNS", False) or persist_analysis) and not is_production

        if not prefetch_only and should_persist:
            persistence_service = persistence_service or _persistence_service()
            try:
                response_data = persistence_service.save_analysis_run(response_data)
            except Exception as error:
                current_app.logger.warning("Could not persist crypto analysis run: %s", error)

        return jsonify(_sanitize_response_payload(response_data))
    except Exception as error:
        current_app.logger.exception("Crypto analysis failed for %s", symbol)
        return jsonify(
            {
                "status": "error",
                "message": _public_crypto_error_message(error, symbol),
                "symbol": symbol.upper(),
                "interval": interval,
                "lookback": lookback,
            }
        ), 500


@crypto_blueprint.route("/crypto/<symbol>/chart", methods=["GET"])
def get_crypto_chart(symbol):
    symbol = _normalize_crypto_symbol(symbol)
    chart_interval = request.args.get(
        "interval",
        default=current_app.config["DEFAULT_INTERVAL"],
        type=str,
    )
    market_data_service = _crypto_market_data_service()

    try:
        response_data = market_data_service.get_stock_chart_data(
            symbol=symbol,
            chart_interval=chart_interval,
        )
        stock = response_data.setdefault("stock", {})
        stock["sector"] = "Crypto"
        stock["industry"] = "Digital Asset"
        return jsonify(_sanitize_response_payload(response_data))
    except Exception as error:
        current_app.logger.exception("Crypto chart data failed for %s", symbol)
        return jsonify(
            {
                "status": "error",
                "message": _public_crypto_error_message(error, symbol),
                "symbol": symbol.upper(),
                "chartInterval": chart_interval,
            }
        ), 500


@crypto_blueprint.route("/crypto/top50", methods=["GET"])
def get_crypto_top50():
    limit = request.args.get("limit", default=50, type=int)
    market_data_service = _crypto_market_data_service()
    assets = market_data_service.get_top_crypto_assets(limit=max(1, min(limit, 100)))
    return jsonify(
        {
            "status": "ok",
            "dataSource": "live",
            "marketDataProvider": market_data_service._market_provider_label(),
            "assets": assets,
        }
    )
