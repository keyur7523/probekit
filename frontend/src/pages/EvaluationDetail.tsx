import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { evaluationsApi, annotationsApi } from '../api/client'
import type { EvaluationRun, EvaluationOutput, EvaluatorResult, Evaluator } from '../types'

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

function EvaluatorBadge({ result }: { result: EvaluatorResult }) {
  const bgColor = result.passed === true
    ? 'bg-green-100 text-green-800'
    : result.passed === false
    ? 'bg-red-100 text-red-800'
    : 'bg-gray-100 text-gray-800'

  return (
    <div className={`inline-flex items-center gap-1.5 px-2 py-1 rounded text-xs font-medium ${bgColor}`}>
      <span>{result.evaluator_name}</span>
      {result.score !== null && (
        <span className="opacity-75">({(result.score * 100).toFixed(0)}%)</span>
      )}
    </div>
  )
}

function OutputCard({ output, runId }: { output: EvaluationOutput; runId: string }) {
  const [isExpanded, setIsExpanded] = useState(false)
  const queryClient = useQueryClient()
  const [annotationType, setAnnotationType] = useState('correctness')
  const [label, setLabel] = useState('')
  const [notes, setNotes] = useState('')

  const createAnnotationMutation = useMutation({
    mutationFn: () =>
      annotationsApi.create({
        output_id: output.id,
        annotation_type: annotationType,
        label,
        notes: notes || undefined,
      }),
    onSuccess: () => {
      setLabel('')
      setNotes('')
      queryClient.invalidateQueries({ queryKey: ['evaluation', runId] })
    },
  })

  const canAnnotate = !output.error && !!output.model_response

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      <div className="p-4 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="font-medium text-gray-900">{output.model}</span>
            {output.error ? (
              <span className="text-xs bg-red-100 text-red-800 px-2 py-0.5 rounded">Error</span>
            ) : (
              <span className="text-xs bg-green-100 text-green-800 px-2 py-0.5 rounded">Success</span>
            )}
          </div>
          <div className="flex items-center gap-4 text-sm text-gray-500">
            <span>{output.latency_ms}ms</span>
            <span>${output.cost_usd?.toFixed(6) || '0.000000'}</span>
            <span>{output.input_tokens}→{output.output_tokens} tokens</span>
          </div>
        </div>
      </div>

      <div className="p-4">
        {output.error ? (
          <div className="text-red-600 text-sm font-mono bg-red-50 p-3 rounded">
            {output.error}
          </div>
        ) : (
          <>
            <div className="mb-3">
              <pre
                className={`text-sm text-gray-700 whitespace-pre-wrap font-mono bg-gray-50 p-3 rounded ${
                  !isExpanded && 'max-h-32 overflow-hidden'
                }`}
              >
                {output.model_response}
              </pre>
              {output.model_response && output.model_response.length > 200 && (
                <button
                  onClick={() => setIsExpanded(!isExpanded)}
                  className="text-sm text-indigo-600 hover:text-indigo-700 mt-2"
                >
                  {isExpanded ? 'Show less' : 'Show more'}
                </button>
              )}
            </div>

            {output.evaluator_results && output.evaluator_results.length > 0 && (
              <div className="border-t border-gray-200 pt-3 mt-3">
                <p className="text-xs font-medium text-gray-500 mb-2">Evaluator Results</p>
                <div className="flex flex-wrap gap-2">
                  {output.evaluator_results.map((result) => (
                    <EvaluatorBadge key={result.id} result={result} />
                  ))}
                </div>
              </div>
            )}

            <div className="border-t border-gray-200 pt-3 mt-3">
              <p className="text-xs font-medium text-gray-500 mb-2">Human Annotations</p>
              {output.annotations && output.annotations.length > 0 ? (
                <div className="space-y-2 mb-3">
                  {output.annotations.map((annotation) => (
                    <div key={annotation.id} className="text-xs text-gray-700 bg-gray-50 rounded p-2">
                      <div className="flex items-center justify-between">
                        <span className="font-medium">{annotation.annotation_type}: {annotation.label}</span>
                        <span className="text-gray-400">{new Date(annotation.created_at).toLocaleString()}</span>
                      </div>
                      {annotation.notes && (
                        <p className="text-gray-600 mt-1">{annotation.notes}</p>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-gray-500 mb-3">No annotations yet.</p>
              )}

              <div className="grid grid-cols-1 md:grid-cols-3 gap-2 mb-2">
                <select
                  value={annotationType}
                  onChange={(e) => setAnnotationType(e.target.value)}
                  disabled={!canAnnotate}
                  className="rounded border-gray-300 text-xs p-2 border"
                >
                  <option value="correctness">correctness</option>
                  <option value="hallucination">hallucination</option>
                  <option value="instruction_adherence">instruction_adherence</option>
                  <option value="refusal_behavior">refusal_behavior</option>
                  <option value="format_consistency">format_consistency</option>
                  <option value="other">other</option>
                </select>
                <input
                  type="text"
                  value={label}
                  onChange={(e) => setLabel(e.target.value)}
                  disabled={!canAnnotate}
                  className="rounded border-gray-300 text-xs p-2 border"
                  placeholder="Label (e.g., correct, incorrect)"
                />
                <input
                  type="text"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  disabled={!canAnnotate}
                  className="rounded border-gray-300 text-xs p-2 border"
                  placeholder="Notes (optional)"
                />
              </div>
              <button
                onClick={() => createAnnotationMutation.mutate()}
                disabled={!canAnnotate || !label || createAnnotationMutation.isPending}
                className="px-3 py-2 text-xs font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded disabled:opacity-50"
              >
                {createAnnotationMutation.isPending ? 'Saving...' : 'Save Annotation'}
              </button>
              {!canAnnotate && (
                <p className="text-xs text-gray-500 mt-2">Annotations are disabled for errored outputs.</p>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  )
}

function RunEvaluatorsModal({
  isOpen,
  onClose,
  runId,
}: {
  isOpen: boolean
  onClose: () => void
  runId: string
}) {
  const [selectedEvaluators, setSelectedEvaluators] = useState<string[]>([])
  const queryClient = useQueryClient()

  const { data: evaluators } = useQuery({
    queryKey: ['evaluators'],
    queryFn: () => evaluationsApi.listEvaluators(),
  })

  const runEvaluatorsMutation = useMutation({
    mutationFn: () => evaluationsApi.runEvaluators(runId, selectedEvaluators),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['evaluation', runId] })
      onClose()
    },
  })

  if (!isOpen) return null

  const toggleEvaluator = (name: string) => {
    setSelectedEvaluators((prev) =>
      prev.includes(name) ? prev.filter((x) => x !== name) : [...prev, name]
    )
  }

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="fixed inset-0 bg-black bg-opacity-50" onClick={onClose} />
      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative bg-white rounded-xl shadow-xl max-w-md w-full p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Run Evaluators</h2>

          {evaluators && evaluators.length > 0 ? (
            <div className="space-y-2 mb-6">
              {evaluators.map((evaluator: Evaluator) => (
                <label
                  key={evaluator.name}
                  className="flex items-center p-3 rounded-lg border border-gray-200 cursor-pointer hover:bg-gray-50"
                >
                  <input
                    type="checkbox"
                    checked={selectedEvaluators.includes(evaluator.name)}
                    onChange={() => toggleEvaluator(evaluator.name)}
                    className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                  />
                  <div className="ml-3">
                    <p className="text-sm font-medium text-gray-900">{evaluator.name}</p>
                    <p className="text-xs text-gray-500">{evaluator.description}</p>
                  </div>
                </label>
              ))}
            </div>
          ) : (
            <p className="text-gray-500 mb-6">No evaluators available</p>
          )}

          <div className="flex justify-end gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-lg"
            >
              Cancel
            </button>
            <button
              onClick={() => runEvaluatorsMutation.mutate()}
              disabled={selectedEvaluators.length === 0 || runEvaluatorsMutation.isPending}
              className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg disabled:opacity-50"
            >
              {runEvaluatorsMutation.isPending ? 'Running...' : 'Run Evaluators'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function EvaluationDetail() {
  const { id } = useParams<{ id: string }>()
  const [isEvalModalOpen, setIsEvalModalOpen] = useState(false)

  const { data: run, isLoading, error } = useQuery({
    queryKey: ['evaluation', id],
    queryFn: () => evaluationsApi.get(id!),
    enabled: !!id,
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading...</div>
      </div>
    )
  }

  if (error || !run) {
    return (
      <div className="text-center py-12">
        <h2 className="text-xl font-semibold text-gray-900">Evaluation not found</h2>
        <Link to="/evaluations" className="text-indigo-600 hover:underline mt-2 inline-block">
          Back to evaluations
        </Link>
      </div>
    )
  }

  // Group outputs by test case
  const outputsByTestCase = run.outputs?.reduce((acc, output) => {
    if (!acc[output.test_case_id]) {
      acc[output.test_case_id] = []
    }
    acc[output.test_case_id].push(output)
    return acc
  }, {} as Record<string, EvaluationOutput[]>) || {}

  return (
    <div>
      <div className="mb-8">
        <Link
          to="/evaluations"
          className="text-sm text-gray-500 hover:text-gray-700 mb-2 inline-block"
        >
          &larr; Back to evaluations
        </Link>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{run.prompt_version}</h1>
            <p className="mt-1 text-gray-500">
              {new Date(run.timestamp).toLocaleString()}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setIsEvalModalOpen(true)}
              className="px-4 py-2 text-sm font-medium text-indigo-600 border border-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
            >
              Run Evaluators
            </button>
            <StatusBadge status={run.status} />
          </div>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <p className="text-sm text-gray-500">Total Cost</p>
          <p className="text-xl font-semibold text-gray-900">
            ${run.total_cost_usd?.toFixed(4) || '0.0000'}
          </p>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <p className="text-sm text-gray-500">Duration</p>
          <p className="text-xl font-semibold text-gray-900">
            {((run.total_duration_ms || 0) / 1000).toFixed(2)}s
          </p>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <p className="text-sm text-gray-500">Test Cases</p>
          <p className="text-xl font-semibold text-gray-900">
            {run.completed_count}/{run.test_case_count}
          </p>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <p className="text-sm text-gray-500">Models</p>
          <p className="text-xl font-semibold text-gray-900">{run.models.length}</p>
        </div>
      </div>

      {/* Regression Check */}
      {run.comparison && (
        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-8">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Regression Check</h2>
              <p className="text-sm text-gray-500">Compared to previous run for this prompt version.</p>
            </div>
            <span className={`text-xs px-2 py-1 rounded-full ${run.comparison.has_regression ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'}`}>
              {run.comparison.has_regression ? 'Regression detected' : 'No regression'}
            </span>
          </div>
          <div className="flex items-center justify-between text-sm text-gray-600 mb-4">
            <span>Previous run: {new Date(run.comparison.previous_timestamp).toLocaleString()}</span>
            <Link to={`/evaluations/${run.comparison.previous_run_id}`} className="text-indigo-600 hover:text-indigo-700">
              View previous run
            </Link>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {run.comparison.deltas.map((item) => (
              <div key={item.evaluator_name} className="border border-gray-200 rounded-lg p-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-gray-900">{item.evaluator_name}</span>
                  <span className={`text-xs ${item.regressed ? 'text-red-600' : 'text-gray-500'}`}>
                    {item.delta >= 0 ? `+${item.delta}` : item.delta}%
                  </span>
                </div>
                <p className="text-xs text-gray-500">{item.previous_rate}% → {item.current_rate}%</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Models Config */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-8">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Model Configuration</h2>
        <div className="flex flex-wrap gap-4">
          {run.models.map((model, i) => (
            <div key={i} className="bg-gray-50 rounded-lg px-4 py-3">
              <p className="font-medium text-gray-900">{model.model_id}</p>
              <p className="text-sm text-gray-500">
                temp: {model.temperature} • max_tokens: {model.max_tokens}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Error message if any */}
      {run.error_message && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-8">
          <p className="text-red-800 font-medium">Error</p>
          <p className="text-red-700 text-sm mt-1">{run.error_message}</p>
        </div>
      )}

      {/* Outputs by Test Case */}
      <div className="space-y-8">
        {Object.entries(outputsByTestCase).map(([testCaseId, outputs]) => (
          <div key={testCaseId}>
            <h3 className="text-sm font-medium text-gray-500 mb-3">
              Test Case: {testCaseId.substring(0, 8)}...
            </h3>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {outputs.map((output) => (
                <OutputCard key={output.id} output={output} runId={run.id} />
              ))}
            </div>
          </div>
        ))}
      </div>

      {(!run.outputs || run.outputs.length === 0) && run.status === 'completed' && (
        <div className="text-center py-12 text-gray-500">
          No outputs available for this run.
        </div>
      )}

      <RunEvaluatorsModal
        isOpen={isEvalModalOpen}
        onClose={() => setIsEvalModalOpen(false)}
        runId={id!}
      />
    </div>
  )
}
