"""
Change Snapshot Worker — calculates delta and Z-score for all indicators daily.
Runs after all collectors finish.
"""
import logging
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from ..models import ChangeSnapshot
from ..services.observation_query_service import (
    get_observation_history,
)

logger = logging.getLogger(__name__)

RATES_CONFIG = {
    "DFF": {"label": "기준금리", "category": "rates", "unit": "%"},
    "DGS2": {"label": "2Y 국채", "category": "rates", "unit": "%"},
    "DGS10": {"label": "10Y 국채", "category": "rates", "unit": "%"},
    "DGS30": {"label": "30Y 국채", "category": "rates", "unit": "%"},
    "T10Y2Y": {"label": "10Y-2Y 스프레드", "category": "rates", "unit": "%"},
    "SOFR": {"label": "SOFR", "category": "rates", "unit": "%"},
}

MACRO_CONFIG = {
    "CPIAUCSL": {"label": "CPI", "category": "macro"},
    "PCEPILFE": {"label": "Core PCE", "category": "macro"},
    "UNRATE": {"label": "실업률", "category": "macro"},
    "ICSA": {"label": "실업수당 청구", "category": "macro"},
    "USSLIND": {"label": "LEI", "category": "macro"},
    "M2SL": {"label": "M2 통화량", "category": "macro"},
}

CREDIT_CONFIG = {
    "HY_OAS": {"label": "HY 크레딧 스프레드", "category": "credit", "unit": "bp"},
    "IG_OAS": {"label": "IG 크레딧 스프레드", "category": "credit", "unit": "bp"},
}

EQUITY_CONFIG = {
    "^GSPC": {"label": "S&P 500", "category": "equity"},
    "^IXIC": {"label": "NASDAQ", "category": "equity"},
    "^KS11": {"label": "KOSPI", "category": "equity"},
    "^N225": {"label": "Nikkei 225", "category": "equity"},
    "^GDAXI": {"label": "DAX", "category": "equity"},
    "^SSEC": {"label": "Shanghai", "category": "equity"},
    "^VIX": {"label": "VIX", "category": "equity"},
    "DX-Y.NYB": {"label": "DXY", "category": "equity"},
    "CL=F": {"label": "WTI 원유", "category": "equity"},
    "GC=F": {"label": "금", "category": "equity"},
    "HG=F": {"label": "구리", "category": "equity"},
}

FX_CONFIG = {
    "USDKRW": {"label": "USDKRW", "category": "fx"},
    "EURUSD": {"label": "EURUSD", "category": "fx"},
    "USDJPY": {"label": "USDJPY", "category": "fx"},
}

REAL_CONFIG = {
    "COPPER_GOLD": {"label": "구리/금 비율", "category": "real"},
    "WTI_BRENT_SPREAD": {"label": "WTI-Brent 스프레드", "category": "real"},
}

SIGNAL_THRESHOLDS = {
    # key: (lower_z_red, upper_z_red)  — outside this = red
    "default": (-1.5, 1.5),
    "HY_OAS": (0, 1.0),       # higher spread = worse, red on upside
    "VIX": (0, 1.2),
}


def _signal(z: float, key: str = "default") -> str:
    low, high = SIGNAL_THRESHOLDS.get(key, SIGNAL_THRESHOLDS["default"])
    if z > high or z < low:
        return "red"
    if abs(z) > 0.8:
        return "yellow"
    return "green"


def _direction(delta_pct: float | None) -> str:
    if delta_pct is None:
        return "flat"
    if delta_pct > 0.1:
        return "up"
    if delta_pct < -0.1:
        return "down"
    return "flat"


def _build_snapshot(
    db: Session, today: datetime, key: str, label: str, category: str,
    current: float, history: list[float], unit: str = ""
):
    history = [float(v) for v in history if v is not None]
    if current is None or not history:
        return
    current = float(current)

    def pct(h_val):
        if h_val is None or h_val == 0:
            return None
        return (current - h_val) / abs(h_val) * 100

    def delta(h_val):
        if h_val is None:
            return None
        return current - h_val

    # Z-score over last 1 year of values
    z = 0.0
    if len(history) >= 10:
        arr = np.array(history, dtype=float)
        std = np.std(arr)
        z = float((current - np.mean(arr)) / std) if std > 0 else 0.0

    # 1D/1W/1M/3M approximate indices
    idx_1d = -2 if len(history) >= 2 else None
    idx_1w = -6 if len(history) >= 6 else None
    idx_1m = -22 if len(history) >= 22 else None
    idx_3m = -66 if len(history) >= 66 else None

    h1d = history[idx_1d] if idx_1d else None
    h1w = history[idx_1w] if idx_1w else None
    h1m = history[idx_1m] if idx_1m else None
    h3m = history[idx_3m] if idx_3m else None

    delta_1d = delta(h1d)
    delta_1d_pct = pct(h1d)

    # Upsert
    snap = db.query(ChangeSnapshot).filter(
        ChangeSnapshot.indicator_key == key,
        ChangeSnapshot.snapshot_date >= today.replace(hour=0, minute=0, second=0)
    ).first()

    data = dict(
        snapshot_date=today,
        indicator_key=key,
        label=label,
        category=category,
        current_value=current,
        unit=unit,
        delta_1d=delta_1d,
        delta_1d_pct=delta_1d_pct,
        delta_1w_pct=pct(h1w),
        delta_1m_pct=pct(h1m),
        delta_3m_pct=pct(h3m),
        z_score_1y=round(z, 3),
        direction=_direction(delta_1d_pct),
        signal=_signal(z, key),
    )
    if snap:
        for k, v in data.items():
            setattr(snap, k, v)
    else:
        db.add(ChangeSnapshot(**data))


def compute_snapshots(db: Session):
    today = datetime.now()
    cutoff = today - timedelta(days=400)

    for config_group in [
        RATES_CONFIG,
        MACRO_CONFIG,
        CREDIT_CONFIG,
        EQUITY_CONFIG,
        FX_CONFIG,
        REAL_CONFIG,
    ]:
        _compute_group_snapshots(db, today, cutoff, config_group)

    try:
        db.commit()
        logger.info("Change snapshots computed successfully")
    except Exception as e:
        db.rollback()
        logger.error(f"Snapshot commit failed: {e}")


def _compute_group_snapshots(
    db: Session,
    today: datetime,
    cutoff: datetime,
    config_group: dict[str, dict[str, str]],
):
    for series_key, config in config_group.items():
        history_payload = get_observation_history(db, series_key, start_date=cutoff.date(), limit=500)
        values = [point["value"] for point in history_payload["data"] if point["value"] is not None]
        if not values:
            continue

        _build_snapshot(
            db,
            today,
            series_key,
            history_payload["name"] or config["label"],
            history_payload["category"] or config["category"],
            values[-1],
            values,
            history_payload["unit"] or config.get("unit", ""),
        )
