import type { ScreenerItem, ScreenerPage, ScoreHistory, FinancialRecord, PriceBar, MacroQuote } from '../types'

const BASE = '/api'

export async function fetchScreener(
  market = 'KR',
  page = 0,
  size = 30,
  q = '',
  sector = '',
  minCap?: number,
  maxCap?: number,
  sortBy = 'compositeScore',
  sortDir = 'desc',
  minScore?: number,
): Promise<ScreenerPage> {
  const params = new URLSearchParams({ market, page: String(page), size: String(size), sortBy, sortDir })
  if (q) params.set('q', q)
  if (sector) params.set('sector', sector)
  if (minCap != null) params.set('minCap', String(minCap))
  if (maxCap != null) params.set('maxCap', String(maxCap))
  if (minScore != null && minScore > 0) params.set('minScore', String(minScore))
  const res = await fetch(`${BASE}/screener?${params}`)
  if (!res.ok) throw new Error('screener fetch failed')
  return res.json()
}

export async function fetchSectors(): Promise<string[]> {
  const res = await fetch(`${BASE}/screener/sectors`)
  if (!res.ok) return []
  return res.json()
}

export async function fetchStockScore(securityId: number): Promise<ScreenerItem> {
  const res = await fetch(`${BASE}/screener/${securityId}`)
  if (!res.ok) throw new Error('score fetch failed')
  return res.json()
}

export async function fetchStockHistory(securityId: number): Promise<ScoreHistory[]> {
  const res = await fetch(`${BASE}/screener/${securityId}/history`)
  if (!res.ok) throw new Error('history fetch failed')
  return res.json()
}

export async function fetchStockFinancials(securityId: number): Promise<FinancialRecord[]> {
  const res = await fetch(`${BASE}/screener/${securityId}/financials`)
  if (!res.ok) return []
  return res.json()
}

export async function fetchStockPrices(securityId: number, days = 365): Promise<PriceBar[]> {
  const res = await fetch(`${BASE}/screener/${securityId}/prices?days=${days}`)
  if (!res.ok) return []
  return res.json()
}

export async function fetchMacroQuotes(): Promise<MacroQuote[]> {
  const res = await fetch(`${BASE}/macro/quotes`)
  if (!res.ok) return []
  return res.json()
}
