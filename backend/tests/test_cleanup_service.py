from datetime import datetime, timedelta
import os
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite://")

from app.core.database import Base
from app.models.indicators import (
    AiSummary,
    ChangeSnapshot,
    DivergenceEvent,
    DivergenceReport,
    InterestRate,
    NewsItem,
    SentimentSignal,
)
from app.services.cleanup_service import CleanupPolicy, run_cleanup


class CleanupServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.Session = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        Base.metadata.create_all(self.engine)
        self.db = self.Session()
        self.now = datetime(2026, 6, 8, 3, 5, 0)
        self.policy = CleanupPolicy(
            collection_success_log_retention_days=90,
            collection_failure_log_retention_days=180,
            raw_response_retention_days=30,
            debug_log_retention_days=30,
            scheduler_log_retention_days=30,
            enable_raw_response_storage=False,
        )

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_old_success_collection_logs_are_deleted(self):
        old_news = NewsItem(
            source="finnhub",
            title="old processed news",
            collected_at=self.now - timedelta(days=120),
            sentiment_extracted=True,
        )
        recent_news = NewsItem(
            source="finnhub",
            title="recent processed news",
            collected_at=self.now - timedelta(days=10),
            sentiment_extracted=True,
        )
        self.db.add_all([old_news, recent_news])
        self.db.commit()

        result = run_cleanup(self.db, now=self.now, policy=self.policy)

        titles = [row.title for row in self.db.query(NewsItem).order_by(NewsItem.id).all()]
        self.assertEqual(result["collection_success_logs_deleted"], 1)
        self.assertEqual(titles, ["recent processed news"])

    def test_success_logs_within_retention_are_kept(self):
        self.db.add(
            NewsItem(
                source="finnhub",
                title="kept processed news",
                collected_at=self.now - timedelta(days=45),
                sentiment_extracted=True,
            )
        )
        self.db.commit()

        result = run_cleanup(self.db, now=self.now, policy=self.policy)

        self.assertEqual(result["collection_success_logs_deleted"], 0)
        self.assertEqual(self.db.query(NewsItem).count(), 1)

    def test_failure_logs_use_longer_retention_window(self):
        keep_failure = NewsItem(
            source="rss",
            title="keep failed-like news",
            collected_at=self.now - timedelta(days=120),
            sentiment_extracted=False,
        )
        delete_failure = NewsItem(
            source="rss",
            title="delete failed-like news",
            collected_at=self.now - timedelta(days=220),
            sentiment_extracted=False,
        )
        self.db.add_all([keep_failure, delete_failure])
        self.db.commit()

        result = run_cleanup(self.db, now=self.now, policy=self.policy)

        titles = [row.title for row in self.db.query(NewsItem).order_by(NewsItem.id).all()]
        self.assertEqual(result["collection_failure_logs_deleted"], 1)
        self.assertEqual(titles, ["keep failed-like news"])

    def test_cleanup_returns_summary_counts_for_debug_and_scheduler_data(self):
        self.db.add_all(
            [
                ChangeSnapshot(
                    snapshot_date=self.now - timedelta(days=45),
                    indicator_key="TEMP",
                    label="temp",
                    category="debug",
                    current_value=1.0,
                ),
                SentimentSignal(
                    source_type="news",
                    source_id=1,
                    batch_date=self.now - timedelta(days=45),
                    extracted_at=self.now - timedelta(days=45),
                    actor="market",
                    dimension="rates",
                    stance="hawkish",
                    stance_score=0.7,
                    intensity=0.8,
                    confidence=0.9,
                    evidence="old",
                ),
                DivergenceEvent(
                    batch_date=self.now - timedelta(days=45),
                    detected_at=self.now - timedelta(days=45),
                    actor="market",
                    dimension="rates",
                    raw_score=0.5,
                    consensus_score=0.1,
                    consensus_strength=0.8,
                    adjusted_gap=0.4,
                    severity="ALERT",
                ),
                DivergenceReport(
                    event_id=1,
                    generated_at=self.now - timedelta(days=45),
                    headline="old report",
                ),
                AiSummary(
                    summary_date=self.now - timedelta(days=45),
                    created_at=self.now - timedelta(days=45),
                    headline="old ai summary",
                    body="body",
                ),
            ]
        )
        self.db.commit()

        result = run_cleanup(self.db, now=self.now, policy=self.policy)

        self.assertEqual(result["raw_responses_deleted"], 0)
        self.assertEqual(result["debug_logs_deleted"], 4)
        self.assertEqual(result["scheduler_logs_deleted"], 1)
        self.assertIsNotNone(result["started_at"])
        self.assertIsNotNone(result["finished_at"])

    def test_observation_timeseries_is_not_cleanup_target(self):
        self.db.add(
            InterestRate(
                series_key="DFF",
                date=self.now - timedelta(days=3650),
                value=5.0,
            )
        )
        self.db.add(
            NewsItem(
                source="finnhub",
                title="old processed news",
                collected_at=self.now - timedelta(days=200),
                sentiment_extracted=True,
            )
        )
        self.db.commit()

        run_cleanup(self.db, now=self.now, policy=self.policy)

        self.assertEqual(self.db.query(InterestRate).count(), 1)
        self.assertEqual(self.db.query(NewsItem).count(), 0)


if __name__ == "__main__":
    unittest.main()
