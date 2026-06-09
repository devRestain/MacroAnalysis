from __future__ import annotations

import json

from ..workers.sentiment_worker import run_daily_sentiment_pipeline


def main() -> int:
    result = run_daily_sentiment_pipeline()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
