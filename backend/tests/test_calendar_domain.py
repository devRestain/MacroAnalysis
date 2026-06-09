from __future__ import annotations

import os
import unittest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite://")

from app.collectors.calendar.rule_based_market_calendar import generate_monthly_opex, generate_triple_witching
from app.core.database import Base
from app.models.calendar import EconomicCalendarEvent
from app.services.calendar_query_service import get_next_fomc_meeting_date
from app.services.calendar_upsert import upsert_calendar_event, upsert_fomc_detail


class CalendarDomainTests(unittest.TestCase):
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

    def test_upsert_calendar_event_is_unique(self) -> None:
        first = upsert_calendar_event(
            self.db,
            {
                "event_date": datetime(2026, 6, 17, 14, 0),
                "event_end_date": datetime(2026, 6, 17, 14, 0),
                "event_time": "14:00",
                "timezone": "America/New_York",
                "event_key": "FOMC_MEETING",
                "event_type": "central_bank",
                "category": "fomc",
                "title": "FOMC Meeting",
                "country": "US",
                "source": "Federal Reserve",
                "source_url": None,
                "importance": "high",
                "status": "scheduled",
                "related_indicator_key": None,
                "related_asset": None,
                "metadata_json": {"has_sep": False},
            },
        )
        second = upsert_calendar_event(
            self.db,
            {
                "event_date": datetime(2026, 6, 17, 14, 0),
                "event_end_date": datetime(2026, 6, 17, 14, 0),
                "event_time": "14:00",
                "timezone": "America/New_York",
                "event_key": "FOMC_MEETING",
                "event_type": "central_bank",
                "category": "fomc",
                "title": "FOMC Rate Decision",
                "country": "US",
                "source": "Federal Reserve",
                "source_url": "https://www.federalreserve.gov/",
                "importance": "high",
                "status": "scheduled",
                "related_indicator_key": None,
                "related_asset": "rates",
                "metadata_json": {"has_sep": True},
            },
        )
        self.db.commit()

        rows = self.db.query(EconomicCalendarEvent).all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(first.id, second.id)
        self.assertEqual(rows[0].title, "FOMC Rate Decision")
        self.assertEqual(rows[0].metadata_json["has_sep"], True)

    def test_fomc_detail_upsert_persists_separate_result_data(self) -> None:
        event = upsert_calendar_event(
            self.db,
            {
                "event_date": datetime(2026, 6, 17, 14, 0),
                "event_end_date": datetime(2026, 6, 17, 14, 0),
                "event_time": "14:00",
                "timezone": "America/New_York",
                "event_key": "FOMC_MEETING",
                "event_type": "central_bank",
                "category": "fomc",
                "title": "FOMC Meeting",
                "country": "US",
                "source": "Federal Reserve",
                "source_url": "https://www.federalreserve.gov/",
                "importance": "high",
                "status": "scheduled",
                "related_indicator_key": None,
                "related_asset": "rates",
                "metadata_json": {"has_sep": True},
            },
        )
        upsert_fomc_detail(
            self.db,
            {
                "calendar_event_id": event.id,
                "meeting_start_date": datetime(2026, 6, 16, 0, 0),
                "meeting_end_date": datetime(2026, 6, 17, 14, 0),
                "decision_rate": 4.5,
                "target_rate_lower": 4.25,
                "target_rate_upper": 4.5,
                "change_bp": 0,
                "statement_url": "https://example.com/statement",
                "minutes_url": "https://example.com/minutes",
                "implementation_note_url": None,
                "press_conference_url": None,
                "projection_materials_url": None,
                "has_sep": True,
            },
        )
        self.db.commit()

        saved_event = self.db.query(EconomicCalendarEvent).filter_by(id=event.id).one()
        self.assertIsNotNone(saved_event.fomc_detail)
        self.assertEqual(saved_event.fomc_detail.decision_rate, 4.5)
        self.assertEqual(saved_event.fomc_detail.statement_url, "https://example.com/statement")

    def test_rule_based_calendar_and_next_fomc_query(self) -> None:
        opex = generate_monthly_opex(2026)
        witching = generate_triple_witching(2026)
        self.assertEqual(len(opex), 12)
        self.assertEqual(len(witching), 4)
        self.assertEqual(opex[0]["event_date"], datetime(2026, 1, 16, 0, 0))
        self.assertEqual(witching[1]["event_date"], datetime(2026, 6, 19, 0, 0))

        upsert_calendar_event(
            self.db,
            {
                "event_date": datetime(2026, 7, 29, 14, 0),
                "event_end_date": datetime(2026, 7, 29, 14, 0),
                "event_time": "14:00",
                "timezone": "America/New_York",
                "event_key": "FOMC_MEETING",
                "event_type": "central_bank",
                "category": "fomc",
                "title": "FOMC Meeting",
                "country": "US",
                "source": "Federal Reserve",
                "source_url": None,
                "importance": "high",
                "status": "scheduled",
                "related_indicator_key": None,
                "related_asset": None,
                "metadata_json": None,
            },
        )
        self.db.commit()
        next_meeting = get_next_fomc_meeting_date(self.db, now=datetime(2026, 6, 1, 0, 0))
        self.assertEqual(next_meeting, datetime(2026, 7, 29, 14, 0))


if __name__ == "__main__":
    unittest.main()
