-- US 기관 스폰서십(13F, 분기) — 오닐 CAN SLIM I 팩터의 US 소스.
-- KR은 일별 외인/기관 순매수(inst_net_buy_10d 등)를 쓰지만 US엔 그 공시가 없어,
-- SEC 13F 파생(yfinance 집계)의 기관 보유비중·기관 수·상위보유기관 증감폭을 별도 컬럼에 적재.
-- us_institutional_loader가 as_of_date(최신 US 거래일) 행에 UPSERT.
-- IScorer는 이 컬럼(inst_pct_held != null)이 있으면 US 13F 분기로 채점, 없으면 KR 일별 분기.
ALTER TABLE derived_metrics
    ADD COLUMN IF NOT EXISTS inst_pct_held      NUMERIC(6,4),   -- 기관 보유비중 0~1 (institutionsPercentHeld)
    ADD COLUMN IF NOT EXISTS inst_holders_count INTEGER,        -- 13F 보고 기관 수 (institutionsCount)
    ADD COLUMN IF NOT EXISTS inst_accum_breadth SMALLINT;       -- 상위보유기관 증가수-감소수 (-N~+N, 분기 순매집 breadth)
