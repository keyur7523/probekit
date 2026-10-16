"""Decide whether a pass-rate change between two runs is a real regression."""
import math

# Minimum results per side before a change is judged at all
MIN_SAMPLES = 20
# Two-sided significance level for the two-proportion z-test
ALPHA = 0.05

REGRESSED = 'regressed'
IMPROVED = 'improved'
NO_SIGNIFICANT_CHANGE = 'no_significant_change'
INSUFFICIENT_DATA = 'insufficient_data'


def two_proportion_p_value(passed_a: int, total_a: int, passed_b: int, total_b: int) -> float:
    """Two-sided p-value of a pooled two-proportion z-test."""
    pooled = (passed_a + passed_b) / (total_a + total_b)
    se = math.sqrt(pooled * (1 - pooled) * (1 / total_a + 1 / total_b))
    if se == 0:
        # Both runs all-pass or all-fail: identical proportions
        return 1.0
    z = (passed_b / total_b - passed_a / total_a) / se
    return math.erfc(abs(z) / math.sqrt(2))


def assess_change(
    baseline_passed: int,
    baseline_total: int,
    current_passed: int,
    current_total: int,
    min_samples: int = MIN_SAMPLES,
    alpha: float = ALPHA,
) -> dict:
    """Classify a baseline -> current pass-rate change.

    Returns the status, the two-sided p-value (None when not tested) and both sample sizes.
    """
    result = {
        'status': INSUFFICIENT_DATA,
        'p_value': None,
        'baseline_n': baseline_total,
        'current_n': current_total,
    }
    if baseline_total < min_samples or current_total < min_samples:
        return result

    p_value = two_proportion_p_value(baseline_passed, baseline_total, current_passed, current_total)
    result['p_value'] = round(p_value, 4)
    if p_value >= alpha:
        result['status'] = NO_SIGNIFICANT_CHANGE
    elif current_passed / current_total < baseline_passed / baseline_total:
        result['status'] = REGRESSED
    else:
        result['status'] = IMPROVED
    return result
