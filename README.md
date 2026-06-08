# MacroWatch

거시경제 지표 추적 시스템. FOMC, 금리, 환율, 증시, 크레딧 스프레드, 섹터 사이클을 매일 자동 수집하고 AI 요약 및 채팅을 제공합니다.

## 빠른 시작

```bash


# 2. VM 기반 Docker 런타임 시작 (권장: Colima)
colima start --cpu 4 --memory 8 --disk 60
docker context use colima

# 3. 전체 스택 시작
make up

# 4. 데이터 즉시 수집 (선택)
make collect
```

접속:
- 대시보드: http://localhost:8080
- API 문서: http://localhost:8000/api/docs

> 프런트 포트는 `.env`의 `FRONTEND_PORT`로 변경할 수 있습니다. VM/Colima 환경에서는 기본값 `8080`이 호스트의 privileged port 80 충돌을 피하기 좋습니다.

## API 키 발급 안내

| 서비스 | 무료 여부 | 링크 |
|---|---|---|
| FRED | 완전 무료 | https://fred.stlouisfed.org/docs/api/api_key.html |
| Finnhub | 무료 티어 있음 | https://finnhub.io/register |
| ExchangeRate-API | 무료 티어 / fallback 자동 | https://www.exchangerate-api.com |
| OpenAI | 유료 (AI 요약·채팅) | https://platform.openai.com |

> OpenAI 없이도 대시보드 데이터는 전부 동작합니다. AI 요약/채팅만 비활성화됩니다.

## 구조

```
MacroAnalysis/
├── backend/                # FastAPI + Celery
│   └── app/
│       ├── collectors/     # 데이터 수집 (FRED, yfinance, Finnhub 등)
│       ├── workers/        # Celery 태스크, AI 요약, 스냅샷 계산
│       ├── models/         # SQLAlchemy 모델
│       ├── api/            # REST 엔드포인트
│       └── core/           # 설정, DB, 캐시
├── frontend/               # React + Tailwind
│   └── src/
│       ├── components/     # Zone 컴포넌트 + 패널 (SidePanel, ChatDrawer)
│       ├── pages/          # Home
│       ├── hooks/          # useApi
│       └── lib/            # API 클라이언트, 유틸
└── docker-compose.yml
```

## 수집 스케줄 (KST)

| 데이터 | 시각 |
|---|---|
| 미국 증시 / 섹터 / 스냅샷 | 매일 07:00 |
| 환율 | 매일 09:00 |
| FRED 거시 지표 | 매일 06:00 |
| FedWatch 확률 | 매일 08:00 |
| 뉴스 | 매 시간 |
| AI 요약 | 매일 06:30 |
| FOMC 캘린더 | 매주 월요일 |

> FedWatch 확률은 공식 CME 상세 확률표가 아니라 공개 Fed Funds futures 가격과 최신 DFF 기준의 보수적 추정값입니다. 데이터가 불완전하면 확률을 생성하지 않습니다.

## Railway 배포 (선택)

```bash
# Railway CLI 설치 후
railway login
railway init
railway up

# 환경변수는 Railway 대시보드에서 .env 내용 입력
```
