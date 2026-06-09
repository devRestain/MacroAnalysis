from __future__ import annotations

import json
from pathlib import Path


SEED_PATH = Path(__file__).resolve().parents[2] / "data" / "calendar_seed.json"


def load_seed_events() -> list[dict]:
    if not SEED_PATH.exists():
        return []
    raw_rows = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    return [row for row in raw_rows if row.get("event_date")]
