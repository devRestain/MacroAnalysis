"""FRED API collector — interest rates, macro indicators, credit spreads."""
import logging
from datetime import datetime, timedelta
from fredapi import Fred
from sqlalchemy.orm import Session
from ..core.config import settings
from ..core.upsert import upsert_rows
from ..models.indicators import InterestRate, MacroIndicator, CreditSpread

logger = logging.getLogger(__name__)

# FRED series mappings
RATE_SERIES = {
    "DFF": "Fed Funds Rate",
    "DGS2": "2Y Treasury Yield",
    "DGS10": "10Y Treasury Yield",
    "DGS30": "30Y Treasury Yield",
    "T10Y2Y": "10Y-2Y Spread",
    "SOFR": "SOFR",
}

MACRO_SERIES = {
    "CPIAUCSL": "CPI",
    "PCEPILFE": "Core PCE",
    "GDPC1": "Real GDP",
    "UNRATE": "Unemployment Rate",
    "ICSA": "Initial Jobless Claims",
    "M2SL": "M2 Money Supply",
    "USSLIND": "LEI",
    "MANEMP": "Manufacturing Employment",
}

CREDIT_SERIES = {
    "BAMLH0A0HYM2": "HY_OAS",   # ICE BofA HY OAS
    "BAMLC0A0CM": "IG_OAS",      # ICE BofA IG OAS
}


def get_fred_client() -> Fred:
    return Fred(api_key=settings.FRED_API_KEY)


def collect_rates(db: Session):
    fred = get_fred_client()
    cutoff = datetime.now() - timedelta(days=30)
    for series_id, label in RATE_SERIES.items():
        try:
            data = fred.get_series(series_id, observation_start=cutoff)
            rows = [
                {
                    "date": date.to_pydatetime(),
                    "series_key": series_id,
                    "value": float(value),
                }
                for date, value in data.dropna().items()
            ]
            upsert_rows(
                db,
                InterestRate,
                rows,
                conflict_columns=["series_key", "date"],
                update_columns=["value"],
            )
            db.commit()
            logger.info(f"Collected {series_id} ({label})")
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to collect {series_id}: {e}")


def collect_macro(db: Session):
    fred = get_fred_client()
    cutoff = datetime.now() - timedelta(days=365 * 2)
    for series_id, label in MACRO_SERIES.items():
        try:
            data = fred.get_series(series_id, observation_start=cutoff)
            rows = [
                {
                    "date": date.to_pydatetime(),
                    "series_key": series_id,
                    "value": float(value),
                }
                for date, value in data.dropna().items()
            ]
            upsert_rows(
                db,
                MacroIndicator,
                rows,
                conflict_columns=["series_key", "date"],
                update_columns=["value"],
            )
            db.commit()
            logger.info(f"Collected macro {series_id} ({label})")
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to collect macro {series_id}: {e}")


def collect_credit_spreads(db: Session):
    fred = get_fred_client()
    cutoff = datetime.now() - timedelta(days=365)
    for series_id, key in CREDIT_SERIES.items():
        try:
            data = fred.get_series(series_id, observation_start=cutoff)
            rows = [
                {
                    "date": date.to_pydatetime(),
                    "series_key": key,
                    "value": float(value),
                }
                for date, value in data.dropna().items()
            ]
            upsert_rows(
                db,
                CreditSpread,
                rows,
                conflict_columns=["series_key", "date"],
                update_columns=["value"],
            )
            db.commit()
            logger.info(f"Collected credit spread {key}")
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to collect credit spread {key}: {e}")
