# DB Management Guide

MacroWatch는 기본적으로 운영 정보를 외부 API로 공개하지 않고, CLI와 Makefile 중심으로 DB 상태를 점검합니다.

## 운영 명령

- `make db-size`
  - 전체 DB 크기와 큰 테이블 요약을 확인합니다.
- `make db-stats`
  - 테이블별 크기, 인덱스 크기, row 수 추정치, 최근 cleanup 결과를 확인합니다.
- `make db-cleanup`
  - retention 기준에 따라 로그성/파생 데이터를 정리합니다.
  - observation 시계열 데이터는 삭제하지 않습니다.
- `make db-deduplicate-check`
  - unique key 기준 중복 후보를 read-only로 점검합니다.

직접 실행 예시:

```bash
cd backend
python -m app.commands.db_stats --top 10
python -m app.commands.db_stats --size-only
python -m app.commands.db_cleanup --json
python -m app.commands.db_deduplicate_check --json
```

## 로컬 Docker / Colima

기본 점검:

```bash
docker system df
docker system df -v
docker volume ls
docker compose ps
```

중요한 차이:

- `docker compose down`
  - 컨테이너와 네트워크만 내립니다. volume은 유지됩니다.
- `docker compose down -v`
  - volume까지 삭제할 수 있으므로 PostgreSQL 데이터가 함께 사라질 수 있습니다.
  - DB를 유지해야 할 때는 사용에 주의해야 합니다.

Colima 운영 메모:

- `colima stop`
  - VM을 중지해 메모리와 배터리 사용을 줄이는 데 도움이 됩니다.
- `colima start`
  - 다시 시작한 뒤 `docker compose up -d`로 서비스를 재개할 수 있습니다.
- `colima ssh`
  - 일반 운영 절차에는 포함하지 않습니다. 필요 시 사용자 판단 하에만 사용합니다.

로컬 검증 순서:

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

설명:

- `docker compose up -d`: 로컬 스택을 올립니다.
- `make migrate`: Alembic migration을 적용합니다.
- `make collect`: 수집을 실행합니다.
- `make collect` 다시 실행: upsert와 중복 방지 동작을 다시 확인합니다.
- `make db-deduplicate-check`: 중복 후보가 남아 있는지 read-only로 점검합니다.
- `make db-size`: 전체 크기와 큰 테이블을 간단히 봅니다.
- `make db-stats`: 더 자세한 DB 상태를 확인합니다.
- `make db-cleanup`: retention cleanup을 수동 실행합니다.
- `make test`: backend 테스트를 실행합니다.

## 배포 환경 가이드

특정 플랫폼 종속 기능 대신 공통 체크리스트를 따릅니다.

- DB storage limit을 먼저 확인합니다.
- 자동 백업 지원 여부를 확인합니다.
- 백업 보관 기간을 확인합니다.
- migration 전에는 백업 또는 snapshot을 권장합니다.
- retention 환경변수를 운영 환경에 맞게 조정합니다.
- raw response 저장은 기본 비활성화를 권장합니다.
- DB 크기 증가 추세를 주기적으로 모니터링합니다.
- 무료/저가 플랜에서는 로그성 데이터가 storage limit에 빠르게 도달할 수 있습니다.

권장 운영 습관:

- 주기적으로 `db-size`, `db-stats`, `db-cleanup`을 실행하거나 스케줄 로그를 확인합니다.
- 가장 큰 테이블이 observation 계열인지 로그성/파생 계열인지 구분해 봅니다.
- cleanup 결과에서 `debug_logs_deleted`, `scheduler_logs_deleted`, `collection_*_deleted` 추세를 확인합니다.
- 배포 환경에서 DB 연결 문자열과 백업 정책을 분리 관리합니다.

## 보안 메모

- 현재는 보안상 인증 없는 admin API를 제공하지 않습니다.
- 운영 정보 조회는 CLI와 Makefile 방식만 제공합니다.
