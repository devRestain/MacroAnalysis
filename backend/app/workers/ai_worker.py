"""AI insight worker helpers."""
import logging

from openai import OpenAI
from sqlalchemy.orm import Session

from ..core.config import settings
from ..services.daily_insight_service import ensure_daily_insight
from ..services.observation_query_service import get_ai_context_payload

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """당신은 거시경제 분석 전문가입니다.
한국어로 간결하지만 실무적으로 유의미한 설명을 제공합니다."""


def generate_daily_summary(db: Session):
    """Backward-compatible wrapper for older manual paths."""
    return ensure_daily_insight(db, force=True)


def chat_with_context(db: Session, user_message: str) -> str:
    """Single-turn chat with macro context injected."""
    ctx = get_ai_context_payload(db, None)
    observation_lines = "\n".join(
        [
            f"- {item['name'] or item['series_key']} ({item['series_key']}): {item['latest_value']}{item.get('unit') or ''}"
            for item in ctx["series"]
            if item["latest_value"] is not None
        ]
    ) or "- 데이터 없음"
    context_block = f"현재 관측 데이터:\n{observation_lines}"

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=settings.AI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT + "\n\n현재 데이터:\n" + context_block},
            {"role": "user", "content": user_message},
        ],
        max_tokens=800,
        temperature=0.5,
        stream=False,
    )
    return response.choices[0].message.content
