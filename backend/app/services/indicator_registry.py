from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy.orm import Session

from ..core.upsert import upsert_rows
from ..models.indicators import Indicator, Observation


@dataclass(frozen=True)
class IndicatorSpec:
    code: str
    name: str
    country: str
    category: str
    source: str
    frequency: str
    unit: str
    description: str | None = None


INDICATOR_SPECS: dict[str, IndicatorSpec] = {
    "DFF": IndicatorSpec("DFF", "Fed Funds Rate", "US", "rates", "fred", "daily", "%"),
    "DGS2": IndicatorSpec("DGS2", "2Y Treasury Yield", "US", "rates", "fred", "daily", "%"),
    "DGS10": IndicatorSpec("DGS10", "10Y Treasury Yield", "US", "rates", "fred", "daily", "%"),
    "DGS30": IndicatorSpec("DGS30", "30Y Treasury Yield", "US", "rates", "fred", "daily", "%"),
    "T10Y2Y": IndicatorSpec("T10Y2Y", "10Y-2Y Spread", "US", "rates", "fred", "daily", "%"),
    "SOFR": IndicatorSpec("SOFR", "SOFR", "US", "rates", "fred", "daily", "%"),
    "CPIAUCSL": IndicatorSpec("CPIAUCSL", "CPI", "US", "macro", "fred", "monthly", "index"),
    "PCEPILFE": IndicatorSpec("PCEPILFE", "Core PCE", "US", "macro", "fred", "monthly", "index"),
    "GDPC1": IndicatorSpec("GDPC1", "Real GDP", "US", "macro", "fred", "quarterly", "index"),
    "UNRATE": IndicatorSpec("UNRATE", "Unemployment Rate", "US", "macro", "fred", "monthly", "%"),
    "ICSA": IndicatorSpec("ICSA", "Initial Jobless Claims", "US", "macro", "fred", "weekly", "count"),
    "M2SL": IndicatorSpec("M2SL", "M2 Money Supply", "US", "macro", "fred", "monthly", "billions"),
    "USSLIND": IndicatorSpec("USSLIND", "Leading Economic Index", "US", "macro", "fred", "monthly", "index"),
    "MANEMP": IndicatorSpec("MANEMP", "Manufacturing Employment", "US", "macro", "fred", "monthly", "thousands"),
    "HY_OAS": IndicatorSpec("HY_OAS", "HY OAS", "US", "credit", "fred", "daily", "bp"),
    "IG_OAS": IndicatorSpec("IG_OAS", "IG OAS", "US", "credit", "fred", "daily", "bp"),
    "^GSPC": IndicatorSpec("^GSPC", "S&P 500", "US", "equity", "yfinance", "daily", "index"),
    "^IXIC": IndicatorSpec("^IXIC", "NASDAQ", "US", "equity", "yfinance", "daily", "index"),
    "^KS11": IndicatorSpec("^KS11", "KOSPI", "KR", "equity", "yfinance", "daily", "index"),
    "^N225": IndicatorSpec("^N225", "Nikkei 225", "JP", "equity", "yfinance", "daily", "index"),
    "^GDAXI": IndicatorSpec("^GDAXI", "DAX", "DE", "equity", "yfinance", "daily", "index"),
    "^SSEC": IndicatorSpec("^SSEC", "Shanghai Composite", "CN", "equity", "yfinance", "daily", "index"),
    "^VIX": IndicatorSpec("^VIX", "VIX", "US", "equity", "yfinance", "daily", "index"),
    "^TNX": IndicatorSpec("^TNX", "10Y Treasury Yield (Market)", "US", "rates", "yfinance", "daily", "%"),
    "DX-Y.NYB": IndicatorSpec("DX-Y.NYB", "DXY", "US", "equity", "yfinance", "daily", "index"),
    "CL=F": IndicatorSpec("CL=F", "WTI Crude", "US", "equity", "yfinance", "daily", "USD"),
    "GC=F": IndicatorSpec("GC=F", "Gold", "US", "equity", "yfinance", "daily", "USD"),
    "HG=F": IndicatorSpec("HG=F", "Copper", "US", "equity", "yfinance", "daily", "USD"),
    "USDKRW": IndicatorSpec("USDKRW", "USD/KRW", "KR", "fx", "exchangerate-api", "daily", "KRW"),
    "EURUSD": IndicatorSpec("EURUSD", "EUR/USD", "EU", "fx", "exchangerate-api", "daily", "USD"),
    "USDJPY": IndicatorSpec("USDJPY", "USD/JPY", "JP", "fx", "exchangerate-api", "daily", "JPY"),
    "USDCNY": IndicatorSpec("USDCNY", "USD/CNY", "CN", "fx", "exchangerate-api", "daily", "CNY"),
    "USDGBP": IndicatorSpec("USDGBP", "USD/GBP", "GB", "fx", "exchangerate-api", "daily", "GBP"),
    "COPPER_GOLD": IndicatorSpec("COPPER_GOLD", "Copper/Gold Ratio", "GLOBAL", "real", "yfinance", "daily", "ratio"),
    "WTI_BRENT_SPREAD": IndicatorSpec("WTI_BRENT_SPREAD", "WTI-Brent Spread", "GLOBAL", "real", "yfinance", "daily", "USD"),
    "XLK": IndicatorSpec("XLK", "Technology", "US", "sector", "yfinance", "daily", "index"),
    "XLF": IndicatorSpec("XLF", "Financials", "US", "sector", "yfinance", "daily", "index"),
    "XLE": IndicatorSpec("XLE", "Energy", "US", "sector", "yfinance", "daily", "index"),
    "XLV": IndicatorSpec("XLV", "Health Care", "US", "sector", "yfinance", "daily", "index"),
    "XLI": IndicatorSpec("XLI", "Industrials", "US", "sector", "yfinance", "daily", "index"),
    "XLY": IndicatorSpec("XLY", "Consumer Discretionary", "US", "sector", "yfinance", "daily", "index"),
    "XLP": IndicatorSpec("XLP", "Consumer Staples", "US", "sector", "yfinance", "daily", "index"),
    "XLU": IndicatorSpec("XLU", "Utilities", "US", "sector", "yfinance", "daily", "index"),
    "XLB": IndicatorSpec("XLB", "Materials", "US", "sector", "yfinance", "daily", "index"),
    "XLRE": IndicatorSpec("XLRE", "Real Estate", "US", "sector", "yfinance", "daily", "index"),
    "XLC": IndicatorSpec("XLC", "Communication", "US", "sector", "yfinance", "daily", "index"),
}


