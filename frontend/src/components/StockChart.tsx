import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'
import type { HistoricalDataPoint } from '../types'

interface StockChartProps {
  data: HistoricalDataPoint[]
  metricName: string
  periodType: 'quarterly' | 'annual'
  chartType?: 'line' | 'bar'
  color?: string
}

export default function StockChart({
  data,
  metricName,
  periodType,
  chartType = 'line',
  color = '#0ea5e9',
}: StockChartProps) {
  const formattedData = data.map((point) => ({
    ...point,
    label:
      periodType === 'quarterly'
        ? `Q${point.fiscal_quarter} ${point.fiscal_year}`
        : `${point.fiscal_year}`,
  }))

  const formatValue = (value: number) => {
    if (Math.abs(value) >= 1e9) return `${(value / 1e9).toFixed(1)}B`
    if (Math.abs(value) >= 1e6) return `${(value / 1e6).toFixed(1)}M`
    if (Math.abs(value) >= 1e3) return `${(value / 1e3).toFixed(1)}K`
    return value.toFixed(1)
  }

  const formatLabel = (name: string) => {
    return name
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ')
  }

  if (data.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center text-gray-500">
        No data available
      </div>
    )
  }

  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        {chartType === 'line' ? (
          <LineChart data={formattedData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis
              dataKey="label"
              tick={{ fontSize: 12 }}
              tickLine={false}
              axisLine={{ stroke: '#e5e7eb' }}
            />
            <YAxis
              tickFormatter={formatValue}
              tick={{ fontSize: 12 }}
              tickLine={false}
              axisLine={{ stroke: '#e5e7eb' }}
            />
            <Tooltip
              formatter={(value: number) => [formatValue(value), formatLabel(metricName)]}
              labelStyle={{ color: '#374151' }}
              contentStyle={{
                backgroundColor: 'white',
                border: '1px solid #e5e7eb',
                borderRadius: '8px',
              }}
            />
            <Legend formatter={() => formatLabel(metricName)} />
            <Line
              type="monotone"
              dataKey="value"
              stroke={color}
              strokeWidth={2}
              dot={{ fill: color, strokeWidth: 2 }}
              activeDot={{ r: 6 }}
            />
          </LineChart>
        ) : (
          <BarChart data={formattedData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis
              dataKey="label"
              tick={{ fontSize: 12 }}
              tickLine={false}
              axisLine={{ stroke: '#e5e7eb' }}
            />
            <YAxis
              tickFormatter={formatValue}
              tick={{ fontSize: 12 }}
              tickLine={false}
              axisLine={{ stroke: '#e5e7eb' }}
            />
            <Tooltip
              formatter={(value: number) => [formatValue(value), formatLabel(metricName)]}
              labelStyle={{ color: '#374151' }}
              contentStyle={{
                backgroundColor: 'white',
                border: '1px solid #e5e7eb',
                borderRadius: '8px',
              }}
            />
            <Legend formatter={() => formatLabel(metricName)} />
            <Bar dataKey="value" fill={color} radius={[4, 4, 0, 0]} />
          </BarChart>
        )}
      </ResponsiveContainer>
    </div>
  )
}
