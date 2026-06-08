from sqlalchemy import (
    Column,
    String,
    Float,
    Date,
    DateTime,
    Integer,
    Text,
    JSON,
    Index,
    Boolean,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..core.database import Base


class InterestRate(Base):
    __tablename__ = "interest_rates"
    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False)
    series_key = Column(String(50), nullable=False)   # DFF, DGS2, DGS10, DGS30
    value = Column(Float)
    created_at = Column(DateTime, server_default=func.now())
    __table_args__ = (
        Index("ix_ir_key_date", "series_key", "date"),
        UniqueConstraint("series_key", "date", name="uq_interest_rates_series_key_date"),
    )


class MacroIndicator(Base):
    __tablename__ = "macro_indicators"
    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False)
    series_key = Column(String(50), nullable=False)   # CPI, PCE, GDP, UNRATE, etc.
    value = Column(Float)
    created_at = Column(DateTime, server_default=func.now())
    __table_args__ = (
        Index("ix_macro_key_date", "series_key", "date"),
        UniqueConstraint("series_key", "date", name="uq_macro_indicators_series_key_date"),
    )


class ExchangeRate(Base):
    __tablename__ = "exchange_rates"
    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False)
    pair = Column(String(20), nullable=False)          # USDKRW, EURUSD, DXY, etc.
    value = Column(Float)
    created_at = Column(DateTime, server_default=func.now())
    __table_args__ = (
        Index("ix_fx_pair_date", "pair", "date"),
        UniqueConstraint("pair", "date", name="uq_exchange_rates_pair_date"),
    )


class EquityIndex(Base):
    __tablename__ = "equity_indices"
    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False)
    ticker = Column(String(20), nullable=False)        # ^GSPC, ^IXIC, ^KS11, ^VIX
    close = Column(Float)
    change_1d = Column(Float)
    change_1d_pct = Column(Float)
    created_at = Column(DateTime, server_default=func.now())
    __table_args__ = (
        Index("ix_eq_ticker_date", "ticker", "date"),
        UniqueConstraint("ticker", "date", name="uq_equity_indices_ticker_date"),
    )


class SectorPerformance(Base):
    __tablename__ = "sector_performance"
    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False)
    ticker = Column(String(10), nullable=False)        # XLK, XLF, XLE, etc.
    sector_name = Column(String(50))
    close = Column(Float)
    change_1d_pct = Column(Float)
    change_1m_pct = Column(Float)
    change_3m_pct = Column(Float)
    change_ytd_pct = Column(Float)
    created_at = Column(DateTime, server_default=func.now())
    __table_args__ = (
        Index("ix_sec_ticker_date", "ticker", "date"),
        UniqueConstraint("ticker", "date", name="uq_sector_performance_ticker_date"),
    )


class CreditSpread(Base):
    __tablename__ = "credit_spreads"
    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False)
    series_key = Column(String(50), nullable=False)    # HY_OAS, IG_OAS
    value = Column(Float)
    created_at = Column(DateTime, server_default=func.now())
    __table_args__ = (
        Index("ix_cs_key_date", "series_key", "date"),
        UniqueConstraint("series_key", "date", name="uq_credit_spreads_series_key_date"),
    )


class SentimentIndicator(Base):
    __tablename__ = "sentiment_indicators"
    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False)
    series_key = Column(String(50), nullable=False)    # AAII_BULL, AAII_BEAR, FEAR_GREED
    value = Column(Float)
    created_at = Column(DateTime, server_default=func.now())
    __table_args__ = (Index("ix_sent_key_date", "series_key", "date"),)


class RealEconomyIndicator(Base):
    __tablename__ = "real_economy"
    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False)
    series_key = Column(String(50), nullable=False)    # BDI, COPPER_GOLD, WTI_BRENT_SPREAD
    value = Column(Float)
    created_at = Column(DateTime, server_default=func.now())
    __table_args__ = (
        Index("ix_re_key_date", "series_key", "date"),
        UniqueConstraint("series_key", "date", name="uq_real_economy_series_key_date"),
    )


class FomcEvent(Base):
    __tablename__ = "fomc_events"
    id = Column(Integer, primary_key=True)
    meeting_date = Column(DateTime, nullable=False, unique=True)
    decision_rate = Column(Float)
    change_bp = Column(Integer)                        # basis points change
    statement_url = Column(Text)
    minutes_url = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


class FedWatch(Base):
    __tablename__ = "fed_watch"
    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False)
    meeting_date = Column(DateTime, nullable=False)
    prob_hike = Column(Float)
    prob_hold = Column(Float)
    prob_cut = Column(Float)
    created_at = Column(DateTime, server_default=func.now())
    __table_args__ = (
        Index("ix_fw_date_meeting", "date", "meeting_date"),
        UniqueConstraint("meeting_date", "date", name="uq_fed_watch_meeting_date_date"),
    )


