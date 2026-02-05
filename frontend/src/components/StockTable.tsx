import { Link } from 'react-router-dom'
import type { ScreenerResult } from '../types'
import ValuationBadge from './ValuationBadge'
import { formatNumber, formatPercent, formatCurrency } from './MetricCard'

interface StockTableProps {
  stocks: ScreenerResult[]
  showValuation?: boolean
}

export default function StockTable({ stocks, showValuation = true }: StockTableProps) {
  if (stocks.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        No stocks found matching your criteria
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Stock
            </th>
            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
              Price
            </th>
            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
              Market Cap
            </th>
            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
              P/E
            </th>
            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
              ROE
            </th>
            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
              ROCE
            </th>
            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
              Net Margin
            </th>
            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
              FCF Yield
            </th>
            {showValuation && (
              <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                Valuation
              </th>
            )}
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {stocks.map((stock) => (
            <tr key={stock.id} className="hover:bg-gray-50">
              <td className="px-4 py-4 whitespace-nowrap">
                <Link to={`/stock/${stock.ticker}`} className="flex flex-col">
                  <span className="font-medium text-primary-600 hover:text-primary-800">
                    {stock.ticker}
                  </span>
                  <span className="text-sm text-gray-500 truncate max-w-[200px]">
                    {stock.name}
                  </span>
                </Link>
              </td>
              <td className="px-4 py-4 whitespace-nowrap text-right text-sm">
                {formatCurrency(stock.current_price)}
              </td>
              <td className="px-4 py-4 whitespace-nowrap text-right text-sm">
                {formatCurrency(stock.market_cap)}
              </td>
              <td className="px-4 py-4 whitespace-nowrap text-right text-sm">
                {stock.pe_ratio?.toFixed(1) ?? 'N/A'}
              </td>
              <td className="px-4 py-4 whitespace-nowrap text-right text-sm">
                {formatPercent(stock.roe)}
              </td>
              <td className="px-4 py-4 whitespace-nowrap text-right text-sm">
                {formatPercent(stock.roce)}
              </td>
              <td className="px-4 py-4 whitespace-nowrap text-right text-sm">
                {formatPercent(stock.net_profit_margin)}
              </td>
              <td className="px-4 py-4 whitespace-nowrap text-right text-sm">
                {formatPercent(stock.fcf_yield)}
              </td>
              {showValuation && (
                <td className="px-4 py-4 whitespace-nowrap text-center">
                  <ValuationBadge
                    status={stock.valuation_status}
                    marginOfSafety={stock.margin_of_safety}
                  />
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
