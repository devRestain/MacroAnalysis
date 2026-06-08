from __future__ import annotations

import hashlib
import json
import logging
import threading
import zlib
from contextlib import contextmanager
from datetime import UTC, date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from openai import OpenAI
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..core.config import settings
from ..models.indicators import DailyInsight, FedWatch, FomcEvent, NewsItem
from .observation_query_service import get_ai_context_payload

logger = logging.getLogger(__name__)

KST = ZoneInfo("Asia/Seoul")
_LOCAL_LOCK = threading.Lock()
_LOCKED_DATES: set[str] = set()

SYSTEM_PROMPT = """당신은 거시경제 분석 전문가입니다.
주어진 관측 데이터와 뉴스 맥락을 바탕으로 KST 기준 당일 시사점을 간결하게 정리하세요.
반드시 JSON으로 응답하며 summary, key_points, risks, opportunities 필드를 포함하세요."""


def get_today_kst() -> date:
    return datetime.now(KST).date()


def get_existing_daily_insight(db: Session, as_of_date) -> DailyInsight | None:
    normalized_date = _normalize_date(as_of_date) or get_today_kst()
    return (
        db.query(DailyInsight)
        .filter(DailyInsight.as_of_date == normalized_date)
        .first()
    )


def build_ai_context_from_observations(db: Session, as_of_date) -> dict[str, Any]:
    normalized_date = _normalize_date(as_of_date) or get_today_kst()
    observation_payload = get_ai_context_payload(db, normalized_date)
    series = observation_payload["series"]

    observation_max_updated_at = max(
        (
            _normalize_datetime(item.get("updated_at"))
            for item in series
            if item.get("updated_at") is not None
        ),
        default=None,
    )
    available_series = [item for item in series if item.get("latest_value") is not None]

    observation_lines = [
        (
            f"- {item['name'] or item['series_key']} ({item['series_key']}): {item['latest_value']}"
            f"{item.get('unit') or ''} | 변화율: {_fmt_pct(item.get('delta_pct'))}"
            f" | 기준일: {item.get('latest_date')}"
        )
        for item in available_series
    ]

    day_start = datetime.combine(normalized_date, datetime.min.time()).replace(tzinfo=KST)
    prev_start = day_start - timedelta(days=1)
    news_items = (
        db.query(NewsItem)
        .filter(NewsItem.published_at >= prev_start.replace(tzinfo=None))
        .order_by(NewsItem.published_at.desc())
        .limit(10)
        .all()
    )
    news_lines = [f"- [{item.source}] {item.title}" for item in news_items]

    next_fomc = (
        db.query(FomcEvent)
        .filter(FomcEvent.meeting_date >= datetime.now().replace(microsecond=0))
        .order_by(FomcEvent.meeting_date)
        .first()
    )
    latest_fw = db.query(FedWatch).order_by(FedWatch.date.desc()).first()
    fomc_text = "없음"
    if next_fomc:
        fomc_text = f"다음 FOMC: {next_fomc.meeting_date.strftime('%Y.%m.%d')}"
        if latest_fw and all(
            value is not None for value in [latest_fw.prob_hold, latest_fw.prob_cut, latest_fw.prob_hike]
        ):
            fomc_text += (
                f" | 동결 {latest_fw.prob_hold * 100:.0f}%"
                f" / 인하 {latest_fw.prob_cut * 100:.0f}%"
                f" / 인상 {latest_fw.prob_hike * 100:.0f}%"
            )

    context_lines = [f"기준일: {normalized_date.isoformat()}", "관측 데이터:"]
    context_lines.extend(observation_lines or ["- 데이터 부족"])
    context_lines.append("최근 뉴스:")
    context_lines.extend(news_lines or ["- 뉴스 없음"])
    context_lines.append(f"FOMC: {fomc_text}")
    context_text = "\n".join(context_lines)

    return {
        "as_of_date": normalized_date,
        "series": series,
        "available_series_count": len(available_series),
        "context_text": context_text,
        "source_observation_max_updated_at": observation_max_updated_at,
        "prompt_hash": hashlib.sha256(context_text.encode("utf-8")).hexdigest(),
    }


def ensure_daily_insight(db: Session, as_of_date=None, force: bool = False) -> DailyInsight | dict[str, Any]:
    normalized_date = _normalize_date(as_of_date) or get_today_kst()
    if not force:
        existing = get_existing_daily_insight(db, normalized_date)
        if existing and existing.status == "success":
            return existing

    with _insight_lock(db, normalized_date) as lock_info:
        if not lock_info["acquired"]:
            return {
                "as_of_date": normalized_date.isoformat(),
                "status": "existing_check_later",
                "reason": "lock_not_acquired",
            }

        existing = get_existing_daily_insight(db, normalized_date)
        if existing and existing.status == "success" and not force:
            return existing

        context = build_ai_context_from_observations(db, normalized_date)
        try:
            insight_payload = _generate_daily_insight_payload(context)
            row = _upsert_daily_insight(
                db,
                normalized_date,
                model=insight_payload["model"],
                summary=insight_payload["summary"],
                key_points=insight_payload["key_points"],
                risks=insight_payload["risks"],
                opportunities=insight_payload["opportunities"],
                source_observation_max_updated_at=context["source_observation_max_updated_at"],
                prompt_hash=context["prompt_hash"],
                status="success",
                error_message=None,
            )
            return row
        except Exception as exc:
            logger.exception("Daily insight generation failed for %s", normalized_date)
            _upsert_daily_insight(
                db,
                normalized_date,
                model=settings.AI_MODEL,
                summary=None,
                key_points=[],
                risks=[],
                opportunities=[],
                source_observation_max_updated_at=context["source_observation_max_updated_at"],
                prompt_hash=context["prompt_hash"],
                status="failed",
                error_message=str(exc),
            )
            raise


