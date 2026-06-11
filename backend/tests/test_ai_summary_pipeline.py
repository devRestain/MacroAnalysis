from __future__ import annotations

import os
import unittest
from datetime import datetime, date
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite://")

from app.core.database import Base
from app.models import CommunicationEvent, Indicator, Observation
from app.services.ai_summary_service import ensure_ai_summary, get_latest_ai_summary


class AiSummaryPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(self.engine)
        self.db = self.SessionLocal()

        indicator = Indicator(
            code="DGS10",
            name="10Y Treasury Yield",
            country="US",
            category="rates",
            source="fred",
            frequency="daily",
            unit="%",
        )
        self.db.add(indicator)
        self.db.flush()
        self.db.add(Observation(indicator_id=indicator.id, date=date(2026, 6, 11), value=4.42))
        self.db.add(
            CommunicationEvent(
                event_date=datetime(2026, 6, 10, 9, 0),
                source="Federal Reserve",
                title="Powell speech on inflation",
                event_type="speech",
                url="https://example.com/speech",
                content_text="Inflation remains above target and policy should stay restrictive.",
            )
        )
        self.db.commit()

    def tearDown(self) -> None:
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_macro_summary_is_scoped_and_reused(self) -> None:
        with patch("app.services.ai_summary_service.settings.OPENAI_API_KEY", ""):
            first = ensure_ai_summary(self.db, summary_type="macro", days=7)
            second = ensure_ai_summary(self.db, summary_type="macro", days=7)

        self.assertEqual(first.id, second.id)
        self.assertEqual(first.summary_type, "macro")
        latest = get_latest_ai_summary(self.db, summary_type="macro", days=7)
        self.assertIsNotNone(latest)
        self.assertEqual(latest.id, first.id)

    def test_communication_summary_can_be_targeted(self) -> None:
        with patch("app.services.ai_summary_service.settings.OPENAI_API_KEY", ""):
            row = ensure_ai_summary(self.db, summary_type="communication", target_key="Powell", days=30, force=True)

        self.assertEqual(row.summary_type, "communication")
        self.assertEqual(row.target_key, "Powell")
        self.assertIn("Powell speech", row.body)


if __name__ == "__main__":
    unittest.main()
