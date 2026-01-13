import asyncio
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import TestCase, EvaluationRun, EvaluationOutput, RunStatus
from app.clients.base import BaseLLMClient
from app.clients.claude import ClaudeClient
from app.clients.openai import OpenAIClient
from app.clients.ollama import OllamaClient
from app.schemas.evaluation import ModelConfig


def get_client_for_model(model_config: ModelConfig) -> BaseLLMClient:
    """Factory function to get the appropriate client for a model."""
    model_id = model_config.model_id.lower()

    if "claude" in model_id:
        return ClaudeClient(model_id=model_config.model_id)
    elif "gpt" in model_id or "o1" in model_id:
        return OpenAIClient(model_id=model_config.model_id)
    elif any(local in model_id for local in ["llama", "mistral", "mixtral", "phi", "qwen"]):
        return OllamaClient(model_id=model_config.model_id)
    else:
        # Default to OpenAI for unknown models
        return OpenAIClient(model_id=model_config.model_id)


async def run_single_evaluation(
    client: BaseLLMClient,
    test_case: TestCase,
    model_config: ModelConfig,
) -> dict:
    """Run evaluation for a single test case against a single model."""
    # Combine prompt template with input
    full_prompt = f"{test_case.prompt}\n\nInput: {test_case.input}"

    try:
        response = await client.generate(
            prompt=full_prompt,
            temperature=model_config.temperature,
            max_tokens=model_config.max_tokens,
        )

        return {
            "success": True,
            "model_response": response.content,
            "latency_ms": response.latency_ms,
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
            "cost_usd": response.cost_usd,
            "error": None,
        }
    except Exception as e:
        return {
            "success": False,
            "model_response": None,
            "latency_ms": None,
            "input_tokens": None,
            "output_tokens": None,
            "cost_usd": None,
            "error": str(e),
        }


async def run_evaluation(
    db: AsyncSession,
    run_id: UUID,
    test_case_ids: list[UUID],
    model_configs: list[ModelConfig],
) -> None:
    """
    Run evaluation for all test cases against all models.
    Updates the database as it progresses.
    """
    # Get the evaluation run
    result = await db.execute(select(EvaluationRun).where(EvaluationRun.id == run_id))
    run = result.scalar_one_or_none()

    if not run:
        return

    # Update status to running
    run.status = RunStatus.RUNNING
    await db.commit()

    # Get all test cases
    result = await db.execute(select(TestCase).where(TestCase.id.in_(test_case_ids)))
    test_cases = result.scalars().all()

    total_cost = 0.0
    total_duration = 0
    completed = 0

    try:
        # For each model, run all test cases in parallel
        for model_config in model_configs:
            client = get_client_for_model(model_config)

            # Create tasks for all test cases
            tasks = []
            for test_case in test_cases:
                task = run_single_evaluation(client, test_case, model_config)
                tasks.append((test_case, task))

            # Run all tasks concurrently (with some rate limiting)
            semaphore = asyncio.Semaphore(10)  # Max 10 concurrent requests per model

            async def run_with_semaphore(tc, task_coro):
                async with semaphore:
                    return tc, await task_coro

            results = await asyncio.gather(*[
                run_with_semaphore(tc, task) for tc, task in tasks
            ])

            # Store results
            for test_case, eval_result in results:
                output = EvaluationOutput(
                    run_id=run_id,
                    test_case_id=test_case.id,
                    model=model_config.model_id,
                    model_response=eval_result.get("model_response"),
                    latency_ms=eval_result.get("latency_ms"),
                    input_tokens=eval_result.get("input_tokens"),
                    output_tokens=eval_result.get("output_tokens"),
                    cost_usd=eval_result.get("cost_usd"),
                    error=eval_result.get("error"),
                )
                db.add(output)

                if eval_result.get("cost_usd"):
                    total_cost += eval_result["cost_usd"]
                if eval_result.get("latency_ms"):
                    total_duration += eval_result["latency_ms"]

                completed += 1

            await db.commit()

        # Update run with final stats
        run.status = RunStatus.COMPLETED
        run.total_cost_usd = total_cost
        run.total_duration_ms = total_duration
        run.completed_count = completed
        await db.commit()

    except Exception as e:
        run.status = RunStatus.FAILED
        run.error_message = str(e)
        await db.commit()
        raise
