# MacroWatch

거시경제 지표를 수집하고, 대시보드와 API로 노출하며, 선택적으로 AI 요약/채팅과 sentiment 파이프라인까지 수행하는 `FastAPI + Celery + React` 프로젝트입니다.

## 실행 가능한 최소 구조

최소 실행 경로는 아래 5개 서비스입니다.

- `postgres`: 영속 데이터 저장
- `redis`: API 캐시 + Celery broker/backend
- `backend`: FastAPI 서버, `/health`, `/api/*`
- `worker`: 수집기와 스냅샷/AI/sentiment 태스크 실행
- `frontend`: 정적 React 빌드 + nginx 프록시(`/api` -> `backend:8000`)

최소 실행만 기준으로 보면 기능 경계는 이렇게 나뉩니다.

| 영역 | 위치 | 역할 | 최소 실행 필수 여부 |
|---|---|---|---|
| Backend | `backend/app/main.py`, `backend/app/api/` | FastAPI 앱, API 라우팅, `/health` | 필수 |
| DB/Core | `backend/app/core/`, `backend/app/models/` | 설정 로드, SQLAlchemy 엔진, Redis 캐시, 테이블 정의 | 필수 |
| Workers | `backend/app/workers/` | Celery 앱, 스케줄, snapshot 계산, AI/sentiment 태스크 | 필수 |
| Collectors | `backend/app/collectors/` | FRED, 시장, 환율, 뉴스, FOMC 수집 | 선택적 데이터 기능 |
| Frontend | `frontend/src/` | 대시보드, 뉴스/FOMC 뷰, AI 패널 | 필수 |

## 디렉터리 구조와 파일 역할

```text
MacroAnalysis/
├── docker-compose.yml          # 전체 스택 진입점
├── .env                        # compose/runtime 환경변수
├── Makefile                    # 자주 쓰는 실행 명령 모음
├── backend/
│   ├── Dockerfile              # backend/worker/beat 공용 이미지
│   ├── requirements.txt
│   ├── tests/
│   │   └── test_fomc_collector.py
│   └── app/
│       ├── main.py             # FastAPI 앱 시작점
│       ├── api/routes.py       # REST API (/api/summary, /news, /fomc 등)
│       ├── core/
│       │   ├── config.py       # .env 기반 Settings
│       │   ├── database.py     # engine/session/init_db
│       │   └── cache.py        # Redis async 캐시
│       ├── models/
│       │   └── indicators.py   # 모든 SQLAlchemy 모델 정의
│       ├── collectors/         # 외부 데이터 수집 모듈
│       └── workers/            # Celery 스케줄/태스크
├── frontend/
│   ├── Dockerfile              # React build + nginx 배포
│   ├── nginx.conf              # SPA 서빙 + /api 프록시
│   ├── package.json
│   └── src/
│       ├── App.tsx             # 단순 경로 분기
│       ├── pages/              # Home, News, Fomc
│       ├── hooks/useApi.ts     # 공통 fetch hook
│       ├── lib/api.ts          # 프런트 API 클라이언트
│       └── components/         # 대시보드 zone/panel UI
└── migrations/
    └── v2_sentiment_pipeline.sql # 수동 SQL 메모 성격의 보조 파일
```

## 런타임 흐름

`docker compose up` 이후의 기본 흐름은 아래와 같습니다.

1. `postgres`, `redis`가 먼저 올라옵니다.
2. `backend`가 시작되면서 `init_db()`로 SQLAlchemy 모델 테이블을 자동 생성합니다.
3. `frontend`는 nginx가 정적 파일을 서빙하고 `/api/*`를 `backend:8000`으로 프록시합니다.
4. `worker`와 `beat`는 Celery 스케줄에 따라 수집기와 후처리 태스크를 실행합니다.
5. 초기 데이터는 비어 있으므로, 실제 화면 데이터를 보려면 `make collect` 또는 batched 수동 명령 실행이 필요합니다.

## 중복되거나 미완성인 코드

현재 기준으로 눈에 띄는 항목은 아래와 같습니다.

