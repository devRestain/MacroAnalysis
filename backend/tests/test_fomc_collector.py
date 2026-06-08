from datetime import datetime
import unittest

from app.collectors.fomc_utils import estimate_policy_probs, parse_meeting_date


class FomcCollectorTests(unittest.TestCase):
    def test_parse_meeting_date_uses_final_day_for_range(self):
        self.assertEqual(parse_meeting_date("January 28-29", 2026), datetime(2026, 1, 29))

    def test_parse_meeting_date_handles_single_day(self):
        self.assertEqual(parse_meeting_date("June 17", 2026), datetime(2026, 6, 17))

    def test_estimate_policy_probs_for_cut_hold_and_hike(self):
        self.assertEqual(estimate_policy_probs(5.00, 4.875), (0.5, 0.5, 0.0))
        self.assertEqual(estimate_policy_probs(5.00, 5.00), (0.0, 1.0, 0.0))
        self.assertEqual(estimate_policy_probs(5.00, 5.125), (0.0, 0.5, 0.5))


if __name__ == "__main__":
    unittest.main()
