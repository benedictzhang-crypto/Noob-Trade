import logging
import time
import threading
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from copy import deepcopy
from datetime import datetime, timedelta
from types import SimpleNamespace
from statistics import mean
from urllib.parse import quote

from config import Config
from models.market_data import DailyPrice, PatternWindow, Symbol
from services.alpaca_market_api_service import AlpacaMarketApiService
from services.persistence_service import PersistenceService
from services.duke_market_api_service import DukeMarketApiService, DukeMarketApiUnavailable
from services.yahoo_market_api_service import YahooMarketApiService
from services.mock_market_data_service import (
    build_mock_stock_pattern_analysis,
    parse_indicators,
)


logger = logging.getLogger(__name__)

VISIBLE_INTERVAL_BARS = {
    "1min": 240,
    "5min": 240,
    "15min": 240,
    "30min": 220,
    "1hour": 220,
    "daily": 3200,
    "5day": 700,
    "weekly": 700,
    "2week": 400,
    "monthly": 240,
}
INTRADAY_INTERVALS = {"1min", "5min", "15min", "30min", "1hour"}


class FallbackMarketApiService:
    """Try the primary market data provider, then a secondary fallback."""

    def __init__(self, primary, secondary=None):
        self.primary = primary
        self.secondary = secondary

    def is_configured(self):
        return self.primary.is_configured() or bool(self.secondary and self.secondary.is_configured())

    def is_available(self):
        return self.primary.is_available() or bool(self.secondary and self.secondary.is_available())

    def mark_unavailable(self, cooldown_seconds=None):
        self.primary.mark_unavailable(cooldown_seconds)
        if self.secondary:
            self.secondary.mark_unavailable(cooldown_seconds)

    def mark_available(self):
        self.primary.mark_available()
        if self.secondary:
            self.secondary.mark_available()

    def get_daily_prices(self, symbol, limit):
        if not self.secondary or not self.secondary.is_configured() or not self.secondary.is_available():
            payload = self.primary.get_daily_prices(symbol, limit)
            self._validate_daily_price_payload(payload, symbol)
            return payload

        executor = ThreadPoolExecutor(max_workers=2)
        pending = {
            executor.submit(self.primary.get_daily_prices, symbol, limit): "primary",
            executor.submit(self.secondary.get_daily_prices, symbol, limit): "secondary",
        }
        errors = []

        try:
            while pending:
                completed, _ = wait(pending, return_when=FIRST_COMPLETED)
                for future in completed:
                    provider_label = pending.pop(future)
                    try:
                        payload = future.result()
                        self._validate_daily_price_payload(payload, symbol)
                        return payload
                    except Exception as error:
                        errors.append(error)
                        logger.warning(
                            "%s daily market data failed quality checks for %s.",
                            provider_label.capitalize(),
                            symbol,
                            exc_info=True,
                        )

            raise errors[-1]
        finally:
            for future in pending:
                future.cancel()
            executor.shutdown(wait=False, cancel_futures=True)

    def get_intraday_prices(self, symbol, interval, limit=390):
        return self._call("get_intraday_prices", symbol, interval, limit)

    def get_company_overview(self, symbol):
        return self._call("get_company_overview", symbol)

    def get_stock_news(self, symbol, limit=5):
        return self._call("get_stock_news", symbol, limit)

    def _call(self, method_name, *args):
        try:
            return getattr(self.primary, method_name)(*args)
        except Exception:
            if self.secondary and self.secondary.is_configured() and self.secondary.is_available():
                logger.warning("Primary market data provider failed; trying secondary %s.", method_name, exc_info=True)
                return getattr(self.secondary, method_name)(*args)
            raise

    def _validate_daily_price_payload(self, payload, symbol):
        rows = payload.get("data", []) if isinstance(payload, dict) else []
        parsed_dates = sorted(
            [
                self._parse_date((row or {}).get("date"))
                for row in rows
            ],
            reverse=True,
        )
        parsed_dates = [item for item in parsed_dates if item is not None]

        if len(parsed_dates) < 20:
            raise DukeMarketApiUnavailable(f"{symbol} daily market data returned too few bars.")

        latest_date = parsed_dates[0]
        if latest_date < (datetime.utcnow().date() - timedelta(days=10)):
            raise DukeMarketApiUnavailable(f"{symbol} daily market data is stale.")

        sample_size = min(60, len(parsed_dates))
        span_days = (parsed_dates[0] - parsed_dates[sample_size - 1]).days
        if span_days > max(120, sample_size * 3):
            raise DukeMarketApiUnavailable(f"{symbol} daily market data is too sparse.")

    def _parse_date(self, value):
        raw_value = str(value or "").strip()
        if not raw_value:
            return None

        try:
            return datetime.fromisoformat(raw_value.replace("Z", "+00:00")).date()
        except ValueError:
            try:
                return datetime.strptime(raw_value[:10], "%Y-%m-%d").date()
            except ValueError:
                return None


