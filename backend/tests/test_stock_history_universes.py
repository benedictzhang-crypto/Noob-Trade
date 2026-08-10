import inspect
import unittest

from routes.stock_routes import WEB_GENERATE_SCORING_PROFILE
from services.market_data_service import MarketDataService
from services.quant_scoring_service import QuantScoringService


class StockHistoryUniverseTests(unittest.TestCase):
    def test_web_generate_uses_current_weighted_profile(self):
        scoring = QuantScoringService()

        self.assertEqual(WEB_GENERATE_SCORING_PROFILE, "paper_weighted")
        self.assertEqual(
            scoring.weights_for_profile(WEB_GENERATE_SCORING_PROFILE),
            {
                "MA": 1,
                "EMA": 1,
                "MACD": 10,
                "BOLL": 10,
                "RSI": 5,
                "VOL": 5,
                "KDJ": 3,
                "OI": 3,
                "OBV": 3,
            },
        )

    def test_isolated_strategy_uses_its_full_universe_by_default(self):
        service = object.__new__(MarketDataService)
        service.top_50_symbols = ("AAPL", "MSFT")

        self.assertEqual(service._pro_signal_candidate_symbols(None, "nq8"), ())
        self.assertEqual(
            service._pro_signal_candidate_symbols(None, None),
            ("AAPL", "MSFT"),
        )
        self.assertEqual(
            service._pro_signal_candidate_symbols(["MU", "PANW"], "nq8"),
            ("MU", "PANW"),
        )

    def test_match_details_are_opt_in(self):
        parameters = inspect.signature(MarketDataService.get_cached_pro_signal).parameters

        self.assertIn("include_match_details", parameters)
        self.assertFalse(parameters["include_match_details"].default)


if __name__ == "__main__":
    unittest.main()
