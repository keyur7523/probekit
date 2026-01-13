import { useMemo, useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { evaluationsApi, annotationsApi } from '../api/client'
import type { EvaluationOutput, EvaluationRun } from '../types'

const ANNOTATION_TYPES = [
  'correctness',
  'hallucination',
  'instruction_adherence',
  'refusal_behavior',
  'format_consistency',
  'other',
]

function OutputNavigator({
  output,
  currentIndex,
  totalCount,
  onPrev,
  onNext,
}: {
  output: EvaluationOutput
  currentIndex: number
  totalCount: number
  onPrev: () => void
  onNext: () => void
}) {
  return (
    <div className="flex items-center justify-between mb-4">
      <div>
        <p className="text-sm text-gray-500">
          Output {currentIndex + 1} of {totalCount}
        </p>
        <p className="text-sm font-medium text-gray-900">{output.model}</p>
        <p className="text-xs text-gray-500">Test Case: {output.test_case_id.slice(0, 8)}...</p>
      </div>
      <div className="flex items-center gap-2">
        <button
          onClick={onPrev}
          disabled={currentIndex === 0}
          className="px-3 py-2 text-xs font-medium text-gray-700 border border-gray-200 rounded-lg disabled:opacity-50"
        >
          Previous
        </button>
        <button
          onClick={onNext}
          disabled={currentIndex >= totalCount - 1}
          className="px-3 py-2 text-xs font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg disabled:opacity-50"
        >
          Next
        </button>
      </div>
    </div>
  )
}

function AnnotationForm({
  output,
  runId,
}: {
  output: EvaluationOutput
  runId: string
}) {
  const queryClient = useQueryClient()
  const [annotationType, setAnnotationType] = useState(ANNOTATION_TYPES[0])
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
    <div className="border border-gray-200 rounded-lg p-4">
      <p className="text-xs font-medium text-gray-500 mb-3">Add Annotation</p>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-2 mb-3">
        <select
          value={annotationType}
          onChange={(e) => setAnnotationType(e.target.value)}
          disabled={!canAnnotate}
          className="rounded border-gray-300 text-xs p-2 border"
        >
          {ANNOTATION_TYPES.map((type) => (
            <option key={type} value={type}>{type}</option>
          ))}
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
  )
}

export default function Annotations() {
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null)
  const [showUnannotatedOnly, setShowUnannotatedOnly] = useState(false)
  const [currentIndex, setCurrentIndex] = useState(0)

  const { data: runsData } = useQuery({
    queryKey: ['evaluations'],
    queryFn: () => evaluationsApi.list({ limit: 50 }),
  })

  const runs = runsData?.runs || []

  useEffect(() => {
    if (!selectedRunId && runs.length > 0) {
      setSelectedRunId(runs[0].id)
    }
  }, [runs, selectedRunId])

  const { data: run } = useQuery({
    queryKey: ['evaluation', selectedRunId],
    queryFn: () => evaluationsApi.get(selectedRunId as string),
    enabled: !!selectedRunId,
  })

  const outputs = useMemo(() => {
    if (!run?.outputs) return []
    if (!showUnannotatedOnly) return run.outputs
    return run.outputs.filter((output) => !output.annotations || output.annotations.length === 0)
  }, [run, showUnannotatedOnly])

  useEffect(() => {
    if (currentIndex >= outputs.length) {
      setCurrentIndex(0)
    }
  }, [currentIndex, outputs.length])

  const currentOutput = outputs[currentIndex]

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Annotations</h1>
        <p className="mt-1 text-gray-500">Review outputs one at a time and add human labels</p>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
        <div className="flex flex-col md:flex-row md:items-center gap-4">
          <div className="flex-1">
            <label className="block text-xs font-medium text-gray-500 mb-1">Evaluation Run</label>
            <select
              value={selectedRunId || ''}
              onChange={(e) => {
                setSelectedRunId(e.target.value)
                setCurrentIndex(0)
              }}
              className="w-full rounded-lg border-gray-300 text-sm p-2 border"
            >
              {runs.length === 0 && (
                <option value="">No runs available</option>
              )}
              {runs.map((item: EvaluationRun) => (
                <option key={item.id} value={item.id}>
                  {item.prompt_version} • {new Date(item.timestamp).toLocaleDateString()}
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={showUnannotatedOnly}
              onChange={(e) => {
                setShowUnannotatedOnly(e.target.checked)
                setCurrentIndex(0)
              }}
              className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
            />
            <span className="text-sm text-gray-600">Only unannotated</span>
          </div>
        </div>
      </div>

      {!run && (
        <div className="text-center py-12 text-gray-500">Select a run to begin annotating.</div>
      )}

      {run && outputs.length === 0 && (
        <div className="text-center py-12 text-gray-500">No outputs to annotate.</div>
      )}

      {run && currentOutput && (
        <div className="space-y-6">
          <OutputNavigator
            output={currentOutput}
            currentIndex={currentIndex}
            totalCount={outputs.length}
            onPrev={() => setCurrentIndex((prev) => Math.max(0, prev - 1))}
            onNext={() => setCurrentIndex((prev) => Math.min(outputs.length - 1, prev + 1))}
          />

          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <p className="text-xs font-medium text-gray-500 mb-2">Model Output</p>
            <pre className="text-sm text-gray-700 whitespace-pre-wrap font-mono bg-gray-50 p-3 rounded">
              {currentOutput.model_response || 'No response'}
            </pre>
          </div>

          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <p className="text-xs font-medium text-gray-500 mb-3">Existing Annotations</p>
            {currentOutput.annotations && currentOutput.annotations.length > 0 ? (
              <div className="space-y-2">
                {currentOutput.annotations.map((annotation) => (
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
              <p className="text-xs text-gray-500">No annotations yet.</p>
            )}
          </div>

          <AnnotationForm output={currentOutput} runId={run.id} />
        </div>
      )}
    </div>
  )
}