- `backend/app/models/indicators.py`의 `SentimentIndicator` 모델은 현재 어떤 collector, worker, API에서도 사용되지 않습니다.
- `migrations/v2_sentiment_pipeline.sql`은 Alembic에 연결된 정식 migration 체인이 아니라 참고용 수동 SQL 파일에 가깝습니다.
- sentiment/divergence 관련 API와 워커는 존재하지만, 프런트 기본 대시보드에서는 아직 사용하지 않습니다.
- AI 기능은 `OPENAI_API_KEY`가 비어 있으면 정상적으로 비활성화되며, 이 경우 `/api/ai/chat`, `/api/ai/summary`는 빈 상태 또는 503/404가 될 수 있습니다.
- 수집기 중 일부는 API 키가 없으면 스킵됩니다.
  - `FRED_API_KEY` 없음: FRED 금리/거시/크레딧 수집 불가
  - `FINNHUB_API_KEY` 없음: Finnhub 뉴스 수집 스킵
  - `EXCHANGERATE_API_KEY` 없음: 무료 fallback으로 환율 수집 시도
  - `OPENAI_API_KEY` 없음: AI 요약/채팅/sentiment 파이프라인 비활성화 또는 실패

즉, 최소 실행 자체는 가능하지만, "데이터가 채워진 완전한 대시보드"와 "AI 파이프라인"은 별도 키 유무에 따라 달라집니다.

## 실행 방법

`.env`는 저장소 루트에 직접 둡니다. 이 저장소는 `.env.example`을 사용하지 않습니다.

최소 예시는 아래와 같습니다.

```dotenv
POSTGRES_PASSWORD=macropass
FRED_API_KEY=
FINNHUB_API_KEY=
EXCHANGERATE_API_KEY=
OPENAI_API_KEY=
AI_MODEL=gpt-4o-mini
SENTIMENT_BATCH_SIZE=20
INERTIA_ALPHA=0.05
DIVERGENCE_WARNING_THRESHOLD=0.25
DIVERGENCE_ALERT_THRESHOLD=0.40
COLLECTION_SUCCESS_LOG_RETENTION_DAYS=90
COLLECTION_FAILURE_LOG_RETENTION_DAYS=180
RAW_RESPONSE_RETENTION_DAYS=30
DEBUG_LOG_RETENTION_DAYS=30
SCHEDULER_LOG_RETENTION_DAYS=30
ENABLE_RAW_RESPONSE_STORAGE=false
LEGACY_TABLE_FALLBACK_ENABLED=false
APP_ENV=production
FRONTEND_PORT=8080
```

실행 순서는 아래가 가장 단순합니다.

```bash
# 1. Docker daemon 실행
# 권장 예시 (Colima)
colima start --cpu 4 --memory 8 --disk 60
docker context use colima

# 2. 전체 스택 기동
docker compose up --build -d

# 3. 상태 확인
docker compose ps
docker compose logs -f backend worker frontend

# 4. 초기 데이터 수집
make collect
```

접속 주소:

- 대시보드: `http://localhost:8080`
- API 문서: `http://localhost:8000/api/docs`
- 헬스체크: `http://localhost:8000/health`

`make` 명령을 쓰고 싶다면 아래만 기억하면 됩니다.

```bash
make doctor   # Docker/Colima 상태 점검
make up       # compose up -d
make logs     # 전체 로그
make collect  # morning -> noon -> evening batch 순차 실행
make collect-weekly
make down     # 종료
```

## 수집 운영 정책

- 기본 운영 단위는 개별 collector가 아니라 `morning / noon / evening / weekly` batch입니다.
- 실시간성보다 유지보수성과 provider 호출량 절감을 우선합니다.
- provider 호출 여부는 beat schedule이 아니라 `collection_runs` 기반 guard가 최종 결정합니다.
- 개별 collector task는 디버깅/수동 실행 용도로 남아 있지만, 기본 운영 schedule에는 사용하지 않습니다.
- 같은 job은 최근 `success` run이 최소 간격 안에 있으면 `skipped` 처리됩니다.
- worker 재시작, 수동 실행, 중복 beat 상황에서도 동일 `job_key`는 advisory lock 또는 local lock으로 중복 실행을 피합니다.

## 수집 스케줄 (KST)

