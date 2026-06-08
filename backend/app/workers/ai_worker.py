"""AI Summary Worker — generates daily macro briefing via OpenAI."""
import logging
from datetime import datetime, timedelta
from openai import OpenAI
from sqlalchemy.orm import Session
from ..core.config import settings
from ..models.indicators import NewsItem, AiSummary, FomcEvent, FedWatch
from ..services.observation_query_service import get_ai_context_payload

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """당신은 거시경제 분석 전문가입니다. 
매일 아침 제공되는 경제 지표 데이터와 뉴스를 바탕으로 간결하고 통찰력 있는 일일 브리핑을 작성하세요.
한국어로 작성하며, 전문적이지만 이해하기 쉬운 언어를 사용하세요.
각 섹션은 2-4문장으로 간결하게 작성하세요."""

SUMMARY_TEMPLATE = """
다음 데이터를 바탕으로 일일 거시경제 브리핑을 작성하세요.

=== 주요 지표 변화 (오늘 기준) ===
{snapshots}

=== 최근 24시간 주요 뉴스 헤드라인 ===
{news}

=== FOMC 일정 ===
{fomc}

아래 형식으로 작성하세요:

**[한 줄 요약]**
오늘의 핵심 거시 키워드를 한 문장으로

**[금리 · 유동성]**
기준금리, 국채 수익률, 크레딧 스프레드 현황 분석

**[성장 · 고용 신호]**  
PMI, LEI, 실업지표, 실물경제 신호 해석

**[시장 심리]**
VIX, 크레딧 스프레드, 달러 동향 기반 심리 분석

**[주목할 이상 신호]**
Z-score ±1.5 초과 지표 중심으로 이상값 해석

**[다음 주 주요 이벤트]**
FOMC 일정, 주요 경제지표 발표 예정
"""


def build_context(db: Session) -> dict:
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    context_payload = get_ai_context_payload(db, today.date())

    snap_text = "\n".join([
        f"- {item['name'] or item['series_key']} ({item['series_key']}): {_fmt_num(item['latest_value'])}{item['unit'] or ''} "
        f"| 변화율: {_fmt_pct(item.get('delta_pct'))} | 기준일: {item['latest_date']}"
        for item in context_payload["series"]
        if item["latest_value"] is not None
    ]) or "데이터 없음"

    # News
    news_items = db.query(NewsItem).filter(
        NewsItem.published_at >= yesterday
    ).order_by(NewsItem.published_at.desc()).limit(15).all()

    news_text = "\n".join([
        f"- [{item.source}] {item.title}"
        for item in news_items
    ]) or "뉴스 없음"

    # FOMC
    next_fomc = db.query(FomcEvent).filter(
        FomcEvent.meeting_date >= today
    ).order_by(FomcEvent.meeting_date).first()

    latest_fw = db.query(FedWatch).order_by(FedWatch.date.desc()).first()

    fomc_text = "없음"
    if next_fomc:
        days_left = (next_fomc.meeting_date - today).days
        fomc_text = f"다음 FOMC: {next_fomc.meeting_date.strftime('%Y.%m.%d')} (D-{days_left})"
        if latest_fw and all(v is not None for v in [latest_fw.prob_hold, latest_fw.prob_cut, latest_fw.prob_hike]):
            fomc_text += (
                f" | 동결 {latest_fw.prob_hold*100:.0f}%"
                f" / 인하 {latest_fw.prob_cut*100:.0f}%"
                f" / 인상 {latest_fw.prob_hike*100:.0f}%"
            )

    return {
        "snapshots": snap_text,
        "news": news_text,
        "fomc": fomc_text,
        "snap_list": [
            {
                "key": item["series_key"],
                "label": item["name"] or item["series_key"],
                "value": item["latest_value"],
                "z_score": None,
                "signal": item["status"],
            }
            for item in context_payload["series"]
        ]
    }


def generate_daily_summary(db: Session):
    if not settings.OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not set, skipping AI summary")
        return

    today = datetime.now()
    today_start = today.replace(hour=0, minute=0, second=0, microsecond=0)

    # Check if already generated today
    existing = db.query(AiSummary).filter(
        AiSummary.summary_date >= today_start
    ).first()
    if existing:
        logger.info("AI summary already generated today")
        return

    ctx = build_context(db)
    prompt = SUMMARY_TEMPLATE.format(**ctx)

    try:
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=settings.AI_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=1200,
            temperature=0.4,
        )
        body = response.choices[0].message.content

        # Extract headline (first bold line)
        headline = ""
        for line in body.split("\n"):
            if line.strip().startswith("**[한 줄 요약]**"):
                idx = body.find(line)
                next_section = body.find("**[", idx + 1)
                headline = body[idx:next_section].replace("**[한 줄 요약]**", "").strip()
                break

        db.add(AiSummary(
            summary_date=today,
            headline=headline[:200] if headline else None,
            body=body,
            indicators_snapshot=ctx["snap_list"],
            model_used=settings.AI_MODEL,
        ))
        db.commit()
        logger.info("AI daily summary generated successfully")
    except Exception as e:
        db.rollback()
        logger.error(f"AI summary generation failed: {e}")


def chat_with_context(db: Session, user_message: str) -> str:
    """Single-turn chat with macro context injected."""
    ctx = build_context(db)
    context_block = f"""현재 거시경제 데이터 (오늘 기준):
{ctx['snapshots']}

최근 뉴스:
{ctx['news']}

FOMC 정보:
{ctx['fomc']}
"""
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


def _fmt_num(value: float | None, digits: int = 2) -> str:
    return "N/A" if value is None else f"{value:.{digits}f}"


def _fmt_pct(value: float | None) -> str:
    return "N/A" if value is None else f"{value:+.1f}%"


def _fmt_signed(value: float | None) -> str:
    return "N/A" if value is None else f"{value:+.2f}"
