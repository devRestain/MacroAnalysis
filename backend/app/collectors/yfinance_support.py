from __future__ import annotations

import logging
from typing import Iterable

import pandas as pd
import yfinance as yf

from ..core.config import settings

logger = logging.getLogger(__name__)

_YFINANCE_CONFIGURED = False


def configure_yfinance() -> None:
    global _YFINANCE_CONFIGURED
    if _YFINANCE_CONFIGURED:
        return

    try:
        yf.config.network.retries = settings.YFINANCE_RETRIES
        yf.config.debug.hide_exceptions = False
    except Exception as exc:
        logger.warning("Unable to apply yfinance network config: %s", exc)

    try:
        if settings.YFINANCE_TZ_CACHE_DIR:
            yf.set_tz_cache_location(settings.YFINANCE_TZ_CACHE_DIR)
    except Exception as exc:
        logger.warning("Unable to set yfinance cache dir: %s", exc)

    _YFINANCE_CONFIGURED = True


def download_ticker_frames(
    tickers: Iterable[str],
    *,
    period: str,
    interval: str = "1d",
) -> dict[str, pd.DataFrame]:
    configure_yfinance()
    tickers = list(dict.fromkeys(tickers))
    if not tickers:
        return {}

    data = yf.download(
        tickers=tickers,
        period=period,
        interval=interval,
        auto_adjust=False,
        progress=False,
        group_by="ticker",
        threads=False,
        timeout=settings.YFINANCE_TIMEOUT_SECONDS,
    )
    if data.empty:
        return {ticker: pd.DataFrame() for ticker in tickers}

    frames: dict[str, pd.DataFrame] = {}
    if isinstance(data.columns, pd.MultiIndex):
        for ticker in tickers:
            if ticker in data.columns.get_level_values(0):
                frames[ticker] = data[ticker].dropna(how="all")
            else:
                frames[ticker] = pd.DataFrame()
        return frames

    # Single ticker path may come back with a flat column index.
    frames[tickers[0]] = data.dropna(how="all")
    for ticker in tickers[1:]:
        frames[ticker] = pd.DataFrame()
    return frames


def normalize_price_history(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty or "Close" not in frame.columns:
        return pd.DataFrame()
    history = frame.dropna(subset=["Close"]).copy()
    if history.empty:
        return history
    if getattr(history.index, "tz", None) is not None:
        history.index = history.index.tz_localize(None)
    return history
