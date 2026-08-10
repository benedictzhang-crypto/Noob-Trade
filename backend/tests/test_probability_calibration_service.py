import unittest

from services.probability_calibration_service import build_probability_calibration_summary


class ProbabilityCalibrationSummaryTests(unittest.TestCase):
    def test_builds_lightweight_summary_from_top_twenty_scores(self):
        matches = [{"matchScore": score} for score in range(100, 70, -1)]

        summary = build_probability_calibration_summary(matches)

        self.assertEqual(summary["method"], "similarity_weighted_v2")
        self.assertEqual(summary["sampleSize"], 20)
        self.assertEqual(summary["top1Similarity"], 100.0)
        self.assertEqual(summary["top10AverageSimilarity"], 95.5)

    def test_ignores_invalid_scores(self):
        summary = build_probability_calibration_summary([
            {"matchScore": "bad"},
            {"matchScore": None},
            {"matchScore": 80},
        ])

        self.assertEqual(summary["sampleSize"], 1)
        self.assertEqual(summary["top1Similarity"], 80.0)


if __name__ == "__main__":
    unittest.main()
