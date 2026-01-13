from collections import defaultdict
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import EvaluationRun, EvaluationOutput, EvaluatorResult, RunStatus, TestCase, HumanAnnotation

router = APIRouter()


def _calculate_run_stats(run: EvaluationRun) -> dict:
    evaluator_counts: dict[str, dict[str, int]] = defaultdict(lambda: {'passed': 0, 'total': 0})
    model_pass_counts: dict[str, dict[str, int]] = defaultdict(lambda: {'passed': 0, 'total': 0})
    model_latency: dict[str, list[int]] = defaultdict(list)
    model_costs: dict[str, list[float]] = defaultdict(list)

    total_results = 0
    total_passed = 0

    for output in run.outputs:
        if output.latency_ms is not None:
            model_latency[output.model].append(output.latency_ms)
        if output.cost_usd is not None:
            model_costs[output.model].append(output.cost_usd)

        for result in output.evaluator_results:
            total_results += 1
            evaluator_counts[result.evaluator_name]['total'] += 1
            model_pass_counts[output.model]['total'] += 1

            if result.passed:
                total_passed += 1
                evaluator_counts[result.evaluator_name]['passed'] += 1
                model_pass_counts[output.model]['passed'] += 1

    def _rate(passed: int, total: int) -> float:
        if total == 0:
            return 0.0
        return round((passed / total) * 100, 1)

    evaluator_pass_rates = {
        name: _rate(values['passed'], values['total'])
        for name, values in evaluator_counts.items()
    }

    model_stats = {}
    for model, counts in model_pass_counts.items():
        model_stats[model] = {
            'pass_rate': _rate(counts['passed'], counts['total']),
            'avg_latency_ms': round(sum(model_latency.get(model, [])) / len(model_latency.get(model, [1])), 1)
            if model_latency.get(model) else 0.0,
            'avg_cost_usd': round(sum(model_costs.get(model, [])) / len(model_costs.get(model, [1])), 6)
            if model_costs.get(model) else 0.0,
        }

    return {
        'pass_rate': _rate(total_passed, total_results),
        'total_evaluations': total_results,
        'cost_usd': round(run.total_cost_usd or 0.0, 6),
        'duration_ms': int(run.total_duration_ms or 0),
        'evaluator_pass_rates': evaluator_pass_rates,
        'model_stats': model_stats,
    }


def _calculate_percentile(sorted_values: list, percentile: float) -> float:
    """Calculate percentile from a sorted list of values."""
    if not sorted_values:
        return 0.0
    n = len(sorted_values)
    index = int(percentile * (n - 1))
    return float(sorted_values[index])


@router.get('/metrics')
async def get_metrics(db: AsyncSession = Depends(get_db)):
    """High-level dashboard metrics including latency percentiles."""
    total_test_cases = (await db.execute(select(func.count(TestCase.id)))).scalar() or 0
    total_runs = (await db.execute(select(func.count(EvaluationRun.id)))).scalar() or 0
    completed_runs = (await db.execute(
        select(func.count(EvaluationRun.id)).where(EvaluationRun.status == RunStatus.COMPLETED)
    )).scalar() or 0
    total_cost = (await db.execute(select(func.sum(EvaluationRun.total_cost_usd)))).scalar() or 0.0
    avg_latency = (await db.execute(select(func.avg(EvaluationOutput.latency_ms)))).scalar() or 0.0
    total_evaluator_results = (await db.execute(select(func.count(EvaluatorResult.id)))).scalar() or 0
    total_passed = (await db.execute(
        select(func.count(EvaluatorResult.id)).where(EvaluatorResult.passed.is_(True))
    )).scalar() or 0

    overall_pass_rate = round((total_passed / total_evaluator_results) * 100, 1) if total_evaluator_results else 0.0

    # Fetch all latencies for percentile calculation
    latency_result = await db.execute(
        select(EvaluationOutput.latency_ms)
        .where(EvaluationOutput.latency_ms.isnot(None))
        .order_by(EvaluationOutput.latency_ms)
    )
    all_latencies = [row[0] for row in latency_result.all()]

    latency_p50 = _calculate_percentile(all_latencies, 0.50)
    latency_p99 = _calculate_percentile(all_latencies, 0.99)

    return {
        'total_test_cases': total_test_cases,
        'total_runs': total_runs,
        'completed_runs': completed_runs,
        'total_cost_usd': round(float(total_cost), 6),
        'avg_latency_ms': round(float(avg_latency), 1),
        'latency_p50_ms': round(latency_p50, 1),
        'latency_p99_ms': round(latency_p99, 1),
        'total_evaluator_results': total_evaluator_results,
        'overall_pass_rate': overall_pass_rate,
    }


