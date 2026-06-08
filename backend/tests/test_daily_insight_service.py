from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, date, datetime
import os
import threading
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")

from app.core.database import Base, get_db
from app.main import app
from app.models.indicators import DailyInsight, Indicator, Observation
from app.services.daily_insight_service import build_ai_context_from_observations, ensure_daily_insight
from app.workers.celery_app import task_ensure_daily_insight


async def _fake_cache_get(_key: str):
    return None


async def _fake_cache_set(_key: str, _value, ttl: int = 3600):
    return None


class DailyInsightServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.Session = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        Base.metadata.create_all(self.engine)
        self.db = self.Session()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_second_ensure_call_reuses_success_without_openai(self):
        self._seed_observation("DFF", "Fed Funds", "rates", "%", date(2026, 6, 9), 4.5)
        with patch(
            "app.services.daily_insight_service._generate_daily_insight_payload",
            return_value=_fake_payload(),
        ) as mocked:
            first = ensure_daily_insight(self.db, as_of_date=date(2026, 6, 9))
            second = ensure_daily_insight(self.db, as_of_date=date(2026, 6, 9))

        self.assertEqual(mocked.call_count, 1)
        self.assertEqual(first.id, second.id)
        self.assertEqual(second.status, "success")

    def test_missing_success_row_triggers_single_generation_and_persists(self):
        self._seed_observation("DGS10", "10Y Treasury", "rates", "%", date(2026, 6, 9), 4.3)
        with patch(
            "app.services.daily_insight_service._generate_daily_insight_payload",
            return_value=_fake_payload(summary="generated"),
        ) as mocked:
            row = ensure_daily_insight(self.db, as_of_date=date(2026, 6, 9))

        self.assertEqual(mocked.call_count, 1)
        self.assertEqual(row.status, "success")
        self.assertEqual(row.summary, "generated")

    def test_openai_failure_can_retry_on_next_execution(self):
        self._seed_observation("USDKRW", "USD/KRW", "fx", "KRW", date(2026, 6, 9), 1380.0)
        with patch(
            "app.services.daily_insight_service._generate_daily_insight_payload",
            side_effect=RuntimeError("boom"),
        ):
            with self.assertRaises(RuntimeError):
                ensure_daily_insight(self.db, as_of_date=date(2026, 6, 9))

        failed_row = self.db.query(DailyInsight).filter(DailyInsight.as_of_date == date(2026, 6, 9)).first()
        self.assertEqual(failed_row.status, "failed")

        with patch(
            "app.services.daily_insight_service._generate_daily_insight_payload",
            return_value=_fake_payload(summary="recovered"),
        ) as mocked:
            row = ensure_daily_insight(self.db, as_of_date=date(2026, 6, 9))

        self.assertEqual(mocked.call_count, 1)
        self.assertEqual(row.status, "success")
        self.assertEqual(row.summary, "recovered")

    def test_concurrent_execution_creates_single_success_row(self):
        self._seed_observation("CPIAUCSL", "CPI", "macro", "idx", date(2026, 6, 9), 302.1)
        start_event = threading.Event()
        release_event = threading.Event()
        results: list[object] = []

        def blocking_payload(_context):
            start_event.set()
            release_event.wait(timeout=2)
            return _fake_payload(summary="thread-safe")

        def run_thread():
            session = self.Session()
            try:
                results.append(ensure_daily_insight(session, as_of_date=date(2026, 6, 9)))
            finally:
                session.close()

        with patch("app.services.daily_insight_service._generate_daily_insight_payload", side_effect=blocking_payload):
            thread_one = threading.Thread(target=run_thread)
            thread_two = threading.Thread(target=run_thread)
            thread_one.start()
            start_event.wait(timeout=2)
            thread_two.start()
            release_event.set()
            thread_one.join()
            thread_two.join()

        success_rows = self.db.query(DailyInsight).filter(DailyInsight.status == "success").all()
        self.assertEqual(len(success_rows), 1)
        self.assertEqual(sum(1 for result in results if isinstance(result, dict)), 1)
        self.assertEqual(sum(1 for result in results if isinstance(result, DailyInsight)), 1)

    def test_missing_observation_data_stores_fallback_success(self):
        row = ensure_daily_insight(self.db, as_of_date=date(2026, 6, 9))

        self.assertEqual(row.status, "success")
        self.assertIn("fallback", row.summary)

    def test_build_ai_context_uses_observation_query_service(self):
        with patch(
            "app.services.daily_insight_service.get_ai_context_payload",
            return_value={"as_of_date": "2026-06-09", "series": []},
        ) as mocked:
            context = build_ai_context_from_observations(self.db, date(2026, 6, 9))

        mocked.assert_called_once()
        self.assertEqual(context["available_series_count"], 0)

    def _seed_observation(
        self,
        code: str,
        name: str,
        category: str,
        unit: str,
        observed_at: date,
        value: float,
    ):
        indicator = Indicator(
            code=code,
            name=name,
            description=name,
            country="US",
            category=category,
            source="test",
            frequency="daily",
            unit=unit,
        )
        self.db.add(indicator)
        self.db.flush()
        self.db.add(
            Observation(
                indicator_id=indicator.id,
                date=observed_at,
                value=value,
            )
        )
        self.db.commit()


class DailyInsightApiTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.Session = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        Base.metadata.create_all(self.engine)
        self.db = self.Session()
        self.cache_get_patcher = patch("app.api.routes.cache_get", new=_fake_cache_get)
        self.cache_set_patcher = patch("app.api.routes.cache_set", new=_fake_cache_set)
        self.cache_get_patcher.start()
        self.cache_set_patcher.start()

        def override_get_db():
            try:
                yield self.db
            finally:
                pass

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()
        self.cache_get_patcher.stop()
        self.cache_set_patcher.stop()
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_dashboard_summary_enqueues_ensure_when_today_missing(self):
        with patch("app.api.routes.get_today_kst", return_value=date(2026, 6, 9)), \
             patch("app.api.routes.celery.send_task") as mocked_send_task:
            response = self.client.get("/api/summary")

        self.assertEqual(response.status_code, 200)
        mocked_send_task.assert_called_once_with("app.workers.celery_app.task_ensure_daily_insight")

    def test_manual_ensure_endpoint_allows_force_true(self):
        with patch(
            "app.api.routes.ensure_daily_insight",
            return_value=DailyInsight(
                as_of_date=date(2026, 6, 9),
                model="gpt-test",
                summary="forced summary",
                status="success",
            ),
        ) as mocked_ensure:
            response = self.client.post("/api/ai/summary/ensure?force=true&as_of_date=2026-06-09")

        self.assertEqual(response.status_code, 200)
        mocked_ensure.assert_called_once_with(self.db, as_of_date="2026-06-09", force=True)
        self.assertEqual(response.json()["body"], "forced summary")

    def test_celery_ensure_task_returns_json_safe_payload(self):
        with patch(
            "app.workers.celery_app._with_db",
            return_value=DailyInsight(
                as_of_date=date(2026, 6, 9),
                model="gpt-test",
                summary="queued summary",
                status="success",
            ),
        ):
            payload = task_ensure_daily_insight()

        self.assertIsInstance(payload, dict)
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["as_of_date"], "2026-06-09")


def _fake_payload(summary: str = "generated insight") -> dict:
    return {
        "model": "gpt-test",
        "summary": summary,
        "key_points": ["point"],
        "risks": ["risk"],
        "opportunities": ["opportunity"],
    }


if __name__ == "__main__":
    unittest.main()