class ChangeSnapshot(Base):
    __tablename__ = "change_snapshots"
    id = Column(Integer, primary_key=True)
    snapshot_date = Column(DateTime, nullable=False)
    indicator_key = Column(String(80), nullable=False)
    label = Column(String(100))
    category = Column(String(50))
    current_value = Column(Float)
    unit = Column(String(30))
    delta_1d = Column(Float)
    delta_1d_pct = Column(Float)
    delta_1w_pct = Column(Float)
    delta_1m_pct = Column(Float)
    delta_3m_pct = Column(Float)
    z_score_1y = Column(Float)
    direction = Column(String(10))                     # up / down / flat
    signal = Column(String(10))                        # green / yellow / red
    created_at = Column(DateTime, server_default=func.now())
    __table_args__ = (Index("ix_cs_ikey_date", "indicator_key", "snapshot_date"),)


class NewsItem(Base):
    __tablename__ = "news_items"
    id = Column(Integer, primary_key=True)
    source = Column(String(100))
    title = Column(Text, nullable=False)
    summary = Column(Text)
    url = Column(Text)
    category = Column(String(50))                      # fed, macro, equity, fx, geopolitics
    published_at = Column(DateTime)
    collected_at = Column(DateTime, server_default=func.now())
    # v2: 배치 sentiment 추출 완료 여부
    sentiment_extracted = Column(Boolean, default=False, nullable=False, server_default="false")


class AiSummary(Base):
    __tablename__ = "ai_summaries"
    id = Column(Integer, primary_key=True)
    summary_date = Column(DateTime, nullable=False, unique=True)
    headline = Column(Text)
    body = Column(Text)
    indicators_snapshot = Column(JSON)
    model_used = Column(String(50))
    created_at = Column(DateTime, server_default=func.now())


# ═══════════════════════════════════════════════════════════════════════════════
# Expectation-Divergence Pipeline (v2)
# ═══════════════════════════════════════════════════════════════════════════════

class SentimentSignal(Base):
    """개별 텍스트(뉴스/연설/FOMC 발표문)에서 추출된 심리 분류 결과."""
    __tablename__ = "sentiment_signals"
    id = Column(Integer, primary_key=True)

    source_type  = Column(String(20), nullable=False)   # news | fomc | fed_speech
    source_id    = Column(Integer, nullable=False)
    extracted_at = Column(DateTime, server_default=func.now())
    batch_date   = Column(DateTime, nullable=False)

    actor        = Column(String(30), nullable=False)   # fed | market | consumer | corporate | geopolitical
    dimension    = Column(String(30), nullable=False)   # rates | inflation | growth | liquidity | risk_appetite | policy
    stance       = Column(String(30), nullable=False)   # hawkish/dovish | optimistic/pessimistic | …
    stance_score = Column(Float, nullable=False)        # -1.0 ~ +1.0
    intensity    = Column(Float, nullable=False)        # 0.0 ~ 1.0
    confidence   = Column(Float, nullable=False)        # LLM 확신도 0.0 ~ 1.0
    evidence     = Column(Text)

    __table_args__ = (
        Index("ix_ss_batch_actor_dim", "batch_date", "actor", "dimension"),
        Index("ix_ss_source", "source_type", "source_id"),
    )


class Expectation(Base):
    """dimension별 누적 컨센서스 (관성 모델 적용). 매일 배치 처리 후 upsert."""
    __tablename__ = "expectations"
    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False)

    actor     = Column(String(30), nullable=False)
    dimension = Column(String(30), nullable=False)

    consensus_score    = Column(Float, nullable=False)  # -1.0 ~ +1.0 (관성 적용 후)
    raw_score          = Column(Float, nullable=False)  # 오늘 신호 가중 평균 (관성 전)
    consensus_strength = Column(Float, nullable=False)  # 신호 일치도 0.0 ~ 1.0

    inertia_age_days    = Column(Float, default=0.0)
    inertia_coefficient = Column(Float, default=0.0)    # tanh(0.05 × age × strength)
    inertia_reset       = Column(Boolean, default=False)

    consensus_7d_ago = Column(Float)
    momentum_score   = Column(Float)                    # (today - 7d_ago) / 2.0

    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_exp_date_actor_dim", "date", "actor", "dimension"),
    )


class DivergenceEvent(Base):
    """adjusted_gap >= 0.25 인 괴리 탐지 이벤트."""
    __tablename__ = "divergence_events"
    id = Column(Integer, primary_key=True)
    detected_at = Column(DateTime, server_default=func.now())
    batch_date  = Column(DateTime, nullable=False)

    actor     = Column(String(30), nullable=False)
    dimension = Column(String(30), nullable=False)

    raw_score          = Column(Float, nullable=False)
    consensus_score    = Column(Float, nullable=False)
    consensus_strength = Column(Float, nullable=False)
    adjusted_gap       = Column(Float, nullable=False)
    severity           = Column(String(10), nullable=False)  # WARNING | ALERT

    inertia_coefficient  = Column(Float)
    inertia_reset        = Column(Boolean, default=False)
    momentum_score       = Column(Float)
    momentum_sign_change = Column(Boolean, default=False)
    multiplier_applied   = Column(Float, default=1.0)

    report_generated = Column(Boolean, default=False)

    __table_args__ = (
        Index("ix_de_batch_severity", "batch_date", "severity"),
        Index("ix_de_actor_dim", "actor", "dimension"),
    )


