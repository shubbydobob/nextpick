"""
KOSPI/KOSDAQ 지수 → market_state 시딩 (오닐 방식)

오닐 Market Direction 판정:
  1. Distribution Day: 지수 -0.2% 이상 하락 + 거래량 전일 대비 증가
     - 25거래일 롤링 카운트
     - 33거래일 경과 시 자동 소멸
  2. Follow-through Day: 조정 후 랠리 4일차+ 에서 지수 +1.5% 이상 + 거래량 증가
  3. Market Phase:
     - CONFIRMED_UPTREND  : follow-through 확인, distribution < 4
     - UPTREND_PRESSURE   : distribution 4~5 또는 지수 50MA 하회 시작
     - CORRECTION         : distribution 6+ 또는 지수 50MA 확실히 이탈

M 점수 (0~100):
  CONFIRMED_UPTREND  → 70~100 (distribution 0=100, 1=90, 2=85, 3=75)
  UPTREND_PRESSURE   → 35~60  (distribution 4=55, 5=40)
  CORRECTION         → 0~30   (distribution 6+=10, 추가 조건 반영)

지수 프록시:
  KOSPI  → 069500 (KODEX 200)
  KOSDAQ → 229200 (KODEX 코스닥150)
"""
import logging
import os
from datetime import date, datetime

os.environ.setdefault("PYTHONUTF8", "1")

import time
import pandas as pd
from pykrx import stock
from sqlalchemy import text
from ..shared.db_writer import get_session

logger = logging.getLogger(__name__)

_PROXY_TICKER = {
    "KOSPI":  "069500",
    "KOSDAQ": "229200",
}

_START_DATE = "20210101"

# ── 오닐 상수 ──────────────────────────────────────────────
_DIST_DROP_THRESHOLD = -0.2    # Distribution day: -0.2% 이상 하락
_DIST_WINDOW = 25              # 25거래일 롤링 카운트
_DIST_EXPIRY = 33              # 33거래일 후 자동 소멸
_FTD_MIN_RALLY_DAY = 4         # Follow-through: 랠리 4일차+
_FTD_MIN_GAIN = 1.5            # Follow-through: +1.5% 이상
_DIST_PRESSURE = 4             # 4개 이상 → pressure
_DIST_CORRECTION = 6           # 6개 이상 → correction


def _fetch_index_ohlcv(proxy_ticker: str, start: str, end: str,
                       delay_sec: float = 0.5) -> pd.DataFrame:
    """ETF 프록시 OHLCV (종가 + 거래량) 수집."""
    start_year = int(start[:4])
    end_year   = int(end[:4])
    frames = []

    for year in range(start_year, end_year + 1):
        y_start = f"{year}0101"
        y_end   = f"{year}1231" if year < end_year else end
        try:
            df = stock.get_market_ohlcv_by_date(y_start, y_end, proxy_ticker)
            if df is not None and not df.empty:
                frames.append(df)
        except Exception as e:
            logger.warning("프록시 %s %d년 조회 실패: %s", proxy_ticker, year, e)
        time.sleep(delay_sec)

    if not frames:
        return pd.DataFrame()

    combined = pd.concat(frames)
    combined.index = pd.to_datetime(combined.index)
    combined = combined[~combined.index.duplicated(keep="last")]
    combined = combined.sort_index()

    # 종가·거래량 컬럼 매핑
    close_col = next(
        (c for c in combined.columns if "종가" in str(c) or str(c).lower() == "close"),
        combined.columns[-1]
    )
    vol_col = next(
        (c for c in combined.columns if "거래량" in str(c) or str(c).lower() == "volume"),
        combined.columns[4] if len(combined.columns) > 4 else combined.columns[-1]
    )
    result = combined[[close_col, vol_col]].copy()
    result.columns = ["close", "volume"]
    return result


