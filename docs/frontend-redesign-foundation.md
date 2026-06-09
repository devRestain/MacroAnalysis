# Frontend Redesign Foundation

작성일: 2026-06-09  
대상 프로젝트: `MacroWatch` / `MacroAnalysis`

## 1. 목적

현재 프론트엔드는 초기 대시보드 중심 구조를 유지하고 있으나, 백엔드와 DB는 이미 다음 방향으로 확장되어 있다.

- `observations + indicators` 기반의 시계열 source of truth 정착
- `indicator_explanations` 기반 정적 설명 메타데이터 도입
- `expectations`, `divergence_events`, `divergence_reports` 기반 심리/괴리 분석 계층 추가
- `daily_insights` 기반 AI 일일 브리핑 정비

즉, 현재 프론트엔드는 "요약 대시보드"에는 맞지만, 현재 백엔드가 제공하는 구조화된 도메인 모델을 반영하지 못하고 있다.  
이 문서는 추후 전달될 상세 프론트 설계 청사진과 논의를 수용하기 전에, 현재 코드 기준으로 재설계 필요 영역과 준비 작업을 정리한 기초 계획서다.

## 2. 현재 코드베이스 진단 요약

### 2.1 프론트 구조

현재 프론트엔드는 아래 특성을 가진다.

- 라우팅은 `frontend/src/App.tsx`에서 직접 분기하는 단순 구조
- 주요 화면은 `Home`, `News`, `Fomc` 3개뿐
- `Home` 화면은 zone 컴포넌트 6개와 오버레이 패널 3개로 조립됨
- 데이터 패칭은 커스텀 `useApi` 훅과 `fetch` 기반 최소 구현
- 상태 관리, 서버 상태 캐시 전략, 도메인 모델 계층이 사실상 없음

이 구조는 빠른 MVP에는 적합하지만, 도메인 확장과 화면 다양화에는 취약하다.

### 2.2 백엔드 구조 변화가 프론트에 미치는 영향

백엔드는 이미 아래 구조를 중심으로 재편되고 있다.

- 기본 조회 source of truth: `indicators`, `observations`, `signals`
- 대시보드용 adapter: `observation_query_service`
- 정적 지표 설명 API: `/api/indicator-explanations`
- 심리/기대/괴리 API: `/api/expectations`, `/api/divergence`
- AI 브리핑 API: `/api/ai/summary`, `/api/ai/summary/ensure`

하지만 프론트는 여전히 아래 엔드포인트에 거의 전부 의존한다.

- `/api/summary`
- `/api/changes`
- `/api/chart/{indicator_key}`
- `/api/news`
- `/api/sectors`
- `/api/fomc`
- `/api/ai/summary`
- `/api/ai/chat`

즉, 프론트가 새 도메인 구조를 직접 소비하지 못하고, 대시보드 집계 응답에 과도하게 결합되어 있다.

## 3. 현재 프론트의 미흡한 부분

### 3.1 정보 구조가 대시보드 1페이지 중심에 고정됨

현재 `Home`은 하나의 화면에 다음을 동시에 담고 있다.

- 이상 신호
- 핵심 지표 카드
- 수익률 곡선
- AI 헤드라인
- 뉴스 미리보기
- 전체 변화량 테이블
- 섹터 강도
- 글로벌 지수

문제는 이것이 "사용자 목표별 탐색"이 아니라 "한 번에 다 보여주기" 방식이라는 점이다.  
백엔드가 richer domain을 갖게 된 현재 시점에는 다음과 같은 탐색 단위가 필요하다.

- 지표 중심 탐색
- 카테고리 중심 탐색
- 이벤트 중심 탐색
- 해석 중심 탐색
- AI 브리핑/괴리 탐지 중심 탐색

### 3.2 상세 패널이 시계열 차트 외 맥락을 제공하지 못함

`SidePanel`은 사실상 아래만 보여준다.

- 현재값
- z-score
- 기간 선택
- 단일 라인 차트

누락된 정보는 아래와 같다.

- 지표 설명 및 해석 문맥
- 왜 중요한지
- 상승/하락 시 의미
- 관련 지표
- 최근 신호 요약
- 데이터 최신성/주기/frequency/source
- 동일 카테고리 내 상대 비교

현재 백엔드의 `indicator_explanations`는 바로 이 문제를 해결할 준비가 되어 있지만, 프론트가 아직 연결하지 못하고 있다.

### 3.3 새 도메인 API가 전혀 표면화되지 않음

현재 프론트는 아래 도메인 기능을 전혀 드러내지 못한다.

- expectation 시계열
- divergence 이벤트 및 severity
- divergence report 기반 해석
- observation 중심 메타데이터
- indicator explanation metadata

이 때문에 DB/백엔드 구조 개편의 상당 부분이 사용자 경험으로 전환되지 못하고 있다.

### 3.4 하드코딩이 많아 도메인 변경 흡수력이 낮음

하드코딩된 지점 예시:

