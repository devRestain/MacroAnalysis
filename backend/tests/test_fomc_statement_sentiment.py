from __future__ import annotations

import os
import unittest
from datetime import datetime
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite://")

from app.collectors.fomc_collector import _maybe_queue_fomc_statement_sentiment
from app.core.database import Base
from app.models.calendar import EconomicCalendarEvent, FomcEventDetail
from app.models.indicators import FomcEvent, SentimentSignal


class FomcStatementSentimentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(self.engine)
        self.db = self.SessionLocal()

        self.settings_patchers = [
            patch("app.collectors.fomc_collector.settings.SENTIMENT_PIPELINE_ENABLED", True),
            patch("app.collectors.fomc_collector.settings.FOMC_SENTIMENT_ENABLED", True),
            patch("app.collectors.fomc_collector.settings.OPENAI_API_KEY", "test-key"),
            patch("app.collectors.fomc_collector.settings.FOMC_SENTIMENT_LOOKBACK_DAYS", 30),
            patch("app.collectors.fomc_collector.settings.FOMC_SENTIMENT_MIN_TEXT_LENGTH", 10),
        ]
        for patcher in self.settings_patchers:
            patcher.start()

    def tearDown(self) -> None:
        for patcher in reversed(self.settings_patchers):
            patcher.stop()
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_recent_released_statement_is_queued_once(self) -> None:
        fomc_event = FomcEvent(meeting_date=datetime(2026, 6, 18, 14, 0))
        calendar_event = EconomicCalendarEvent(
            event_date=datetime(2026, 6, 18, 14, 0),
            event_end_date=datetime(2026, 6, 18, 14, 0),
            event_time="14:00",
            timezone="America/New_York",
            event_key="FOMC_MEETING",
            event_type="central_bank",
            category="fomc",
            title="FOMC Meeting",
            country="US",
            source="Federal Reserve",
            importance="high",
            status="released",
        )
        self.db.add_all([fomc_event, calendar_event])
        self.db.commit()
        self.db.add(
            FomcEventDetail(
                calendar_event_id=calendar_event.id,
                meeting_start_date=datetime(2026, 6, 17, 0, 0),
                meeting_end_date=datetime(2026, 6, 18, 14, 0),
                statement_url="https://example.com/statement",
                has_sep=False,
            )
        )
        self.db.commit()

        with patch(
            "app.collectors.fomc_collector._fetch_fomc_statement_text",
            return_value="Federal Reserve statement text long enough.",
        ) as fetch_text, patch(
            "app.collectors.fomc_collector._enqueue_fomc_sentiment_task"
        ) as enqueue_task:
            queued = _maybe_queue_fomc_statement_sentiment(
                self.db,
                fomc_event_id=fomc_event.id,
                calendar_event_id=calendar_event.id,
                meeting_end_dt=datetime(2026, 6, 18, 14, 0),
                statement_url="https://example.com/statement",
                now=datetime(2026, 6, 19, 9, 0),
            )

        self.assertTrue(queued)
        fetch_text.assert_called_once()
        enqueue_task.assert_called_once_with(
            fomc_event_id=fomc_event.id,
            text="Federal Reserve statement text long enough.",
        )
        detail = self.db.query(FomcEventDetail).filter_by(calendar_event_id=calendar_event.id).one()
        self.assertEqual(detail.sentiment_status, "pending")

    def test_existing_fomc_signal_prevents_requeue(self) -> None:
        fomc_event = FomcEvent(meeting_date=datetime(2026, 6, 18, 14, 0))
        calendar_event = EconomicCalendarEvent(
            event_date=datetime(2026, 6, 18, 14, 0),
            event_end_date=datetime(2026, 6, 18, 14, 0),
            event_time="14:00",
            timezone="America/New_York",
            event_key="FOMC_MEETING",
            event_type="central_bank",
            category="fomc",
            title="FOMC Meeting",
            country="US",
            source="Federal Reserve",
            importance="high",
            status="released",
        )
        self.db.add_all([fomc_event, calendar_event])
        self.db.commit()
        self.db.add(
            FomcEventDetail(
                calendar_event_id=calendar_event.id,
                meeting_start_date=datetime(2026, 6, 17, 0, 0),
                meeting_end_date=datetime(2026, 6, 18, 14, 0),
                statement_url="https://example.com/statement",
                has_sep=False,
                sentiment_status="success",
            )
        )
        self.db.commit()
        self.db.add(
            SentimentSignal(
                source_type="fomc",
                source_id=fomc_event.id,
                batch_date=datetime(2026, 6, 19, 0, 0),
                actor="fed",
                dimension="rates",
                stance="hawkish",
                stance_score=0.4,
                intensity=0.7,
                confidence=0.8,
                evidence="Policy stance remained restrictive.",
            )
        )
        self.db.commit()

        with patch("app.collectors.fomc_collector._fetch_fomc_statement_text") as fetch_text, patch(
            "app.collectors.fomc_collector._enqueue_fomc_sentiment_task"
        ) as enqueue_task:
            queued = _maybe_queue_fomc_statement_sentiment(
                self.db,
                fomc_event_id=fomc_event.id,
                calendar_event_id=calendar_event.id,
                meeting_end_dt=datetime(2026, 6, 18, 14, 0),
                statement_url="https://example.com/statement",
                now=datetime(2026, 6, 19, 9, 0),
            )

        self.assertFalse(queued)
        fetch_text.assert_not_called()
        enqueue_task.assert_not_called()


if __name__ == "__main__":
    unittest.main()
