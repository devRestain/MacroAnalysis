from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite://")

from app.core.database import Base
from app.services.collection_orchestrator import run_calendar_batch, run_morning_batch


class CalendarBatchCacheBehaviorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(self.engine)
        self.db = self.SessionLocal()

    def tearDown(self) -> None:
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_calendar_batch_invalidates_only_calendar_cache(self) -> None:
        with patch("app.services.collection_orchestrator.collect_calendar_events") as calendar_events, patch(
            "app.services.collection_orchestrator.collect_fomc_calendar"
        ) as fomc_calendar, patch(
            "app.services.collection_orchestrator.collect_fed_communications"
        ) as communications, patch(
            "app.services.collection_orchestrator._invalidate_dashboard_cache"
        ) as invalidate_dashboard, patch(
            "app.services.collection_orchestrator._invalidate_calendar_cache"
        ) as invalidate_calendar:
            calendar_events.return_value = {"fetched_count": 1, "inserted_count": 1, "updated_count": 1}
            fomc_calendar.return_value = {"fetched_count": 1, "inserted_count": 1, "updated_count": 1}
            communications.return_value = {"fetched_count": 1, "inserted_count": 1, "updated_count": 1}

            result = run_calendar_batch(self.db)

        self.assertEqual(result["batch"], "calendar")
        invalidate_dashboard.assert_not_called()
        invalidate_calendar.assert_called_once()

    def test_morning_batch_invalidates_dashboard_cache(self) -> None:
        success_counts = {"fetched_count": 1, "inserted_count": 1, "updated_count": 1}
        with patch("app.services.collection_orchestrator.collect_rates", return_value=success_counts), patch(
            "app.services.collection_orchestrator.collect_macro", return_value=success_counts
        ), patch(
            "app.services.collection_orchestrator.collect_credit_spreads", return_value=success_counts
        ), patch(
            "app.services.collection_orchestrator._collect_us_global_market_bundle", return_value=success_counts
        ), patch(
            "app.services.collection_orchestrator.collect_sectors", return_value=success_counts
        ), patch(
            "app.services.collection_orchestrator.collect_fedwatch", return_value=success_counts
        ), patch(
            "app.services.collection_orchestrator.collect_exchange_rates", return_value=success_counts
        ), patch(
            "app.services.collection_orchestrator._collect_news_bundle", return_value=success_counts
        ), patch(
            "app.services.collection_orchestrator._compute_snapshots", return_value=success_counts
        ), patch(
            "app.services.collection_orchestrator._enqueue_daily_insight_if_missing",
            return_value={"job_key": "daily_insight_enqueue", "status": "skipped", "reason": "test", "fetched_count": 0, "inserted_count": 0, "updated_count": 0},
        ), patch(
            "app.services.collection_orchestrator._invalidate_dashboard_cache"
        ) as invalidate_dashboard, patch(
            "app.services.collection_orchestrator._invalidate_calendar_cache"
        ) as invalidate_calendar:
            result = run_morning_batch(self.db)

        self.assertEqual(result["batch"], "morning")
        invalidate_dashboard.assert_called_once()
        invalidate_calendar.assert_not_called()


if __name__ == "__main__":
    unittest.main()
