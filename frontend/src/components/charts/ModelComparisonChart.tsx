import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
} from 'recharts'

interface ModelData {
  model: string
  pass_rate: number
  avg_latency_ms: number
  avg_cost_usd: number
  total_evaluations: number
  [key: string]: string | number
}

interface ModelComparisonChartProps {
  data: ModelData[]
  metric?: 'pass_rate' | 'avg_latency_ms' | 'avg_cost_usd'
  title?: string
}

const COLORS = [
  '#6366f1', // indigo
  '#10b981', // emerald
  '#f59e0b', // amber
  '#ef4444', // red
  '#8b5cf6', // violet
  '#ec4899', // pink
]

const METRIC_LABELS: Record<string, { label: string; format: (v: number) => string }> = {
  pass_rate: { label: 'Pass Rate', format: (v) => `${v}%` },
  avg_latency_ms: { label: 'Avg Latency', format: (v) => `${v}ms` },
  avg_cost_usd: { label: 'Avg Cost', format: (v) => `$${v.toFixed(4)}` },
}

function truncateModelName(name: string): string {
  // Truncate long model names for display
  if (name.length > 20) {
    return name.substring(0, 17) + '...'
  }
  return name
}

export default function ModelComparisonChart({
  data,
  metric = 'pass_rate',
  title = 'Model Comparison',
}: ModelComparisonChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">{title}</h3>
        <div className="h-64 flex items-center justify-center text-gray-500">
          No model comparison data available yet.
        </div>
      </div>
    )
  }

  const metricConfig = METRIC_LABELS[metric]
  const maxValue = metric === 'pass_rate' ? 100 : Math.max(...data.map((d) => d[metric] as number)) * 1.1

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">{title}</h3>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 50 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis
              dataKey="model"
              tick={{ fontSize: 11 }}
              tickFormatter={truncateModelName}
              angle={-35}
              textAnchor="end"
              height={60}
            />
            <YAxis
              domain={[0, maxValue]}
              tick={{ fontSize: 12 }}
              tickFormatter={metricConfig.format}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#fff',
                border: '1px solid #e5e7eb',
                borderRadius: '8px',
                fontSize: '12px',
              }}
              formatter={(value: number) => [metricConfig.format(value), metricConfig.label]}
              labelFormatter={(label) => `Model: ${label}`}
            />
            <Legend wrapperStyle={{ fontSize: '12px' }} />
            <Bar
              dataKey={metric}
              name={metricConfig.label}
              radius={[4, 4, 0, 0]}
            >
              {data.map((_, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