class MarketDataService:
    """
    Small service layer for stock pattern analysis data.

    For now it returns mock data. Later this class can coordinate real market
    data providers, pattern engines, and caching without changing the routes.
    """

    MARKET_NEWS_CACHE = {}
    MARKET_API_CACHE = {}
    MARKET_API_CACHE_LOCK = threading.RLock()
    MARKET_API_CACHE_INFLIGHT = {}
    MARKET_API_CACHE_MAX_ENTRIES = 512
    ANALYSIS_RESPONSE_CACHE = {}
    ANALYSIS_RESPONSE_CACHE_LOCK = threading.RLock()
    ANALYSIS_RESPONSE_INFLIGHT = {}
    ANALYSIS_RESPONSE_CACHE_MAX_ENTRIES = 256
    ANALYSIS_RESPONSE_CACHE_TTL_SECONDS = Config.ANALYSIS_RESPONSE_CACHE_TTL_SECONDS
    TOP_50_SYMBOLS = list(Config.MATCH_SCORING_SYMBOLS)
    HOT_NEWS_SYMBOLS = ["SPY", "QQQ", "NVDA", "AAPL", "MSFT", "AMZN", "TSLA", "META", "AMD", "JPM"]
    LIVE_MATCH_TARGET = 20
    LIVE_FORWARD_DAYS = 5
    LIVE_FORWARD_OUTLIER_LIMIT = 40.0
    PRODUCTION_PRICE_LIMIT = 160
    PRODUCTION_SNAPSHOT_PRICE_LIMIT = 90
    PRODUCTION_MATCH_CANDLE_LIMIT = 120
    PRODUCTION_MATCH_STEP = 3
    PRODUCTION_MATCH_TARGET = 6
    CHART_ONLY_PRICE_LIMIT = 1600
    CHART_ONLY_DAILY_LIMITS = {
        "daily": 420,
        "5day": 700,
        "weekly": 900,
        "2week": 900,
        "monthly": 1600,
    }
    PRO_SIGNAL_DEEP_CANDIDATE_LIMIT = 2000
    SYMBOL_ALIASES = {
        "APL": "AAPL",
        "APPL": "AAPL",
        "BRKB": "BRK.B",
        "BRK-B": "BRK.B",
        "BRK/B": "BRK.B",
    }

    def __init__(self, config):
        self.config = config
        self.top_50_symbols = tuple(config.get("MATCH_SCORING_SYMBOLS") or self.TOP_50_SYMBOLS)
        self.persistence_service = PersistenceService()
        self.market_api = self._build_market_api(config)

    def _build_market_api(self, config):
        provider = str(config.get("MARKET_DATA_PROVIDER") or "auto").strip().lower()

        if provider == "duke":
            return DukeMarketApiService(
                base_url=config["MARKET_DATA_BASE_URL"],
                token=config["MARKET_DATA_TOKEN"],
                timeout=config["MARKET_DATA_TIMEOUT_SECONDS"],
                cooldown_seconds=config["MARKET_DATA_COOLDOWN_SECONDS"],
            )

        if provider == "alpaca":
            return AlpacaMarketApiService(
                api_key=config.get("ALPACA_API_KEY", ""),
                api_secret=config.get("ALPACA_API_SECRET", ""),
                base_url=config.get("ALPACA_DATA_BASE_URL", "https://data.alpaca.markets/v2"),
                feed=config.get("ALPACA_DATA_FEED", "iex"),
                timeout=config["MARKET_DATA_TIMEOUT_SECONDS"],
                cooldown_seconds=config["MARKET_DATA_COOLDOWN_SECONDS"],
            )

        if provider == "auto":
            yahoo = YahooMarketApiService(
                base_url=config.get("YAHOO_DATA_BASE_URL", "https://query1.finance.yahoo.com"),
                timeout=config["MARKET_DATA_TIMEOUT_SECONDS"],
                cooldown_seconds=config["MARKET_DATA_COOLDOWN_SECONDS"],
            )
            alpaca = self._build_alpaca_market_api(config)
            if alpaca.is_configured():
                return FallbackMarketApiService(yahoo, alpaca)
            return yahoo

        if provider != "yahoo":
            logger.warning("Unknown MARKET_DATA_PROVIDER=%s; using auto market data provider.", provider)

        return YahooMarketApiService(
            base_url=config.get("YAHOO_DATA_BASE_URL", "https://query1.finance.yahoo.com"),
            timeout=config["MARKET_DATA_TIMEOUT_SECONDS"],
            cooldown_seconds=config["MARKET_DATA_COOLDOWN_SECONDS"],
        )

    def _build_alpaca_market_api(self, config):
        return AlpacaMarketApiService(
            api_key=config.get("ALPACA_API_KEY", ""),
            api_secret=config.get("ALPACA_API_SECRET", ""),
            base_url=config.get("ALPACA_DATA_BASE_URL", "https://data.alpaca.markets/v2"),
            feed=config.get("ALPACA_DATA_FEED", "iex"),
            timeout=config["MARKET_DATA_TIMEOUT_SECONDS"],
            cooldown_seconds=config["MARKET_DATA_COOLDOWN_SECONDS"],
        )

    def _normalize_symbol_code(self, symbol):
        normalized = str(symbol or "").upper().strip()
        compact = normalized.replace(" ", "")
        return self.SYMBOL_ALIASES.get(compact, self.SYMBOL_ALIASES.get(normalized, normalized))

    def _market_provider_label(self):
        provider = str(self.config.get("MARKET_DATA_PROVIDER") or "auto").strip().lower()

        if provider == "auto":
            alpaca = self._build_alpaca_market_api(self.config)
            return "Auto: Yahoo -> Alpaca IEX" if alpaca.is_configured() else "Auto: Yahoo no-key"

        if provider == "alpaca":
            return "Alpaca IEX"

        if provider == "yahoo":
            return "Yahoo no-key"

        if provider == "duke":
            return "Duke API"

        return provider or "Market data"

    def get_stock_pattern_analysis(
        self,
        symbol,
        interval,
        lookback_window,
        raw_indicators,
        default_indicators,
        compact_response=False,
        analysis_mode="full",
        chart_interval=None,
        include_match_details=False,
        scoring_profile=None,
    ):
        indicators = parse_indicators(raw_indicators, default_indicators)
        symbol_code = self._normalize_symbol_code(symbol)
        chart_interval = str(chart_interval or interval or "daily")
        is_production = str(self.config.get("ENVIRONMENT", "")).lower() == "production"
        summary_only = str(analysis_mode or "full").lower() != "full"

        if is_production:
            cache_key = self._analysis_response_cache_key(
                symbol=symbol_code,
                interval=interval,
                lookback_window=lookback_window,
                indicators=indicators,
                compact_response=compact_response,
                analysis_mode=analysis_mode,
                chart_interval=chart_interval,
                include_match_details=include_match_details,
                scoring_profile=scoring_profile,
            )
            cached_response = self._get_cached_analysis_response(cache_key)
            if cached_response is not None:
                if compact_response:
                    self._overlay_cached_live_compact_price(
                        cached_response,
                        symbol_code,
                        max(lookback_window + 10, 45),
                    )
                return cached_response
            is_cache_owner, cache_event = self._begin_analysis_cache_fill(cache_key)
            if not is_cache_owner:
                cached_response = self._wait_for_analysis_cache_fill(cache_key, cache_event)
                if cached_response is not None:
                    return cached_response
                is_cache_owner, cache_event = self._begin_analysis_cache_fill(cache_key)

            def cache_response(response):
                self._store_analysis_response(cache_key, response)
                return response

            cache_error = None
            try:
                if compact_response:
                    try:
                        return cache_response(self._build_production_compact_response(
                            symbol=symbol_code,
                            interval=interval,
                            lookback_window=lookback_window,
                            indicators=indicators,
                            include_match_details=include_match_details,
                            scoring_profile=scoring_profile,
                        ))
                    except Exception:
                        logger.warning(
                            "Production compact response failed for %s; falling back to standard path.",
                            symbol_code,
                            exc_info=True,
                        )

                if self.market_api.is_configured() and self.market_api.is_available():
                    try:
                        response = self._build_live_current_vs_cached_response(
                            symbol=symbol_code,
                            interval=interval,
                            chart_interval=chart_interval,
                            lookback_window=lookback_window,
                            indicators=indicators,
                            compact_response=compact_response,
                            scoring_profile=scoring_profile,
                        )

                        if summary_only:
                            return cache_response(response)

                        try:
                            return cache_response(self.persistence_service.apply_cached_match_preview(
                                response,
                                scoring_profile=scoring_profile,
                            ))
                        except Exception:
                            logger.warning(
                                "Production cached match preview failed for %s; returning live response.",
                                symbol_code,
                                exc_info=True,
                            )
                            return cache_response(response)
                    except DukeMarketApiUnavailable:
                        logger.warning(
                            "Production live market data provider is unavailable for %s; falling back to cached history when possible.",
                            symbol_code,
                            exc_info=True,
                        )
                    except Exception:
                        logger.warning(
                            "Production live generate failed for %s; falling back to cached history when possible.",
                            symbol_code,
                            exc_info=True,
                        )

                if self._has_cached_history(symbol_code):
                    try:
                        return cache_response(self._build_cached_db_response(
                            symbol=symbol_code,
                            interval=interval,
                            chart_interval=chart_interval,
                            lookback_window=lookback_window,
                            indicators=indicators,
                            compact_response=compact_response,
                            apply_match_preview=not summary_only,
                            scoring_profile=scoring_profile,
                        ))
                    except Exception:
                        logger.warning(
                            "Production cached database response failed for %s.",
                            symbol_code,
                            exc_info=True,
                        )

                if self._allow_demo_fallback(symbol_code):
                    return cache_response(self._build_demo_fallback_response(symbol_code, interval, lookback_window, indicators))

                raise ValueError(f"{symbol_code} is temporarily unavailable.")
            except Exception as error:
                cache_error = error
                raise
            finally:
                if is_cache_owner:
                    self._finish_analysis_cache_fill(cache_key, cache_event, error=cache_error)

        if self.market_api.is_configured() and self.market_api.is_available() and self._has_cached_history(symbol_code):
            try:
                return self._build_live_current_vs_cached_response(
                    symbol=symbol_code,
                    interval=interval,
                    chart_interval=chart_interval,
                    lookback_window=lookback_window,
                    indicators=indicators,
                    compact_response=compact_response,
                    scoring_profile=scoring_profile,
                )
            except DukeMarketApiUnavailable:
                logger.warning(
                    "Live market data provider is unavailable for %s; skipping the slower retry path and falling back.",
                    symbol_code,
                    exc_info=True,
                )
            except Exception:
                logger.warning(
                    "Current snapshot build failed for %s and the service is falling back to the slower history path.",
                    symbol_code,
                    exc_info=True,
                )

        if self.market_api.is_configured() and self.market_api.is_available():
            try:
                return self._build_live_response(
                    symbol_code,
                    interval,
                    lookback_window,
                    indicators,
                    chart_interval=chart_interval,
                    compact_response=compact_response,
                    scoring_profile=scoring_profile,
                )
            except DukeMarketApiUnavailable:
                logger.warning(
                    "Live market data provider is unavailable for %s and the service is falling back to mock data.",
                    symbol_code,
                    exc_info=True,
                )
            except Exception:
                logger.warning(
                    "Live market data failed for %s and the service is falling back to mock data.",
                    symbol_code,
                    exc_info=True,
                )

                if not self.config["USE_MOCK_FALLBACK"]:
                    raise

        if is_production:
            raise ValueError(f"{symbol_code} is temporarily unavailable.")

        return self._build_demo_fallback_response(symbol_code, interval, lookback_window, indicators)

    def get_stock_chart_data(self, symbol, chart_interval="daily"):
        symbol_code = self._normalize_symbol_code(symbol)
        chart_interval = str(chart_interval or "daily").strip().lower()

        if chart_interval in INTRADAY_INTERVALS and hasattr(self.market_api, "get_intraday_prices"):
            intraday_limit = VISIBLE_INTERVAL_BARS.get(chart_interval, 390)
            try:
                intraday_payload = self._get_cached_market_payload(
                    f"intraday:{symbol_code}:{chart_interval}:{intraday_limit}",
                    self.config.get("MARKET_DATA_INTRADAY_CACHE_TTL_SECONDS", 20),
                    lambda: self.market_api.get_intraday_prices(
                        symbol_code,
                        chart_interval,
                        limit=intraday_limit,
                    ),
                )
                intraday_prices = intraday_payload.get("data", []) if isinstance(intraday_payload, dict) else []
                intraday_prices = self._normalize_price_rows_latest_first(intraday_prices)
                intraday_candles = self._build_intraday_candles(intraday_prices)

                if intraday_candles:
                    latest = intraday_candles[-1]
                    previous = intraday_candles[-2] if len(intraday_candles) > 1 else latest
                    return {
                        "dataSource": "live",
                        "marketDataProvider": self._market_provider_label(),
                        "request": {
                            "symbol": symbol_code,
                            "chartInterval": chart_interval,
                        },
                        "stock": {
                            "symbol": symbol_code,
                            "currentPrice": self._to_float(latest.get("close")),
                            "previousClose": self._to_float(previous.get("close")),
                            "open": self._to_float(latest.get("open", latest.get("close"))),
                            "volume": self._to_int(latest.get("volume", 0)),
                        },
                        "chartData": {
                            "series": {
                                chart_interval: intraday_candles[-intraday_limit:],
                            },
                        },
                    }
            except Exception:
                logger.warning("Could not build chart-only %s candles for %s.", chart_interval, symbol_code, exc_info=True)

        price_limit = self.CHART_ONLY_DAILY_LIMITS.get(chart_interval, 700)
        prices_payload = self._get_cached_market_payload(
            f"daily:{symbol_code}:{price_limit}",
            self.config.get("MARKET_DATA_CACHE_TTL_SECONDS", 90),
            lambda: self.market_api.get_daily_prices(symbol_code, limit=price_limit),
        )
        prices = prices_payload.get("data", []) if isinstance(prices_payload, dict) else []
        prices = self._normalize_price_rows_latest_first(prices)

        if len(prices) < 2:
            raise ValueError("No price data returned from market API.")

        daily_candles = self._build_daily_candles(prices)
        latest = daily_candles[-1]
        previous = daily_candles[-2] if len(daily_candles) > 1 else latest
        high_values = [self._to_float(item.get("high", item.get("close"))) for item in daily_candles]
        low_values = [self._to_float(item.get("low", item.get("close"))) for item in daily_candles]
        volume_values = [self._to_int(item.get("volume", 0)) for item in daily_candles]
        interval_series = self._build_interval_series(daily_candles, prices, chart_interval, symbol_code)
        selected_series = interval_series.get(chart_interval) or interval_series.get("daily") or []

        return {
            "dataSource": "live",
            "marketDataProvider": self._market_provider_label(),
            "request": {
                "symbol": symbol_code,
                "chartInterval": chart_interval,
            },
            "stock": {
                "symbol": symbol_code,
                "companyName": symbol_code,
                "sector": "Market Data",
                "industry": "Live chart",
                "currentPrice": self._to_float(latest.get("close")),
                "previousClose": self._to_float(previous.get("close")),
                "open": self._to_float(latest.get("open", latest.get("close"))),
                "volume": volume_values[-1] if volume_values else 0,
                "week52High": round(max(high_values[-252:] or high_values), 2),
                "week52Low": round(min(low_values[-252:] or low_values), 2),
            },
            "chartData": {
                "series": {
                    chart_interval: selected_series,
                },
            },
        }

    def _allow_demo_fallback(self, symbol):
        if not (self.config.get("ENABLE_DEMO_FALLBACK") or self.config.get("USE_MOCK_FALLBACK")):
            return False

        if self.config.get("ENABLE_DEMO_FALLBACK_ALL_SYMBOLS", True):
            return True

        fallback_symbols = tuple(self.config.get("DEMO_FALLBACK_SYMBOLS") or ())
        return not fallback_symbols or symbol in fallback_symbols

    def _build_demo_fallback_response(self, symbol, interval, lookback_window, indicators):
        response = build_mock_stock_pattern_analysis(symbol, interval, lookback_window, indicators)
        response["dataSource"] = "demo"
        response["marketDataProvider"] = "Demo replay"
        stock = response.get("stock", {})
        stock["companyName"] = f"{symbol} Demo Market Data"
        stock["sector"] = "Demo"
        stock["industry"] = "Cached replay"
        return response

    def get_market_news(self, symbol=None, limit=5):
        normalized_symbol = self._normalize_symbol_code(symbol)
        hour_bucket = datetime.utcnow().strftime("%Y-%m-%d-%H")
        cache_key = f"{normalized_symbol or 'market'}:{limit}:{hour_bucket}"
        cached_value = self.MARKET_NEWS_CACHE.get(cache_key)
        is_production = str(self.config.get("ENVIRONMENT", "")).lower() == "production"

        if cached_value is not None:
            return cached_value

        if is_production or not self.market_api.is_configured():
            fallback_news = self._build_fallback_news(normalized_symbol, limit)
            self.MARKET_NEWS_CACHE[cache_key] = fallback_news
            return fallback_news

        focus_universe = self._build_news_focus_universe(normalized_symbol)
        collected = []
        seen_links = set()

        for focus_symbol in focus_universe:
            try:
                payload = self.market_api.get_stock_news(focus_symbol, limit=limit)
            except DukeMarketApiUnavailable:
                logger.warning("Live news provider is temporarily unavailable; using fallback headlines.", exc_info=True)
                break
            except Exception:
                logger.warning("Live news fetch failed for %s", focus_symbol, exc_info=True)
                continue

            raw_items = payload.get("data", []) if isinstance(payload, dict) else []

            for item in raw_items:
                article = self._normalize_news_article(item, focus_symbol)
                if not article:
                    continue

                article_link = article["href"]
                if article_link in seen_links:
                    continue

                seen_links.add(article_link)
                collected.append(article)

                if len(collected) >= limit:
                    break

            if len(collected) >= limit:
                break

        if not collected:
            collected = self._build_fallback_news(normalized_symbol, limit)

        self.MARKET_NEWS_CACHE[cache_key] = collected[:limit]
        return collected[:limit]

    def get_cached_pro_signal(
        self,
        symbol,
        interval="daily",
        lookback_window=30,
        current_price=None,
        daily_candles_override=None,
        indicators=None,
        deep_history=False,
        candidate_limit=None,
    ):
        symbol_code = symbol.upper()
        symbol_record = Symbol.query.filter_by(symbol=symbol_code).first()

        if symbol_record is None:
            raise ValueError(f"No cached symbol data found for {symbol_code}.")

        price_limit = max(self.PRODUCTION_PRICE_LIMIT, lookback_window + self.LIVE_FORWARD_DAYS + 10)
        minimum_candle_count = lookback_window + self.LIVE_FORWARD_DAYS + 1
        daily_candles = self._normalize_external_daily_candles(daily_candles_override)

        if len(daily_candles) < minimum_candle_count:
            price_records = self._load_cached_daily_prices(symbol_record, limit=price_limit)

            if len(price_records) < minimum_candle_count:
                raise ValueError(f"Not enough cached price history for {symbol_code}.")

            daily_candles = [
                {
                    "date": record.trade_date.isoformat(),
                    "open": self._to_float(record.open),
                    "high": self._to_float(record.high),
                    "low": self._to_float(record.low),
                    "close": self._to_float(record.close),
                    "volume": self._to_int(record.volume or 0),
                }
                for record in price_records
                if record.trade_date is not None
            ]
        else:
            daily_candles = daily_candles[-price_limit:]

        if current_price is not None and daily_candles:
            live_price = self._to_float(current_price)
            if live_price > 0:
                last_candle = daily_candles[-1]
                last_candle["close"] = live_price
                last_candle["high"] = max(self._to_float(last_candle.get("high")), live_price)
                last_candle["low"] = min(self._to_float(last_candle.get("low")) or live_price, live_price)

        selected_indicators = indicators or ["MA", "EMA", "MACD", "BOLL", "RSI", "VOL", "KDJ", "OI", "OBV"]
        current_price_value = self._to_float(current_price) if current_price is not None else self._to_float(daily_candles[-1]["close"])
        if deep_history:
            live_match_summary = self._build_deep_pro_signal_summary(
                symbol=symbol_code,
                interval=interval,
                lookback_window=lookback_window,
                daily_candles=daily_candles,
                current_price=current_price_value,
                last_date=daily_candles[-1]["date"] if daily_candles else None,
                indicators=selected_indicators,
                compact_response=True,
                candidate_limit=candidate_limit,
            )
        else:
            live_match_summary = self._build_live_match_summary(
                symbol=symbol_code,
                interval=interval,
                lookback_window=lookback_window,
                daily_candles=daily_candles,
                current_price=current_price_value,
                last_date=daily_candles[-1]["date"] if daily_candles else None,
                indicators=selected_indicators,
                compact_response=True,
            )

        return {
            "status": "ok",
            "symbol": symbol_code,
            "companyName": symbol_record.company_name or symbol_code,
            "sector": symbol_record.sector or "Unknown",
            "currentPrice": current_price_value,
            "patternAnalysis": live_match_summary,
        }

    def _normalize_external_daily_candles(self, daily_candles):
        if not isinstance(daily_candles, list):
            return []

        normalized = []
        seen_dates = set()

        for candle in daily_candles:
            if not isinstance(candle, dict):
                continue

            trade_date = str(candle.get("date") or "").strip()
            if not trade_date:
                continue

            if "T" in trade_date:
                trade_date = trade_date.split("T", 1)[0]

            if trade_date in seen_dates:
                continue

            normalized.append(
                {
                    "date": trade_date,
                    "open": self._to_float(candle.get("open")),
                    "high": self._to_float(candle.get("high")),
                    "low": self._to_float(candle.get("low")),
                    "close": self._to_float(candle.get("close")),
                    "volume": self._to_int(candle.get("volume", 0)),
                }
            )
            seen_dates.add(trade_date)

        normalized.sort(key=lambda item: item.get("date") or "")
        return normalized

    def _build_cached_db_response(
        self,
        symbol,
        interval,
        lookback_window,
        indicators,
        chart_interval=None,
        compact_response=False,
        apply_match_preview=True,
        scoring_profile=None,
    ):
        symbol_record = Symbol.query.filter_by(symbol=symbol).first()

        if symbol_record is None:
            raise ValueError(f"No cached symbol data found for {symbol}.")

        price_limit = max(self.PRODUCTION_PRICE_LIMIT, lookback_window + self.LIVE_FORWARD_DAYS + 10)
        price_records = self._load_cached_daily_prices(symbol_record, limit=price_limit)

        if len(price_records) < lookback_window + self.LIVE_FORWARD_DAYS + 1:
            raise ValueError(f"Not enough cached price history for {symbol}.")

        daily_candles = self._serialize_cached_daily_prices(price_records)
        current_price = self._to_float(daily_candles[-1]["close"])
        previous_close = self._to_float(daily_candles[-2]["close"]) if len(daily_candles) > 1 else current_price
        open_price = self._to_float(daily_candles[-1]["open"])
        high_values = [self._to_float(item.get("high", item.get("close"))) for item in daily_candles]
        low_values = [self._to_float(item.get("low", item.get("close"))) for item in daily_candles]
        volume_values = [self._to_int(item.get("volume", 0)) for item in daily_candles]
        current_window = self.persistence_service._find_current_window(
            symbol_record.id,
            interval,
            lookback_window,
        )
        match_summary = self._empty_live_match_summary(
            interval,
            daily_candles[-1]["date"] if daily_candles else None,
            current_price,
        )

        response = {
            "dataSource": "cached",
            "marketDataProvider": "Cached database",
            "_currentWindow": self._current_window_payload(current_window, interval, lookback_window),
            "request": {
                "symbol": symbol,
                "interval": interval,
                "chartInterval": chart_interval or interval,
                "lookback": lookback_window,
                "indicators": indicators,
            },
            "stock": {
                "symbol": symbol,
                "companyName": symbol_record.company_name or symbol,
                "sector": symbol_record.sector or "Unknown",
                "industry": symbol_record.industry or "Unknown",
                "currentPrice": current_price,
                "previousClose": previous_close,
                "open": open_price,
                "volume": volume_values[-1] if volume_values else 0,
                "week52High": round(max(high_values), 2),
                "week52Low": round(min(low_values), 2),
            },
            "patternAnalysis": {
                "lookbackWindow": lookback_window,
                "selectedIndicators": indicators,
                "probabilityOfIncrease": match_summary["probabilityOfIncrease"],
                "probabilityOfDecrease": match_summary["probabilityOfDecrease"],
                "avgReturn": match_summary["avgReturn"],
                "maxDrawdown": match_summary["maxDrawdown"],
                "matchedPatternsCount": match_summary["matchedPatternsCount"],
                "matchedHistoricalPatterns": match_summary["matchedHistoricalPatterns"],
                "quantConfidence": match_summary["quantConfidence"],
                "signalClassification": match_summary["signalClassification"],
                "futureFiveDayProbabilities": match_summary["futureFiveDayProbabilities"],
                "recommendedSellPrice": match_summary["recommendedSellPrice"],
                "recommendedSellDate": match_summary["recommendedSellDate"],
                "stopLossPrice": match_summary["stopLossPrice"],
                "highFitHistoricalPaths": match_summary.get("highFitHistoricalPaths", []),
            },
        }
        if not compact_response:
            response["chartData"] = {
                "series": self._build_interval_series(daily_candles, daily_candles, chart_interval or interval),
            }

        if apply_match_preview:
            return self.persistence_service.apply_cached_match_preview(
                response,
                include_historical_candles=not compact_response,
                scoring_profile=scoring_profile,
            )

        return response

    def _build_production_compact_response(self, symbol, interval, lookback_window, indicators, include_match_details=False, scoring_profile=None):
        price_limit = max(lookback_window + 10, 45)
        try:
            response = self._build_cached_db_response(
                symbol=symbol,
                interval=interval,
                lookback_window=lookback_window,
                indicators=indicators,
                chart_interval=interval,
                compact_response=True,
                apply_match_preview=False,
                scoring_profile=scoring_profile,
            )
            self._overlay_cached_live_compact_price(response, symbol, price_limit)
        except ValueError as error:
            logger.info(
                "Compact cached stock signal is not available for %s; building live snapshot for fixed-library scoring.",
                symbol,
            )
            logger.debug("Compact cached stock signal detail for %s: %s", symbol, error)
            response = self._build_compact_live_snapshot_response(
                symbol,
                interval,
                lookback_window,
                indicators,
                price_limit,
                scoring_profile=scoring_profile,
            )
        except Exception:
            logger.warning(
                "Compact cached stock signal failed for %s; building live snapshot for fixed-library scoring.",
                symbol,
                exc_info=True,
            )
            response = self._build_compact_live_snapshot_response(
                symbol,
                interval,
                lookback_window,
                indicators,
                price_limit,
                scoring_profile=scoring_profile,
            )

        try:
            response = self.persistence_service.apply_cached_match_preview(
                response,
                include_historical_candles=include_match_details,
                scoring_profile=scoring_profile,
            )
        except Exception:
            logger.warning(
                "Production compact cached match preview failed for %s; returning compact signal.",
                symbol,
                exc_info=True,
            )

        if include_match_details:
            response.pop("_currentWindow", None)
        else:
            self._strip_compact_analysis_payload(response)
        return response

    def _build_compact_live_snapshot_response(self, symbol, interval, lookback_window, indicators, price_limit, scoring_profile=None):
        try:
            return self._build_live_current_vs_cached_response(
                symbol=symbol,
                interval=interval,
                chart_interval=interval,
                lookback_window=lookback_window,
                indicators=indicators,
                compact_response=True,
                price_limit=price_limit,
                scoring_profile=scoring_profile,
            )
        except Exception:
            logger.warning("Compact live snapshot signal is not available for %s.", symbol, exc_info=True)
            response = self._build_empty_compact_signal_response(symbol, interval, lookback_window, indicators)
            self._overlay_cached_live_compact_price(response, symbol, price_limit)
            return response

    def _build_empty_compact_signal_response(self, symbol, interval, lookback_window, indicators):
        return {
            "dataSource": "cached",
            "marketDataProvider": "NoobTrade historical cache",
            "request": {
                "symbol": symbol,
                "interval": interval,
                "chartInterval": interval,
                "lookback": lookback_window,
                "indicators": indicators,
            },
            "stock": {
                "symbol": symbol,
                "companyName": symbol,
                "sector": "Market Data",
                "industry": "Historical signal pending",
                "currentPrice": None,
                "previousClose": None,
                "open": None,
                "volume": 0,
                "week52High": None,
                "week52Low": None,
            },
            "patternAnalysis": {
                "lookbackWindow": lookback_window,
                "selectedIndicators": indicators,
                "probabilityOfIncrease": None,
                "probabilityOfDecrease": None,
                "avgReturn": None,
                "maxDrawdown": None,
                "matchedPatternsCount": 0,
                "matchedHistoricalPatterns": [],
                "quantConfidence": None,
                "signalClassification": "Historical score is not available for this symbol yet.",
                "futureFiveDayProbabilities": {"up": [], "down": []},
                "recommendedSellPrice": None,
                "recommendedSellDate": None,
                "stopLossPrice": None,
                "highFitHistoricalPaths": [],
            },
        }

    def _overlay_cached_live_compact_price(self, response, symbol, price_limit):
        cache_key = f"daily:{symbol}:{price_limit}"
        try:
            prices_payload = self._get_cached_market_payload(
                cache_key,
                self.config.get("MARKET_DATA_CACHE_TTL_SECONDS", 90),
                lambda: self.market_api.get_daily_prices(symbol, limit=price_limit),
            )
        except Exception:
            logger.warning("Could not refresh compact live price for %s.", symbol, exc_info=True)
            prices_payload = self._peek_cached_market_payload(cache_key)
        prices = prices_payload.get("data", []) if isinstance(prices_payload, dict) else []
        prices = self._normalize_price_rows_latest_first(prices)

        if not prices:
            return response

        current_price = self._to_float(prices[0].get("close"))
        previous_close = self._to_float(prices[1].get("close", current_price)) if len(prices) > 1 else current_price
        open_price = self._to_float(prices[0].get("open", current_price))
        high_values = [self._to_float(item.get("high", item.get("close"))) for item in prices]
        low_values = [self._to_float(item.get("low", item.get("close"))) for item in prices]
        volume_values = [self._to_int(item.get("volume", 0)) for item in prices]

        stock = response.setdefault("stock", {})
        stock.update(
            {
                "currentPrice": current_price,
                "previousClose": previous_close,
                "open": open_price,
                "volume": sum(volume_values),
                "week52High": round(max(high_values), 2),
                "week52Low": round(min(low_values), 2),
            }
        )
        response["dataSource"] = "live"
        response["marketDataProvider"] = self._market_provider_label()
        return response

    def _strip_compact_analysis_payload(self, response):
        response.pop("_currentWindow", None)
        analysis = response.get("patternAnalysis")
        if isinstance(analysis, dict):
            analysis.pop("matchedHistoricalPatterns", None)
            analysis.pop("highFitHistoricalPaths", None)
        return response

    def _build_live_current_vs_cached_response(self, symbol, interval, lookback_window, indicators, compact_response=False, price_limit=None, chart_interval=None, scoring_profile=None):
        overview, prices = self._fetch_live_overview_and_prices(
            symbol,
            price_limit=price_limit or VISIBLE_INTERVAL_BARS["daily"],
        )

        if not prices:
            raise ValueError("No price data returned from market API.")

        full_recent_candles = self._build_daily_candles(prices)
        prepared_candles = self.persistence_service._prepare_candles(full_recent_candles)
        current_window = self._build_current_window_snapshot(
            prepared_candles,
            interval,
            lookback_window,
        )
        chart_interval = chart_interval or interval
        live_interval_series = None if compact_response else self._build_interval_series(full_recent_candles, prices, chart_interval, symbol)

        if current_window is None:
            raise ValueError(f"Not enough recent data to build {interval}/{lookback_window} snapshot.")

        current_price = self._to_float(prices[0].get("close"))
        previous_close = self._to_float(prices[1].get("close", current_price)) if len(prices) > 1 else current_price
        open_price = self._to_float(prices[0].get("open", current_price))
        high_values = [self._to_float(item.get("high", item.get("close"))) for item in prices]
        low_values = [self._to_float(item.get("low", item.get("close"))) for item in prices]
        volume_values = [self._to_int(item.get("volume", 0)) for item in prices]
        average_return = self._to_float(current_window.avg_return) or 0.0
        max_drawdown = self._to_float(current_window.max_drawdown) or 0.0
        live_match_summary = self._build_live_match_summary(
            symbol=symbol,
            interval=interval,
            lookback_window=lookback_window,
            daily_candles=full_recent_candles,
            current_price=current_price,
            last_date=full_recent_candles[-1]["date"] if full_recent_candles else None,
            indicators=indicators,
            compact_response=compact_response,
            scoring_profile=scoring_profile,
        )
        response = {
            "dataSource": "live",
            "marketDataProvider": self._market_provider_label(),
            "_currentWindow": self._current_window_payload(current_window, interval, lookback_window),
            "_skipCacheWrite": True,
            "request": {
                "symbol": symbol,
                "interval": interval,
                "chartInterval": chart_interval,
                "lookback": lookback_window,
                "indicators": indicators
            },
            "stock": {
                "symbol": symbol,
                "companyName": overview.get("companyName", f"{symbol} Holdings Inc."),
                "sector": overview.get("sector", "Unknown"),
                "industry": overview.get("industry", "Unknown"),
                "currentPrice": current_price,
                "previousClose": previous_close,
                "open": open_price,
                "volume": sum(volume_values),
                "week52High": round(max(high_values), 2),
                "week52Low": round(min(low_values), 2),
            },
            "patternAnalysis": {
                "lookbackWindow": lookback_window,
                "selectedIndicators": indicators,
                "probabilityOfIncrease": live_match_summary["probabilityOfIncrease"],
                "probabilityOfDecrease": live_match_summary["probabilityOfDecrease"],
                "avgReturn": live_match_summary["avgReturn"] if live_match_summary["avgReturn"] is not None else round(average_return, 4),
                "maxDrawdown": live_match_summary["maxDrawdown"] if live_match_summary["maxDrawdown"] is not None else round(max_drawdown, 4),
                "matchedPatternsCount": live_match_summary["matchedPatternsCount"],
                "matchedHistoricalPatterns": live_match_summary["matchedHistoricalPatterns"],
                "quantConfidence": live_match_summary["quantConfidence"],
                "signalClassification": live_match_summary["signalClassification"],
                "futureFiveDayProbabilities": live_match_summary["futureFiveDayProbabilities"],
                "recommendedSellPrice": live_match_summary["recommendedSellPrice"],
                "recommendedSellDate": live_match_summary["recommendedSellDate"],
                "stopLossPrice": live_match_summary["stopLossPrice"],
                "highFitHistoricalPaths": live_match_summary["highFitHistoricalPaths"],
            },
        }
        if compact_response:
            response["patternAnalysis"].pop("matchedHistoricalPatterns", None)
            response["patternAnalysis"].pop("highFitHistoricalPaths", None)
        else:
            response["chartData"] = {
                "series": live_interval_series,
                "history": {
                    "daily": full_recent_candles,
                }
            }
        return response

    def _build_live_response(self, symbol, interval, lookback_window, indicators, price_limit=None, compact_response=False, chart_interval=None, scoring_profile=None):
        overview, prices = self._fetch_live_overview_and_prices(
            symbol,
            price_limit=price_limit or max(lookback_window, 3200),
        )

        if not prices:
            raise ValueError("No price data returned from market API.")

        current_price = self._to_float(prices[0].get("close"))
        previous_close = self._to_float(prices[1].get("close", current_price)) if len(prices) > 1 else current_price
        open_price = self._to_float(prices[0].get("open", current_price))
        high_values = [self._to_float(item.get("high", item.get("close"))) for item in prices]
        low_values = [self._to_float(item.get("low", item.get("close"))) for item in prices]
        volume_values = [self._to_int(item.get("volume", 0)) for item in prices]
        returns = self._calculate_returns(prices)
        full_daily_candles = self._build_daily_candles(prices)
        chart_interval = chart_interval or interval
        interval_series = None if compact_response else self._build_interval_series(full_daily_candles, prices, chart_interval, symbol)
        live_match_summary = self._build_live_match_summary(
            symbol=symbol.upper(),
            interval=interval,
            lookback_window=lookback_window,
            daily_candles=full_daily_candles,
            current_price=current_price,
            last_date=full_daily_candles[-1]["date"] if full_daily_candles else None,
            indicators=indicators,
            compact_response=compact_response,
            scoring_profile=scoring_profile,
        )
        probability_of_increase = live_match_summary["probabilityOfIncrease"] or self._estimate_probability(returns)
        average_return = live_match_summary["avgReturn"]
        max_drawdown = live_match_summary["maxDrawdown"]
        recommended_sell_price = live_match_summary["recommendedSellPrice"]
        stop_loss_price = live_match_summary["stopLossPrice"]
        recommended_sell_date = live_match_summary["recommendedSellDate"]

        response = {
            "dataSource": "live",
            "marketDataProvider": self._market_provider_label(),
            "request": {
                "symbol": symbol.upper(),
                "interval": interval,
                "chartInterval": chart_interval,
                "lookback": lookback_window,
                "indicators": indicators
            },
            "stock": {
                "symbol": symbol.upper(),
                "companyName": overview.get("companyName", f"{symbol.upper()} Holdings Inc."),
                "sector": overview.get("sector", "Unknown"),
                "industry": overview.get("industry", "Unknown"),
                "currentPrice": current_price,
                "previousClose": previous_close,
                "open": open_price,
                "volume": sum(volume_values),
                "week52High": round(max(high_values), 2),
                "week52Low": round(min(low_values), 2)
            },
            "patternAnalysis": {
                "lookbackWindow": lookback_window,
                "selectedIndicators": indicators,
                "probabilityOfIncrease": probability_of_increase,
                "probabilityOfDecrease": live_match_summary["probabilityOfDecrease"],
                "avgReturn": average_return,
                "maxDrawdown": max_drawdown,
                "matchedPatternsCount": live_match_summary["matchedPatternsCount"],
                "matchedHistoricalPatterns": live_match_summary["matchedHistoricalPatterns"],
                "quantConfidence": live_match_summary["quantConfidence"],
                "signalClassification": live_match_summary["signalClassification"],
                "futureFiveDayProbabilities": live_match_summary["futureFiveDayProbabilities"],
                "recommendedSellPrice": recommended_sell_price,
                "recommendedSellDate": recommended_sell_date,
                "stopLossPrice": stop_loss_price,
                "highFitHistoricalPaths": live_match_summary["highFitHistoricalPaths"],
            },
        }
        if compact_response:
            response["patternAnalysis"].pop("matchedHistoricalPatterns", None)
            response["patternAnalysis"].pop("highFitHistoricalPaths", None)
        else:
            response["chartData"] = {
                "series": interval_series,
                "history": {
                    "daily": full_daily_candles
                }
            }
        return response

    def _build_news_focus_universe(self, symbol):
        focus_universe = []

        if symbol:
            focus_universe.append(symbol)

        for hot_symbol in self.HOT_NEWS_SYMBOLS:
            if hot_symbol not in focus_universe:
                focus_universe.append(hot_symbol)

        if symbol:
            for candidate in self.top_50_symbols:
                if candidate != symbol and candidate not in focus_universe:
                    focus_universe.append(candidate)

        return focus_universe

    def _normalize_news_article(self, item, focus_symbol):
        if not isinstance(item, dict):
            return None

        title = (
            item.get("title")
            or item.get("headline")
            or item.get("name")
            or f"{focus_symbol} market update"
        )
        summary = (
            item.get("summary")
            or item.get("description")
            or item.get("snippet")
            or item.get("content")
            or f"Latest market coverage for {focus_symbol}."
        )
        source = (
            item.get("source")
            or item.get("publisher")
            or item.get("site")
            or "Live News"
        )
        published_at = (
            item.get("publishedAt")
            or item.get("published_at")
            or item.get("datetime")
            or item.get("date")
            or item.get("createdAt")
        )
        href = (
            item.get("url")
            or item.get("link")
            or item.get("articleUrl")
            or item.get("article_url")
            or item.get("sourceUrl")
        )

        if not href:
            href = self._build_google_news_link(focus_symbol, title)

        return {
            "title": str(title).strip(),
            "summary": str(summary).strip(),
            "source": str(source).strip(),
            "time": self._format_news_time(published_at),
            "href": href,
            "symbol": focus_symbol,
            "isFocusSymbol": bool(focus_symbol),
        }

    def _build_fallback_news(self, symbol, limit):
        focus_symbol = symbol or ""
        fallback_symbols = self._build_news_focus_universe(focus_symbol)
        stories = []

        for index, fallback_symbol in enumerate(fallback_symbols[: max(limit, 5)]):
            if focus_symbol and index < 2:
                title = f"{focus_symbol} stays active as traders rotate back into the market leaders"
                summary = f"{focus_symbol} remains part of the market conversation while traders compare it with the latest index and sector momentum."
                href = self._build_google_news_link(focus_symbol, f"{focus_symbol} latest stock headlines")
                story_symbol = focus_symbol
            else:
                title = f"Hot market headline: {fallback_symbol} joins the latest rotation watch"
                summary = f"Fresh stock-market coverage is centering on leadership, momentum, and macro follow-through across active names."
                href = self._build_google_news_link(fallback_symbol, f"{fallback_symbol} latest stock headlines")
                story_symbol = fallback_symbol

            stories.append(
                {
                    "title": title,
                    "summary": summary,
                    "source": "Market Headlines",
                    "time": "Live search",
                    "href": href,
                    "symbol": story_symbol,
                    "isFocusSymbol": story_symbol == focus_symbol and bool(focus_symbol),
                }
            )

            if len(stories) >= limit:
                break

        return stories

    def _fetch_live_overview_and_prices(self, symbol, price_limit):
        with ThreadPoolExecutor(max_workers=2) as executor:
            overview_future = executor.submit(
                self._get_cached_market_payload,
                f"overview:{symbol}",
                self.config.get("MARKET_DATA_OVERVIEW_CACHE_TTL_SECONDS", 900),
                lambda: self.market_api.get_company_overview(symbol),
            )
            prices_future = executor.submit(
                self._get_cached_market_payload,
                f"daily:{symbol}:{price_limit}",
                self.config.get("MARKET_DATA_CACHE_TTL_SECONDS", 90),
                lambda: self.market_api.get_daily_prices(symbol, limit=price_limit),
            )
            overview_payload = overview_future.result()
            prices_payload = prices_future.result()

        overview = self._extract_first_record(overview_payload)
        prices = prices_payload.get("data", []) if isinstance(prices_payload, dict) else []
        return overview, self._normalize_price_rows_latest_first(prices)

    def _normalize_price_rows_latest_first(self, prices):
        return sorted(
            list(prices or []),
            key=lambda item: self._parse_datetime((item or {}).get("date")) or datetime.min,
            reverse=True,
        )

    def _get_cached_market_payload(self, cache_key, ttl_seconds, loader):
        ttl = max(0, int(ttl_seconds or 0))
        wait_timeout = max(5.0, float(self.config.get("MARKET_DATA_TIMEOUT_SECONDS", 3.5)) + 1.0)
        owner_event = None
        cached = None

        while owner_event is None:
            now = time.time()
            with self.MARKET_API_CACHE_LOCK:
                cached = self.MARKET_API_CACHE.get(cache_key)
                if ttl and cached and cached.get("expires_at", 0) > now:
                    return deepcopy(cached["value"])

                inflight_event = self.MARKET_API_CACHE_INFLIGHT.get(cache_key)
                if inflight_event is None:
                    owner_event = threading.Event()
                    self.MARKET_API_CACHE_INFLIGHT[cache_key] = owner_event
                    break

            if not inflight_event.wait(timeout=wait_timeout):
                with self.MARKET_API_CACHE_LOCK:
                    stale = self.MARKET_API_CACHE.get(cache_key)
                if stale:
                    return deepcopy(stale["value"])
                raise TimeoutError(f"Timed out waiting for shared market data: {cache_key}")

        try:
            value = loader()
        except Exception:
            with self.MARKET_API_CACHE_LOCK:
                stale = self.MARKET_API_CACHE.get(cache_key)
            if stale:
                logger.warning("Using stale market data cache for %s.", cache_key, exc_info=True)
                return deepcopy(stale["value"])
            raise
        else:
            if ttl:
                now = time.time()
                with self.MARKET_API_CACHE_LOCK:
                    if len(self.MARKET_API_CACHE) >= self.MARKET_API_CACHE_MAX_ENTRIES:
                        oldest_key = min(
                            self.MARKET_API_CACHE,
                            key=lambda key: self.MARKET_API_CACHE[key].get("stored_at", 0),
                        )
                        self.MARKET_API_CACHE.pop(oldest_key, None)

                    self.MARKET_API_CACHE[cache_key] = {
                        "stored_at": now,
                        "expires_at": now + ttl,
                        "value": deepcopy(value),
                    }
            return value
        finally:
            with self.MARKET_API_CACHE_LOCK:
                current_event = self.MARKET_API_CACHE_INFLIGHT.get(cache_key)
                if current_event is owner_event:
                    self.MARKET_API_CACHE_INFLIGHT.pop(cache_key, None)
            owner_event.set()

    def _peek_cached_market_payload(self, cache_key):
        with self.MARKET_API_CACHE_LOCK:
            cached = self.MARKET_API_CACHE.get(cache_key)
            if cached and cached.get("expires_at", 0) > time.time():
                return deepcopy(cached["value"])
        return None

    def _analysis_response_cache_key(
        self,
        symbol,
        interval,
        lookback_window,
        indicators,
        compact_response,
        analysis_mode,
        chart_interval=None,
        include_match_details=False,
        scoring_profile=None,
    ):
        normalized_indicators = ",".join(parse_indicators(",".join(indicators or []), ""))
        return "|".join(
            [
                self.__class__.__name__,
                self._market_provider_label(),
                str(symbol or "").upper(),
                str(interval or "daily"),
                str(chart_interval or interval or "daily"),
                str(int(lookback_window or 0)),
                normalized_indicators,
                str(analysis_mode or "full").lower(),
                "compact" if compact_response else "full",
                "match-details" if include_match_details else "summary",
                str(scoring_profile or "default"),
            ]
        )

    def _get_cached_analysis_response(self, cache_key):
        with self.ANALYSIS_RESPONSE_CACHE_LOCK:
            cached = self.ANALYSIS_RESPONSE_CACHE.get(cache_key)
            if cached and cached.get("expires_at", 0) > time.time():
                return deepcopy(cached["value"])
            if cached:
                self.ANALYSIS_RESPONSE_CACHE.pop(cache_key, None)
        return None

    def _store_analysis_response(self, cache_key, response):
        if not cache_key or not isinstance(response, dict):
            return

        with self.ANALYSIS_RESPONSE_CACHE_LOCK:
            if len(self.ANALYSIS_RESPONSE_CACHE) >= self.ANALYSIS_RESPONSE_CACHE_MAX_ENTRIES:
                oldest_key = min(
                    self.ANALYSIS_RESPONSE_CACHE,
                    key=lambda key: self.ANALYSIS_RESPONSE_CACHE[key].get("stored_at", 0),
                )
                self.ANALYSIS_RESPONSE_CACHE.pop(oldest_key, None)

            now = time.time()
            self.ANALYSIS_RESPONSE_CACHE[cache_key] = {
                "stored_at": now,
                "expires_at": now + self.ANALYSIS_RESPONSE_CACHE_TTL_SECONDS,
                "value": deepcopy(response),
            }

    def _begin_analysis_cache_fill(self, cache_key):
        with self.ANALYSIS_RESPONSE_CACHE_LOCK:
            cached_response = self._get_cached_analysis_response(cache_key)
            if cached_response is not None:
                event = threading.Event()
                event.set()
                return False, event

            inflight = self.ANALYSIS_RESPONSE_INFLIGHT.get(cache_key)
            if inflight is not None:
                return False, inflight["event"]

            event = threading.Event()
            self.ANALYSIS_RESPONSE_INFLIGHT[cache_key] = {"event": event}
            return True, event

    def _wait_for_analysis_cache_fill(self, cache_key, event):
        event.wait(timeout=45)
        return self._get_cached_analysis_response(cache_key)

    def _finish_analysis_cache_fill(self, cache_key, event, error=None):
        with self.ANALYSIS_RESPONSE_CACHE_LOCK:
            inflight = self.ANALYSIS_RESPONSE_INFLIGHT.get(cache_key)
            if inflight is not None and inflight.get("event") is event:
                self.ANALYSIS_RESPONSE_INFLIGHT.pop(cache_key, None)
        event.set()

    def _build_google_news_link(self, symbol, title):
        query = f"{symbol} stock news {title}"
        return f"https://news.google.com/search?q={quote(query)}"

    def _format_news_time(self, published_at):
        if not published_at:
            return "Just now"

        parsed_value = self._parse_datetime(published_at)
        if parsed_value is None:
            return str(published_at)

        delta = datetime.utcnow() - parsed_value
        minutes = max(int(delta.total_seconds() // 60), 0)

        if minutes >= 60:
            hours = max(minutes // 60, 1)
            return f"{hours} hr ago"

        return f"{max(minutes, 1)} min ago"

    def _build_live_match_summary(self, symbol, interval, lookback_window, daily_candles, current_price, last_date, indicators, compact_response=False, scoring_profile=None):
        prepared_candles = self.persistence_service._prepare_candles(daily_candles)
        candles = self.persistence_service._group_prepared_candles(
            prepared_candles,
            self.persistence_service.TIMEFRAME_GROUP_SIZES.get(interval, 1),
        )
        is_production = str(self.config.get("ENVIRONMENT", "")).lower() == "production"

        if is_production and len(candles) > self.PRODUCTION_MATCH_CANDLE_LIMIT:
            candles = candles[-self.PRODUCTION_MATCH_CANDLE_LIMIT:]

        if len(candles) < lookback_window + self.LIVE_FORWARD_DAYS + 1:
            return self._empty_live_match_summary(interval, last_date, current_price)

        current_window_candles = candles[-lookback_window:]
        current_window = self._build_live_window_record(current_window_candles, interval, lookback_window)
        candidates = []
        step = self.PRODUCTION_MATCH_STEP if is_production else 1

        for end_index in range(lookback_window - 1, len(candles) - self.LIVE_FORWARD_DAYS, step):
            candidate_window = candles[end_index - lookback_window + 1:end_index + 1]
            future_window = candles[end_index + 1:end_index + 1 + self.LIVE_FORWARD_DAYS]
            future_stats = self._calculate_future_window_stats(candidate_window, future_window)

            if not self._is_usable_future_stats(future_stats):
                continue

            candidate_record = self._build_live_window_record(candidate_window, interval, lookback_window)
            score = self._score_live_candidate_match(
                current_window,
                candidate_record,
                indicators,
                interval=interval,
                lookback_window=lookback_window,
                scoring_profile=scoring_profile,
            )

            candidates.append(
                {
                    "candidate_window": candidate_window,
                    "future_window": future_window,
                    "candidate_record": candidate_record,
                    "score": score,
                    "distance": self._window_distance(current_window_candles, candidate_window),
                    "future_stats": future_stats,
                }
            )

        if not candidates:
            return self._empty_live_match_summary(interval, last_date, current_price)

        selected_candidates = sorted(
            candidates,
            key=lambda item: (
                -(item["score"].get("selected_score_percent") or 0),
                item["distance"],
            ),
        )[:(self.PRODUCTION_MATCH_TARGET if is_production else self.LIVE_MATCH_TARGET)]
        matched_patterns = []

        for index, item in enumerate(selected_candidates, start=1):
            candidate_window = item["candidate_window"]
            candidate_record = item["candidate_record"]
            future_stats = item["future_stats"]
            score = item["score"]
            match_score = round(score.get("selected_score_percent") or 0, 2)
            return_pct = self._to_float(candidate_record.return_pct)
            max_drawdown = self._to_float(candidate_record.max_drawdown)

            matched_patterns.append(
                {
                    "patternName": self._build_live_pattern_label(interval, lookback_window, index),
                    "matchScore": match_score,
                    "date": candidate_record.end_date.isoformat(),
                    "symbol": symbol,
                    "timeframe": interval,
                    "windowSize": lookback_window,
                    "returnPct": return_pct,
                    "maxDrawdown": max_drawdown,
                    "futureReturn5d": future_stats["maxUpPct"],
                    "futureDrawdown5d": future_stats["maxDownPct"],
                    "futureStats5d": future_stats,
                    "quantSelectedPercent": match_score,
                    "historicalCandles": [] if compact_response else self._serialize_grouped_candles(candidate_window),
                }
            )

        up_probabilities = self._build_threshold_probabilities(matched_patterns, "up")
        down_probabilities = self._build_threshold_probabilities(matched_patterns, "down")
        avg_up_touch = round(mean(match["futureStats5d"]["maxUpPct"] for match in matched_patterns), 4)
        avg_down_touch = round(mean(match["futureStats5d"]["maxDownPct"] for match in matched_patterns), 4)
        signal = "Bullish Bias" if up_probabilities[0]["probability"] >= down_probabilities[0]["probability"] else "Bearish Bias"

        response = {
            "probabilityOfIncrease": up_probabilities[0]["probability"],
            "probabilityOfDecrease": down_probabilities[0]["probability"],
            "avgReturn": avg_up_touch,
            "maxDrawdown": avg_down_touch,
            "matchedPatternsCount": len(matched_patterns),
            "matchedHistoricalPatterns": matched_patterns,
            "quantConfidence": round(mean(match["matchScore"] for match in matched_patterns) / 100, 2),
            "signalClassification": signal,
            "futureFiveDayProbabilities": {
                "up": up_probabilities,
                "down": down_probabilities,
            },
            "recommendedSellPrice": round(current_price * (1 + max(avg_up_touch, 0) / 100), 2),
            "recommendedSellDate": self._estimate_sell_date_from_last_date(interval, last_date),
            "stopLossPrice": round(current_price * (1 + min(avg_down_touch, 0) / 100), 2),
        }
        if compact_response:
            response["highFitHistoricalPaths"] = []
        else:
            response["highFitHistoricalPaths"] = [
                {
                    "label": match["patternName"],
                    "fitScore": match["matchScore"],
                    "status": f"{match['symbol']} ended on {match['date']} | +5D hi {self._format_signed_percent(match['futureReturn5d'])} | -5D lo {self._format_signed_percent(match['futureDrawdown5d'])}",
                }
                for match in matched_patterns
            ]
        return response

    def _score_live_candidate_match(self, current_window, candidate_record, indicators, interval, lookback_window, scoring_profile=None):
        del interval, lookback_window
        return self.persistence_service.quant_scoring_service.score_match(
            current_window,
            candidate_record,
            indicators,
            include_breakdown=False,
            scoring_profile=scoring_profile,
        )

    def _build_deep_pro_signal_summary(
        self,
        symbol,
        interval,
        lookback_window,
        daily_candles,
        current_price,
        last_date,
        indicators,
        compact_response=False,
        candidate_limit=None,
    ):
        prepared_candles = self.persistence_service._prepare_candles(daily_candles)
        current_window = self._build_current_window_snapshot(prepared_candles, interval, lookback_window)
        if current_window is None or current_window.end_date is None:
            return self._empty_live_match_summary(interval, last_date, current_price)

        max_candidates = max(20, int(candidate_limit or self.PRO_SIGNAL_DEEP_CANDIDATE_LIMIT))
        candidate_windows = self._load_recent_pro_signal_candidates(current_window, max_candidates)
        matched_patterns = self._rank_pro_signal_candidates(
            current_window=current_window,
            candidate_windows=candidate_windows,
            indicators=indicators,
            compact_response=compact_response,
        )
        if not matched_patterns:
            return self._empty_live_match_summary(interval, last_date, current_price)

        probability_summary = self.persistence_service._build_future_probability_summary(
            matched_patterns,
            indicators,
        )
        average_return = probability_summary["average_return"]
        average_drawdown = probability_summary["average_drawdown"]
        response = {
            "probabilityOfIncrease": probability_summary["probability_percent"],
            "probabilityOfDecrease": probability_summary["probability_of_decrease"],
            "avgReturn": average_return,
            "maxDrawdown": average_drawdown,
            "matchedPatternsCount": len(matched_patterns),
            "matchedHistoricalPatterns": [] if compact_response else matched_patterns,
            "quantConfidence": probability_summary["historical_confidence"],
            "signalClassification": probability_summary["signal"],
            "futureFiveDayProbabilities": probability_summary["future_five_day_probabilities"],
            "recommendedSellPrice": round(current_price * (1 + max(average_return or 0, 0) / 100), 2),
            "recommendedSellDate": self._estimate_sell_date_from_last_date(interval, last_date),
            "stopLossPrice": round(current_price * (1 + min(average_drawdown or 0, 0) / 100), 2),
        }
        if compact_response:
            response["highFitHistoricalPaths"] = []
        else:
            response["highFitHistoricalPaths"] = [
                {
                    "label": match["patternName"],
                    "fitScore": match["matchScore"],
                    "status": f"{match['symbol']} ended on {match['date']} | +5D hi {self._format_signed_percent(match.get('futureReturn5d'))} | -5D lo {self._format_signed_percent(match.get('futureDrawdown5d'))}",
                }
                for match in matched_patterns
            ]
        return response

    def _load_recent_pro_signal_candidates(self, current_window, limit):
        query = PatternWindow.query.filter(
            PatternWindow.timeframe == current_window.timeframe,
            PatternWindow.window_size == current_window.window_size,
        )
        if self.top_50_symbols:
            query = query.join(
                Symbol,
                Symbol.id == PatternWindow.symbol_id,
            ).filter(Symbol.symbol.in_(self.top_50_symbols))
        if getattr(current_window, "end_date", None) is not None:
            query = query.filter(PatternWindow.end_date < current_window.end_date)

        return query.order_by(
            PatternWindow.end_date.desc(),
            PatternWindow.id.desc(),
        ).limit(limit).all()

    def _rank_pro_signal_candidates(self, current_window, candidate_windows, indicators, compact_response=False):
        if not candidate_windows:
            return []

        ranked_matches = []
        for candidate in candidate_windows:
            score = self.persistence_service.quant_scoring_service.score_match(
                current_window,
                candidate,
                indicators,
                include_breakdown=False,
            )
            future_stats_5d = self.persistence_service._cached_forward_extremes(candidate, trading_days=5)
            score["future_stats_5d"] = future_stats_5d
            score["future_return_5d"] = future_stats_5d.get("maxUpPct")
            score["future_drawdown_5d"] = future_stats_5d.get("maxDownPct")
            score["is_future_bullish"] = (
                score["future_return_5d"] is not None and score["future_return_5d"] >= 0.5
            )
            ranked_matches.append((candidate, score))

        ranked_matches.sort(key=lambda item: item[1]["selected_score_percent"], reverse=True)
        top_matches = self.persistence_service._select_match_bundles(ranked_matches)
        matched_windows = [matched_window for matched_window, _ in top_matches]
        matched_symbol_ids = [matched_window.symbol_id for matched_window in matched_windows]
        symbol_lookup = {
            symbol.id: symbol.symbol
            for symbol in Symbol.query.filter(Symbol.id.in_(matched_symbol_ids)).all()
        } if matched_symbol_ids else {}
        candle_lookup = {}
        if not compact_response:
            candle_lookup = self.persistence_service._build_match_candles_map(matched_windows)

        response_matches = []
        for matched_window, score in top_matches:
            future_stats = score.get("future_stats_5d") or self._empty_forward_stat()
            response_matches.append(
                {
                    "patternName": self.persistence_service._build_pattern_label(matched_window),
                    "matchScore": round(score["selected_score_percent"], 2),
                    "date": matched_window.end_date.isoformat(),
                    "symbol": symbol_lookup.get(matched_window.symbol_id, "N/A"),
                    "timeframe": matched_window.timeframe,
                    "windowSize": matched_window.window_size,
                    "returnPct": self.persistence_service._to_response_number(matched_window.return_pct),
                    "maxDrawdown": self.persistence_service._to_response_number(matched_window.max_drawdown),
                    "futureReturn5d": self.persistence_service._to_response_number(score["future_return_5d"]),
                    "futureDrawdown5d": self.persistence_service._to_response_number(score["future_drawdown_5d"]),
                    "isFutureBullish": score["is_future_bullish"],
                    "futureStats5d": future_stats,
                    "quantSelectedPercent": score["selected_score_percent"],
                    "historicalCandles": candle_lookup.get(matched_window.id, []),
                }
            )

        return response_matches

    def _empty_live_match_summary(self, interval, last_date, current_price):
        return {
            "probabilityOfIncrease": 50.0,
            "probabilityOfDecrease": 50.0,
            "avgReturn": None,
            "maxDrawdown": None,
            "matchedPatternsCount": 0,
            "matchedHistoricalPatterns": [],
            "quantConfidence": 0.0,
            "signalClassification": "Bullish Bias",
            "futureFiveDayProbabilities": {
                "up": [{"threshold": threshold, "probability": 0.0} for threshold in (1, 5, 10)],
                "down": [{"threshold": threshold, "probability": 0.0} for threshold in (1, 5, 10)],
            },
            "recommendedSellPrice": round(current_price * 1.02, 2),
            "recommendedSellDate": self._estimate_sell_date_from_last_date(interval, last_date),
            "stopLossPrice": round(current_price * 0.98, 2),
            "highFitHistoricalPaths": [],
        }

    def _calculate_future_window_stats(self, candidate_window, future_window):
        if not candidate_window or not future_window:
            return self._empty_forward_stat()

        base_close = self._to_float(candidate_window[-1].get("close"))

        if base_close == 0:
            return self._empty_forward_stat()

        future_high = max((self._to_float(candle.get("high")) for candle in future_window), default=None)
        future_low = min((self._to_float(candle.get("low")) for candle in future_window), default=None)

        if future_high is None or future_low is None:
            return self._empty_forward_stat()

        return {
            "maxUpPct": round(((future_high - base_close) / base_close) * 100, 4),
            "maxDownPct": round(((future_low - base_close) / base_close) * 100, 4),
            "targetPrice": round(future_high, 4),
            "riskPrice": round(future_low, 4),
        }

    def _build_live_window_record(self, candles, interval, lookback_window):
        summary = self.persistence_service._build_window_summary(candles)
        return SimpleNamespace(
            feature_vector=summary["feature_vector"],
            return_pct=summary["return_pct"],
            avg_return=summary["avg_return"],
            max_drawdown=summary["max_drawdown"],
            timeframe=interval,
            window_size=lookback_window,
            end_date=candles[-1]["trade_date"],
            id=None,
        )

    def _serialize_grouped_candles(self, candles):
        serialized = []

        for candle in candles:
            trade_date = candle.get("trade_date")
            serialized.append(
                {
                    "date": trade_date.isoformat() if hasattr(trade_date, "isoformat") else str(trade_date),
                    "open": self._to_float(candle.get("open")),
                    "high": self._to_float(candle.get("high")),
                    "low": self._to_float(candle.get("low")),
                    "close": self._to_float(candle.get("close")),
                    "volume": self._to_int(candle.get("volume", 0)),
                }
            )

        return serialized

    def _is_usable_future_stats(self, future_stats):
        max_up_pct = future_stats.get("maxUpPct")
        max_down_pct = future_stats.get("maxDownPct")

        if max_up_pct is None or max_down_pct is None:
            return False

        return (
            max_up_pct <= self.LIVE_FORWARD_OUTLIER_LIMIT
            and max_down_pct >= -self.LIVE_FORWARD_OUTLIER_LIMIT
        )

    def _window_distance(self, current_window, candidate_window):
        current_path = self._normalized_close_path(current_window)
        candidate_path = self._normalized_close_path(candidate_window)

        if not current_path or not candidate_path or len(current_path) != len(candidate_path):
            return float("inf")

        distance = sum(abs(current_point - candidate_point) for current_point, candidate_point in zip(current_path, candidate_path))
        current_range = max(current_path) - min(current_path)
        candidate_range = max(candidate_path) - min(candidate_path)
        return round(distance + abs(current_range - candidate_range), 6)

    def _normalized_close_path(self, candles):
        if not candles:
            return []

        base_close = self._to_float(candles[0].get("close"))

        if base_close == 0:
            return []

        return [
            round(((self._to_float(candle.get("close")) - base_close) / base_close) * 100, 6)
            for candle in candles
        ]

    def _distance_to_match_score(self, distance, max_distance, rank, total_count):
        if total_count <= 0:
            return 0.0

        distance_ratio = 0.0 if max_distance == 0 else min(distance / max_distance, 1.0)
        rank_penalty = ((rank - 1) / max(total_count - 1, 1)) * 8
        return round(max(55.0, 97.0 - (distance_ratio * 24) - rank_penalty), 2)

    def _window_return_pct_from_candles(self, candles):
        if not candles:
            return 0.0

        start_close = self._to_float(candles[0].get("close"))
        end_close = self._to_float(candles[-1].get("close"))

        if start_close == 0:
            return 0.0

        return round(((end_close - start_close) / start_close) * 100, 4)

    def _window_max_drawdown_from_candles(self, candles):
        closes = [self._to_float(candle.get("close")) for candle in candles]
        peak = closes[0] if closes else 0.0
        max_drawdown = 0.0

        for close in closes:
            if close > peak:
                peak = close

            if peak:
                max_drawdown = min(max_drawdown, ((close - peak) / peak) * 100)

        return round(max_drawdown, 4)

    def _build_threshold_probabilities(self, matched_patterns, side):
        probabilities = []

        for threshold in (1, 5, 10):
            if side == "up":
                hit_count = sum(1 for match in matched_patterns if (match["futureStats5d"].get("maxUpPct") or 0) >= threshold)
            else:
                hit_count = sum(1 for match in matched_patterns if (match["futureStats5d"].get("maxDownPct") or 0) <= -threshold)

            probabilities.append(
                {
                    "threshold": threshold,
                    "probability": round((hit_count / len(matched_patterns)) * 100, 2) if matched_patterns else 0.0,
                }
            )

        return probabilities

    def _build_live_pattern_label(self, interval, lookback_window, rank):
        del interval, lookback_window
        return f"Historical setup #{rank}"

    def _format_signed_percent(self, value):
        if value is None:
            return "TBD"

        numeric_value = self._to_float(value)
        prefix = "+" if numeric_value > 0 else ""
        return f"{prefix}{round(numeric_value, 2)}%"

    def _estimate_sell_date_from_last_date(self, interval, last_date):
        if not last_date:
            return None

        interval_offsets = {
            "daily": 7,
            "5day": 15,
            "weekly": 21,
            "2week": 30,
            "monthly": 45,
        }

        offset_days = interval_offsets.get(interval, 14)

        try:
            parsed_date = datetime.strptime(str(last_date), "%Y-%m-%d").date()
            return (parsed_date + timedelta(days=offset_days)).isoformat()
        except ValueError:
            return None

    def _parse_datetime(self, raw_value):
        if isinstance(raw_value, datetime):
            return raw_value.replace(tzinfo=None)

        if not raw_value:
            return None

        raw_text = str(raw_value).replace("Z", "+00:00")

        for parser in (datetime.fromisoformat,):
            try:
                parsed = parser(raw_text)
                return parsed.replace(tzinfo=None)
            except Exception:
                continue

        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y%m%d"):
            try:
                return datetime.strptime(str(raw_value), fmt)
            except Exception:
                continue

        return None

    def _extract_first_record(self, payload):
        records = payload.get("data")

        if isinstance(records, list) and records:
            return records[0]

        if isinstance(records, dict):
            return records

        return payload

    def _calculate_returns(self, prices):
        returns = []

        for index in range(len(prices) - 1):
            current_close = self._to_float(prices[index].get("close"))
            older_close = self._to_float(prices[index + 1].get("close"))

            if older_close:
                percent_change = ((current_close - older_close) / older_close) * 100
                returns.append(round(percent_change, 2))

        return returns

    def _estimate_probability(self, returns):
        if not returns:
            return 50.0

        positive_count = len([value for value in returns if value > 0])
        return round((positive_count / len(returns)) * 100, 1)

    def _estimate_max_drawdown(self, prices):
        closes = [self._to_float(item.get("close")) for item in prices]
        peak = closes[0]
        max_drawdown = 0.0

        for close in closes:
            if close > peak:
                peak = close

            if peak:
                drawdown = ((close - peak) / peak) * 100
                max_drawdown = min(max_drawdown, drawdown)

        return round(max_drawdown, 2)

    def _build_daily_candles(self, prices, candle_limit=None):
        candles = []

        selected_prices = prices if candle_limit is None else prices[:candle_limit]

        for item in reversed(selected_prices):
            candles.append(
                {
                    "date": item.get("date", "N/A"),
                    "open": self._to_float(item.get("open", item.get("close"))),
                    "high": self._to_float(item.get("high", item.get("close"))),
                    "low": self._to_float(item.get("low", item.get("close"))),
                    "close": self._to_float(item.get("close")),
                    "volume": self._to_int(item.get("volume", 0))
                }
            )

        return candles

    def _build_intraday_candles(self, prices, candle_limit=None):
        candles = []
        selected_prices = prices if candle_limit is None else prices[:candle_limit]

        for item in reversed(selected_prices):
            candles.append(
                {
                    "date": item.get("date", "N/A"),
                    "open": self._to_float(item.get("open", item.get("close"))),
                    "high": self._to_float(item.get("high", item.get("close"))),
                    "low": self._to_float(item.get("low", item.get("close"))),
                    "close": self._to_float(item.get("close")),
                    "volume": self._to_int(item.get("volume", 0)),
                }
            )

        return candles

    def _group_candles_by_size(self, candles, group_size):
        grouped = []

        for index in range(0, len(candles), group_size):
            chunk = candles[index:index + group_size]

            if not chunk:
                continue

            grouped.append(
                {
                    "date": chunk[-1]["date"],
                    "open": chunk[0]["open"],
                    "high": max(item["high"] for item in chunk),
                    "low": min(item["low"] for item in chunk),
                    "close": chunk[-1]["close"],
                    "volume": sum(item["volume"] for item in chunk)
                }
            )

        return grouped

    def _build_monthly_candles(self, prices):
        grouped = {}
        sorted_prices = sorted(
            list(prices or []),
            key=lambda item: self._parse_datetime((item or {}).get("date")) or datetime.min,
        )

        for item in sorted_prices:
            date_value = str(item.get("date", ""))
            month_key = date_value[:7]

            if month_key not in grouped:
                grouped[month_key] = {
                    "date": month_key,
                    "open": self._to_float(item.get("open", item.get("close"))),
                    "high": self._to_float(item.get("high", item.get("close"))),
                    "low": self._to_float(item.get("low", item.get("close"))),
                    "close": self._to_float(item.get("close")),
                    "volume": self._to_int(item.get("volume", 0))
                }
                continue

            month = grouped[month_key]
            month["high"] = max(month["high"], self._to_float(item.get("high", item.get("close"))))
            month["low"] = min(month["low"], self._to_float(item.get("low", item.get("close"))))
            month["close"] = self._to_float(item.get("close"))
            month["volume"] += self._to_int(item.get("volume", 0))

        return list(grouped.values())

    def _build_interval_series(self, daily_candles, prices, selected_interval=None, symbol=None):
        weekly_like = self._group_candles_by_size(daily_candles, 5)
        biweekly = self._group_candles_by_size(daily_candles, 10)
        monthly_source = prices or daily_candles
        monthly = self._build_monthly_candles(monthly_source)

        series = {
            "daily": daily_candles[-VISIBLE_INTERVAL_BARS["daily"]:],
            "5day": weekly_like[-VISIBLE_INTERVAL_BARS["5day"]:],
            "weekly": weekly_like[-VISIBLE_INTERVAL_BARS["weekly"]:],
            "2week": biweekly[-VISIBLE_INTERVAL_BARS["2week"]:],
            "monthly": monthly[-VISIBLE_INTERVAL_BARS["monthly"]:]
        }

        if symbol and selected_interval in INTRADAY_INTERVALS and hasattr(self.market_api, "get_intraday_prices"):
            intraday_limit = VISIBLE_INTERVAL_BARS.get(selected_interval, 390)
            try:
                intraday_payload = self._get_cached_market_payload(
                    f"intraday:{symbol}:{selected_interval}:{intraday_limit}",
                    self.config.get("MARKET_DATA_INTRADAY_CACHE_TTL_SECONDS", 20),
                    lambda: self.market_api.get_intraday_prices(
                        symbol,
                        selected_interval,
                        limit=intraday_limit,
                    ),
                )
                intraday_prices = intraday_payload.get("data", []) if isinstance(intraday_payload, dict) else []
                intraday_candles = self._build_intraday_candles(intraday_prices)
                if intraday_candles:
                    series[selected_interval] = intraday_candles[-VISIBLE_INTERVAL_BARS.get(selected_interval, 390):]
            except Exception:
                logger.warning("Could not fetch %s intraday candles for %s.", selected_interval, symbol, exc_info=True)

            if not series.get(selected_interval) and self._allow_demo_fallback(symbol):
                demo_response = self._build_demo_fallback_response(symbol, selected_interval, 30, ["MA", "EMA", "MACD", "BOLL", "Vol"])
                demo_series = demo_response.get("chartData", {}).get("series", {}).get(selected_interval) or []
                if demo_series:
                    series[selected_interval] = demo_series[-intraday_limit:]

        return series

    def _load_cached_daily_prices(self, symbol_record, limit=None):
        query = DailyPrice.query.filter(
            DailyPrice.symbol_id == symbol_record.id,
        ).order_by(DailyPrice.trade_date.desc())
        if limit:
            query = query.limit(limit)
        records = query.all()
        return list(reversed(records))

    def _serialize_cached_daily_prices(self, records):
        candles = []
        for record in records:
            candles.append(
                {
                    "date": record.trade_date.isoformat() if record.trade_date else "N/A",
                    "open": self._to_float(record.open),
                    "high": self._to_float(record.high),
                    "low": self._to_float(record.low),
                    "close": self._to_float(record.close),
                    "volume": self._to_int(record.volume or 0),
                }
            )
        return candles

    def _has_cached_history(self, symbol):
        symbol_record = Symbol.query.with_entities(Symbol.id).filter_by(symbol=symbol).first()

        if symbol_record is None:
            return False

        return (
            PatternWindow.query.with_entities(PatternWindow.id)
            .filter(PatternWindow.symbol_id == symbol_record.id)
            .limit(1)
            .first()
            is not None
        )

    def _build_current_window_snapshot(self, prepared_candles, interval, lookback_window):
        grouped_candles = self.persistence_service._group_prepared_candles(
            prepared_candles,
            self.persistence_service.TIMEFRAME_GROUP_SIZES.get(interval, 1),
        )

        if len(grouped_candles) < lookback_window:
            return None

        current_window_candles = grouped_candles[-lookback_window:]
        summary = self.persistence_service._build_window_summary(current_window_candles)
        return SimpleNamespace(
            feature_vector=summary["feature_vector"],
            return_pct=summary["return_pct"],
            avg_return=summary["avg_return"],
            max_drawdown=summary["max_drawdown"],
            volatility=summary["volatility"],
            probability_score=summary["probability_score"],
            ma_slope=summary["ma_slope"],
            ema_slope=summary["ema_slope"],
            macd_trend=summary["macd_trend"],
            rsi_avg=summary["rsi_avg"],
            rsi_min=summary["rsi_min"],
            rsi_max=summary["rsi_max"],
            volume_change_ratio=summary["volume_change_ratio"],
            timeframe=interval,
            window_size=lookback_window,
            end_date=current_window_candles[-1]["trade_date"],
            id=None,
        )

    def _current_window_payload(self, current_window, interval, lookback_window):
        if current_window is None:
            return {
                "featureVector": {},
                "returnPct": None,
                "timeframe": interval,
                "windowSize": lookback_window,
                "endDate": None,
            }

        end_date = getattr(current_window, "end_date", None)
        return {
            "featureVector": getattr(current_window, "feature_vector", None) or {},
            "returnPct": self._to_float(getattr(current_window, "return_pct", None)),
            "avgReturn": self._to_float(getattr(current_window, "avg_return", None)),
            "maxDrawdown": self._to_float(getattr(current_window, "max_drawdown", None)),
            "volatility": self._to_float(getattr(current_window, "volatility", None)),
            "probabilityScore": self._to_float(getattr(current_window, "probability_score", None)),
            "maSlope": self._to_float(getattr(current_window, "ma_slope", None)),
            "emaSlope": self._to_float(getattr(current_window, "ema_slope", None)),
            "macdTrend": self._to_float(getattr(current_window, "macd_trend", None)),
            "rsiAvg": self._to_float(getattr(current_window, "rsi_avg", None)),
            "rsiMin": self._to_float(getattr(current_window, "rsi_min", None)),
            "rsiMax": self._to_float(getattr(current_window, "rsi_max", None)),
            "volumeChangeRatio": self._to_float(getattr(current_window, "volume_change_ratio", None)),
            "timeframe": interval,
            "windowSize": lookback_window,
            "endDate": end_date.isoformat() if hasattr(end_date, "isoformat") else end_date,
        }

    def _estimate_sell_date(self, interval, prices):
        last_date = prices[0].get("date", "N/A")

        interval_offsets = {
            "daily": 7,
            "5day": 15,
            "weekly": 21,
            "2week": 30,
            "monthly": 45
        }

        offset_days = interval_offsets.get(interval, 14)

        try:
            parsed_date = datetime.strptime(str(last_date), "%Y-%m-%d").date()
            return (parsed_date + timedelta(days=offset_days)).isoformat()
        except ValueError:
            return None

    def _to_float(self, value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def _to_int(self, value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    def _empty_forward_stat(self):
        return {
            "maxUpPct": None,
            "maxDownPct": None,
            "targetPrice": None,
            "riskPrice": None,
        }
