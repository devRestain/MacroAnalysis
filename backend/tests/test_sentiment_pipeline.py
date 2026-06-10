from __future__ import annotations

import os
import unittest
from datetime import datetime
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite://")

from app.core.database import Base
from app.models import DivergenceEvent, Expectation, NewsItem, SentimentSignal
from app.workers import sentiment_worker


class SentimentPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(self.engine)
        self.db = self.SessionLocal()

        self.session_patcher = patch("app.workers.sentiment_worker.SessionLocal", self.SessionLocal)
        self.session_patcher.start()

        self.settings_patchers = [
            patch.object(sentiment_worker.settings, "SENTIMENT_MAX_NEWS_ITEMS_PER_RUN", 10),
            patch.object(sentiment_worker.settings, "SENTIMENT_LOOKBACK_DAYS", 7),
            patch.object(sentiment_worker.settings, "SENTIMENT_REPORTS_ENABLED", False),
            patch.object(sentiment_worker.settings, "OPENAI_API_KEY", "test-key"),
            patch.object(sentiment_worker.settings, "SENTIMENT_PIPELINE_ENABLED", True),
        ]
        for patcher in self.settings_patchers:
            patcher.start()

    def tearDown(self) -> None:
        for patcher in reversed(self.settings_patchers):
            patcher.stop()
        self.session_patcher.stop()
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_extract_daily_sentiments_skips_irrelevant_news_without_llm(self) -> None:
        self.db.add(
            NewsItem(
                source="Example",
                title="Company launches new product",
                summary="No macro content here.",
                category="general",
                published_at=datetime(2026, 6, 9, 9, 0),
            )
        )
        self.db.commit()

        with patch("app.workers.sentiment_worker._call_llm") as mocked_llm:
            result = sentiment_worker.extract_daily_sentiments.run(batch_date_iso="2026-06-09T00:00:00")

        self.assertEqual(result["processed"], 0)
        self.assertEqual(result["signals"], 0)
        self.assertEqual(result["auto_marked_irrelevant"], 1)
        mocked_llm.assert_not_called()

        saved = self.db.query(NewsItem).one()
        self.assertTrue(saved.sentiment_extracted)
        self.assertEqual(self.db.query(SentimentSignal).count(), 0)

    def test_replaying_same_batch_does_not_duplicate_signals_or_expectations(self) -> None:
        news = NewsItem(
            source="Example",
            title="Inflation cools as CPI slows",
            summary="Markets expect the Fed to become less hawkish.",
            category="macro",
            published_at=datetime(2026, 6, 9, 8, 0),
        )
        self.db.add(news)
        self.db.commit()

        llm_payload = """
        [
          {
            "news_index": 1,
            "actor": "market",
            "dimension": "inflation",
            "stance": "dovish",
            "stance_score": -0.6,
            "intensity": 0.8,
            "confidence": 0.9,
            "evidence": "Inflation slowed more than expected."
          }
        ]
        """

        with patch("app.workers.sentiment_worker._call_llm", return_value=llm_payload):
            sentiment_worker.extract_daily_sentiments.run(batch_date_iso="2026-06-09T00:00:00")

        news = self.db.query(NewsItem).one()
        news.sentiment_extracted = False
        self.db.commit()

        with patch("app.workers.sentiment_worker._call_llm", return_value=llm_payload):
            sentiment_worker.extract_daily_sentiments.run(batch_date_iso="2026-06-09T00:00:00")

        sentiment_worker.update_expectations.run(batch_date_iso="2026-06-09T00:00:00")
        sentiment_worker.update_expectations.run(batch_date_iso="2026-06-09T00:00:00")

        self.assertEqual(self.db.query(SentimentSignal).count(), 1)
        self.assertEqual(self.db.query(Expectation).count(), 1)

        saved = self.db.query(Expectation).one()
        self.assertEqual(saved.actor, "market")
        self.assertEqual(saved.dimension, "inflation")
        self.assertAlmostEqual(saved.raw_score, -0.6, places=4)

    def test_detect_divergence_is_idempotent_and_reports_stay_disabled(self) -> None:
        self.db.add(
            Expectation(
                date=datetime(2026, 6, 9, 0, 0),
                actor="market",
                dimension="rates",
                raw_score=0.9,
                consensus_score=0.1,
                consensus_strength=0.3,
                inertia_age_days=1.0,
                inertia_coefficient=0.0,
                inertia_reset=False,
                consensus_7d_ago=None,
                momentum_score=None,
            )
        )
        self.db.commit()

        sentiment_worker.detect_divergence.run(batch_date_iso="2026-06-09T00:00:00")
        sentiment_worker.detect_divergence.run(batch_date_iso="2026-06-09T00:00:00")

        events = self.db.query(DivergenceEvent).all()
        self.assertEqual(len(events), 1)
        self.assertFalse(events[0].report_generated)

        with patch("app.workers.sentiment_worker._call_llm") as mocked_llm:
            result = sentiment_worker.generate_divergence_report.run(events[0].id)

        self.assertEqual(result["reason"], "sentiment_reports_disabled")
        mocked_llm.assert_not_called()


if __name__ == "__main__":
    unittest.main()
