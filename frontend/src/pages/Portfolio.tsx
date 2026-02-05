import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Briefcase, Plus, Trash2, TrendingUp, TrendingDown } from 'lucide-react'
import { portfolioApi } from '../services/api'
import { formatCurrency, formatPercent } from '../components/MetricCard'
import Loading from '../components/Loading'

export default function Portfolio() {
  const queryClient = useQueryClient()
  const [showAddForm, setShowAddForm] = useState(false)
  const [newPosition, setNewPosition] = useState({
    ticker: '',
    shares: '',
    averageCost: '',
  })

  const { data: portfolio, isLoading } = useQuery({
    queryKey: ['portfolio'],
    queryFn: portfolioApi.get,
  })

  const addMutation = useMutation({
    mutationFn: () =>
      portfolioApi.add(
        newPosition.ticker.toUpperCase(),
        parseFloat(newPosition.shares),
        parseFloat(newPosition.averageCost)
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portfolio'] })
      setNewPosition({ ticker: '', shares: '', averageCost: '' })
      setShowAddForm(false)
    },
  })

  const removeMutation = useMutation({
    mutationFn: (ticker: string) => portfolioApi.remove(ticker),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portfolio'] })
    },
  })

  const handleAdd = (e: React.FormEvent) => {
    e.preventDefault()
    addMutation.mutate()
  }

  if (isLoading) {
    return <Loading message="Loading portfolio..." />
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
            <Briefcase className="h-8 w-8 text-primary-600" />
            Portfolio
          </h1>
          <p className="mt-1 text-gray-600">Track your investments</p>
        </div>
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className="btn btn-primary flex items-center gap-2"
        >
          <Plus className="h-4 w-4" />
          Add Position
        </button>
      </div>

      {/* Portfolio Summary */}
      {portfolio && portfolio.positions.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="metric-card">
            <p className="metric-label">Total Cost</p>
            <p className="metric-value">{formatCurrency(portfolio.total_cost)}</p>
          </div>
          <div className="metric-card">
            <p className="metric-label">Current Value</p>
            <p className="metric-value">{formatCurrency(portfolio.total_value)}</p>
          </div>
          <div className="metric-card">
            <p className="metric-label">Total Gain/Loss</p>
            <p
              className={`metric-value ${
                portfolio.total_gain_loss >= 0 ? 'text-green-600' : 'text-red-600'
              }`}
            >
              {portfolio.total_gain_loss >= 0 ? '+' : ''}
              {formatCurrency(portfolio.total_gain_loss)}
            </p>
          </div>
          <div className="metric-card">
            <p className="metric-label">Total Return</p>
            <p
              className={`metric-value flex items-center gap-1 ${
                portfolio.total_gain_loss_percent >= 0 ? 'text-green-600' : 'text-red-600'
              }`}
            >
              {portfolio.total_gain_loss_percent >= 0 ? (
                <TrendingUp className="h-5 w-5" />
              ) : (
                <TrendingDown className="h-5 w-5" />
              )}
              {portfolio.total_gain_loss_percent >= 0 ? '+' : ''}
              {formatPercent(portfolio.total_gain_loss_percent)}
            </p>
          </div>
        </div>
      )}

      {/* Add Position Form */}
      {showAddForm && (
        <form onSubmit={handleAdd} className="card p-6">
          <h2 className="font-semibold text-gray-900 mb-4">Add Position</h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Ticker
              </label>
              <input
                type="text"
                className="input"
                placeholder="e.g., AAPL"
                value={newPosition.ticker}
                onChange={(e) =>
                  setNewPosition((prev) => ({
                    ...prev,
                    ticker: e.target.value.toUpperCase(),
                  }))
                }
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Shares
              </label>
              <input
                type="number"
                className="input"
                placeholder="e.g., 10"
                step="0.001"
                value={newPosition.shares}
                onChange={(e) =>
                  setNewPosition((prev) => ({ ...prev, shares: e.target.value }))
                }
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Average Cost
              </label>
              <input
                type="number"
                className="input"
                placeholder="e.g., 150.00"
                step="0.01"
                value={newPosition.averageCost}
                onChange={(e) =>
                  setNewPosition((prev) => ({
                    ...prev,
                    averageCost: e.target.value,
                  }))
                }
                required
              />
            </div>
            <div className="flex items-end gap-2">
              <button
                type="submit"
                disabled={addMutation.isPending}
                className="btn btn-primary"
              >
                Add
              </button>
              <button
                type="button"
                onClick={() => setShowAddForm(false)}
                className="btn btn-secondary"
              >
                Cancel
              </button>
            </div>
          </div>
          {addMutation.isError && (
            <p className="text-red-500 text-sm mt-2">
              Failed to add position. Make sure the ticker is valid.
            </p>
          )}
        </form>
      )}

      {/* Portfolio Table */}
      <div className="card">
        {portfolio?.positions.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            <Briefcase className="h-12 w-12 mx-auto mb-4 text-gray-300" />
            <p>Your portfolio is empty</p>
            <p className="text-sm mt-1">Add positions to track your investments</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Stock
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                    Shares
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                    Avg Cost
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                    Current Price
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                    Current Value
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                    Gain/Loss
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                    Return
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {portfolio?.positions.map((position) => (
                  <tr key={position.id} className="hover:bg-gray-50">
                    <td className="px-4 py-4 whitespace-nowrap">
                      <Link
                        to={`/stock/${position.ticker}`}
                        className="flex flex-col"
                      >
                        <span className="font-medium text-primary-600 hover:text-primary-800">
                          {position.ticker}
                        </span>
                        <span className="text-sm text-gray-500 truncate max-w-[150px]">
                          {position.name}
                        </span>
                      </Link>
                    </td>
                    <td className="px-4 py-4 whitespace-nowrap text-right">
                      {position.shares.toFixed(2)}
                    </td>
                    <td className="px-4 py-4 whitespace-nowrap text-right">
                      ${position.average_cost.toFixed(2)}
                    </td>
                    <td className="px-4 py-4 whitespace-nowrap text-right">
                      {formatCurrency(position.current_price)}
                    </td>
                    <td className="px-4 py-4 whitespace-nowrap text-right font-medium">
                      {formatCurrency(position.current_value)}
                    </td>
                    <td
                      className={`px-4 py-4 whitespace-nowrap text-right ${
                        (position.gain_loss ?? 0) >= 0
                          ? 'text-green-600'
                          : 'text-red-600'
                      }`}
                    >
                      {(position.gain_loss ?? 0) >= 0 ? '+' : ''}
                      {formatCurrency(position.gain_loss)}
                    </td>
                    <td
                      className={`px-4 py-4 whitespace-nowrap text-right ${
                        (position.gain_loss_percent ?? 0) >= 0
                          ? 'text-green-600'
                          : 'text-red-600'
                      }`}
                    >
                      {(position.gain_loss_percent ?? 0) >= 0 ? '+' : ''}
                      {formatPercent(position.gain_loss_percent)}
                    </td>
                    <td className="px-4 py-4 whitespace-nowrap text-center">
                      <button
                        onClick={() => removeMutation.mutate(position.ticker)}
                        disabled={removeMutation.isPending}
                        className="text-red-500 hover:text-red-700 p-2"
                        title="Remove position"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
