-- KIS inquire-price 밸류에이션 스냅샷(EOD) — 장외/주말에도 PER·PBR·EPS·BPS 실측 표시.
-- 장중엔 RealtimePriceController가 실시간으로 덮고, 장외엔 이 배치값을 폴백으로 사용.
-- kis_valuation_loader(run_daily 7d)가 as_of_date=당일 행에 UPDATE로 적재.
ALTER TABLE derived_metrics
    ADD COLUMN IF NOT EXISTS per NUMERIC(12,4),   -- 주가수익비율
    ADD COLUMN IF NOT EXISTS pbr NUMERIC(12,4),   -- 주가순자산비율
    ADD COLUMN IF NOT EXISTS eps NUMERIC(16,4),   -- 주당순이익(원)
    ADD COLUMN IF NOT EXISTS bps NUMERIC(16,4);   -- 주당순자산(원)
