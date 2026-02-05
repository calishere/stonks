import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { TrendingUp, TrendingDown, Star, BarChart3 } from 'lucide-react'
import { screenerApi } from '../services/api'
import StockTable from '../components/StockTable'
import Loading from '../components/Loading'

export default function Dashboard() {
  const { data: undervalued, isLoading: loadingUndervalued } = useQuery({
    queryKey: ['undervalued'],
    queryFn: () => screenerApi.getUndervalued(15),
  })

  const { data: quality, isLoading: loadingQuality } = useQuery({
    queryKey: ['quality'],
    queryFn: screenerApi.getQuality,
  })

  const { data: growth, isLoading: loadingGrowth } = useQuery({
    queryKey: ['growth'],
    queryFn: screenerApi.getGrowth,
  })

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Stock Analysis Dashboard</h1>
        <p className="mt-2 text-gray-600">
          Fundamental analysis for US stocks with market cap over $1 billion
        </p>
      </div>

      {/* Quick Links */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Link
          to="/screener?preset=undervalued"
          className="card p-6 hover:shadow-md transition-shadow"
        >
          <div className="flex items-center gap-4">
            <div className="p-3 bg-green-100 rounded-lg">
              <TrendingUp className="h-6 w-6 text-green-600" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">Undervalued Stocks</h3>
              <p className="text-sm text-gray-500">
                Stocks trading below fair value
              </p>
            </div>
          </div>
        </Link>

        <Link
          to="/screener?preset=quality"
          className="card p-6 hover:shadow-md transition-shadow"
        >
          <div className="flex items-center gap-4">
            <div className="p-3 bg-blue-100 rounded-lg">
              <Star className="h-6 w-6 text-blue-600" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">Quality Stocks</h3>
              <p className="text-sm text-gray-500">
                High ROE, ROCE, and margins
              </p>
            </div>
          </div>
        </Link>

        <Link
          to="/screener?preset=growth"
          className="card p-6 hover:shadow-md transition-shadow"
        >
          <div className="flex items-center gap-4">
            <div className="p-3 bg-purple-100 rounded-lg">
              <BarChart3 className="h-6 w-6 text-purple-600" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">Growth Stocks</h3>
              <p className="text-sm text-gray-500">
                Strong revenue and EPS growth
              </p>
            </div>
          </div>
        </Link>
      </div>

      {/* Undervalued Stocks */}
      <section className="card">
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-green-600" />
              Top Undervalued Stocks
            </h2>
            <Link
              to="/screener?preset=undervalued"
              className="text-primary-600 hover:text-primary-800 text-sm"
            >
              View All
            </Link>
          </div>
        </div>
        {loadingUndervalued ? (
          <Loading message="Loading undervalued stocks..." />
        ) : (
          <StockTable stocks={undervalued?.slice(0, 5) || []} />
        )}
      </section>

      {/* Quality Stocks */}
      <section className="card">
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
              <Star className="h-5 w-5 text-blue-600" />
              Quality Stocks
            </h2>
            <Link
              to="/screener?preset=quality"
              className="text-primary-600 hover:text-primary-800 text-sm"
            >
              View All
            </Link>
          </div>
        </div>
        {loadingQuality ? (
          <Loading message="Loading quality stocks..." />
        ) : (
          <StockTable stocks={quality?.slice(0, 5) || []} />
        )}
      </section>

      {/* Growth Stocks */}
      <section className="card">
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
              <BarChart3 className="h-5 w-5 text-purple-600" />
              Growth Stocks
            </h2>
            <Link
              to="/screener?preset=growth"
              className="text-primary-600 hover:text-primary-800 text-sm"
            >
              View All
            </Link>
          </div>
        </div>
        {loadingGrowth ? (
          <Loading message="Loading growth stocks..." />
        ) : (
          <StockTable stocks={growth?.slice(0, 5) || []} />
        )}
      </section>
    </div>
  )
}
