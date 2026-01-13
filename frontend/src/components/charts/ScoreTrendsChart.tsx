import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'

interface TrendData {
  date: string
  [key: string]: string | number
}

interface ScoreTrendsChartProps {
  data: TrendData[]
  title?: string
}

const COLORS = [
  '#6366f1', // indigo
  '#10b981', // emerald
  '#f59e0b', // amber
  '#ef4444', // red
  '#8b5cf6', // violet
]

const EVALUATOR_NAMES: Record<string, string> = {
  instruction_adherence: 'Instruction',
  hallucination: 'Hallucination',
  format_consistency: 'Format',
  refusal_behavior: 'Refusal',
  output_stability: 'Stability',
}

export default function ScoreTrendsChart({ data, title = 'Evaluation Score Trends' }: ScoreTrendsChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">{title}</h3>
        <div className="h-64 flex items-center justify-center text-gray-500">
          No trend data available yet. Run some evaluations to see trends.
        </div>
      </div>
    )
  }

  // Extract unique metric keys (ending in _pass_rate)
  const metricKeys = Object.keys(data[0] || {}).filter(
    (key) => key.endsWith('_pass_rate') && key !== 'date'
  )

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">{title}</h3>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 12 }}
              tickFormatter={(value) => {
                const date = new Date(value)
                return `${date.getMonth() + 1}/${date.getDate()}`
              }}
            />
            <YAxis
              domain={[0, 100]}
              tick={{ fontSize: 12 }}
              tickFormatter={(value) => `${value}%`}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#fff',
                border: '1px solid #e5e7eb',
                borderRadius: '8px',
                fontSize: '12px',
              }}
              formatter={(value: number) => [`${value}%`, '']}
              labelFormatter={(label) => new Date(label).toLocaleDateString()}
            />
            <Legend
              wrapperStyle={{ fontSize: '12px' }}
              formatter={(value) => {
                const evalName = value.replace('_pass_rate', '')
                return EVALUATOR_NAMES[evalName] || evalName
              }}
            />
            {metricKeys.map((key, index) => (
              <Line
                key={key}
                type="monotone"
                dataKey={key}
                name={key}
                stroke={COLORS[index % COLORS.length]}
                strokeWidth={2}
                dot={{ r: 3 }}
                activeDot={{ r: 5 }}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
