from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite://")

from app.core.database import Base
from app.models import CollectionRun
from app.services.collection_orchestrator import run_guarded_job


class CollectionFailureVisibilityTests(unittest.TestCase):
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

    def test_equity_bundle_failure_is_reported_as_failed_job(self) -> None:
        with patch("app.services.collection_orchestrator.collect_equity_indices") as equities, patch(
            "app.services.collection_orchestrator.collect_real_economy"
        ) as real_economy:
            equities.side_effect = RuntimeError("yfinance equity collection failed for all tickers: ^GSPC:JSONDecodeError")
            real_economy.side_effect = RuntimeError("yfinance real economy collection failed: RuntimeError: empty history")

            result = run_guarded_job(self.db, "equity_us_global")

        self.assertEqual(result["status"], "failed")
        self.assertIn("yfinance equity collection failed", result["reason"])
        self.assertIn("yfinance real economy collection failed", result["reason"])

        saved_run = self.db.query(CollectionRun).filter(CollectionRun.job_key == "equity_us_global").one()
        self.assertEqual(saved_run.status, "failed")
        self.assertIn("yfinance equity collection failed", saved_run.error_message)

    def test_equity_bundle_partial_success_still_returns_counts(self) -> None:
        with patch("app.services.collection_orchestrator.collect_equity_indices") as equities, patch(
            "app.services.collection_orchestrator.collect_real_economy"
        ) as real_economy:
            equities.return_value = {"fetched_count": 3, "inserted_count": 3, "updated_count": 3}
            real_economy.side_effect = RuntimeError("secondary source unavailable")

            result = run_guarded_job(self.db, "equity_us_global")

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["fetched_count"], 3)


if __name__ == "__main__":
    unittest.main()
