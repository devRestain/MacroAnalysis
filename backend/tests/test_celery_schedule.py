from __future__ import annotations

import unittest

from app.workers.celery_app import celery


class CeleryScheduleTests(unittest.TestCase):
    def test_batched_schedules_are_registered(self):
        schedule = celery.conf.beat_schedule

        self.assertIn("morning-batch", schedule)
        self.assertIn("noon-batch", schedule)
        self.assertIn("evening-batch", schedule)
        self.assertIn("weekly-batch", schedule)
        self.assertIn("cleanup-retention-data", schedule)

    def test_old_hourly_and_fx_specific_schedules_are_removed(self):
        schedule = celery.conf.beat_schedule

        self.assertNotIn("collect-news", schedule)
        self.assertNotIn("collect-fx", schedule)
        self.assertNotIn("collect-us-equity", schedule)
        self.assertNotIn("collect-kr-equity", schedule)
        self.assertNotIn("collect-sectors", schedule)
        self.assertNotIn("collect-fedwatch", schedule)

    def test_timezone_configuration_stays_in_kst(self):
        self.assertEqual(celery.conf.timezone, "Asia/Seoul")
        self.assertTrue(celery.conf.enable_utc)


if __name__ == "__main__":
    unittest.main()
