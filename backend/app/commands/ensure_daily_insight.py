from __future__ import annotations

import argparse
import json
import sys

from ..core.database import SessionLocal
from ..services.daily_insight_service import daily_insight_to_summary_response, ensure_daily_insight


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ensure daily AI insight row exists.")
    parser.add_argument("--as-of-date", help="Target date in YYYY-MM-DD format.")
    parser.add_argument("--force", action="store_true", help="Force synchronous regeneration.")
    parser.add_argument("--json", action="store_true", help="Print raw JSON output.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    db = SessionLocal()
    try:
        result = ensure_daily_insight(db, as_of_date=args.as_of_date, force=args.force)
    except Exception as exc:
        print(f"Daily insight ensure failed: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()

    if hasattr(result, "as_of_date"):
        payload = daily_insight_to_summary_response(result)
    else:
        payload = result

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print("Daily insight ensure completed:")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
