"""
KIS 종목 특이사항(뱃지) EOD 로더 — 거래정지·관리·시장경보·단기과열·정리매매

데이터 소스: 한국투자증권 KIS Open API
  TR: FHKST01010100 (주식현재가 시세)
  상태 코드:
    iscd_stat_cls_code : 58=거래정지, 51=관리, 52=투자위험, 53=투자경고, 54=투자주의, 59=단기과열
    mrkt_warn_cls_code : 01=투자주의, 02=투자경고, 03=투자위험
    short_over_yn      : Y=단기과열
    sltr_yn            : Y=정리매매

설계:
  · 상태는 지정→해제가 있는 '기간성' 이벤트라 매일 EOD에 그날 현재 상태를 스냅샷으로 적재.
  · 특이사항이 있는 종목만 security_status_daily에 upsert(정상 종목은 행 없음).
  · 해제된 종목은 다음날 스냅샷에 안 담기므로 최신 status_date 조인에서 자연 제외.
  · 백엔드 RealtimePriceController.deriveStatuses 와 동일한 매핑(장중 오버레이와 라벨 일치).

속도: 전종목 종목당 1콜, 0.06s 딜레이 → 약 3~5분 (초당 16건, 한도 20건 여유).
실행: python -m etl.kr_adapter.kis_status_loader [YYYYMMDD]
"""
import os
import logging
import time
from datetime import date, datetime

os.environ.setdefault("PYTHONUTF8", "1")

import requests

from .investor_flow_loader import _get_token, _load_config
from ..shared.db_writer import get_all_active_security_ids, upsert_security_status
from ..shared.ingestion_meta import start_run, finish_run, fail_run

logger = logging.getLogger(__name__)

SOURCE   = "KIS_STATUS_KR"
_BASE_URL = "https://openapi.koreainvestment.com:9443"
_DELAY    = 0.06   # 초당 약 16건 (한도 20건보다 여유)


def _headers(cfg: dict, token: str, tr_id: str) -> dict:
    return {
        "content-type": "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "appkey":        cfg["app_key"],
        "appsecret":     cfg["app_secret"],
        "tr_id":         tr_id,
        "custtype":      "P",
    }


def _derive_statuses(output: dict) -> list[str]:
    """KIS 시세 응답 → 특이사항 라벨 리스트. 심각한 상태 우선, 중복 제거.
    백엔드 RealtimePriceController.deriveStatuses 와 매핑을 일치시킬 것."""
    stat = str(output.get("iscd_stat_cls_code", "")).strip()
    warn = str(output.get("mrkt_warn_cls_code", "")).strip()
    short_over = str(output.get("short_over_yn", "")).strip().upper() == "Y"
    sltr       = str(output.get("sltr_yn", "")).strip().upper() == "Y"

    statuses: list[str] = []

    def add(v: str) -> None:
        if v not in statuses:
            statuses.append(v)

    if stat == "58":
        add("거래정지")
    if sltr:
        add("정리매매")
    if stat == "51":
        add("관리")
    # 시장경고: 종목상태코드(52/53/54)와 시장경고코드(01/02/03) 둘 다 반영, 중복 제거.
    if warn == "03" or stat == "52":
        add("위험")
    if warn == "02" or stat == "53":
        add("경고")
    if warn == "01" or stat == "54":
        add("주의")
    if short_over or stat == "59":
        add("과열")

    return statuses


def _fetch_status(ticker: str, cfg: dict, token: str) -> list[str]:
    """종목 1개의 특이사항 리스트 조회. 실패·정상 종목은 빈 리스트."""
    try:
        r = requests.get(
            f"{_BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-price",
            headers=_headers(cfg, token, "FHKST01010100"),
            params={"fid_cond_mrkt_div_code": "J", "fid_input_iscd": ticker},
            timeout=10,
        )
        time.sleep(_DELAY)
        if r.ok and r.json().get("rt_cd") == "0":
            output = r.json().get("output")
            if output:
                return _derive_statuses(output)
    except Exception as e:
        logger.debug("상태 조회 실패 %s: %s", ticker, e)
    return []


def load(target_date: date = None) -> None:
    """전종목 KIS 상태 조회 → 특이종목만 security_status_daily 스냅샷 적재."""
    if target_date is None:
        target_date = date.today()

    run_id = start_run(SOURCE, target_date, market="KR")
    if run_id is None:
        logger.info("KIS 종목상태 수집 이미 완료(%s) — 스킵", target_date)
        return

    try:
        cfg   = _load_config()
        token = _get_token(cfg)

        securities = (
            get_all_active_security_ids("KOSPI") +
            get_all_active_security_ids("KOSDAQ")
        )
        total = len(securities)
        logger.info("KIS 종목상태 수집 시작: %d 종목", total)

        rows = []
        flagged = failed = 0
        for idx, (security_id, ticker) in enumerate(securities, 1):
            try:
                statuses = _fetch_status(ticker, cfg, token)
            except Exception as e:
                failed += 1
                logger.debug("[%d/%d] %s 상태 실패: %s", idx, total, ticker, e)
                continue
            if statuses:
                rows.append({
                    "security_id": security_id,
                    "status_date": target_date,
                    "statuses":    statuses,
                })
                flagged += 1
            if idx % 200 == 0:
                logger.info("[%d/%d] 특이종목 %d / 실패 %d", idx, total, flagged, failed)

        ins, upd = upsert_security_status(rows)
        finish_run(SOURCE, target_date, rows_inserted=ins, rows_updated=upd)
        logger.info("KIS 종목상태 수집 완료 — 특이종목 %d (신규 %d / 갱신 %d) / 실패 %d",
                    flagged, ins, upd, failed)

    except Exception as e:
        logger.error("KIS 종목상태 수집 실패: %s", e)
        fail_run(SOURCE, target_date, str(e))
        raise


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    if len(__import__("sys").argv) > 1:
        load(datetime.strptime(__import__("sys").argv[1], "%Y%m%d").date())
    else:
        load()
