"""yfinance collector — equity indices, sectors, commodities."""
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from ..core.upsert import upsert_rows
from ..models.indicators import EquityIndex, SectorPerformance, RealEconomyIndicator
from .result_utils import add_counts, empty_counts, format_error_summary
from .yfinance_support import download_ticker_frames, normalize_price_history

logger = logging.getLogger(__name__)

EQUITY_TICKERS = {
    "^GSPC": "S&P 500",
    "^IXIC": "NASDAQ",
    "^KS11": "KOSPI",
    "^N225": "Nikkei 225",
    "^GDAXI": "DAX",
    "000001.SS": "Shanghai Composite",
    "^VIX": "VIX",
    "^TNX": "10Y Yield (Market)",
    "GC=F": "Gold",
    "CL=F": "WTI Crude",
    "BZ=F": "Brent Crude",
    "HG=F": "Copper",
    "DX-Y.NYB": "DXY",
}

SECTOR_TICKERS = {
    "XLK": "Technology",
    "XLF": "Financials",
    "XLE": "Energy",
    "XLV": "Health Care",
    "XLI": "Industrials",
    "XLY": "Consumer Disc.",
    "XLP": "Consumer Staples",
    "XLU": "Utilities",
    "XLB": "Materials",
    "XLRE": "Real Estate",
    "XLC": "Communication",
}


def collect_equity_indices(db: Session, tickers: list[str] | None = None):
    selected_tickers = tickers or list(EQUITY_TICKERS.keys())
    counts = empty_counts()
    errors: list[str] = []
    frames = download_ticker_frames(selected_tickers, period="5d")
    for ticker in selected_tickers:
        name = EQUITY_TICKERS.get(ticker, ticker)
        try:
            hist = normalize_price_history(frames.get(ticker))
            if len(hist) < 1:
                errors.append(f"{ticker}:empty_history")
                continue
            latest = hist.iloc[-1]
            prev = hist.iloc[-2] if len(hist) >= 2 else None
            close = float(latest["Close"])
            date = latest.name.to_pydatetime().replace(tzinfo=None)
            change_1d = float(latest["Close"] - prev["Close"]) if prev is not None else 0.0
            change_1d_pct = (change_1d / float(prev["Close"]) * 100) if prev is not None else 0.0

            upsert_rows(
                db,
                EquityIndex,
                [{
                    "date": date,
                    "ticker": ticker,
                    "close": close,
                    "change_1d": change_1d,
                    "change_1d_pct": change_1d_pct,
                }],
                conflict_columns=["ticker", "date"],
                update_columns=["close", "change_1d", "change_1d_pct"],
            )
            db.commit()
            add_counts(counts, {"fetched_count": 1, "inserted_count": 1, "updated_count": 1})
            logger.info(f"Collected {ticker} ({name}): {close:.2f}")
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to collect equity {ticker}: {e}")
            errors.append(f"{ticker}:{type(e).__name__}")
    if counts["fetched_count"] == 0 and errors:
        raise RuntimeError(f"yfinance equity collection failed for all tickers: {format_error_summary(errors)}")
    if errors:
        logger.warning("Partial yfinance equity collection failure: %s", format_error_summary(errors))
    return counts


def collect_sectors(db: Session):
    counts = empty_counts()
    errors: list[str] = []
    frames = download_ticker_frames(SECTOR_TICKERS.keys(), period="1y")
    for ticker, name in SECTOR_TICKERS.items():
        try:
            hist = normalize_price_history(frames.get(ticker))
            if len(hist) < 5:
                errors.append(f"{ticker}:insufficient_history")
                continue
            latest = hist.iloc[-1]
            date = latest.name.to_pydatetime().replace(tzinfo=None)
            close = float(latest["Close"])

            def pct(days):
                idx = max(0, len(hist) - 1 - days)
                base = float(hist.iloc[idx]["Close"])
                return (close - base) / base * 100 if base else 0.0

            # YTD
            ytd_start = datetime(date.year, 1, 1)
            ytd_hist = hist[hist.index >= ytd_start]
            if len(ytd_hist) > 0:
                ytd_base = float(ytd_hist.iloc[0]["Close"])
                ytd_pct = (close - ytd_base) / ytd_base * 100
            else:
                ytd_pct = 0.0

            upsert_rows(
                db,
                SectorPerformance,
                [{
                    "date": date,
                    "ticker": ticker,
                    "sector_name": name,
                    "close": close,
                    "change_1d_pct": pct(1),
                    "change_1m_pct": pct(21),
                    "change_3m_pct": pct(63),
                    "change_ytd_pct": ytd_pct,
                }],
                conflict_columns=["ticker", "date"],
                update_columns=[
                    "sector_name",
                    "close",
                    "change_1d_pct",
                    "change_1m_pct",
                    "change_3m_pct",
                    "change_ytd_pct",
                ],
            )
            db.commit()
            add_counts(counts, {"fetched_count": 1, "inserted_count": 1, "updated_count": 1})
            logger.info(f"Collected sector {ticker} ({name})")
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to collect sector {ticker}: {e}")
            errors.append(f"{ticker}:{type(e).__name__}")
    if counts["fetched_count"] == 0 and errors:
        raise RuntimeError(f"yfinance sector collection failed for all tickers: {format_error_summary(errors)}")
    if errors:
        logger.warning("Partial yfinance sector collection failure: %s", format_error_summary(errors))
    return counts


def collect_real_economy(db: Session):
    """Copper/Gold ratio and WTI/Brent spread."""
    counts = empty_counts()
    try:
        frames = download_ticker_frames(["HG=F", "GC=F", "CL=F", "BZ=F"], period="5d")
        copper = normalize_price_history(frames.get("HG=F"))
        gold = normalize_price_history(frames.get("GC=F"))
        wti = normalize_price_history(frames.get("CL=F"))
        brent = normalize_price_history(frames.get("BZ=F"))

        if len(copper) >= 1 and len(gold) >= 1:
            date = copper.iloc[-1].name.to_pydatetime().replace(tzinfo=None)
            ratio = float(copper.iloc[-1]["Close"]) / float(gold.iloc[-1]["Close"])
            _upsert_real(db, date, "COPPER_GOLD", ratio)
            add_counts(counts, {"fetched_count": 1, "inserted_count": 1, "updated_count": 1})

        if len(wti) >= 1 and len(brent) >= 1:
            date = wti.iloc[-1].name.to_pydatetime().replace(tzinfo=None)
            spread = float(brent.iloc[-1]["Close"]) - float(wti.iloc[-1]["Close"])
            _upsert_real(db, date, "WTI_BRENT_SPREAD", spread)
            add_counts(counts, {"fetched_count": 1, "inserted_count": 1, "updated_count": 1})

        db.commit()
        if counts["fetched_count"] == 0:
            raise RuntimeError("yfinance real economy collection returned no usable price history")
        return counts
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to collect real economy: {e}")
        raise RuntimeError(f"yfinance real economy collection failed: {type(e).__name__}: {e}") from e


def _upsert_real(db: Session, date: datetime, key: str, value: float):
    upsert_rows(
        db,
        RealEconomyIndicator,
        [{"date": date, "series_key": key, "value": value}],
        conflict_columns=["series_key", "date"],
        update_columns=["value"],
    )
