const TOKEN_KEY = 'canslim_token'
const BASE = '/api/auth'

export interface UserInfo {
  email: string
  plan: 'free' | 'premium'
  expiresAt: string | null
}

export function getToken(): string | null {
  try { return localStorage.getItem(TOKEN_KEY) } catch { return null }
}

export function setToken(token: string): void {
  try { localStorage.setItem(TOKEN_KEY, token) } catch {}
}

export function clearToken(): void {
  try { localStorage.removeItem(TOKEN_KEY) } catch {}
}

export function isPremium(): boolean {
  // Fast local check: store plan in localStorage too
  try {
    const raw = localStorage.getItem('canslim_user')
    if (!raw) return false
    const user: UserInfo = JSON.parse(raw)
    return user.plan === 'premium'
  } catch { return false }
}

export function isLoggedIn(): boolean {
  return getToken() !== null
}

export async function fetchMe(): Promise<UserInfo | null> {
  const token = getToken()
  if (!token) return null
  try {
    const res = await fetch(`${BASE}/me`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    if (!res.ok) {
      clearToken()
      localStorage.removeItem('canslim_user')
      return null
    }
    const data: UserInfo = await res.json()
    localStorage.setItem('canslim_user', JSON.stringify(data))
    return data
  } catch { return null }
}

export async function login(email: string, password: string): Promise<string> {
  const res = await fetch(`${BASE}/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  const data = await res.json()
  if (!res.ok) throw new Error(data.error ?? '로그인 실패')
  setToken(data.token)
  await fetchMe()
  return data.token
}

export async function register(email: string, password: string): Promise<{ userId: number; email: string }> {
  const res = await fetch(`${BASE}/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  const data = await res.json()
  if (!res.ok) throw new Error(data.error ?? '회원가입 실패')
  return data
}

export function logout(): void {
  clearToken()
  localStorage.removeItem('canslim_user')
}
