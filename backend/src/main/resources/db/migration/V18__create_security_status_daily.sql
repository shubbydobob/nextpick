-- ============================================================
-- V18: security_status_daily — 종목 특이사항 일별 스냅샷
-- ============================================================
-- 거래정지 / 관리종목 / 투자주의·경고·위험(시장경보) / 단기과열 / 정리매매 등
-- 종목 상태를 매일 EOD 배치가 KIS 주식현재가시세(FHKST01010100)의 상태 코드에서
-- 도출해 적재한다. 상태는 지정→해제가 있는 '기간성' 이벤트이므로, 매일 그날의
-- 현재 상태를 새 status_date로 덮어쓰는 스냅샷 방식으로 관리한다.
--   · 화면은 최신 status_date의 행만 조인 → 해제된 종목은 다음날 스냅샷에서 자연 제외.
--   · 특이사항이 있는 종목만 적재(정상 종목은 행 없음 = LEFT JOIN null).
-- statuses 예: {거래정지}, {주의,과열}, {관리} 등 (프론트 StatusBadges가 그대로 렌더).
-- ============================================================
CREATE TABLE security_status_daily (
    id           BIGSERIAL   PRIMARY KEY,
    security_id  BIGINT      NOT NULL REFERENCES instruments(id),
    status_date  DATE        NOT NULL,
    statuses     TEXT[]      NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_security_status_daily UNIQUE (security_id, status_date)
);

CREATE INDEX idx_security_status_daily_date     ON security_status_daily (status_date DESC);
CREATE INDEX idx_security_status_daily_sec_date ON security_status_daily (security_id, status_date DESC);
