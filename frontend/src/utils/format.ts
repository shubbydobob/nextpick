export function fmtPrice(v: number | null): string {
  return v === null ? '—' : v.toLocaleString('ko-KR', { maximumFractionDigits: 0 })
}

/** 한국 실시간 오버레이 창(평일 08:00~20:00 KST). 이 창에선 배치 시세가 전일 종가 기준이라
 *  실시간이 붙기 전 전일 등락률·상한가·상태뱃지를 노출하지 않도록 게이트에 쓴다. (백엔드 isKrMarketOpen과 동일 창) */
export function isKrMarketHours(): boolean {
  const now = new Date()
  const kst = new Date(now.getTime() + (now.getTimezoneOffset() + 540) * 60000)
  const day = kst.getDay()
  if (day === 0 || day === 6) return false
  const mins = kst.getHours() * 60 + kst.getMinutes()
  return mins >= 480 && mins <= 1200   // 08:00 ~ 20:00
}

export function fmtRate(v: number | null): string {
  return v === null ? '—' : (v > 0 ? '+' : '') + v.toFixed(2) + '%'
}

/** 시가총액: 조 / 천억 / 억 단위 (정수 반올림) */
export function fmtMarketCap(v: number | null): string {
  if (v === null) return '—'
  const b = v / 1e8
  if (b >= 10000) return Math.round(b / 10000) + '조'
  if (b >= 1000) return Math.round(b / 1000) + '천억'
  return Math.round(b) + '억'
}

/** 거래대금 등 금액: 천억 / 억 단위 (정수 반올림) */
export function fmtAmt(v: number | null): string {
  if (v === null) return '—'
  const b = v / 1e8
  if (b >= 1000) return Math.round(b / 1000) + '천억'
  return Math.round(b) + '억'
}

/** 거래량: 천만 / 만 단위 (정수 반올림) */
export function fmtVolume(v: number | null): string {
  if (v === null) return '—'
  if (v >= 1e7) return Math.round(v / 1e7) + '천만'
  if (v >= 1e4) return Math.round(v / 1e4) + '만'
  return v.toLocaleString()
}

/** 재무 금액 → 억 단위 정수 (차트용) */
export function fmtFinAmt(v: number | null): number | null {
  return v === null ? null : Math.round(v / 1e8)
}

/** 거래량: 천만주 / 만주 단위 (상세용, '주' 접미) */
export function fmtVol(v: number | null): string {
  if (v === null) return '—'
  if (v >= 1e7) return Math.round(v / 1e7) + '천만주'
  return Math.round(v / 1e4) + '만주'
}

/** 순매수 금액 → 억 단위 부호 표기 */
export function fmtFlow(v: number | null): string {
  if (v === null) return '—'
  const b = v / 1e8
  return (b > 0 ? '+' : '') + Math.round(b) + '억'
}

/** 52주 고가 대비 등락률 */
export function fmtHigh52pct(close: number | null, high: number | null): string {
  if (!close || !high || high <= 0) return '—'
  const pct = (close - high) / high * 100
  return (pct >= 0 ? '+' : '') + Math.round(pct) + '%'
}
