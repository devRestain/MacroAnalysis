from __future__ import annotations

import os
import sys
import types
import unittest
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite://")

from app.collectors.news_collector import build_news_url_hash, collect_fed_rss
from app.core.database import Base
from app.models import NewsItem


class NewsDeduplicationTests(unittest.TestCase):
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

    def test_collect_fed_rss_skips_existing_url_hash(self) -> None:
        published_at = datetime(2026, 6, 10, 9, 0, 0)
        existing_hash = build_news_url_hash(
            source="Federal Reserve",
            title="Rates unchanged",
            url="https://www.federalreserve.gov/newsevents/pressreleases/monetary20260610a.htm?utm_source=test",
            published_at=published_at,
        )
        self.db.add(
            NewsItem(
                source="Federal Reserve",
                title="Rates unchanged",
                summary="existing",
                url="https://www.federalreserve.gov/newsevents/pressreleases/monetary20260610a.htm",
                url_hash=existing_hash,
                category="fed",
                published_at=published_at,
            )
        )
        self.db.commit()

        fake_feedparser = types.SimpleNamespace(
            parse=lambda _: types.SimpleNamespace(
                entries=[
                    {
                        "link": "https://www.federalreserve.gov/newsevents/pressreleases/monetary20260610a.htm?utm_source=test",
                        "title": "Rates unchanged",
                        "summary": "duplicate",
                        "published_parsed": published_at.timetuple(),
                    }
                ]
            )
        )

        with unittest.mock.patch.dict(sys.modules, {"feedparser": fake_feedparser}):
            result = collect_fed_rss(self.db)

        self.assertEqual(result["fetched_count"], 1)
        self.assertEqual(result["inserted_count"], 0)
        self.assertEqual(self.db.query(NewsItem).count(), 1)


if __name__ == "__main__":
    unittest.main()
