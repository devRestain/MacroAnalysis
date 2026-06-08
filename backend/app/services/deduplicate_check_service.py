from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models.indicators import (
    CreditSpread,
    EquityIndex,
    ExchangeRate,
    FedWatch,
    InterestRate,
    MacroIndicator,
    RealEconomyIndicator,
    SectorPerformance,
)


DEDUP_TABLES = [
    (InterestRate, ["series_key", "date"]),
    (MacroIndicator, ["series_key", "date"]),
    (CreditSpread, ["series_key", "date"]),
    (EquityIndex, ["ticker", "date"]),
    (SectorPerformance, ["ticker", "date"]),
    (ExchangeRate, ["pair", "date"]),
    (RealEconomyIndicator, ["series_key", "date"]),
    (FedWatch, ["meeting_date", "date"]),
]


def check_duplicate_candidates(db: Session, *, sample_limit: int = 3) -> dict:
    results = []
    total_groups = 0
    for model, key_columns in DEDUP_TABLES:
        key_attrs = [getattr(model, key) for key in key_columns]
        duplicate_groups = (
            db.query(*key_attrs, func.count(model.id).label("duplicate_count"))
            .group_by(*key_attrs)
            .having(func.count(model.id) > 1)
            .order_by(func.count(model.id).desc())
            .all()
        )
        sample = []
        for row in duplicate_groups[:sample_limit]:
            row_map = {key: getattr(row, key) for key in key_columns}
            row_map["duplicate_count"] = int(row.duplicate_count)
            sample.append(row_map)
        duplicate_group_count = len(duplicate_groups)
        total_groups += duplicate_group_count
        results.append(
            {
                "table_name": model.__tablename__,
                "key_columns": key_columns,
                "duplicate_group_count": duplicate_group_count,
                "sample": sample,
            }
        )
    return {
        "total_duplicate_groups": total_groups,
        "tables": results,
    }
