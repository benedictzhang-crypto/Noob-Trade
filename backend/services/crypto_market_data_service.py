from services.crypto_market_api_service import CryptoMarketApiService
from services.market_data_service import MarketDataService
from services.mock_market_data_service import build_mock_stock_pattern_analysis


class CryptoMarketDataService(MarketDataService):
    """Crypto flavor of the stock market data service with the same response shape."""

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
        return self.get_stock_pattern_analysis(
            symbol=symbol,
            interval=interval,
            lookback_window=lookback_window,
            raw_indicators=raw_indicators,
            default_indicators=default_indicators,
            compact_response=compact_response,
            analysis_mode=analysis_mode,
        )

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
