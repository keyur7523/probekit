import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { testCasesApi } from '../api/client'
import type { TestCase, TestCaseCreate } from '../types'

function TestCaseModal({
  isOpen,
  onClose,
  onSubmit,
  initialData,
}: {
  isOpen: boolean
  onClose: () => void
  onSubmit: (data: TestCaseCreate) => void
  initialData?: TestCase
}) {
  const [formData, setFormData] = useState<TestCaseCreate>({
    prompt: initialData?.prompt || '',
    input: initialData?.input || '',
    expected_structure: initialData?.expected_structure,
    context: initialData?.context || '',
    category: initialData?.category || '',
  })

  if (!isOpen) return null

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit(formData)
  }

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="fixed inset-0 bg-black bg-opacity-50" onClick={onClose} />
      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative bg-white rounded-xl shadow-xl max-w-2xl w-full p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            {initialData ? 'Edit Test Case' : 'Create Test Case'}
          </h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                System Prompt
              </label>
              <textarea
                value={formData.prompt}
                onChange={(e) => setFormData({ ...formData, prompt: e.target.value })}
                rows={3}
                className="w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 border p-2"
                placeholder="You are a helpful assistant..."
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                User Input
              </label>
              <textarea
                value={formData.input}
                onChange={(e) => setFormData({ ...formData, input: e.target.value })}
                rows={2}
                className="w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 border p-2"
                placeholder="What is the capital of France?"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Context (optional)
              </label>
              <textarea
                value={formData.context || ''}
                onChange={(e) => setFormData({ ...formData, context: e.target.value })}
                rows={2}
                className="w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 border p-2"
                placeholder="Additional context for the model..."
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Category (optional)
              </label>
              <input
                type="text"
                value={formData.category || ''}
                onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                className="w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 border p-2"
                placeholder="factual, reasoning, creative..."
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Expected Structure (JSON, optional)
              </label>
              <textarea
                value={formData.expected_structure ? JSON.stringify(formData.expected_structure, null, 2) : ''}
                onChange={(e) => {
                  try {
                    const parsed = e.target.value ? JSON.parse(e.target.value) : undefined
                    setFormData({ ...formData, expected_structure: parsed })
                  } catch {
                    // Allow invalid JSON while typing
                  }
                }}
                rows={3}
                className="w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 border p-2 font-mono text-sm"
                placeholder='{"format": "json", "required_fields": ["name", "age"]}'
              />
            </div>
            <div className="flex justify-end gap-3 pt-4">
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
                {initialData ? 'Update' : 'Create'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}

export default function TestCases() {
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingTestCase, setEditingTestCase] = useState<TestCase | undefined>()
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['testCases'],
    queryFn: () => testCasesApi.list({ limit: 100 }),
  })

  const createMutation = useMutation({
    mutationFn: testCasesApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['testCases'] })
      setIsModalOpen(false)
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<TestCaseCreate> }) =>
      testCasesApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['testCases'] })
      setIsModalOpen(false)
      setEditingTestCase(undefined)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: testCasesApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['testCases'] })
    },
  })

  const handleSubmit = (formData: TestCaseCreate) => {
    if (editingTestCase) {
      updateMutation.mutate({ id: editingTestCase.id, data: formData })
    } else {
      createMutation.mutate(formData)
    }
  }

  const handleEdit = (testCase: TestCase) => {
    setEditingTestCase(testCase)
    setIsModalOpen(true)
  }

  const handleDelete = (id: string) => {
    if (confirm('Are you sure you want to delete this test case?')) {
      deleteMutation.mutate(id)
    }
  }

  const testCases = data?.test_cases || []

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Test Cases</h1>
          <p className="mt-1 text-gray-500">Manage your prompt test cases</p>
        </div>
        <button
          onClick={() => {
            setEditingTestCase(undefined)
            setIsModalOpen(true)
          }}
          className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg transition-colors"
        >
          + New Test Case
        </button>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200">
        {isLoading ? (
          <div className="p-6 text-center text-gray-500">Loading...</div>
        ) : testCases.length === 0 ? (
          <div className="p-6 text-center text-gray-500">
            No test cases yet. Create your first one!
          </div>
        ) : (
          <div className="divide-y divide-gray-200">
            {testCases.map((testCase) => (
              <div key={testCase.id} className="p-6">
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                      {testCase.category && (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                          {testCase.category}
                        </span>
                      )}
                      <span className="text-xs text-gray-500">
                        {new Date(testCase.created_at).toLocaleDateString()}
                      </span>
                    </div>
                    <p className="text-sm font-medium text-gray-900 mb-1 line-clamp-2">
                      {testCase.prompt}
                    </p>
                    <p className="text-sm text-gray-500 line-clamp-1">
                      Input: {testCase.input}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 ml-4">
                    <button
                      onClick={() => handleEdit(testCase)}
                      className="px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleDelete(testCase.id)}
                      className="px-3 py-1.5 text-sm font-medium text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <TestCaseModal
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false)
          setEditingTestCase(undefined)
        }}
        onSubmit={handleSubmit}
        initialData={editingTestCase}
      />
    </div>
  )
}
