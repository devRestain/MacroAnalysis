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
5. 초기 데이터는 비어 있으므로, 실제 화면 데이터를 보려면 `make collect` 또는 개별 Celery 호출이 필요합니다.

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
make collect  # 수집 즉시 실행
make down     # 종료
```

## 수집 스케줄 (KST)

| 데이터 | 시각 |
|---|---|
| 미국 증시 / 섹터 / 스냅샷 | 매일 07:00 전후 |
| 환율 | 매일 09:00 |
| FRED 거시 지표 | 매일 06:00 |
| FedWatch 확률 | 매일 08:00 |
| 뉴스 | 매 시간 |
| AI 요약 | 매일 06:30 |
| FOMC 캘린더 | 매주 월요일 |

> FedWatch 확률은 공식 CME 상세 확률표가 아니라 공개 Fed Funds futures 가격과 최신 DFF 기준의 추정값입니다.

## 확인 결과

로컬 코드 기준으로 확인한 내용은 아래와 같습니다.

- `docker compose config`: 성공
- `backend` 단위 테스트: `cd backend && python3 -m unittest discover -s tests` 성공
- `docker compose up --build -d`: 이 세션에서는 Docker daemon 소켓(`/var/run/docker.sock`)에 연결되지 않아 실제 기동 확인은 미완료

즉, compose 파일 문법과 백엔드 기본 테스트는 통과했지만, 실제 컨테이너 기동 여부는 Docker daemon이 살아 있는 로컬 환경에서 한 번 더 확인해야 합니다.
