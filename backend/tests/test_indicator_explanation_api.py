import os
import unittest
from importlib.util import find_spec

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

FASTAPI_AVAILABLE = find_spec("fastapi") is not None

if FASTAPI_AVAILABLE:
    from fastapi.testclient import TestClient
    from app.core.database import Base, get_db
    from app.main import app
    from app.services.indicator_explanation_loader import load_indicator_explanations
    from app.services.indicator_explanation_seed_service import seed_indicator_explanations


@unittest.skipUnless(FASTAPI_AVAILABLE, "fastapi is not installed in the current test environment")
class IndicatorExplanationApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        cls.Session = sessionmaker(bind=cls.engine, autoflush=False, autocommit=False)
        Base.metadata.create_all(bind=cls.engine)

        with cls.Session() as db:
            seed_indicator_explanations(db, payload=load_indicator_explanations())

        def override_get_db():
            db = cls.Session()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=cls.engine)
        cls.engine.dispose()

    def test_list_endpoint_returns_items(self):
        response = self.client.get("/api/indicator-explanations")
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertEqual(payload["count"], 47)
        self.assertEqual(len(payload["indicator_explanations"]), 47)
        self.assertIn("workflow_status", payload["indicator_explanations"][0])
        self.assertIn("analysis_hints", payload["indicator_explanations"][0])

    def test_category_filter_applies(self):
        response = self.client.get("/api/indicator-explanations?category=rates")
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertGreater(payload["count"], 0)
        self.assertTrue(
            all(item["category"] == "rates" for item in payload["indicator_explanations"])
        )

    def test_detail_endpoint_returns_single_item(self):
        response = self.client.get("/api/indicator-explanations/DGS10")
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertEqual(payload["indicator_key"], "DGS10")
        self.assertIn("workflow_status", payload)
        self.assertIn("analysis_hints", payload)
        self.assertNotIn("sentiment", payload)
        self.assertNotIn("expectation", payload)
        self.assertNotIn("sentiment_score", payload)
        self.assertNotIn("expectation_score", payload)

    def test_missing_key_returns_404(self):
        response = self.client.get("/api/indicator-explanations/DOES_NOT_EXIST")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
