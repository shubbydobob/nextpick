import { Routes, Route } from 'react-router-dom'
import ScreenerPage from './pages/ScreenerPage'
import StockDetailPage from './pages/StockDetailPage'
import TradingCalcPage from './pages/TradingCalcPage'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<ScreenerPage />} />
      <Route path="/stock/:securityId" element={<StockDetailPage />} />
      <Route path="/calc" element={<TradingCalcPage />} />
    </Routes>
  )
}
