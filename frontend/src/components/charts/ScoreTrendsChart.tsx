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
import { COLORS, GRID, chartMotion, tooltipStyle } from './theme'
import { parseDay } from '../../utils/date'

interface TrendData {
  date: string
  [key: string]: string | number
}

interface ScoreTrendsChartProps {
  data: TrendData[]
  title?: string
}

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
            <CartesianGrid strokeDasharray="3 3" stroke={GRID} />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 12 }}
              tickFormatter={(value) => {
                const date = parseDay(value)
                return `${date.getMonth() + 1}/${date.getDate()}`
              }}
            />
            <YAxis
              domain={[0, 100]}
              tick={{ fontSize: 12 }}
              tickFormatter={(value) => `${value}%`}
            />
            <Tooltip
              contentStyle={tooltipStyle}
              formatter={(value: number) => [`${value}%`, '']}
              labelFormatter={(label) => parseDay(label).toLocaleDateString()}
            />
            <Legend
              wrapperStyle={{ fontSize: '12px' }}
              formatter={(value) => {
                const evalName = value.replace('_pass_rate', '')
                return EVALUATOR_NAMES[evalName] || evalName
              }}
            />
            {metricKeys.map((key, index) => (
              <Line {...chartMotion}
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
