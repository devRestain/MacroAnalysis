"""
Sentiment Worker — v2 파이프라인
=================================
Layer 1 : 뉴스 배치 LLM 분류  (매일 22:00 UTC 일괄)
Layer 2 : Expectation 업데이트 (관성 모델 적용)
Layer 3 : Divergence 탐지
Layer 4 : 리포트 생성 (ALERT 등급)

Celery chain: extract_daily_sentiments → update_expectations → detect_divergence
Central-bank communication events are handled immediately through
extract_communication_event_sentiment.
"""

from __future__ import annotations

import json
import logging
import math
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

try:
    from celery import shared_task, chain
except ModuleNotFoundError:  # pragma: no cover - lightweight test fallback
    class _RetryableTaskContext:
        def retry(self, exc=None, countdown=None):
            raise exc or RuntimeError("retry requested")

    class _TaskWrapper:
        def __init__(self, fn, *, bind: bool):
            self._fn = fn
            self._bind = bind

        def _invoke(self, *args, **kwargs):
            if self._bind:
                return self._fn(_RetryableTaskContext(), *args, **kwargs)
            return self._fn(*args, **kwargs)

        def run(self, *args, **kwargs):
            return self._invoke(*args, **kwargs)

        def delay(self, *args, **kwargs):
            return self._invoke(*args, **kwargs)

        def s(self, *args, **kwargs):
            return lambda: self._invoke(*args, **kwargs)

        def __call__(self, *args, **kwargs):
            return self._invoke(*args, **kwargs)

    def shared_task(*args, **kwargs):
        def decorator(fn):
            return _TaskWrapper(fn, bind=bool(kwargs.get("bind")))
        return decorator

    class _ChainFallback:
        def __init__(self, *steps):
            self.steps = steps

        def apply_async(self, app=None):
            result = None
            for step in self.steps:
                result = step()
            return result

    def chain(*steps):
        return _ChainFallback(*steps)

try:
    from kombu.exceptions import OperationalError
except ModuleNotFoundError:  # pragma: no cover - lightweight test fallback
    class OperationalError(Exception):
        pass

from ..core.config import settings
from ..core.database import SessionLocal
from ..core.upsert import upsert_rows
from ..models import CommunicationEvent, DivergenceEvent, DivergenceReport, Expectation, FomcEventDetail, NewsItem, SentimentSignal

logger = logging.getLogger(__name__)

# ─── 상수 ─────────────────────────────────────────────────────────────────────

ACTORS = ["fed", "market", "consumer", "corporate", "geopolitical"]
DIMENSIONS = ["rates", "inflation", "growth", "liquidity", "risk_appetite", "policy"]

# 상수는 config에서 로드 (런타임 오버라이드 가능)
BATCH_SIZE = settings.SENTIMENT_BATCH_SIZE

# 관성 계수 파라미터
INERTIA_ALPHA = settings.INERTIA_ALPHA
INERTIA_BREAKOUT_GAP = 0.6    # 임계점 돌파 최소 괴리
INERTIA_BREAKOUT_ALIGNMENT = 0.8  # 신호 방향 일치도
INERTIA_BREAKOUT_CONSECUTIVE = 3  # 연속 일수

# Divergence 임계값
WARNING_THRESHOLD = settings.DIVERGENCE_WARNING_THRESHOLD
ALERT_THRESHOLD = settings.DIVERGENCE_ALERT_THRESHOLD

# severity_multiplier 승수
MULT_INERTIA_RESET = 1.5
MULT_MOMENTUM_FLIP = 1.2
MULT_MULTI_DIM     = 1.3
RELEVANT_NEWS_CATEGORIES = {"fed", "macro", "fx", "geopolitics", "commodity"}


def _normalize_batch_date(batch_date_iso: str | None = None, batch_date: datetime | None = None) -> datetime:
    base = batch_date or (
        datetime.fromisoformat(batch_date_iso)
        if batch_date_iso
        else datetime.now(timezone.utc).replace(tzinfo=None)
    )
    return base.replace(hour=0, minute=0, second=0, microsecond=0)


def _batch_window(batch_date: datetime) -> tuple[datetime, datetime]:
    return batch_date, batch_date + timedelta(days=1)


def _news_reference_time(item: NewsItem) -> datetime:
    return item.published_at or item.collected_at or datetime.min


def _is_sentiment_candidate(item: NewsItem) -> bool:
    return (item.category or "general") in RELEVANT_NEWS_CATEGORIES