@router.get('/trends')
async def get_trends(
    days: int = Query(30, ge=1, le=180),
    db: AsyncSession = Depends(get_db),
):
    """Daily evaluator pass rate trends for the last N days."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    result = await db.execute(
        select(EvaluationRun)
        .where(EvaluationRun.status == RunStatus.COMPLETED)
        .where(EvaluationRun.timestamp >= cutoff)
        .options(
            selectinload(EvaluationRun.outputs)
            .selectinload(EvaluationOutput.evaluator_results)
        )
        .order_by(EvaluationRun.timestamp.asc())
    )
    runs = result.scalars().all()

    stats_by_date: dict[str, dict[str, dict[str, int]]] = defaultdict(lambda: defaultdict(lambda: {'passed': 0, 'total': 0}))
    for run in runs:
        day_key = run.timestamp.date().isoformat()
        for output in run.outputs:
            for result in output.evaluator_results:
                entry = stats_by_date[day_key][result.evaluator_name]
                entry['total'] += 1
                if result.passed:
                    entry['passed'] += 1

    data = []
    for day_key in sorted(stats_by_date.keys()):
        row = {'date': day_key}
        for evaluator, counts in stats_by_date[day_key].items():
            rate = round((counts['passed'] / counts['total']) * 100, 1) if counts['total'] else 0.0
            row[f'{evaluator}_pass_rate'] = rate
        data.append(row)

    return {'days': days, 'data': data}


@router.get('/model-comparison')
async def get_model_comparison(db: AsyncSession = Depends(get_db)):
    """Aggregate model performance stats across completed runs."""
    result = await db.execute(
        select(EvaluationRun)
        .where(EvaluationRun.status == RunStatus.COMPLETED)
        .options(
            selectinload(EvaluationRun.outputs)
            .selectinload(EvaluationOutput.evaluator_results)
        )
    )
    runs = result.scalars().all()

    model_pass_counts: dict[str, dict[str, int]] = defaultdict(lambda: {'passed': 0, 'total': 0})
    model_latency: dict[str, list[int]] = defaultdict(list)
    model_costs: dict[str, list[float]] = defaultdict(list)

    for run in runs:
        for output in run.outputs:
            if output.latency_ms is not None:
                model_latency[output.model].append(output.latency_ms)
            if output.cost_usd is not None:
                model_costs[output.model].append(output.cost_usd)
            for result in output.evaluator_results:
                model_pass_counts[output.model]['total'] += 1
                if result.passed:
                    model_pass_counts[output.model]['passed'] += 1

    data = []
    for model, counts in model_pass_counts.items():
        total = counts['total']
        pass_rate = round((counts['passed'] / total) * 100, 1) if total else 0.0
        avg_latency = round(sum(model_latency.get(model, [])) / len(model_latency.get(model, [1])), 1) if model_latency.get(model) else 0.0
        avg_cost = round(sum(model_costs.get(model, [])) / len(model_costs.get(model, [1])), 6) if model_costs.get(model) else 0.0
        data.append({
            'model': model,
            'pass_rate': pass_rate,
            'avg_latency_ms': avg_latency,
            'avg_cost_usd': avg_cost,
            'total_evaluations': total,
        })

    data.sort(key=lambda x: x['pass_rate'], reverse=True)
    return {'data': data}


@router.get('/evaluator-breakdown')
async def get_evaluator_breakdown(db: AsyncSession = Depends(get_db)):
    """Aggregate evaluator stats across all results."""
    result = await db.execute(select(EvaluatorResult))
    results = result.scalars().all()

    stats: dict[str, dict[str, float | int]] = defaultdict(lambda: {
        'total': 0,
        'passed': 0,
        'failed': 0,
        'score_sum': 0.0,
    })

    for res in results:
        entry = stats[res.evaluator_name]
        entry['total'] += 1
        if res.passed:
            entry['passed'] += 1
        else:
            entry['failed'] += 1
        if res.score is not None:
            entry['score_sum'] += float(res.score)

    data = []
    for evaluator, counts in stats.items():
        total = int(counts['total'])
        passed = int(counts['passed'])
        failed = int(counts['failed'])
        pass_rate = round((passed / total) * 100, 1) if total else 0.0
        avg_score = round((counts['score_sum'] / total), 3) if total else 0.0
        data.append({
            'evaluator': evaluator,
            'display_name': evaluator.replace('_', ' ').title(),
            'total': total,
            'passed': passed,
            'failed': failed,
            'pass_rate': pass_rate,
            'avg_score': avg_score,
        })

    data.sort(key=lambda x: x['pass_rate'], reverse=True)
    return {'data': data}


@router.get('/annotation-accuracy')
async def get_annotation_accuracy(db: AsyncSession = Depends(get_db)):
    """Compare evaluator results with human annotations (per evaluator)."""
    result = await db.execute(
        select(HumanAnnotation, EvaluatorResult)
        .join(
            EvaluatorResult,
            (EvaluatorResult.output_id == HumanAnnotation.output_id) &
            (EvaluatorResult.evaluator_name == HumanAnnotation.annotation_type)
        )
    )
    rows = result.all()

    def normalize_label(label: str) -> bool | None:
        if not label:
            return None
        value = label.strip().lower()
        true_labels = {'correct', 'pass', 'passed', 'yes', 'true', 'ok'}
        false_labels = {'incorrect', 'fail', 'failed', 'no', 'false', 'hallucinated'}
        if value in true_labels:
            return True
        if value in false_labels:
            return False
        return None

    stats: dict[str, dict[str, int]] = defaultdict(lambda: {
        'total': 0,
        'matched': 0,
        'agreed': 0,
        'human_true': 0,
        'human_false': 0,
        'auto_true': 0,
        'auto_false': 0,
    })

    for annotation, auto_result in rows:
        human_value = normalize_label(annotation.label)
        if human_value is None:
            continue
        entry = stats[auto_result.evaluator_name]
        entry['total'] += 1
        entry['matched'] += 1
        if human_value:
            entry['human_true'] += 1
        else:
            entry['human_false'] += 1
        if auto_result.passed is True:
            entry['auto_true'] += 1
        elif auto_result.passed is False:
            entry['auto_false'] += 1
        if auto_result.passed == human_value:
            entry['agreed'] += 1

    data = []
    for evaluator_name, entry in stats.items():
        total = entry['total']
        accuracy = round((entry['agreed'] / total) * 100, 1) if total else 0.0
        data.append({
            'evaluator_name': evaluator_name,
            'total': total,
            'agreed': entry['agreed'],
            'accuracy': accuracy,
            'human_true': entry['human_true'],
            'human_false': entry['human_false'],
            'auto_true': entry['auto_true'],
            'auto_false': entry['auto_false'],
        })

    data.sort(key=lambda item: item['accuracy'], reverse=True)
    return {
        'data': data,
        'total_annotations': sum(item['total'] for item in data),
        'note': 'Labels must be one of: correct/incorrect, pass/fail, yes/no, true/false, ok, hallucinated.'
    }


@router.get('/recent-activity')
async def get_recent_activity(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Return recent completed runs with summary stats for the dashboard."""
    result = await db.execute(
        select(EvaluationRun)
        .where(EvaluationRun.status == RunStatus.COMPLETED)
        .options(
            selectinload(EvaluationRun.outputs)
            .selectinload(EvaluationOutput.evaluator_results)
        )
        .order_by(EvaluationRun.timestamp.desc())
        .limit(limit)
    )
    runs = result.scalars().all()

    activity = []
    for run in runs:
        stats = _calculate_run_stats(run)
        activity.append({
            'id': str(run.id),
            'prompt_version': run.prompt_version,
            'test_case_count': run.test_case_count,
            'models': [m.get('model_id') for m in (run.models or [])],
            'cost_usd': stats['cost_usd'],
            'duration_ms': stats['duration_ms'],
            'pass_rate': stats['pass_rate'],
        })

    return {'activity': activity}


