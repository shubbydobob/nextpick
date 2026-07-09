import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { login, register } from '../api/auth'

type Tab = 'login' | 'register'

export default function AuthPage() {
  const navigate = useNavigate()
  const [tab, setTab] = useState<Tab>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSuccess(null)
    setLoading(true)
    try {
      if (tab === 'login') {
        await login(email.trim(), password)
        navigate('/')
      } else {
        await register(email.trim(), password)
        setSuccess('회원가입 완료! 로그인하세요.')
        setTab('login')
        setPassword('')
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '오류가 발생했습니다.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        {/* 로고 */}
        <div className="auth-logo">
          <div className="auth-brand">
            <span className="auth-brand-dot" />
            NEXT<em>PICK</em>
          </div>
          <div className="auth-tagline">주도주 스코어 스크리너</div>
        </div>

        {/* 탭 */}
        <div className="auth-tabs">
          {(['login', 'register'] as Tab[]).map(t => (
            <button key={t} onClick={() => { setTab(t); setError(null); setSuccess(null) }}
              className={`auth-tab${tab === t ? ' on' : ''}`}>
              {t === 'login' ? '로그인' : '회원가입'}
            </button>
          ))}
        </div>

        {/* 폼 */}
        <form onSubmit={handleSubmit} className="auth-form">
          <div>
            <label className="auth-label">이메일</label>
            <input
              className="auth-input"
              type="email" value={email} onChange={e => setEmail(e.target.value)}
              placeholder="you@example.com" required autoComplete="email"
            />
          </div>

          <div>
            <label className="auth-label">
              비밀번호 {tab === 'register' && <small>(6자 이상)</small>}
            </label>
            <input
              className="auth-input"
              type="password" value={password} onChange={e => setPassword(e.target.value)}
              placeholder="••••••••" required minLength={tab === 'register' ? 6 : 1}
              autoComplete={tab === 'login' ? 'current-password' : 'new-password'}
            />
          </div>

          {error && <div className="auth-alert err">{error}</div>}
          {success && <div className="auth-alert ok">{success}</div>}

          <button type="submit" disabled={loading} className="btn-fill auth-submit">
            {loading ? '처리 중...' : tab === 'login' ? '로그인' : '회원가입'}
          </button>
        </form>

        {/* 하단 링크 */}
        <div className="auth-back-wrap">
          <button onClick={() => navigate('/')} className="auth-back">
            ← 스크리너로 돌아가기
          </button>
        </div>
      </div>
    </div>
  )
}
