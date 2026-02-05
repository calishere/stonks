interface ValuationBadgeProps {
  status: 'undervalued' | 'overvalued' | 'fair' | string | null
  marginOfSafety?: number | null
}

export default function ValuationBadge({ status, marginOfSafety }: ValuationBadgeProps) {
  if (!status) return null

  const badgeClass =
    status === 'undervalued'
      ? 'badge-green'
      : status === 'overvalued'
      ? 'badge-red'
      : 'badge-yellow'

  const label =
    status === 'undervalued'
      ? 'Undervalued'
      : status === 'overvalued'
      ? 'Overvalued'
      : 'Fair Value'

  return (
    <span className={badgeClass}>
      {label}
      {marginOfSafety !== undefined && marginOfSafety !== null && (
        <span className="ml-1">({marginOfSafety > 0 ? '+' : ''}{marginOfSafety.toFixed(0)}%)</span>
      )}
    </span>
  )
}
