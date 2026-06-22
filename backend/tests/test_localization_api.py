from __future__ import annotations

import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("DATABASE_URL", "sqlite://")

try:
    from datetime import date, datetime, timedelta

    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from app.core.cache import clear_local_fallback_state
    from app.core.database import Base, get_db
    from app.main import app
    from app.models import ChangeSnapshot, Indicator, Observation
    from app.services.calendar_upsert import upsert_calendar_event
    from app.services.localization import localized_indicator_fields

    FASTAPI_AVAILABLE = True
except ModuleNotFoundError:
    FASTAPI_AVAILABLE = False


@unittest.skipUnless(FASTAPI_AVAILABLE, "fastapi test dependencies are not installed")
class LocalizationApiTests(unittest.TestCase):
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

    def test_summary_lang_overlays_snapshot_label_from_static_metadata(self) -> None:
        snapshot_date = datetime.now().replace(microsecond=0, second=0, minute=0) - timedelta(hours=1)
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
        self.db.add(Observation(indicator_id=indicator.id, date=snapshot_date.date(), value=4.42))
        self.db.add(
            ChangeSnapshot(
                snapshot_date=snapshot_date,
                indicator_key="DGS10",
                label="10Y Treasury Yield",
                category="rates",
                current_value=4.42,
                unit="%",
                signal="yellow",
            )
        )
        self.db.commit()

        expected_label = localized_indicator_fields("DGS10", locale="ko").get("display_name")

        with patch("app.main.init_db", return_value=None):
            with TestClient(app) as client:
                response = client.get("/api/summary?lang=ko")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["snapshots"]["DGS10"]["label"], expected_label)
        self.assertEqual(payload["snapshots"]["DGS10"]["signal_label"], "주의")

    def test_calendar_events_lang_adds_label_fields(self) -> None:
        event_date = datetime.now().replace(microsecond=0, second=0, minute=0) + timedelta(days=3)
        upsert_calendar_event(
            self.db,
            {
                "event_date": event_date,
                "event_end_date": event_date,
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
                "watch_items": ["FedWatch"],
            },
        )
        self.db.commit()

        with patch("app.main.init_db", return_value=None):
            with TestClient(app) as client:
                response = client.get("/api/calendar/events?days=30&lang=en")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["count"], 1)
        event = payload["events"][0]
        self.assertEqual(event["importance_label"], "high")
        self.assertEqual(event["status_label"], "scheduled")
        self.assertEqual(event["category_label"], "Inflation")
        self.assertEqual(event["source_label"], "FRED")

    def test_indicator_explanations_fall_back_to_static_metadata_when_db_is_empty(self) -> None:
        with patch("app.main.init_db", return_value=None):
            with TestClient(app) as client:
                response = client.get("/api/indicator-explanations?lang=ko")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertGreater(payload["count"], 0)
        keys = {item["indicator_key"] for item in payload["indicator_explanations"]}
        self.assertIn("DGS10", keys)


class StaticMetadataArtifactTests(unittest.TestCase):
    def test_translation_request_artifact_has_expected_missing_counts(self) -> None:
        artifact_path = Path(__file__).resolve().parent.parent / "app" / "data" / "static_metadata_translation_request.json"
        payload = json.loads(artifact_path.read_text(encoding="utf-8"))
        collections = {item["entity"]: item for item in payload["collections"]}

        indicator_explanations = collections["indicator_explanations"]["items"]
        calendar_items = collections["calendar_event_definitions"]["items"]

        self.assertEqual(len(indicator_explanations), 47)
        self.assertEqual(sum(1 for item in indicator_explanations if item["current_status"] == "missing"), 47)
        self.assertEqual(
            sorted(item["key"] for item in calendar_items if item["current_status"] == "missing"),
            ["US_MONTHLY_OPEX", "US_TRIPLE_WITCHING"],
        )


if __name__ == "__main__":
    unittest.main()
