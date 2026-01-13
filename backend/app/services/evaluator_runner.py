from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import EvaluationRun, EvaluationOutput, EvaluatorResult, TestCase
from app.schemas.evaluation import ModelConfig
from app.services.evaluation import get_client_for_model
from app.evaluators import (
    get_evaluator,
    EvaluationContext,
    InstructionAdherenceEvaluator,
    HallucinationEvaluator,
    FormatEvaluator,
    RefusalEvaluator,
    StabilityEvaluator,
)


async def run_evaluators_on_output(
    db: AsyncSession,
    output: EvaluationOutput,
    test_case: TestCase,
    evaluator_names: list[str],
    model_configs: dict[str, ModelConfig],
) -> list[EvaluatorResult]:
    """
    Run specified evaluators on a single output.

    Args:
        db: Database session
        output: The model output to evaluate
        test_case: The test case that generated this output
        evaluator_names: List of evaluator names to run

    Returns:
        List of EvaluatorResult objects
    """
    results = []

    # Skip if no model response
    if not output.model_response:
        return results

    # Build evaluation context with spec fields
    context = EvaluationContext(
        output=output.model_response,
        prompt=test_case.prompt,
        input_text=test_case.input,
        context=test_case.context,
        expected_structure=test_case.expected_structure,
        category=test_case.category,
        instruction_spec=getattr(test_case, 'instruction_spec', None),
        format_spec=getattr(test_case, 'format_spec', None),
        stability_params=getattr(test_case, 'stability_params', None),
        should_refuse=getattr(test_case, 'should_refuse', None),
    )

    for evaluator_name in evaluator_names:
        try:
            if evaluator_name == "output_stability":
                stability_result = await _run_stability_evaluator(
                    output,
                    test_case,
                    model_configs.get(output.model),
                )
                result = EvaluatorResult(
                    output_id=output.id,
                    evaluator_name=stability_result.evaluator_name,
                    passed=stability_result.passed,
                    score=stability_result.score,
                    details=stability_result.details,
                    reasoning=stability_result.reasoning,
                )
                db.add(result)
                results.append(result)
                continue

            # Get evaluator with default config
            if evaluator_name == "refusal_behavior":
                # Use should_refuse from test case if set, otherwise infer from category
                if context.should_refuse is not None:
                    expect_refusal = context.should_refuse
                else:
                    category = (test_case.category or "").lower()
                    expect_refusal = "safety" in category or "refusal" in category or "policy" in category
                evaluator = get_evaluator(
                    evaluator_name,
                    expect_refusal=expect_refusal,
                    expect_answer=not expect_refusal,
                )
            else:
                evaluator = get_evaluator(evaluator_name)

            # Run evaluation
            eval_output = await evaluator.evaluate(context)

            # Create result
            result = EvaluatorResult(
                output_id=output.id,
                evaluator_name=eval_output.evaluator_name,
                passed=eval_output.passed,
                score=eval_output.score,
                details=eval_output.details,
                reasoning=eval_output.reasoning,
            )
            db.add(result)
            results.append(result)

        except Exception as e:
            # Log error but continue with other evaluators
            result = EvaluatorResult(
                output_id=output.id,
                evaluator_name=evaluator_name,
                passed=False,
                score=0.0,
                details={"error": str(e)},
                reasoning=f"Evaluator error: {str(e)}",
            )
            db.add(result)
            results.append(result)

    await db.commit()
    return results


async def run_evaluators_on_run(
    db: AsyncSession,
    run_id: UUID,
    evaluator_names: list[str],
) -> dict:
    """
    Run evaluators on all outputs in an evaluation run.

    Args:
        db: Database session
        run_id: ID of the evaluation run
        evaluator_names: List of evaluator names to run

    Returns:
        Summary of evaluator results
    """
    # Get the run with outputs
    result = await db.execute(
        select(EvaluationRun)
        .options(selectinload(EvaluationRun.outputs))
        .where(EvaluationRun.id == run_id)
    )
    run = result.scalar_one_or_none()

    if not run:
        raise ValueError(f"Evaluation run not found: {run_id}")

    # Get test cases for all outputs
    test_case_ids = [o.test_case_id for o in run.outputs]
    tc_result = await db.execute(
        select(TestCase).where(TestCase.id.in_(test_case_ids))
    )
    test_cases = {tc.id: tc for tc in tc_result.scalars().all()}

    model_configs: dict[str, ModelConfig] = {}
    for model in run.models or []:
        try:
            model_config = ModelConfig(**model)
            model_configs[model_config.model_id] = model_config
        except Exception:
            continue

    # Run evaluators on each output
    total_results = []
    for output in run.outputs:
        test_case = test_cases.get(output.test_case_id)
        if not test_case:
            continue

        results = await run_evaluators_on_output(db, output, test_case, evaluator_names, model_configs)
        total_results.extend(results)

    # Calculate summary
    summary = {
        "run_id": str(run_id),
        "outputs_evaluated": len(run.outputs),
        "evaluators_run": evaluator_names,
        "results_count": len(total_results),
        "pass_rates": {},
    }

    # Calculate pass rate per evaluator
    for evaluator_name in evaluator_names:
        evaluator_results = [r for r in total_results if r.evaluator_name == evaluator_name]
        if evaluator_results:
            passed = sum(1 for r in evaluator_results if r.passed)
            summary["pass_rates"][evaluator_name] = {
                "passed": passed,
                "total": len(evaluator_results),
                "rate": round(passed / len(evaluator_results), 3),
            }

    return summary


async def _run_stability_evaluator(
    output: EvaluationOutput,
    test_case: TestCase,
    model_config: ModelConfig | None,
) -> "EvaluatorOutput":
    """Run multi-sample stability evaluation by re-sampling the same prompt."""
    evaluator = StabilityEvaluator()

    config = model_config or ModelConfig(model_id=output.model, temperature=0.0, max_tokens=1024)
    client = get_client_for_model(config)

    # Use stability_params from test case if available, otherwise use defaults
    stability_params = getattr(test_case, 'stability_params', None) or {}
    temperatures = stability_params.get('temperatures', [0.0, 0.5, 1.0])
    samples_per_temp = stability_params.get('samples_per_temp', 2)

    full_prompt = f"{test_case.prompt}\n\nInput: {test_case.input}"
    outputs = [output.model_response]

    async def sample(temp: float) -> str:
        response = await client.generate(
            prompt=full_prompt,
            temperature=temp,
            max_tokens=config.max_tokens,
        )
        return response.content

    tasks = []
    for temp in temperatures:
        for _ in range(samples_per_temp):
            tasks.append(sample(temp))

    if tasks:
        sampled = await asyncio.gather(*tasks)
        outputs.extend(sampled)

    eval_output = await evaluator.evaluate_multiple(outputs)
    return eval_output
