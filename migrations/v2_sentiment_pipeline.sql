-- MacroAnalysis v2 Migration
-- 기존 DB(production)에 적용 시 실행. 신규 배포는 create_all()로 자동 생성됨.
-- Railway Postgres 콘솔 또는 psql로 실행.

-- 1. news_items 테이블에 sentiment_extracted 컬럼 추가
ALTER TABLE news_items
    ADD COLUMN IF NOT EXISTS sentiment_extracted BOOLEAN NOT NULL DEFAULT FALSE;

-- 2. sentiment_signals 테이블 생성
CREATE TABLE IF NOT EXISTS sentiment_signals (
    id              SERIAL PRIMARY KEY,
    source_type     VARCHAR(20)  NOT NULL,
    source_id       INTEGER      NOT NULL,
    extracted_at    TIMESTAMP    DEFAULT NOW(),
    batch_date      TIMESTAMP    NOT NULL,
    actor           VARCHAR(30)  NOT NULL,
    dimension       VARCHAR(30)  NOT NULL,
    stance          VARCHAR(30)  NOT NULL,
    stance_score    FLOAT        NOT NULL,
    intensity       FLOAT        NOT NULL,
    confidence      FLOAT        NOT NULL,
    evidence        TEXT
);

CREATE INDEX IF NOT EXISTS ix_ss_batch_actor_dim
    ON sentiment_signals (batch_date, actor, dimension);
CREATE INDEX IF NOT EXISTS ix_ss_source
    ON sentiment_signals (source_type, source_id);

-- 3. expectations 테이블 생성
CREATE TABLE IF NOT EXISTS expectations (
    id                   SERIAL PRIMARY KEY,
    date                 TIMESTAMP    NOT NULL,
    actor                VARCHAR(30)  NOT NULL,
    dimension            VARCHAR(30)  NOT NULL,
    consensus_score      FLOAT        NOT NULL,
    raw_score            FLOAT        NOT NULL,
    consensus_strength   FLOAT        NOT NULL,
    inertia_age_days     FLOAT        DEFAULT 0.0,
    inertia_coefficient  FLOAT        DEFAULT 0.0,
    inertia_reset        BOOLEAN      DEFAULT FALSE,
    consensus_7d_ago     FLOAT,
    momentum_score       FLOAT,
    updated_at           TIMESTAMP    DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_exp_date_actor_dim
    ON expectations (date, actor, dimension);

-- 4. divergence_events 테이블 생성
CREATE TABLE IF NOT EXISTS divergence_events (
    id                   SERIAL PRIMARY KEY,
    detected_at          TIMESTAMP   DEFAULT NOW(),
    batch_date           TIMESTAMP   NOT NULL,
    actor                VARCHAR(30) NOT NULL,
    dimension            VARCHAR(30) NOT NULL,
    raw_score            FLOAT       NOT NULL,
    consensus_score      FLOAT       NOT NULL,
    consensus_strength   FLOAT       NOT NULL,
    adjusted_gap         FLOAT       NOT NULL,
    severity             VARCHAR(10) NOT NULL,
    inertia_coefficient  FLOAT,
    inertia_reset        BOOLEAN     DEFAULT FALSE,
    momentum_score       FLOAT,
    momentum_sign_change BOOLEAN     DEFAULT FALSE,
    multiplier_applied   FLOAT       DEFAULT 1.0,
    report_generated     BOOLEAN     DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS ix_de_batch_severity
    ON divergence_events (batch_date, severity);
CREATE INDEX IF NOT EXISTS ix_de_actor_dim
    ON divergence_events (actor, dimension);

-- 5. divergence_reports 테이블 생성
CREATE TABLE IF NOT EXISTS divergence_reports (
    id            SERIAL PRIMARY KEY,
    event_id      INTEGER  NOT NULL,
    generated_at  TIMESTAMP DEFAULT NOW(),
    headline      TEXT      NOT NULL,
    background    TEXT,
    evidence      TEXT,
    action_plan   TEXT,
    risk_scenario TEXT,
    notified      BOOLEAN   DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS ix_dr_event_id
    ON divergence_reports (event_id);

-- 완료 확인
SELECT 'v2 migration complete' AS status;
