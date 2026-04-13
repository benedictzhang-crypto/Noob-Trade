import logging
from datetime import datetime, timedelta
from types import SimpleNamespace
from statistics import mean
from urllib.parse import quote

from models.market_data import DailyPrice, PatternWindow, Symbol
from services.persistence_service import PersistenceService
from services.duke_market_api_service import DukeMarketApiService, DukeMarketApiUnavailable
from services.mock_market_data_service import (
    build_mock_stock_pattern_analysis,
    parse_indicators,
)


logger = logging.getLogger(__name__)

VISIBLE_INTERVAL_BARS = {
    "daily": 3200,
    "5day": 700,
    "weekly": 700,
    "2week": 400,
    "monthly": 240,
}


class MarketDataService:
    """
    Small service layer for stock pattern analysis data.

    For now it returns mock data. Later this class can coordinate real market
    data providers, pattern engines, and caching without changing the routes.
    """

    MARKET_NEWS_CACHE = {}
    TOP_50_SYMBOLS = [
        "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "BRK.B", "LLY", "AVGO", "JPM",
        "V", "XOM", "UNH", "MA", "COST", "JNJ", "HD", "ORCL", "PG", "MRK",
        "NFLX", "ABBV", "BAC", "KO", "AMD", "CVX", "PEP", "CRM", "WMT", "TMO",
        "ACN", "CSCO", "MCD", "ABT", "IBM", "GE", "LIN", "DIS", "ADBE", "NOW",
        "INTU", "QCOM", "CAT", "TXN", "AXP", "AMAT", "BKNG", "UBER", "GS", "SPY",
    ]
    HOT_NEWS_SYMBOLS = ["SPY", "QQQ", "NVDA", "AAPL", "MSFT", "AMZN", "TSLA", "META", "AMD", "JPM"]
    LIVE_MATCH_TARGET = 20
    LIVE_FORWARD_DAYS = 5
    LIVE_FORWARD_OUTLIER_LIMIT = 40.0
    PRODUCTION_PRICE_LIMIT = 260
    PRODUCTION_SNAPSHOT_PRICE_LIMIT = 90
    PRODUCTION_MATCH_CANDLE_LIMIT = 220
    PRODUCTION_MATCH_STEP = 3
    PRODUCTION_MATCH_TARGET = 10

    def __init__(self, config):
        self.config = config
        self.persistence_service = PersistenceService()
        self.market_api = DukeMarketApiService(
            base_url=config["MARKET_DATA_BASE_URL"],
            token=config["MARKET_DATA_TOKEN"],
            timeout=config["MARKET_DATA_TIMEOUT_SECONDS"],
            cooldown_seconds=config["MARKET_DATA_COOLDOWN_SECONDS"],
        )

    def get_stock_pattern_analysis(self, symbol, interval, lookback_window, raw_indicators, default_indicators, compact_response=False):
        indicators = parse_indicators(raw_indicators, default_indicators)
        symbol_code = symbol.upper()
        is_production = str(self.config.get("ENVIRONMENT", "")).lower() == "production"

        if (
            is_production
            and compact_response
            and self.market_api.is_configured()
            and self.market_api.is_available()
            and self._has_cached_history(symbol_code)
        ):
            try:
                return self._build_production_compact_response(
                    symbol=symbol_code,
                    interval=interval,
                    lookback_window=lookback_window,
                    indicators=indicators,
                )
            except DukeMarketApiUnavailable:
                logger.warning(
                    "Production compact Duke snapshot is unavailable for %s; falling back.",
                    symbol_code,
                    exc_info=True,
                )
            except Exception:
                logger.warning(
                    "Production compact Duke snapshot failed for %s; falling back.",
                    symbol_code,
                    exc_info=True,
                )

        if (
            is_production
            and self.market_api.is_configured()
            and self.market_api.is_available()
            and self._has_cached_history(symbol_code)
        ):
            try:
                return self._build_live_current_vs_cached_response(
                    symbol=symbol_code,
                    interval=interval,
                    lookback_window=lookback_window,
                    indicators=indicators,
                    compact_response=compact_response,
                    price_limit=self.PRODUCTION_SNAPSHOT_PRICE_LIMIT,
                )
            except DukeMarketApiUnavailable:
                logger.warning(
                    "Production cached live snapshot provider is unavailable for %s; falling back.",
                    symbol_code,
                    exc_info=True,
                )
            except Exception:
                logger.warning(
                    "Production cached live snapshot failed for %s and the service is falling back.",
                    symbol_code,
                    exc_info=True,
                )

        if self.market_api.is_configured() and self.market_api.is_available() and self._has_cached_history(symbol_code):
            try:
                return self._build_live_current_vs_cached_response(
                    symbol=symbol_code,
                    interval=interval,
                    lookback_window=lookback_window,
                    indicators=indicators,
                    compact_response=compact_response,
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
                return self._build_live_response(symbol_code, interval, lookback_window, indicators, compact_response=compact_response)
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

        return build_mock_stock_pattern_analysis(symbol_code, interval, lookback_window, indicators)

    def get_market_news(self, symbol=None, limit=5):
        normalized_symbol = (symbol or "").upper().strip()
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

    def get_cached_pro_signal(self, symbol, interval="daily", lookback_window=30, current_price=None, indicators=None):
        symbol_code = symbol.upper()
        symbol_record = Symbol.query.filter_by(symbol=symbol_code).first()

        if symbol_record is None:
            raise ValueError(f"No cached symbol data found for {symbol_code}.")

        price_records = DailyPrice.query.filter(
            DailyPrice.symbol_id == symbol_record.id,
        ).order_by(DailyPrice.trade_date.asc()).limit(self.PRODUCTION_MATCH_CANDLE_LIMIT).all()

        if len(price_records) < lookback_window + self.LIVE_FORWARD_DAYS + 1:
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

        if current_price is not None and daily_candles:
            live_price = self._to_float(current_price)
            if live_price > 0:
                last_candle = daily_candles[-1]
                last_candle["close"] = live_price
                last_candle["high"] = max(self._to_float(last_candle.get("high")), live_price)
                last_candle["low"] = min(self._to_float(last_candle.get("low")) or live_price, live_price)

        selected_indicators = indicators or ["MA", "EMA", "MACD", "BOLL", "RSI", "VOL", "KDJ", "OI", "OBV"]
        current_price_value = self._to_float(current_price) if current_price is not None else self._to_float(daily_candles[-1]["close"])
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

    def _build_production_compact_response(self, symbol, interval, lookback_window, indicators):
        overview_payload = self.market_api.get_company_overview(symbol)
        prices_payload = self.market_api.get_daily_prices(symbol, limit=max(lookback_window + 10, 40))
        overview = self._extract_first_record(overview_payload)
        prices = prices_payload.get("data", [])

        if not prices:
            raise ValueError("No price data returned from market API.")

        current_price = self._to_float(prices[0].get("close"))
        previous_close = self._to_float(prices[1].get("close", current_price)) if len(prices) > 1 else current_price
        open_price = self._to_float(prices[0].get("open", current_price))
        high_values = [self._to_float(item.get("high", item.get("close"))) for item in prices]
        low_values = [self._to_float(item.get("low", item.get("close"))) for item in prices]
        volume_values = [self._to_int(item.get("volume", 0)) for item in prices]

        cached_signal = self.get_cached_pro_signal(
            symbol=symbol,
            interval=interval,
            lookback_window=lookback_window,
            current_price=current_price,
            indicators=indicators,
        )
        analysis = cached_signal.get("patternAnalysis", {})

        return {
            "dataSource": "live",
            "request": {
                "symbol": symbol,
                "interval": interval,
                "lookback": lookback_window,
                "indicators": indicators,
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
                "probabilityOfIncrease": analysis.get("probabilityOfIncrease", 50.0),
                "probabilityOfDecrease": analysis.get("probabilityOfDecrease", 50.0),
                "avgReturn": analysis.get("avgReturn"),
                "maxDrawdown": analysis.get("maxDrawdown"),
                "matchedPatternsCount": analysis.get("matchedPatternsCount", 0),
                "matchedHistoricalPatterns": analysis.get("matchedHistoricalPatterns", []),
                "quantConfidence": analysis.get("quantConfidence", 0.0),
                "signalClassification": analysis.get("signalClassification", "Bullish Bias"),
                "futureFiveDayProbabilities": analysis.get("futureFiveDayProbabilities", {"up": [], "down": []}),
                "recommendedSellPrice": analysis.get("recommendedSellPrice"),
                "recommendedSellDate": analysis.get("recommendedSellDate"),
                "stopLossPrice": analysis.get("stopLossPrice"),
                "highFitHistoricalPaths": analysis.get("highFitHistoricalPaths", []),
            },
        }

    def _build_live_current_vs_cached_response(self, symbol, interval, lookback_window, indicators, compact_response=False, price_limit=None):
        symbol_record = Symbol.query.filter_by(symbol=symbol).first()

        if symbol_record is None:
            raise ValueError(f"No cached symbol data found for {symbol}.")

        overview_payload = self.market_api.get_company_overview(symbol)
        prices_payload = self.market_api.get_daily_prices(
            symbol,
            limit=price_limit or VISIBLE_INTERVAL_BARS["daily"],
        )
        overview = self._extract_first_record(overview_payload)
        prices = prices_payload.get("data", [])

        if not prices:
            raise ValueError("No price data returned from market API.")

        full_recent_candles = self._build_daily_candles(prices)
        prepared_candles = self.persistence_service._prepare_candles(full_recent_candles)
        current_window = self._build_current_window_snapshot(
            prepared_candles,
            interval,
            lookback_window,
        )
        live_interval_series = None if compact_response else self._build_interval_series(full_recent_candles, prices)

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
        )
        response = {
            "dataSource": "live",
            "_currentWindow": {
                "featureVector": current_window.feature_vector,
                "returnPct": self._to_float(current_window.return_pct),
                "timeframe": interval,
                "windowSize": lookback_window,
                "endDate": current_window.end_date.isoformat(),
            },
            "_skipCacheWrite": True,
            "request": {
                "symbol": symbol,
                "interval": interval,
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

    def _build_live_response(self, symbol, interval, lookback_window, indicators, price_limit=None, compact_response=False):
        overview_payload = self.market_api.get_company_overview(symbol)
        prices_payload = self.market_api.get_daily_prices(symbol, limit=price_limit or max(lookback_window, 3200))

        overview = self._extract_first_record(overview_payload)
        prices = prices_payload.get("data", [])

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
        interval_series = None if compact_response else self._build_interval_series(full_daily_candles, prices)
        live_match_summary = self._build_live_match_summary(
            symbol=symbol.upper(),
            interval=interval,
            lookback_window=lookback_window,
            daily_candles=full_daily_candles,
            current_price=current_price,
            last_date=full_daily_candles[-1]["date"] if full_daily_candles else None,
            indicators=indicators,
            compact_response=compact_response,
        )
        probability_of_increase = live_match_summary["probabilityOfIncrease"] or self._estimate_probability(returns)
        average_return = live_match_summary["avgReturn"]
        max_drawdown = live_match_summary["maxDrawdown"]
        recommended_sell_price = live_match_summary["recommendedSellPrice"]
        stop_loss_price = live_match_summary["stopLossPrice"]
        recommended_sell_date = live_match_summary["recommendedSellDate"]

        response = {
            "dataSource": "live",
            "request": {
                "symbol": symbol.upper(),
                "interval": interval,
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
            for candidate in self.TOP_50_SYMBOLS:
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

    def _build_live_match_summary(self, symbol, interval, lookback_window, daily_candles, current_price, last_date, indicators, compact_response=False):
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
            score = self.persistence_service.quant_scoring_service.score_match(
                current_window,
                candidate_record,
                indicators,
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
        interval_label = interval.upper()

        if rank == 1:
            return f"{interval_label} {lookback_window}-bar best-fit setup"

        return f"{interval_label} {lookback_window}-bar setup"

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

        for item in reversed(prices):
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

    def _build_interval_series(self, daily_candles, prices):
        weekly_like = self._group_candles_by_size(daily_candles, 5)
        biweekly = self._group_candles_by_size(daily_candles, 10)
        monthly = self._build_monthly_candles(prices)

        return {
            "daily": daily_candles[-VISIBLE_INTERVAL_BARS["daily"]:],
            "5day": weekly_like[-VISIBLE_INTERVAL_BARS["5day"]:],
            "weekly": weekly_like[-VISIBLE_INTERVAL_BARS["weekly"]:],
            "2week": biweekly[-VISIBLE_INTERVAL_BARS["2week"]:],
            "monthly": monthly[-VISIBLE_INTERVAL_BARS["monthly"]:]
        }

    def _has_cached_history(self, symbol):
        symbol_record = Symbol.query.filter_by(symbol=symbol).first()

        if symbol_record is None:
            return False

        return PatternWindow.query.filter(
            PatternWindow.symbol_id == symbol_record.id,
        ).count() > 0

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
            timeframe=interval,
            window_size=lookback_window,
            end_date=current_window_candles[-1]["trade_date"],
            id=None,
        )

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
