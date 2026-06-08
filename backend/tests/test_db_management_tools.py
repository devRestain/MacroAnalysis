from datetime import datetime
import io
import os
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite://")

from app.commands import db_cleanup
from app.core.database import Base
from app.models.indicators import ChangeSnapshot, CleanupRun
from app.services.db_stats_service import get_db_stats
from app.services.deduplicate_check_service import check_duplicate_candidates


class DbManagementToolTests(unittest.TestCase):
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

    def test_db_stats_returns_dict_structure_on_sqlite_fallback(self):
        self.db.add(
            CleanupRun(
                started_at=datetime(2026, 6, 8, 3, 5, 0),
                finished_at=datetime(2026, 6, 8, 3, 6, 0),
                collection_success_logs_deleted=1,
                collection_failure_logs_deleted=2,
                raw_responses_deleted=0,
                debug_logs_deleted=3,
                scheduler_logs_deleted=4,
                result_json={"ok": True},
            )
        )
        self.db.commit()

        stats = get_db_stats(self.db, top_n=3)

        self.assertIsInstance(stats, dict)
        self.assertIn("database_size_bytes", stats)
        self.assertIn("tables", stats)
        self.assertIn("largest_tables", stats)
        self.assertIn("largest_indexes", stats)
        self.assertIn("latest_cleanup", stats)
        self.assertEqual(stats["largest_indexes"], [])
        self.assertEqual(stats["latest_cleanup"]["debug_logs_deleted"], 3)

    def test_deduplicate_check_is_read_only(self):
        observed_at = datetime(2026, 6, 8, 0, 0, 0)
        self.db.add_all(
            [
                ChangeSnapshot(
                    snapshot_date=observed_at,
                    indicator_key="TEMP",
                    label="temp-1",
                    category="debug",
                    current_value=1.0,
                ),
                ChangeSnapshot(
                    snapshot_date=observed_at,
                    indicator_key="TEMP",
                    label="temp-2",
                    category="debug",
                    current_value=2.0,
                ),
            ]
        )
        self.db.commit()

        before_count = self.db.query(ChangeSnapshot).count()
        with patch(
            "app.services.deduplicate_check_service.DEDUP_TABLES",
            [(ChangeSnapshot, ["indicator_key", "snapshot_date"])],
        ):
            result = check_duplicate_candidates(self.db, sample_limit=2)
        after_count = self.db.query(ChangeSnapshot).count()

        snapshot_result = result["tables"][0]
        self.assertEqual(before_count, after_count)
        self.assertEqual(result["total_duplicate_groups"], 1)
        self.assertEqual(snapshot_result["duplicate_group_count"], 1)
        self.assertEqual(snapshot_result["sample"][0]["duplicate_count"], 2)

    def test_cleanup_command_calls_cleanup_service(self):
        fake_result = {
            "collection_success_logs_deleted": 1,
            "collection_failure_logs_deleted": 0,
            "raw_responses_deleted": 0,
            "debug_logs_deleted": 2,
            "scheduler_logs_deleted": 0,
            "started_at": "2026-06-08T03:05:00",
            "finished_at": "2026-06-08T03:06:00",
        }
        stdout = io.StringIO()
        with patch("app.commands.db_cleanup.run_cleanup", return_value=fake_result) as mocked:
            with redirect_stdout(stdout):
                exit_code = db_cleanup.main([])

        self.assertEqual(exit_code, 0)
        mocked.assert_called_once()
        self.assertIn("Cleanup completed", stdout.getvalue())
        self.assertIn('"debug_logs_deleted": 2', stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