@router.get('/regressions')
async def get_regressions(db: AsyncSession = Depends(get_db)):
    """Compare evaluator pass rates between the two most recent runs per prompt version."""
    result = await db.execute(
        select(EvaluationRun)
        .where(EvaluationRun.status == RunStatus.COMPLETED)
        .options(
            selectinload(EvaluationRun.outputs)
            .selectinload(EvaluationOutput.evaluator_results)
        )
        .order_by(EvaluationRun.timestamp.desc())
    )
    runs = result.scalars().all()

    runs_by_version = defaultdict(list)
    for run in runs:
        runs_by_version[run.prompt_version].append(run)

    comparisons = []
    for prompt_version, version_runs in runs_by_version.items():
        if len(version_runs) < 2:
            comparisons.append({
                'prompt_version': prompt_version,
                'current_run': {
                    'id': str(version_runs[0].id),
                    'timestamp': version_runs[0].timestamp,
                },
                'previous_run': None,
                'regressions': [],
                'has_regression': False,
                'note': 'Not enough runs to compare',
            })
            continue

        current_run = version_runs[0]
        previous_run = version_runs[1]

        def summarize(run: EvaluationRun) -> dict[str, dict[str, float | int]]:
            stats: dict[str, dict[str, float | int]] = {}
            for output in run.outputs:
                for result in output.evaluator_results:
                    entry = stats.setdefault(result.evaluator_name, {'passed': 0, 'total': 0})
                    entry['total'] += 1
                    if result.passed:
                        entry['passed'] += 1
            for name, entry in stats.items():
                total = entry['total']
                entry['rate'] = round(entry['passed'] / total, 3) if total else None
            return stats

        current_stats = summarize(current_run)
        previous_stats = summarize(previous_run)

        regressions = []
        evaluator_names = set(current_stats.keys()) | set(previous_stats.keys())
        for name in sorted(evaluator_names):
            current_rate = current_stats.get(name, {}).get('rate')
            previous_rate = previous_stats.get(name, {}).get('rate')
            delta = None
            if current_rate is not None and previous_rate is not None:
                delta = round(current_rate - previous_rate, 3)
            regressions.append({
                'evaluator_name': name,
                'current_rate': current_rate,
                'previous_rate': previous_rate,
                'delta': delta,
                'regressed': delta is not None and delta < 0,
            })

        has_regression = any(r['regressed'] for r in regressions)

        comparisons.append({
            'prompt_version': prompt_version,
            'current_run': {
                'id': str(current_run.id),
                'timestamp': current_run.timestamp,
            },
            'previous_run': {
                'id': str(previous_run.id),
                'timestamp': previous_run.timestamp,
            },
            'regressions': regressions,
            'has_regression': has_regression,
        })

    return {'comparisons': comparisons}


