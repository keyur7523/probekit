# Behavioral Eval

I built this open-source framework to systematically measure LLM behaviors across prompts and models. The core insight driving this project: **prompts are deployable software artifacts**—they should be tested and versioned like software, with clear metrics, regression detection, and rollback strategies.

## Why I Built This

The current state of prompt evaluation is immature. "Is this response good?" is subjective and doesn't scale. When you ship a prompt update and users complain, you often don't know why. I wanted a tool that answers: **How do I measure if my prompt change made things better, worse, or broke something?**

## Features

- **Multi-model evaluation** — Run the same prompt against Claude, GPT-4, and local models; track cost and latency
- **Pre-built evaluators** — Instruction adherence, hallucination detection, output stability, refusal behavior, format consistency
- **Human annotation UI** — Review outputs, add labels, track agreement between human and automated evaluations
- **Regression detection** — Compare prompt versions, flag regressions automatically
- **Dashboard** — Visualize trends, model comparison, evaluator performance over time

## Quick Start

### 1. Start PostgreSQL

I use a local Postgres instance with a database named `probekit`. Update the `DATABASE_URL` in `.env` if yours differs.

### 2. Set up the backend

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

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

API available at http://localhost:8001

### 4. Set up the frontend

```bash
cd ../frontend
npm install
npm run dev
```

UI available at http://localhost:5173

### 5. Seed sample data (optional)

```bash
# Sample test cases
python3 backend/scripts/seed_test_cases.py --api http://localhost:8001

# Demo evaluation runs with results
python3 backend/scripts/seed_demo_runs.py
```

## API Endpoints

### Test Cases
- `POST /api/test-cases` — Create a test case
- `GET /api/test-cases` — List test cases
- `GET /api/test-cases/{id}` — Get a test case
- `PUT /api/test-cases/{id}` — Update a test case
- `DELETE /api/test-cases/{id}` — Delete a test case

### Evaluations
- `POST /api/evaluations/run` — Start an evaluation run
- `GET /api/evaluations/runs` — List evaluation runs
- `GET /api/evaluations/runs/{id}` — Get evaluation run details
- `GET /api/evaluations/results` — Get aggregated results
- `POST /api/evaluations/runs/{id}/evaluate` — Run evaluators on a completed run
- `GET /api/evaluations/evaluators` — List available evaluators

### Conversations (Multi-turn)
- `POST /api/conversations/run` — Start a multi-turn conversation run
- `GET /api/conversations/runs` — List conversation runs
- `GET /api/conversations/{run_id}` — Get conversation details with all turns
- `GET /api/conversations/metrics` — Verbosity stability metrics
- `GET /api/conversations/compare` — Compare conditions (baseline vs treatment)

### Annotations
- `POST /api/annotations` — Create a human annotation
- `GET /api/annotations` — List annotations

### Dashboard
- `GET /api/dashboard/metrics` — Overall metrics (includes p50/p99 latency)
- `GET /api/dashboard/trends` — Evaluator pass-rate trends
- `GET /api/dashboard/model-comparison` — Model comparison stats
- `GET /api/dashboard/evaluator-breakdown` — Evaluator summary stats
- `GET /api/dashboard/versions` — Latest run per prompt version
- `GET /api/dashboard/compare` — Compare two versions and flag regressions
- `GET /api/dashboard/regressions` — Latest regressions per version
- `GET /api/dashboard/annotation-accuracy` — Human vs evaluator agreement

## Example Usage

### Create a test case

```bash
curl -X POST http://localhost:8001/api/test-cases \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Summarize the following text in 2-3 sentences.",
    "input": "The quick brown fox jumps over the lazy dog.",
    "category": "summarization"
  }'
```

### Run an evaluation

```bash
curl -X POST http://localhost:8001/api/evaluations/run \
  -H "Content-Type: application/json" \
  -d '{
    "prompt_version": "v1.0",
    "test_case_ids": ["<test-case-uuid>"],
    "models": [
      {"model_id": "claude-sonnet-4-20250514", "temperature": 0.0, "max_tokens": 1000},
      {"model_id": "gpt-4o", "temperature": 0.0, "max_tokens": 1000}
    ],
    "evaluators": ["instruction_adherence", "hallucination", "format_consistency"]
  }'
```

### Run a multi-turn conversation

```bash
curl -X POST http://localhost:8001/api/conversations/run \
  -H "Content-Type: application/json" \
  -d '{
    "condition": "baseline",
    "model": {"model_id": "claude-sonnet-4-20250514", "temperature": 0.2, "max_tokens": 512},
    "turns": [
      "Explain what a hash table is.",
      "Give an everyday example.",
      "What is one tradeoff?"
    ],
    "system_prompt": "You are a concise assistant.",
    "intent_id": "concept_explanation"
  }'
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
│   ├── scripts/          # Seed scripts, utilities
│   └── tests/            # pytest tests
├── frontend/
│   ├── src/
│   │   ├── components/   # React components
│   │   ├── pages/        # Route pages
│   │   ├── api/          # API client
│   │   └── types/        # TypeScript types
│   └── package.json
└── artifacts/            # Conversation run outputs (gitignored)
```

## Supported Models

### Claude (Anthropic)
- claude-sonnet-4-20250514
- claude-opus-4-20250514
- claude-3-5-haiku-20241022

### OpenAI
- gpt-4o
- gpt-4o-mini
- gpt-4-turbo

### Local (via Ollama)
- llama3.1, mistral, or any Ollama-supported model

## Evaluators

I built five core evaluators based on what matters for production prompts:

| Evaluator | What It Measures |
|-----------|------------------|
| **Instruction Adherence** | Does output follow constraints? (JSON validity, required fields, length limits, forbidden terms) |
| **Hallucination Detection** | Are claims grounded in provided context? Uses LLM-as-judge to verify factual claims |
| **Output Stability** | Is output consistent across re-runs? Measures semantic similarity via Jaccard |
| **Refusal Behavior** | Does model refuse appropriately? Classifies responses as refusal/abstention/clarification/answer |
| **Format Consistency** | Does output match expected format? Validates JSON schema, markdown structure, regex patterns |
| **Verbosity Stability** | (Conversations) Does response length drift over turns? Measures drift slope, growth ratio |

### Adding a Custom Evaluator

```python
# backend/app/evaluators/my_evaluator.py
from app.evaluators.base import BaseEvaluator, EvaluationContext, EvaluatorOutput

class MyEvaluator(BaseEvaluator):
    name = "my_evaluator"
    description = "What this evaluator checks"

    async def evaluate(self, context: EvaluationContext) -> EvaluatorOutput:
        output = context.output
        passed = len(output) < 500  # Example check
        return EvaluatorOutput(
            evaluator_name=self.name,
            passed=passed,
            score=1.0 if passed else 0.0,
            details={"length": len(output)},
            reasoning="Output length check",
        )
```

Register it in `backend/app/evaluators/__init__.py`:

```python
from app.evaluators.my_evaluator import MyEvaluator

EVALUATOR_REGISTRY = {
    # ...existing
    "my_evaluator": MyEvaluator,
}
```

## Database Migrations

I use Alembic for migrations. For hosted environments without shell access (like Render free tier), tables are created automatically on app startup via `Base.metadata.create_all`.

```bash
cd backend

# Generate migration after model changes
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head
```

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy 2.x (async), Pydantic v2, PostgreSQL
- **Frontend**: React 18, TypeScript, Vite, TanStack Query, Tailwind CSS, Recharts
- **LLM Clients**: Anthropic SDK, OpenAI SDK, Ollama

## License

MIT
