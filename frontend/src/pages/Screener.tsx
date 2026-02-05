import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Filter, X, ChevronDown, ChevronUp } from 'lucide-react'
import { screenerApi } from '../services/api'
import type { ScreenerFilters } from '../types'
import StockTable from '../components/StockTable'
import Loading from '../components/Loading'

const DEFAULT_FILTERS: ScreenerFilters = {
  sort_by: 'market_cap',
  sort_order: 'desc',
  page: 1,
  per_page: 50,
}

export default function Screener() {
  const [searchParams] = useSearchParams()
  const preset = searchParams.get('preset')
  const [showFilters, setShowFilters] = useState(true)
  const [filters, setFilters] = useState<ScreenerFilters>(DEFAULT_FILTERS)

  // Load preset filters
  useEffect(() => {
    if (preset === 'undervalued') {
      setFilters({
        ...DEFAULT_FILTERS,
        valuation_status: 'undervalued',
        positive_fcf_only: true,
        sort_by: 'margin_of_safety',
      })
    } else if (preset === 'quality') {
      setFilters({
        ...DEFAULT_FILTERS,
        min_roe: 15,
        min_roce: 12,
        min_net_margin: 10,
        positive_fcf_only: true,
        max_debt_to_equity: 1,
        sort_by: 'roe',
      })
    } else if (preset === 'growth') {
      setFilters({
        ...DEFAULT_FILTERS,
        min_revenue_growth: 15,
        min_eps_growth: 10,
        positive_fcf_only: true,
        sort_by: 'revenue_growth',
      })
    }
  }, [preset])

  const { data: sectors } = useQuery({
    queryKey: ['sectors'],
    queryFn: screenerApi.getSectors,
  })

  const { data: results, isLoading } = useQuery({
    queryKey: ['screener', filters],
    queryFn: () => screenerApi.screen(filters),
  })

  const updateFilter = (key: keyof ScreenerFilters, value: unknown) => {
    setFilters((prev) => ({ ...prev, [key]: value, page: 1 }))
  }

  const clearFilters = () => {
    setFilters(DEFAULT_FILTERS)
  }

  const hasActiveFilters = Object.keys(filters).some(
    (key) =>
      filters[key as keyof ScreenerFilters] !==
      DEFAULT_FILTERS[key as keyof ScreenerFilters]
  )

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Stock Screener</h1>
          <p className="mt-1 text-gray-600">
            Filter stocks by fundamental metrics
          </p>
        </div>
        <button
          onClick={() => setShowFilters(!showFilters)}
          className="btn btn-secondary flex items-center gap-2"
        >
          <Filter className="h-4 w-4" />
          Filters
          {showFilters ? (
            <ChevronUp className="h-4 w-4" />
          ) : (
            <ChevronDown className="h-4 w-4" />
          )}
        </button>
      </div>

      {/* Filters */}
      {showFilters && (
        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-gray-900">Filters</h2>
            {hasActiveFilters && (
              <button
                onClick={clearFilters}
                className="text-sm text-primary-600 hover:text-primary-800 flex items-center gap-1"
              >
                <X className="h-4 w-4" />
                Clear All
              </button>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Sector */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Sector
              </label>
              <select
                className="input"
                value={filters.sectors?.[0] || ''}
                onChange={(e) =>
                  updateFilter('sectors', e.target.value ? [e.target.value] : undefined)
                }
              >
                <option value="">All Sectors</option>
                {sectors?.map((sector) => (
                  <option key={sector} value={sector}>
                    {sector}
                  </option>
                ))}
              </select>
            </div>

            {/* Market Cap */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Min Market Cap (B)
              </label>
              <input
                type="number"
                className="input"
                placeholder="e.g., 10"
                value={filters.min_market_cap || ''}
                onChange={(e) =>
                  updateFilter(
                    'min_market_cap',
                    e.target.value ? parseFloat(e.target.value) : undefined
                  )
                }
              />
            </div>

            {/* ROE */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Min ROE (%)
              </label>
              <input
                type="number"
                className="input"
                placeholder="e.g., 15"
                value={filters.min_roe || ''}
                onChange={(e) =>
                  updateFilter(
                    'min_roe',
                    e.target.value ? parseFloat(e.target.value) : undefined
                  )
                }
              />
            </div>

            {/* ROCE */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Min ROCE (%)
              </label>
              <input
                type="number"
                className="input"
                placeholder="e.g., 12"
                value={filters.min_roce || ''}
                onChange={(e) =>
                  updateFilter(
                    'min_roce',
                    e.target.value ? parseFloat(e.target.value) : undefined
                  )
                }
              />
            </div>

            {/* Net Margin */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Min Net Margin (%)
              </label>
              <input
                type="number"
                className="input"
                placeholder="e.g., 10"
                value={filters.min_net_margin || ''}
                onChange={(e) =>
                  updateFilter(
                    'min_net_margin',
                    e.target.value ? parseFloat(e.target.value) : undefined
                  )
                }
              />
            </div>

            {/* FCF Yield */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Min FCF Yield (%)
              </label>
              <input
                type="number"
                className="input"
                placeholder="e.g., 5"
                value={filters.min_fcf_yield || ''}
                onChange={(e) =>
                  updateFilter(
                    'min_fcf_yield',
                    e.target.value ? parseFloat(e.target.value) : undefined
                  )
                }
              />
            </div>

            {/* Max P/E */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Max P/E Ratio
              </label>
              <input
                type="number"
                className="input"
                placeholder="e.g., 25"
                value={filters.max_pe_ratio || ''}
                onChange={(e) =>
                  updateFilter(
                    'max_pe_ratio',
                    e.target.value ? parseFloat(e.target.value) : undefined
                  )
                }
              />
            </div>

            {/* Max Debt/Equity */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Max Debt/Equity
              </label>
              <input
                type="number"
                className="input"
                placeholder="e.g., 1"
                step="0.1"
                value={filters.max_debt_to_equity || ''}
                onChange={(e) =>
                  updateFilter(
                    'max_debt_to_equity',
                    e.target.value ? parseFloat(e.target.value) : undefined
                  )
                }
              />
            </div>

            {/* Revenue Growth */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Min Revenue Growth (%)
              </label>
              <input
                type="number"
                className="input"
                placeholder="e.g., 10"
                value={filters.min_revenue_growth || ''}
                onChange={(e) =>
                  updateFilter(
                    'min_revenue_growth',
                    e.target.value ? parseFloat(e.target.value) : undefined
                  )
                }
              />
            </div>

            {/* Valuation Status */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Valuation Status
              </label>
              <select
                className="input"
                value={filters.valuation_status || ''}
                onChange={(e) =>
                  updateFilter('valuation_status', e.target.value || undefined)
                }
              >
                <option value="">Any</option>
                <option value="undervalued">Undervalued</option>
                <option value="fair">Fair Value</option>
                <option value="overvalued">Overvalued</option>
              </select>
            </div>

            {/* Positive FCF */}
            <div className="flex items-center">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  checked={filters.positive_fcf_only || false}
                  onChange={(e) =>
                    updateFilter('positive_fcf_only', e.target.checked || undefined)
                  }
                />
                <span className="text-sm text-gray-700">Positive FCF Only</span>
              </label>
            </div>

            {/* Sort By */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Sort By
              </label>
              <select
                className="input"
                value={filters.sort_by}
                onChange={(e) => updateFilter('sort_by', e.target.value)}
              >
                <option value="market_cap">Market Cap</option>
                <option value="roe">ROE</option>
                <option value="roce">ROCE</option>
                <option value="net_profit_margin">Net Margin</option>
                <option value="fcf_yield">FCF Yield</option>
                <option value="revenue_growth">Revenue Growth</option>
                <option value="margin_of_safety">Margin of Safety</option>
                <option value="pe_ratio">P/E Ratio</option>
              </select>
            </div>
          </div>
        </div>
      )}

      {/* Results */}
      <div className="card">
        <div className="p-4 border-b border-gray-200 flex items-center justify-between">
          <span className="text-gray-600">
            {results?.total || 0} stocks found
          </span>
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-500">Per page:</span>
            <select
              className="input w-20"
              value={filters.per_page}
              onChange={(e) => updateFilter('per_page', parseInt(e.target.value))}
            >
              <option value={25}>25</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
            </select>
          </div>
        </div>

        {isLoading ? (
          <Loading message="Screening stocks..." />
        ) : (
          <StockTable stocks={results?.results || []} />
        )}

        {/* Pagination */}
        {results && results.total > (filters.per_page || 50) && (
          <div className="p-4 border-t border-gray-200 flex items-center justify-center gap-2">
            <button
              disabled={filters.page === 1}
              onClick={() => updateFilter('page', (filters.page || 1) - 1)}
              className="btn btn-secondary disabled:opacity-50"
            >
              Previous
            </button>
            <span className="text-gray-600">
              Page {filters.page} of {Math.ceil(results.total / (filters.per_page || 50))}
            </span>
            <button
              disabled={
                (filters.page || 1) >= Math.ceil(results.total / (filters.per_page || 50))
              }
              onClick={() => updateFilter('page', (filters.page || 1) + 1)}
              className="btn btn-secondary disabled:opacity-50"
            >
              Next
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
