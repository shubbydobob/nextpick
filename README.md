# NEXTPICK 스코어링 엔진

한국 주식시장 CAN SLIM 방법론 기반 자동 스코어링 · 스크리너 서비스.

- **운영**: [k-stock-score.vercel.app](https://k-stock-score.vercel.app)
- **파이프라인**: ETL(Python) → PostgreSQL → Scoring Engine(Spring Boot) → Screener UI(React)

---

## 아키텍처

```
etl/ (Python)          KIS Open API로 가격·수급·재무·종목상태 수집 (DART 미사용)
   │                   매일 EOD 배치 → PostgreSQL 적재
   ▼
PostgreSQL             price_daily / financials / derived_metrics /
   │                   nextpick_scores / security_status_daily 등
   ▼
backend/ (Spring Boot) CAN SLIM 채점 엔진 + 스크리너/랭킹 REST API + KIS 실시간 시세 오버레이
   │
   ▼
frontend/ (React+Vite) 대시보드 · 스코어 랭킹 · 스크리너 · 종목상세 (Vercel 자동배포)
```

### 데이터 갱신 정책 — 실시간 vs 배치 (중요)

화면에는 **두 종류의 데이터가 섞여** 있습니다.

| 구분 | 항목 | 갱신 |
|------|------|------|
| **배치 (하루 1회 EOD)** | CAN SLIM 종합점수 + C/A/N/S/L/I 팩터, 재무·RS·수급·신고가 파생, **종목 특이사항 뱃지** | 20:05 KST 크론 |
| **실시간 (KIS 15초)** | 현재가 · 등락률 · 거래량 · 거래대금 | 장중 오버레이 |

CAN SLIM은 장기 펀더멘털·추세 방법론이라 점수가 초/분 단위로 바뀌지 않는 게 정상입니다. 등락률 등 시세성 필드만 장중 실시간으로 덮어씁니다.

---

## 종목 특이사항 뱃지 (security_status_daily)

거래정지 · 관리 · 투자주의/경고/위험(시장경보) · 단기과열 · 정리매매 등은 **지정→해제가 있는 기간성 상태**입니다. 매일 EOD에 그날의 현재 상태를 **스냅샷**으로 적재하여, 해제된 종목은 다음날 스냅샷에서 자연히 빠지도록 관리합니다.

- **수집**: `etl/kr_adapter/kis_status_loader.py` — KIS 주식현재가시세(FHKST01010100)의 `iscd_stat_cls_code` / `mrkt_warn_cls_code` / `short_over_yn` / `sltr_yn` 코드에서 도출.
- **저장**: `security_status_daily(security_id, status_date, statuses TEXT[])` — 특이사항이 있는 종목만 적재.
- **표시**: 스크리너/랭킹 응답의 `statuses[]` → 프론트 `StatusBadges` 컴포넌트. 장중에는 KIS 실시간 상태를, 장외/주말에는 배치 스냅샷을 사용.

```
표시 우선순위: 실시간(장중 오버레이) → 없으면 EOD 배치 스냅샷
```

매핑(백엔드 `RealtimePriceController.deriveStatuses`와 ETL 로더가 동일):

| 코드 | 뱃지 |
|------|------|
| iscd_stat 58 | 거래정지 |
| sltr_yn Y | 정리매매 |
| iscd_stat 51 | 관리 |
| mrkt_warn 03 / iscd_stat 52 | 위험 |
| mrkt_warn 02 / iscd_stat 53 | 경고 |
| mrkt_warn 01 / iscd_stat 54 | 주의 |
| short_over Y / iscd_stat 59 | 과열 |

---

## 배치 스케줄 (EC2 crontab, KST)

```
5 20 * * 1-5   run_daily   # 평일 20:05 — 시간외 단일가 20:00 마감 후 확정 종가·상태로 채점
```

`run_daily` 파이프라인: 종목목록(월) → 가격 → KIS 수급 → KIS 재무 → 정규화 → 파생 → market_state → **KIS 종목상태(뱃지)** → 채점 트리거 → SNS.

> 과거 16:10 크론은 시간외 반영 전이라 시간외 급등락이 종가에 안 잡혔습니다. 20:05로 이동해 시간외까지 반영된 확정 데이터로 채점합니다. **DART는 사용하지 않으며 관련 스케줄(오펀 watcher)도 제거**했습니다.

### 운영 워크플로우 (GitHub Actions, workflow_dispatch)

| 워크플로우 | 용도 |
|-----------|------|
| `deploy.yml` | master의 `backend/**` 변경 시 EC2 자동 배포 (git pull + docker compose, Flyway 마이그레이션 자동) |
| `update-cron.yml` | 운영 crontab을 20:05로 갱신 + 지정현황(뱃지) 즉시 시드 |
| `rescore.yml` | 정규화+파생+채점만 재실행 |
| `recover.yml` | 가격→수급→정규화→파생→채점 지정일 복구 |
| `backfill.yml` | 10년 백필 (`--rebuild` opt-in) |
| `db-status.yml` | 운영 DB 상태 읽기 진단 |

---

## 최근 개선 (2026-07 세션)

- **모바일 스코어 랭킹 간격 개선** — 고정 7열 그리드가 좁은 화면에서 넘쳐 점수·종목명이 겹치던 것을 flex 카드형 반응형 레이아웃으로 교체(`RankingView`).
- **종목 특이사항 뱃지 상시화** — KIS 실시간 상태를 EOD 배치(`security_status_daily`)로도 적재해 장외/주말에도 거래정지·관리·경보·과열 뱃지가 유지되도록.
- **뒤로가기 앱 이탈 방지** — 탭/종목상세가 `/` 단일 라우트 state로만 전환돼 뒤로가기 시 앱을 벗어나던 문제를, `history.pushState`/`popstate` 동기화로 앱 내 이전 화면 복원.
- **상한가 섹션 stale 배치값 오노출 수정** — 어제 상한가가 오늘도 노출되던 것을, 실시간 조회 대상에 상한가 후보 우선 포함 + 실시간 미조회 종목 배제로 해결.
- **배치 20:05 이동** — 시간외(20:00) 마감 반영. **DART 스케줄 제거.**

---

## 빠른 명령어

### ETL (로컬)
```bash
PYTHONUTF8=1 python -m etl.kr_adapter.run_daily            # 전체 일별 파이프라인
PYTHONUTF8=1 python -m etl.kr_adapter.kis_status_loader    # 종목 특이사항(뱃지)만
```

### Backend
```bash
cd backend && DB_PASSWORD=1234 ./gradlew bootRun
curl -s -X POST http://localhost:8080/api/admin/scoring/run   # 채점 트리거
```

### Frontend
```bash
cd frontend && npm run dev      # 개발
cd frontend && npm run build    # 프로덕션 빌드
```

### DB 확인
```bash
psql -U nextpick_user -d nextpick -c "SELECT status_date, count(*) FROM security_status_daily GROUP BY status_date ORDER BY status_date DESC LIMIT 3;"
```

---

## 주요 디렉토리

```
etl/kr_adapter/     KIS 로더 (price/investor_flow/kis_financial/kis_status), run_daily
etl/shared/         db_writer, ingestion_meta (공용 upsert·실행추적)
backend/src/.../api/          ScreenerController, RealtimePriceController
backend/src/.../resources/db/migration/   Flyway (V1~V18)
frontend/src/pages/           DashboardView, RankingView, ScreenerPage, StockDetailPage
frontend/src/components/      StatusBadges 등
```