- 핵심 카드 키 목록 (`Zone2Grid`)
- 글로벌 지수 메타 (`Zone6Equities`)
- 수익률 곡선 key 매핑 (`Zone3Trio`)
- 섹터 표시 방식 (`Zone5Sectors`)
- 카테고리 라벨 매핑 (`News`, `Zone4Heatmap`)

이 구조는 DB나 API에서 지표 정의가 바뀌었을 때 프론트 수정을 반복적으로 요구한다.

### 3.5 프론트 타입이 백엔드 응답의 집계형 DTO에만 맞춰져 있음

`frontend/src/lib/api.ts`의 타입은 대부분 현재 응답 형태를 직접 반영한 DTO다.  
문제는 프론트 내부에서 별도의 도메인 모델 변환층이 없다는 점이다.

결과적으로 아래 문제가 생긴다.

- API 응답이 바뀌면 컴포넌트가 직접 깨짐
- 같은 의미의 데이터를 화면별로 재해석하기 어려움
- 백엔드의 정규화 모델과 프론트 UI 모델이 분리되지 않음

### 3.6 상태 관리와 오류 처리 전략이 부족함

현재 `useApi`는 최소한의 fetch wrapper다.

- 로딩/에러/재시도 정책이 일관되지 않음
- 캐시 무효화 전략이 없음
- 병렬 요청 중복 제어가 없음
- 실패 원인별 UX 분기가 어려움
- AI 비활성화/데이터 없음/일시 장애를 구분하기 어려움

### 3.7 내비게이션과 화면 확장성이 낮음

현재는 사실상 해시/경로 문자열 수동 분기 방식이라서 다음 확장에 불리하다.

- 지표 상세 페이지
- 카테고리별 뷰
- divergence 전용 화면
- AI 브리핑 아카이브
- 설명/메타데이터 탐색 화면

## 4. 재설계의 핵심 방향

### 4.1 프론트를 "대시보드 묶음"에서 "도메인 탐색 UI"로 전환

재설계 목표는 단순 미관 개선이 아니라 정보 구조 전환이어야 한다.

- 기존: 한 화면에서 모든 것을 압축 노출
- 변경: 사용자 질문과 분석 흐름에 맞는 탐색 구조 제공

권장 상위 정보 구조 초안:

- Dashboard: 오늘의 핵심 상황 요약
- Indicators: 지표 탐색/비교/상세
- Signals: 이상 신호, 변화량, 위험 레벨
- Expectations: actor/dimension별 기대 흐름
- Divergence: 괴리 이벤트와 리포트
- Briefing: AI 일일 브리핑 및 대화형 탐색
- News & Events: 뉴스/FOMC 및 이벤트 문맥

### 4.2 API 응답과 UI 사이에 도메인 어댑터 계층 도입

프론트 내부에는 최소한 다음 레이어 구분이 필요하다.

- `api client`: HTTP 호출
- `query hooks`: 서버 상태 관리
- `adapters`: API DTO -> 프론트 도메인 모델 변환
- `view models`: 화면 조합용 파생 데이터
- `presentational components`: 순수 UI

이 레이어를 만들면 백엔드의 응답 변화가 컴포넌트 전역으로 퍼지는 것을 줄일 수 있다.

### 4.3 indicator explanation을 중심으로 상세 경험 강화

지표 상세 경험은 차트만 보여주는 수준에서 아래 구성으로 확장하는 것이 좋다.

- 현재값 및 변화
- 시계열 차트
- 지표 설명
- 높을 때/낮을 때 의미
- watch points
- 관련 지표 링크
- 최근 신호/요약
- 데이터 출처 및 업데이트 정보

이는 현재 백엔드 capability와 가장 자연스럽게 맞물리는 첫 번째 개편 축이다.

### 4.4 expectation/divergence를 신규 1급 화면으로 승격

최근 DB/백엔드 변경에서 가장 큰 신규 가치 영역은 expectation/divergence다.  
따라서 이 기능은 숨겨진 API로 남겨두지 말고, 재설계 시 독립 내비게이션 단위로 올려야 한다.

초기 화면 아이디어:

- actor x dimension matrix
- 최근 divergence feed
- severity별 필터
- divergence report 카드
- 시계열 흐름과 당일 이벤트 연결

### 4.5 요약 응답 의존도를 줄이고 세분화된 쿼리 설계로 이동

`/summary`는 여전히 첫 진입용으로 유효하지만, 화면 전체의 유일한 데이터 계약이 되어서는 안 된다.

권장 방향:

- 홈 대시보드는 summary 기반 유지 가능
- 상세 화면은 목적별 endpoint를 직접 사용
- 프론트 내부에서 점진적으로 summary coupling 축소

## 5. 우선 반영해야 할 프론트 아키텍처 초안

### 5.1 폴더 구조 초안