class DivergenceReport(Base):
    """ALERT 등급 이벤트에 대해 LLM이 생성한 대처 리포트."""
    __tablename__ = "divergence_reports"
    id = Column(Integer, primary_key=True)
    event_id     = Column(Integer, nullable=False)      # DivergenceEvent.id
    generated_at = Column(DateTime, server_default=func.now())

    headline      = Column(Text, nullable=False)
    background    = Column(Text)
    evidence      = Column(Text)                        # JSON 직렬화 근거 목록
    action_plan   = Column(Text)
    risk_scenario = Column(Text)

    notified = Column(Boolean, default=False)

    __table_args__ = (
        Index("ix_dr_event_id", "event_id"),
    )


class Indicator(Base):
    """Macro indicator metadata."""
    __tablename__ = "indicators"

    id = Column(Integer, primary_key=True)
    code = Column(String(64), nullable=False, unique=True)   # CPIAUCSL, DFF, USDKRW
    name = Column(String(255), nullable=False)
    description = Column(Text)
    country = Column(String(64), nullable=False)
    category = Column(String(64), nullable=False)
    source = Column(String(128), nullable=False)
    frequency = Column(String(32), nullable=False)           # daily, weekly, monthly, quarterly
    unit = Column(String(32), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    observations = relationship(
        "Observation",
        back_populates="indicator",
        cascade="all, delete-orphan",
    )
    signals = relationship(
        "Signal",
        back_populates="indicator",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_indicator_country_category", "country", "category"),
        Index("ix_indicator_source_frequency", "source", "frequency"),
    )


class Observation(Base):
    """Time-series values for an indicator."""
    __tablename__ = "observations"

    id = Column(Integer, primary_key=True)
    indicator_id = Column(Integer, ForeignKey("indicators.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    value = Column(Float, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    indicator = relationship("Indicator", back_populates="observations")
    signals = relationship("Signal", back_populates="observation")

    __table_args__ = (
        UniqueConstraint("indicator_id", "date", "value", name="uq_observation_indicator_date_value"),
        Index("ix_observation_indicator_date", "indicator_id", "date"),
    )


class Signal(Base):
    """Derived signal based on indicator observations."""
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True)
    indicator_id = Column(Integer, ForeignKey("indicators.id", ondelete="CASCADE"), nullable=False)
    observation_id = Column(Integer, ForeignKey("observations.id", ondelete="SET NULL"))
    signal_date = Column(Date, nullable=False)
    signal_type = Column(String(64), nullable=False)         # trend, threshold, surprise, regime
    signal_level = Column(String(32), nullable=False)        # info, watch, alert
    signal_value = Column(Float)
    summary = Column(Text)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    indicator = relationship("Indicator", back_populates="signals")
    observation = relationship("Observation", back_populates="signals")

    __table_args__ = (
        Index("ix_signal_indicator_date", "indicator_id", "signal_date"),
        Index("ix_signal_type_level", "signal_type", "signal_level"),
    )


class CleanupRun(Base):
    """Latest cleanup execution summaries for operators."""
    __tablename__ = "cleanup_runs"

    id = Column(Integer, primary_key=True)
    started_at = Column(DateTime, nullable=False)
    finished_at = Column(DateTime, nullable=False)
    collection_success_logs_deleted = Column(Integer, nullable=False, default=0, server_default="0")
    collection_failure_logs_deleted = Column(Integer, nullable=False, default=0, server_default="0")
    raw_responses_deleted = Column(Integer, nullable=False, default=0, server_default="0")
    debug_logs_deleted = Column(Integer, nullable=False, default=0, server_default="0")
    scheduler_logs_deleted = Column(Integer, nullable=False, default=0, server_default="0")
    result_json = Column(JSON, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        Index("ix_cleanup_runs_started_at", "started_at"),
        Index("ix_cleanup_runs_created_at", "created_at"),
    )


class CollectionRun(Base):
    """Provider collection run history and guard metadata."""
    __tablename__ = "collection_runs"

    id = Column(Integer, primary_key=True)
    job_key = Column(String(100), nullable=False)
    provider = Column(String(100), nullable=False)
    target_date = Column(Date)
    status = Column(String(20), nullable=False)
    started_at = Column(DateTime, nullable=False)
    finished_at = Column(DateTime)
    min_interval_minutes = Column(Integer, nullable=False)
    fetched_count = Column(Integer, nullable=False, default=0, server_default="0")
    inserted_count = Column(Integer, nullable=False, default=0, server_default="0")
    updated_count = Column(Integer, nullable=False, default=0, server_default="0")
    error_message = Column(Text)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_collection_runs_job_key_started_at", "job_key", "started_at"),
        Index("ix_collection_runs_provider_target_date", "provider", "target_date"),
        Index("ix_collection_runs_status_finished_at", "status", "finished_at"),
    )
