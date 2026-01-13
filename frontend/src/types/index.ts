export interface TestCase {
  id: string
  title?: string
  prompt: string
  input: string
  expected_structure?: Record<string, unknown>
  context?: string
  category?: string
  created_at: string
  updated_at: string
}

export interface TestCaseCreate {
  title?: string
  prompt: string
  input: string
  expected_structure?: Record<string, unknown>
  context?: string
  category?: string
}

export interface ModelConfig {
  model_id: string
  temperature: number
  max_tokens: number
}

export interface HumanAnnotation {
  id: string
  output_id: string
  annotation_type: string
  label: string
  notes?: string | null
  extra_data?: Record<string, unknown> | null
  created_by?: string | null
  created_at: string
}

export interface EvaluatorResult {
  id: string
  evaluator_name: string
  passed: boolean | null
  score: number | null
  details: Record<string, unknown> | null
  reasoning: string | null
}

export interface EvaluationOutput {
  id: string
  test_case_id: string
  test_case_title?: string | null
  model: string
  model_response: string | null
  latency_ms: number | null
  input_tokens: number | null
  output_tokens: number | null
  cost_usd: number | null
  error: string | null
  evaluator_results: EvaluatorResult[]
  annotations: HumanAnnotation[]
}

export interface EvaluatorRegressionDelta {
  evaluator_name: string
  current_rate: number
  previous_rate: number
  delta: number
  regressed: boolean
}

export interface RunComparison {
  previous_run_id: string
  previous_timestamp: string
  deltas: EvaluatorRegressionDelta[]
  has_regression: boolean
}

export interface EvaluationRun {
  id: string
  prompt_version: string
  models: ModelConfig[]
  status: 'pending' | 'running' | 'completed' | 'failed'
  timestamp: string
  total_cost_usd: number
  total_duration_ms: number
  test_case_count: number
  completed_count: number
  error_message: string | null
  test_case_titles?: string[]
  outputs?: EvaluationOutput[]
  comparison?: RunComparison | null
}

export interface EvaluationRunCreate {
  prompt_version: string
  test_case_ids: string[]
  models: ModelConfig[]
  evaluators?: string[]
}

export interface Evaluator {
  name: string
  description: string
}

export interface RegressionEntry {
  evaluator_name: string
  current_rate: number | null
  previous_rate: number | null
  delta: number | null
  regressed: boolean
}

export interface RegressionComparison {
  prompt_version: string
  current_run: {
    id: string
    timestamp: string
  }
  previous_run: {
    id: string
    timestamp: string
  } | null
  regressions: RegressionEntry[]
  has_regression: boolean
  note?: string
}
