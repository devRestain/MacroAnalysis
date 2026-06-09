from __future__ import annotations

import json
import sys

from ..core.database import SessionLocal, init_db
from ..services.indicator_explanation_seed_service import seed_indicator_explanations


def format_text(result: dict) -> str:
    return "\n".join(
        [
            "Indicator explanation seed completed.",
            f"Inserted count: {result['inserted_count']}",
            f"Updated count: {result['updated_count']}",
            f"Skipped count: {result['skipped_count']}",
            f"Total processed count: {result['total_processed_count']}",
            f"Source file path: {result['source_file_path']}",
            f"Source schema version: {result['source_schema_version']}",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    as_json = bool(argv and "--json" in argv)
    init_db()
    db = SessionLocal()
    try:
        result = seed_indicator_explanations(db)
    except Exception as exc:
        db.rollback()
        print(f"Indicator explanation seed failed: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()

    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_text(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
