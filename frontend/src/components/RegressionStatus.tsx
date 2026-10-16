export type ChangeStatus = 'regressed' | 'improved' | 'no_significant_change' | 'insufficient_data'

export const INSUFFICIENT_DATA_HINT =
  'Too few results to judge (each run needs at least 20 per evaluator for a two-proportion test).'

export function RegressionVerdict({
  hasRegression,
  hasInsufficientData,
}: {
  hasRegression: boolean
  hasInsufficientData?: boolean
}) {
  if (hasRegression) {
    return <span className="text-xs px-2 py-1 rounded-full bg-red-100 text-red-800">Regression detected</span>
  }
  if (hasInsufficientData) {
    return (
      <span className="text-xs px-2 py-1 rounded-full bg-gray-100 text-gray-700" title={INSUFFICIENT_DATA_HINT}>
        Insufficient data
      </span>
    )
  }
  return <span className="text-xs px-2 py-1 rounded-full bg-green-100 text-green-800">No significant regression</span>
}

export function formatChangeStatus(status: ChangeStatus, pValue: number | null): string {
  switch (status) {
    case 'regressed':
      return `significant drop (p=${pValue})`
    case 'improved':
      return `significant rise (p=${pValue})`
    case 'no_significant_change':
      return `not significant (p=${pValue})`
    case 'insufficient_data':
      return 'insufficient data'
  }
}

const pill = 'inline-flex items-center px-2 py-0.5 rounded text-xs font-medium'

export function ChangeStatusBadge({
  regression,
  status,
  pValue,
  baselineN,
  currentN,
}: {
  regression: boolean
  status: ChangeStatus
  pValue: number | null
  baselineN: number
  currentN: number
}) {
  if (regression) {
    return <span className={`${pill} bg-red-100 text-red-800`}>Regression (p={pValue})</span>
  }
  switch (status) {
    case 'insufficient_data':
      return (
        <span className={`${pill} bg-gray-100 text-gray-600`} title={INSUFFICIENT_DATA_HINT}>
          Insufficient data (n={baselineN}/{currentN})
        </span>
      )
    case 'improved':
      return <span className={`${pill} bg-green-100 text-green-800`}>Improved (p={pValue})</span>
    case 'regressed':
      // Significant, but smaller than the regression threshold
      return <span className={`${pill} bg-yellow-100 text-yellow-800`}>Small drop (p={pValue})</span>
    default:
      return <span className={`${pill} bg-gray-100 text-gray-800`}>No significant change</span>
  }
}
