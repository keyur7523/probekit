import axios from 'axios'
import type {
  TestCase,
  TestCaseCreate,
  EvaluationRun,
  EvaluationRunCreate,
  Evaluator,
  HumanAnnotation,
} from '../types'

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Test Cases
export const testCasesApi = {
  list: async (params?: { skip?: number; limit?: number; category?: string }) => {
    const { data } = await api.get<{ test_cases: TestCase[]; total: number }>(
      '/test-cases/',
      { params }
    )
    return data
  },

  get: async (id: string) => {
    const { data } = await api.get<TestCase>(`/test-cases/${id}`)
    return data
  },

  create: async (testCase: TestCaseCreate) => {
    const { data } = await api.post<TestCase>('/test-cases/', testCase)
    return data
  },

  update: async (id: string, testCase: Partial<TestCaseCreate>) => {
    const { data } = await api.put<TestCase>(`/test-cases/${id}`, testCase)
    return data
  },

  delete: async (id: string) => {
    await api.delete(`/test-cases/${id}`)
  },
}

// Evaluations
export const evaluationsApi = {
  list: async (params?: {
    skip?: number
    limit?: number
    prompt_version?: string
    status?: string
  }) => {
    const { data } = await api.get<{ runs: EvaluationRun[]; total: number }>(
      '/evaluations/runs',
      { params }
    )
    return data
  },

  get: async (id: string) => {
    const { data } = await api.get<EvaluationRun>(`/evaluations/runs/${id}`)
    return data
  },

  create: async (request: EvaluationRunCreate) => {
    const { data } = await api.post<{ run_id: string; status: string; message: string }>(
      '/evaluations/run',
      request
    )
    return data
  },

  delete: async (id: string) => {
    await api.delete(`/evaluations/runs/${id}`)
  },

  getResults: async (params?: { prompt_version?: string; model?: string }) => {
    const { data } = await api.get('/evaluations/results', { params })
    return data
  },

  runEvaluators: async (runId: string, evaluators: string[]) => {
    const { data } = await api.post(`/evaluations/runs/${runId}/evaluate`, null, {
      params: { evaluators },
    })
    return data
  },

  listEvaluators: async () => {
    const { data } = await api.get<{ evaluators: Evaluator[] }>('/evaluations/evaluators')
    return data.evaluators
  },
}


// Annotations
export const annotationsApi = {
  list: async (params?: { output_id?: string; skip?: number; limit?: number }) => {
    const { data } = await api.get<{ annotations: HumanAnnotation[]; total: number }>(
      '/annotations/',
      { params }
    )
    return data
  },

  create: async (annotation: {
    output_id: string
    annotation_type: string
    label: string
    notes?: string
    extra_data?: Record<string, unknown>
    created_by?: string
  }) => {
    const { data } = await api.post<HumanAnnotation>('/annotations/', annotation)
    return data
  },
}

// Dashboard
export const dashboardApi = {
  getMetrics: async () => {
    const { data } = await api.get<DashboardMetrics>('/dashboard/metrics')
    return data
  },

  getTrends: async (days: number = 30) => {
    const { data } = await api.get<TrendsResponse>('/dashboard/trends', { params: { days } })
    return data
  },

  getModelComparison: async () => {
    const { data } = await api.get<ModelComparisonResponse>('/dashboard/model-comparison')
    return data
  },

  getEvaluatorBreakdown: async () => {
    const { data } = await api.get<EvaluatorBreakdownResponse>('/dashboard/evaluator-breakdown')
    return data
  },

  getAnnotationAccuracy: async () => {
    const { data } = await api.get<AnnotationAccuracyResponse>('/dashboard/annotation-accuracy')
    return data
  },

  getRecentActivity: async (limit: number = 10) => {
    const { data } = await api.get<RecentActivityResponse>('/dashboard/recent-activity', { params: { limit } })
    return data
  },

  getVersions: async () => {
    const { data } = await api.get<VersionsResponse>('/dashboard/versions')
    return data
  },

  compareVersions: async (baselineVersion: string, currentVersion: string, threshold: number = 5.0) => {
    const { data } = await api.get<ComparisonResponse>('/dashboard/compare', {
      params: {
        baseline_version: baselineVersion,
        current_version: currentVersion,
        regression_threshold: threshold,
      },
    })
    return data
  },

  getRegressions: async () => {
    const { data } = await api.get<RegressionsResponse>('/dashboard/regressions')
    return data
  },
}