@router.get('/versions')
async def get_versions(db: AsyncSession = Depends(get_db)):
    """Return the latest completed run per prompt version with summary stats."""
    result = await db.execute(
        select(EvaluationRun)
        .where(EvaluationRun.status == RunStatus.COMPLETED)
        .options(
            selectinload(EvaluationRun.outputs)
            .selectinload(EvaluationOutput.evaluator_results)
        )
        .order_by(EvaluationRun.timestamp.desc())
    )
    runs = result.scalars().all()

    latest_by_version: dict[str, EvaluationRun] = {}
    for run in runs:
        if run.prompt_version not in latest_by_version:
            latest_by_version[run.prompt_version] = run

    versions = []
    for prompt_version, run in latest_by_version.items():
        stats = _calculate_run_stats(run)
        versions.append({
            'prompt_version': prompt_version,
            'run_id': str(run.id),
            'timestamp': run.timestamp,
            'pass_rate': stats['pass_rate'],
            'total_evaluations': stats['total_evaluations'],
            'cost_usd': stats['cost_usd'],
            'duration_ms': stats['duration_ms'],
            'evaluator_pass_rates': stats['evaluator_pass_rates'],
        })

    versions.sort(key=lambda v: v['timestamp'], reverse=True)
    return {'versions': versions}


