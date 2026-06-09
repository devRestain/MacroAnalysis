from __future__ import annotations

from typing import Any


def empty_counts() -> dict[str, int]:
    return {
        "fetched_count": 0,
        "inserted_count": 0,
        "updated_count": 0,
    }


def add_counts(total: dict[str, int], counts: dict[str, Any] | None) -> dict[str, int]:
    counts = counts or {}
    total["fetched_count"] += int(counts.get("fetched_count", 0) or 0)
    total["inserted_count"] += int(counts.get("inserted_count", 0) or 0)
    total["updated_count"] += int(counts.get("updated_count", 0) or 0)
    return total


def format_error_summary(errors: list[str], *, limit: int = 3) -> str:
    if not errors:
        return ""
    summary = ", ".join(errors[:limit])
    if len(errors) > limit:
        summary = f"{summary} (+{len(errors) - limit} more)"
    return summary
