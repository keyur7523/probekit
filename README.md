# Behavioral Eval

An open-source framework for systematically measuring LLM behaviors across prompts and models.

## Highlights

- Multi-model evaluation with cost/latency tracking
- Pre-built evaluators: instruction adherence, hallucination, stability, refusal, format consistency
- Human annotation UI + accuracy tracking
- Regression detection with version comparison
- Dashboard for trends, model comparison, evaluator performance

## Quick Start (No Docker)

### 1. Start PostgreSQL

Use your local Postgres instance and ensure you have a database named `probekit` (or update the `DATABASE_URL`).

### 2. Set up the backend

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scriptsctivate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys and database URL
```

### 3. Run the server

```bash
uvicorn app.main:app --reload --port 8001
```

The API will be available at http://localhost:8001

### 4. Set up the frontend

```bash
cd ../frontend
npm install
npm run dev
```

The UI will be available at http://localhost:5173

### 5. Seed sample test cases (optional)

```bash
python3 backend/scripts/seed_test_cases.py --api http://localhost:8001
```

### 6. Seed demo evaluation runs (optional)

This creates completed runs, evaluator results, and a few annotations for dashboard demos:

```bash
python3 backend/scripts/seed_demo_runs.py
```

## API Endpoints

### Test Cases
- `POST /api/test-cases` - Create a test case
- `GET /api/test-cases` - List test cases
- `GET /api/test-cases/{id}` - Get a test case
- `PUT /api/test-cases/{id}` - Update a test case
- `DELETE /api/test-cases/{id}` - Delete a test case

### Evaluations
- `POST /api/evaluations/run` - Start an evaluation run
- `GET /api/evaluations/runs` - List evaluation runs
- `GET /api/evaluations/runs/{id}` - Get evaluation run details
- `GET /api/evaluations/results` - Get aggregated results
- `POST /api/evaluations/runs/{id}/evaluate` - Run evaluators on a completed run
- `GET /api/evaluations/evaluators` - List available evaluators

### Annotations
- `POST /api/annotations` - Create a human annotation
- `GET /api/annotations` - List annotations (filter by output_id)

### Dashboard / Regressions
- `GET /api/dashboard/metrics` - Overall metrics (includes p50/p99 latency)
- `GET /api/dashboard/trends` - Evaluator pass-rate trends
- `GET /api/dashboard/model-comparison` - Model comparison stats
- `GET /api/dashboard/evaluator-breakdown` - Evaluator summary stats
- `GET /api/dashboard/recent-activity` - Recent completed runs
- `GET /api/dashboard/versions` - Latest run per prompt version
- `GET /api/dashboard/compare` - Compare two versions and flag regressions
- `GET /api/dashboard/regressions` - Latest regressions per version
- `GET /api/dashboard/annotation-accuracy` - Human vs evaluator agreement
- `GET /api/dashboard/refusal-stats` - Refusal FP/FN rates with examples

## Example Usage

### Create a test case

```bash
curl -X POST http://localhost:8001/api/test-cases   -H "Content-Type: application/json"   -d '{
    "prompt": "Summarize the following text in 2-3 sentences.",
    "input": "The quick brown fox jumps over the lazy dog. This pangram contains every letter of the alphabet.",
    "category": "summarization"
  }'
```

### Run an evaluation

```bash
curl -X POST http://localhost:8001/api/evaluations/run   -H "Content-Type: application/json"   -d '{
    "prompt_version": "v1.0",
    "test_case_ids": ["<test-case-uuid>"],
    "models": [
      {"model_id": "claude-3-5-sonnet-20241022", "temperature": 0.0, "max_tokens": 1000},
      {"model_id": "gpt-4o", "temperature": 0.0, "max_tokens": 1000}
    ],
    "evaluators": ["instruction_adherence", "hallucination", "format_consistency"]
  }'
```

## Database Migrations

The project uses Alembic for database migrations.

```bash
cd backend

# Show current revision
alembic current

# Generate a new migration after model changes
alembic revision --autogenerate -m "description"

# Apply all pending migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

## Project Structure

```
probekit/
├── backend/
│   ├── alembic/          # Database migrations
│   ├── app/
│   │   ├── api/          # FastAPI routes
│   │   ├── clients/      # LLM API clients (Claude, OpenAI, Ollama)
│   │   ├── evaluators/   # Behavioral evaluators
│   │   ├── models/       # SQLAlchemy models
│   │   ├── schemas/      # Pydantic schemas
│   │   ├── services/     # Business logic
│   │   ├── config.py     # Settings
│   │   ├── database.py   # DB connection
│   │   └── main.py       # FastAPI app
│   ├── sample_data/      # Sample test cases
│   ├── scripts/          # Helper scripts
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── api/
│   │   └── types/
│   └── package.json
└── README.md
```

## Supported Models

### Claude (Anthropic)
- claude-3-5-sonnet-20241022
- claude-3-opus-20240229
- claude-3-5-haiku-20241022

### OpenAI
- gpt-4o
- gpt-4o-mini
- gpt-4-turbo

### Local (via Ollama)
- llama3.1
- mistral
- Any other Ollama-supported model


## Evaluator Customization

You can add new evaluators or configure existing ones by editing the backend.

### Configure built-in evaluators

The evaluators are defined in `backend/app/evaluators/` and registered in `backend/app/evaluators/__init__.py`.

Examples:

- **Instruction adherence**: Uses JSON validity + required fields. If `expected_structure` includes `required`, it will enforce those fields.
- **Format consistency**: Validates JSON schema constraints like `minLength`, `maxLength`, `enum`, `minimum`, `maximum`, and `additionalProperties: false`.
- **Refusal behavior**: If the test case `category` includes `safety`, `refusal`, or `policy`, it expects refusal/abstention.
- **Output stability**: Re-samples the same prompt at multiple temperatures and computes consistency.

### Add a custom evaluator

1) Create a new evaluator class:

```python
# backend/app/evaluators/length_guard.py
from app.evaluators.base import BaseEvaluator, EvaluationContext, EvaluatorOutput

class LengthGuardEvaluator(BaseEvaluator):
    name = "length_guard"
    description = "Checks output length bounds"

    def __init__(self, min_len: int = 10, max_len: int = 200):
        self.min_len = min_len
        self.max_len = max_len

    async def evaluate(self, context: EvaluationContext) -> EvaluatorOutput:
        length = len(context.output)
        passed = self.min_len <= length <= self.max_len
        return EvaluatorOutput(
            evaluator_name=self.name,
            passed=passed,
            score=1.0 if passed else 0.0,
            details={"length": length, "min": self.min_len, "max": self.max_len},
            reasoning="Within bounds" if passed else "Out of bounds",
        )
```

2) Register it:

```python
# backend/app/evaluators/__init__.py
from app.evaluators.length_guard import LengthGuardEvaluator

EVALUATOR_REGISTRY = {
    # ...existing evaluators
    "length_guard": LengthGuardEvaluator,
}
```

3) Run it via API:

```bash
curl -X POST http://localhost:8001/api/evaluations/runs/<run-id>/evaluate   -H "Content-Type: application/json"   -d ''   "?evaluators=length_guard"
```

### Configure evaluators per run

You can specify evaluator names when starting a run:

```bash
curl -X POST http://localhost:8001/api/evaluations/run   -H "Content-Type: application/json"   -d '{
    "prompt_version": "v1.0",
    "test_case_ids": ["<test-case-uuid>"],
    "models": [{"model_id": "gpt-4o", "temperature": 0.0, "max_tokens": 512}],
    "evaluators": ["instruction_adherence", "format_consistency", "length_guard"]
  }'
```
