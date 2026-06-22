from __future__ import annotations

import os
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite://")

try:
    from fastapi.testclient import TestClient

    from app.core.cache import clear_local_fallback_state
    from app.core.database import Base, get_db
    from app.main import app
    from app.services.calendar_upsert import upsert_calendar_event, upsert_fomc_detail

    FASTAPI_AVAILABLE = True
except ModuleNotFoundError:
    FASTAPI_AVAILABLE = False


@unittest.skipUnless(FASTAPI_AVAILABLE, "fastapi test dependencies are not installed")
class CalendarApiTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_local_fallback_state()
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(self.engine)
        self.db = self.SessionLocal()

        def override_get_db():
            try:
                yield self.db
            finally:
                pass

        app.dependency_overrides[get_db] = override_get_db

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()
        clear_local_fallback_state()

    def test_calendar_events_returns_empty_list_safely(self) -> None:
        with patch("app.main.init_db", return_value=None):
            with TestClient(app) as client:
                response = client.get("/api/calendar/events?days=30")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["events"], [])
        self.assertEqual(payload["count"], 0)

    def test_calendar_events_range_includes_description_fields(self) -> None:
        upsert_calendar_event(
            self.db,
            {
                "event_date": datetime(2026, 6, 10, 8, 30),
                "event_end_date": datetime(2026, 6, 10, 8, 30),
                "event_time": "08:30",
                "timezone": "America/New_York",
                "event_datetime_utc": datetime(2026, 6, 10, 12, 30),
                "event_date_local": datetime(2026, 6, 10).date(),
                "event_time_local": "08:30",
                "event_key": "US_CPI",
                "event_type": "macro_release",
                "category": "inflation",
                "title": "미국 CPI",
                "display_name": "미국 CPI",
                "short_name": "CPI",
                "country": "US",
                "source": "fred",
                "importance": "high",
                "status": "scheduled",
                "date_precision": "datetime_estimated",
                "time_source": "static_time_map",
                "time_confidence": "static_high",
                "related_indicator_key": "CPIAUCSL",
                "related_indicator_keys": ["CPIAUCSL", "CPILFESL"],
                "beginner_description": "소비자가 실제로 구매하는 상품과 서비스 가격의 변화를 보여주는 대표 물가 지표입니다.",
                "why_it_matters": "물가 압력이 높으면 금리 인하 기대가 약해지고 주식시장에는 부담이 될 수 있습니다.",
                "watch_items": ["2Y Treasury Yield", "DXY", "S&P 500", "FedWatch"],
            },
        )
        self.db.commit()

        with patch("app.main.init_db", return_value=None):
            with TestClient(app) as client:
                response = client.get("/api/calendar/events?from=2026-06-01&to=2026-06-30")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["count"], 1)
        event = payload["events"][0]
        self.assertEqual(event["event_key"], "US_CPI")
        self.assertEqual(event["display_name"], "미국 CPI")
        self.assertEqual(event["short_name"], "CPI")
        self.assertEqual(event["display_time"], "08:30 ET")
        self.assertEqual(event["date_precision"], "datetime_estimated")
        self.assertEqual(event["time_source"], "static_time_map")
        self.assertEqual(event["time_confidence"], "static_high")
        self.assertIn("CPIAUCSL", event["related_indicator_keys"])
        self.assertIn("FedWatch", event["watch_items"])
        self.assertIsNotNone(event["beginner_description"])
        self.assertIsNotNone(event["why_it_matters"])

    def test_calendar_event_detail_endpoint_returns_single_event(self) -> None:
        event = upsert_calendar_event(
            self.db,
            {
                "event_date": datetime(2026, 6, 10, 8, 30),
                "event_end_date": datetime(2026, 6, 10, 8, 30),
                "event_time": "08:30",
                "timezone": "America/New_York",
                "event_key": "US_CPI",
                "event_type": "macro_release",
                "category": "inflation",
                "title": "미국 CPI",
                "display_name": "미국 CPI",
                "short_name": "CPI",
                "country": "US",
                "source": "fred",
                "importance": "high",
                "status": "scheduled",
                "beginner_description": "설명",
                "why_it_matters": "의미",
                "watch_items": ["DXY"],
            },
        )
        self.db.commit()

        with patch("app.main.init_db", return_value=None):
            with TestClient(app) as client:
                response = client.get(f"/api/calendar/events/{event.id}")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["id"], event.id)
        self.assertEqual(payload["event_key"], "US_CPI")
        self.assertEqual(payload["display_name"], "미국 CPI")

    def test_calendar_event_detail_returns_404_for_missing_event(self) -> None:
        with patch("app.main.init_db", return_value=None):
            with TestClient(app) as client:
                response = client.get("/api/calendar/events/99999")

        self.assertEqual(response.status_code, 404)

    def test_calendar_events_include_fomc_details_when_requested(self) -> None:
        meeting_end = datetime.now().replace(microsecond=0, second=0, minute=0) + timedelta(days=7)
        meeting_start = meeting_end - timedelta(days=1, hours=14)
        event = upsert_calendar_event(
            self.db,
            {
                "event_date": meeting_end,
                "event_end_date": meeting_end,
                "event_time": "14:00",
                "timezone": "America/New_York",
                "event_key": "FOMC_MEETING",
                "event_type": "central_bank",
                "category": "fed",
                "title": "FOMC 금리결정",
                "display_name": "FOMC 금리결정",
                "short_name": "FOMC",
                "country": "US",
                "source": "Federal Reserve",
                "importance": "critical",
                "status": "scheduled",
                "beginner_description": "연준 회의",
                "why_it_matters": "시장 영향이 큼",
                "watch_items": ["FedWatch"],
            },
        )
        upsert_fomc_detail(
            self.db,
            {
                "calendar_event_id": event.id,
                "meeting_start_date": meeting_start,
                "meeting_end_date": meeting_end,
                "decision_rate": 4.5,
                "target_rate_lower": 4.25,
                "target_rate_upper": 4.5,
                "change_bp": 0,
                "statement_url": "https://example.com/statement",
                "minutes_url": "https://example.com/minutes",
                "has_sep": True,
            },
        )
        self.db.commit()

        from_date = (meeting_end - timedelta(days=1)).date().isoformat()
        to_date = (meeting_end + timedelta(days=1)).date().isoformat()
        with patch("app.main.init_db", return_value=None):
            with TestClient(app) as client:
                response = client.get(f"/api/calendar/events?from={from_date}&to={to_date}&include_details=true")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["count"], 1)
        details = payload["events"][0]["details"]
        self.assertIsNotNone(details)
        self.assertEqual(details["fomc"]["decision_rate"], 4.5)
        self.assertEqual(details["fomc"]["statement_url"], "https://example.com/statement")

    def test_fomc_endpoint_returns_enriched_calendar_meetings(self) -> None:
        meeting_end = datetime.now().replace(microsecond=0, second=0, minute=0) + timedelta(days=7)
        meeting_start = meeting_end - timedelta(days=1, hours=14)
        event = upsert_calendar_event(
            self.db,
            {
                "event_date": meeting_end,
                "event_end_date": meeting_end,
                "event_time": "14:00",
                "timezone": "America/New_York",
                "event_key": "FOMC_MEETING",
                "event_type": "central_bank",
                "category": "fed",
                "title": "FOMC 금리결정",
                "display_name": "FOMC 금리결정",
                "short_name": "FOMC",
                "country": "US",
                "source": "Federal Reserve",
                "importance": "critical",
                "status": "scheduled",
            },
        )
        upsert_fomc_detail(
            self.db,
            {
                "calendar_event_id": event.id,
                "meeting_start_date": meeting_start,
                "meeting_end_date": meeting_end,
                "decision_rate": 4.5,
                "change_bp": 0,
                "statement_url": "https://example.com/statement",
                "minutes_url": "https://example.com/minutes",
                "has_sep": True,
            },
        )
        self.db.commit()

        with patch("app.main.init_db", return_value=None):
            with TestClient(app) as client:
                response = client.get("/api/fomc")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload["meetings"]), 1)
        meeting = payload["meetings"][0]
        self.assertEqual(meeting["id"], event.id)
        self.assertEqual(meeting["display_name"], "FOMC 금리결정")
        self.assertEqual(meeting["event_time_local"], "14:00")
        self.assertEqual(meeting["rate"], 4.5)
        self.assertIsNotNone(meeting["details"])

    def test_fomc_endpoint_returns_safely_when_fedwatch_table_is_missing(self) -> None:
        event = upsert_calendar_event(
            self.db,
            {
                "event_date": datetime(2026, 6, 17, 14, 0),
                "event_end_date": datetime(2026, 6, 17, 14, 0),
                "event_time": "14:00",
                "timezone": "America/New_York",
                "event_key": "FOMC_MEETING",
                "event_type": "central_bank",
                "category": "fed",
                "title": "FOMC 금리결정",
                "display_name": "FOMC 금리결정",
                "short_name": "FOMC",
                "country": "US",
                "source": "Federal Reserve",
                "importance": "critical",
                "status": "scheduled",
            },
        )
        self.db.commit()
        self.db.execute(text("DROP TABLE fed_watch"))
        self.db.commit()

        with patch("app.main.init_db", return_value=None):
            with TestClient(app) as client:
                response = client.get("/api/fomc")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload["meetings"]), 1)
        self.assertIsNone(payload["fedwatch"])
        self.assertEqual(payload["meetings"][0]["id"], event.id)


if __name__ == "__main__":
    unittest.main()
