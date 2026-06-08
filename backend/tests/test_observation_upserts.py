from datetime import datetime
import os
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite://")

from app.collectors.fomc_collector import _upsert_fedwatch
from app.collectors.fx_collector import _upsert_rate
from app.core.database import Base
from app.core.upsert import upsert_rows
from app.models.indicators import ExchangeRate, FedWatch, InterestRate


class ObservationUpsertTests(unittest.TestCase):
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

    def test_interest_rate_upsert_keeps_single_row_per_series_and_date(self):
        observed_at = datetime(2026, 6, 8, 0, 0, 0)

        upsert_rows(
            self.db,
            InterestRate,
            [{"series_key": "DFF", "date": observed_at, "value": 4.25}],
            conflict_columns=["series_key", "date"],
            update_columns=["value"],
        )
        self.db.commit()

        upsert_rows(
            self.db,
            InterestRate,
            [{"series_key": "DFF", "date": observed_at, "value": 4.50}],
            conflict_columns=["series_key", "date"],
            update_columns=["value"],
        )
        self.db.commit()

        rows = self.db.query(InterestRate).filter(InterestRate.series_key == "DFF").all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].value, 4.50)

    def test_exchange_rate_upsert_normalizes_same_day_to_single_row(self):
        _upsert_rate(self.db, datetime(2026, 6, 8, 9, 0, 0), "USDKRW", 1375.0)
        self.db.commit()

        _upsert_rate(self.db, datetime(2026, 6, 8, 18, 30, 0), "USDKRW", 1380.5)
        self.db.commit()

        rows = self.db.query(ExchangeRate).filter(ExchangeRate.pair == "USDKRW").all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].date, datetime(2026, 6, 8, 0, 0, 0))
        self.assertEqual(rows[0].value, 1380.5)

    def test_fedwatch_upsert_uses_meeting_date_and_observation_date_key(self):
        meeting_a = datetime(2026, 7, 29, 0, 0, 0)
        meeting_b = datetime(2026, 9, 16, 0, 0, 0)
        observation_date = datetime(2026, 6, 8, 0, 0, 0)

        _upsert_fedwatch(self.db, observation_date, meeting_a, 0.1, 0.8, 0.1)
        self.db.commit()
        _upsert_fedwatch(self.db, observation_date, meeting_a, 0.2, 0.7, 0.1)
        self.db.commit()
        _upsert_fedwatch(self.db, observation_date, meeting_b, 0.3, 0.6, 0.1)
        self.db.commit()

        rows = self.db.query(FedWatch).order_by(FedWatch.meeting_date).all()
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].meeting_date, meeting_a)
        self.assertEqual(rows[0].prob_hike, 0.2)
        self.assertEqual(rows[1].meeting_date, meeting_b)


if __name__ == "__main__":
    unittest.main()