def _count_recent_unprocessed_news(db: Session, batch_date: datetime) -> int:
    recent_cutoff = batch_date - timedelta(days=settings.SENTIMENT_LOOKBACK_DAYS)
    return (
        db.query(NewsItem)
        .filter(
            NewsItem.sentiment_extracted == False,  # noqa: E712
            or_(
                NewsItem.published_at.is_(None),
                NewsItem.published_at >= recent_cutoff,
            ),
        )
        .count()
    )


def _load_sentiment_news_batch(db: Session, batch_date: datetime) -> tuple[list[NewsItem], int]:
    recent_cutoff = batch_date - timedelta(days=settings.SENTIMENT_LOOKBACK_DAYS)
    rows = (
        db.query(NewsItem)
        .filter(
            NewsItem.sentiment_extracted == False,  # noqa: E712
            or_(
                NewsItem.published_at.is_(None),
                NewsItem.published_at >= recent_cutoff,
            ),
        )
        .order_by(NewsItem.published_at.asc(), NewsItem.id.asc())
        .all()
    )

    candidates: list[NewsItem] = []
    auto_marked_irrelevant = 0
    for row in rows:
        if not _is_sentiment_candidate(row):
            row.sentiment_extracted = True
            auto_marked_irrelevant += 1
            continue
        candidates.append(row)
        if len(candidates) >= settings.SENTIMENT_MAX_NEWS_ITEMS_PER_RUN:
            break

    if auto_marked_irrelevant:
        db.commit()

    return candidates, auto_marked_irrelevant


# ═══════════════════════════════════════════════════════════════════════════════
# Layer 1 : LLM 배치 Sentiment 추출
# ═══════════════════════════════════════════════════════════════════════════════

def _build_batch_prompt(items: list[dict]) -> str:
    """뉴스 배치 → sentiment 추출 프롬프트."""
    news_block = "\n".join(
        f"[{i+1}] title={it['title']!r} summary={it['summary']!r}"
        for i, it in enumerate(items)
    )
    return f"""You are a macro-economic sentiment classifier.
Analyze the following {len(items)} news items and extract sentiment signals.

For EACH news item, output ALL applicable actor×dimension combinations.
Return a JSON array of signal objects. Each object must have:
  - news_index: int (1-based)
  - actor: one of {ACTORS}
  - dimension: one of {DIMENSIONS}
  - stance: string label (e.g. "hawkish", "dovish", "optimistic", "pessimistic",
            "tightening", "easing", "risk_on", "risk_off", "neutral")
  - stance_score: float -1.0 to +1.0 (positive = hawkish/optimistic/risk_on)
  - intensity: float 0.0 to 1.0 (how strongly the article conveys this signal)
  - confidence: float 0.0 to 1.0 (your confidence in this classification)
  - evidence: string (1 sentence quoting/paraphrasing the key phrase)

If a news item has no macro-relevant sentiment, output nothing for it.
Return ONLY valid JSON, no markdown fences.

NEWS ITEMS:
{news_block}
"""


def _parse_batch_response(raw: str) -> list[dict]:
    """LLM 응답 JSON 파싱. 실패 시 빈 리스트."""
    try:
        # markdown fence 제거
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)
    except Exception as e:
        logger.warning(f"[sentiment] JSON parse failed: {e} — raw[:200]={raw[:200]}")
        return []


def _is_explicit_empty_array(raw: str) -> bool:
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return text.strip() == "[]"


def _call_llm(prompt: str) -> str:
    """OpenAI API 동기 호출 (Celery 워커 내부용)."""
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    import openai
    client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
    resp = client.chat.completions.create(
        model=settings.AI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=4096,
    )
    return resp.choices[0].message.content or ""


