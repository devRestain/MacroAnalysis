from __future__ import annotations

import importlib.util
import os
import unittest
from datetime import datetime
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite://")

from app.collectors.calendar.rule_based_market_calendar import generate_monthly_opex, generate_triple_witching
from app.api.route_helpers import calendar_event_to_dict
from app.core.database import Base
from app.models import CommunicationEvent
from app.services.calendar_description_service import (
    get_calendar_event_description,
    get_related_indicator_keys,
    get_watch_items,
    get_why_it_matters,
    list_calendar_event_descriptions,
)
from app.services.calendar_collection_service import collect_calendar_events
from app.models.calendar import EconomicCalendarEvent
from app.services.communication_event_service import upsert_communication_event
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
        self.assertEqual(opex[0]["event_key"], "US_MONTHLY_OPEX")
        self.assertEqual(witching[0]["event_key"], "US_TRIPLE_WITCHING")

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

    def test_communication_event_supports_non_fomc_records(self) -> None:
        first = upsert_communication_event(
            self.db,
            {
                "event_date": datetime(2026, 6, 20, 10, 0),
                "source": "Federal Reserve",
                "title": "Chair speech on inflation outlook",
                "event_type": "speech",
                "url": "https://example.com/speech",
                "content_text": "Inflation progress continues, but policy remains restrictive.",
            },
        )
        second = upsert_communication_event(
            self.db,
            {
                "event_date": datetime(2026, 6, 20, 10, 0),
                "source": "Federal Reserve",
                "title": "Chair speech on inflation outlook",
                "event_type": "speech",
                "url": "https://example.com/speech-v2",
                "content_text": "Updated speech body.",
            },
        )
        self.db.commit()

        rows = self.db.query(CommunicationEvent).all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(first.id, second.id)
        self.assertEqual(rows[0].url, "https://example.com/speech-v2")

    def test_calendar_event_dict_exposes_new_fields_with_legacy_fallbacks(self) -> None:
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
                "importance": "high",
                "status": "scheduled",
                "related_indicator_key": "FEDFUNDS",
            },
        )
        self.db.commit()

        payload = calendar_event_to_dict(event, include_details=False)

        self.assertEqual(payload["display_name"], "FOMC Meeting")
        self.assertEqual(payload["short_name"], "FOMC Meeting")
        self.assertEqual(payload["event_datetime_utc"], datetime(2026, 6, 17, 14, 0))
        self.assertEqual(str(payload["event_date_local"]), "2026-06-17")
        self.assertEqual(payload["event_time_local"], "14:00")
        self.assertEqual(payload["date_precision"], "datetime_estimated")
        self.assertEqual(payload["related_indicator_keys"], ["FEDFUNDS"])

    def test_calendar_description_service_returns_static_metadata(self) -> None:
        description = get_calendar_event_description("US_CPI")

        self.assertEqual(description["event_key"], "US_CPI")
        self.assertEqual(description["display_name"], "미국 CPI")
        self.assertEqual(description["short_name"], "CPI")
        self.assertEqual(description["provider"], "fred")
        self.assertEqual(description["event_type"], "macro_release")
        self.assertEqual(description["default_time"], "08:30")
        self.assertEqual(description["timezone"], "America/New_York")
        self.assertIn("CPIAUCSL", description["related_indicators"])
        self.assertIn("S&P 500", description["watch_items"])

    def test_calendar_description_service_fallback_is_safe(self) -> None:
        description = get_calendar_event_description("UNKNOWN_EVENT")

        self.assertEqual(description["event_key"], "UNKNOWN_EVENT")
        self.assertFalse(description["enabled"])
        self.assertEqual(description["related_indicators"], [])
        self.assertEqual(description["watch_items"], [])
        self.assertIsNone(description["why_it_matters"])

    def test_calendar_description_service_lists_enabled_items(self) -> None:
        items = list_calendar_event_descriptions(enabled_only=True)

        self.assertEqual(len(items), 18)
        self.assertTrue(all(item["enabled"] for item in items))
        self.assertIn("CPILFESL", get_related_indicator_keys("US_CPI"))
        self.assertIn("FedWatch", get_watch_items("FOMC_MEETING"))
        self.assertIsNotNone(get_why_it_matters("US_GDP"))

    def test_calendar_collection_records_fred_failure_without_crashing(self) -> None:
        with patch(
            "app.services.calendar_collection_service.FredReleaseDateLoader.collect"
        ) as fred:
            fred.return_value = {
                "job_key": "calendar_fred",
                "status": "failed",
                "reason": "calendar_fred_error:HTTPStatusError",
                "fetched_count": 0,
                "inserted_count": 0,
                "updated_count": 0,
            }
            result = collect_calendar_events(self.db)

        self.assertEqual(result["status"], "success")
        self.assertIn("calendar_fred:calendar_fred_error:HTTPStatusError", result["reason"])

    def test_bls_calendar_module_is_removed(self) -> None:
        spec = importlib.util.find_spec("app.collectors.calendar.bls_calendar")
        self.assertIsNone(spec)


if __name__ == "__main__":
    unittest.main()
