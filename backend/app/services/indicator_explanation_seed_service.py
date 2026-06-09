from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from ..models.indicators import IndicatorExplanation
from .indicator_explanation_loader import (
    get_indicator_explanations_path,
    iter_indicator_explanation_items,
    load_indicator_explanations,
)

logger = logging.getLogger(__name__)


UPSERT_FIELDS = (
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
    "workflow_status",
    "display_text",
    "analysis_hints",
    "source_schema_version",
    "source_file",
)


def seed_indicator_explanations(
    db: Session,
    *,
    commit: bool = True,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Seed static indicator explanation metadata into the database.

    Indicator explanation metadata is static display/rule-seed data,
    not runtime sentiment or expectation output.
    """
    payload = payload or load_indicator_explanations()
    schema_version = payload.get("schema_version")
    source_file = str(get_indicator_explanations_path())
    items = iter_indicator_explanation_items(payload)

    inserted = 0
    updated = 0
    skipped = 0

    for item in items:
        indicator_key = item["key"]
        row = (
            db.query(IndicatorExplanation)
            .filter(IndicatorExplanation.indicator_key == indicator_key)
            .first()
        )

        mapped = _map_item_to_row_data(
            item,
            source_schema_version=schema_version,
            source_file=source_file,
        )

        if row is None:
            db.add(IndicatorExplanation(indicator_key=indicator_key, **mapped))
            inserted += 1
            continue

        if _row_matches(row, mapped):
            skipped += 1
            continue

        for field, value in mapped.items():
            setattr(row, field, value)
        updated += 1

    if commit:
        db.commit()

    result = {
        "inserted_count": inserted,
        "updated_count": updated,
        "skipped_count": skipped,
        "total_processed_count": len(items),
        "source_file_path": source_file,
        "source_schema_version": schema_version,
    }
    logger.info("Seeded indicator explanations: %s", result)
    return result


def _map_item_to_row_data(
    item: dict[str, Any],
    *,
    source_schema_version: str | None,
    source_file: str,
) -> dict[str, Any]:
    return {
        "display_name": item.get("display_name") or item["key"],
        "category": item.get("category"),
        "provider": item.get("provider"),
        "description": item.get("description"),
        "short_label": item.get("short_label"),
        "market_role": item.get("market_role"),
        "higher_meaning": item.get("higher_meaning"),
        "lower_meaning": item.get("lower_meaning"),
        "watch_points": item.get("watch_points"),
        "related_indicators": item.get("related_indicators"),
        "workflow_status": item.get("workflow_status"),
        "display_text": item.get("display_text"),
        "analysis_hints": item.get("analysis_hints"),
        "source_schema_version": source_schema_version or "unknown",
        "source_file": source_file,
    }


def _row_matches(row: IndicatorExplanation, mapped: dict[str, Any]) -> bool:
    for field in UPSERT_FIELDS:
        if getattr(row, field) != mapped[field]:
            return False
    return True
