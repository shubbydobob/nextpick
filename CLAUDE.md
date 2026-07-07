# CANSLIM 스코어링 엔진 — 세션 진입점

## 프로젝트 개요
한국 주식시장 CAN SLIM 방법론 기반 자동 스코어링 시스템.
ETL(Python) → PostgreSQL → Scoring Engine(Spring Boot) → Screener UI(React)

**현재**: 운영 배포 중 (NEXTPICK · k-stock-score.vercel.app). 프론트=React 실서비스(mockData 아님).

---

## 🔴 운영/실시간 아키텍처 (2026-07 세션 정리 — 반드시 숙지)

### 배포·인프라
- **운영 서버**: EC2 `13.209.47.193` (ubuntu, `/home/ubuntu/canslim`). Docker: `canslim-postgres` + `canslim-backend`(8080). 프론트=Vercel(자동배포).
- **이 샌드박스는 EC2에 직접 접속 불가**(아웃바운드 allowlist). 서버 작업은 **GitHub Actions로만** 가능:
  - `.github/workflows/deploy.yml` — master의 `backend/**` 변경 시 SSH→`git pull`+`docker compose up --build backend`.
  - **운영 ops 워크플로우(workflow_dispatch, EC2_HOST/EC2_SSH_KEY 시크릿 사용)**:
    - `db-status.yml` — 운영 DB 상태 읽기 진단(테이블/점수/가격/프로세스). **서버 확인은 이걸로.**
    - `recover.yml` — 가격→수급→정규화→파생→채점 지정일 복구.
    - `rescore.yml` — 정규화+파생+채점만.
    - `backfill.yml` — 10년 백필(`--rebuild` opt-in).
  - MCP `mcp__github__actions_run_trigger`로 트리거, `get_job_logs`로 결과 확인.

### ETL 스케줄 (전부 서버·평일, 사용자 PC 무관)
- **16:10 KST 크론** → `run_daily` (가격→수급→DART→정규화→파생→채점트리거). 가격·수급은 ~16:25 완료, DART 이후.
- **18:30 KST** 백엔드 `@Scheduled ScoringJob` 재채점(안전망).
- **매월 1~7일**: `_maybe_reset_dart_ingestion`이 DART 전량 재수집(수 시간) → 그동안 채점/재무 지연.

### 실시간 vs 배치
- **스코어(종합·C/A/N/S/L/I) = 일 1회 배치**(장중 고정). CANSLIM 특성상 정상.
- **가격·등락률·거래량·거래대금 = KIS 15초 실시간 오버레이(장중 09:00~15:30만)**. 장 마감 후엔 KIS가 실시간 안 줘서 종가(배치) 표시.
- 대시보드: 상한가섹션·TOP랭킹 등락률 실시간 오버레이. **업종 히트맵 = KIS 업종지수(FHPUP02100000) 실시간**(`/api/macro/sectors`).

### 이번 세션 주요 픽스 (모두 master 반영)
- `run_daily`: 월요일 종목수집(FinanceDataReader) 크래시가 전 파이프라인 죽이던 것 → try/except 비치명적.
- `financial_normalizer`: 전분기 EPS≈0일 때 eps_qoq_yoy_pct 폭발→NUMERIC(10,4) 오버플로우로 정규화 전체 롤백(C/A 전멸) → **±9999 클램프**.
- `run_backfill_10yr`: TRUNCATE-먼저-후-실패로 운영 비우던 것 → 기본 안전(upsert), `--rebuild` opt-in.
- `finance-datareader` requirements 누락 추가.
- `/stats`·`/limit-up`: 가격을 score_date 정확일치→**최신 2거래일(cur/prev)** & limit-up은 **최신 가격일 앵커**(채점 지연 시 stale 상한가 방지).
- 프론트: 모바일 카드/하단탭바 반응형(토스풍), 스크리너 하단 가로스크롤바 sticky, 상한가 섹션.

### 알려진 데이터 함정
- **거래정지 종목**: 정지 기간 종가 고정+거래량 0, 재개일 폭등(예: 제이케이시냅스 060230 299→1172=+292%). "상한가" 아님(제한폭 초과). limit-up은 최신 가격일 앵커로 자연 배제.
- **채점 지연**: 가격은 최신일(예 07-07)인데 canslim_scores는 이전일(07-06)일 수 있음(DART 재수집 등). 헤더 "매일 갱신" 날짜 = 최신 채점일.

