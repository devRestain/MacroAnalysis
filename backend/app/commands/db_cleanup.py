from __future__ import annotations

import argparse
import json
import sys

from ..core.database import SessionLocal
from ..services.cleanup_service import run_cleanup


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run retention cleanup manually.")
    parser.add_argument("--json", action="store_true", help="Print raw JSON output.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    db = SessionLocal()
    try:
        result = run_cleanup(db)
    except Exception as exc:
        print(f"DB cleanup failed. Check DATABASE_URL and DB connectivity: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("Cleanup completed:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
