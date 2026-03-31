from services.market_data_service import MarketDataService
from services.persistence_service import PersistenceService
from services.mock_market_data_service import build_mock_stock_pattern_analysis


class PrecomputeService:
    """Warm the local cache so Generate can reuse persisted factor windows."""

    def __init__(self, config):
        self.config = config
        self.market_data_service = MarketDataService(config)
        self.persistence_service = PersistenceService()

    def warm_symbols(self, symbols=None, timeframes=None, window_sizes=None):
        selected_symbols = tuple(symbols or self.config["PRECOMPUTE_DEMO_SYMBOLS"])
        results = []

        for symbol in selected_symbols:
            response_data = self._build_cache_seed_response(symbol, window_sizes)
            cache_result = self.persistence_service.warm_symbol_cache(
                response_data,
                timeframes=timeframes,
                window_sizes=window_sizes,
            )
            results.append(cache_result)

        return results

    def _build_cache_seed_response(self, symbol, window_sizes):
        lookback_window = max(window_sizes or self.persistence_service.SUPPORTED_WINDOW_SIZES)
        indicators = self.config["DEFAULT_INDICATORS"]

        if self.market_data_service.market_api.is_configured():
            return self.market_data_service._build_live_response(
                symbol=symbol,
                interval=self.config["DEFAULT_INTERVAL"],
                lookback_window=lookback_window,
                indicators=indicators,
            )

        return build_mock_stock_pattern_analysis(
            symbol=symbol,
            interval=self.config["DEFAULT_INTERVAL"],
            lookback_window=lookback_window,
            indicators=indicators,
        )
