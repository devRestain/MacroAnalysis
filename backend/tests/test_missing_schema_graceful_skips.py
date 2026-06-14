from __future__ import annotations

import os
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite://")

from app.core.database import Base
from app.models import CollectionRun
from app.services.collection_orchestrator import run_guarded_job


class MissingSchemaGracefulSkipTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(self.engine, tables=[CollectionRun.__table__])
        self.db = self.SessionLocal()

    def tearDown(self) -> None:
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_news_job_skips_when_news_items_table_is_missing(self) -> None:
        result = run_guarded_job(self.db, "news")

        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["reason"], "news_items_table_missing")

        saved_run = self.db.query(CollectionRun).filter(CollectionRun.job_key == "news").one()
        self.assertEqual(saved_run.status, "skipped")
        self.assertEqual(saved_run.error_message, "news_items_table_missing")

    def test_snapshot_job_skips_when_change_snapshots_table_is_missing(self) -> None:
        result = run_guarded_job(self.db, "snapshot_compute")

        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["reason"], "change_snapshots_table_missing")

        saved_run = self.db.query(CollectionRun).filter(CollectionRun.job_key == "snapshot_compute").one()
        self.assertEqual(saved_run.status, "skipped")
        self.assertEqual(saved_run.error_message, "change_snapshots_table_missing")


if __name__ == "__main__":
    unittest.main()