@shared_task(name="workers.extract_daily_sentiments", bind=True, max_retries=2)
def extract_daily_sentiments(self, batch_date_iso: str | None = None):
    """
    매일 22:00 UTC 실행.
    sentiment_extracted=False 인 미처리 뉴스를 BATCH_SIZE씩 LLM으로 분류.
    FOMC 발표문은 extract_fomc_sentiment 에서 별도 처리하므로 여기선 건너뜀.
    """
    batch_date = _normalize_batch_date(batch_date_iso)

    db: Session = SessionLocal()
    try:
        unprocessed, auto_marked_irrelevant = _load_sentiment_news_batch(db, batch_date)

        if not unprocessed:
            logger.info(
                "[sentiment] 분류 대상 뉴스 없음 — 배치 스킵 (auto_marked_irrelevant=%s)",
                auto_marked_irrelevant,
            )
            return {"processed": 0, "signals": 0, "auto_marked_irrelevant": auto_marked_irrelevant}

        total_signals = 0
        for batch_start in range(0, len(unprocessed), BATCH_SIZE):
            batch = unprocessed[batch_start : batch_start + BATCH_SIZE]
            items = [
                {"id": n.id, "title": n.title or "", "summary": n.summary or ""}
                for n in batch
            ]

            prompt = _build_batch_prompt(items)
            try:
                raw = _call_llm(prompt)
            except Exception as exc:
                logger.error(f"[sentiment] LLM 호출 실패 batch_start={batch_start}: {exc}")
                raise self.retry(exc=exc, countdown=60)

            signals = _parse_batch_response(raw)
            if raw.strip() and not signals and not _is_explicit_empty_array(raw):
                raise self.retry(exc=RuntimeError("sentiment_parse_failed"), countdown=60)

            # index → NewsItem.id 매핑
            idx_to_id = {i + 1: n.id for i, n in enumerate(batch)}
            signal_rows = []

            for sig in signals:
                news_id = idx_to_id.get(sig.get("news_index"))
                if not news_id:
                    continue
                actor = sig.get("actor", "")
                dimension = sig.get("dimension", "")
                if actor not in ACTORS or dimension not in DIMENSIONS:
                    continue

                signal_rows.append(
                    {
                        "source_type": "news",
                        "source_id": news_id,
                        "batch_date": batch_date,
                        "actor": actor,
                        "dimension": dimension,
                        "stance": sig.get("stance", "neutral"),
                        "stance_score": float(sig.get("stance_score", 0.0)),
                        "intensity": float(sig.get("intensity", 0.5)),
                        "confidence": float(sig.get("confidence", 0.5)),
                        "evidence": sig.get("evidence", ""),
                    }
                )

            upsert_rows(
                db,
                SentimentSignal,
                signal_rows,
                conflict_columns=["source_type", "source_id", "batch_date", "actor", "dimension", "stance"],
                update_columns=["stance_score", "intensity", "confidence", "evidence"],
            )
            total_signals += len(signal_rows)

            # 처리 완료 표시
            for n in batch:
                n.sentiment_extracted = True

            db.commit()
            logger.info(
                f"[sentiment] 배치 {batch_start//BATCH_SIZE + 1} 처리 완료 "
                f"({len(batch)}건 → {len(signals)}개 신호)"
            )

        logger.info(f"[sentiment] 일일 배치 완료: {len(unprocessed)}건 뉴스, {total_signals}개 신호")
        return {
            "processed": len(unprocessed),
            "signals": total_signals,
            "auto_marked_irrelevant": auto_marked_irrelevant,
        }

    finally:
        db.close()


