import os
import unittest

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models import IndicatorExplanation
from app.services.indicator_explanation_loader import load_indicator_explanations
from app.services.indicator_explanation_seed_service import seed_indicator_explanations


class IndicatorExplanationSeedServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
        Base.metadata.create_all(bind=self.engine)

    def tearDown(self):
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def test_seed_persists_all_items(self):
        payload = load_indicator_explanations()
        with self.Session() as db:
            result = seed_indicator_explanations(db, payload=payload)

            row_count = db.query(IndicatorExplanation).count()
            self.assertEqual(result["inserted_count"], 47)
            self.assertEqual(result["updated_count"], 0)
            self.assertEqual(result["skipped_count"], 0)
            self.assertEqual(result["total_processed_count"], 47)
            self.assertEqual(row_count, 47)

            timeseries_count = db.query(IndicatorExplanation).filter(
                IndicatorExplanation.category != "fomc",
                IndicatorExplanation.category != "fedwatch",
            ).count()
            non_series_count = db.query(IndicatorExplanation).filter(
                IndicatorExplanation.category.in_(["fomc", "fedwatch"])
            ).count()
            self.assertEqual(timeseries_count, 41)
            self.assertEqual(non_series_count, 6)

    def test_seed_is_idempotent_and_preserves_static_fields(self):
        payload = load_indicator_explanations()
        with self.Session() as db:
            first = seed_indicator_explanations(db, payload=payload)
            second = seed_indicator_explanations(db, payload=payload)

            self.assertEqual(first["inserted_count"], 47)
            self.assertEqual(second["inserted_count"], 0)
            self.assertEqual(second["updated_count"], 0)
            self.assertEqual(second["skipped_count"], 47)
            self.assertEqual(db.query(IndicatorExplanation).count(), 47)

            dgs10 = db.query(IndicatorExplanation).filter_by(indicator_key="DGS10").first()
            vix = db.query(IndicatorExplanation).filter_by(indicator_key="^VIX").first()
            fedwatch_cut = db.query(IndicatorExplanation).filter_by(indicator_key="fedwatch_prob_cut").first()

            self.assertIsNotNone(dgs10)
            self.assertIsNotNone(vix)
            self.assertIsNotNone(fedwatch_cut)
            self.assertEqual(fedwatch_cut.workflow_status["is_runtime_signal"], False)
            self.assertIn("sentiment_mapping", fedwatch_cut.analysis_hints)
            self.assertIn("expectation_role", fedwatch_cut.analysis_hints)
            self.assertNotIn("sentiment_score", fedwatch_cut.analysis_hints)
            self.assertNotIn("expectation_value", fedwatch_cut.analysis_hints)


if __name__ == "__main__":
    unittest.main()
