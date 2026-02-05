import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  ArrowLeft,
  Star,
  StarOff,
  RefreshCw,
  TrendingUp,
  DollarSign,
  PieChart,
  Activity,
} from 'lucide-react'
import { stocksApi, valuationApi, watchlistApi } from '../services/api'
import { useAuth } from '../context/AuthContext'
import MetricCard, { formatNumber, formatPercent, formatCurrency } from '../components/MetricCard'
import ValuationBadge from '../components/ValuationBadge'
import StockChart from '../components/StockChart'
import Loading from '../components/Loading'

const METRICS = [
  { key: 'revenue', label: 'Revenue', type: 'bar', color: '#0ea5e9' },
  { key: 'net_income', label: 'Net Income', type: 'bar', color: '#22c55e' },
  { key: 'free_cash_flow', label: 'Free Cash Flow', type: 'bar', color: '#8b5cf6' },
  { key: 'roe', label: 'ROE (%)', type: 'line', color: '#f59e0b' },
  { key: 'roce', label: 'ROCE (%)', type: 'line', color: '#ec4899' },
  { key: 'net_profit_margin', label: 'Net Margin (%)', type: 'line', color: '#14b8a6' },
]

export default function StockDetail() {
  const { ticker } = useParams<{ ticker: string }>()
  const { isAuthenticated } = useAuth()
  const [periodType, setPeriodType] = useState<'quarterly' | 'annual'>('quarterly')
  const [selectedMetric, setSelectedMetric] = useState(METRICS[0])

  const { data: stock, isLoading: loadingStock } = useQuery({
    queryKey: ['stock', ticker],
    queryFn: () => stocksApi.get(ticker!),
    enabled: !!ticker,
  })

  const { data: valuation, isLoading: loadingValuation } = useQuery({
    queryKey: ['valuation', ticker],
    queryFn: () => valuationApi.get(ticker!),
    enabled: !!ticker,
  })

  const { data: chartData, isLoading: loadingChart } = useQuery({
    queryKey: ['chart', ticker, selectedMetric.key, periodType],
    queryFn: () =>
      stocksApi.getMetricHistory(ticker!, selectedMetric.key, periodType, 20),
    enabled: !!ticker,
  })

  const { data: watchlist, refetch: refetchWatchlist } = useQuery({
    queryKey: ['watchlist'],
    queryFn: watchlistApi.get,
    enabled: isAuthenticated,
  })

  const isInWatchlist = watchlist?.some((item) => item.ticker === ticker?.toUpperCase())

  const handleWatchlistToggle = async () => {
    if (!ticker) return
    try {
      if (isInWatchlist) {
        await watchlistApi.remove(ticker)
      } else {
        await watchlistApi.add(ticker)
      }
      refetchWatchlist()
    } catch (error) {
      console.error('Failed to update watchlist:', error)
    }
  }

  if (loadingStock) {
    return <Loading message="Loading stock data..." />
  }

  if (!stock) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Stock not found</p>
        <Link to="/" className="text-primary-600 hover:underline mt-2 inline-block">
          Back to Dashboard
        </Link>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <Link
            to="/"
            className="inline-flex items-center text-gray-600 hover:text-gray-900 mb-2"
          >
            <ArrowLeft className="h-4 w-4 mr-1" />
            Back
          </Link>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold text-gray-900">{stock.ticker}</h1>
            <ValuationBadge
              status={stock.valuation_status}
              marginOfSafety={stock.margin_of_safety}
            />
          </div>
          <p className="text-gray-600">{stock.name}</p>
          <p className="text-sm text-gray-500">
            {stock.sector} • {stock.industry}
          </p>
        </div>

        <div className="flex items-center gap-3">
          {isAuthenticated && (
            <button
              onClick={handleWatchlistToggle}
              className={`btn ${isInWatchlist ? 'btn-secondary' : 'btn-primary'}`}
            >
              {isInWatchlist ? (
                <>
                  <StarOff className="h-4 w-4 mr-2" />
                  Remove from Watchlist
                </>
              ) : (
                <>
                  <Star className="h-4 w-4 mr-2" />
                  Add to Watchlist
                </>
              )}
            </button>
          )}
        </div>
      </div>

      {/* Price and Key Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        <MetricCard
          label="Current Price"
          value={formatCurrency(stock.current_price)}
          icon={<DollarSign className="h-5 w-5" />}
        />
        <MetricCard
          label="Market Cap"
          value={formatCurrency(stock.market_cap)}
          icon={<PieChart className="h-5 w-5" />}
        />
        <MetricCard
          label="P/E Ratio"
          value={stock.pe_ratio?.toFixed(1)}
        />
        <MetricCard
          label="P/B Ratio"
          value={stock.pb_ratio?.toFixed(1)}
        />
        <MetricCard
          label="Fair Value"
          value={formatCurrency(stock.fair_value_per_share)}
          icon={<TrendingUp className="h-5 w-5" />}
        />
        <MetricCard
          label="Margin of Safety"
          value={formatPercent(stock.margin_of_safety)}
        />
      </div>

      {/* Profitability Metrics */}
      <div className="card p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <Activity className="h-5 w-5 text-primary-600" />
          Profitability Metrics
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
          <MetricCard label="Gross Margin" value={formatPercent(stock.gross_margin)} />
          <MetricCard label="Operating Margin" value={formatPercent(stock.operating_margin)} />
          <MetricCard label="Net Margin" value={formatPercent(stock.net_profit_margin)} />
          <MetricCard label="ROE" value={formatPercent(stock.roe)} />
          <MetricCard label="ROCE" value={formatPercent(stock.roce)} />
          <MetricCard label="FCF Yield" value={formatPercent(stock.fcf_yield)} />
        </div>
      </div>

      {/* Growth Metrics */}
      <div className="card p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <TrendingUp className="h-5 w-5 text-green-600" />
          Growth Metrics
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <MetricCard
            label="Revenue Growth"
            value={formatPercent(stock.revenue_growth)}
            change={stock.revenue_growth ?? undefined}
          />
          <MetricCard
            label="EPS Growth"
            value={formatPercent(stock.eps_growth)}
            change={stock.eps_growth ?? undefined}
          />
          <MetricCard label="FCF Margin" value={formatPercent(stock.fcf_margin)} />
          <MetricCard label="Free Cash Flow" value={formatCurrency(stock.free_cash_flow)} />
        </div>
      </div>

      {/* Historical Charts */}
      <div className="card p-6">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
          <h2 className="text-lg font-semibold text-gray-900">Historical Trends</h2>
          <div className="flex items-center gap-4">
            <div className="flex gap-2">
              <button
                onClick={() => setPeriodType('quarterly')}
                className={`px-3 py-1 rounded-lg text-sm ${
                  periodType === 'quarterly'
                    ? 'bg-primary-100 text-primary-700'
                    : 'bg-gray-100 text-gray-600'
                }`}
              >
                Quarterly
              </button>
              <button
                onClick={() => setPeriodType('annual')}
                className={`px-3 py-1 rounded-lg text-sm ${
                  periodType === 'annual'
                    ? 'bg-primary-100 text-primary-700'
                    : 'bg-gray-100 text-gray-600'
                }`}
              >
                Annual
              </button>
            </div>
          </div>
        </div>

        {/* Metric Selection */}
        <div className="flex flex-wrap gap-2 mb-6">
          {METRICS.map((metric) => (
            <button
              key={metric.key}
              onClick={() => setSelectedMetric(metric)}
              className={`px-3 py-1 rounded-lg text-sm ${
                selectedMetric.key === metric.key
                  ? 'bg-primary-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {metric.label}
            </button>
          ))}
        </div>

        {/* Chart */}
        {loadingChart ? (
          <Loading message="Loading chart..." />
        ) : (
          <StockChart
            data={chartData?.data || []}
            metricName={selectedMetric.key}
            periodType={periodType}
            chartType={selectedMetric.type as 'line' | 'bar'}
            color={selectedMetric.color}
          />
        )}
      </div>

      {/* Valuation Analysis */}
      {valuation && (
        <div className="card p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">DCF Valuation Analysis</h2>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <MetricCard label="Latest FCF" value={formatCurrency(valuation.latest_fcf)} />
            <MetricCard
              label="Growth Rate"
              value={`${valuation.estimated_growth_rate.toFixed(1)}%`}
            />
            <MetricCard
              label="Discount Rate"
              value={`${valuation.discount_rate.toFixed(1)}%`}
            />
            <MetricCard
              label="Enterprise Value"
              value={formatCurrency(valuation.enterprise_value)}
            />
          </div>

          <div className="bg-gray-50 rounded-lg p-4">
            <p className="text-gray-700">{valuation.valuation_summary}</p>
          </div>

          {/* Alternative Valuations */}
          <div className="mt-6">
            <h3 className="text-sm font-medium text-gray-700 mb-3">
              Alternative Valuation Methods
            </h3>
            <div className="grid grid-cols-3 gap-4">
              <MetricCard
                label="P/E Based"
                value={formatCurrency(valuation.pe_based_value)}
              />
              <MetricCard
                label="P/B Based"
                value={formatCurrency(valuation.pb_based_value)}
              />
              <MetricCard
                label="P/S Based"
                value={formatCurrency(valuation.ps_based_value)}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