def _compute_oneil_signals(df: pd.DataFrame) -> pd.DataFrame:
    """
    오닐 방식 시그널 계산:
    - distribution_day: 당일이 distribution day인지
    - dist_count_25d: 최근 25거래일 distribution day 수
    - rally_day_count: 최근 저점 이후 연속 상승일 수
    - follow_through: 당일이 follow-through day인지
    - phase: CONFIRMED_UPTREND / UPTREND_PRESSURE / CORRECTION
    - m_score: 0~100
    """
    df = df.copy()

    # 일간 수익률
    df["pct_change"] = df["close"].pct_change() * 100
    df["vol_prev"] = df["volume"].shift(1)

    # Distribution Day 판정: 하락 >= 0.2% AND 거래량 > 전일
    df["is_dist_day"] = (
        (df["pct_change"] <= _DIST_DROP_THRESHOLD) &
        (df["volume"] > df["vol_prev"])
    ).fillna(False)

    # 25거래일 롤링 distribution count
    df["dist_count_25d"] = df["is_dist_day"].rolling(_DIST_WINDOW, min_periods=1).sum().astype(int)

    # 이동평균
    df["ma50"] = df["close"].rolling(50, min_periods=1).mean()
    df["ma200_raw"] = df["close"].rolling(200, min_periods=200).mean()
    # min_periods=200 미만은 NaN → 50일선으로 대체 (초기 기간)
    df["ma200"] = df["ma200_raw"].fillna(df["ma50"])

    # Rally day count: 저점 이후 연속 상승일
    rally_days = []
    count = 0
    for i in range(len(df)):
        if df["pct_change"].iloc[i] is not None and df["pct_change"].iloc[i] > 0:
            count += 1
        else:
            count = 0
        rally_days.append(count)
    df["rally_day_count"] = rally_days

    # Follow-through Day: 랠리 4일차+ AND +1.5% 이상 AND 거래량 증가
    df["is_ftd"] = (
        (df["rally_day_count"] >= _FTD_MIN_RALLY_DAY) &
        (df["pct_change"] >= _FTD_MIN_GAIN) &
        (df["volume"] > df["vol_prev"])
    ).fillna(False)

    # Phase 판정 (상태 기계)
    phases = []
    m_scores = []
    current_phase = "CORRECTION"
    ftd_confirmed = False

    for i in range(len(df)):
        close = df["close"].iloc[i]
        ma50 = df["ma50"].iloc[i]
        ma200 = df["ma200"].iloc[i]
        dist = df["dist_count_25d"].iloc[i]
        is_ftd = df["is_ftd"].iloc[i]

        above_ma50 = close > ma50 if not pd.isna(ma50) else True
        above_ma200 = close > ma200 if not pd.isna(ma200) else True

        # Follow-through 감지 → uptrend 전환
        if is_ftd and current_phase == "CORRECTION":
            current_phase = "CONFIRMED_UPTREND"
            ftd_confirmed = True

        # Phase 전환 로직
        if current_phase == "CONFIRMED_UPTREND":
            if dist >= _DIST_CORRECTION or (not above_ma50 and not above_ma200):
                current_phase = "CORRECTION"
                ftd_confirmed = False
            elif dist >= _DIST_PRESSURE or not above_ma50:
                current_phase = "UPTREND_PRESSURE"

        elif current_phase == "UPTREND_PRESSURE":
            if dist >= _DIST_CORRECTION or (not above_ma50 and not above_ma200):
                current_phase = "CORRECTION"
                ftd_confirmed = False
            elif dist < _DIST_PRESSURE and above_ma50:
                current_phase = "CONFIRMED_UPTREND"

        elif current_phase == "CORRECTION":
            if is_ftd:
                current_phase = "CONFIRMED_UPTREND"
                ftd_confirmed = True

        phases.append(current_phase)

        # M 점수 계산
        m = _compute_m_score(current_phase, dist, above_ma50, above_ma200)
        m_scores.append(m)

    df["phase"] = phases
    df["m_score"] = m_scores

    # trend direction
    df["trend"] = df.apply(
        lambda r: "UP" if (not pd.isna(r["ma50"]) and not pd.isna(r["ma200"]) and r["ma50"] > r["ma200"] * 1.002)
        else ("DOWN" if (not pd.isna(r["ma50"]) and not pd.isna(r["ma200"]) and r["ma50"] < r["ma200"] * 0.998)
              else "SIDEWAYS"),
        axis=1)

    return df


