from __future__ import annotations

import os
import unittest
from datetime import date, datetime, timedelta
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite://")

try:
    from fastapi.testclient import TestClient

    from app.core.cache import cache_delete_pattern_sync, clear_local_fallback_state
    from app.core.database import Base, get_db
    from app.main import app
    from app.models import ChangeSnapshot, Indicator, Observation

    FASTAPI_AVAILABLE = True
except ModuleNotFoundError:
    FASTAPI_AVAILABLE = False


@unittest.skipUnless(FASTAPI_AVAILABLE, "fastapi test dependencies are not installed")
class SummaryApiRegressionTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_local_fallback_state()
        cache_delete_pattern_sync("summary:v*")
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
        cache_delete_pattern_sync("summary:v*")
        clear_local_fallback_state()

    def test_summary_api_keeps_expected_top_level_shape(self) -> None:
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
            ChangeSnapshot(
                snapshot_date=datetime(2026, 6, 11, 9, 0),
                indicator_key="DGS10",
                label="10Y Treasury Yield",
                category="rates",
                current_value=4.42,
                unit="%",
                signal="yellow",
            )
        )
        self.db.commit()

        with patch("app.main.init_db", return_value=None):
            with TestClient(app) as client:
                response = client.get("/api/summary")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(
            set(payload.keys()),
            {
                "updated_at",
                "alerts",
                "snapshots",
                "equities",
                "yield_curve",
                "fomc",
                "ai_headline",
                "ai_as_of_date",
                "news_preview",
            },
        )
        self.assertIsInstance(payload["alerts"], list)
        self.assertIsInstance(payload["snapshots"], dict)
        self.assertIsInstance(payload["equities"], dict)
        self.assertIsInstance(payload["yield_curve"], dict)
        self.assertIsInstance(payload["fomc"], dict)
        self.assertIn("next_date", payload["fomc"])
        self.assertIn("prob_hold", payload["fomc"])

    def test_summary_api_falls_back_to_latest_stale_snapshots(self) -> None:
        snapshot_date = datetime.now().replace(microsecond=0, second=0, minute=0) - timedelta(days=5)
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

        with patch("app.main.init_db", return_value=None):
            with TestClient(app) as client:
                response = client.get("/api/summary")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("DGS10", payload["snapshots"])
        self.assertEqual(payload["updated_at"], snapshot_date.isoformat())


if __name__ == "__main__":
    unittest.main()