### 미해결/주의
- **가격 실시간 반영 지연**(사용자 리포트) — 조사 중. 장중 KIS 오버레이 vs 배치 anchoring 확인 필요.
- 스크리너 리스트 changeRate는 loadPriceAndFlow가 score_date 앵커 → 채점 지연 시 리스트도 이전일 등락 보일 수 있음(상한가섹션만 최신가격 앵커로 고침).

---

## 빠른 명령어

### ETL
```bash
cd /c/Projects/canslim
PYTHONUTF8=1 python etl/kr_adapter/investor_flow_loader.py   # KIS 수급
PYTHONUTF8=1 python etl/kr_adapter/dart_loader.py             # DART 재무
PYTHONUTF8=1 python etl/kr_adapter/run_backfill_10yr.py       # 10년 백필
```

### Spring Boot
```bash
cd backend && DB_PASSWORD=1234 mvn spring-boot:run
curl -s -X POST http://localhost:8080/api/admin/scoring/run   # 스코어링 실행
```

### DB 확인
```bash
psql -U canslim_user -d canslim -c "SELECT COUNT(*) FROM canslim_scores;"
psql -U canslim_user -d canslim -c "SELECT ticker, composite_score FROM canslim_scores ORDER BY composite_score DESC LIMIT 10;"
```

### 슬래시 커맨드
| 커맨드 | 설명 |
|--------|------|
| `/etl-run` | KIS + DART ETL 실행 |
| `/score-run` | 스코어링 트리거 + Top 10 출력 |
| `/db-check` | 주요 테이블 row 수 확인 |
| `/backfill` | 10년 백필 실행 |
| `/gap-status` | 미구현 GAP 현황 분석 |

---

## 미구현 GAP (Phase 4 목표)

| # | GAP | 담당 에이전트 |
|---|-----|--------------|
| 1 | EDGAR Java compile error (JdbcFinancialHistoryRepository 미구현) | @debugger + @persistence-designer |
| 2 | ScreenerView mockData → 실제 `/api/screener` 연동 | @frontend-integrator |
| 3 | completeness_discount Stage 2 미구현 (C/A null 시 감산) | @strategy-architect + @executor |

---

## 에이전트 라우팅

| 작업 | 에이전트 |
|------|---------|
| 코드/파일 탐색 | `@explore` |
| 명령 실행, 빌드 | `@executor` |
| 버그 원인 분석 | `@debugger` |
| 설계 결정 | `@architect` |
| 코드 리뷰 | `@code-reviewer` |
| 테스트 작성 | `@test-engineer` |
| 커밋/브랜치 | `@git-master` |
| API/E2E 검증 | `@qa-tester` |
| ETL 파이프라인 전체 | `@etl-orchestrator` |
| 프론트 API 연동 | `@frontend-integrator` |
| 스코어 분석 | `@scoring-analyst` |
| CAN SLIM 전략 | `@strategy-architect` |
| 외부 API 계약 | `@data-contract-analyst` |
| DB/JPA 설계 | `@persistence-designer` |

---

## 주요 파일 경로

### ETL (Python)
- `etl/kr_adapter/investor_flow_loader.py` — KIS 기관/외인 수급 (hot)
- `etl/kr_adapter/dart_loader.py` — DART 재무제표 (hot)
- `etl/kr_adapter/run_backfill_10yr.py` — 10년 백필 (hot)
- `etl/config/kis.yaml` — KIS API 설정

### Backend (Spring Boot)
- `backend/src/main/java/.../scoring/` — CAN SLIM 스코어링 엔진
- `backend/src/main/java/.../repository/` — JPA/JDBC 레포지터리
- `db/schema.sql` — DB 스키마

### Frontend (React)
- `frontend/src/views/ScreenerView.tsx` — 스크리너 UI (mockData 사용 중)
- `frontend/src/` — Vite + TypeScript

---

## DB 스키마 요약
```
price_metrics          (~2558 종목, 10년 일별 가격)
rs_percentile          (~2513 종목, 상대강도 백분위)
financial_metrics_normalized  (~285 종목, DART 재무 정규화)
canslim_scores         (~2558 종목, CAN SLIM 종합 점수)
```

## 알려진 데이터 현황
- 최고 점수: 미래에셋생명(085620) C=95.8, I=100
- C 점수 null: 상위 30위 중 21개 (DART 커버리지 부족)
- A 점수 null: 상위 30위 중 27개 (DART 커버리지 부족)
