from datetime import date
import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")

from app.core.database import Base, get_db
from app.main import app
from app.models.indicators import Indicator, Observation
from app.services.observation_query_service import (
    get_latest_by_category,
    get_latest_observations,
)


async def _fake_cache_get(_key: str):
    return None


async def _fake_cache_set(_key: str, _value, ttl: int = 3600):
    return None


class ObservationQueryServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.Session = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        Base.metadata.create_all(self.engine)
        self.db = self.Session()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_latest_observation_returns_newest_value(self):
        indicator = self._add_indicator(code="DFF", name="Fed Funds", category="rates", unit="%")
        self._add_observation(indicator, date(2026, 6, 7), 4.25)
        self._add_observation(indicator, date(2026, 6, 8), 4.50)
        self.db.commit()

        rows = get_latest_observations(self.db, ["DFF"])

        self.assertEqual(rows[0]["latest_value"], 4.50)
        self.assertEqual(str(rows[0]["latest_date"]), "2026-06-08")
        self.assertEqual(rows[0]["status"], "ok")

    def test_series_without_observation_returns_missing_payload(self):
        self._add_indicator(code="DGS10", name="10Y Treasury", category="rates", unit="%")
        self.db.commit()

        rows = get_latest_observations(self.db, ["DGS10"])

        self.assertIsNone(rows[0]["latest_value"])
        self.assertEqual(rows[0]["status"], "missing")
        self.assertEqual(rows[0]["name"], "10Y Treasury")

    def test_unknown_series_returns_graceful_missing_payload(self):
        rows = get_latest_observations(self.db, ["UNKNOWN_SERIES"])

        self.assertEqual(rows[0]["series_key"], "UNKNOWN_SERIES")
        self.assertIsNone(rows[0]["value"])
        self.assertEqual(rows[0]["status"], "missing")

    def test_latest_by_category_returns_only_matching_series(self):
        rate_indicator = self._add_indicator(code="DFF", name="Fed Funds", category="rates", unit="%")
        macro_indicator = self._add_indicator(code="CPIAUCSL", name="CPI", category="macro", unit="idx")
        self._add_observation(rate_indicator, date(2026, 6, 8), 4.5)
        self._add_observation(macro_indicator, date(2026, 6, 8), 302.1)
        self.db.commit()

        rows = get_latest_by_category(self.db, "rates")

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["series_key"], "DFF")
        self.assertEqual(rows[0]["latest_value"], 4.5)

    def _add_indicator(
        self,
        *,
        code: str,
        name: str,
        category: str,
        unit: str,
        frequency: str = "daily",
        source: str = "fred",
    ) -> Indicator:
        indicator = Indicator(
            code=code,
            name=name,
            description=f"{name} description",
            country="US",
            category=category,
            source=source,
            frequency=frequency,
            unit=unit,
        )
        self.db.add(indicator)
        self.db.flush()
        return indicator

    def _add_observation(self, indicator: Indicator, observed_at: date, value: float):
        self.db.add(
            Observation(
                indicator_id=indicator.id,
                date=observed_at,
                value=value,
            )
        )


class ObservationApiTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.Session = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        Base.metadata.create_all(self.engine)
        self.db = self.Session()

        self.cache_get_patcher = patch("app.api.routes.cache_get", new=_fake_cache_get)
        self.cache_set_patcher = patch("app.api.routes.cache_set", new=_fake_cache_set)
        self.cache_get_patcher.start()
        self.cache_set_patcher.start()

        def override_get_db():
            try:
                yield self.db
            finally:
                pass

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()
        self.cache_get_patcher.stop()
        self.cache_set_patcher.stop()
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_dashboard_summary_returns_200_with_observations_only(self):
        spx = self._add_indicator(code="^GSPC", name="S&P 500", category="equity", unit="idx", source="yfinance")
        dgs10 = self._add_indicator(code="DGS10", name="10Y Treasury", category="rates", unit="%", source="fred")
        self._add_observation(spx, date(2026, 6, 8), 5300.0)
        self._add_observation(spx, date(2026, 6, 7), 5250.0)
        self._add_observation(dgs10, date(2026, 6, 8), 4.32)
        self.db.commit()

        response = self.client.get("/api/summary")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["equities"]["^GSPC"]["close"], 5300.0)
        self.assertEqual(body["yield_curve"]["DGS10"], 4.32)

    def test_dashboard_summary_handles_series_without_observations(self):
        self._add_indicator(code="^IXIC", name="NASDAQ", category="equity", unit="idx", source="yfinance")
        self.db.commit()

        response = self.client.get("/api/summary")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["equities"], {})
        self.assertEqual(body["yield_curve"], {})

    def test_history_api_returns_observation_series(self):
        indicator = self._add_indicator(code="USDKRW", name="USD/KRW", category="fx", unit="KRW", source="fx")
        self._add_observation(indicator, date(2026, 6, 7), 1370.0)
        self._add_observation(indicator, date(2026, 6, 8), 1381.5)
        self.db.commit()

        response = self.client.get("/api/indicators/history/USDKRW?period=1y")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["indicator_key"], "USDKRW")
        self.assertEqual(len(body["data"]), 2)
        self.assertEqual(body["data"][-1]["value"], 1381.5)

    def _add_indicator(
        self,
        *,
        code: str,
        name: str,
        category: str,
        unit: str,
        frequency: str = "daily",
        source: str = "fred",
    ) -> Indicator:
        indicator = Indicator(
            code=code,
            name=name,
            description=f"{name} description",
            country="US",
            category=category,
            source=source,
            frequency=frequency,
            unit=unit,
        )
        self.db.add(indicator)
        self.db.flush()
        return indicator

    def _add_observation(self, indicator: Indicator, observed_at: date, value: float):
        self.db.add(
            Observation(
                indicator_id=indicator.id,
                date=observed_at,
                value=value,
            )
        )


if __name__ == "__main__":
    unittest.main()
