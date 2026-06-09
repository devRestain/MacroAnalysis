from __future__ import annotations

import unittest
from datetime import datetime

from app.collectors.fomc_utils import (
    estimate_next_meeting_move_from_monthly_rates,
    get_fed_funds_futures_symbol,
)


class FomcUtilsTests(unittest.TestCase):
    def test_contract_symbol_uses_cme_month_codes(self) -> None:
        self.assertEqual(get_fed_funds_futures_symbol(datetime(2026, 6, 17)), "ZQM26.CBT")
        self.assertEqual(get_fed_funds_futures_symbol(datetime(2026, 11, 5)), "ZQX26.CBT")

    def test_next_meeting_directional_probs_follow_cme_methodology_example_shape(self) -> None:
        prob_cut, prob_hold, prob_hike = estimate_next_meeting_move_from_monthly_rates(
            meeting_avg_rate=2.5525,
            anchor_avg_rate=3.0600,
            meeting_date=datetime(2022, 9, 21),
        )
        self.assertEqual((prob_cut, prob_hold, prob_hike), (0.0, 0.0, 1.0))


if __name__ == "__main__":
    unittest.main()
