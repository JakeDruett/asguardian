"""
Confidence calibration (plan 10 s4): reliability diagrams, isotonic
regression via Pool Adjacent Violators (PAVA), and Brier score. Pure
stdlib -- no numpy/sklearn, per the plan's explicit constraint.

Pipeline (DEEPTHINK_03 s5):
    1. Run the engine over the corpus; record (raw_confidence, ground_truth).
    2. ``reliability_diagram`` bins scores into deciles and reports
       predicted vs. empirical TP rate per bin -- perfect calibration is
       the y=x line.
    3. If monotonic-but-miscalibrated, ``IsotonicCalibrator.fit`` produces
       a non-decreasing raw -> true-probability map (PAVA), which
       ``predict`` applies via step-function interpolation.
    4. ``brier_score`` is the objective KPI: mean squared error of
       probability vs. binary outcome. A new/changed rule must not
       worsen it on the corpus (enforced by ``gate.py``).

Persisted maps (``save_map`` / ``load_calibrator``) are a trust root:
they shift scan confidence buckets. Writes and loads stay under CWD or
``HEIMDALL_CALIBRATION_DIR`` and are HMAC-signed when
``HEIMDALL_CALIBRATION_HMAC_KEY`` is set.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence, Tuple


@dataclass(frozen=True)
class ReliabilityBin:
    lower: float
    upper: float
    count: int
    predicted_mean: float
    empirical_rate: float


def reliability_diagram(
    records: Sequence[Tuple[float, bool]], n_bins: int = 10
) -> List[ReliabilityBin]:
    """Bin ``(raw_confidence, is_true_positive)`` records into ``n_bins``
    equal-width deciles over [0, 1] and report predicted-mean vs.
    empirical-TP-rate per bin. Empty bins are omitted."""
    if n_bins <= 0:
        raise ValueError("n_bins must be positive")
    width = 1.0 / n_bins
    buckets: List[List[Tuple[float, bool]]] = [[] for _ in range(n_bins)]
    for score, label in records:
        s = min(max(score, 0.0), 1.0)
        idx = min(int(s / width), n_bins - 1)
        buckets[idx].append((score, label))

    result: List[ReliabilityBin] = []
    for i, bucket in enumerate(buckets):
        if not bucket:
            continue
        count = len(bucket)
        predicted_mean = sum(s for s, _ in bucket) / count
        empirical_rate = sum(1 for _, y in bucket if y) / count
        result.append(
            ReliabilityBin(
                lower=i * width,
                upper=(i + 1) * width,
                count=count,
                predicted_mean=predicted_mean,
                empirical_rate=empirical_rate,
            )
        )
    return result


def brier_score(records: Sequence[Tuple[float, bool]]) -> float:
    """Mean squared error of predicted probability vs. binary outcome.
    Lower is better; 0.0 is perfect, 1.0 is maximally wrong. Empty input
    is defined as 0.0 (no evidence of miscalibration)."""
    if not records:
        return 0.0
    total = 0.0
    for score, label in records:
        y = 1.0 if label else 0.0
        total += (score - y) ** 2
    return total / len(records)


def isotonic_regression(
    x: Sequence[float], y: Sequence[float], weights: Sequence[float] = None
) -> List[float]:
    """Pool Adjacent Violators Algorithm: the non-decreasing sequence of
    fitted values (in ``x``-sorted order) minimizing weighted squared
    error against ``y``. Returns fitted values aligned to the sorted
    order of ``x`` (caller re-sorts back to original order if needed).

    Pure-Python O(n) PAVA using a stack of (value, weight, count) pool
    blocks.
    """
    n = len(x)
    if n == 0:
        return []
    if weights is None:
        weights = [1.0] * n

    order = sorted(range(n), key=lambda i: x[i])
    ys = [y[i] for i in order]
    ws = [weights[i] for i in order]

    # Each stack entry: [weighted_mean, total_weight, block_length]
    stack: List[List[float]] = []
    for yi, wi in zip(ys, ws):
        block = [yi, wi, 1]
        stack.append(block)
        while len(stack) > 1 and stack[-2][0] > stack[-1][0]:
            prev = stack.pop()
            cur = stack.pop()
            merged_weight = prev[1] + cur[1]
            merged_mean = (prev[0] * prev[1] + cur[0] * cur[1]) / merged_weight
            stack.append([merged_mean, merged_weight, prev[2] + cur[2]])

    fitted_sorted: List[float] = []
    for mean, _weight, length in stack:
        fitted_sorted.extend([mean] * length)

    # Re-map back to original order.
    fitted = [0.0] * n
    for pos, orig_idx in enumerate(order):
        fitted[orig_idx] = fitted_sorted[pos]
    return fitted


class IsotonicCalibrator:
    """Fits a monotonic raw-confidence -> empirical-probability map via
    PAVA and applies it to new raw scores by step-function lookup
    (nearest fitted knot at or below the query, else linear interpolation
    between neighboring knots)."""

    def __init__(self) -> None:
        self._knots_x: List[float] = []
        self._knots_y: List[float] = []

    def fit(self, raw_scores: Sequence[float], labels: Sequence[bool]) -> "IsotonicCalibrator":
        y = [1.0 if lbl else 0.0 for lbl in labels]
        fitted = isotonic_regression(list(raw_scores), y)
        pairs = sorted(zip(raw_scores, fitted), key=lambda p: p[0])
        # Collapse duplicate x's (PAVA already makes y non-decreasing).
        xs: List[float] = []
        ys: List[float] = []
        for xv, yv in pairs:
            if xs and xs[-1] == xv:
                continue
            xs.append(xv)
            ys.append(yv)
        self._knots_x = xs
        self._knots_y = ys
        return self

    def predict(self, raw_score: float) -> float:
        if not self._knots_x:
            return raw_score
        xs, ys = self._knots_x, self._knots_y
        if raw_score <= xs[0]:
            return ys[0]
        if raw_score >= xs[-1]:
            return ys[-1]
        # Binary search for the bracketing interval.
        lo, hi = 0, len(xs) - 1
        while lo < hi - 1:
            mid = (lo + hi) // 2
            if xs[mid] <= raw_score:
                lo = mid
            else:
                hi = mid
        x0, x1 = xs[lo], xs[hi]
        y0, y1 = ys[lo], ys[hi]
        if x1 == x0:
            return y0
        t = (raw_score - x0) / (x1 - x0)
        return y0 + t * (y1 - y0)

    def to_map(self) -> List[Tuple[float, float]]:
        """Serializable (raw, calibrated) knot pairs, e.g. for persisting
        the fitted map alongside a rule-version manifest."""
        return list(zip(self._knots_x, self._knots_y))

    @classmethod
    def from_map(cls, knots: Sequence[Tuple[float, float]]) -> "IsotonicCalibrator":
        """Rebuild a calibrator from persisted ``to_map()`` knot pairs.

        Validation (monotonicity, range) is delegated to the shared
        normalization-side loader so both consumers reject the same
        corrupt maps.
        """
        from Asgard.Heimdall.Security.normalization.calibration import (
            calibration_from_knots,
        )
        validated = calibration_from_knots(list(knots))
        calibrator = cls()
        calibrator._knots_x = list(validated.knots_x)
        calibrator._knots_y = list(validated.knots_y)
        return calibrator

    def save_map(self, path, *, jail=None) -> None:
        """Persist the fitted map as the shared JSON schema
        (``{"version": 1, "knots": [[raw, calibrated], ...]}``) consumed by
        ``Asgard.Heimdall.Security.normalization.calibration``.

        The map is a trust root. *path* must stay under CWD or
        ``HEIMDALL_CALIBRATION_DIR`` (or *jail*). When
        ``HEIMDALL_CALIBRATION_HMAC_KEY`` is set, the file is HMAC-signed.

        Refuses to persist an unfitted (empty) calibrator -- an empty map
        would fail loading anyway, and silently writing one would look
        like a successful calibration run.
        """
        from Asgard.Heimdall.Security.normalization.calibration import (
            CALIBRATION_MAP_VERSION,
            write_calibration_map,
        )
        if not self._knots_x:
            raise ValueError("Cannot save an unfitted calibrator (no knots)")
        payload = {
            "version": CALIBRATION_MAP_VERSION,
            "knots": [[x, y] for x, y in zip(self._knots_x, self._knots_y)],
        }
        write_calibration_map(path, payload, jail=jail)


def load_calibrator(path, *, jail=None) -> IsotonicCalibrator:
    """Load a persisted calibration-map file back into a calibrator.

    Same jail and HMAC rules as ``load_calibration_map``: the map is a
    trust root.
    """
    from Asgard.Heimdall.Security.normalization.calibration import (
        load_calibration_map,
    )
    loaded = load_calibration_map(path, jail=jail)
    return IsotonicCalibrator.from_map(list(zip(loaded.knots_x, loaded.knots_y)))