| Batch | 시각 | 포함 작업 |
|---|---|
| Morning batch | 매일 07:30 | 전일 미국장/글로벌 데이터, FRED rates/macro/credit, sector, FedWatch, FX, news, snapshot, daily insight trigger hook |
| Noon batch | 매일 12:30 | news, FX, snapshot |
| Evening batch | 매일 18:30 | KR/Asia market data, FX, news, snapshot |
| Weekly batch | 매주 월요일 08:00 | FOMC calendar, event/maintenance hook |
| Cleanup schedule | 매일 03:05 | retention cleanup |

> FedWatch 확률은 공식 CME 상세 확률표가 아니라 공개 Fed Funds futures 가격과 최신 DFF 기준의 추정값입니다.

Celery 설정 메모:

- `timezone="Asia/Seoul"`을 유지합니다.
- `enable_utc=True`여도 beat의 `crontab(...)` 시간은 위 timezone 기준으로 해석되도록 설정했습니다.

## Provider Guard

`collection_runs` 테이블과 collection guard가 provider 호출을 제한합니다.

기본 최소 간격:

- FRED rates/macro/credit: `1440`분
- FX: `360`분
- equity/sector: `720`분
- FedWatch: `720`분
- news: `360`분
- FOMC calendar: `10080`분
- snapshot compute: `180`분

동작 방식:

- 최근 `success` run이 최소 간격 안에 있으면 provider 호출 없이 `skipped` 처리합니다.
- `failed` run만 있는 경우에는 재실행을 허용합니다.
- lock 획득에 실패하면 `failed`가 아니라 `skipped`로 기록합니다.
- 수동 실행과 batch 연속 실행(`make collect-all-batched`)에서도 guard가 중복 호출을 막습니다.

## Observation 저장 정책

- 반복 수집되는 시계열 observation 성격의 테이블은 지표 키와 관측 날짜 기준으로 `UNIQUE` 제약을 둡니다.
- 같은 지표와 같은 날짜 데이터를 다시 수집하면 새 row를 추가하지 않고 기존 row를 `upsert`로 갱신합니다.
- 따라서 revision이나 장중 재수집으로 값이 바뀌면 기존 row의 값이 최신 수집 결과로 업데이트됩니다.
- 중복 row 정리와 upsert는 적용되어 있으며, retention/cleanup은 비시계열 파생 데이터에만 제한적으로 적용됩니다.

## 수동 수집 명령

```bash
make collect-morning
make collect-noon
make collect-evening
make collect-weekly
make collect-all-batched
```

- `make collect`: `morning -> noon -> evening` batch를 순차 실행합니다.
- `make collect-weekly`: FOMC calendar와 주간 maintenance hook만 실행합니다.
- 개별 batch를 연속 실행해도 guard가 같은 provider를 과도하게 재호출하지 않도록 설계되어 있습니다.

## DB Retention

- `interest_rates`, `macro_indicators`, `credit_spreads`, `equity_indices`, `sector_performance`, `exchange_rates`, `real_economy`, `fed_watch` 같은 observation 시계열 데이터는 장기 보관합니다.
- 수집 로그/파생 임시 데이터 성격의 테이블은 retention 정책에 따라 정리합니다.
- 현재 프로젝트에는 별도 `raw_responses` 영구 저장 테이블이 없으므로, `ENABLE_RAW_RESPONSE_STORAGE=false`가 기본이며 raw response cleanup 대상도 현재는 `0`건입니다.
- `news_items`는 현재 스키마에서 반복 수집으로 계속 증가하는 대표적인 비시계열 수집 payload 테이블이라 retention 대상으로 취급합니다.
- `change_snapshots`, `sentiment_signals`, `divergence_events`, `divergence_reports`, `ai_summaries`는 재생성 가능하거나 파생 성격이 강하므로 retention 대상으로 정리합니다.

기본값:

- `COLLECTION_SUCCESS_LOG_RETENTION_DAYS=90`
- `COLLECTION_FAILURE_LOG_RETENTION_DAYS=180`
- `RAW_RESPONSE_RETENTION_DAYS=30`
- `DEBUG_LOG_RETENTION_DAYS=30`
- `SCHEDULER_LOG_RETENTION_DAYS=30`
- `ENABLE_RAW_RESPONSE_STORAGE=false`

