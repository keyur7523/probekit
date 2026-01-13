import { useState, useEffect, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { evaluationsApi, testCasesApi } from '../api/client'
import type { EvaluationRun, EvaluationRunCreate, ModelConfig, Evaluator } from '../types'

function StatusBadge({ status }: { status: EvaluationRun['status'] }) {
  const styles = {
    pending: 'bg-yellow-100 text-yellow-800',
    running: 'bg-blue-100 text-blue-800',
    completed: 'bg-green-100 text-green-800',
    failed: 'bg-red-100 text-red-800',
  }
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${styles[status]}`}>
      {status}
    </span>
  )
}

const DEFAULT_MODELS: ModelConfig[] = [
  { model_id: 'claude-sonnet-4-20250514', temperature: 0.7, max_tokens: 1024 },
  { model_id: 'gpt-4o', temperature: 0.7, max_tokens: 1024 },
]

function NewEvaluationModal({
  isOpen,
  onClose,
  onSubmit,
}: {
  isOpen: boolean
  onClose: () => void
  onSubmit: (data: EvaluationRunCreate) => void
}) {
  const [promptVersion, setPromptVersion] = useState('v1.0')
  const [selectedTestCases, setSelectedTestCases] = useState<string[]>([])
  const [models, setModels] = useState<ModelConfig[]>(DEFAULT_MODELS)
  const [selectedEvaluators, setSelectedEvaluators] = useState<string[]>([])
  const [autoRunEvaluators, setAutoRunEvaluators] = useState(true)
  const hasInitializedEvaluators = useRef(false)

  const { data: testCasesData } = useQuery({
    queryKey: ['testCases'],
    queryFn: () => testCasesApi.list({ limit: 100 }),
  })

  const { data: evaluators } = useQuery({
    queryKey: ['evaluators'],
    queryFn: () => evaluationsApi.listEvaluators(),
  })

  useEffect(() => {
    if (hasInitializedEvaluators.current) {
      return
    }
    if (!evaluators || evaluators.length == 0) {
      return
    }
    setSelectedEvaluators(evaluators.map((evaluator) => evaluator.name))
    hasInitializedEvaluators.current = true
  }, [evaluators])

  if (!isOpen) return null

  const testCases = testCasesData?.test_cases || []

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (selectedTestCases.length === 0) {
      alert('Please select at least one test case')
      return
    }
    onSubmit({
      prompt_version: promptVersion,
      test_case_ids: selectedTestCases,
      models,
      evaluators: autoRunEvaluators && selectedEvaluators.length > 0 ? selectedEvaluators : undefined,
    })
  }

  const toggleTestCase = (id: string) => {
    setSelectedTestCases((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    )
  }

  const toggleEvaluator = (name: string) => {
    setSelectedEvaluators((prev) =>
      prev.includes(name) ? prev.filter((x) => x !== name) : [...prev, name]
    )
  }

  const addModel = () => {
    setModels([...models, { model_id: '', temperature: 0.7, max_tokens: 1024 }])
  }

  const removeModel = (index: number) => {
    setModels(models.filter((_, i) => i !== index))
  }

  const updateModel = (index: number, field: keyof ModelConfig, value: string | number) => {
    const newModels = [...models]
    newModels[index] = { ...newModels[index], [field]: value }
    setModels(newModels)
  }

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="fixed inset-0 bg-black bg-opacity-50" onClick={onClose} />
      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative bg-white rounded-xl shadow-xl max-w-3xl w-full p-6 max-h-[90vh] overflow-y-auto">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">New Evaluation Run</h2>
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Prompt Version
              </label>
              <input
                type="text"
                value={promptVersion}
                onChange={(e) => setPromptVersion(e.target.value)}
                className="w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 border p-2"
                placeholder="v1.0"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Select Test Cases
              </label>
              {testCases.length === 0 ? (
                <p className="text-sm text-gray-500">
                  No test cases available.{' '}
                  <Link to="/test-cases" className="text-indigo-600 hover:underline">
                    Create some first
                  </Link>
                </p>
              ) : (
                <div className="max-h-48 overflow-y-auto border border-gray-200 rounded-lg divide-y divide-gray-200">
                  {testCases.map((tc) => (
                    <label
                      key={tc.id}
                      className="flex items-center px-4 py-3 hover:bg-gray-50 cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={selectedTestCases.includes(tc.id)}
                        onChange={() => toggleTestCase(tc.id)}
                        className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                      />
                      <div className="ml-3 flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {tc.prompt.substring(0, 60)}...
                        </p>
                        <p className="text-xs text-gray-500 truncate">{tc.input}</p>
                      </div>
                      {tc.category && (
                        <span className="ml-2 text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">
                          {tc.category}
                        </span>
                      )}
                    </label>
                  ))}
                </div>
              )}
              <p className="mt-1 text-sm text-gray-500">
                {selectedTestCases.length} selected
              </p>
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="block text-sm font-medium text-gray-700">Models</label>
                <button
                  type="button"
                  onClick={addModel}
                  className="text-sm text-indigo-600 hover:text-indigo-700"
                >
                  + Add Model
                </button>
              </div>
              <div className="space-y-3">
                {models.map((model, index) => (
                  <div key={index} className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                    <input
                      type="text"
                      value={model.model_id}
                      onChange={(e) => updateModel(index, 'model_id', e.target.value)}
                      className="flex-1 rounded border-gray-300 text-sm p-2 border"
                      placeholder="Model ID (e.g., gpt-4o)"
                      required
                    />
                    <div className="flex items-center gap-1">
                      <span className="text-xs text-gray-500">Temp:</span>
                      <input
                        type="number"
                        value={model.temperature}
                        onChange={(e) => updateModel(index, 'temperature', parseFloat(e.target.value))}
                        className="w-16 rounded border-gray-300 text-sm p-2 border"
                        step="0.1"
                        min="0"
                        max="2"
                      />
                    </div>
                    <div className="flex items-center gap-1">
                      <span className="text-xs text-gray-500">Tokens:</span>
                      <input
                        type="number"
                        value={model.max_tokens}
                        onChange={(e) => updateModel(index, 'max_tokens', parseInt(e.target.value))}
                        className="w-20 rounded border-gray-300 text-sm p-2 border"
                        min="1"
                      />
                    </div>
                    {models.length > 1 && (
                      <button
                        type="button"
                        onClick={() => removeModel(index)}
                        className="text-red-500 hover:text-red-700"
                      >
                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="block text-sm font-medium text-gray-700">
                  Evaluators (optional)
                </label>
                <label className="inline-flex items-center gap-2 text-xs text-gray-600">
                  <input
                    type="checkbox"
                    checked={autoRunEvaluators}
                    onChange={(e) => setAutoRunEvaluators(e.target.checked)}
                    className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                  />
                  Auto-run evaluators
                </label>
              </div>
              {evaluators && evaluators.length > 0 ? (
                <>
                  <p className="text-xs text-gray-500 mb-2">All evaluators are selected by default for new runs.</p>
                  <div className="flex flex-wrap gap-2">
                    {evaluators.map((evaluator: Evaluator) => (
                    <label
                      key={evaluator.name}
                      className={`inline-flex items-center px-3 py-2 rounded-lg border cursor-pointer transition-colors ${
                        selectedEvaluators.includes(evaluator.name)
                          ? 'border-indigo-500 bg-indigo-50 text-indigo-700'
                          : 'border-gray-200 hover:bg-gray-50'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={selectedEvaluators.includes(evaluator.name)}
                        onChange={() => toggleEvaluator(evaluator.name)}
                        className="sr-only"
                      />
                      <span className="text-sm font-medium">{evaluator.name}</span>
                    </label>
                  ))}
                  </div>
                </>
              ) : (
                <p className="text-sm text-gray-500">No evaluators available</p>
              )}
            </div>

            <div className="flex justify-end gap-3 pt-4 border-t">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg transition-colors"
              >
                Run Evaluation
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}