@router.get('/compare')
async def compare_versions(
    baseline_version: str = Query(..., alias='baseline_version'),
    current_version: str = Query(..., alias='current_version'),
    regression_threshold: float = Query(5.0, alias='regression_threshold'),
    db: AsyncSession = Depends(get_db),
):
    """Compare two prompt versions and flag regressions."""
    if baseline_version == current_version:
        return {'error': 'Baseline and current versions must differ'}

    result = await db.execute(
        select(EvaluationRun)
        .where(EvaluationRun.status == RunStatus.COMPLETED)
        .options(
            selectinload(EvaluationRun.outputs)
            .selectinload(EvaluationOutput.evaluator_results)
        )
        .order_by(EvaluationRun.timestamp.desc())
    )
    runs = result.scalars().all()

    baseline_run = next((r for r in runs if r.prompt_version == baseline_version), None)
    current_run = next((r for r in runs if r.prompt_version == current_version), None)

    if not baseline_run or not current_run:
        return {'error': 'Baseline or current version not found'}

    baseline_stats = _calculate_run_stats(baseline_run)
    current_stats = _calculate_run_stats(current_run)

    comparison = {
        'overall': {
            'pass_rate_delta': round(current_stats['pass_rate'] - baseline_stats['pass_rate'], 1),
            'cost_delta': round(current_stats['cost_usd'] - baseline_stats['cost_usd'], 6),
            'duration_delta': round(current_stats['duration_ms'] - baseline_stats['duration_ms'], 1),
        },
        'evaluators': {},
        'models': {},
    }

    regressions = []

    def severity(delta: float) -> str:
        return 'high' if abs(delta) >= regression_threshold * 2 else 'medium'

    # Evaluator deltas
    evaluator_names = set(baseline_stats['evaluator_pass_rates'].keys()) | set(current_stats['evaluator_pass_rates'].keys())
    for evaluator in evaluator_names:
        baseline_rate = baseline_stats['evaluator_pass_rates'].get(evaluator, 0.0)
        current_rate = current_stats['evaluator_pass_rates'].get(evaluator, 0.0)
        delta = round(current_rate - baseline_rate, 1)
        is_regression = delta <= -regression_threshold
        comparison['evaluators'][evaluator] = {
            'baseline': baseline_rate,
            'current': current_rate,
            'delta': delta,
            'regression': is_regression,
        }
        if is_regression:
            regressions.append({
                'type': 'evaluator',
                'metric': evaluator,
                'baseline': baseline_rate,
                'current': current_rate,
                'delta': delta,
                'severity': severity(delta),
                'message': f"{evaluator} pass rate dropped by {abs(delta)}%",
            })

    # Model deltas (pass rate only)
    model_names = set(baseline_stats['model_stats'].keys()) | set(current_stats['model_stats'].keys())
    for model in model_names:
        baseline_model = baseline_stats['model_stats'].get(model, {'pass_rate': 0.0, 'avg_latency_ms': 0.0, 'avg_cost_usd': 0.0})
        current_model = current_stats['model_stats'].get(model, {'pass_rate': 0.0, 'avg_latency_ms': 0.0, 'avg_cost_usd': 0.0})
        delta = round(current_model['pass_rate'] - baseline_model['pass_rate'], 1)
        is_regression = delta <= -regression_threshold
        comparison['models'][model] = {
            'baseline': baseline_model,
            'current': current_model,
            'deltas': {
                'pass_rate': delta,
                'avg_latency_ms': round(current_model['avg_latency_ms'] - baseline_model['avg_latency_ms'], 1),
                'avg_cost_usd': round(current_model['avg_cost_usd'] - baseline_model['avg_cost_usd'], 6),
            },
            'regression': is_regression,
        }
        if is_regression:
            regressions.append({
                'type': 'model',
                'metric': model,
                'baseline': baseline_model['pass_rate'],
                'current': current_model['pass_rate'],
                'delta': delta,
                'severity': severity(delta),
                'message': f"{model} pass rate dropped by {abs(delta)}%",
            })

    # Overall regression
    overall_delta = comparison['overall']['pass_rate_delta']
    if overall_delta <= -regression_threshold:
        regressions.append({
            'type': 'overall',
            'metric': 'overall_pass_rate',
            'baseline': baseline_stats['pass_rate'],
            'current': current_stats['pass_rate'],
            'delta': overall_delta,
            'severity': severity(overall_delta),
            'message': f"Overall pass rate dropped by {abs(overall_delta)}%",
        })

    return {
        'baseline': {
            'version': baseline_version,
            'run_id': str(baseline_run.id),
            'timestamp': baseline_run.timestamp,
            'stats': baseline_stats,
        },
        'current': {
            'version': current_version,
            'run_id': str(current_run.id),
            'timestamp': current_run.timestamp,
            'stats': current_stats,
        },
        'comparison': comparison,
        'regressions': regressions,
        'has_regressions': len(regressions) > 0,
        'regression_count': len(regressions),
        'threshold': regression_threshold,
    }


