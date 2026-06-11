from __future__ import annotations

import os
import unittest
from datetime import datetime
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite://")

from app.collectors.communication_collector import _maybe_queue_communication_sentiment
from app.core.database import Base
from app.models import CommunicationEvent


class CommunicationSentimentQueueTests(unittest.TestCase):
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
            patch("app.collectors.communication_collector.settings.SENTIMENT_PIPELINE_ENABLED", True),
            patch("app.collectors.communication_collector.settings.OPENAI_API_KEY", "test-key"),
            patch("app.collectors.communication_collector.settings.FOMC_SENTIMENT_MIN_TEXT_LENGTH", 10),
            patch("app.collectors.communication_collector.settings.FOMC_SENTIMENT_PENDING_TTL_HOURS", 24),
        ]
        for patcher in self.settings_patchers:
            patcher.start()

    def tearDown(self) -> None:
        for patcher in reversed(self.settings_patchers):
            patcher.stop()
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_broker_failure_falls_back_to_sync_communication_sentiment(self) -> None:
        communication_event = CommunicationEvent(
            event_date=datetime(2026, 6, 20, 10, 0),
            source="Federal Reserve",
            title="Chair speech on inflation outlook",
            event_type="speech",
            url="https://example.com/speech",
            content_text="This is a sufficiently long communication body for sentiment extraction.",
        )
        self.db.add(communication_event)
        self.db.commit()

        def _sync_run(event_id: int, _text: str):
            event = self.db.query(CommunicationEvent).filter_by(id=event_id).one()
            event.sentiment_status = "success"
            event.sentiment_extracted_at = datetime(2026, 6, 20, 10, 5)
            self.db.commit()
            return {"signals": 1}

        with patch(
            "app.workers.sentiment_worker.extract_communication_event_sentiment.delay",
            side_effect=OSError("Connection refused"),
        ), patch(
            "app.workers.sentiment_worker.extract_communication_event_sentiment.run",
            side_effect=_sync_run,
        ) as run_task:
            queued = _maybe_queue_communication_sentiment(
                self.db,
                communication_event=communication_event,
                now=datetime(2026, 6, 20, 10, 1),
            )

        self.assertTrue(queued)
        run_task.assert_called_once()
        saved_event = self.db.query(CommunicationEvent).filter_by(id=communication_event.id).one()
        self.assertEqual(saved_event.sentiment_status, "success")
        self.assertIsNotNone(saved_event.sentiment_extracted_at)


if __name__ == "__main__":
    unittest.main()
