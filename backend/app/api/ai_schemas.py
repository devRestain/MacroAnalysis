from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class AiChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str


class AiChatResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reply: str


class AiSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    summary_date: str
    summary_type: str
    target_key: str | None = None
    headline: str | None = None
    body: str | None = None
    model_used: str | None = None
    metadata: dict = {}
