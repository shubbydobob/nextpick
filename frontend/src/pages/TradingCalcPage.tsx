import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { searchStocks, fetchRealtimePrice } from '../api/client'
import type { ScreenerItem } from '../types'

interface BuyRow {
  price: string
  qty: string
}

function numOrNull(s: string): number | null {
  const v = parseFloat(s.replace(/,/g, ''))
  return isNaN(v) || v <= 0 ? null : v
}

export default function TradingCalcPage() {
  const navigate = useNavigate()

  // ── 자동완성 ────────────────────────────────────────────────
  const [query, setQuery] = useState('')
  const [suggestions, setSuggestions] = useState<ScreenerItem[]>([])
  const [selectedStock, setSelectedStock] = useState<ScreenerItem | null>(null)
  const [showDrop, setShowDrop] = useState(false)
  const [loadingPrice, setLoadingPrice] = useState(false)
  const [currentPrice, setCurrentPrice] = useState('')
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const wrapRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const onClickOutside = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node))
        setShowDrop(false)
    }
    document.addEventListener('mousedown', onClickOutside)
    return () => document.removeEventListener('mousedown', onClickOutside)
  }, [])

  useEffect(() => () => { if (debounceRef.current) clearTimeout(debounceRef.current) }, [])

  const handleQueryChange = useCallback((val: string) => {
    setQuery(val)
    setSelectedStock(null)
    if (debounceRef.current) clearTimeout(debounceRef.current)
    if (!val.trim()) { setSuggestions([]); setShowDrop(false); return }
    debounceRef.current = setTimeout(async () => {
      const results = await searchStocks(val)
      setSuggestions(results)
      setShowDrop(results.length > 0)
    }, 250)
  }, [])

  const handleSelect = useCallback(async (item: ScreenerItem) => {
    setSelectedStock(item)
    setQuery(`${item.name} (${item.ticker})`)
    setShowDrop(false)
    setSuggestions([])
    // KIS 실시간 현재가 조회
    setLoadingPrice(true)
    try {
      const rt = await fetchRealtimePrice(item.ticker)
      if (rt && rt.price > 0)
        setCurrentPrice(String(rt.price))
      else if (item.closePrice != null)
        setCurrentPrice(String(item.closePrice)) // 장 마감 후 폴백
    } finally {
      setLoadingPrice(false)
    }
  }, [])

  const [rows, setRows] = useState<BuyRow[]>([
    { price: '', qty: '' },
    { price: '', qty: '' },
    { price: '', qty: '' },
  ])
  // 물타기 섹션
  const [addPrice, setAddPrice] = useState('')
  const [addQty, setAddQty] = useState('')

  const updateRow = (i: number, field: keyof BuyRow, val: string) => {
    setRows(prev => prev.map((r, idx) => idx === i ? { ...r, [field]: val } : r))
  }

  // ── 계산 ─────────────────────────────────────────────────────
  const buyData = rows
    .map(r => ({ p: numOrNull(r.price), q: numOrNull(r.qty) }))
    .filter(r => r.p !== null && r.q !== null) as { p: number; q: number }[]

  const totalQty = buyData.reduce((s, r) => s + r.q, 0)
  const totalAmt = buyData.reduce((s, r) => s + r.p * r.q, 0)
  const avgPrice = totalQty > 0 ? totalAmt / totalQty : null

  const stopLoss    = avgPrice != null ? avgPrice * 0.92 : null
  const target1     = avgPrice != null ? avgPrice * 1.20 : null
  const target2     = avgPrice != null ? avgPrice * 1.25 : null

  const cp = numOrNull(currentPrice)
  const currentPnl = avgPrice != null && cp != null
    ? ((cp - avgPrice) / avgPrice) * 100
    : null

  // 물타기
  const addP = numOrNull(addPrice)
  const addQ = numOrNull(addQty)
  const avgAfterAdd = (avgPrice != null && addP != null && addQ != null && (totalQty + addQ) > 0)
    ? (totalAmt + addP * addQ) / (totalQty + addQ)
    : null

  const fmt = (v: number) => v.toLocaleString('ko-KR', { maximumFractionDigits: 0 })
  const fmtM = (v: number) => {
    const b = v / 1e8
    if (b >= 10000) return (b / 10000).toFixed(2) + '조'
    if (b >= 1000) return (b / 1000).toFixed(1) + '천억'
    if (b >= 100) return b.toFixed(1) + '억'
    return b.toFixed(2) + '억'
  }

  // 손익률 색: 한국식(상승 빨강 / 하락 파랑)
  const pnlColor = currentPnl == null ? undefined
    : currentPnl > 0 ? 'var(--up)' : currentPnl < 0 ? 'var(--down)' : 'var(--text-3)'

  return (
    <div className="calc-page">
      {/* nav */}
      <div className="calc-nav nav-bar">
        <span className="calc-brand" onClick={() => navigate('/')}>
          <span className="calc-brand-dot" />
          NEXT<em>PICK</em>
        </span>
        <nav className="calc-navlinks">
          <button className="calc-navlink" onClick={() => navigate('/')}>스크리너</button>
          <button className="calc-navlink">시장</button>
          <button className="calc-navlink on">포지션 플래너</button>
        </nav>
      </div>

      <div className="calc-body">
        {/* ── 입력 패널 ── */}
        <div className="calc-col">
          {/* 종목 + 현재가 */}
          <div className="calc-card">
            <div className="calc-title">종목 정보</div>
            <div className="calc-grid-2">
              {/* 자동완성 */}
              <div ref={wrapRef} className="calc-ac">
                <span className="calc-label">종목명 / 티커</span>
                <input
                  className="calc-input"
                  placeholder="종목명 또는 티커 검색"
                  value={query}
                  onChange={e => handleQueryChange(e.target.value)}
                  onFocus={() => suggestions.length > 0 && setShowDrop(true)}
                  autoComplete="off"
                />
                {showDrop && (
                  <div className="calc-drop">
                    {suggestions.map(s => (
                      <div key={s.securityId} className="calc-drop-item"
                        onMouseDown={() => handleSelect(s)}>
                        <div>
                          <span className="calc-drop-name">{s.name}</span>
                          <span className="calc-drop-sector">{s.sector ?? ''}</span>
                        </div>
                        <div>
                          <span className="calc-drop-ticker">{s.ticker}</span>
                          {s.closePrice != null && (
                            <div className="calc-drop-price">
                              {s.closePrice.toLocaleString('ko-KR')}원
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
                {selectedStock && (
                  <div className="calc-meta">
                    SCORE {selectedStock.compositeScore.toFixed(1)} · RS {(selectedStock.marketPercentile * 100).toFixed(0)}%
                  </div>
                )}
              </div>

              {/* 현재가 */}
              <div>
                <span className="calc-label">
                  현재가 (원)
                  {loadingPrice && <small> 조회중...</small>}
                </span>
                <input
                  className="calc-input"
                  placeholder="종목 선택 시 자동 입력"
                  value={currentPrice}
                  onChange={e => setCurrentPrice(e.target.value)}
                />
              </div>
            </div>
          </div>

          {/* 매수 행 */}
          <div className="calc-card">
            <div className="calc-title">매수 계획</div>
            <div className="calc-buy-grid calc-buy-head">
              <span className="calc-label" />
              <span className="calc-label">매수가 (원)</span>
              <span className="calc-label">수량 (주)</span>
              <span className="calc-label">소계</span>
            </div>
            {rows.map((r, i) => {
              const p = numOrNull(r.price)
              const q = numOrNull(r.qty)
              const sub = p != null && q != null ? p * q : null
              return (
                <div key={i} className="calc-buy-grid">
                  <span className="calc-stage">
                    {i === 0 ? '1차' : i === 1 ? '2차' : '3차'}
                  </span>
                  <input
                    className="calc-input r"
                    placeholder="0"
                    value={r.price}
                    onChange={e => updateRow(i, 'price', e.target.value)}
                  />
                  <input
                    className="calc-input r"
                    placeholder="0"
                    value={r.qty}
                    onChange={e => updateRow(i, 'qty', e.target.value)}
                  />
                  <span className="calc-sub">{sub != null ? fmtM(sub) : '-'}</span>
                </div>
              )
            })}
          </div>

          {/* 물타기 섹션 */}
          <div className="calc-card">
            <div className="calc-title">물타기 시나리오</div>
            <div className="calc-hint">
              현재 보유 포지션에 추가 매수 시 새 평단가 계산
            </div>
            <div className="calc-grid-2 mb">
              <div>
                <span className="calc-label">추가 매수가 (원)</span>
                <input
                  className="calc-input r"
                  placeholder="0"
                  value={addPrice}
                  onChange={e => setAddPrice(e.target.value)}
                />
              </div>
              <div>
                <span className="calc-label">추가 수량 (주)</span>
                <input
                  className="calc-input r"
                  placeholder="0"
                  value={addQty}
                  onChange={e => setAddQty(e.target.value)}
                />
              </div>
            </div>
            {avgAfterAdd != null && (
              <div className="calc-avg-box">
                <div className="calc-avg-row">
                  <span className="calc-avg-cap">추가 후 평단가</span>
                  <span className="calc-avg-val">{fmt(avgAfterAdd)}원</span>
                </div>
                {addP != null && (
                  <div className="calc-avg-note">
                    기존 평단 {avgPrice != null ? fmt(avgPrice) : '-'}원 →
                    {avgAfterAdd < (avgPrice ?? Infinity) ? ' ▼ 평단 낮아짐' : ' ▲ 평단 높아짐'}
                  </div>
                )}
              </div>
            )}
            {avgAfterAdd == null && avgPrice == null && (
              <div className="calc-empty">위 매수 계획을 먼저 입력하세요</div>
            )}
          </div>
        </div>

        {/* ── 결과 패널 ── */}
        <div className="calc-col res">
          <div className="calc-card">
            <div className="calc-title">포지션 요약</div>

            <ResultRow label="총 매수금액" value={totalAmt > 0 ? fmtM(totalAmt) : '-'} />
            <ResultRow label="총 수량" value={totalQty > 0 ? `${totalQty.toLocaleString()}주` : '-'} />

            <div className="calc-divider" />

            <div className="calc-avg-block">
              <span className="calc-label">평균 매수가</span>
              <div className={`calc-avg-big${avgPrice != null ? '' : ' empty'}`}>
                {avgPrice != null ? fmt(avgPrice) + '원' : '-'}
              </div>
            </div>

            <div className="calc-divider" />

            <div className="calc-targets">
              <PriceTarget label="손절가 (−8%)" value={stopLoss} fmt={fmt} color="var(--down)" />
              <PriceTarget label="1차 익절 (+20%)" value={target1} fmt={fmt} color="var(--up)" />
              <PriceTarget label="2차 익절 (+25%)" value={target2} fmt={fmt} color="var(--up)" />
            </div>

            {currentPnl != null && (
              <>
                <div className="calc-divider" />
                <div>
                  <span className="calc-label">현재 손익률</span>
                  <div className="calc-pnl" style={{ ['--pc' as string]: pnlColor }}>
                    {currentPnl > 0 ? '+' : ''}{currentPnl.toFixed(2)}%
                  </div>
                  {cp != null && avgPrice != null && (
                    <div className="calc-pnl-note">
                      현재가 {fmt(cp)}원 / 평단 {fmt(avgPrice)}원
                    </div>
                  )}
                </div>
              </>
            )}
          </div>

          <div className="calc-card calc-principles">
            <b>성장주 매수 원칙</b>
            <div>• 1차: 계획 물량의 50%</div>
            <div>• 2차: 상승 확인 후 30%</div>
            <div>• 3차: 추세 강화 시 20%</div>
            <div className="gap">• 손절 기준: −8% (원칙 준수)</div>
            <div>• 1차 익절: +20%</div>
          </div>
        </div>
      </div>
    </div>
  )
}

function ResultRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="calc-rrow">
      <span className="calc-rrow-label">{label}</span>
      <span className="calc-rrow-val">{value}</span>
    </div>
  )
}

function PriceTarget({ label, value, fmt, color }: { label: string; value: number | null; fmt: (v: number) => string; color: string }) {
  return (
    <div className="calc-target">
      <span className="calc-target-label">{label}</span>
      <span className="calc-target-val" style={value != null ? { ['--tc' as string]: color } : undefined}>
        {value != null ? fmt(value) + '원' : '-'}
      </span>
    </div>
  )
}
