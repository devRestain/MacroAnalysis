from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from ..models import IndicatorExplanation
from .indicator_explanation_loader import iter_indicator_explanation_items, load_indicator_explanations


def list_indicator_explanations(
    db: Session,
    *,
    category: str | None = None,
) -> list[dict[str, Any]]:
    q = db.query(IndicatorExplanation)
    if category:
        q = q.filter(IndicatorExplanation.category == category)

    rows = q.order_by(IndicatorExplanation.indicator_key.asc()).all()
    if rows:
        return [indicator_explanation_to_dict(row) for row in rows]

    payload = load_indicator_explanations()
    schema_version = str(payload.get("schema_version") or "unknown")
    items = [_static_indicator_explanation_to_dict(item, schema_version=schema_version) for item in iter_indicator_explanation_items(payload)]
    if category:
        items = [item for item in items if item.get("category") == category]
    return sorted(items, key=lambda item: str(item.get("indicator_key") or ""))


def get_indicator_explanation(
    db: Session,
    indicator_key: str,
) -> dict[str, Any] | None:
    row = (
        db.query(IndicatorExplanation)
        .filter(IndicatorExplanation.indicator_key == indicator_key)
        .first()
    )
    if not row:
        return _static_indicator_explanation_by_key(indicator_key)
    return indicator_explanation_to_dict(row)


def indicator_explanation_to_dict(row: IndicatorExplanation) -> dict[str, Any]:
    return {
        "indicator_key": row.indicator_key,
        "display_name": row.display_name,
        "category": row.category,
        "provider": row.provider,
        "description": row.description,
        "short_label": row.short_label,
        "market_role": row.market_role,
        "higher_meaning": row.higher_meaning,
        "lower_meaning": row.lower_meaning,
        "watch_points": row.watch_points,
        "related_indicators": row.related_indicators,
        "display_text": row.display_text,
        "workflow_status": row.workflow_status,
        "analysis_hints": row.analysis_hints,
        "source_schema_version": row.source_schema_version,
    }


def _static_indicator_explanation_by_key(indicator_key: str) -> dict[str, Any] | None:
    payload = load_indicator_explanations()
    schema_version = str(payload.get("schema_version") or "unknown")
    for item in iter_indicator_explanation_items(payload):
        if item.get("key") == indicator_key:
            return _static_indicator_explanation_to_dict(item, schema_version=schema_version)
    return None


def _static_indicator_explanation_to_dict(item: dict[str, Any], *, schema_version: str = "unknown") -> dict[str, Any]:
    return {
        "indicator_key": item["key"],
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
        "display_text": item.get("display_text"),
        "workflow_status": item.get("workflow_status"),
        "analysis_hints": item.get("analysis_hints"),
        "source_schema_version": schema_version,
    }
