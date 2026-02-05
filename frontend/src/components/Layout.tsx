import { Outlet, Link, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import {
  LayoutDashboard,
  Search,
  Star,
  Briefcase,
  LogIn,
  LogOut,
  TrendingUp,
} from 'lucide-react'

export default function Layout() {
  const { isAuthenticated, user, logout } = useAuth()
  const location = useLocation()

  const navItems = [
    { path: '/', label: 'Dashboard', icon: LayoutDashboard },
    { path: '/screener', label: 'Screener', icon: Search },
    { path: '/watchlist', label: 'Watchlist', icon: Star, auth: true },
    { path: '/portfolio', label: 'Portfolio', icon: Briefcase, auth: true },
  ]

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            {/* Logo */}
            <Link to="/" className="flex items-center gap-2">
              <TrendingUp className="h-8 w-8 text-primary-600" />
              <span className="text-xl font-bold text-gray-900">Stonks</span>
            </Link>

            {/* Navigation */}
            <nav className="hidden md:flex items-center gap-6">
              {navItems.map((item) => {
                if (item.auth && !isAuthenticated) return null
                const Icon = item.icon
                const isActive = location.pathname === item.path
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ${
                      isActive
                        ? 'bg-primary-50 text-primary-600'
                        : 'text-gray-600 hover:bg-gray-100'
                    }`}
                  >
                    <Icon className="h-5 w-5" />
                    <span>{item.label}</span>
                  </Link>
                )
              })}
            </nav>

            {/* Auth */}
            <div className="flex items-center gap-4">
              {isAuthenticated ? (
                <>
                  <span className="text-sm text-gray-600">
                    {user?.full_name || user?.email}
                  </span>
                  <button
                    onClick={logout}
                    className="flex items-center gap-2 text-gray-600 hover:text-gray-900"
                  >
                    <LogOut className="h-5 w-5" />
                  </button>
                </>
              ) : (
                <Link
                  to="/login"
                  className="flex items-center gap-2 text-gray-600 hover:text-gray-900"
                >
                  <LogIn className="h-5 w-5" />
                  <span>Login</span>
                </Link>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Mobile Navigation */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 z-50">
        <div className="flex justify-around py-2">
          {navItems.map((item) => {
            if (item.auth && !isAuthenticated) return null
            const Icon = item.icon
            const isActive = location.pathname === item.path
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex flex-col items-center p-2 ${
                  isActive ? 'text-primary-600' : 'text-gray-600'
                }`}
              >
                <Icon className="h-6 w-6" />
                <span className="text-xs mt-1">{item.label}</span>
              </Link>
            )
          })}
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 pb-24 md:pb-8">
        <Outlet />
      </main>
    </div>
  )
}
