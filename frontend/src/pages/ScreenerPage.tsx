import React, { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { fetchScreener, fetchSectors } from '../api/client'
import MacroTicker from '../components/MacroTicker'
import type { ScreenerItem } from '../types'

// ── types ──────────────────────────────────────────────────────
type ViewTab = 'overview' | 'technical' | 'flow'
type FlowUnit = '억원' | '백만원'
type SortDir = 'desc' | 'asc'
type SortKey = keyof Pick<ScreenerItem,
  'compositeScore' | 'cScore' | 'aScore' | 'nScore' | 'sScore' | 'lScore' | 'iScore' | 'mScore' |
  'closePrice' | 'changeRate' | 'weekHigh52' | 'turnover' | 'volume' |
  'foreignNetBuy10d' | 'instNetBuy10d' | 'marketPercentile' | 'marketCap'
>

// ── color helpers ──────────────────────────────────────────────
const scoreColor = (v: number | null) => {
  if (v === null) return 'transparent'
  if (v >= 85) return 'rgba(74,222,128,0.18)'
  if (v >= 70) return 'rgba(74,222,128,0.09)'
  if (v >= 55) return 'rgba(250,189,68,0.15)'
  if (v >= 40) return 'rgba(249,115,22,0.18)'
  return 'rgba(248,113,113,0.15)'
}
const scoreText = (v: number | null) => {
  if (v === null) return '#3d4451'
  if (v >= 70) return '#4ade80'
  if (v >= 55) return '#fabd44'
  if (v >= 40) return '#f97316'
  return '#f87171'
}
const compositeGrade = (v: number) => {
  if (v >= 85) return { color: '#4ade80', label: 'A+' }
  if (v >= 75) return { color: '#86efac', label: 'A' }
  if (v >= 65) return { color: '#fabd44', label: 'B+' }
  if (v >= 55) return { color: '#fbbf24', label: 'B' }
  if (v >= 45) return { color: '#f97316', label: 'C' }
  return { color: '#f87171', label: 'D' }
}
const changeColor = (v: number | null) => {
  if (v === null) return '#4b5563'
  if (v > 0) return '#4ade80'
  if (v < 0) return '#f87171'
  return '#6b7280'
}

// ── format helpers ─────────────────────────────────────────────
const fmtPrice = (v: number | null) =>
  v === null ? '-' : v.toLocaleString('ko-KR', { maximumFractionDigits: 0 })
const fmtRate = (v: number | null) =>
  v === null ? '-' : (v > 0 ? '+' : '') + v.toFixed(2) + '%'
const fmtMarketCap = (v: number | null) => {
  if (v === null) return '-'
  const b = v / 1e8
  if (b >= 10000) return (b / 10000).toFixed(1) + '조'
  if (b >= 1000) return (b / 1000).toFixed(1) + '천억'
  return b.toFixed(0) + '억'
}
const fmtTurnover = (v: number | null) => {
  if (v === null) return '-'
  const b = v / 1e8
  if (b >= 1000) return (b / 1000).toFixed(1) + '천억'
  return b.toFixed(0) + '억'
}
const fmtVolume = (v: number | null) => {
  if (v === null) return '-'
  if (v >= 1e7) return (v / 1e7).toFixed(1) + '천만'
  if (v >= 1e4) return (v / 1e4).toFixed(0) + '만'
  return v.toLocaleString()
}
const fmtFlow = (v: number | null, unit: FlowUnit) => {
  if (v === null) return '-'
  if (unit === '억원') return (v > 0 ? '+' : '') + (v / 1e8).toFixed(1)
  return (v > 0 ? '+' : '') + (v / 1e6).toFixed(0)
}
const fmtHigh52pct = (close: number | null, high: number | null) => {
  if (!close || !high || high <= 0) return '-'
  const pct = (close - high) / high * 100
  return (pct >= 0 ? '+' : '') + pct.toFixed(1) + '%'
}

// ── sub-components ─────────────────────────────────────────────
function ScoreCell({ value }: { value: number | null }) {
  return (
    <td style={{
      padding: '0 5px', textAlign: 'center',
      background: scoreColor(value), color: scoreText(value),
      fontWeight: value !== null ? 600 : 400, fontSize: 11,
      borderRight: '1px solid #1c2230',
    }}>
      {value !== null ? value.toFixed(1) : <span style={{ color: '#2d3748' }}>·</span>}
    </td>
  )
}

function SortTh({ label, sortKey: sk, current, dir, onSort, align = 'right', style = {} }: {
  label: string; sortKey?: SortKey; current: SortKey; dir: SortDir
  onSort: (k: SortKey) => void; align?: string; style?: React.CSSProperties
}) {
  const active = sk && current === sk
  return (
    <th
      onClick={sk ? () => onSort(sk) : undefined}
      style={{
        padding: '7px 6px', textAlign: align as any, fontSize: 10, fontWeight: 600,
        color: active ? '#c9d1d9' : '#4b5563', letterSpacing: '0.05em',
        cursor: sk ? 'pointer' : 'default', userSelect: 'none',
        whiteSpace: 'nowrap', borderBottom: '1px solid #21262d',
        background: '#0d1117', ...style,
      }}
    >
      {label}
      {sk && <span style={{ marginLeft: 2, opacity: active ? 1 : 0.3, fontSize: 9 }}>
        {active ? (dir === 'desc' ? '▼' : '▲') : '⇅'}
      </span>}
    </th>
  )
}

// ── main component ─────────────────────────────────────────────
export default function ScreenerPage() {
  const [items, setItems] = useState<ScreenerItem[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [page, setPage] = useState(0)
  const [size, setSize] = useState(30)
  const [flowUnit, setFlowUnit] = useState<FlowUnit>('억원')
  const [hoveredId, setHoveredId] = useState<number | null>(null)
  const [sortKey, setSortKey] = useState<SortKey>('compositeScore')
  const [sortDir, setSortDir] = useState<SortDir>('desc')
  const [sector, setSector] = useState('')
  const [capRange, setCapRange] = useState<'all' | 'large' | 'mid' | 'small'>('all')
  const [sectors, setSectors] = useState<string[]>([])
  const [viewTab, setViewTab] = useState<ViewTab>('overview')
  const [minScore, setMinScore] = useState(0)
  const [watchlist, setWatchlist] = useState<Set<number>>(() => {
    try {
      const raw = localStorage.getItem('canslim_watchlist')
      return raw ? new Set<number>(JSON.parse(raw)) : new Set<number>()
    } catch { return new Set<number>() }
  })
  const [showWatchOnly, setShowWatchOnly] = useState(false)
  const navigate = useNavigate()
  const scrollRef = useRef<HTMLDivElement>(null)
  const mirrorRef = useRef<HTMLDivElement>(null)

  const CAP_PARAMS: Record<string, { minCap?: number; maxCap?: number }> = {
    all:   {},
    large: { minCap: 1_000_000_000_000 },
    mid:   { minCap: 200_000_000_000, maxCap: 1_000_000_000_000 },
    small: { maxCap: 200_000_000_000 },
  }

  useEffect(() => { fetchSectors().then(setSectors) }, [])

  useEffect(() => {
    setLoading(true)
    const { minCap, maxCap } = CAP_PARAMS[capRange]
    fetchScreener('KR', page, size, query.trim(), sector, minCap, maxCap, sortKey, sortDir, minScore)
      .then(d => { setItems(d.items); setTotal(d.total) })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [page, size, query, sector, capRange, sortKey, sortDir, minScore])

  const toggleWatch = (id: number, e: React.MouseEvent) => {
    e.stopPropagation()
    setWatchlist(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      try { localStorage.setItem('canslim_watchlist', JSON.stringify([...next])) } catch {}
      return next
    })
  }

  const handleSort = (key: SortKey) => {
    if (sortKey === key) setSortDir(d => d === 'desc' ? 'asc' : 'desc')
    else { setSortKey(key); setSortDir('desc') }
    setPage(0)
  }
  const handleQuery = (v: string) => { setQuery(v); setPage(0) }
  const handleSize = (v: number) => { setSize(v); setPage(0) }
  const totalPages = Math.ceil(total / size)

  const onTableScroll = () => {
    if (mirrorRef.current && scrollRef.current)
      mirrorRef.current.scrollLeft = scrollRef.current.scrollLeft
  }
  const onMirrorScroll = () => {
    if (scrollRef.current && mirrorRef.current)
      scrollRef.current.scrollLeft = mirrorRef.current.scrollLeft
  }

  // ── styles ──────────────────────────────────────────────────
  const S = {
    filterSelect: {
      background: '#161b22', border: '1px solid #21262d', borderRadius: 4,
      color: '#9ca3af', padding: '4px 8px', fontSize: 11, outline: 'none',
      cursor: 'pointer',
    } as React.CSSProperties,
    filterInput: {
      background: '#161b22', border: '1px solid #21262d', borderRadius: 4,
      color: '#e6edf3', padding: '4px 10px', fontSize: 12, outline: 'none', width: 200,
    } as React.CSSProperties,
    capBtn: (active: boolean) => ({
      padding: '4px 9px', fontSize: 10, fontWeight: 600,
      background: active ? '#1f3a5f' : 'transparent',
      color: active ? '#58a6ff' : '#4b5563',
      border: 'none', cursor: 'pointer',
      borderRight: '1px solid #21262d',
    } as React.CSSProperties),
    tab: (active: boolean) => ({
      padding: '8px 16px', fontSize: 12, fontWeight: active ? 600 : 400,
      color: active ? '#e6edf3' : '#4b5563',
      background: 'none', border: 'none', cursor: 'pointer',
      borderBottom: active ? '2px solid #1f6feb' : '2px solid transparent',
      marginBottom: -1,
    } as React.CSSProperties),
    td: {
      padding: '5px 6px', fontSize: 11, color: '#9ca3af',
      borderBottom: '1px solid #0d1117',
    } as React.CSSProperties,
  }

  const flowColLabel = (label: string) =>
    `${label}(${flowUnit === '억원' ? '억' : '백만'})`

  // ── table header & row per tab ──────────────────────────────
  const renderHead = () => {
    const Th = (props: React.ComponentProps<typeof SortTh>) =>
      <SortTh {...props} current={sortKey} dir={sortDir} onSort={handleSort} />

    if (viewTab === 'overview') return (
      <tr>
        <th style={{ ...S.td, width: 28, textAlign: 'center', color: '#4b5563', fontSize: 10, borderBottom: '1px solid #21262d', background: '#0d1117' }}>★</th>
        <th style={{ ...S.td, width: 36, textAlign: 'center', color: '#4b5563', fontSize: 10, borderBottom: '1px solid #21262d', background: '#0d1117' }}>#</th>
        <Th label="티커" align="center" style={{ width: 72 }} />
        <Th label="종목명" align="left" style={{ width: 140 }} />
        <Th label="섹터" align="left" style={{ width: 80 }} />
        <Th label="SCORE" sortKey="compositeScore" style={{ width: 70 }} />
        <Th label="Δ" style={{ width: 48, textAlign: 'center' as any }} />
        <Th label="C분기" sortKey="cScore" align="center" style={{ width: 52 }} />
        <Th label="A연간" sortKey="aScore" align="center" style={{ width: 52 }} />
        <Th label="N신고가" sortKey="nScore" align="center" style={{ width: 52 }} />
        <Th label="S수급" sortKey="sScore" align="center" style={{ width: 52 }} />
        <Th label="L강도" sortKey="lScore" align="center" style={{ width: 52 }} />
        <Th label="I기관" sortKey="iScore" align="center" style={{ width: 52 }} />
        <Th label="M시장" sortKey="mScore" align="center" style={{ width: 48 }} />
        <Th label="종가" sortKey="closePrice" style={{ width: 78 }} />
        <Th label="등락률" sortKey="changeRate" style={{ width: 64 }} />
        <Th label="시가총액" sortKey="marketCap" style={{ width: 78 }} />
        <Th label="베이스" align="center" style={{ width: 52 }} />
      </tr>
    )

    if (viewTab === 'technical') return (
      <tr>
        <th style={{ ...S.td, width: 36, textAlign: 'center', color: '#4b5563', fontSize: 10, borderBottom: '1px solid #21262d', background: '#0d1117' }}>#</th>
        <Th label="티커" align="center" style={{ width: 72 }} />
        <Th label="종목명" align="left" style={{ width: 160 }} />
        <Th label="종가" sortKey="closePrice" style={{ width: 88 }} />
        <Th label="등락률" sortKey="changeRate" style={{ width: 70 }} />
        <Th label="52주고점비" sortKey="weekHigh52" style={{ width: 80 }} />
        <Th label="거래량" sortKey="volume" style={{ width: 80 }} />
        <Th label="거래대금" sortKey="turnover" style={{ width: 88 }} />
        <Th label="RS%" sortKey="marketPercentile" style={{ width: 60 }} />
        <Th label="시가총액" sortKey="marketCap" style={{ width: 88 }} />
        <Th label="SCORE" sortKey="compositeScore" style={{ width: 68 }} />
      </tr>
    )

    // flow
    return (
      <tr>
        <th style={{ ...S.td, width: 36, textAlign: 'center', color: '#4b5563', fontSize: 10, borderBottom: '1px solid #21262d', background: '#0d1117' }}>#</th>
        <Th label="티커" align="center" style={{ width: 72 }} />
        <Th label="종목명" align="left" style={{ width: 160 }} />
        <Th label={flowColLabel('외국인')} sortKey="foreignNetBuy10d" style={{ width: 96, color: '#22d3ee' }} />
        <Th label={flowColLabel('기관')} sortKey="instNetBuy10d" style={{ width: 88, color: '#a78bfa' }} />
        <Th label="거래대금" sortKey="turnover" style={{ width: 88 }} />
        <Th label="거래량" sortKey="volume" style={{ width: 80 }} />
        <Th label="S수급" sortKey="sScore" align="center" style={{ width: 56 }} />
        <Th label="I기관" sortKey="iScore" align="center" style={{ width: 56 }} />
        <Th label="RS%" sortKey="marketPercentile" style={{ width: 60 }} />
        <Th label="SCORE" sortKey="compositeScore" style={{ width: 68 }} />
      </tr>
    )
  }

  const renderRow = (item: ScreenerItem, idx: number) => {
    const hovered = hoveredId === item.securityId
    const rowBg = hovered ? '#161b22' : idx % 2 === 0 ? '#0b0f17' : '#0d1117'
    const grade = compositeGrade(item.compositeScore)
    const isWatched = watchlist.has(item.securityId)

    const watchBtn = (
      <td style={{ ...S.td, textAlign: 'center', padding: '0 2px' }}
        onClick={e => toggleWatch(item.securityId, e)}>
        <span style={{ fontSize: 13, cursor: 'pointer', color: isWatched ? '#facc15' : '#374151',
          lineHeight: 1, userSelect: 'none' }}>
          {isWatched ? '★' : '☆'}
        </span>
      </td>
    )

    const base = (
      <>
        <td style={{ ...S.td, textAlign: 'center', color: '#374151', fontSize: 10 }}>
          {item.marketRank}
        </td>
        <td style={{ ...S.td, textAlign: 'center', fontWeight: 700, fontFamily: 'monospace',
          fontSize: 12, color: hovered ? '#93c5fd' : '#3b82f6' }}>
          {item.ticker}
          {item.breakoutToday === true && (
            <span style={{ fontSize: 8, background: '#16a34a', color: '#fff', borderRadius: 3, padding: '1px 3px', marginLeft: 3 }}>NEW</span>
          )}
        </td>
        <td style={{ ...S.td, fontSize: 12, color: hovered ? '#e6edf3' : '#d1d5db',
          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 160 }}>
          {item.name}
        </td>
      </>
    )

    const scoreChip = (
      <td style={{ ...S.td, textAlign: 'right', fontWeight: 700, fontSize: 13, color: grade.color }}>
        {item.compositeScore.toFixed(1)}
        <span style={{ fontSize: 9, marginLeft: 3, opacity: 0.7 }}>{grade.label}</span>
      </td>
    )

    const deltaCell = (() => {
      const d = item.scoreDelta
      if (d === null || d === undefined) return (
        <td style={{ ...S.td, textAlign: 'center', color: '#374151' }}>-</td>
      )
      const abs = Math.abs(d)
      const bold = abs >= 2
      const color = d > 0 ? '#4ade80' : d < 0 ? '#f87171' : '#6b7280'
      const text = d > 0 ? `+${d.toFixed(1)}` : d.toFixed(1)
      return (
        <td style={{ ...S.td, textAlign: 'center', color, fontWeight: bold ? 700 : 400, fontSize: 11 }}>
          {text}
        </td>
      )
    })()

    if (viewTab === 'overview') return (
      <>
        {watchBtn}
        {base}
        <td style={{ ...S.td, fontSize: 10, color: '#1d4ed8', opacity: 0.9,
          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {item.sector ?? '·'}
        </td>
        {scoreChip}
        {deltaCell}
        <ScoreCell value={item.cScore} />
        <ScoreCell value={item.aScore} />
        <ScoreCell value={item.nScore} />
        <ScoreCell value={item.sScore} />
        <ScoreCell value={item.lScore} />
        <ScoreCell value={item.iScore} />
        <ScoreCell value={item.mScore} />
        <td style={{ ...S.td, textAlign: 'right', fontFamily: 'monospace', color: '#d1d5db' }}>
          {fmtPrice(item.closePrice)}
        </td>
        <td style={{ ...S.td, textAlign: 'right', fontWeight: 600, color: changeColor(item.changeRate) }}>
          {fmtRate(item.changeRate)}
        </td>
        <td style={{ ...S.td, textAlign: 'right', color: '#6b7280' }}>
          {fmtMarketCap(item.marketCap)}
        </td>
        <td style={{ ...S.td, textAlign: 'center', fontSize: 10, color: '#6b7280' }}>
          {item.baseDays ? `${item.baseDays}일` : '-'}
        </td>
      </>
    )

    if (viewTab === 'technical') {
      const high52pct = fmtHigh52pct(item.closePrice, item.weekHigh52)
      const isNearHigh = item.weekHigh52 !== null && item.closePrice !== null &&
        item.weekHigh52 > 0 && (item.closePrice / item.weekHigh52) >= 0.97
      return (
        <>
          {base}
          <td style={{ ...S.td, textAlign: 'right', fontFamily: 'monospace', color: '#d1d5db', fontSize: 12, fontWeight: 600 }}>
            {fmtPrice(item.closePrice)}
          </td>
          <td style={{ ...S.td, textAlign: 'right', fontWeight: 600, color: changeColor(item.changeRate) }}>
            {fmtRate(item.changeRate)}
          </td>
          <td style={{ ...S.td, textAlign: 'right', color: isNearHigh ? '#4ade80' : '#6b7280' }}>
            {high52pct}
          </td>
          <td style={{ ...S.td, textAlign: 'right' }}>{fmtVolume(item.volume)}</td>
          <td style={{ ...S.td, textAlign: 'right' }}>{fmtTurnover(item.turnover)}</td>
          <td style={{ ...S.td, textAlign: 'right', color: '#9ca3af' }}>
            {(item.marketPercentile * 100).toFixed(0)}
          </td>
          <td style={{ ...S.td, textAlign: 'right', color: '#6b7280' }}>
            {fmtMarketCap(item.marketCap)}
          </td>
          {scoreChip}
        </>
      )
    }

    // flow tab
    return (
      <>
        {base}
        <td style={{ ...S.td, textAlign: 'right', fontWeight: 600,
          color: item.foreignNetBuy10d === null ? '#374151' : item.foreignNetBuy10d > 0 ? '#22d3ee' : '#f87171' }}>
          {fmtFlow(item.foreignNetBuy10d, flowUnit)}
        </td>
        <td style={{ ...S.td, textAlign: 'right', fontWeight: 600,
          color: item.instNetBuy10d === null ? '#374151' : item.instNetBuy10d > 0 ? '#a78bfa' : '#f87171' }}>
          {fmtFlow(item.instNetBuy10d, flowUnit)}
        </td>
        <td style={{ ...S.td, textAlign: 'right' }}>{fmtTurnover(item.turnover)}</td>
        <td style={{ ...S.td, textAlign: 'right' }}>{fmtVolume(item.volume)}</td>
        <ScoreCell value={item.sScore} />
        <ScoreCell value={item.iScore} />
        <td style={{ ...S.td, textAlign: 'right', color: '#9ca3af' }}>
          {(item.marketPercentile * 100).toFixed(0)}
        </td>
        {scoreChip}
      </>
    )
  }

  // ── pagination helpers ──────────────────────────────────────
  const pageNums = (() => {
    const total7 = Math.min(totalPages, 7)
    const start = Math.max(0, Math.min(page - 3, totalPages - total7))
    return Array.from({ length: total7 }, (_, i) => start + i)
  })()

  if (error) return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center',
      height: '100vh', color: '#f87171' }}>{error}</div>
  )

  const displayItems = showWatchOnly ? items.filter(i => watchlist.has(i.securityId)) : items
  const hasActiveFilter = sector !== '' || capRange !== 'all' || query !== '' || minScore > 0 || showWatchOnly
  const activeFilterCount = [sector !== '', capRange !== 'all', query !== '', minScore > 0, showWatchOnly].filter(Boolean).length

  return (
    <div style={{ minHeight: '100vh', background: '#0b0f17', color: '#e6edf3' }}>
      <MacroTicker />

      {/* ══ Section 1: 브랜드 네비게이션 ═══════════════════════ */}
      <div style={{
        background: '#0d1117', borderBottom: '1px solid #21262d',
        padding: '0 20px', display: 'flex', alignItems: 'center',
        justifyContent: 'space-between', height: 40,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
            <span style={{ fontSize: 14, fontWeight: 800, letterSpacing: '-0.5px' }}>
              CAN<span style={{ color: '#1f6feb' }}>SLIM</span>
            </span>
          </div>
          <nav style={{ display: 'flex', gap: 0 }}>
            {(['스크리너', '시장', '포지션 플래너'] as const).map((label, i) => (
              <span key={label} onClick={i === 2 ? () => navigate('/calc') : undefined} style={{
                padding: '0 12px', fontSize: 12, color: i === 0 ? '#e6edf3' : '#4b5563',
                fontWeight: i === 0 ? 600 : 400, cursor: i === 2 ? 'pointer' : 'default', lineHeight: '40px',
                borderBottom: i === 0 ? '2px solid #1f6feb' : '2px solid transparent',
              }}>{label}</span>
            ))}
          </nav>
        </div>
        {items[0] && (
          <div style={{ display: 'flex', gap: 20 }}>
            <Stat label="기준일" value={items[0].scoreDate} />
            <Stat label="Top" value={String(items[0].compositeScore)} color="#4ade80" />
            <Stat label="Avg" value={(items.reduce((s, i) => s + i.compositeScore, 0) / items.length).toFixed(1)} />
          </div>
        )}
      </div>

      {/* ══ 시장 M 배너 ══════════════════════════════════════════ */}
      {!loading && items.length > 0 && (() => {
        const avgM = items.reduce((s, i) => s + (i.mScore ?? 0), 0) / items.length
        const { bg, border, label, desc } = avgM >= 60
          ? { bg: 'rgba(74,222,128,0.08)', border: '#4ade80', label: '매수 구간', desc: '시장 모멘텀 양호' }
          : avgM >= 40
          ? { bg: 'rgba(250,189,68,0.08)', border: '#fabd44', label: '관망 구간', desc: '추세 불확실' }
          : { bg: 'rgba(248,113,113,0.08)', border: '#f87171', label: '약세 구간 — 신규 매수 자제', desc: '하락 압력 우세' }
        const dot = avgM >= 60 ? '🟢' : avgM >= 40 ? '🟡' : '🔴'
        return (
          <div style={{
            margin: '0 20px', marginTop: 8, marginBottom: 4,
            background: bg, border: `1px solid ${border}`,
            borderRadius: 6, padding: '5px 14px',
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          }}>
            <span style={{ fontSize: 12, fontWeight: 600, color: '#e6edf3' }}>
              {dot} 시장 M 지수: {avgM.toFixed(1)} · {label}
            </span>
            <span style={{ fontSize: 10, color: '#6b7280' }}>{desc}</span>
          </div>
        )
      })()}

      {/* ══ Section 2: 필터 패널 ════════════════════════════════ */}
      <div style={{ background: '#0d1117', borderBottom: '2px solid #21262d', padding: '12px 20px' }}>
        <div style={{
          border: '1px solid #21262d', borderRadius: 6, background: '#0b0f17',
          overflow: 'hidden',
        }}>
          {/* 패널 헤더 */}
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '6px 12px', background: '#161b22', borderBottom: '1px solid #21262d',
          }}>
            <span style={{ fontSize: 10, fontWeight: 700, color: '#4b5563', letterSpacing: '0.08em' }}>
              스크리너 필터
              {activeFilterCount > 0 && (
                <span style={{
                  marginLeft: 8, background: '#1f3a5f', color: '#58a6ff',
                  borderRadius: 10, padding: '1px 7px', fontSize: 9,
                }}>{activeFilterCount}개 적용중</span>
              )}
            </span>
            {hasActiveFilter && (
              <button onClick={() => { setSector(''); setCapRange('all'); setQuery(''); setMinScore(0); setShowWatchOnly(false); setPage(0) }}
                style={{ fontSize: 10, color: '#6b7280', background: 'none', border: 'none', cursor: 'pointer' }}>
                초기화
              </button>
            )}
          </div>

          {/* 필터 그리드 */}
          <div style={{
            display: 'grid', gridTemplateColumns: 'auto 1fr auto 1fr',
            gap: '1px', background: '#21262d',
          }}>
            {/* 섹터 */}
            <FilterCell label="섹터">
              <select value={sector} onChange={e => { setSector(e.target.value); setPage(0) }}
                style={S.filterSelect}>
                <option value="">전체</option>
                {sectors.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </FilterCell>

            {/* 시가총액 */}
            <FilterCell label="시가총액">
              <div style={{ display: 'flex', gap: 3 }}>
                {(['all', 'large', 'mid', 'small'] as const).map(k => (
                  <button key={k} onClick={() => { setCapRange(k); setPage(0) }} style={{
                    padding: '3px 9px', fontSize: 10, fontWeight: 600, borderRadius: 3,
                    background: capRange === k ? '#1f3a5f' : '#161b22',
                    color: capRange === k ? '#58a6ff' : '#4b5563',
                    border: `1px solid ${capRange === k ? '#1d4ed8' : '#21262d'}`,
                    cursor: 'pointer',
                  }}>
                    {k === 'all' ? '전체' : k === 'large' ? '대형(1조↑)' : k === 'mid' ? '중형' : '소형'}
                  </button>
                ))}
              </div>
            </FilterCell>

            {/* 검색 */}
            <FilterCell label="종목검색">
              <input placeholder="종목명 / 티커" value={query}
                onChange={e => handleQuery(e.target.value)}
                style={{ ...S.filterInput, width: 180 }} />
            </FilterCell>

            {/* 수급단위 */}
            <FilterCell label="수급단위">
              <div style={{ display: 'flex', gap: 3 }}>
                {(['억원', '백만원'] as FlowUnit[]).map(u => (
                  <button key={u} onClick={() => setFlowUnit(u)} style={{
                    padding: '3px 10px', fontSize: 10, fontWeight: 600, borderRadius: 3,
                    background: flowUnit === u ? '#1a2a40' : '#161b22',
                    color: flowUnit === u ? '#38bdf8' : '#4b5563',
                    border: `1px solid ${flowUnit === u ? '#0e7490' : '#21262d'}`,
                    cursor: 'pointer',
                  }}>{u}</button>
                ))}
              </div>
            </FilterCell>

            {/* SCORE 최소 */}
            <FilterCell label="SCORE 최소">
              <div style={{ display: 'flex', gap: 3 }}>
                {([0, 60, 70, 80] as const).map(v => (
                  <button key={v} onClick={() => { setMinScore(v); setPage(0) }} style={{
                    padding: '3px 9px', fontSize: 10, fontWeight: 600, borderRadius: 3,
                    background: minScore === v ? '#1f3a5f' : '#161b22',
                    color: minScore === v ? '#58a6ff' : '#4b5563',
                    border: `1px solid ${minScore === v ? '#1d4ed8' : '#21262d'}`,
                    cursor: 'pointer',
                  }}>
                    {v === 0 ? '전체' : String(v)}
                  </button>
                ))}
              </div>
            </FilterCell>

            {/* 관심종목 */}
            <FilterCell label="관심종목">
              <button onClick={() => setShowWatchOnly(v => !v)} style={{
                padding: '3px 12px', fontSize: 10, fontWeight: 600, borderRadius: 3,
                background: showWatchOnly ? '#2d1a4a' : '#161b22',
                color: showWatchOnly ? '#c084fc' : '#4b5563',
                border: `1px solid ${showWatchOnly ? '#7c3aed' : '#21262d'}`,
                cursor: 'pointer',
              }}>
                {showWatchOnly ? '★ 관심종목만' : '☆ 전체보기'}
              </button>
            </FilterCell>
          </div>
        </div>
      </div>

      {/* ══ Section 3: 결과바 + 뷰탭 (sticky) ══════════════════ */}
      <div style={{
        position: 'sticky', top: 0, zIndex: 20,
        background: '#0d1117', borderBottom: '1px solid #21262d',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0 20px',
      }}>
        {/* 뷰 탭 */}
        <div style={{ display: 'flex' }}>
          {([
            ['overview', '개요'],
            ['technical', '기술적'],
            ['flow', '수급'],
          ] as [ViewTab, string][]).map(([key, label]) => (
            <button key={key} onClick={() => setViewTab(key)} style={S.tab(viewTab === key)}>
              {label}
            </button>
          ))}
        </div>

        {/* 결과 카운트 + 행수 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {!loading && (
            <span style={{ fontSize: 11, color: '#4b5563' }}>
              <span style={{ color: '#6b7280', fontWeight: 600 }}>{total.toLocaleString()}</span>
              {' '}종목
              {hasActiveFilter && <span style={{ color: '#1d4ed8' }}> (필터 적용)</span>}
            </span>
          )}
          <select value={size} onChange={e => handleSize(Number(e.target.value))}
            style={{ ...S.filterSelect, fontSize: 10 }}>
            {[30, 50, 100].map(n => <option key={n} value={n}>{n}행</option>)}
          </select>
        </div>
      </div>

      {/* ── Table area ───────────────────────────────────────── */}
      <div style={{ padding: '0 20px' }}>
        <div ref={scrollRef} onScroll={onTableScroll} className="hide-scrollbar"
          style={{ overflowX: 'auto' }}>
          {loading ? (
            <div style={{ textAlign: 'center', padding: '80px 0', color: '#374151', fontSize: 13 }}>
              <span style={{ display: 'inline-block', animation: 'spin 1s linear infinite' }}>⟳</span>
              {' '}데이터 로딩 중...
            </div>
          ) : (
            <table style={{
              width: '100%', borderCollapse: 'collapse', tableLayout: 'fixed',
              minWidth: viewTab === 'overview' ? 900 : 700,
            }}>
              <thead>{renderHead()}</thead>
              <tbody>
                {displayItems.map((item, idx) => (
                  <tr key={item.securityId}
                    onClick={() => navigate(`/stock/${item.securityId}`)}
                    onMouseEnter={() => setHoveredId(item.securityId)}
                    onMouseLeave={() => setHoveredId(null)}
                    style={{
                      cursor: 'pointer',
                      background: hoveredId === item.securityId ? '#161b22'
                        : idx % 2 === 0 ? '#0b0f17' : '#0d1117',
                      transition: 'background 0.08s',
                    }}>
                    {renderRow(item, idx)}
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {!loading && items.length === 0 && (
            <div style={{ textAlign: 'center', padding: '60px 0', color: '#374151', fontSize: 13 }}>
              검색 결과 없음
            </div>
          )}
        </div>

        {/* sticky mirror scrollbar */}
        <div ref={mirrorRef} onScroll={onMirrorScroll} style={{
          position: 'sticky', bottom: 0, overflowX: 'auto', overflowY: 'hidden',
          zIndex: 5, background: '#0b0f17', borderTop: '1px solid #161b22',
        }}>
          <div style={{
            minWidth: viewTab === 'overview' ? 900 : 700, height: 1,
          }} />
        </div>
      </div>

      {/* ── Pagination ───────────────────────────────────────── */}
      {!loading && totalPages > 1 && (
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          padding: '12px 20px 32px', borderTop: '1px solid #161b22',
        }}>
          <span style={{ fontSize: 11, color: '#374151' }}>
            {total.toLocaleString()}종목 · {page + 1}/{totalPages}페이지
          </span>
          <div style={{ display: 'flex', gap: 3 }}>
            <PgBtn label="«" onClick={() => setPage(0)} disabled={page === 0} />
            <PgBtn label="‹" onClick={() => setPage(p => p - 1)} disabled={page === 0} />
            {pageNums.map(p => (
              <PgBtn key={p} label={String(p + 1)} onClick={() => setPage(p)} active={p === page} />
            ))}
            <PgBtn label="›" onClick={() => setPage(p => p + 1)} disabled={page >= totalPages - 1} />
            <PgBtn label="»" onClick={() => setPage(totalPages - 1)} disabled={page >= totalPages - 1} />
          </div>
          <div style={{ width: 120 }} />
        </div>
      )}
    </div>
  )
}

// ── small helpers ──────────────────────────────────────────────
function Stat({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'baseline', gap: 4 }}>
      <span style={{ fontSize: 9, color: '#374151', fontWeight: 600, letterSpacing: '0.05em' }}>{label}</span>
      <span style={{ fontSize: 12, color: color ?? '#6b7280', fontWeight: 600 }}>{value}</span>
    </div>
  )
}

function FilterCell({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <>
      <div style={{
        background: '#0d1117', padding: '8px 12px',
        display: 'flex', alignItems: 'center',
        borderRight: '1px solid #21262d',
      }}>
        <span style={{
          fontSize: 10, fontWeight: 700, color: '#374151',
          letterSpacing: '0.06em', whiteSpace: 'nowrap',
        }}>{label}</span>
      </div>
      <div style={{
        background: '#0b0f17', padding: '8px 12px',
        display: 'flex', alignItems: 'center',
        borderRight: '1px solid #21262d',
      }}>
        {children}
      </div>
    </>
  )
}

function PgBtn({ label, onClick, disabled, active }: {
  label: string; onClick: () => void; disabled?: boolean; active?: boolean
}) {
  return (
    <button onClick={onClick} disabled={disabled} style={{
      minWidth: 28, height: 26, padding: '0 6px',
      background: active ? '#1f3a5f' : 'transparent',
      border: `1px solid ${active ? '#1f6feb' : '#21262d'}`,
      borderRadius: 4, color: disabled ? '#21262d' : active ? '#58a6ff' : '#4b5563',
      fontSize: 11, cursor: disabled ? 'default' : 'pointer', fontWeight: active ? 700 : 400,
    }}>
      {label}
    </button>
  )
}