// Dashboard Types
export interface DashboardMetrics {
  total_test_cases: number
  total_runs: number
  completed_runs: number
  total_cost_usd: number
  avg_latency_ms: number
  latency_p50_ms: number
  latency_p99_ms: number
  total_evaluator_results: number
  overall_pass_rate: number
}

export interface TrendsResponse {
  days: number
  data: Array<{
    date: string
    [key: string]: string | number
  }>
}

export interface ModelComparisonResponse {
  data: Array<{
    model: string
    pass_rate: number
    avg_latency_ms: number
    avg_cost_usd: number
    total_evaluations: number
    [key: string]: string | number
  }>
}

export interface EvaluatorBreakdownResponse {
  data: Array<{
    evaluator: string
    display_name: string
    total: number
    passed: number
    failed: number
    pass_rate: number
    avg_score: number
  }>
}

export interface RecentActivityResponse {
  activity: Array<{
    id: string
    prompt_version: string
    timestamp: string
    models: string[]
    test_case_count: number
    total_evaluations: number
    passed: number
    pass_rate: number
    cost_usd: number
    duration_ms: number
  }>
}

export interface VersionInfo {
  prompt_version: string
  run_id: string
  timestamp: string
  pass_rate: number
  total_evaluations: number
  cost_usd: number
  duration_ms: number
  evaluator_pass_rates: Record<string, number>
}

export interface VersionsResponse {
  versions: VersionInfo[]
}

export interface Regression {
  type: 'overall' | 'evaluator' | 'model'
  metric: string
  baseline: number
  current: number
  delta: number
  severity: 'high' | 'medium'
  message: string
}

export interface ComparisonResponse {
  error?: string
  baseline?: {
    version: string
    run_id: string
    timestamp: string
    stats: {
      pass_rate: number
      total_evaluations: number
      cost_usd: number
      duration_ms: number
      evaluator_pass_rates: Record<string, number>
      model_stats: Record<string, {
        pass_rate: number
        avg_latency_ms: number
        avg_cost_usd: number
      }>
    }
  }
  current?: {
    version: string
    run_id: string
    timestamp: string
    stats: {
      pass_rate: number
      total_evaluations: number
      cost_usd: number
      duration_ms: number
      evaluator_pass_rates: Record<string, number>
      model_stats: Record<string, {
        pass_rate: number
        avg_latency_ms: number
        avg_cost_usd: number
      }>
    }
  }
  comparison?: {
    overall: {
      pass_rate_delta: number
      cost_delta: number
      duration_delta: number
    }
    evaluators: Record<string, {
      baseline: number
      current: number
      delta: number
      regression: boolean
    }>
    models: Record<string, {
      baseline: { pass_rate: number; avg_latency_ms: number; avg_cost_usd: number }
      current: { pass_rate: number; avg_latency_ms: number; avg_cost_usd: number }
      deltas: { pass_rate: number; avg_latency_ms: number; avg_cost_usd: number }
      regression: boolean
    }>
  }
  regressions?: Regression[]
  has_regressions?: boolean
  regression_count?: number
  threshold?: number
}

export interface RegressionItem {
  evaluator_name: string
  current_rate: number | null
  previous_rate: number | null
  delta: number | null
  regressed: boolean
}

export interface VersionComparison {
  prompt_version: string
  current_run: {
    id: string
    timestamp: string
  }
  previous_run: {
    id: string
    timestamp: string
  } | null
  regressions: RegressionItem[]
  has_regression: boolean
  note?: string
}

export interface RegressionsResponse {
  comparisons: VersionComparison[]
}

export default api

export interface AnnotationAccuracyResponse {
  data: Array<{
    evaluator_name: string
    total: number
    agreed: number
    accuracy: number
    human_true: number
    human_false: number
    auto_true: number
    auto_false: number
  }>
  total_annotations: number
  note?: string
}

