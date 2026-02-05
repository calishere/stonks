import { ReactNode } from 'react'

interface MetricCardProps {
  label: string
  value: string | number | null | undefined
  suffix?: string
  prefix?: string
  change?: number
  icon?: ReactNode
  tooltip?: string
}

export default function MetricCard({
  label,
  value,
  suffix = '',
  prefix = '',
  change,
  icon,
  tooltip,
}: MetricCardProps) {
  const formattedValue = value !== null && value !== undefined ? value : 'N/A'

  return (
    <div className="metric-card" title={tooltip}>
      <div className="flex items-start justify-between">
        <div>
          <p className="metric-label">{label}</p>
          <p className="metric-value mt-1">
            {prefix}
            {formattedValue}
            {suffix}
          </p>
          {change !== undefined && (
            <p
              className={`text-sm mt-1 ${
                change >= 0 ? 'text-green-600' : 'text-red-600'
              }`}
            >
              {change >= 0 ? '+' : ''}
              {change.toFixed(1)}%
            </p>
          )}
        </div>
        {icon && <div className="text-gray-400">{icon}</div>}
      </div>
    </div>
  )
}

export function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined) return 'N/A'
  if (Math.abs(value) >= 1e12) return `${(value / 1e12).toFixed(2)}T`
  if (Math.abs(value) >= 1e9) return `${(value / 1e9).toFixed(2)}B`
  if (Math.abs(value) >= 1e6) return `${(value / 1e6).toFixed(2)}M`
  if (Math.abs(value) >= 1e3) return `${(value / 1e3).toFixed(2)}K`
  return value.toFixed(2)
}

export function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) return 'N/A'
  return `${value.toFixed(1)}%`
}

export function formatCurrency(value: number | null | undefined): string {
  if (value === null || value === undefined) return 'N/A'
  return `$${formatNumber(value)}`
}
