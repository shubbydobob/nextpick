-- V14: S점수 개선 — 시가총액 희소성 점수용 컬럼 추가
-- float_shares = total_shares 근사값 의존도 제거 → market_cap_tril 기반으로 교체

ALTER TABLE derived_metrics
    ADD COLUMN IF NOT EXISTS market_cap_tril NUMERIC(14,4);

ALTER TABLE market_config
    ADD COLUMN IF NOT EXISTS s_cap_max_tril NUMERIC(8,2) DEFAULT 10.0;

COMMENT ON COLUMN derived_metrics.market_cap_tril IS '시가총액 (조원 단위) = close_adj × total_shares / 1e12';
COMMENT ON COLUMN market_config.s_cap_max_tril     IS 'S점수 시가총액 상한 (조원). 이 이상이면 floatScore=0';