export default function Evaluations() {
  const [isModalOpen, setIsModalOpen] = useState(false)
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['evaluations'],
    queryFn: () => evaluationsApi.list({ limit: 50 }),
  })

  const createMutation = useMutation({
    mutationFn: evaluationsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['evaluations'] })
      setIsModalOpen(false)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: evaluationsApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['evaluations'] })
    },
  })

  const handleDelete = (id: string) => {
    if (confirm('Are you sure you want to delete this evaluation run?')) {
      deleteMutation.mutate(id)
    }
  }

  const runs = data?.runs || []

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Evaluations</h1>
          <p className="mt-1 text-gray-500">Run and manage LLM evaluations</p>
        </div>
        <button
          onClick={() => setIsModalOpen(true)}
          className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg transition-colors"
        >
          + New Evaluation
        </button>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200">
        {isLoading ? (
          <div className="p-6 text-center text-gray-500">Loading...</div>
        ) : runs.length === 0 ? (
          <div className="p-6 text-center text-gray-500">
            No evaluation runs yet. Start your first one!
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Version
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Models
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Test Cases
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Cost
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Duration
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Date
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {runs.map((run) => (
                  <tr key={run.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <Link
                        to={`/evaluations/${run.id}`}
                        className="text-sm font-medium text-indigo-600 hover:text-indigo-800"
                      >
                        {run.prompt_version}
                      </Link>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <StatusBadge status={run.status} />
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {run.models.map((m) => m.model_id).join(', ')}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {run.completed_count}/{run.test_case_count}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      ${run.total_cost_usd?.toFixed(4) || '0.0000'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {((run.total_duration_ms || 0) / 1000).toFixed(2)}s
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {new Date(run.timestamp).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
                      <Link
                        to={`/evaluations/${run.id}`}
                        className="text-indigo-600 hover:text-indigo-800 mr-3"
                      >
                        View
                      </Link>
                      <button
                        onClick={() => handleDelete(run.id)}
                        className="text-red-600 hover:text-red-800"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <NewEvaluationModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSubmit={(data) => createMutation.mutate(data)}
      />
    </div>
  )
}
