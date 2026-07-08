-- canslim_scores → nextpick_scores 리네이밍 (CAN SLIM 상표 회피).
-- 메타데이터 rename이라 데이터 이동 없음. 기존 마이그레이션(V6/V13/V17 등)은
-- Flyway 이력·체크섬 보존을 위해 수정하지 않는다(과거 파일명에 canslim 잔존은 정상).
-- 인덱스/제약 이름(idx_canslim_scores_*)은 pg 카탈로그 내부 식별자라 그대로 둔다.
ALTER TABLE IF EXISTS canslim_scores RENAME TO nextpick_scores;
