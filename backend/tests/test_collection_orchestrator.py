from __future__ import annotations

import json
from datetime import date
import unittest
from unittest.mock import patch

from app.models.indicators import DailyInsight
from app.services.collection_orchestrator import (
    _enqueue_daily_insight_if_missing,
    run_evening_batch,
    run_morning_batch,
    run_noon_batch,
    run_weekly_batch,
)


class CollectionOrchestratorTests(unittest.TestCase):
    def test_morning_batch_includes_expected_jobs(self):
        with patch("app.services.collection_orchestrator.run_with_guard", side_effect=_run_with_guard_side_effect), \
             patch("app.services.collection_orchestrator._enqueue_daily_insight_if_missing", return_value=_queue_result()), \
             patch("app.services.collection_orchestrator._invalidate_dashboard_cache"):
            result = run_morning_batch(object())

        job_keys = [job["job_key"] for job in result["jobs"]]
        self.assertIn("fred_rates", job_keys)
        self.assertIn("fred_macro", job_keys)
        self.assertIn("credit_spreads", job_keys)
        self.assertIn("equity_us_global", job_keys)
        self.assertIn("sector_performance", job_keys)
        self.assertIn("fedwatch", job_keys)
        self.assertIn("fx_rates", job_keys)
        self.assertIn("news", job_keys)
        self.assertIn("snapshot_compute", job_keys)
        self.assertIn("daily_insight_enqueue", job_keys)

    def test_noon_batch_only_runs_news_fx_and_snapshot(self):
        with patch("app.services.collection_orchestrator.run_with_guard", side_effect=_run_with_guard_side_effect), \
             patch("app.services.collection_orchestrator._enqueue_daily_insight_if_missing", return_value=_queue_result()), \
             patch("app.services.collection_orchestrator._invalidate_dashboard_cache"):
            result = run_noon_batch(object())

        job_keys = [job["job_key"] for job in result["jobs"]]
        self.assertEqual(job_keys, ["news", "fx_rates", "snapshot_compute", "daily_insight_enqueue"])
        self.assertNotIn("fred_macro", job_keys)
        self.assertNotIn("equity_us_global", job_keys)

    def test_evening_batch_only_runs_asia_fx_news_and_snapshot(self):
        with patch("app.services.collection_orchestrator.run_with_guard", side_effect=_run_with_guard_side_effect), \
             patch("app.services.collection_orchestrator._enqueue_daily_insight_if_missing", return_value=_queue_result()), \
             patch("app.services.collection_orchestrator._invalidate_dashboard_cache"):
            result = run_evening_batch(object())

        job_keys = [job["job_key"] for job in result["jobs"]]
        self.assertEqual(job_keys, ["equity_asia", "fx_rates", "news", "snapshot_compute", "daily_insight_enqueue"])
        self.assertNotIn("fred_rates", job_keys)
        self.assertNotIn("sector_performance", job_keys)
        self.assertNotIn("equity_us_global", job_keys)

    def test_weekly_batch_includes_fomc_calendar(self):
        with patch("app.services.collection_orchestrator.run_with_guard", side_effect=_run_with_guard_side_effect), \
             patch("app.services.collection_orchestrator._invalidate_dashboard_cache"):
            result = run_weekly_batch(object())

        job_keys = [job["job_key"] for job in result["jobs"]]
        self.assertIn("fomc_calendar", job_keys)

    def test_batch_continues_after_partial_failure(self):
        def fake_run_with_guard(_db, job_key, provider, min_interval_minutes, fn):
            if job_key == "fred_macro":
                return {"job_key": job_key, "status": "failed", "reason": "provider_error", "fetched_count": 0, "inserted_count": 0, "updated_count": 0}
            return {"job_key": job_key, "status": "success", "fetched_count": 0, "inserted_count": 0, "updated_count": 0}

        with patch("app.services.collection_orchestrator.run_with_guard", side_effect=fake_run_with_guard), \
             patch("app.services.collection_orchestrator._enqueue_daily_insight_if_missing", return_value=_queue_result()), \
             patch("app.services.collection_orchestrator._invalidate_dashboard_cache"):
            result = run_morning_batch(object())

        job_keys = [job["job_key"] for job in result["jobs"]]
        self.assertIn("snapshot_compute", job_keys)
        macro_job = next(job for job in result["jobs"] if job["job_key"] == "fred_macro")
        self.assertEqual(macro_job["status"], "failed")

    def test_snapshot_runs_at_most_once_per_batch(self):
        seen_job_keys = []

        def fake_run_with_guard(_db, job_key, provider, min_interval_minutes, fn):
            seen_job_keys.append(job_key)
            return {"job_key": job_key, "status": "success", "fetched_count": 0, "inserted_count": 0, "updated_count": 0}

        with patch("app.services.collection_orchestrator.run_with_guard", side_effect=fake_run_with_guard), \
             patch("app.services.collection_orchestrator._enqueue_daily_insight_if_missing", return_value=_queue_result()), \
             patch("app.services.collection_orchestrator._invalidate_dashboard_cache"):
            run_morning_batch(object())

        self.assertEqual(seen_job_keys.count("snapshot_compute"), 1)

    def test_noon_and_evening_use_enqueue_not_direct_openai_call(self):
        with patch("app.services.collection_orchestrator.run_with_guard", side_effect=_run_with_guard_side_effect), \
             patch("app.services.collection_orchestrator._enqueue_daily_insight_if_missing", return_value=_queue_result()) as mocked_enqueue, \
             patch("app.services.collection_orchestrator._invalidate_dashboard_cache"):
            run_noon_batch(object())
            run_evening_batch(object())

        self.assertEqual(mocked_enqueue.call_count, 2)

    def test_batch_result_is_json_serializable_and_invalidates_cache_once(self):
        with patch("app.services.collection_orchestrator.run_with_guard", side_effect=_run_with_guard_side_effect), \
             patch("app.services.collection_orchestrator._enqueue_daily_insight_if_missing", return_value=_queue_result()), \
             patch("app.services.collection_orchestrator._invalidate_dashboard_cache") as mocked_invalidate:
            result = run_morning_batch(object())

        json.dumps(result)
        mocked_invalidate.assert_called_once()

    def test_enqueue_helper_skips_when_success_exists(self):
        existing = DailyInsight(as_of_date=date(2026, 6, 9), status="success")
        with patch("app.services.collection_orchestrator.get_today_kst", return_value=date(2026, 6, 9)), \
             patch("app.services.collection_orchestrator.get_existing_daily_insight", return_value=existing), \
             patch("app.services.collection_orchestrator.settings.AI_DAILY_INSIGHT_ENABLED", True):
            result = _enqueue_daily_insight_if_missing(object())

        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["reason"], "already_succeeded_today")

    def test_enqueue_helper_queues_when_success_missing(self):
        with patch("app.services.collection_orchestrator.get_today_kst", return_value=date(2026, 6, 9)), \
             patch("app.services.collection_orchestrator.get_existing_daily_insight", return_value=None), \
             patch("app.services.collection_orchestrator.settings.AI_DAILY_INSIGHT_ENABLED", True), \
             patch("app.workers.celery_app.celery.send_task") as mocked_send_task:
            result = _enqueue_daily_insight_if_missing(object())

        self.assertEqual(result["status"], "queued")
        mocked_send_task.assert_called_once_with("app.workers.celery_app.task_ensure_daily_insight")


def _run_with_guard_side_effect(_db, job_key, provider, min_interval_minutes, fn):
    return {
        "job_key": job_key,
        "status": "success",
        "fetched_count": 0,
        "inserted_count": 0,
        "updated_count": 0,
    }


def _queue_result():
    return {
        "job_key": "daily_insight_enqueue",
        "status": "queued",
        "reason": "missing_success_row",
        "fetched_count": 0,
        "inserted_count": 0,
        "updated_count": 0,
    }


if __name__ == "__main__":
    unittest.main()
