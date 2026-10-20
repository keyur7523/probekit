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
import { COLORS, GRID, chartMotion, tooltipStyle } from './theme'
import { LOCAL_COST_LABEL } from '../../utils/cost'

interface ModelData {
  model: string
  pass_rate: number
  avg_latency_ms: number
  avg_cost_usd: number
  is_local?: boolean
  total_evaluations: number
  [key: string]: string | number | boolean | undefined
}

interface ModelComparisonChartProps {
  data: ModelData[]
  metric?: 'pass_rate' | 'avg_latency_ms' | 'avg_cost_usd'
  title?: string
}

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
            <CartesianGrid strokeDasharray="3 3" stroke={GRID} />
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
              contentStyle={tooltipStyle}
              formatter={(value: number, _name, item) => [
                metric === 'avg_cost_usd' && item.payload.is_local ? LOCAL_COST_LABEL : metricConfig.format(value),
                metricConfig.label,
              ]}
              labelFormatter={(label) => `Model: ${label}`}
            />
            <Legend wrapperStyle={{ fontSize: '12px' }} />
            <Bar {...chartMotion}
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
