.PHONY: help doctor check-docker up down build logs shell-backend shell-db seed collect

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
	@echo "  make collect     데이터 수집 즉시 실행"
	@echo "  make shell       백엔드 컨테이너 쉘 접속"
	@echo "  make shell-db    PostgreSQL 접속"
	@echo ""

doctor: check-docker
	@echo "  Docker daemon: ok"
	@echo "  Compose: $(COMPOSE)"

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

up: check-docker
	@cp -n .env.example .env 2>/dev/null || true
	$(COMPOSE) up -d
	@echo ""
	@echo "  ✓ MacroWatch started"
	@echo "  → Frontend: http://localhost:8080"
	@echo "  → API Docs: http://localhost:8000/api/docs"
	@echo ""

down: check-docker
	$(COMPOSE) down

build: check-docker
	$(COMPOSE) build --no-cache

logs: check-docker
	$(COMPOSE) logs -f

collect: check-docker
	@echo ">>> 데이터 즉시 수집 실행..."
	$(COMPOSE) exec worker celery -A app.workers.celery_app.celery call app.workers.celery_app.task_collect_fred
	$(COMPOSE) exec worker celery -A app.workers.celery_app.celery call app.workers.celery_app.task_collect_equity
	$(COMPOSE) exec worker celery -A app.workers.celery_app.celery call app.workers.celery_app.task_collect_fx
	$(COMPOSE) exec worker celery -A app.workers.celery_app.celery call app.workers.celery_app.task_collect_news
	$(COMPOSE) exec worker celery -A app.workers.celery_app.celery call app.workers.celery_app.task_compute_snapshots
	@echo ">>> 수집 완료"

shell: check-docker
	$(COMPOSE) exec backend bash

shell-db: check-docker
	$(COMPOSE) exec postgres psql -U macro -d macrodb
