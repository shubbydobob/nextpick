-- V16: 거래대금·시총 정렬 및 상한가 조회 속도 개선용 인덱스
-- price_daily는 파티션 테이블 → 부모에 인덱스 생성 시 전 파티션에 자동 전파 (PG11+)

-- 특정 거래일 기준 거래대금 상위 N / 등락 조건 조회 가속
CREATE INDEX IF NOT EXISTS idx_price_daily_date_turnover
    ON price_daily (trade_date, turnover DESC);

-- 특정 거래일 기준 시가총액 상위 N 조회 가속 (derived_metrics.market_cap_tril)
CREATE INDEX IF NOT EXISTS idx_derived_metrics_date_cap
    ON derived_metrics (as_of_date DESC, market_cap_tril DESC);
