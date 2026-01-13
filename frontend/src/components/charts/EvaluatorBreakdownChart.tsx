import {
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
  PieChart,
  Pie,
  Cell,
  Legend,
} from 'recharts'

interface EvaluatorData {
  evaluator: string
  display_name: string
  total: number
  passed: number
  failed: number
  pass_rate: number
  avg_score: number
}

interface EvaluatorBreakdownChartProps {
  data: EvaluatorData[]
  chartType?: 'radar' | 'pie'
  title?: string
}

const COLORS = [
  '#6366f1', // indigo
  '#10b981', // emerald
  '#f59e0b', // amber
  '#ef4444', // red
  '#8b5cf6', // violet
]

export default function EvaluatorBreakdownChart({
  data,
  chartType = 'radar',
  title = 'Evaluator Performance',
}: EvaluatorBreakdownChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">{title}</h3>
        <div className="h-64 flex items-center justify-center text-gray-500">
          No evaluator data available yet.
        </div>
      </div>
    )
  }

  if (chartType === 'pie') {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">{title}</h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                outerRadius={80}
                dataKey="total"
                nameKey="display_name"
                label={({ display_name, pass_rate }) => `${display_name}: ${pass_rate}%`}
                labelLine={{ stroke: '#9ca3af' }}
              >
                {data.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: '#fff',
                  border: '1px solid #e5e7eb',
                  borderRadius: '8px',
                  fontSize: '12px',
                }}
                formatter={(_value, _name, props) => {
                  const payload = props.payload as EvaluatorData | undefined
                  if (!payload) return ['', '']
                  return [
                    `${payload.passed}/${payload.total} passed (${payload.pass_rate}%)`,
                    payload.display_name,
                  ]
                }}
              />
              <Legend wrapperStyle={{ fontSize: '12px' }} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>
    )
  }

  // Radar chart
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">{title}</h3>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart cx="50%" cy="50%" outerRadius="70%" data={data}>
            <PolarGrid stroke="#e5e7eb" />
            <PolarAngleAxis
              dataKey="display_name"
              tick={{ fontSize: 11, fill: '#6b7280' }}
            />
            <PolarRadiusAxis
              angle={90}
              domain={[0, 100]}
              tick={{ fontSize: 10 }}
              tickFormatter={(value) => `${value}%`}
            />
            <Radar
              name="Pass Rate"
              dataKey="pass_rate"
              stroke="#6366f1"
              fill="#6366f1"
              fillOpacity={0.5}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#fff',
                border: '1px solid #e5e7eb',
                borderRadius: '8px',
                fontSize: '12px',
              }}
              formatter={(value: number) => [`${value}%`, 'Pass Rate']}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>
      {/* Legend below radar */}
      <div className="mt-4 flex flex-wrap gap-2 justify-center">
        {data.map((item, index) => (
          <div
            key={item.evaluator}
            className="flex items-center gap-1.5 text-xs text-gray-600"
          >
            <div
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: COLORS[index % COLORS.length] }}
            />
            <span>{item.display_name}: {item.passed}/{item.total}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
