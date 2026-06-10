from __future__ import annotations

import os
import unittest
from unittest.mock import patch

os.environ.setdefault("DATABASE_URL", "sqlite://")

try:
    from fastapi.testclient import TestClient

    from app.core.cache import clear_local_fallback_state
    from app.core.config import settings
    from app.main import app

    FASTAPI_AVAILABLE = True
except ModuleNotFoundError:
    FASTAPI_AVAILABLE = False


@unittest.skipUnless(FASTAPI_AVAILABLE, "fastapi test dependencies are not installed")
class ApiSecurityTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_local_fallback_state()

    def tearDown(self) -> None:
        clear_local_fallback_state()

    def test_ai_chat_requires_api_key_when_configured(self) -> None:
        with patch("app.main.init_db", return_value=None), patch.object(settings, "API_ACCESS_KEY", "secret-key"), patch.object(
            settings, "OPENAI_API_KEY", "openai-test-key"
        ):
            with TestClient(app) as client:
                response = client.post("/api/ai/chat", json={"message": "hello"})
        self.assertEqual(response.status_code, 401)

    def test_ai_chat_rate_limit_returns_429_after_limit(self) -> None:
        with patch("app.main.init_db", return_value=None), patch.object(settings, "API_ACCESS_KEY", ""), patch.object(
            settings, "OPENAI_API_KEY", "openai-test-key"
        ), patch.object(settings, "AI_ROUTE_RATE_LIMIT_MAX_REQUESTS", 1), patch.object(
            settings, "AI_ROUTE_RATE_LIMIT_WINDOW_SECONDS", 60
        ), patch(
            "app.api.routes.ai.chat_with_context",
            return_value="ok",
        ):
            with TestClient(app) as client:
                first = client.post("/api/ai/chat", json={"message": "hello"})
                second = client.post("/api/ai/chat", json={"message": "hello again"})

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)


if __name__ == "__main__":
    unittest.main()
