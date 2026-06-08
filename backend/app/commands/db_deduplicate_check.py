from __future__ import annotations

import argparse
import json
import sys

from ..core.database import SessionLocal
from ..services.deduplicate_check_service import check_duplicate_candidates


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only duplicate candidate check.")
    parser.add_argument("--json", action="store_true", help="Print raw JSON output.")
    parser.add_argument("--sample-limit", type=int, default=3, help="Samples per table.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    db = SessionLocal()
    try:
        result = check_duplicate_candidates(db, sample_limit=args.sample_limit)
    except Exception as exc:
        print(f"Deduplicate check failed. Check DATABASE_URL and DB connectivity: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    else:
        print(f"Total duplicate groups: {result['total_duplicate_groups']}")
        for table in result["tables"]:
            print(f"- {table['table_name']}: {table['duplicate_group_count']}")
            for sample in table["sample"]:
                print(f"    sample: {sample}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
