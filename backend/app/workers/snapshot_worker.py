"""
Change Snapshot Worker — calculates delta and Z-score for all indicators daily.
Runs after all collectors finish.
"""
import logging
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from ..models.indicators import (
    InterestRate, MacroIndicator, CreditSpread,
    EquityIndex, SectorPerformance, ExchangeRate,
    RealEconomyIndicator, ChangeSnapshot
)

logger = logging.getLogger(__name__)

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

    # --- Interest Rates ---
    for key in ["DFF", "DGS2", "DGS10", "DGS30", "T10Y2Y", "SOFR"]:
        rows = db.query(InterestRate).filter(
            InterestRate.series_key == key,
            InterestRate.date >= cutoff
        ).order_by(InterestRate.date).all()
        if not rows:
            continue
        history = [r.value for r in rows]
        labels = {"DFF": "기준금리", "DGS2": "2Y 국채", "DGS10": "10Y 국채",
                  "DGS30": "30Y 국채", "T10Y2Y": "10Y-2Y 스프레드", "SOFR": "SOFR"}
        _build_snapshot(db, today, key, labels.get(key, key), "rates", history[-1], history, "%")

    # --- Macro ---
    for key, label in {"CPIAUCSL": "CPI", "PCEPILFE": "Core PCE",
                       "UNRATE": "실업률", "ICSA": "실업수당 청구",
                       "USSLIND": "LEI", "M2SL": "M2 통화량"}.items():
        rows = db.query(MacroIndicator).filter(
            MacroIndicator.series_key == key,
            MacroIndicator.date >= cutoff
        ).order_by(MacroIndicator.date).all()
        if not rows:
            continue
        history = [r.value for r in rows]
        _build_snapshot(db, today, key, label, "macro", history[-1], history)

    # --- Credit Spreads ---
    for key, label in {"HY_OAS": "HY 크레딧 스프레드", "IG_OAS": "IG 크레딧 스프레드"}.items():
        rows = db.query(CreditSpread).filter(
            CreditSpread.series_key == key,
            CreditSpread.date >= cutoff
        ).order_by(CreditSpread.date).all()
        if not rows:
            continue
        history = [r.value for r in rows]
        _build_snapshot(db, today, key, label, "credit", history[-1], history, "bp")

    # --- Equity ---
    for ticker, label in {
        "^GSPC": "S&P 500",
        "^IXIC": "NASDAQ",
        "^KS11": "KOSPI",
        "^N225": "Nikkei 225",
        "^GDAXI": "DAX",
        "^SSEC": "Shanghai",
        "^VIX": "VIX",
        "DX-Y.NYB": "DXY",
        "CL=F": "WTI 원유",
        "GC=F": "금",
        "HG=F": "구리",
    }.items():
        rows = db.query(EquityIndex).filter(
            EquityIndex.ticker == ticker,
            EquityIndex.date >= cutoff
        ).order_by(EquityIndex.date).all()
        if not rows:
            continue
        history = [r.close for r in rows]
        _build_snapshot(db, today, ticker, label, "equity", history[-1], history)

    # --- FX ---
    for pair in ["USDKRW", "EURUSD", "USDJPY"]:
        rows = db.query(ExchangeRate).filter(
            ExchangeRate.pair == pair,
            ExchangeRate.date >= cutoff
        ).order_by(ExchangeRate.date).all()
        if not rows:
            continue
        history = [r.value for r in rows]
        _build_snapshot(db, today, pair, pair, "fx", history[-1], history)

    # --- Real Economy ---
    for key, label in {"COPPER_GOLD": "구리/금 비율", "WTI_BRENT_SPREAD": "WTI-Brent 스프레드"}.items():
        rows = db.query(RealEconomyIndicator).filter(
            RealEconomyIndicator.series_key == key,
            RealEconomyIndicator.date >= cutoff
        ).order_by(RealEconomyIndicator.date).all()
        if not rows:
            continue
        history = [r.value for r in rows]
        _build_snapshot(db, today, key, label, "real", history[-1], history)

    try:
        db.commit()
        logger.info("Change snapshots computed successfully")
    except Exception as e:
        db.rollback()
        logger.error(f"Snapshot commit failed: {e}")
