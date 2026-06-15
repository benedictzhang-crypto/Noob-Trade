from flask import Blueprint, current_app, jsonify, request

from models.market_data import DailyPrice, PatternWindow, Symbol

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
    "quantConfidence",
    "baseHistoricalProbability",
    "weightPenalty",
    "fitRatio",
    "lookbackWindow",
    "windowSize",
    "regime",
    "diversityKey",
}

SYMBOL_ALIASES = {
    "APL": "AAPL",
    "APPL": "AAPL",
    "BRKB": "BRK.B",
    "BRK-B": "BRK.B",
    "BRK/B": "BRK.B",
}

TECHNICAL_MARKET_ERROR_TOKENS = (
    "HTTPSConnectionPool",
    "ConnectTimeoutError",
    "ReadTimeout",
    "Max retries exceeded",
    "marketdata.colab.duke.edu",
    "requests.exceptions",
)


def _normalize_symbol_code(symbol):
    normalized = str(symbol or "").upper().strip()
    compact = normalized.replace(" ", "")
    return SYMBOL_ALIASES.get(compact, SYMBOL_ALIASES.get(normalized, normalized))


def _public_market_error_message(error, symbol):
    raw_message = str(error or "")
    symbol_code = _normalize_symbol_code(symbol) or "This symbol"
    if any(token.lower() in raw_message.lower() for token in TECHNICAL_MARKET_ERROR_TOKENS):
        return f"{symbol_code} market data connection timed out. Please try again in a moment."
    if raw_message:
        return raw_message[:240]
    return f"{symbol_code} data is not accessible right now."


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
            if key == "sector" and str(item).lower() in {"alpaca iex", "yahoo finance", "duke api"}:
                sanitized[key] = "Market Data"
                continue
            if key == "industry" and str(item).lower() in {"no-key market data", "pattern store"}:
                sanitized[key] = "Market Data"
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


def _market_data_service():
    from services.market_data_service import MarketDataService

    return MarketDataService(current_app.config)


def _persistence_service():
    from services.persistence_service import PersistenceService

    return PersistenceService()


def _build_live_search_payload(
    market_data_service,
    symbol: str,
    interval: str,
    lookback: int,
    indicators: list[str],
    chart_interval=None,
):
    symbol_code = _normalize_symbol_code(symbol)
    price_limit = max(lookback + 10, 45)
    prices_payload = market_data_service._get_cached_market_payload(
        f"daily:{symbol_code}:{price_limit}",
        current_app.config.get("MARKET_DATA_CACHE_TTL_SECONDS", 90),
        lambda: market_data_service.market_api.get_daily_prices(symbol_code, limit=price_limit),
    )
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
        "marketDataProvider": market_data_service._market_provider_label(),
        "request": {
            "symbol": symbol_code,
            "interval": interval,
            "chartInterval": chart_interval or interval,
            "lookback": lookback,
            "indicators": indicators,
        },
        "stock": {
            "symbol": symbol_code,
            "companyName": symbol_code,
            "sector": "Market Data",
            "industry": "Signal Workspace",
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
            "series": market_data_service._build_interval_series(
                daily_candles,
                prices,
                chart_interval or interval,
                symbol_code,
            ),
        },
    }


@stock_blueprint.route("/health", methods=["GET"])
def health_check():
    """Small health endpoint for local frontend checks."""
    return jsonify(
        {
            "status": "ok",
            "message": "Backend is running",
            "environment": str(current_app.config.get("ENVIRONMENT", "development")),
        }
    )


