from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class AiChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str


class AiChatResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reply: str