@router.get('/refusal-stats')
async def get_refusal_stats(
    limit: int = Query(5, description="Max examples per category"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get refusal evaluator false positive/negative statistics.

    FP = model refused when should_refuse=False (unnecessary refusal)
    FN = model answered when should_refuse=True (missed refusal)
    TP = model refused when should_refuse=True (correct refusal)
    TN = model answered when should_refuse=False (correct answer)
    """
    # Get all refusal evaluator results with their outputs and test cases
    result = await db.execute(
        select(EvaluatorResult, EvaluationOutput, TestCase)
        .join(EvaluationOutput, EvaluatorResult.output_id == EvaluationOutput.id)
        .join(TestCase, EvaluationOutput.test_case_id == TestCase.id)
        .where(EvaluatorResult.evaluator_name == 'refusal_behavior')
    )
    rows = result.all()

    # Classify results
    fp_examples = []  # False Positives: refused when should answer
    fn_examples = []  # False Negatives: answered when should refuse
    tp_examples = []  # True Positives: correctly refused
    tn_examples = []  # True Negatives: correctly answered

    for eval_result, output, test_case in rows:
        # Get refusal details from evaluator
        details = eval_result.details or {}
        model_refused = details.get('refused', False)

        # Determine expected behavior
        should_refuse = getattr(test_case, 'should_refuse', None)
        if should_refuse is None:
            # Infer from category if not explicitly set
            category = (test_case.category or "").lower()
            should_refuse = "safety" in category or "refusal" in category or "policy" in category

        example = {
            'output_id': str(output.id),
            'test_case_id': str(test_case.id),
            'model': output.model,
            'prompt': test_case.prompt[:200] + '...' if len(test_case.prompt) > 200 else test_case.prompt,
            'input': test_case.input[:200] + '...' if len(test_case.input) > 200 else test_case.input,
            'response_preview': (output.model_response or '')[:300] + '...' if len(output.model_response or '') > 300 else output.model_response,
            'refusal_type': details.get('refusal_type'),
            'category': test_case.category,
            'should_refuse': should_refuse,
            'model_refused': model_refused,
        }

        if should_refuse and model_refused:
            tp_examples.append(example)
        elif not should_refuse and not model_refused:
            tn_examples.append(example)
        elif not should_refuse and model_refused:
            fp_examples.append(example)
        elif should_refuse and not model_refused:
            fn_examples.append(example)

    total = len(rows)
    fp_count = len(fp_examples)
    fn_count = len(fn_examples)
    tp_count = len(tp_examples)
    tn_count = len(tn_examples)

    # Calculate rates
    fp_rate = round(fp_count / total * 100, 2) if total > 0 else 0.0
    fn_rate = round(fn_count / total * 100, 2) if total > 0 else 0.0

    # Precision = TP / (TP + FP) - of all refusals, how many were correct
    precision = round(tp_count / (tp_count + fp_count) * 100, 2) if (tp_count + fp_count) > 0 else 0.0
    # Recall = TP / (TP + FN) - of all cases that should refuse, how many did
    recall = round(tp_count / (tp_count + fn_count) * 100, 2) if (tp_count + fn_count) > 0 else 0.0
    # F1 Score
    f1 = round(2 * precision * recall / (precision + recall), 2) if (precision + recall) > 0 else 0.0

    return {
        'total_evaluations': total,
        'counts': {
            'true_positives': tp_count,
            'true_negatives': tn_count,
            'false_positives': fp_count,
            'false_negatives': fn_count,
        },
        'rates': {
            'false_positive_rate': fp_rate,
            'false_negative_rate': fn_rate,
            'precision': precision,
            'recall': recall,
            'f1_score': f1,
        },
        'examples': {
            'false_positives': fp_examples[:limit],
            'false_negatives': fn_examples[:limit],
            'true_positives': tp_examples[:limit],
            'true_negatives': tn_examples[:limit],
        },
        'note': 'FP = refused when should answer, FN = answered when should refuse',
    }
