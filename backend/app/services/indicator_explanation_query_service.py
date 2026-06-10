from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from ..models import IndicatorExplanation


def list_indicator_explanations(
    db: Session,
    *,
    category: str | None = None,
) -> list[dict[str, Any]]:
    q = db.query(IndicatorExplanation)
    if category:
        q = q.filter(IndicatorExplanation.category == category)

    rows = q.order_by(IndicatorExplanation.indicator_key.asc()).all()
    return [indicator_explanation_to_dict(row) for row in rows]


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
        return None
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
