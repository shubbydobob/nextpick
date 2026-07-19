"""
US 기관 스폰서십 로더 (13F, yfinance 집계) — CAN SLIM I 팩터의 US 소스.

배경:
  US엔 한국식 일별 외인/기관 순매수 공시가 없다. 오닐 원전 CAN SLIM의 I는
  '기관 스폰서십의 존재 + 분기별 증가'이며, 그 실측 소스가 곧 SEC 13F(분기 공시).
  yfinance가 13F를 집계해 제공한다:
    - major_holders.institutionsPercentHeld  : 기관 보유비중 (0~1)
    - major_holders.institutionsCount        : 보고 기관 수
    - institutional_holders.pctChange        : 상위 보유기관별 QoQ 지분 증감
  → inst_pct_held / inst_holders_count / inst_accum_breadth(증가수-감소수)로 적재.

채점(백엔드 IScorer US 분기):
  ownershipScore = clamp((pct-0.5)*40, ±20),  breadthScore = clamp(breadth/10*15, ±15)
  I = clamp(50 + ownershipScore + breadthScore, 0, 100)

적재 대상: derived_metrics (as_of_date = 최신 US 거래일, 채점일과 정렬).
빈도: 13F는 분기 공시라 월 1회(또는 종목 갱신 주기)면 충분. us_run_daily 종목 갱신 단계에 편입.

실행:
  python -m etl.us_adapter.us_institutional_loader             # 전량
  python -m etl.us_adapter.us_institutional_loader --limit 5   # 디버그

함정:
  - yfinance 종목당 네트워크 왕복 2회(major_holders + institutional_holders) → 518종목 수 분.
    종목별 try/except 비치명적. Yahoo 레이트리밋 방지 슬립.
  - 신규 진입 기관은 pctChange가 큰 양수(+1.0=신규/2배)로 표기 → 증가로 카운트(순매집 신호로 타당).
  - 데이터 없는 종목(소형·신규 상장)은 스킵 → I=null(채점기가 분모 제외).
"""
import os
import time
import logging
from datetime import date

os.environ.setdefault("PYTHONUTF8", "1")

from ..shared.db_writer import get_all_active_security_ids, upsert_us_institutional, get_session

logger = logging.getLogger(__name__)


def _latest_us_trade_date(fallback: date) -> date:
    """price_daily의 최신 US 거래일(채점 as_of와 정렬)."""
    from sqlalchemy import text
    try:
        with get_session() as sess:
            row = sess.execute(text("""
                SELECT MAX(p.trade_date)
                FROM price_daily p JOIN instruments i ON i.id = p.security_id
                WHERE i.market = 'US'
            """)).fetchone()
        return row[0] if row and row[0] else fallback
    except Exception:
        return fallback


def _fetch_one(ticker: str) -> dict | None:
    """yfinance로 단일 종목 13F 집계 조회. 실패/데이터없음 → None."""
    import yfinance as yf
    import math
    try:
        t = yf.Ticker(ticker)
        mh = t.major_holders
    except Exception as e:
        logger.warning("major_holders 실패 %s: %s", ticker, e)
        return None

    pct_held = count = None
    # major_holders는 DataFrame(index=Breakdown, col=Value) 형태.
    try:
        if mh is not None and "Value" in getattr(mh, "columns", []):
            d = mh["Value"].to_dict()
            pct_held = d.get("institutionsPercentHeld")
            count = d.get("institutionsCount")
    except Exception:
        pass

    if pct_held is None:
        return None  # 기관 보유비중 없으면 채점 불가 종목

    # 상위 보유기관 증감 breadth (증가수 - 감소수)
    breadth = None
    try:
        ih = t.institutional_holders
        if ih is not None and "pctChange" in getattr(ih, "columns", []):
            inc = dec = 0
            for v in ih["pctChange"].tolist():
                if v is None or (isinstance(v, float) and math.isnan(v)):
                    continue
                if v > 0:
                    inc += 1
                elif v < 0:
                    dec += 1
            breadth = inc - dec
    except Exception as e:
        logger.debug("institutional_holders 실패 %s: %s", ticker, e)

    return {
        "inst_pct_held": round(float(pct_held), 4),
        "inst_holders_count": int(count) if count else None,
        "inst_accum_breadth": int(breadth) if breadth is not None else None,
    }


def load(as_of: date | None = None, limit: int | None = None, sleep: float = 0.2) -> int:
    """US 활성 종목의 13F 기관 지표를 yfinance로 적재."""
    as_of = as_of or _latest_us_trade_date(date.today())
    universe = get_all_active_security_ids("US")
    if limit:
        universe = universe[:limit]
    if not universe:
        logger.warning("US 활성 종목 없음 — 종목 로더 선행 필요")
        return 0

    logger.info("US 기관(13F) 적재 시작: %d 종목 (as_of=%s)", len(universe), as_of)
    rows: list[dict] = []
    ok = 0
    for i, (sid, ticker) in enumerate(universe, 1):
        data = _fetch_one(ticker)
        if data:
            ok += 1
            rows.append({"security_id": sid, "as_of_date": as_of, **data})
        if i % 50 == 0:
            logger.info("  진행 %d/%d (기관데이터 %d)", i, len(universe), ok)
        if sleep:
            time.sleep(sleep)

    written = upsert_us_institutional(rows)
    logger.info("US 기관(13F) 적재 완료: %d행 (기관데이터 있는 종목 %d/%d)",
                written, ok, len(universe))
    return written


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="상위 N 종목만(디버그)")
    parser.add_argument("--sleep", type=float, default=0.2, help="종목간 슬립(초)")
    args = parser.parse_args()
    load(limit=args.limit, sleep=args.sleep)
