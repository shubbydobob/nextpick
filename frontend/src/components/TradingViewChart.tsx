interface Props {
  ticker: string
  height?: number
  onFallback?: () => void
}

export default function TradingViewChart({ ticker, height = 460 }: Props) {
  const params = new URLSearchParams({
    symbol:         `KRX:${ticker}`,
    interval:       'D',
    theme:          'dark',
    style:          '1',
    locale:         'ko',
    timezone:       'Asia/Seoul',
    hide_top_toolbar: '0',
    hide_legend:    '0',
    studies:        'RSI@tv-basicstudies,Volume@tv-basicstudies',
    backgroundColor: '#0d1117',
    gridColor:      'rgba(255,255,255,0.04)',
  })

  return (
    <div style={{
      background: '#0d1117',
      borderRadius: 10,
      border: '1px solid #21262d',
      overflow: 'hidden',
      height,
    }}>
      <iframe
        key={ticker}
        src={`https://s.tradingview.com/widgetembed/?${params}`}
        style={{ width: '100%', height: '100%', border: 'none' }}
        allowFullScreen
        referrerPolicy="no-referrer-when-downgrade"
      />
    </div>
  )
}
