import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { fetchMe, isLoggedIn, logout } from '../api/auth'
import type { UserInfo } from '../api/auth'

const BENEFITS = [
  { icon: '🔔', title: '알림 무제한', free: '5개 종목 제한', premium: '무제한 관심종목 알림' },
  { icon: '📄', title: 'PDF 리포트 다운로드', free: '미지원', premium: '종목별 상세 PDF 리포트' },
  { icon: '🔬', title: '섹터별 심층 분석', free: '기본 섹터 비교', premium: '섹터 내 전체 종목 심층 분석' },
  { icon: '💼', title: '포트폴리오 추적', free: '미지원', premium: '보유 종목 수익률 추적' },
  { icon: '📊', title: '점수 히스토리', free: '30일', premium: '전체 기간 히스토리' },
  { icon: '⚡', title: '실시간 알림', free: '미지원', premium: '브레이크아웃 즉시 알림 (예정)' },
]

export default function PremiumPage() {
  const navigate = useNavigate()
  const [user, setUser] = useState<UserInfo | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!isLoggedIn()) {
      setLoading(false)
      return
    }
    fetchMe().then(u => { setUser(u); setLoading(false) })
  }, [])

  const handleLogout = () => {
    logout()
    navigate('/')
  }

  if (loading) return <div className="prem-loading">로딩 중...</div>

  return (
    <div className="prem-page">
      {/* Header */}
      <div className="prem-header">
        <button onClick={() => navigate('/')} className="prem-back">
          ← NEXT<em>PICK</em>
        </button>
        {user && (
          <div className="prem-user">
            <span className="prem-email">{user.email}</span>
            <button onClick={handleLogout} className="prem-logout">로그아웃</button>
          </div>
        )}
      </div>

      <div className="prem-body">
        {/* 현재 플랜 */}
        <div className="prem-plan">
          {user ? (
            <>
              <div className="prem-plan-cap">현재 플랜</div>
              <div className="prem-plan-row">
                <div className={`prem-plan-name${user.plan === 'premium' ? ' gold' : ''}`}>
                  {user.plan === 'premium' ? '✦ 프리미엄' : '무료 플랜'}
                </div>
                {user.plan === 'premium' && user.expiresAt && (
                  <div className="prem-plan-exp">
                    만료: {new Date(user.expiresAt).toLocaleDateString('ko-KR')}
                  </div>
                )}
              </div>
              <div className="prem-plan-email">{user.email}</div>
            </>
          ) : (
            <>
              <div className="prem-login-title">로그인이 필요합니다</div>
              <button onClick={() => navigate('/auth')} className="btn-fill prem-cta-btn">
                로그인 / 회원가입
              </button>
            </>
          )}
        </div>

        {/* 혜택 비교 */}
        <div className="prem-sec-title">플랜 비교</div>
        <div className="prem-table">
          {/* 컬럼 헤더 */}
          <div className="prem-trow prem-thead">
            <div className="prem-th">기능</div>
            <div className="prem-th c">무료</div>
            <div className="prem-th c gold">✦ 프리미엄</div>
          </div>

          {BENEFITS.map(b => (
            <div key={b.title} className="prem-trow">
              <div className="prem-feat">
                <span className="prem-feat-icon">{b.icon}</span>
                <span className="prem-feat-name">{b.title}</span>
              </div>
              <div className="prem-free">
                {b.free === '미지원' ? <span className="x">✕</span> : b.free}
              </div>
              <div className="prem-prem">
                <span>✓</span> {b.premium}
              </div>
            </div>
          ))}
        </div>

        {/* 업그레이드 CTA */}
        {user?.plan !== 'premium' && (
          <div className="prem-cta">
            <div className="prem-cta-title">프리미엄 업그레이드</div>
            <div className="prem-cta-desc">
              NEXTPICK의 분석 도구를 최대한 활용하세요.<br />
              고급 분석 도구와 무제한 알림으로 투자 엣지를 확보하세요.
            </div>
            <a href="mailto:contact@nextpick.kr?subject=프리미엄 구독 문의" className="prem-cta-btn">
              문의하기 (Toss Payments 연동 예정)
            </a>
            <div className="prem-cta-note">
              현재 베타 서비스 중 — 출시 시 별도 안내 예정
            </div>
          </div>
        )}

        {user?.plan === 'premium' && (
          <div className="prem-member">
            <div className="prem-member-title">✦ 프리미엄 멤버</div>
            <div className="prem-member-desc">모든 프리미엄 기능을 이용하실 수 있습니다.</div>
          </div>
        )}
      </div>
    </div>
  )
}
