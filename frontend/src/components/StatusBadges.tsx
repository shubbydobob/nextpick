/**
 * 종목 특이사항 뱃지 — 거래정지·투자주의/경고/위험·관리종목·단기과열 등.
 *
 * 데이터 출처: KIS 주식현재가시세(FHKST01010100)의 종목상태/시장경고/단기과열 코드.
 * 백엔드 /api/realtime/quotes 가 statuses(string[])로 내려주며, 장중 오버레이 창에서만 채워진다.
 * (장외 시간엔 KIS가 상태를 주지 않으므로 뱃지도 표시되지 않음 — 실시간 시세와 동일한 정책.)
 */

interface BadgeStyle {
  bg: string
  color: string
  border: string
}

// 심각도 높은 순으로 정렬 우선순위 + 색상.
const BADGE_STYLES: Record<string, BadgeStyle & { order: number }> = {
  거래정지: { order: 0, bg: 'rgba(107,114,128,0.18)', color: '#d1d5db', border: 'rgba(156,163,175,0.5)' },
  정리매매: { order: 1, bg: 'rgba(120,53,15,0.25)', color: '#fdba74', border: 'rgba(234,88,12,0.5)' },
  위험:     { order: 2, bg: 'rgba(127,29,29,0.3)', color: '#fca5a5', border: 'rgba(239,68,68,0.55)' },
  경고:     { order: 3, bg: 'rgba(124,45,18,0.3)', color: '#fdba74', border: 'rgba(249,115,22,0.55)' },
  주의:     { order: 4, bg: 'rgba(113,63,18,0.3)', color: '#fcd34d', border: 'rgba(234,179,8,0.5)' },
  과열:     { order: 5, bg: 'rgba(131,24,67,0.3)', color: '#f9a8d4', border: 'rgba(236,72,153,0.5)' },
  관리:     { order: 6, bg: 'rgba(76,29,149,0.28)', color: '#c4b5fd', border: 'rgba(139,92,246,0.5)' },
}

// 뱃지 라벨을 좀 더 명확한 표기로 (툴팁·접근성용).
const FULL_LABEL: Record<string, string> = {
  거래정지: '거래정지 — 매매 중단 상태',
  정리매매: '정리매매 — 상장폐지 절차 진행',
  위험: '투자위험 — 시장경보 3단계',
  경고: '투자경고 — 시장경보 2단계',
  주의: '투자주의 — 시장경보 1단계',
  과열: '단기과열 — 단기 급등락 지정',
  관리: '관리종목 — 상장폐지 우려',
}

interface Props {
  statuses?: string[] | null
  size?: 'sm' | 'xs'
}

export default function StatusBadges({ statuses, size = 'sm' }: Props) {
  if (!statuses || statuses.length === 0) return null

  const sorted = [...new Set(statuses)]
    .filter(s => BADGE_STYLES[s])
    .sort((a, b) => BADGE_STYLES[a].order - BADGE_STYLES[b].order)

  if (sorted.length === 0) return null

  const fs = size === 'xs' ? 8.5 : 9.5
  const pad = size === 'xs' ? '1px 4px' : '1.5px 5px'

  return (
    <span style={{ display: 'inline-flex', gap: 3, flexShrink: 0, verticalAlign: 'middle' }}>
      {sorted.map(s => {
        const st = BADGE_STYLES[s]
        return (
          <span
            key={s}
            title={FULL_LABEL[s] ?? s}
            style={{
              fontSize: fs,
              fontWeight: 700,
              lineHeight: 1.4,
              padding: pad,
              borderRadius: 4,
              background: st.bg,
              color: st.color,
              border: `1px solid ${st.border}`,
              whiteSpace: 'nowrap',
              letterSpacing: '-0.01em',
            }}
          >
            {s}
          </span>
        )
      })}
    </span>
  )
}
