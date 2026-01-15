from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from app.evaluators.base import EvaluatorOutput


@dataclass
class VerbosityThresholds:
    max_drift_slope: float = 3.0
    max_growth_ratio: float = 1.2
    max_stddev_ratio: float = 0.35
    max_fallback_rate: float = 0.15


def _linear_regression_slope(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    xs = list(range(len(values)))
    x_mean = sum(xs) / len(xs)
    y_mean = sum(values) / len(values)
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, values))
    denominator = sum((x - x_mean) ** 2 for x in xs)
    return numerator / denominator if denominator else 0.0


def compute_verbosity_metrics(output_tokens: Sequence[int], start_index: int = 0) -> dict[str, float]:
    tokens = list(output_tokens[start_index:]) if output_tokens else []
    if not tokens:
        return {
            "mean_tokens_per_turn": 0.0,
            "drift_slope": 0.0,
            "length_stddev": 0.0,
            "growth_ratio": 0.0,
        }

    mean = sum(tokens) / len(tokens)
    variance = sum((val - mean) ** 2 for val in tokens) / len(tokens)
    stddev = variance ** 0.5
    drift_slope = _linear_regression_slope([float(val) for val in tokens])

    first_window = tokens[:3]
    last_window = tokens[-3:]
    first_avg = sum(first_window) / len(first_window)
    last_avg = sum(last_window) / len(last_window)
    growth_ratio = (last_avg / first_avg) if first_avg else 0.0

    return {
        "mean_tokens_per_turn": round(mean, 3),
        "drift_slope": round(drift_slope, 3),
        "length_stddev": round(stddev, 3),
        "growth_ratio": round(growth_ratio, 3),
    }


def evaluate_verbosity_stability(
    output_tokens: Sequence[int],
    fallback_used: Sequence[bool],
    thresholds: VerbosityThresholds | None = None,
) -> EvaluatorOutput:
    thresholds = thresholds or VerbosityThresholds()
    metrics_all = compute_verbosity_metrics(output_tokens, start_index=0)
    metrics = compute_verbosity_metrics(output_tokens, start_index=1)

    mean_tokens = metrics["mean_tokens_per_turn"]
    stddev_limit = thresholds.max_stddev_ratio * mean_tokens if mean_tokens else 0.0
    fallback_rate = (sum(1 for val in fallback_used if val) / len(fallback_used)) if fallback_used else 0.0

    checks = {
        "drift_slope": metrics["drift_slope"] <= thresholds.max_drift_slope,
        "growth_ratio": metrics["growth_ratio"] <= thresholds.max_growth_ratio,
        "length_stddev": metrics["length_stddev"] <= stddev_limit,
        "fallback_rate": fallback_rate <= thresholds.max_fallback_rate,
    }

    passed = all(checks.values())
    score = round(sum(1 for value in checks.values() if value) / len(checks), 3)

    return EvaluatorOutput(
        evaluator_name="verbosity_stability",
        passed=passed,
        score=score,
        details={
            "metrics": metrics,
            "metrics_all_turns": metrics_all,
            "metrics_start_index": 1,
            "fallback_rate": round(fallback_rate, 3),
            "thresholds": {
                "max_drift_slope": thresholds.max_drift_slope,
                "max_growth_ratio": thresholds.max_growth_ratio,
                "max_stddev_ratio": thresholds.max_stddev_ratio,
                "max_fallback_rate": thresholds.max_fallback_rate,
            },
            "checks": checks,
        },
        reasoning="All verbosity thresholds satisfied" if passed else "One or more verbosity thresholds failed",
    )
