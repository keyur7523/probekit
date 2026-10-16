"""Latency percentiles interpolate between ranks (hand-computed fixtures)."""

import pytest

from app.api.dashboard import _calculate_percentile

LATENCIES = [2810, 3014, 3808, 4056, 6951]


def test_p99_interpolates_toward_the_slowest_value():
    # rank = 0.99 * 4 = 3.96 -> 4056 + 0.96 * (6951 - 4056) = 6835.2
    # (previously truncated to rank 3 -> 4056, below the 4127.8 mean)
    assert _calculate_percentile(LATENCIES, 0.99) == pytest.approx(6835.2)


def test_p50_is_the_median():
    assert _calculate_percentile(LATENCIES, 0.50) == 3808.0
    assert _calculate_percentile([100, 200], 0.50) == 150.0


def test_bounds_and_edge_cases():
    assert _calculate_percentile(LATENCIES, 0.0) == 2810.0
    assert _calculate_percentile(LATENCIES, 1.0) == 6951.0
    assert _calculate_percentile([500], 0.99) == 500.0
    assert _calculate_percentile([], 0.99) == 0.0


def test_matches_numpy_linear_method():
    values = sorted([12, 7, 45, 3, 3, 28, 19, 90, 61, 33])
    # numpy.percentile(values, [10, 25, 90, 99]) with method="linear"
    expected = {0.10: 3.0, 0.25: 8.25, 0.90: 63.9, 0.99: 87.39}
    for p, value in expected.items():
        assert _calculate_percentile(values, p) == pytest.approx(value)
