"""Agreement statistics between human labels and automatic evaluator verdicts."""
import math
from dataclasses import dataclass

# 95% two-sided normal quantile
Z_95 = 1.959963984540054

TRUE_LABELS = {'correct', 'pass', 'passed', 'yes', 'true', 'ok', 'faithful', 'grounded'}
FALSE_LABELS = {'incorrect', 'fail', 'failed', 'no', 'false', 'hallucinated', 'unfaithful'}


def normalize_label(label: str | None) -> bool | None:
    """Map a free-text human label to pass (True) / fail (False), or None if unrecognized."""
    if not label:
        return None
    value = label.strip().lower()
    if value in TRUE_LABELS:
        return True
    if value in FALSE_LABELS:
        return False
    return None


@dataclass
class ConfusionMatrix:
    """Human verdict x evaluator verdict counts (pass = True)."""
    human_pass_auto_pass: int = 0
    human_pass_auto_fail: int = 0
    human_fail_auto_pass: int = 0
    human_fail_auto_fail: int = 0

    def add(self, human: bool, auto: bool) -> None:
        if human and auto:
            self.human_pass_auto_pass += 1
        elif human:
            self.human_pass_auto_fail += 1
        elif auto:
            self.human_fail_auto_pass += 1
        else:
            self.human_fail_auto_fail += 1

    @property
    def n(self) -> int:
        return (self.human_pass_auto_pass + self.human_pass_auto_fail +
                self.human_fail_auto_pass + self.human_fail_auto_fail)

    @property
    def agreed(self) -> int:
        return self.human_pass_auto_pass + self.human_fail_auto_fail


def wilson_interval(successes: int, n: int, z: float = Z_95) -> tuple[float, float] | None:
    """Wilson score interval for a binomial proportion; None when n == 0."""
    if n == 0:
        return None
    p = successes / n
    z2 = z * z
    denom = 1 + z2 / n
    center = (p + z2 / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n)) / denom
    return max(0.0, center - half), min(1.0, center + half)


def cohens_kappa(matrix: ConfusionMatrix) -> float | None:
    """Cohen's kappa; None when n == 0 or chance agreement is 1 (both raters constant)."""
    n = matrix.n
    if n == 0:
        return None
    observed = matrix.agreed / n
    human_pass = matrix.human_pass_auto_pass + matrix.human_pass_auto_fail
    auto_pass = matrix.human_pass_auto_pass + matrix.human_fail_auto_pass
    expected = (human_pass * auto_pass + (n - human_pass) * (n - auto_pass)) / (n * n)
    if expected == 1:
        return None
    return (observed - expected) / (1 - expected)


def summarize(matrix: ConfusionMatrix) -> dict:
    """Reportable agreement summary. Rates are percentages; all are None when n == 0."""
    n = matrix.n
    interval = wilson_interval(matrix.agreed, n)
    kappa = cohens_kappa(matrix)
    return {
        'n': n,
        'agreed': matrix.agreed,
        'agreement': round(matrix.agreed / n * 100, 1) if n else None,
        'agreement_ci_95': (
            {'low': round(interval[0] * 100, 1), 'high': round(interval[1] * 100, 1)}
            if interval else None
        ),
        'kappa': round(kappa, 3) if kappa is not None else None,
        'confusion_matrix': {
            'human_pass_auto_pass': matrix.human_pass_auto_pass,
            'human_pass_auto_fail': matrix.human_pass_auto_fail,
            'human_fail_auto_pass': matrix.human_fail_auto_pass,
            'human_fail_auto_fail': matrix.human_fail_auto_fail,
        },
    }
