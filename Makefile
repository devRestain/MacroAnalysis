.PHONY: help doctor check-docker check-env up down build logs shell-backend shell-db seed collect collect-fed collect-calendar collect-morning collect-noon collect-evening collect-weekly collect-all-batched collect-sentiment ensure-ai-insight shell migrate db-stats db-size db-cleanup db-deduplicate-check

COMPOSE := $(shell if docker compose version >/dev/null 2>&1; then echo "docker compose"; else echo "docker-compose"; fi)

help:
	@echo ""
	@echo "  MacroWatch — 주요 명령어"
	@echo "  ─────────────────────────────────────────────────"
	@echo "  make up          전체 스택 시작 (백그라운드)"
	@echo "  make doctor      Docker/Colima 실행 상태 확인"
	@echo "  make down        전체 스택 종료"
	@echo "  make build       Docker 이미지 빌드"
	@echo "  make logs        전체 로그 출력"
	@echo "  make collect     기본 batched 수집 즉시 실행 (morning -> noon -> evening)"
	@echo "  make collect-morning  morning batch 수동 실행"
	@echo "  make collect-noon     noon batch 수동 실행"
	@echo "  make collect-evening  evening batch 수동 실행"
	@echo "  make collect-calendar economic calendar batch 수동 실행"
	@echo "  make collect-weekly   weekly batch 수동 실행"
	@echo "  make collect-all-batched  morning -> noon -> evening batch 순차 실행"
	@echo "  make collect-sentiment sentiment/expectation 파이프라인 수동 실행"
	@echo "  make ensure-ai-insight  당일 AI insight ensure 실행"
	@echo "  make collect-fed  weekly/Fed 관련 batch 수동 실행"
	@echo "  make migrate     Alembic migration 적용"
	@echo "  make db-stats    DB 상태 상세 요약"
	@echo "  make db-size     DB 크기와 큰 테이블 요약"
	@echo "  make db-cleanup  retention cleanup 수동 실행"
	@echo "  make db-deduplicate-check  중복 후보 read-only 점검"
	@echo "  make shell       백엔드 컨테이너 쉘 접속"
	@echo "  make shell-db    PostgreSQL 접속"
	@echo ""

doctor: check-docker
	@echo "  Docker daemon: ok"
	@echo "  Compose: $(COMPOSE)"
	@test -f .env && echo "  .env: ok" || echo "  .env: missing"

check-docker:
	@docker info >/dev/null 2>&1 || ( \
		echo ""; \
		echo "  Docker daemon에 연결할 수 없습니다."; \
		echo "  Colima 사용 시:"; \
		echo "    colima start --cpu 4 --memory 8 --disk 60"; \
		echo "    docker context use colima"; \
		echo "    make up"; \
		echo ""; \
		exit 1; \
	)

check-env:
	@test -f .env || ( \
		echo ""; \
		echo "  .env 파일이 없습니다."; \
		echo "  로컬 전용 .env 파일을 직접 만든 뒤 다시 실행하세요."; \
		echo ""; \
		exit 1; \
	)

up: check-docker check-env
	$(COMPOSE) up -d --build
	@echo ""
	@echo "  ✓ MacroWatch started"
	@echo "  → Frontend: http://localhost:8080"
	@echo "  → API Docs: http://localhost:8000/api/docs"
	@echo ""

down: check-docker
	$(COMPOSE) down

build: check-docker check-env
	$(COMPOSE) build --no-cache

logs: check-docker
	$(COMPOSE) logs -f

collect: check-docker check-env
	@$(MAKE) collect-all-batched

collect-morning: check-docker check-env
	@echo ">>> morning batch 실행..."
	$(COMPOSE) exec backend python -m app.commands.collect_batches morning

collect-noon: check-docker check-env
	@echo ">>> noon batch 실행..."
	$(COMPOSE) exec backend python -m app.commands.collect_batches noon

collect-evening: check-docker check-env
	@echo ">>> evening batch 실행..."
	$(COMPOSE) exec backend python -m app.commands.collect_batches evening

collect-calendar: check-docker check-env
	@echo ">>> calendar batch 실행..."
	$(COMPOSE) exec backend python -m app.commands.collect_batches calendar

collect-weekly: check-docker check-env
	@echo ">>> weekly batch 실행..."
	$(COMPOSE) exec backend python -m app.commands.collect_batches weekly

collect-all-batched: check-docker check-env
	@echo ">>> batched 수집 실행 (morning -> noon -> evening)..."
	$(COMPOSE) exec backend python -m app.commands.collect_batches all-batched
	@echo ">>> batched 수집 완료"

collect-sentiment: check-docker check-env
	@echo ">>> sentiment/expectation 파이프라인 실행..."
	$(COMPOSE) exec backend python -m app.commands.run_sentiment_pipeline

collect-fed: check-docker check-env
	@$(MAKE) collect-weekly

ensure-ai-insight: check-docker check-env
	@echo ">>> daily insight ensure 실행..."
	$(COMPOSE) exec backend python -m app.commands.ensure_daily_insight

shell: check-docker
	$(COMPOSE) exec backend bash

shell-db: check-docker
	$(COMPOSE) exec postgres psql -U macro -d macrodb

migrate: check-docker check-env
	$(COMPOSE) exec backend alembic -c alembic.ini upgrade head

db-stats: check-docker check-env
	$(COMPOSE) exec backend python -m app.commands.db_stats --top 10

db-size: check-docker check-env
	$(COMPOSE) exec backend python -m app.commands.db_stats --size-only --top 10

db-cleanup: check-docker check-env
	@echo ">>> retention cleanup 실행 (observation 시계열 데이터는 삭제하지 않음)"
	$(COMPOSE) exec backend python -m app.commands.db_cleanup

db-deduplicate-check: check-docker check-env
	$(COMPOSE) exec backend python -m app.commands.db_deduplicate_check --sample-limit 5