def ensure_indicators(db: Session, codes: list[str]) -> dict[str, Indicator]:
    specs = [INDICATOR_SPECS[code] for code in dict.fromkeys(codes) if code in INDICATOR_SPECS]
    if specs:
        upsert_rows(
            db,
            Indicator,
            [
                {
                    "code": spec.code,
                    "name": spec.name,
                    "description": spec.description,
                    "country": spec.country,
                    "category": spec.category,
                    "source": spec.source,
                    "frequency": spec.frequency,
                    "unit": spec.unit,
                    "is_active": True,
                }
                for spec in specs
            ],
            conflict_columns=["code"],
            update_columns=["name", "description", "country", "category", "source", "frequency", "unit", "is_active"],
        )
        db.flush()

    indicators = db.query(Indicator).filter(Indicator.code.in_(codes)).all()
    return {indicator.code: indicator for indicator in indicators}


def upsert_indicator_observations(
    db: Session,
    rows: list[dict[str, object]],
) -> None:
    if not rows:
        return

    indicator_map = ensure_indicators(db, [str(row["series_key"]) for row in rows])
    payload = []
    for row in rows:
        series_key = str(row["series_key"])
        indicator = indicator_map.get(series_key)
        if indicator is None:
            continue
        payload.append(
            {
                "indicator_id": indicator.id,
                "date": _normalize_observation_date(row["date"]),
                "value": float(row["value"]),
            }
        )

    upsert_rows(
        db,
        Observation,
        payload,
        conflict_columns=["indicator_id", "date"],
        update_columns=["value"],
    )


def _normalize_observation_date(value: object) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value).date()
    raise TypeError(f"Unsupported observation date value: {value!r}")
