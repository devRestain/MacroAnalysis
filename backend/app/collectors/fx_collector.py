"""ExchangeRate-API collector for forex pairs."""
import logging
import httpx
from datetime import datetime
from sqlalchemy.orm import Session
from ..core.config import settings
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
        _collect_free_rates(db)
        return

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
    except Exception as e:
        db.rollback()
        logger.error(f"ExchangeRate-API error: {e}")
        _collect_free_rates(db)


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
    except Exception as e:
        db.rollback()
        logger.error(f"Free FX API error: {e}")


def _upsert_rate(db: Session, date: datetime, pair: str, value: float):
    exists = db.query(ExchangeRate).filter(
        ExchangeRate.pair == pair,
        ExchangeRate.date >= date.replace(hour=0, minute=0, second=0)
    ).first()
    if not exists:
        db.add(ExchangeRate(date=date, pair=pair, value=value))
