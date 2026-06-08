from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..core.config import settings
from ..models.indicators import (
    CreditSpread,
    EquityIndex,
    ExchangeRate,
    Indicator,
    InterestRate,
    MacroIndicator,
    Observation,
    RealEconomyIndicator,
    SectorPerformance,
)


DASHBOARD_EQUITY_KEYS = [
    "^GSPC",
    "^IXIC",
    "^KS11",
    "^N225",
    "^GDAXI",
    "^SSEC",
    "^VIX",
    "DX-Y.NYB",
    "CL=F",
    "GC=F",
    "HG=F",
]

YIELD_CURVE_KEYS = ["DGS2", "DGS10", "DGS30", "T10Y2Y"]

SECTOR_SERIES = {
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

AI_CONTEXT_SERIES_KEYS = [
    "DFF",
    "DGS2",
    "DGS10",
    "DGS30",
    "T10Y2Y",
    "SOFR",
    "CPIAUCSL",
    "PCEPILFE",
    "UNRATE",
    "ICSA",
    "USSLIND",
    "M2SL",
    "HY_OAS",
    "IG_OAS",
    "^GSPC",
    "^IXIC",
    "^KS11",
    "^VIX",
    "DX-Y.NYB",
    "CL=F",
    "GC=F",
    "HG=F",
    "USDKRW",
    "EURUSD",
    "USDJPY",
    "COPPER_GOLD",
    "WTI_BRENT_SPREAD",
]

LEGACY_SERIES_SOURCES = {
    "DFF": (InterestRate, "series_key", "value", "date"),
    "DGS2": (InterestRate, "series_key", "value", "date"),
    "DGS10": (InterestRate, "series_key", "value", "date"),
    "DGS30": (InterestRate, "series_key", "value", "date"),
    "T10Y2Y": (InterestRate, "series_key", "value", "date"),
    "SOFR": (InterestRate, "series_key", "value", "date"),
    "CPIAUCSL": (MacroIndicator, "series_key", "value", "date"),
    "PCEPILFE": (MacroIndicator, "series_key", "value", "date"),
    "GDPC1": (MacroIndicator, "series_key", "value", "date"),
    "UNRATE": (MacroIndicator, "series_key", "value", "date"),
    "ICSA": (MacroIndicator, "series_key", "value", "date"),
    "M2SL": (MacroIndicator, "series_key", "value", "date"),
    "USSLIND": (MacroIndicator, "series_key", "value", "date"),
    "MANEMP": (MacroIndicator, "series_key", "value", "date"),
    "HY_OAS": (CreditSpread, "series_key", "value", "date"),
    "IG_OAS": (CreditSpread, "series_key", "value", "date"),
    "^GSPC": (EquityIndex, "ticker", "close", "date"),
    "^IXIC": (EquityIndex, "ticker", "close", "date"),
    "^KS11": (EquityIndex, "ticker", "close", "date"),
    "^N225": (EquityIndex, "ticker", "close", "date"),
    "^GDAXI": (EquityIndex, "ticker", "close", "date"),
    "^SSEC": (EquityIndex, "ticker", "close", "date"),
    "^VIX": (EquityIndex, "ticker", "close", "date"),
    "DX-Y.NYB": (EquityIndex, "ticker", "close", "date"),
    "CL=F": (EquityIndex, "ticker", "close", "date"),
    "GC=F": (EquityIndex, "ticker", "close", "date"),
    "HG=F": (EquityIndex, "ticker", "close", "date"),
    "USDKRW": (ExchangeRate, "pair", "value", "date"),
    "EURUSD": (ExchangeRate, "pair", "value", "date"),
    "USDJPY": (ExchangeRate, "pair", "value", "date"),
    "COPPER_GOLD": (RealEconomyIndicator, "series_key", "value", "date"),
    "WTI_BRENT_SPREAD": (RealEconomyIndicator, "series_key", "value", "date"),
    "XLK": (SectorPerformance, "ticker", "close", "date"),
    "XLF": (SectorPerformance, "ticker", "close", "date"),
    "XLE": (SectorPerformance, "ticker", "close", "date"),
    "XLV": (SectorPerformance, "ticker", "close", "date"),
    "XLI": (SectorPerformance, "ticker", "close", "date"),
    "XLY": (SectorPerformance, "ticker", "close", "date"),
    "XLP": (SectorPerformance, "ticker", "close", "date"),
    "XLU": (SectorPerformance, "ticker", "close", "date"),
    "XLB": (SectorPerformance, "ticker", "close", "date"),
    "XLRE": (SectorPerformance, "ticker", "close", "date"),
    "XLC": (SectorPerformance, "ticker", "close", "date"),
}


def get_latest_observations(db: Session, series_keys: list[str]) -> list[dict[str, Any]]:
    if not series_keys:
        return []

    indicators = (
        db.query(Indicator)
        .filter(Indicator.code.in_(series_keys))
        .all()
    )
    indicator_map = {indicator.code: indicator for indicator in indicators}
    latest_rows = _get_latest_observation_map(db, [indicator.id for indicator in indicators])

    results: list[dict[str, Any]] = []
    for series_key in series_keys:
        indicator = indicator_map.get(series_key)
        latest = latest_rows.get(indicator.id) if indicator else None
        if indicator or latest:
            results.append(_build_series_payload(series_key, indicator, latest))
            continue

        legacy_payload = _legacy_latest_payload(db, series_key)
        if legacy_payload:
            results.append(legacy_payload)
            continue

        results.append(_missing_payload(series_key))
    return results


def get_observation_history(
    db: Session,
    series_key: str,
    start_date=None,
    end_date=None,
    limit: int = 500,
) -> dict[str, Any]:
    indicator = db.query(Indicator).filter(Indicator.code == series_key).first()
    if indicator:
        q = db.query(Observation).filter(Observation.indicator_id == indicator.id)
        start_dt = _to_date(start_date)
        end_dt = _to_date(end_date)
        if start_dt:
            q = q.filter(Observation.date >= start_dt)
        if end_dt:
            q = q.filter(Observation.date <= end_dt)

        rows = q.order_by(Observation.date.desc(), Observation.id.desc()).limit(limit).all()
        rows.reverse()
        latest = rows[-1] if rows else None
        payload = _build_series_payload(series_key, indicator, latest)
        payload["data"] = [_observation_point(row) for row in rows]
        return payload

    legacy_payload = _legacy_history_payload(db, series_key, start_date=start_date, end_date=end_date, limit=limit)
    if legacy_payload:
        return legacy_payload

    payload = _missing_payload(series_key)
    payload["data"] = []
    return payload


def get_latest_by_category(db: Session, category: str) -> list[dict[str, Any]]:
    indicators = (
        db.query(Indicator)
        .filter(Indicator.category == category)
        .order_by(Indicator.code.asc())
        .all()
    )
    latest_rows = _get_latest_observation_map(db, [indicator.id for indicator in indicators])
    return [
        _build_series_payload(indicator.code, indicator, latest_rows.get(indicator.id))
        for indicator in indicators
    ]


def get_dashboard_observation_payload(db: Session) -> dict[str, Any]:
    latest_items = get_latest_observations(
        db,
        DASHBOARD_EQUITY_KEYS + YIELD_CURVE_KEYS + list(SECTOR_SERIES.keys()),
    )
    latest_map = {item["series_key"]: item for item in latest_items}

    sectors = []
    for series_key, default_name in SECTOR_SERIES.items():
        history = get_observation_history(db, series_key, limit=400)
        if history["status"] == "missing" and history["name"] is None:
            continue
        sectors.append(adapt_sector_history_to_response(history, default_name=default_name))

    return {
        "series": latest_map,
        "equities": adapt_latest_to_equities_payload(latest_map, DASHBOARD_EQUITY_KEYS),
        "yield_curve": adapt_latest_to_yield_curve_payload(latest_map, YIELD_CURVE_KEYS),
        "sectors": sectors,
    }


def get_ai_context_payload(db: Session, as_of_date) -> dict[str, Any]:
    as_of = _to_date(as_of_date) or datetime.now().date()
    series_payloads = []
    for series_key in AI_CONTEXT_SERIES_KEYS:
        history = get_observation_history(db, series_key, end_date=as_of, limit=8)
        previous_value = history["data"][-2]["value"] if len(history["data"]) >= 2 else None
        latest_value = history["latest_value"]
        delta_pct = None
        if previous_value not in (None, 0) and latest_value is not None:
            delta_pct = (float(latest_value) - float(previous_value)) / abs(float(previous_value)) * 100
        history["previous_value"] = previous_value
        history["delta_pct"] = delta_pct
        series_payloads.append(history)

    return {
        "as_of_date": as_of.isoformat(),
        "series": series_payloads,
    }


def adapt_latest_to_equities_payload(
    latest_map: dict[str, dict[str, Any]],
    series_keys: list[str] | None = None,
) -> dict[str, dict[str, Any]]:
    result = {}
    for series_key in series_keys or DASHBOARD_EQUITY_KEYS:
        item = latest_map.get(series_key)
        if not item or item["latest_value"] is None or item["latest_date"] is None:
            continue
        result[series_key] = {
            "close": float(item["latest_value"]),
            "change_pct": item.get("change_pct"),
            "date": str(item["latest_date"]),
        }
    return result


def adapt_latest_to_yield_curve_payload(
    latest_map: dict[str, dict[str, Any]],
    series_keys: list[str] | None = None,
) -> dict[str, float]:
    result = {}
    for series_key in series_keys or YIELD_CURVE_KEYS:
        item = latest_map.get(series_key)
        if item and item["latest_value"] is not None:
            result[series_key] = float(item["latest_value"])
    return result


def adapt_history_to_chart_response(history_payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "indicator_key": history_payload["series_key"],
        "period": history_payload.get("period"),
        "data": history_payload["data"],
    }


def adapt_sector_history_to_response(history_payload: dict[str, Any], default_name: str | None = None) -> dict[str, Any]:
    values = [point["value"] for point in history_payload["data"] if point["value"] is not None]
    latest_date = history_payload["latest_date"]

    def pct(offset: int) -> float | None:
        if len(values) <= offset:
            return None
        base = values[-1 - offset]
        if base in (None, 0):
            return None
        return (float(values[-1]) - float(base)) / abs(float(base)) * 100

    change_ytd = None
    if latest_date and values:
        latest_date_obj = _to_date(latest_date)
        ytd_points = [
            point for point in history_payload["data"]
            if _to_date(point["date"]) and _to_date(point["date"]).year == latest_date_obj.year and point["value"] is not None
        ]
        if ytd_points:
            ytd_base = ytd_points[0]["value"]
            if ytd_base not in (None, 0):
                change_ytd = (float(values[-1]) - float(ytd_base)) / abs(float(ytd_base)) * 100

    return {
        "ticker": history_payload["series_key"],
        "name": history_payload["name"] or default_name or history_payload["series_key"],
        "change_1d": pct(1),
        "change_1m": pct(21),
        "change_3m": pct(63),
        "change_ytd": change_ytd,
        "date": str(latest_date) if latest_date is not None else "",
    }


def _get_latest_observation_map(db: Session, indicator_ids: list[int]) -> dict[int, Observation]:
    if not indicator_ids:
        return {}

    ranked = (
        db.query(
            Observation.id.label("id"),
            Observation.indicator_id.label("indicator_id"),
            func.row_number().over(
                partition_by=Observation.indicator_id,
                order_by=(Observation.date.desc(), Observation.id.desc()),
            ).label("row_num"),
        )
        .filter(Observation.indicator_id.in_(indicator_ids))
        .subquery()
    )

    rows = (
        db.query(Observation)
        .join(ranked, ranked.c.id == Observation.id)
        .filter(ranked.c.row_num == 1)
        .all()
    )
    return {row.indicator_id: row for row in rows}


def _build_series_payload(series_key: str, indicator: Indicator | None, latest: Observation | Any | None) -> dict[str, Any]:
    latest_value = None
    latest_date = None
    updated_at = indicator.updated_at if indicator else None
    status = "missing"

    if latest is not None:
        latest_value = getattr(latest, "value", None)
        latest_date = getattr(latest, "date", None)
        updated_at = getattr(latest, "created_at", None) or updated_at
        status = "ok"

    return {
        "series_key": series_key,
        "name": indicator.name if indicator else None,
        "category": indicator.category if indicator else None,
        "frequency": indicator.frequency if indicator else None,
        "unit": indicator.unit if indicator else None,
        "provider": indicator.source if indicator else None,
        "latest_value": latest_value,
        "latest_date": latest_date,
        "updated_at": updated_at,
        "value": latest_value,
        "status": status,
    }


def _missing_payload(series_key: str) -> dict[str, Any]:
    return {
        "series_key": series_key,
        "name": None,
        "category": None,
        "frequency": None,
        "unit": None,
        "provider": None,
        "latest_value": None,
        "latest_date": None,
        "updated_at": None,
        "value": None,
        "status": "missing",
    }


def _legacy_latest_payload(db: Session, series_key: str) -> dict[str, Any] | None:
    if not settings.LEGACY_TABLE_FALLBACK_ENABLED:
        return None

    source = LEGACY_SERIES_SOURCES.get(series_key)
    if not source:
        return None

    model, key_column, value_column, date_column = source
    row = (
        db.query(model)
        .filter(getattr(model, key_column) == series_key)
        .order_by(getattr(model, date_column).desc())
        .first()
    )
    if not row:
        return None

    return {
        "series_key": series_key,
        "name": series_key,
        "category": None,
        "frequency": None,
        "unit": None,
        "provider": f"legacy:{model.__tablename__}",
        "latest_value": getattr(row, value_column),
        "latest_date": getattr(row, date_column),
        "updated_at": getattr(row, "created_at", None),
        "value": getattr(row, value_column),
        "status": "legacy_fallback",
    }


def _legacy_history_payload(
    db: Session,
    series_key: str,
    start_date=None,
    end_date=None,
    limit: int = 500,
) -> dict[str, Any] | None:
    if not settings.LEGACY_TABLE_FALLBACK_ENABLED:
        return None

    source = LEGACY_SERIES_SOURCES.get(series_key)
    if not source:
        return None

    model, key_column, value_column, date_column = source
    q = db.query(model).filter(getattr(model, key_column) == series_key)
    start_dt = _to_date(start_date)
    end_dt = _to_date(end_date)
    if start_dt:
        q = q.filter(getattr(model, date_column) >= start_dt)
    if end_dt:
        q = q.filter(getattr(model, date_column) <= end_dt)

    rows = q.order_by(getattr(model, date_column).desc()).limit(limit).all()
    rows.reverse()
    if not rows:
        return None

    latest = rows[-1]
    return {
        "series_key": series_key,
        "name": series_key,
        "category": None,
        "frequency": None,
        "unit": None,
        "provider": f"legacy:{model.__tablename__}",
        "latest_value": getattr(latest, value_column),
        "latest_date": getattr(latest, date_column),
        "updated_at": getattr(latest, "created_at", None),
        "value": getattr(latest, value_column),
        "status": "legacy_fallback",
        "data": [
            {"date": str(getattr(row, date_column)), "value": float(getattr(row, value_column))}
            for row in rows
            if getattr(row, value_column) is not None
        ],
    }


def _observation_point(row: Observation) -> dict[str, Any]:
    return {
        "date": str(row.date),
        "value": float(row.value),
    }


def _to_date(value) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value).date()
        except ValueError:
            return None
    return None
