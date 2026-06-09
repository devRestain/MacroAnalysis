import os
import unittest
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from sqlalchemy import create_engine

from app.core.database import Base
from app.models import IndicatorExplanation
from app.services.indicator_explanation_loader import (
    get_indicator_explanations_path,
    iter_indicator_explanation_items,
    load_indicator_explanations,
)


class IndicatorExplanationLoaderTests(unittest.TestCase):
    def test_resource_loads_from_backend_package(self):
        path = get_indicator_explanations_path()
        expected = Path(__file__).resolve().parents[1] / "app" / "data" / "indicator_explanations_v1_1_workflow_aware.json"
        self.assertTrue(path.exists())
        self.assertEqual(path, expected)

        payload = load_indicator_explanations()
        self.assertEqual(payload["schema_version"], "1.1.0")

    def test_workflow_metadata_and_top_level_lists_exist(self):
        payload = load_indicator_explanations()
        self.assertIn("workflow_metadata", payload)
        self.assertIn("timeseries_indicators", payload)
        self.assertIn("non_series_display_metrics", payload)
        self.assertIsInstance(payload["timeseries_indicators"], list)
        self.assertIsInstance(payload["non_series_display_metrics"], list)

    def test_all_items_have_keys_and_dynamic_counts_match(self):
        payload = load_indicator_explanations()
        items = iter_indicator_explanation_items(payload)
        self.assertTrue(items)
        self.assertTrue(all(item.get("key") for item in items))
        self.assertEqual(len(payload["timeseries_indicators"]), 41)
        self.assertEqual(len(payload["non_series_display_metrics"]), 0)
        self.assertEqual(len(items), 41)

    def test_indicator_explanation_model_is_initializable(self):
        self.assertEqual(IndicatorExplanation.__tablename__, "indicator_explanations")

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        self.assertIn("indicator_explanations", Base.metadata.tables)


if __name__ == "__main__":
    unittest.main()