@shared_task(name="workers.extract_communication_event_sentiment", bind=True, max_retries=3)
def extract_communication_event_sentiment(self, communication_event_id: int, text: str):
    """
    FOMC 발표문 / FED 연설 이벤트 기반 즉시 처리.
    fomc_collector 또는 news_collector 가 해당 이벤트 후 직접 호출.
    """
    db: Session = SessionLocal()
    try:
        batch_date = _normalize_batch_date()
        prompt = f"""You are a macro-economic sentiment classifier specializing in Fed communications.
Analyze the following Federal Reserve statement/speech and extract sentiment signals.

Return a JSON array of signal objects with fields:
  actor, dimension, stance, stance_score (-1.0 to +1.0), intensity (0-1),
  confidence (0-1), evidence (key phrase).

Actor should be "fed" for direct Fed views; also classify implied "market" reactions if stated.
Dimensions: {DIMENSIONS}

TEXT:
{text[:3000]}
"""
        try:
            raw = _call_llm(prompt)
        except Exception as exc:
            raise self.retry(exc=exc, countdown=30)

        signals = _parse_batch_response(raw)
        if raw.strip() and not signals and not _is_explicit_empty_array(raw):
            raise self.retry(exc=RuntimeError("sentiment_parse_failed"), countdown=30)
        signal_rows = []
        for sig in signals:
            actor = sig.get("actor", "fed")
            dimension = sig.get("dimension", "rates")
            if actor not in ACTORS or dimension not in DIMENSIONS:
                continue
            signal_rows.append(
                {
                    "source_type": "communication_event",
                    "source_id": communication_event_id,
                    "batch_date": batch_date,
                    "actor": actor,
                    "dimension": dimension,
                    "stance": sig.get("stance", "neutral"),
                    "stance_score": float(sig.get("stance_score", 0.0)),
                    "intensity": float(sig.get("intensity", 0.7)),
                    "confidence": float(sig.get("confidence", 0.8)),
                    "evidence": sig.get("evidence", ""),
                }
            )
        upsert_rows(
            db,
            SentimentSignal,
            signal_rows,
            conflict_columns=["source_type", "source_id", "batch_date", "actor", "dimension", "stance"],
            update_columns=["stance_score", "intensity", "confidence", "evidence"],
        )
        _mark_communication_event_sentiment_extracted(
            db,
            communication_event_id=communication_event_id,
            extracted_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        db.commit()
        logger.info(f"[sentiment] communication_event {communication_event_id} → {len(signal_rows)}개 신호")
        return {"signals": len(signal_rows)}
    finally:
        db.close()


@shared_task(name="workers.extract_fomc_sentiment", bind=True, max_retries=3)
def extract_fomc_sentiment(self, fomc_event_id: int, text: str):
    """Backward-compatible alias for older queues; expects a communication_event id now."""
    return extract_communication_event_sentiment.run(fomc_event_id, text)


def _mark_communication_event_sentiment_extracted(
    db: Session,
    *,
    communication_event_id: int,
    extracted_at: datetime,
) -> None:
    communication_event = db.query(CommunicationEvent).filter(CommunicationEvent.id == communication_event_id).first()
    if communication_event is None:
        return
    communication_event.sentiment_status = "success"
    communication_event.sentiment_extracted_at = extracted_at
    if communication_event.event_type == "fomc_meeting" and communication_event.meeting_date is not None:
        detail = (
            db.query(FomcEventDetail)
            .filter(FomcEventDetail.meeting_end_date == communication_event.meeting_date)
            .first()
        )
        if detail is not None:
            detail.sentiment_status = "success"
            detail.sentiment_extracted_at = extracted_at


# ═══════════════════════════════════════════════════════════════════════════════
# Layer 2 : Expectation 업데이트 (관성 모델)
# ═══════════════════════════════════════════════════════════════════════════════

def _compute_raw_score(signals: list[SentimentSignal]) -> tuple[float, float]:
    """
    신호들로부터 가중 평균 raw_score 와 consensus_strength 계산.
    가중치 = intensity × confidence.
    consensus_strength = 방향 일치 신호 비율.
    """
    if not signals:
        return 0.0, 0.0

    weighted_sum = 0.0
    weight_total = 0.0
    for s in signals:
        w = s.intensity * s.confidence
        weighted_sum += s.stance_score * w
        weight_total += w

    raw = weighted_sum / weight_total if weight_total > 0 else 0.0

    # consensus_strength: raw 방향과 같은 신호 비율
    dominant_sign = 1 if raw >= 0 else -1
    aligned = sum(1 for s in signals if (s.stance_score * dominant_sign) > 0)
    strength = aligned / len(signals) if signals else 0.0

    return round(raw, 4), round(strength, 4)


def _compute_inertia(
    age_days: float,
    strength: float,
    raw: float,
    prev_consensus: float,
    recent_raws: list[float],  # 최근 3일 raw (오늘 포함, 가장 오래된 것 먼저)
) -> tuple[float, bool]:
    """
    관성 계수와 임계점 돌파 여부 반환.

    Returns:
        (inertia_coefficient, is_reset)
    """
    gap = abs(raw - prev_consensus)

    # 임계점 돌파 조건
    if len(recent_raws) >= INERTIA_BREAKOUT_CONSECUTIVE:
        direction = math.copysign(1, raw - prev_consensus)
        same_dir = all(
            math.copysign(1, r - prev_consensus) == direction
            for r in recent_raws[-INERTIA_BREAKOUT_CONSECUTIVE:]
        )
        aligned_count = sum(
            1 for r in recent_raws[-INERTIA_BREAKOUT_CONSECUTIVE:]
            if math.copysign(1, r - prev_consensus) == direction
        )
        alignment_ratio = aligned_count / INERTIA_BREAKOUT_CONSECUTIVE

        if (
            gap >= INERTIA_BREAKOUT_GAP
            and alignment_ratio >= INERTIA_BREAKOUT_ALIGNMENT
            and same_dir
        ):
            return 0.0, True  # 관성 리셋

    coeff = math.tanh(INERTIA_ALPHA * age_days * strength)
    return round(coeff, 4), False


@shared_task(name="workers.update_expectations", bind=True)
def update_expectations(self, extract_result: dict | None = None, batch_date_iso: str | None = None):
    """
    오늘 배치에서 추출된 신호로 Expectation 테이블 upsert.
    Celery chain 에서 extract_daily_sentiments 다음에 실행.
    """
    batch_date = _normalize_batch_date(batch_date_iso)
    window_start, window_end = _batch_window(batch_date)
    db: Session = SessionLocal()
    try:
        # 오늘 배치 신호 로드
        today_signals = (
            db.query(SentimentSignal)
            .filter(
                SentimentSignal.batch_date >= window_start,
                SentimentSignal.batch_date < window_end,
            )
            .all()
        )

        if not today_signals:
            logger.info("[expectation] 오늘 신호 없음 — 스킵")
            return {"updated": 0}

        # actor × dimension 조합별 그룹화
        from collections import defaultdict
        groups: dict[tuple, list[SentimentSignal]] = defaultdict(list)
        for s in today_signals:
            groups[(s.actor, s.dimension)].append(s)

        updated = 0
        rows_to_upsert = []
        for (actor, dimension), sigs in groups.items():
            raw_score, strength = _compute_raw_score(sigs)

            # 어제 Expectation 로드 (관성 계산용)
            yesterday = batch_date - timedelta(days=1)
            prev_exp = (
                db.query(Expectation)
                .filter(
                    Expectation.actor == actor,
                    Expectation.dimension == dimension,
                    Expectation.date >= yesterday - timedelta(days=1),
                    Expectation.date < batch_date,
                )
                .order_by(Expectation.date.desc())
                .first()
            )

            if prev_exp is None:
                # 첫 번째 기록: 관성 없이 raw = consensus
                rows_to_upsert.append(
                    {
                        "date": batch_date,
                        "actor": actor,
                        "dimension": dimension,
                        "raw_score": raw_score,
                        "consensus_score": raw_score,
                        "consensus_strength": strength,
                        "inertia_age_days": 1.0,
                        "inertia_coefficient": 0.0,
                        "inertia_reset": False,
                        "consensus_7d_ago": None,
                        "momentum_score": None,
                    }
                )
            else:
                # 최근 3일 raw 수집 (모멘텀·관성 계산)
                recent = (
                    db.query(Expectation)
                    .filter(
                        Expectation.actor == actor,
                        Expectation.dimension == dimension,
                        Expectation.date >= batch_date - timedelta(days=4),
                        Expectation.date < batch_date,
                    )
                    .order_by(Expectation.date.asc())
                    .all()
                )
                recent_raws = [r.raw_score for r in recent] + [raw_score]

                # 방향 유지 일수 계산
                if (
                    prev_exp.inertia_reset
                    or math.copysign(1, raw_score) != math.copysign(1, prev_exp.raw_score)
                ):
                    age_days = 1.0
                else:
                    age_days = (prev_exp.inertia_age_days or 0.0) + 1.0

                coeff, is_reset = _compute_inertia(
                    age_days, strength, raw_score,
                    prev_exp.consensus_score, recent_raws
                )

                if is_reset:
                    new_consensus = raw_score
                    age_days = 1.0
                else:
                    new_consensus = (
                        (1.0 - coeff) * raw_score
                        + coeff * prev_exp.consensus_score
                    )

                # 7일 전 컨센서스 조회 (모멘텀)
                seven_days_ago = (
                    db.query(Expectation)
                    .filter(
                        Expectation.actor == actor,
                        Expectation.dimension == dimension,
                        Expectation.date >= batch_date - timedelta(days=8),
                        Expectation.date < batch_date - timedelta(days=6),
                    )
                    .order_by(Expectation.date.desc())
                    .first()
                )
                c7 = seven_days_ago.consensus_score if seven_days_ago else None
                momentum = (new_consensus - c7) / 2.0 if c7 is not None else None

                rows_to_upsert.append(
                    {
                        "date": batch_date,
                        "actor": actor,
                        "dimension": dimension,
                        "raw_score": raw_score,
                        "consensus_score": round(new_consensus, 4),
                        "consensus_strength": strength,
                        "inertia_age_days": age_days,
                        "inertia_coefficient": coeff,
                        "inertia_reset": is_reset,
                        "consensus_7d_ago": c7,
                        "momentum_score": round(momentum, 4) if momentum is not None else None,
                    }
                )

            updated += 1

        upsert_rows(
            db,
            Expectation,
            rows_to_upsert,
            conflict_columns=["date", "actor", "dimension"],
            update_columns=[
                "raw_score",
                "consensus_score",
                "consensus_strength",
                "inertia_age_days",
                "inertia_coefficient",
                "inertia_reset",
                "consensus_7d_ago",
                "momentum_score",
            ],
        )
        db.commit()
        logger.info(f"[expectation] {updated}개 actor×dimension 업데이트 완료")
        return {"updated": updated, "batch_date": batch_date.isoformat()}

    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════════════════════
# Layer 3 : Divergence 탐지
# ═══════════════════════════════════════════════════════════════════════════════

@shared_task(name="workers.detect_divergence", bind=True)
def detect_divergence(self, expectation_result: dict | None = None, batch_date_iso: str | None = None):
    """
    오늘 업데이트된 Expectation에서 괴리 탐지.
    adjusted_gap >= WARNING_THRESHOLD 이면 DivergenceEvent 저장.
    """
    batch_date = _normalize_batch_date(batch_date_iso)
    window_start, window_end = _batch_window(batch_date)
    db: Session = SessionLocal()
    try:
        # 오늘 Expectation 로드
        today_exps = (
            db.query(Expectation)
            .filter(
                Expectation.date >= window_start,
                Expectation.date < window_end,
            )
            .all()
        )

        if not today_exps:
            logger.info("[divergence] 오늘 Expectation 없음 — 스킵")
            return {"events": 0}

        # dimension별 ALERT 카운트 (복수 dimension 동시 승수용)
        alert_dims_today: list[tuple[str, str]] = []
        events_to_upsert = []

        for exp in today_exps:
            base_gap = abs(exp.raw_score - exp.consensus_score)
            if base_gap < WARNING_THRESHOLD:
                continue

            # adjusted_gap = base_gap / (1 - consensus_strength + 0.1)
            adjusted = base_gap / (1.0 - exp.consensus_strength + 0.1)

            # severity multiplier
            multiplier = 1.0
            if exp.inertia_reset:
                multiplier *= MULT_INERTIA_RESET

            # 모멘텀 부호 반전 확인 (어제와 비교)
            yesterday = batch_date - timedelta(days=1)
            prev_exp = (
                db.query(Expectation)
                .filter(
                    Expectation.actor == exp.actor,
                    Expectation.dimension == exp.dimension,
                    Expectation.date >= yesterday - timedelta(days=1),
                    Expectation.date < batch_date,
                )
                .order_by(Expectation.date.desc())
                .first()
            )
            momentum_flip = False
            if (
                prev_exp
                and exp.momentum_score is not None
                and prev_exp.momentum_score is not None
            ):
                if (
                    exp.momentum_score * prev_exp.momentum_score < 0  # 부호 반전
                ):
                    momentum_flip = True
                    multiplier *= MULT_MOMENTUM_FLIP

            adjusted_final = round(adjusted * multiplier, 4)
            severity = "ALERT" if adjusted_final >= ALERT_THRESHOLD else "WARNING"

            if severity == "ALERT":
                alert_dims_today.append((exp.actor, exp.dimension))

            events_to_upsert.append(
                {
                    "batch_date": batch_date,
                    "actor": exp.actor,
                    "dimension": exp.dimension,
                    "raw_score": exp.raw_score,
                    "consensus_score": exp.consensus_score,
                    "consensus_strength": exp.consensus_strength,
                    "adjusted_gap": adjusted_final,
                    "severity": severity,
                    "inertia_coefficient": exp.inertia_coefficient,
                    "inertia_reset": exp.inertia_reset,
                    "momentum_score": exp.momentum_score,
                    "momentum_sign_change": momentum_flip,
                    "multiplier_applied": multiplier,
                    "report_generated": False,
                }
            )

        # 복수 dimension 동시 ALERT 승수 적용
        if len(alert_dims_today) >= 2:
            for ev in events_to_upsert:
                if ev["severity"] == "ALERT":
                    ev["multiplier_applied"] = round((ev["multiplier_applied"] or 1.0) * MULT_MULTI_DIM, 4)
                    ev["adjusted_gap"] = round(ev["adjusted_gap"] * MULT_MULTI_DIM, 4)

        upsert_rows(
            db,
            DivergenceEvent,
            events_to_upsert,
            conflict_columns=["batch_date", "actor", "dimension"],
            update_columns=[
                "raw_score",
                "consensus_score",
                "consensus_strength",
                "adjusted_gap",
                "severity",
                "inertia_coefficient",
                "inertia_reset",
                "momentum_score",
                "momentum_sign_change",
                "multiplier_applied",
                "report_generated",
            ],
        )
        db.commit()

        # ALERT 이벤트 → 리포트 생성 Celery 태스크 비동기 호출
        alert_count = 0
        total_alerts = sum(1 for ev in events_to_upsert if ev["severity"] == "ALERT")
        if settings.SENTIMENT_REPORTS_ENABLED and events_to_upsert:
            alert_events = (
                db.query(DivergenceEvent)
                .filter(
                    DivergenceEvent.batch_date >= window_start,
                    DivergenceEvent.batch_date < window_end,
                    DivergenceEvent.severity == "ALERT",
                    DivergenceEvent.report_generated.is_(False),
                )
                .all()
            )
            for ev in alert_events:
                generate_divergence_report.delay(ev.id)
            alert_count = total_alerts
        else:
            alert_count = total_alerts

        logger.info(
            f"[divergence] {len(events_to_upsert)}개 이벤트 저장 "
            f"(ALERT {alert_count}, WARNING {len(events_to_upsert) - alert_count})"
        )
        return {
            "events": len(events_to_upsert),
            "alerts": alert_count,
            "warnings": len(events_to_upsert) - alert_count,
        }

    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════════════════════
# Layer 4 : 리포트 생성
# ═══════════════════════════════════════════════════════════════════════════════

@shared_task(name="workers.generate_divergence_report", bind=True, max_retries=2)
def generate_divergence_report(self, event_id: int):
    """
    ALERT 등급 DivergenceEvent 에 대한 LLM 리포트 생성.
    근거 뉴스·데이터를 컨텍스트로 주입 후 대처 방법 생성.
    """
    db: Session = SessionLocal()
    try:
        if not settings.SENTIMENT_REPORTS_ENABLED:
            logger.info("[report] sentiment reports disabled — skip event_id=%s", event_id)
            return {"skipped": True, "reason": "sentiment_reports_disabled"}

        event = db.query(DivergenceEvent).filter(DivergenceEvent.id == event_id).first()
        if not event:
            logger.warning(f"[report] event_id={event_id} 없음")
            return

        # 근거 신호 수집
        signals = (
            db.query(SentimentSignal)
            .filter(
                SentimentSignal.batch_date == event.batch_date,
                SentimentSignal.actor == event.actor,
                SentimentSignal.dimension == event.dimension,
            )
            .order_by(SentimentSignal.confidence.desc())
            .limit(10)
            .all()
        )

        evidence_block = "\n".join(
            f"- [{s.source_type}#{s.source_id}] stance={s.stance} "
            f"score={s.stance_score} | {s.evidence}"
            for s in signals
        )

        prompt = f"""You are a macro-economic risk analyst.

A divergence has been detected between current market sentiment and established consensus:

ACTOR      : {event.actor}
DIMENSION  : {event.dimension}
RAW SCORE  : {event.raw_score:.3f}  (today's signal: -1=very dovish/pessimistic, +1=very hawkish/optimistic)
CONSENSUS  : {event.consensus_score:.3f}  (running expectation with inertia)
GAP        : {event.adjusted_gap:.3f}  (severity: {event.severity})
INERTIA RESET : {event.inertia_reset}
MOMENTUM FLIP : {event.momentum_sign_change}

KEY EVIDENCE:
{evidence_block}

Write a concise risk report in Korean with these sections:
1. **헤드라인** (한 문장)
2. **배경 분석** (2-3문장: 왜 이 괴리가 발생했는가)
3. **근거 요약** (bullet 3-5개)
4. **대처 방법** (포트폴리오/리스크 관점에서 구체적 행동 2-3가지)
5. **리스크 시나리오** (이 신호가 맞을 경우 vs 틀릴 경우)

Return JSON with keys: headline, background, evidence, action_plan, risk_scenario
"""
        try:
            raw = _call_llm(prompt)
        except Exception as exc:
            raise self.retry(exc=exc, countdown=60)

        parsed = _parse_batch_response(raw)
        if isinstance(parsed, list) and parsed:
            parsed = parsed[0]

        if not isinstance(parsed, dict):
            # fallback: 전체 텍스트를 headline으로
            parsed = {"headline": raw[:200], "background": raw}

        report_rows = [
            {
                "event_id": event_id,
                "headline": parsed.get("headline", "divergence detected"),
                "background": parsed.get("background", ""),
                "evidence": json.dumps(
                    [{"source": f"{s.source_type}#{s.source_id}", "evidence": s.evidence} for s in signals],
                    ensure_ascii=False,
                ),
                "action_plan": parsed.get("action_plan", ""),
                "risk_scenario": parsed.get("risk_scenario", ""),
                "notified": False,
            }
        ]
        upsert_rows(
            db,
            DivergenceReport,
            report_rows,
            conflict_columns=["event_id"],
            update_columns=["headline", "background", "evidence", "action_plan", "risk_scenario", "notified"],
        )

        event.report_generated = True
        db.commit()
        report = db.query(DivergenceReport).filter(DivergenceReport.event_id == event_id).first()

        logger.info(f"[report] event_id={event_id} 리포트 생성 완료")
        return {"report_id": report.id, "headline": report.headline}

    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════════════════════
# Celery Chain Entry Point
# ═══════════════════════════════════════════════════════════════════════════════

def _prepare_sentiment_pipeline(batch_date: datetime | None = None) -> dict[str, Any]:
    if not settings.SENTIMENT_PIPELINE_ENABLED:
        logger.info("[pipeline] sentiment pipeline disabled")
        return {"status": "skipped", "reason": "sentiment_pipeline_disabled"}

    if not settings.OPENAI_API_KEY:
        logger.info("[pipeline] OPENAI_API_KEY 없음 — sentiment 파이프라인 스킵")
        return {"status": "skipped", "reason": "OPENAI_API_KEY not configured"}

    normalized_batch_date = _normalize_batch_date(batch_date=batch_date)
    db: Session = SessionLocal()
    try:
        pending_count = _count_recent_unprocessed_news(db, normalized_batch_date)
    finally:
        db.close()

    if pending_count == 0:
        logger.info("[pipeline] 최근 미처리 뉴스 없음 — sentiment 파이프라인 스킵")
        return {"status": "skipped", "reason": "no_recent_unprocessed_news"}

    return {
        "status": "ready",
        "batch_date": normalized_batch_date,
        "batch_date_iso": normalized_batch_date.isoformat(),
        "pending_count": pending_count,
    }


def run_daily_sentiment_pipeline_sync(batch_date: datetime | None = None) -> dict[str, Any]:
    prep = _prepare_sentiment_pipeline(batch_date=batch_date)
    if prep["status"] != "ready":
        return {"skipped": True, "reason": prep["reason"]}

    bd_iso = prep["batch_date_iso"]
    extract_result = extract_daily_sentiments.run(batch_date_iso=bd_iso)
    expectation_result = update_expectations.run(extract_result=extract_result, batch_date_iso=bd_iso)
    divergence_result = detect_divergence.run(expectation_result=expectation_result, batch_date_iso=bd_iso)
    logger.info(
        "[pipeline] sentiment 파이프라인 동기 실행 완료: %s (pending_count=%s)",
        bd_iso,
        prep["pending_count"],
    )
    return {
        "mode": "sync",
        "batch_date": bd_iso,
        "pending_count": prep["pending_count"],
        "extract": extract_result,
        "expectation": expectation_result,
        "divergence": divergence_result,
    }


def run_daily_sentiment_pipeline(batch_date: datetime | None = None):
    """
    daily Celery Beat 에서 호출하는 체인 진입점.
    extract → update → detect 순서로 chain 실행.
    """
    prep = _prepare_sentiment_pipeline(batch_date=batch_date)
    if prep["status"] != "ready":
        return {"skipped": True, "reason": prep["reason"]}

    bd_iso = prep["batch_date_iso"]

    pipeline = chain(
        extract_daily_sentiments.s(batch_date_iso=bd_iso),
        update_expectations.s(batch_date_iso=bd_iso),
        detect_divergence.s(batch_date_iso=bd_iso),
    )
    try:
        from .celery_app import celery

        pipeline.apply_async(app=celery)
    except OperationalError as exc:
        logger.warning("[pipeline] broker unavailable, falling back to sync execution: %s", exc)
        return run_daily_sentiment_pipeline_sync(batch_date=prep["batch_date"])

    logger.info(f"[pipeline] 일일 sentiment 파이프라인 시작: {bd_iso} (pending_count={prep['pending_count']})")
    return {"queued": True, "batch_date": bd_iso, "pending_count": prep["pending_count"]}
