import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts'

interface AnnotationAccuracyDatum {
  evaluator_name: string
  accuracy: number
}

interface AnnotationAccuracyChartProps {
  data: AnnotationAccuracyDatum[]
  title?: string
}

const COLORS = [
  '#10b981',
  '#6366f1',
  '#f59e0b',
  '#ef4444',
  '#8b5cf6',
]

function prettyName(name: string): string {
  return name.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())
}

export default function AnnotationAccuracyChart({
  data,
  title = 'Annotation Accuracy',
}: AnnotationAccuracyChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">{title}</h3>
        <div className="h-56 flex items-center justify-center text-gray-500">
          No annotation accuracy data available yet.
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">{title}</h3>
      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 40 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis
              dataKey="evaluator_name"
              tick={{ fontSize: 11 }}
              tickFormatter={prettyName}
              angle={-25}
              textAnchor="end"
              height={50}
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
              formatter={(value: number) => [`${value}%`, 'Accuracy']}
              labelFormatter={(label) => prettyName(label)}
            />
            <Bar dataKey="accuracy" radius={[4, 4, 0, 0]}>
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
