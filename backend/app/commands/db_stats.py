from __future__ import annotations

import argparse
import json
import sys

from ..core.database import SessionLocal
from ..services.db_stats_service import get_db_stats


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Show database size and table statistics.")
    parser.add_argument("--json", action="store_true", help="Print raw JSON output.")
    parser.add_argument("--top", type=int, default=5, help="Number of largest tables/indexes to show.")
    parser.add_argument("--size-only", action="store_true", help="Print a compact size-only summary.")
    return parser


def format_text(stats: dict, *, size_only: bool = False) -> str:
    lines = [
        f"Dialect: {stats['dialect']}",
        f"Database: {stats['database_name']}",
        f"Database Size (bytes): {stats['database_size_bytes']}",
        f"Table Count: {stats['table_count']}",
    ]
    latest_cleanup = stats.get("latest_cleanup")
    if latest_cleanup:
        lines.append(
            "Latest Cleanup: "
            f"{latest_cleanup['finished_at']} "
            f"(success={latest_cleanup['collection_success_logs_deleted']}, "
            f"failure={latest_cleanup['collection_failure_logs_deleted']}, "
            f"debug={latest_cleanup['debug_logs_deleted']}, "
            f"scheduler={latest_cleanup['scheduler_logs_deleted']})"
        )
    if size_only:
        lines.append("Largest Tables:")
        for row in stats["largest_tables"]:
            lines.append(
                f"  - {row['table_name']}: total={row['total_size_bytes']} table={row['table_size_bytes']} "
                f"index={row['index_size_bytes']} rows={row['row_estimate']}"
            )
        return "\n".join(lines)

    lines.append("Tables:")
    for row in stats["tables"]:
        lines.append(
            f"  - {row['table_name']}: total={row['total_size_bytes']} "
            f"table={row['table_size_bytes']} index={row['index_size_bytes']} rows={row['row_estimate']}"
        )
    if stats["largest_indexes"]:
        lines.append("Largest Indexes:")
        for row in stats["largest_indexes"]:
            lines.append(
                f"  - {row['index_name']} ({row['table_name']}): size={row['index_size_bytes']}"
            )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    db = SessionLocal()
    try:
        stats = get_db_stats(db, top_n=args.top)
    except Exception as exc:
        print(f"DB stats failed. Check DATABASE_URL and DB connectivity: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()

    if args.json:
        print(json.dumps(stats, ensure_ascii=False, indent=2))
    else:
        print(format_text(stats, size_only=args.size_only))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
