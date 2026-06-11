from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

try:
    from kombu.exceptions import OperationalError
except ModuleNotFoundError:  # pragma: no cover - lightweight test fallback
    class OperationalError(Exception):
        pass


BROKER_UNAVAILABLE_EXCEPTIONS = (OperationalError, ConnectionError, OSError)


def dispatch_task_or_run_sync(
    task: Any,
    *args: Any,
    task_name: str,
    logger: logging.Logger,
    before_sync_fallback: Callable[[], None] | None = None,
    **kwargs: Any,
) -> str:
    try:
        task.delay(*args, **kwargs)
        return "queued"
    except BROKER_UNAVAILABLE_EXCEPTIONS as exc:
        logger.info("%s queue unavailable, falling back to sync execution: %s", task_name, exc)
        if before_sync_fallback is not None:
            before_sync_fallback()
        task.run(*args, **kwargs)
        return "sync"