def _generate_daily_insight_payload(context: dict[str, Any]) -> dict[str, Any]:
    if context["available_series_count"] == 0:
        return _fallback_insight_payload(context, reason="observation_data_missing")

    if not settings.OPENAI_API_KEY:
        return _fallback_insight_payload(context, reason="openai_not_configured")

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=settings.AI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "아래 컨텍스트를 기반으로 JSON만 반환하세요.\n"
                    f"{context['context_text']}\n"
                    '형식: {"summary": "...", "key_points": ["..."], "risks": ["..."], "opportunities": ["..."]}'
                ),
            },
        ],
        max_tokens=900,
        temperature=0.3,
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content or "{}"
    data = json.loads(content)
    return {
        "model": settings.AI_MODEL,
        "summary": data.get("summary") or "당일 관측 데이터를 기반으로 생성된 시사점이 없습니다.",
        "key_points": _normalize_list(data.get("key_points")),
        "risks": _normalize_list(data.get("risks")),
        "opportunities": _normalize_list(data.get("opportunities")),
    }


def _fallback_insight_payload(context: dict[str, Any], reason: str) -> dict[str, Any]:
    if reason == "observation_data_missing":
        summary = "오늘 KST 기준 관측 데이터가 충분하지 않아 자동 시사점을 간략 fallback 형태로 저장했습니다."
        key_points = ["관측 데이터가 부족해 정교한 시사점 생성 대신 fallback insight를 저장했습니다."]
    else:
        summary = "OpenAI 구성이 없어 오늘 KST 기준 fallback 시사점을 저장했습니다."
        key_points = ["OpenAI 호출 없이 관측 데이터 기반 fallback summary를 저장했습니다."]

    return {
        "model": settings.AI_MODEL,
        "summary": summary,
        "key_points": key_points,
        "risks": ["실제 데이터 업데이트가 늦어질 경우 판단 근거가 제한될 수 있습니다."],
        "opportunities": ["다음 batch 또는 수동 재실행 시 더 풍부한 insight로 갱신할 수 있습니다."],
    }


def _upsert_daily_insight(
    db: Session,
    as_of_date: date,
    *,
    model: str | None,
    summary: str | None,
    key_points: list[str],
    risks: list[str],
    opportunities: list[str],
    source_observation_max_updated_at: datetime | None,
    prompt_hash: str | None,
    status: str,
    error_message: str | None,
) -> DailyInsight:
    row = get_existing_daily_insight(db, as_of_date)
    if row is None:
        row = DailyInsight(as_of_date=as_of_date)
        db.add(row)

    row.model = model
    row.summary = summary
    row.key_points = key_points
    row.risks = risks
    row.opportunities = opportunities
    row.source_observation_max_updated_at = source_observation_max_updated_at
    row.prompt_hash = prompt_hash
    row.status = status
    row.error_message = error_message
    db.commit()
    db.refresh(row)
    return row


@contextmanager
def _insight_lock(db: Session, as_of_date: date):
    lock_key = f"daily_insight:{as_of_date.isoformat()}"
    if db.get_bind().dialect.name == "postgresql":
        lock_id = int(zlib.crc32(lock_key.encode("utf-8")))
        acquired = bool(
            db.execute(text("SELECT pg_try_advisory_lock(:lock_id)"), {"lock_id": lock_id}).scalar()
        )
        try:
            yield {"acquired": acquired}
        finally:
            if acquired:
                db.execute(text("SELECT pg_advisory_unlock(:lock_id)"), {"lock_id": lock_id})
                db.commit()
        return

    acquired = False
    with _LOCAL_LOCK:
        if lock_key not in _LOCKED_DATES:
            _LOCKED_DATES.add(lock_key)
            acquired = True
    try:
        yield {"acquired": acquired}
    finally:
        if acquired:
            with _LOCAL_LOCK:
                _LOCKED_DATES.discard(lock_key)


def daily_insight_to_summary_response(row: DailyInsight) -> dict[str, Any]:
    return {
        "date": row.as_of_date.isoformat(),
        "headline": _headline_from_summary(row.summary),
        "body": row.summary or "시사점이 아직 생성되지 않았습니다.",
        "model": row.model or settings.AI_MODEL,
        "status": row.status,
    }


def _headline_from_summary(summary: str | None) -> str | None:
    if not summary:
        return None
    first_line = summary.splitlines()[0].strip()
    if len(first_line) <= 200:
        return first_line
    return first_line[:197] + "..."


def _normalize_date(value) -> date | None:
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


def _normalize_datetime(value) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return None


def _normalize_list(value) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return []


def _fmt_pct(value: float | None) -> str:
    return "N/A" if value is None else f"{value:+.1f}%"