```text
frontend/src/
├── app/
│   ├── router/
│   ├── providers/
│   └── layout/
├── domains/
│   ├── dashboard/
│   ├── indicators/
│   ├── signals/
│   ├── expectations/
│   ├── divergence/
│   ├── briefing/
│   └── news/
├── shared/
│   ├── api/
│   ├── ui/
│   ├── hooks/
│   ├── utils/
│   └── types/
└── pages/
```

핵심은 "컴포넌트 종류"가 아니라 "도메인 기준"으로 코드를 나누는 것이다.

### 5.2 데이터 계층 초안

권장 준비 항목:

- `api.ts` 단일 파일 구조 해체
- endpoint별 client 모듈 분리
- DTO 타입과 UI 타입 분리
- adapter 함수 도입
- query key 체계 수립

가능한 모듈 예시:

- `shared/api/dashboard.ts`
- `shared/api/indicators.ts`
- `shared/api/explanations.ts`
- `shared/api/expectations.ts`
- `shared/api/divergence.ts`
- `shared/api/briefing.ts`

### 5.3 라우팅 초안

현 시점에서는 최소 아래 라우트 단위를 상정하는 것이 좋다.

- `/`
- `/indicators`
- `/indicators/:indicatorKey`
- `/signals`
- `/expectations`
- `/divergence`
- `/briefing`
- `/news`
- `/fomc`

### 5.4 디자인 시스템 준비

현재 UI는 Tailwind utility 중심이지만, 화면이 커질수록 의미 단위 컴포넌트가 필요하다.

우선 정의할 항목:

- page shell
- section header
- metric card
- data state block
- filter bar
- info panel
- chart container
- badge/severity token
- empty/error/loading state

## 6. 단계별 개편 계획 초안

### Phase 0. 정렬 및 계약 확인

- 현재 API 목록과 응답 shape 재정리
- 프론트에서 실제 사용하는 엔드포인트와 미사용 엔드포인트 구분
- 백엔드 source of truth와 프론트 용어 불일치 정리
- 추후 전달될 ChatGPT 설계 청사진과 본 문서 병합

### Phase 1. 기반 공사

- 라우팅 체계 정비
- 도메인 폴더 구조 생성
- 공통 query/data adapter 계층 도입
- 공통 레이아웃/상태 컴포넌트 정비

### Phase 2. 지표 상세 경험 재구성

- `indicator_explanations` 연결
- 기존 `SidePanel` 대체 또는 확장
- 차트 + 설명 + 관련 지표 + 메타데이터 결합
- 지표 상세 페이지 신설 여부 결정

### Phase 3. 대시보드 재설계

- 홈 화면에서 과밀한 정보 구조 재배치
- 핵심 KPI, 위험 신호, 브리핑, 이벤트를 역할별로 분리
- summary 의존성 최소화

### Phase 4. 신규 분석 화면 추가

- expectations 화면
- divergence 화면
- AI briefing 강화 화면

### Phase 5. 품질 보강

- 빈 상태/오류 상태 체계화
- 로딩 UX 정리
- 모바일 대응 정비
- 시각적 일관성 정리

## 7. 추후 상세 설계 논의 시 반드시 확인할 항목

이 항목들은 다음 설계 청사진 수신 후 우선 결정해야 한다.

- `react-router` 도입 여부
- 서버 상태 라이브러리 도입 여부
  - 예: TanStack Query
- 차트 라이브러리 유지 여부
  - 현재 `chart.js`
- `summary` endpoint의 장기 역할
  - 유지 / 축소 / 대체
- 지표 상세를 drawer로 유지할지 page로 승격할지
- expectation/divergence의 기본 진입 정보 구조
- AI 기능 비활성 상태의 UX 정책
- 모바일 우선 여부와 데스크톱 분석형 레이아웃 우선 여부

## 8. 즉시 실행 가능한 준비 작업

실제 대개편 전에 바로 할 수 있는 준비 작업은 아래와 같다.

- 현재 프론트에서 사용하는 API 계약 문서화
- indicator key, category, label 하드코딩 위치 목록화
- 미사용 백엔드 API를 프론트 요구사항 관점에서 재분류
- 상세 패널에서 필요한 explanation 필드 매핑 정의
- expectation/divergence용 UI 요구 데이터 shape 초안 작성

## 9. 현재 기준 권장 결론

현재 프론트는 "동작하는 요약 대시보드"로서는 충분하지만, 지금의 백엔드/DB 구조를 담기에는 정보 구조와 데이터 계층이 모두 얕다.  
따라서 다음 개편은 단순 컴포넌트 수정이 아니라 아래 두 축을 함께 다루는 재설계여야 한다.

- 정보 구조 재편
- 데이터/도메인 계층 재정렬

추후 ChatGPT에서 정리한 프론트 설계 청사진이 도착하면, 이 문서를 기반으로 다음 작업으로 바로 이어갈 수 있다.

- 최종 IA 확정
- API 계약 매핑표 작성
- 우선 구현 순서 확정
- 실제 리팩터링 착수