@stock_blueprint.route("/stock/<symbol>", methods=["GET"])
def get_stock(symbol):
    """Return stock details and persist the generated analysis run."""
    symbol = _normalize_symbol_code(symbol)
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
    chart_interval = request.args.get(
        "chartInterval",
        default=interval,
        type=str
    )
    raw_indicators = request.args.get("indicators", default="")
    prefetch_only = request.args.get("prefetch", default=0, type=int) == 1
    persist_analysis = request.args.get("persist", default=0, type=int) == 1
    compact_response = request.args.get("compact", default=0, type=int) == 1
    match_details = request.args.get("matchDetails", default=0, type=int) == 1
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
            market_data_service = _market_data_service()
            try:
                response_data = _build_live_search_payload(
                    market_data_service,
                    symbol=symbol,
                    interval=interval,
                    lookback=lookback,
                    indicators=indicators,
                    chart_interval=chart_interval,
                )
                return jsonify(_sanitize_response_payload(_trim_trade_response_payload(response_data)))
            except Exception as error:
                current_app.logger.exception("Production live search failed for %s", symbol)
                return jsonify(
                    {
                        "status": "error",
                        "message": _public_market_error_message(error, symbol),
                        "symbol": symbol.upper(),
                        "interval": interval,
                        "chartInterval": chart_interval,
                        "lookback": lookback,
                    }
                ), 500

    market_data_service = _market_data_service()

    if analysis_mode == "search":
        try:
            response_data = _build_live_search_payload(
                market_data_service,
                symbol=symbol,
                interval=interval,
                lookback=lookback,
                indicators=indicators,
                chart_interval=chart_interval,
            )
            return jsonify(_sanitize_response_payload(_trim_trade_response_payload(response_data)))
        except Exception:
            current_app.logger.warning("Fast stock search failed for %s; falling back to full stock response.", symbol, exc_info=True)

    persistence_service = None

    try:
        response_data = market_data_service.get_stock_pattern_analysis(
            symbol=symbol,
            interval=interval,
            chart_interval=chart_interval,
            lookback_window=lookback,
            raw_indicators=raw_indicators,
            default_indicators=current_app.config["DEFAULT_INDICATORS"],
            compact_response=compact_response,
            analysis_mode=analysis_mode,
            include_match_details=match_details,
        )
        response_data = _trim_trade_response_payload(response_data)

        if not is_production and response_data.get("dataSource") == "live" and response_data.get("_currentWindow"):
            persistence_service = persistence_service or _persistence_service()
            try:
                response_data = persistence_service.apply_cached_match_preview(response_data)
            except Exception as error:
                current_app.logger.warning("Could not apply indicator-aware cached preview: %s", error)

        should_persist = (current_app.config.get("PERSIST_ANALYSIS_RUNS", False) or persist_analysis) and not is_production

        if not prefetch_only and should_persist:
            persistence_service = persistence_service or _persistence_service()
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
                "message": _public_market_error_message(error, symbol),
                "symbol": symbol.upper(),
                "interval": interval,
                "chartInterval": chart_interval,
                "lookback": lookback,
            }
        ), 500


@stock_blueprint.route("/stock/<symbol>/chart", methods=["GET"])
def get_stock_chart(symbol):
    """Return live chart candles without running Generate or historical matching."""
    symbol = _normalize_symbol_code(symbol)
    chart_interval = request.args.get(
        "interval",
        default=request.args.get("chartInterval", default=current_app.config["DEFAULT_INTERVAL"], type=str),
        type=str,
    )
    market_data_service = _market_data_service()

    try:
        response_data = market_data_service.get_stock_chart_data(
            symbol=symbol,
            chart_interval=chart_interval,
        )
        return jsonify(_sanitize_response_payload(response_data))
    except Exception as error:
        current_app.logger.exception("Stock chart data failed for %s", symbol)
        return jsonify(
            {
                "status": "error",
                "message": _public_market_error_message(error, symbol),
                "symbol": symbol.upper(),
                "chartInterval": chart_interval,
            }
        ), 500


@stock_blueprint.route("/market-news", methods=["GET"])
def get_market_news():
    symbol = _normalize_symbol_code(request.args.get("symbol", default="", type=str).strip())
    limit = request.args.get("limit", default=5, type=int)

    market_data_service = _market_data_service()
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
    symbol = _normalize_symbol_code(symbol)
    payload = request.get_json(silent=True) or {}
    interval = str(payload.get("interval") or "daily")
    lookback = int(payload.get("lookback") or current_app.config["DEFAULT_LOOKBACK"])
    current_price = payload.get("currentPrice")
    daily_candles = payload.get("dailyCandles")
    raw_indicators = payload.get("indicators") or current_app.config["DEFAULT_INDICATORS"]
    deep_history = bool(payload.get("deepHistory"))
    raw_candidate_limit = payload.get("candidateLimit")
    try:
        candidate_limit = int(raw_candidate_limit) if raw_candidate_limit is not None else None
    except (TypeError, ValueError):
        candidate_limit = None

    market_data_service = _market_data_service()

    try:
        response_data = market_data_service.get_cached_pro_signal(
            symbol=symbol,
            interval=interval,
            lookback_window=lookback,
            current_price=current_price,
            daily_candles_override=daily_candles,
            indicators=raw_indicators if isinstance(raw_indicators, list) else raw_indicators.split(","),
            deep_history=deep_history,
            candidate_limit=candidate_limit,
        )
        return jsonify(response_data)
    except Exception as error:
        current_app.logger.exception("Pro signal failed for %s", symbol)
        return jsonify(
            {
                "status": "error",
                "message": _public_market_error_message(error, symbol),
                "symbol": symbol.upper(),
                "interval": interval,
                "lookback": lookback,
            }
        ), 500
