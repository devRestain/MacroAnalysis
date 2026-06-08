from __future__ import annotations

import argparse
import json
import sys

from ..core.database import SessionLocal
from ..services.collection_orchestrator import (
    run_evening_batch,
    run_morning_batch,
    run_noon_batch,
    run_weekly_batch,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run batched collection jobs manually.")
    parser.add_argument(
        "batch",
        choices=["morning", "noon", "evening", "weekly", "all-batched"],
        help="Batch to run.",
    )
    parser.add_argument("--json", action="store_true", help="Print raw JSON output.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    db = SessionLocal()
    try:
        if args.batch == "morning":
            result = run_morning_batch(db)
        elif args.batch == "noon":
            result = run_noon_batch(db)
        elif args.batch == "evening":
            result = run_evening_batch(db)
        elif args.batch == "weekly":
            result = run_weekly_batch(db)
        else:
            result = {
                "runs": [
                    run_morning_batch(db),
                    run_noon_batch(db),
                    run_evening_batch(db),
                ]
            }
    except Exception as exc:
        print(f"Batch collection failed: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(_format_text(result))
    return 0


def _format_text(result: dict) -> str:
    runs = result.get("runs")
    if runs:
        return "\n\n".join(_format_single_run(run) for run in runs)
    return _format_single_run(result)


def _format_single_run(run: dict) -> str:
    lines = [
        f"Batch: {run['batch']}",
        f"Started: {run['started_at']}",
        f"Finished: {run['finished_at']}",
        "Jobs:",
    ]
    for job in run["jobs"]:
        suffix = ""
        if job.get("reason"):
            suffix = f" ({job['reason']})"
        lines.append(
            "  - "
            f"{job['job_key']}: {job['status']}{suffix} "
            f"[fetched={job.get('fetched_count', 0)}, inserted={job.get('inserted_count', 0)}, updated={job.get('updated_count', 0)}]"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