def _compute_m_score(phase: str, dist_count: int,
                     above_ma50: bool, above_ma200: bool) -> float:
    """오닐 기반 M 점수 (0~100)."""
    if phase == "CONFIRMED_UPTREND":
        # 기본 80, distribution 0개=100, 1개=90, 2개=85, 3개=75
        base = {0: 100, 1: 90, 2: 85, 3: 75}.get(dist_count, 70)
        # MA200 위면 보너스
        if above_ma200:
            base = min(100, base + 5)
        return float(base)

    elif phase == "UPTREND_PRESSURE":
        # 기본 50, distribution에 따라 조정
        base = {4: 55, 5: 40}.get(dist_count, 35)
        if above_ma50:
            base += 5
        if above_ma200:
            base += 5
        return float(min(65, base))

    else:  # CORRECTION
        base = 15
        if above_ma200:
            base += 10
        if above_ma50:
            base += 5
        # distribution 많을수록 감산
        penalty = max(0, (dist_count - 5) * 3)
        return float(max(0, base - penalty))


def _upsert_states(market: str, df: pd.DataFrame) -> int:
    """market_state 배치 upsert."""
    sql = text("""
        INSERT INTO market_state (
            market, state_date, index_close, index_close_adj,
            ma_50d, ma_200d,
            distribution_day_count, distribution_day_today, rally_day_count,
            trend_direction, market_phase, prev_phase, notes
        ) VALUES (
            :market, :state_date, :close, :close,
            :ma50, :ma200,
            :dist_count, :dist_today, :rally_count,
            :trend, :phase, :prev_phase, :notes
        )
        ON CONFLICT (market, state_date) DO UPDATE SET
            index_close             = EXCLUDED.index_close,
            index_close_adj         = EXCLUDED.index_close_adj,
            ma_50d                  = EXCLUDED.ma_50d,
            ma_200d                 = EXCLUDED.ma_200d,
            distribution_day_count  = EXCLUDED.distribution_day_count,
            distribution_day_today  = EXCLUDED.distribution_day_today,
            rally_day_count         = EXCLUDED.rally_day_count,
            trend_direction         = EXCLUDED.trend_direction,
            market_phase            = EXCLUDED.market_phase,
            prev_phase              = EXCLUDED.prev_phase,
            notes                   = EXCLUDED.notes
    """)

    count = 0
    with get_session() as session:
        prev_phase = None
        for idx_date, row in df.iterrows():
            if pd.isna(row["close"]):
                continue
            state_date = idx_date.date() if hasattr(idx_date, "date") else idx_date
            phase = row["phase"]
            notes = f"M={row['m_score']:.0f}"
            if row.get("is_dist_day", False):
                notes += " [DIST]"
            if row.get("is_ftd", False):
                notes += " [FTD]"

            session.execute(sql, {
                "market":      market,
                "state_date":  state_date,
                "close":       float(row["close"]),
                "ma50":        None if pd.isna(row["ma50"]) else float(row["ma50"]),
                "ma200":       None if pd.isna(row.get("ma200_raw", row["ma200"])) else float(row.get("ma200_raw", row["ma200"])),
                "dist_count":  int(row["dist_count_25d"]),
                "dist_today":  bool(row["is_dist_day"]),
                "rally_count": int(row["rally_day_count"]),
                "trend":       row["trend"],
                "phase":       phase,
                "prev_phase":  prev_phase,
                "notes":       notes,
            })
            prev_phase = phase
            count += 1
    return count


def seed(market: str = "KOSPI", start_date: str = _START_DATE,
         end_date: str = None) -> None:
    """지정 시장 market_state 시딩."""
    if end_date is None:
        end_date = datetime.today().strftime("%Y%m%d")

    proxy = _PROXY_TICKER.get(market)
    if not proxy:
        raise ValueError(f"지원하지 않는 시장: {market}. 지원: {list(_PROXY_TICKER)}")

    logger.info("[%s] 프록시(%s) 데이터 로드 (%s ~ %s)...", market, proxy, start_date, end_date)
    df = _fetch_index_ohlcv(proxy, start_date, end_date)
    if df.empty:
        logger.warning("[%s] 지수 데이터 없음", market)
        return

    logger.info("[%s] 오닐 시그널 계산 중...", market)
    df = _compute_oneil_signals(df)

    # 2022-01-01 이후만 적재 (이전은 MA200 워밍업용)
    df = df[df.index >= "2022-01-01"]

    count = _upsert_states(market, df)
    logger.info("[%s] market_state 적재 완료: %d건", market, count)


def seed_all() -> None:
    """KOSPI + KOSDAQ 모두 시딩."""
    for market in _PROXY_TICKER:
        seed(market)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    seed_all()
