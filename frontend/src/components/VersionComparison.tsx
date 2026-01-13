import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { dashboardApi, type Regression, type ComparisonResponse } from '../api/client'

function DeltaIndicator({ delta, suffix = '%', inverse = false }: { delta: number; suffix?: string; inverse?: boolean }) {
  const isPositive = inverse ? delta < 0 : delta > 0
  const isNegative = inverse ? delta > 0 : delta < 0

  if (delta === 0) {
    return <span className="text-gray-500">-</span>
  }

  return (
    <span className={`inline-flex items-center font-medium ${isPositive ? 'text-green-600' : isNegative ? 'text-red-600' : 'text-gray-600'}`}>
      {delta > 0 ? '+' : ''}{delta}{suffix}
      {isPositive && (
        <svg className="w-4 h-4 ml-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
        </svg>
      )}
      {isNegative && (
        <svg className="w-4 h-4 ml-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
        </svg>
      )}
    </span>
  )
}

function RegressionBadge({ severity }: { severity: 'high' | 'medium' }) {
  const styles = severity === 'high'
    ? 'bg-red-100 text-red-800 border-red-200'
    : 'bg-yellow-100 text-yellow-800 border-yellow-200'

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${styles}`}>
      {severity === 'high' ? 'High' : 'Medium'} Risk
    </span>
  )
}

function RegressionWarnings({ regressions }: { regressions: Regression[] }) {
  if (regressions.length === 0) return null

  return (
    <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-6">
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0">
          <svg className="w-5 h-5 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        </div>
        <div className="flex-1">
          <h3 className="text-sm font-semibold text-red-800 mb-2">
            {regressions.length} Regression{regressions.length > 1 ? 's' : ''} Detected
          </h3>
          <ul className="space-y-2">
            {regressions.map((regression, index) => (
              <li key={index} className="flex items-center justify-between text-sm">
                <span className="text-red-700">{regression.message}</span>
                <RegressionBadge severity={regression.severity} />
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  )
}

function ComparisonTable({ comparison }: { comparison: ComparisonResponse }) {
  if (!comparison.baseline || !comparison.current || !comparison.comparison) {
    return null
  }

  const { baseline, current, comparison: comp } = comparison

  // Get all evaluators
  const allEvaluators = Object.keys(comp.evaluators)

  // Get all models
  const allModels = Object.keys(comp.models)

  return (
    <div className="space-y-6">
      {/* Overall Stats */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
          <h3 className="text-lg font-semibold text-gray-900">Overall Comparison</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Metric</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                  {baseline.version} (Baseline)
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                  {current.version} (Current)
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Change</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              <tr>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">Pass Rate</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 text-right">{baseline.stats.pass_rate}%</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 text-right">{current.stats.pass_rate}%</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-right">
                  <DeltaIndicator delta={comp.overall.pass_rate_delta} />
                </td>
              </tr>
              <tr>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">Total Cost</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 text-right">${baseline.stats.cost_usd.toFixed(4)}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 text-right">${current.stats.cost_usd.toFixed(4)}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-right">
                  <DeltaIndicator delta={comp.overall.cost_delta} suffix="" inverse />
                </td>
              </tr>
              <tr>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">Duration</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 text-right">{(baseline.stats.duration_ms / 1000).toFixed(2)}s</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 text-right">{(current.stats.duration_ms / 1000).toFixed(2)}s</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-right">
                  <DeltaIndicator delta={Math.round(comp.overall.duration_delta / 1000 * 100) / 100} suffix="s" inverse />
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Evaluator Breakdown */}
      {allEvaluators.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
            <h3 className="text-lg font-semibold text-gray-900">By Evaluator</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Evaluator</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Baseline</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Current</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Change</th>
                  <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase">Status</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {allEvaluators.map((evaluator) => {
                  const data = comp.evaluators[evaluator]
                  return (
                    <tr
                      key={evaluator}
                      className={data.regression ? 'bg-red-50 border-l-4 border-red-400' : ''}
                    >
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {evaluator.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 text-right">{data.baseline}%</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 text-right">{data.current}%</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-right">
                        <DeltaIndicator delta={data.delta} />
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-center">
                        {data.regression ? (
                          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800">
                            Regression
                          </span>
                        ) : data.delta > 0 ? (
                          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                            Improved
                          </span>
                        ) : (
                          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800">
                            Stable
                          </span>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Model Breakdown */}
      {allModels.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
            <h3 className="text-lg font-semibold text-gray-900">By Model</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Model</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Pass Rate</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Latency</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Cost</th>
                  <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase">Status</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {allModels.map((model) => {
                  const data = comp.models[model]
                  return (
                    <tr
                      key={model}
                      className={data.regression ? 'bg-red-50 border-l-4 border-red-400' : ''}
                    >
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{model}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-right">
                        <div className="flex items-center justify-end gap-2">
                          <span className="text-gray-600">{data.current.pass_rate}%</span>
                          <DeltaIndicator delta={data.deltas.pass_rate} />
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-right">
                        <div className="flex items-center justify-end gap-2">
                          <span className="text-gray-600">{data.current.avg_latency_ms}ms</span>
                          <DeltaIndicator delta={data.deltas.avg_latency_ms} suffix="ms" inverse />
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-right">
                        <div className="flex items-center justify-end gap-2">
                          <span className="text-gray-600">${data.current.avg_cost_usd.toFixed(6)}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-center">
                        {data.regression ? (
                          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800">
                            Regression
                          </span>
                        ) : data.deltas.pass_rate > 0 ? (
                          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                            Improved
                          </span>
                        ) : (
                          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800">
                            Stable
                          </span>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Run Links */}
      <div className="flex items-center justify-center gap-4 text-sm">
        <Link to={`/evaluations/${baseline.run_id}`} className="text-indigo-600 hover:text-indigo-800">
          View Baseline Run
        </Link>
        <span className="text-gray-300">|</span>
        <Link to={`/evaluations/${current.run_id}`} className="text-indigo-600 hover:text-indigo-800">
          View Current Run
        </Link>
      </div>
    </div>
  )
}

export default function VersionComparison() {
  const [baselineVersion, setBaselineVersion] = useState<string>('')
  const [currentVersion, setCurrentVersion] = useState<string>('')
  const [threshold, setThreshold] = useState(5)

  const { data: versionsData, isLoading: versionsLoading } = useQuery({
    queryKey: ['versions'],
    queryFn: () => dashboardApi.getVersions(),
  })

  const { data: comparison, isLoading: comparisonLoading, error } = useQuery({
    queryKey: ['compare', baselineVersion, currentVersion, threshold],
    queryFn: () => dashboardApi.compareVersions(baselineVersion, currentVersion, threshold),
    enabled: !!baselineVersion && !!currentVersion && baselineVersion !== currentVersion,
  })

  const versions = versionsData?.versions || []

  // Auto-select first two versions if available
  if (versions.length >= 2 && !baselineVersion && !currentVersion) {
    setBaselineVersion(versions[1].prompt_version)
    setCurrentVersion(versions[0].prompt_version)
  }

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Version Comparison</h1>
        <p className="mt-1 text-gray-500">Compare prompt versions and detect regressions</p>
      </div>

      {/* Version Selectors */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Baseline Version</label>
            <select
              value={baselineVersion}
              onChange={(e) => setBaselineVersion(e.target.value)}
              className="w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 border p-2"
              disabled={versionsLoading}
            >
              <option value="">Select baseline...</option>
              {versions.map((v) => (
                <option key={v.prompt_version} value={v.prompt_version}>
                  {v.prompt_version} ({v.pass_rate}% pass)
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Current Version</label>
            <select
              value={currentVersion}
              onChange={(e) => setCurrentVersion(e.target.value)}
              className="w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 border p-2"
              disabled={versionsLoading}
            >
              <option value="">Select current...</option>
              {versions.map((v) => (
                <option key={v.prompt_version} value={v.prompt_version}>
                  {v.prompt_version} ({v.pass_rate}% pass)
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Regression Threshold</label>
            <div className="flex items-center gap-2">
              <input
                type="range"
                min="1"
                max="20"
                value={threshold}
                onChange={(e) => setThreshold(Number(e.target.value))}
                className="flex-1"
              />
              <span className="text-sm font-medium text-gray-700 w-12">{threshold}%</span>
            </div>
            <p className="text-xs text-gray-500 mt-1">Flag drops greater than {threshold}%</p>
          </div>
        </div>
      </div>

      {/* Empty State */}
      {versions.length === 0 && !versionsLoading && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
          <p className="text-gray-500 mb-4">No completed evaluation runs found.</p>
          <Link to="/evaluations" className="text-indigo-600 hover:underline">
            Run your first evaluation
          </Link>
        </div>
      )}

      {/* Same Version Warning */}
      {baselineVersion && currentVersion && baselineVersion === currentVersion && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4 mb-6">
          <p className="text-yellow-800 text-sm">Please select two different versions to compare.</p>
        </div>
      )}

      {/* Loading State */}
      {comparisonLoading && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
          <p className="text-gray-500">Loading comparison...</p>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-6">
          <p className="text-red-800 text-sm">Error loading comparison. Please try again.</p>
        </div>
      )}

      {/* Comparison Error */}
      {comparison?.error && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4 mb-6">
          <p className="text-yellow-800 text-sm">{comparison.error}</p>
        </div>
      )}

      {/* Regression Warnings */}
      {comparison?.regressions && comparison.regressions.length > 0 && (
        <RegressionWarnings regressions={comparison.regressions} />
      )}

      {/* Success State - No Regressions */}
      {comparison && !comparison.error && comparison.regressions?.length === 0 && (
        <div className="bg-green-50 border border-green-200 rounded-xl p-4 mb-6">
          <div className="flex items-center gap-2">
            <svg className="w-5 h-5 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="text-green-800 text-sm font-medium">No regressions detected with current threshold ({threshold}%)</p>
          </div>
        </div>
      )}

      {/* Comparison Table */}
      {comparison && !comparison.error && (
        <ComparisonTable comparison={comparison} />
      )}
    </div>
  )
}
