// frontend/src/utils/factors.ts
// 팩터 스코어 → 색/티어/등급 매핑 (전부 index.css 변수 → [data-theme] 라이트/다크 자동 대응).

export interface Tier { color: string; label: string; tint: string }

/** 종합 스코어 → 티어(색·라벨·배경틴트). null은 미집계 처리. */
export function scoreTier(score: number | null): Tier {
  if (score == null) return { color: 'var(--text-4)', label: '미집계', tint: 'transparent' }
  if (score >= 80)   return { color: 'var(--accent-strong)', label: '매우 강함', tint: 'var(--accent-soft)' }
  if (score >= 68)   return { color: 'var(--accent)',        label: '강함',       tint: 'var(--accent-soft)' }
  if (score >= 52)   return { color: 'var(--accent)',        label: '보통',       tint: 'transparent' }
  return               { color: 'var(--text-3)',       label: '약함',       tint: 'transparent' }
}

/** 한국식 등락 색 (index.css --up/--down). */
export const changeColor = (chg: number | null): string =>
  chg == null ? 'var(--text-3)' : chg > 0 ? 'var(--up)' : chg < 0 ? 'var(--down)' : 'var(--text-3)'

/** 스코어(0~100) → 텍스트/포인트 색. */
export function scoreFg(v: number | null): string {
  if (v == null) return 'var(--text-4)'
  if (v >= 85) return '#4ade80'
  if (v >= 70) return '#86efac'
  if (v >= 55) return '#fabd44'
  if (v >= 40) return '#f97316'
  return '#f87171'
}

/** 스코어(0~100) → 셀 배경 틴트 (스크리너 스코어 셀). */
export function scoreBg(v: number | null): string {
  if (v == null) return 'transparent'
  if (v >= 85) return 'rgba(74,222,128,0.18)'
  if (v >= 70) return 'rgba(74,222,128,0.09)'
  if (v >= 55) return 'rgba(250,189,68,0.15)'
  if (v >= 40) return 'rgba(249,115,22,0.18)'
  return 'rgba(248,113,113,0.15)'
}

export interface Grade { color: string; label: string }

/** 스코어(0~100) → 등급 뱃지(색·라벨). composite/factor 공통 스케일. */
export function scoreGrade(v: number | null): Grade {
  if (v == null) return { color: 'var(--text-3)', label: 'N/A' }
  if (v >= 85) return { color: '#4ade80', label: 'A+' }
  if (v >= 75) return { color: '#86efac', label: 'A' }
  if (v >= 65) return { color: '#fabd44', label: 'B+' }
  if (v >= 55) return { color: '#fbbf24', label: 'B' }
  if (v >= 45) return { color: '#f97316', label: 'C' }
  return { color: '#f87171', label: 'D' }
}
