import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import StockDetail from './pages/StockDetail'
import Screener from './pages/Screener'
import Watchlist from './pages/Watchlist'
import Portfolio from './pages/Portfolio'
import Login from './pages/Login'
import Register from './pages/Register'

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth()
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" />
}

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="stock/:ticker" element={<StockDetail />} />
        <Route path="screener" element={<Screener />} />
        <Route
          path="watchlist"
          element={
            <PrivateRoute>
              <Watchlist />
            </PrivateRoute>
          }
        />
        <Route
          path="portfolio"
          element={
            <PrivateRoute>
              <Portfolio />
            </PrivateRoute>
          }
        />
      </Route>
    </Routes>
  )
}

export default App
