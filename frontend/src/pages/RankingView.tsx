import { type CSSProperties } from 'react'
import type { ScreenerItem } from '../types'
import type { LiveQuote } from '../api/client'
import { useIsMobile } from '../hooks/useIsMobile'
import StatusBadges from '../components/StatusBadges'
import { scoreFg, changeColor } from '../utils/factors'
import { fmtRate } from '../utils/format'

interface Props {
  items: ScreenerItem[]
  loading: boolean
  onStockClick: (id: number) => void
  liveMap?: Record<string, LiveQuote>
}

export default function RankingView({ items, loading, onStockClick, liveMap }: Props) {
  const isMobile = useIsMobile()

  const topItems = [...items]
    .sort((a, b) => b.compositeScore - a.compositeScore)
    .slice(0, 50)
  const maxScore = topItems[0]?.compositeScore ?? 100

  // 장중 라이브 오버레이 — 등락률·특이사항(뱃지) 병합.
  const liveOf = (item: ScreenerItem) => {
    const q = liveMap?.[item.ticker]
    return {
      changeRate: q?.changeRate ?? item.changeRate,
      statuses: q?.statuses ?? item.statuses ?? null,
    }
  }

  if (loading) {
    return (
      <div className="rank-loading">
        <span className="spinner" />
        랭킹 데이터 로딩 중...
      </div>
    )
  }

  const medalColor = (idx: number) =>
    idx === 0 ? '#FFD700' : idx === 1 ? '#C0C0C0' : idx === 2 ? '#CD7F32' : null

  // 링 게이지 스타일(점수·색·지름·안쪽배경) 헬퍼 — 동적값만 CSS 변수로 전달.
  const ring = (score: number, color: string, size: string, bg: string): CSSProperties => ({
    ['--v' as string]: score,
    ['--gc' as string]: color,
    ['--sr' as string]: size,
    ['--ring-bg' as string]: bg,
  })

  // ── 모바일: 카드형 리스트 ──────────────────────────────────────────────
  if (isMobile) {
    return (
      <div className="rank-mobile">
        <div className="rank-head">
          <div className="rank-title">스코어 랭킹</div>
          <div className="rank-sub">종합점수 기준 상위 50개 종목</div>
        </div>

        <div className="rank-list">
          {topItems.map((item, idx) => {
            const live = liveOf(item)
            const sc = scoreFg(item.compositeScore)
            const barPct = maxScore > 0 ? (item.compositeScore / maxScore) * 100 : 0
            const medal = medalColor(idx)

            return (
              <div key={item.securityId} className="rank-card"
                onClick={() => onStockClick(item.securityId)}
                style={medal ? { ['--medal' as string]: medal } : undefined}>
                <span className="rank-medal">{idx + 1}</span>

                <div className="rank-card-id">
                  <div className="rank-name-line">
                    <span className="rank-name">{item.name}</span>
                    {item.breakoutToday && <span className="rank-badge-new">NEW</span>}
                    <StatusBadges statuses={live.statuses} size="xs" />
                  </div>
                  <div className="rank-sub-line">
                    <span className="rank-ticker">{item.ticker}</span>
                    {item.sector && <span className="rank-sector">· {item.sector}</span>}
                  </div>
                  <div className="rank-bar">
                    <div className="rank-bar-fill" style={{ ['--bar-pct' as string]: `${barPct}%`, ['--bar-color' as string]: sc }} />
                  </div>
                </div>

                <div className="rank-card-right">
                  <div className="rank-card-metrics">
                    <span className="rank-rate" style={{ ['--sc-rate' as string]: changeColor(live.changeRate) }}>
                      {fmtRate(live.changeRate)}
                    </span>
                  </div>
                  <div className="score-ring" style={ring(item.compositeScore, sc, '50px', 'var(--bg-nav)')}>
                    <b>{Math.round(item.compositeScore)}</b>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    )
  }

  // ── 데스크톱: 그리드 테이블 ────────────────────────────────────────────
  return (
    <div className="rank-page">
      <div className="rank-head">
        <div className="rank-title">스코어 랭킹</div>
        <div className="rank-sub">종합점수 기준 상위 50개 종목</div>
      </div>

      <div className="rank-table">
        <div className="rank-grid rank-thead">
          <div className="rank-ta-c">순위</div>
          <div>티커</div>
          <div>종목명</div>
          <div className="rank-ta-c">점수</div>
          <div className="rank-ta-r">등락률</div>
          <div className="rank-ta-r">섹터</div>
        </div>

        {topItems.map((item, idx) => {
          const live = liveOf(item)
          const sc = scoreFg(item.compositeScore)
          const barPct = maxScore > 0 ? (item.compositeScore / maxScore) * 100 : 0
          const medal = medalColor(idx)

          return (
            <div key={item.securityId} className="rank-grid rank-row"
              onClick={() => onStockClick(item.securityId)}
              style={medal ? { ['--medal' as string]: medal } : undefined}>
              <span className="rank-medal">{idx + 1}</span>

              <span className="rank-ticker">
                {item.ticker}
                {item.breakoutToday && <span className="rank-badge-new">NEW</span>}
              </span>

              <div className="rank-namecol">
                <div className="rank-name-line">
                  <span className="rank-name">{item.name}</span>
                  <StatusBadges statuses={live.statuses} size="sm" />
                </div>
                <div className="rank-bar">
                  <div className="rank-bar-fill" style={{ ['--bar-pct' as string]: `${barPct}%`, ['--bar-color' as string]: sc }} />
                </div>
              </div>

              <div className="rank-ta-c">
                <div className="score-ring" style={ring(item.compositeScore, sc, '40px', 'var(--bg-surface)')}>
                  <b>{Math.round(item.compositeScore)}</b>
                </div>
              </div>

              <div className="rank-ta-r">
                <span className="rank-rate" style={{ ['--sc-rate' as string]: changeColor(live.changeRate) }}>
                  {fmtRate(live.changeRate)}
                </span>
              </div>

              <div className="rank-sector rank-ta-r">{item.sector ?? '—'}</div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
