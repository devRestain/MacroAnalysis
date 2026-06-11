from __future__ import annotations

import os
import unittest
from datetime import datetime
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite://")

from app.collectors.calendar_collector import CalendarDefinitionLoader, CalendarUpsertService, FredReleaseDateLoader
from app.core.database import Base
from app.models.calendar import EconomicCalendarEvent


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self):
        return self._payload


class _FakeHttpxClient:
    def __init__(self, payload):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def get(self, url, params=None):
        return _FakeResponse(self._payload)


class CalendarCollectorUnitTests(unittest.TestCase):
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

    def test_fred_release_loader_applies_static_time_map(self) -> None:
        definition_loader = CalendarDefinitionLoader()
        release_map = definition_loader.load_fred_release_map()
        upsert_service = CalendarUpsertService(self.db)
        payload = {
            "release_dates": [
                {
                    "release_id": 10,
                    "release_name": "Consumer Price Index",
                    "date": "2026-06-10",
                }
            ]
        }

        with patch("app.collectors.calendar_collector.settings.CALENDAR_FRED_ENABLED", True), patch(
            "app.collectors.calendar_collector.settings.FRED_API_KEY", "test-key"
        ), patch(
            "app.collectors.calendar_collector.httpx.Client",
            return_value=_FakeHttpxClient(payload),
        ):
            result = FredReleaseDateLoader(release_map).collect(self.db, upsert_service)
            self.db.commit()

        self.assertEqual(result["status"], "success")
        row = self.db.query(EconomicCalendarEvent).filter_by(event_key="US_CPI").one()
        self.assertEqual(row.display_name, "미국 CPI")
        self.assertEqual(row.event_time_local, "08:30")
        self.assertEqual(row.time_source, "static_time_map")
        self.assertEqual(row.time_confidence, "static_high")
        self.assertEqual(row.date_precision, "datetime_estimated")
        self.assertEqual(row.event_datetime_utc, datetime(2026, 6, 10, 12, 30))

    def test_fred_release_loader_uses_normalized_exact_matching(self) -> None:
        definition_loader = CalendarDefinitionLoader()
        release_map = definition_loader.load_fred_release_map()
        upsert_service = CalendarUpsertService(self.db)
        payload = {
            "release_dates": [
                {
                    "release_id": 11,
                    "release_name": "  Consumer   Price Index  ",
                    "date": "2026-06-10",
                }
            ]
        }

        with patch("app.collectors.calendar_collector.settings.CALENDAR_FRED_ENABLED", True), patch(
            "app.collectors.calendar_collector.settings.FRED_API_KEY", "test-key"
        ), patch(
            "app.collectors.calendar_collector.httpx.Client",
            return_value=_FakeHttpxClient(payload),
        ):
            result = FredReleaseDateLoader(release_map).collect(self.db, upsert_service)
            self.db.commit()

        self.assertEqual(result["inserted_count"], 1)
        self.assertEqual(
            self.db.query(EconomicCalendarEvent).filter_by(event_key="US_CPI").count(),
            1,
        )

    def test_fred_release_loader_ignores_non_allowlist_release(self) -> None:
        definition_loader = CalendarDefinitionLoader()
        release_map = definition_loader.load_fred_release_map()
        upsert_service = CalendarUpsertService(self.db)
        payload = {
            "release_dates": [
                {
                    "release_id": 99,
                    "release_name": "Some Untracked Release",
                    "date": "2026-06-10",
                }
            ]
        }

        with patch("app.collectors.calendar_collector.settings.CALENDAR_FRED_ENABLED", True), patch(
            "app.collectors.calendar_collector.settings.FRED_API_KEY", "test-key"
        ), patch(
            "app.collectors.calendar_collector.httpx.Client",
            return_value=_FakeHttpxClient(payload),
        ):
            result = FredReleaseDateLoader(release_map).collect(self.db, upsert_service)
            self.db.commit()

        self.assertEqual(result["fetched_count"], 1)
        self.assertEqual(result["inserted_count"], 0)
        self.assertEqual(self.db.query(EconomicCalendarEvent).count(), 0)


if __name__ == "__main__":
    unittest.main()
