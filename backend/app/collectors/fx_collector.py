"""ExchangeRate-API collector for forex pairs."""
import logging
import httpx
from datetime import datetime
from sqlalchemy.orm import Session
from ..core.config import settings
from ..core.upsert import upsert_rows
from ..models.indicators import ExchangeRate

logger = logging.getLogger(__name__)

BASE_CURRENCIES = ["USD", "EUR"]
TARGET_PAIRS = {
    "USD": ["KRW", "JPY", "EUR", "CNY", "GBP"],
    "EUR": ["USD"],
}


def collect_exchange_rates(db: Session):
    if not settings.EXCHANGERATE_API_KEY:
        # Fallback: use free open.er-api.com (no key needed, 1500 req/month)
        return _collect_free_rates(db)

    url = f"https://v6.exchangerate-api.com/v6/{settings.EXCHANGERATE_API_KEY}/latest/USD"
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.get(url)
            resp.raise_for_status()
            data = resp.json()
            rates = data.get("conversion_rates", {})
            date = datetime.now().replace(microsecond=0)
            for target in ["KRW", "JPY", "EUR", "CNY", "GBP"]:
                if target in rates:
                    pair = f"USD{target}"
                    _upsert_rate(db, date, pair, float(rates[target]))
        db.commit()
        logger.info("Collected exchange rates via ExchangeRate-API")
        return {
            "fetched_count": len([target for target in ["KRW", "JPY", "EUR", "CNY", "GBP"] if target in rates]),
            "inserted_count": len([target for target in ["KRW", "JPY", "EUR", "CNY", "GBP"] if target in rates]),
            "updated_count": len([target for target in ["KRW", "JPY", "EUR", "CNY", "GBP"] if target in rates]),
        }
    except Exception as e:
        db.rollback()
        logger.error(f"ExchangeRate-API error: {e}")
        return _collect_free_rates(db)


def _collect_free_rates(db: Session):
    """Fallback: open.er-api.com free tier (no key required)."""
    try:
        url = "https://open.er-api.com/v6/latest/USD"
        with httpx.Client(timeout=15) as client:
            resp = client.get(url)
            resp.raise_for_status()
            data = resp.json()
            rates = data.get("rates", {})
            date = datetime.now().replace(microsecond=0)
            for target in ["KRW", "JPY", "EUR", "CNY", "GBP"]:
                if target in rates:
                    pair = f"USD{target}"
                    _upsert_rate(db, date, pair, float(rates[target]))
        db.commit()
        logger.info("Collected exchange rates via open.er-api.com (free fallback)")
        return {
            "fetched_count": len([target for target in ["KRW", "JPY", "EUR", "CNY", "GBP"] if target in rates]),
            "inserted_count": len([target for target in ["KRW", "JPY", "EUR", "CNY", "GBP"] if target in rates]),
            "updated_count": len([target for target in ["KRW", "JPY", "EUR", "CNY", "GBP"] if target in rates]),
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Free FX API error: {e}")
        raise RuntimeError(f"FX collection failed for both primary and fallback providers: {type(e).__name__}: {e}") from e


def _upsert_rate(db: Session, date: datetime, pair: str, value: float):
    normalized_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
    upsert_rows(
        db,
        ExchangeRate,
        [{"date": normalized_date, "pair": pair, "value": value}],
        conflict_columns=["pair", "date"],
        update_columns=["value"],
    )
