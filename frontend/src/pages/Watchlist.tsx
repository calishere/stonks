import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Star, Trash2, Plus } from 'lucide-react'
import { watchlistApi } from '../services/api'
import { formatCurrency } from '../components/MetricCard'
import Loading from '../components/Loading'
import { useState } from 'react'

export default function Watchlist() {
  const queryClient = useQueryClient()
  const [newTicker, setNewTicker] = useState('')

  const { data: watchlist, isLoading } = useQuery({
    queryKey: ['watchlist'],
    queryFn: watchlistApi.get,
  })

  const addMutation = useMutation({
    mutationFn: (ticker: string) => watchlistApi.add(ticker),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['watchlist'] })
      setNewTicker('')
    },
  })

  const removeMutation = useMutation({
    mutationFn: (ticker: string) => watchlistApi.remove(ticker),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['watchlist'] })
    },
  })

  const handleAdd = (e: React.FormEvent) => {
    e.preventDefault()
    if (newTicker.trim()) {
      addMutation.mutate(newTicker.trim().toUpperCase())
    }
  }

  if (isLoading) {
    return <Loading message="Loading watchlist..." />
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
          <Star className="h-8 w-8 text-yellow-500" />
          Watchlist
        </h1>
        <p className="mt-1 text-gray-600">
          Track stocks you're interested in
        </p>
      </div>

      {/* Add Stock Form */}
      <form onSubmit={handleAdd} className="card p-4">
        <div className="flex gap-2">
          <input
            type="text"
            className="input flex-1"
            placeholder="Enter ticker symbol (e.g., AAPL)"
            value={newTicker}
            onChange={(e) => setNewTicker(e.target.value.toUpperCase())}
          />
          <button
            type="submit"
            disabled={addMutation.isPending}
            className="btn btn-primary flex items-center gap-2"
          >
            <Plus className="h-4 w-4" />
            Add
          </button>
        </div>
        {addMutation.isError && (
          <p className="text-red-500 text-sm mt-2">
            Failed to add stock. Make sure the ticker is valid.
          </p>
        )}
      </form>

      {/* Watchlist Table */}
      <div className="card">
        {watchlist?.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            <Star className="h-12 w-12 mx-auto mb-4 text-gray-300" />
            <p>Your watchlist is empty</p>
            <p className="text-sm mt-1">Add stocks to track them here</p>
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
                    Price
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                    Market Cap
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Sector
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Added
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {watchlist?.map((item) => (
                  <tr key={item.id} className="hover:bg-gray-50">
                    <td className="px-4 py-4 whitespace-nowrap">
                      <Link
                        to={`/stock/${item.ticker}`}
                        className="flex flex-col"
                      >
                        <span className="font-medium text-primary-600 hover:text-primary-800">
                          {item.ticker}
                        </span>
                        <span className="text-sm text-gray-500 truncate max-w-[200px]">
                          {item.name}
                        </span>
                      </Link>
                    </td>
                    <td className="px-4 py-4 whitespace-nowrap text-right">
                      {formatCurrency(item.current_price)}
                    </td>
                    <td className="px-4 py-4 whitespace-nowrap text-right">
                      {formatCurrency(item.market_cap)}
                    </td>
                    <td className="px-4 py-4 whitespace-nowrap text-gray-500">
                      {item.sector || '-'}
                    </td>
                    <td className="px-4 py-4 whitespace-nowrap text-gray-500 text-sm">
                      {new Date(item.added_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-4 whitespace-nowrap text-center">
                      <button
                        onClick={() => removeMutation.mutate(item.ticker)}
                        disabled={removeMutation.isPending}
                        className="text-red-500 hover:text-red-700 p-2"
                        title="Remove from watchlist"
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
