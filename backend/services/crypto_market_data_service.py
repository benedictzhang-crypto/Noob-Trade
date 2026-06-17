import logging

from services.crypto_market_api_service import CryptoMarketApiService
from services.crypto_pattern_store_service import CryptoPatternStoreService
from services.market_data_service import MarketDataService
from services.mock_market_data_service import build_mock_stock_pattern_analysis


logger = logging.getLogger(__name__)


class CryptoMarketDataService(MarketDataService):
    """Crypto flavor of the stock market data service with the same response shape."""

    DAILY_GENERATE_STRATEGY = {
        "id": "crypto9-1d-moderate-smooth13",
        "name": "Crypto Daily Moderate",
        "timeframe": "daily",
        "sourceVariantId": "crypto9_1d_smooth13_ma011_ema010_macd011_boll011_rsi011_vol011_kdj011_oi011_obv303__indicator75_path25_thr88",
        "indicatorFitWeight": 0.75,
        "pathWeight": 0.25,
        "buyThreshold": 88.0,
        "evidence": {
            "totalReturnPct": 34.1334,
            "maxDrawdownPct": 5.5299,
            "executedTrades": 2379,
            "winRatePct": 37.4947,
        },
        "indicators": ("MA", "EMA", "MACD", "BOLL", "RSI", "VOL", "KDJ", "OI", "OBV"),
        "weights": {
            "BOLL": 1.1,
            "EMA": 1.0,
            "KDJ": 1.1,
            "MA": 1.1,
            "MACD": 1.1,
            "OBV": 30.3,
            "OI": 1.1,
            "RSI": 1.1,
            "VOL": 1.1,
        },
    }

    def _build_market_api(self, config):
        return CryptoMarketApiService(
            okx_base_url=config.get("OKX_DATA_BASE_URL", "https://www.okx.com"),
            coingecko_base_url=config.get("COINGECKO_DATA_BASE_URL", "https://api.coingecko.com/api/v3"),
            timeout=config["MARKET_DATA_TIMEOUT_SECONDS"],
            cooldown_seconds=config["MARKET_DATA_COOLDOWN_SECONDS"],
            exclude_stablecoins=config.get("CRYPTO_EXCLUDE_STABLECOINS", False),
        )

    def _normalize_symbol_code(self, symbol):
        return self.market_api._normalize_asset_symbol(symbol)

    def _market_provider_label(self):
        return "Crypto: OKX public spot"

    def get_crypto_pattern_analysis(
        self,
        symbol,
        interval,
        lookback_window,
        raw_indicators,
        default_indicators,
        compact_response=False,
        analysis_mode="full",
    ):
        normalized_interval = self._normalize_strategy_interval(interval)
        if self._uses_daily_generate_strategy(normalized_interval):
            raw_indicators = ",".join(self.DAILY_GENERATE_STRATEGY["indicators"])
            response = self._get_daily_pattern_store_response(
                symbol=symbol,
                requested_interval=normalized_interval,
                lookback_window=lookback_window,
                compact_response=compact_response,
                analysis_mode=analysis_mode,
            )
            if response is not None:
                self._overlay_live_crypto_price(response, symbol)
                return response

        try:
            response = self.get_stock_pattern_analysis(
                symbol=symbol,
                interval=normalized_interval,
                lookback_window=lookback_window,
                raw_indicators=raw_indicators,
                default_indicators=default_indicators,
                compact_response=compact_response,
                analysis_mode=analysis_mode,
            )
        except Exception:
            response = self._get_daily_pattern_store_response(
                symbol=symbol,
                requested_interval=normalized_interval,
                lookback_window=lookback_window,
                compact_response=compact_response,
                analysis_mode=analysis_mode,
            )
            if response is not None:
                logger.warning(
                    "Crypto live market data failed for %s/%s; using daily pattern-store fallback.",
                    symbol,
                    normalized_interval,
                    exc_info=True,
                )
                self._overlay_live_crypto_price(response, symbol)
                return response
            raise
        if self._uses_daily_generate_strategy(normalized_interval):
            self._apply_daily_generate_strategy(response)
        return response

    def _get_daily_pattern_store_response(
        self,
        symbol,
        requested_interval,
        lookback_window,
        compact_response,
        analysis_mode,
    ):
        pattern_store = CryptoPatternStoreService(self.config)
        if not pattern_store.is_available():
            return None

        try:
            response = pattern_store.get_crypto_pattern_analysis(
                symbol=symbol,
                interval=self.DAILY_GENERATE_STRATEGY["timeframe"],
                lookback_window=lookback_window,
                compact_response=compact_response,
                analysis_mode=analysis_mode,
            )
        except ValueError as error:
            if not self._should_fallback_from_pattern_store(error):
                raise
            logger.info("Crypto pattern store skipped for %s: %s", symbol, error)
            return None

        self._apply_daily_generate_strategy(response)
        request = response.setdefault("request", {})
        request["requestedInterval"] = requested_interval
        request["fallbackInterval"] = self.DAILY_GENERATE_STRATEGY["timeframe"]
        return response

    def _overlay_live_crypto_price(self, response, symbol):
        if not isinstance(response, dict):
            return response

        symbol_code = self._normalize_symbol_code(symbol)
        try:
            _overview, prices = self._fetch_live_overview_and_prices(
                symbol_code,
                price_limit=max(45, int(self.config.get("DEFAULT_LOOKBACK", 30) or 30) + 10),
            )
        except Exception:
            logger.warning("Could not refresh crypto live price for %s.", symbol_code, exc_info=True)
            return response

        if not prices:
            return response

        current_price = self._to_float(prices[0].get("close"))
        if current_price is None:
            return response

        previous_close = self._to_float(prices[1].get("close", current_price)) if len(prices) > 1 else current_price
        open_price = self._to_float(prices[0].get("open", current_price))
        volume = self._to_float(prices[0].get("volume")) or 0.0
        stock = response.setdefault("stock", {})
        stock.update(
            {
                "currentPrice": current_price,
                "previousClose": previous_close,
                "open": open_price,
                "volume": volume,
            }
        )

        analysis = response.get("patternAnalysis")
        if isinstance(analysis, dict):
            avg_return = self._to_float(analysis.get("avgReturn"))
            max_drawdown = self._to_float(analysis.get("maxDrawdown"))
            if avg_return is not None:
                analysis["recommendedSellPrice"] = round(current_price * (1 + max(avg_return, 0.0) / 100), 8)
            if max_drawdown is not None:
                analysis["stopLossPrice"] = round(current_price * (1 + min(max_drawdown, 0.0) / 100), 8)

        response["dataSource"] = "live"
        response["marketDataProvider"] = self._market_provider_label()
        return response

    def _should_fallback_from_pattern_store(self, error):
        message = str(error).lower()
        return (
            "not in the crypto pattern store" in message
            or "not enough stored candles" in message
        )

    def _normalize_strategy_interval(self, interval):
        normalized = str(interval or "daily").strip().lower()
        if normalized in {"1d", "1day", "day"}:
            return "daily"
        return normalized

    def _uses_daily_generate_strategy(self, interval):
        return self._normalize_strategy_interval(interval) == self.DAILY_GENERATE_STRATEGY["timeframe"]

    def _score_live_candidate_match(self, current_window, candidate_record, indicators, interval, lookback_window):
        if self._uses_daily_generate_strategy(interval):
            return self.persistence_service.quant_scoring_service.score_match(
                current_window,
                candidate_record,
                self.DAILY_GENERATE_STRATEGY["indicators"],
                include_breakdown=False,
                indicator_weights=self.DAILY_GENERATE_STRATEGY["weights"],
                indicator_fit_weight=self.DAILY_GENERATE_STRATEGY["indicatorFitWeight"],
                path_weight=self.DAILY_GENERATE_STRATEGY["pathWeight"],
            )
        return super()._score_live_candidate_match(
            current_window,
            candidate_record,
            indicators,
            interval=interval,
            lookback_window=lookback_window,
        )

    def _apply_daily_generate_strategy(self, response):
        if not isinstance(response, dict):
            return

        analysis = response.get("patternAnalysis")
        if not isinstance(analysis, dict):
            return

        analysis["selectedIndicators"] = list(self.DAILY_GENERATE_STRATEGY["indicators"])
        analysis["strategyProfile"] = {
            "id": self.DAILY_GENERATE_STRATEGY["id"],
            "name": self.DAILY_GENERATE_STRATEGY["name"],
            "timeframe": self.DAILY_GENERATE_STRATEGY["timeframe"],
            "buyThreshold": self.DAILY_GENERATE_STRATEGY["buyThreshold"],
            "mode": "daily-generate-only",
            "probabilityTarget": "5D +1% touch",
        }
        analysis["signalClassification"] = self._daily_strategy_signal_label(analysis)

    def _daily_strategy_signal_label(self, analysis):
        upside_probability = self._to_float(analysis.get("probabilityOfIncrease"))
        downside_probability = self._to_float(analysis.get("probabilityOfDecrease"))
        confidence = self._to_float(analysis.get("quantConfidence"))
        if upside_probability >= 60 and upside_probability >= downside_probability and confidence >= 0.45:
            return "Crypto Daily Moderate Bias"
        if downside_probability > upside_probability:
            return "Crypto Daily Risk Bias"
        return "Crypto Daily Neutral Bias"

    def get_top_crypto_assets(self, limit=50):
        return self.market_api.get_top_market_assets(limit=limit)

    def _build_demo_fallback_response(self, symbol, interval, lookback_window, indicators):
        response = build_mock_stock_pattern_analysis(symbol, interval, lookback_window, indicators)
        response["dataSource"] = "crypto-demo"
        response["marketDataProvider"] = "Crypto demo replay"
        stock = response.get("stock", {})
        stock["companyName"] = f"{symbol} Crypto Demo Data"
        stock["sector"] = "Crypto"
        stock["industry"] = "Cached replay"
        stock["exchange"] = "Demo"
        return response
