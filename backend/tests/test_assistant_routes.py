import unittest

from routes.assistant_routes import ALL_INDICATORS, _rule_based_intent


class AssistantRuleIntentTests(unittest.TestCase):
    def test_select_all_indicators(self):
        result = _rule_based_intent("select all indicators please")

        self.assertEqual(result["intent"], "set_indicator")
        self.assertEqual(result["indicators"], ALL_INDICATORS)
        self.assertTrue(result["active"])
        self.assertGreaterEqual(result["confidence"], 0.92)

    def test_opv_is_treated_as_obv(self):
        result = _rule_based_intent("select OPV please")

        self.assertEqual(result["intent"], "set_indicator")
        self.assertEqual(result["indicators"], ["OBV"])
        self.assertTrue(result["active"])

    def test_generate_again_uses_current_symbol(self):
        result = _rule_based_intent("generate AGAIN", {"symbol": "TSLA"})

        self.assertEqual(result["intent"], "generate")
        self.assertEqual(result["symbol"], "TSLA")
        self.assertGreaterEqual(result["confidence"], 0.92)

    def test_generate_again_never_uses_again_as_symbol(self):
        result = _rule_based_intent("please generate again")

        self.assertEqual(result["intent"], "generate")
        self.assertIsNone(result["symbol"])


if __name__ == "__main__":
    unittest.main()
