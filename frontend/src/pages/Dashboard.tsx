import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { dashboardApi } from '../api/client'
import {
  ScoreTrendsChart,
  ModelComparisonChart,
  EvaluatorBreakdownChart,
  AnnotationAccuracyChart,
} from '../components/charts'

function StatCard({
  title,
  value,
  subtitle,
  trend,
}: {
  title: string
  value: string | number
  subtitle?: string
  trend?: { value: number; positive: boolean }
}) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <p className="text-sm font-medium text-gray-500">{title}</p>
      <div className="mt-2 flex items-baseline gap-2">
        <p className="text-3xl font-semibold text-gray-900">{value}</p>
        {trend && (
          <span
            className={`text-sm font-medium ${
              trend.positive ? 'text-green-600' : 'text-red-600'
            }`}
          >
            {trend.positive ? '+' : ''}{trend.value}%
          </span>
        )}
      </div>
      {subtitle && <p className="mt-1 text-sm text-gray-500">{subtitle}</p>}
    </div>
  )
}

function StatusBadge({ passRate }: { passRate: number }) {
  const getColor = () => {
    if (passRate >= 80) return 'bg-green-100 text-green-800'
    if (passRate >= 60) return 'bg-yellow-100 text-yellow-800'
    return 'bg-red-100 text-red-800'
  }
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getColor()}`}>
      {passRate}% pass
    </span>
  )
}

export default function Dashboard() {
  const [modelMetric, setModelMetric] = useState<'pass_rate' | 'avg_latency_ms' | 'avg_cost_usd'>('pass_rate')
  const [trendDays, setTrendDays] = useState(30)

  const { data: metrics, isLoading: metricsLoading } = useQuery({
    queryKey: ['dashboard-metrics'],
    queryFn: () => dashboardApi.getMetrics(),
  })

  const { data: trends } = useQuery({
    queryKey: ['dashboard-trends', trendDays],
    queryFn: () => dashboardApi.getTrends(trendDays),
  })

  const { data: modelComparison } = useQuery({
    queryKey: ['dashboard-model-comparison'],
    queryFn: () => dashboardApi.getModelComparison(),
  })

  const { data: evaluatorBreakdown } = useQuery({
    queryKey: ['dashboard-evaluator-breakdown'],
    queryFn: () => dashboardApi.getEvaluatorBreakdown(),
  })

  const { data: recentActivity } = useQuery({
    queryKey: ['dashboard-recent-activity'],
    queryFn: () => dashboardApi.getRecentActivity(5),
  })

  const { data: versionComparisons } = useQuery({
    queryKey: ['dashboard-regressions'],
    queryFn: () => dashboardApi.getRegressions(),
  })

  const { data: annotationAccuracy } = useQuery({
    queryKey: ['dashboard-annotation-accuracy'],
    queryFn: () => dashboardApi.getAnnotationAccuracy(),
  })

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="mt-1 text-gray-500">Overview of your LLM evaluation runs</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6 mb-8">
        <StatCard
          title="Test Cases"
          value={metricsLoading ? '...' : metrics?.total_test_cases || 0}
        />
        <StatCard
          title="Evaluation Runs"
          value={metricsLoading ? '...' : metrics?.completed_runs || 0}
          subtitle={`${metrics?.total_runs || 0} total`}
        />
        <StatCard
          title="Overall Pass Rate"
          value={metricsLoading ? '...' : `${metrics?.overall_pass_rate || 0}%`}
          subtitle={`${metrics?.total_evaluator_results || 0} evaluations`}
        />
        <StatCard
          title="Latency"
          value={metricsLoading ? '...' : `${metrics?.latency_p50_ms?.toFixed(0) || 0}ms`}
          subtitle={`p50 • p99: ${metrics?.latency_p99_ms?.toFixed(0) || 0}ms`}
        />
        <StatCard
          title="Total Cost"
          value={metricsLoading ? '...' : `$${metrics?.total_cost_usd?.toFixed(4) || '0.0000'}`}
          subtitle={`Avg latency: ${metrics?.avg_latency_ms?.toFixed(0) || 0}ms`}
        />
      </div>

      {/* Charts Row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Score Trends */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-500">Time range</span>
            <select
              value={trendDays}
              onChange={(e) => setTrendDays(Number(e.target.value))}
              className="text-sm border border-gray-300 rounded-md px-2 py-1"
            >
              <option value={7}>Last 7 days</option>
              <option value={14}>Last 14 days</option>
              <option value={30}>Last 30 days</option>
              <option value={60}>Last 60 days</option>
            </select>
          </div>
          <ScoreTrendsChart data={trends?.data || []} />
        </div>

        {/* Evaluator Breakdown */}
        <EvaluatorBreakdownChart
          data={evaluatorBreakdown?.data || []}
          chartType="radar"
          title="Evaluator Performance"
        />
      </div>

      {/* Charts Row 2 */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-gray-500">Metric</span>
          <select
            value={modelMetric}
            onChange={(e) => setModelMetric(e.target.value as typeof modelMetric)}
            className="text-sm border border-gray-300 rounded-md px-2 py-1"
          >
            <option value="pass_rate">Pass Rate</option>
            <option value="avg_latency_ms">Latency</option>
            <option value="avg_cost_usd">Cost</option>
          </select>
        </div>
        <ModelComparisonChart
          data={modelComparison?.data || []}
          metric={modelMetric}
          title="Model Comparison"
        />
      </div>

      {/* Annotation Accuracy */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 mb-8">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Annotation Accuracy</h2>
            <p className="text-xs text-gray-500">Agreement between human labels and evaluator results.</p>
          </div>
        </div>
        <div className="divide-y divide-gray-200">
          {!annotationAccuracy?.data?.length ? (
            <div className="p-6 text-center text-gray-500">No annotation accuracy data yet. Add some labels.</div>
          ) : (
            <>
              <div className="p-6 border-b border-gray-200">
                <AnnotationAccuracyChart data={annotationAccuracy.data} title="Accuracy by Evaluator" />
              </div>
              {annotationAccuracy.data.map((entry) => (
                <div key={entry.evaluator_name} className="px-6 py-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-900">{entry.evaluator_name}</p>
                      <p className="text-xs text-gray-500">{entry.agreed}/{entry.total} agreed</p>
                    </div>
                    <span className={`text-xs px-2 py-1 rounded-full ${entry.accuracy >= 80 ? 'bg-green-100 text-green-800' : entry.accuracy >= 60 ? 'bg-yellow-100 text-yellow-800' : 'bg-red-100 text-red-800'}`}>
                      {entry.accuracy}% accuracy
                    </span>
                  </div>
                  <div className="mt-2 text-xs text-gray-500">
                    Human: {entry.human_true} pass / {entry.human_false} fail • Auto: {entry.auto_true} pass / {entry.auto_false} fail
                  </div>
                </div>
              ))}
            </>
          )}
        </div>
      </div>

      {/* Latest Regressions */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 mb-8">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">Latest Regressions</h2>
          <Link to="/version-comparison" className="text-sm font-medium text-indigo-600 hover:text-indigo-700">
            Compare versions
          </Link>
        </div>
        <div className="divide-y divide-gray-200">
          {!versionComparisons?.comparisons?.length ? (
            <div className="p-6 text-center text-gray-500">No regression data available yet.</div>
          ) : (
            versionComparisons.comparisons.slice(0, 3).map((comparison) => (
              <div key={comparison.prompt_version} className="px-6 py-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-900">{comparison.prompt_version}</p>
                    {comparison.previous_run ? (
                      <p className="text-xs text-gray-500">
                        {new Date(comparison.previous_run.timestamp).toLocaleDateString()} → {new Date(comparison.current_run.timestamp).toLocaleDateString()}
                      </p>
                    ) : (
                      <p className="text-xs text-gray-500">{comparison.note || 'Not enough runs to compare'}</p>
                    )}
                  </div>
                  <span className={`text-xs px-2 py-1 rounded-full ${comparison.has_regression ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'}`}>
                    {comparison.has_regression ? 'Regression detected' : 'No regression'}
                  </span>
                </div>
                {comparison.has_regression && comparison.regressions?.length ? (
                  <div className="mt-2 text-xs text-red-700">
                    {comparison.regressions.filter((item) => item.regressed).map((item) => item.evaluator_name).join(', ')}
                  </div>
                ) : null}
              </div>
            ))
          )}
        </div>
      </div>

      {/* Recent Activity */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">Recent Evaluations</h2>
          <Link
            to="/evaluations"
            className="text-sm font-medium text-indigo-600 hover:text-indigo-700"
          >
            View all
          </Link>
        </div>
        <div className="divide-y divide-gray-200">
          {!recentActivity?.activity?.length ? (
            <div className="p-6 text-center text-gray-500">
              No evaluations yet.{' '}
              <Link to="/evaluations" className="text-indigo-600 hover:underline">
                Run your first evaluation
              </Link>
            </div>
          ) : (
            recentActivity.activity.map((run) => (
              <Link
                key={run.id}
                to={`/evaluations/${run.id}`}
                className="block px-6 py-4 hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-gray-900">{run.prompt_version}</p>
                    <p className="text-sm text-gray-500">
                      {run.test_case_count} test cases | {run.models.join(', ')}
                    </p>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <p className="text-sm font-medium text-gray-900">
                        ${run.cost_usd.toFixed(4)}
                      </p>
                      <p className="text-xs text-gray-500">
                        {(run.duration_ms / 1000).toFixed(2)}s
                      </p>
                    </div>
                    <StatusBadge passRate={run.pass_rate} />
                  </div>
                </div>
              </Link>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
