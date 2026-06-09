from __future__ import annotations

import argparse
import json

from ..workers.sentiment_worker import run_daily_sentiment_pipeline, run_daily_sentiment_pipeline_sync


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the sentiment/expectation pipeline.")
    parser.add_argument(
        "--queue",
        action="store_true",
        help="Queue through Celery instead of running synchronously in this process.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    result = run_daily_sentiment_pipeline() if args.queue else run_daily_sentiment_pipeline_sync()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