정리 기준 timestamp:

- `news_items`: `collected_at`
- `change_snapshots`: `snapshot_date`
- `sentiment_signals`: `extracted_at`
- `divergence_events`: `detected_at`
- `divergence_reports`: `generated_at`
- `ai_summaries`: `created_at`

운영 메모:

- raw response 저장은 기본적으로 꺼두는 것을 권장합니다.
- 배포 환경에서는 retention 외에도 DB storage limit과 backup 정책을 별도로 점검해야 합니다.
- 로컬 개발 환경은 Colima 위 Docker 컨테이너 실행을 전제로 합니다.
- `docker compose down -v`는 DB volume을 삭제할 수 있으므로 사용에 주의해야 합니다.
- `colima stop`, `colima start`, `colima restart`는 사용자가 직접 판단해 실행해야 하며 자동 테스트 절차에 포함하지 않습니다.

수동 cleanup 실행:

```bash
cd backend
../.venv/bin/python -m app.services.cleanup_service
```

Docker 컨테이너 내부 cleanup 실행:

```bash
docker compose exec worker python -m app.services.cleanup_service
```

Docker/Colima 기준 검증 절차:

```bash
# 1. 로컬 단위 테스트
cd backend
../.venv/bin/python -m unittest discover -s tests

# 2. 컨테이너 상태 확인
docker compose ps

# 3. backend 컨테이너 내부 테스트
docker compose exec backend python -m unittest discover -s tests

# 4. worker 컨테이너에서 cleanup 수동 실행
docker compose exec worker python -m app.services.cleanup_service
```

후속 TODO:

- 현재 raw response 영구 저장 구조는 없으므로, 필요 시 별도 테이블과 opt-in 저장 전략을 후속 작업에서 검토합니다.
- 고급 storage 모니터링과 장기 추세 분석은 후속 작업으로 넘깁니다.

## DB Operations

- 운영 정보는 보안상 인증 없는 admin API로 노출하지 않습니다.
- 현재는 CLI와 Makefile 방식만 제공합니다.
- 상세 운영 가이드는 [docs/db-management.md](/Users/yuk/DevFolder/CodePractice/WorkingProject/MacroAnalysis/docs/db-management.md) 를 참고하세요.

주요 명령:

```bash
make db-size
make db-stats
make db-cleanup
make db-deduplicate-check
```

- `make db-size`: 전체 DB 크기와 큰 테이블 요약
- `make db-stats`: 테이블별 크기, 인덱스 크기, row 수 추정치, 최근 cleanup 결과
- `make db-cleanup`: retention cleanup 수동 실행
- `make db-deduplicate-check`: unique key 기준 중복 후보 read-only 점검

로컬 검증 명령 순서:

```bash
docker compose up -d
make migrate
make collect
make collect
make db-deduplicate-check
make db-size
make db-stats
make db-cleanup
make test
```

- `docker compose up -d`: 로컬 Docker/Colima 스택 기동
- `make migrate`: 최신 Alembic migration 반영
- `make collect`: 수집 실행
- `make collect` 다시 실행: 중복 방지/upsert 재확인
- `make db-deduplicate-check`: 중복 후보가 남아 있는지 read-only 점검
- `make db-size`: 전체 DB 크기와 큰 테이블 확인
- `make db-stats`: 테이블별 세부 DB 상태 확인
- `make db-cleanup`: retention cleanup 수동 실행
- `make test`: backend 테스트 실행

## 확인 결과

로컬 코드 기준으로 확인한 내용은 아래와 같습니다.

- `docker compose config`: 성공
- `backend` 단위 테스트: `cd backend && python3 -m unittest discover -s tests` 성공
- `docker compose up --build -d`: 이 세션에서는 Docker daemon 소켓(`/var/run/docker.sock`)에 연결되지 않아 실제 기동 확인은 미완료

즉, compose 파일 문법과 백엔드 기본 테스트는 통과했지만, 실제 컨테이너 기동 여부는 Docker daemon이 살아 있는 로컬 환경에서 한 번 더 확인해야 합니다.
