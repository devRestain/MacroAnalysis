from __future__ import annotations

import os
import unittest
from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite://")

from app.core.database import Base
from app.models.indicators import Indicator, Observation
from app.services.indicator_registry import upsert_indicator_observations
from app.services.observation_query_service import get_latest_observations, get_observation_history


class ObservationPipelineTests(unittest.TestCase):
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

    def test_upsert_indicator_observations_updates_same_day_value(self) -> None:
        upsert_indicator_observations(
            self.db,
            [
                {"series_key": "DGS10", "date": date(2026, 6, 10), "value": 4.41},
                {"series_key": "^GSPC", "date": date(2026, 6, 10), "value": 6123.45},
            ],
        )
        self.db.commit()

        upsert_indicator_observations(
            self.db,
            [
                {"series_key": "DGS10", "date": date(2026, 6, 10), "value": 4.55},
            ],
        )
        self.db.commit()

        self.assertEqual(self.db.query(Indicator).count(), 2)
        self.assertEqual(self.db.query(Observation).count(), 2)

        dgs10 = self.db.query(Indicator).filter(Indicator.code == "DGS10").one()
        saved = self.db.query(Observation).filter(Observation.indicator_id == dgs10.id).one()
        self.assertEqual(saved.value, 4.55)

        latest = get_latest_observations(self.db, ["DGS10", "^GSPC"])
        self.assertEqual(latest[0]["latest_value"], 4.55)
        self.assertEqual(latest[1]["latest_value"], 6123.45)

        history = get_observation_history(self.db, "DGS10")
        self.assertEqual(history["status"], "ok")
        self.assertEqual(len(history["data"]), 1)
        self.assertEqual(history["data"][0]["value"], 4.55)


if __name__ == "__main__":
    unittest.main()
