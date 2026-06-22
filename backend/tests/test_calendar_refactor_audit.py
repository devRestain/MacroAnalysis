from __future__ import annotations

import importlib.util
import os
import unittest
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite://")

from app.collectors.calendar.rule_based_market_calendar import (
    generate_monthly_opex,
    generate_triple_witching,
)
from app.core.config import settings
from app.models.calendar import EconomicCalendarEvent, FomcEventDetail
from app.services import calendar_collection_service
from app.services.calendar_description_service import (
    get_calendar_event_definitions_path,
    get_calendar_event_description,
    list_calendar_event_descriptions,
    load_calendar_event_definitions,
)


class CalendarRefactorAuditTests(unittest.TestCase):
    def test_goal_2_calendar_allowlist_definition_has_18_events(self) -> None:
        payload = load_calendar_event_definitions()

        self.assertEqual(payload["schema_version"], "1.0.0")
        self.assertEqual(len(payload["calendar_events"]), 18)
        self.assertEqual(len(list_calendar_event_descriptions(enabled_only=True)), 18)

        expected_keys = {
            "US_CPI",
            "US_PPI",
            "US_PCE",
            "US_EMPLOYMENT_SITUATION",
            "US_JOBLESS_CLAIMS",
            "US_JOLTS",
            "US_GDP",
            "US_RETAIL_SALES",
            "US_DURABLE_GOODS",
            "US_HOUSING_STARTS",
            "US_NEW_HOME_SALES",
            "US_ISM_MANUFACTURING",
            "US_ISM_SERVICES",
            "FOMC_MEETING",
            "FOMC_MINUTES",
            "US_MONTHLY_OPEX",
            "US_TRIPLE_WITCHING",
            "US_CONSUMER_SENTIMENT",
        }
        self.assertEqual(
            {item["key"] for item in payload["calendar_events"]},
            expected_keys,
        )

    def test_goal_2_calendar_definition_uses_indicator_like_metadata_shape(self) -> None:
        payload = load_calendar_event_definitions()
        first = payload["calendar_events"][0]

        for top_level_key in (
            "schema_version",
            "purpose",
            "language",
            "tone_guidelines",
            "field_definitions",
            "recommended_frontend_usage",
            "recommended_backend_shape",
            "calendar_events",
        ):
            self.assertIn(top_level_key, payload)

        for item_key in (
            "key",
            "display_name",
            "category",
            "provider",
            "description",
            "short_label",
            "market_role",
            "higher_meaning",
            "lower_meaning",
            "watch_points",
            "related_indicators",
            "display_text",
            "workflow_status",
            "analysis_hints",
            "event_definition",
        ):
            self.assertIn(item_key, first)

    def test_goal_3_calendar_models_preserve_domain_split(self) -> None:
        calendar_columns = set(EconomicCalendarEvent.__table__.columns.keys())
        for required_column in (
            "event_key",
            "event_type",
            "category",
            "title",
            "display_name",
            "short_name",
            "event_datetime_utc",
            "event_date_local",
            "event_time_local",
            "timezone",
            "importance",
            "status",
            "date_precision",
            "time_source",
            "time_confidence",
            "beginner_description",
            "why_it_matters",
            "watch_items",
            "related_indicator_keys",
        ):
            self.assertIn(required_column, calendar_columns)

        fomc_detail_columns = set(FomcEventDetail.__table__.columns.keys())
        self.assertIn("calendar_event_id", fomc_detail_columns)
        self.assertIn("statement_url", fomc_detail_columns)
        self.assertIn("minutes_url", fomc_detail_columns)

    def test_goal_4_calendar_description_service_exposes_shared_metadata(self) -> None:
        description = get_calendar_event_description("US_CPI")

        self.assertEqual(description["event_key"], "US_CPI")
        self.assertEqual(description["display_name"], "미국 CPI")
        self.assertEqual(description["provider"], "fred")
        self.assertEqual(description["event_type"], "macro_release")
        self.assertEqual(description["default_time"], "08:30")
        self.assertIn("PCEPILFE", description["related_indicators"])
        self.assertIn("S&P 500", description["watch_items"])
        self.assertEqual(get_calendar_event_definitions_path().name, "calendar_event_definitions.json")

    def test_goal_5_calendar_collection_service_is_definition_driven(self) -> None:
        service_source = Path(calendar_collection_service.__file__).read_text(encoding="utf-8")

        self.assertIn("CalendarDefinitionLoader", service_source)
        self.assertIn("FredReleaseDateLoader", service_source)
        self.assertIn("RuleBasedMarketCalendarBuilder", service_source)
        self.assertNotIn("collect_bls_calendar", service_source)

    def test_goal_5_rule_based_events_match_new_mvp_keys(self) -> None:
        monthly = generate_monthly_opex(2026)
        quarterly = generate_triple_witching(2026)

        self.assertEqual(monthly[0]["event_key"], "US_MONTHLY_OPEX")
        self.assertEqual(monthly[0]["event_time"], "16:00")
        self.assertEqual(monthly[0]["category"], "market_structure")
        self.assertEqual(quarterly[0]["event_key"], "US_TRIPLE_WITCHING")
        self.assertEqual(quarterly[0]["event_time"], "16:00")
        self.assertEqual(quarterly[0]["category"], "market_structure")

    def test_goal_6_bls_calendar_implementation_is_removed(self) -> None:
        bls_module_spec = importlib.util.find_spec("app.collectors.calendar.bls_calendar")
        self.assertIsNone(bls_module_spec)

        self.assertFalse(hasattr(settings, "CALENDAR_BLS_ENABLED"))
        self.assertFalse(hasattr(settings, "CALENDAR_BLS_ICS_URL"))

        bls_file = Path(__file__).resolve().parents[1] / "app" / "collectors" / "calendar" / "bls_calendar.py"
        self.assertFalse(bls_file.exists())


if __name__ == "__main__":
    unittest.main()
