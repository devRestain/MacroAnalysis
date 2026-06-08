from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
import os
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite://")

from app.core.database import Base
from app.models.indicators import CollectionRun
from app.services.collection_guard import run_with_guard, should_run


class CollectionGuardTests(unittest.TestCase):
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

    def test_should_run_returns_false_when_recent_success_exists(self):
        now = datetime.now(UTC).replace(tzinfo=None, microsecond=0)
        self.db.add(
            CollectionRun(
                job_key="fred_macro",
                provider="fred",
                target_date=now.date(),
                status="success",
                started_at=now - timedelta(minutes=5),
                finished_at=now - timedelta(minutes=1),
                min_interval_minutes=1440,
            )
        )
        self.db.commit()

        result = should_run(self.db, "fred_macro", 1440)

        self.assertFalse(result["should_run"])
        self.assertEqual(result["reason"], "min_interval_not_elapsed")

    def test_should_run_returns_true_after_min_interval_elapsed(self):
        now = datetime.now(UTC).replace(tzinfo=None, microsecond=0)
        self.db.add(
            CollectionRun(
                job_key="fx_rates",
                provider="fx",
                target_date=now.date(),
                status="success",
                started_at=now - timedelta(hours=7),
                finished_at=now - timedelta(hours=7),
                min_interval_minutes=360,
            )
        )
        self.db.commit()

        result = should_run(self.db, "fx_rates", 360)

        self.assertTrue(result["should_run"])
        self.assertIsNone(result["reason"])

    def test_failed_runs_do_not_block_retry(self):
        now = datetime.now(UTC).replace(tzinfo=None, microsecond=0)
        self.db.add(
            CollectionRun(
                job_key="news",
                provider="news",
                target_date=now.date(),
                status="failed",
                started_at=now - timedelta(minutes=30),
                finished_at=now - timedelta(minutes=29),
                min_interval_minutes=360,
                error_message="boom",
            )
        )
        self.db.commit()

        result = should_run(self.db, "news", 360)

        self.assertTrue(result["should_run"])

    def test_lock_failure_is_recorded_as_skipped(self):
        @contextmanager
        def fake_lock(_db, _job_key):
            yield {"acquired": False, "lock_id": None}

        with patch("app.services.collection_guard._job_lock", fake_lock):
            result = run_with_guard(
                self.db,
                job_key="snapshot_compute",
                provider="internal",
                min_interval_minutes=180,
                fn=lambda db: {"fetched_count": 1},
            )

        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["reason"], "lock_not_acquired")
        runs = self.db.query(CollectionRun).filter(CollectionRun.job_key == "snapshot_compute").all()
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0].status, "skipped")


if __name__ == "__main__":
    unittest.main()
