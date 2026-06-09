from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DATA_FILE_NAME = "indicator_explanations_v1_1_workflow_aware.json"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_FILE_PATH = DATA_DIR / DATA_FILE_NAME
TOP_LEVEL_KEYS = (
    "schema_version",
    "purpose",
    "workflow_metadata",
    "timeseries_indicators",
    "non_series_display_metrics",
)


class IndicatorExplanationLoaderError(ValueError):
    """Raised when static indicator explanation metadata is missing or malformed."""


def get_indicator_explanations_path() -> Path:
    return DATA_FILE_PATH


def load_indicator_explanations() -> dict[str, Any]:
    path = get_indicator_explanations_path()
    if not path.exists():
        raise IndicatorExplanationLoaderError(
            f"Indicator explanations file not found: {path}"
        )

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise IndicatorExplanationLoaderError(
            f"Indicator explanations file is not valid JSON: {path}"
        ) from exc

    validate_indicator_explanations_payload(payload)
    return payload


def validate_indicator_explanations_payload(payload: dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise IndicatorExplanationLoaderError("Indicator explanations payload must be a JSON object.")

    for key in TOP_LEVEL_KEYS:
        if key not in payload:
            raise IndicatorExplanationLoaderError(
                f"Indicator explanations payload is missing top-level key: {key}"
            )

    for list_key in ("timeseries_indicators", "non_series_display_metrics"):
        items = payload.get(list_key)
        if not isinstance(items, list):
            raise IndicatorExplanationLoaderError(
                f"Indicator explanations field `{list_key}` must be a list."
            )
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                raise IndicatorExplanationLoaderError(
                    f"Indicator explanations item `{list_key}[{index}]` must be an object."
                )
            item_key = item.get("key")
            if not isinstance(item_key, str) or not item_key.strip():
                raise IndicatorExplanationLoaderError(
                    f"Indicator explanations item `{list_key}[{index}]` is missing a non-empty `key`."
                )

    workflow_metadata = payload.get("workflow_metadata")
    if not isinstance(workflow_metadata, dict):
        raise IndicatorExplanationLoaderError(
            "Indicator explanations payload `workflow_metadata` must be an object."
        )


def iter_indicator_explanation_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    validate_indicator_explanations_payload(payload)
    return [
        *payload["timeseries_indicators"],
        *payload["non_series_display_metrics"],
    ]
