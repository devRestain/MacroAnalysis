from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class SentimentSignalResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    batch_date: str
    source_type: str
    source_id: int
    actor: str
    dimension: str
    stance: str
    stance_score: float
    intensity: float
    confidence: float
    evidence: str | None = None


class SentimentSignalListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    signals: list[SentimentSignalResponse]
    count: int
