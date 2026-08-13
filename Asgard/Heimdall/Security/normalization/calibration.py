"""
Persisted confidence-calibration map (Heimdall plan 10 s4, concrete
change #3): the normalization engine loads a fitted isotonic map (produced
by ``heimdall eval corpus --save-calibration``) and converts raw heuristic
confidence scores into empirical probabilities BEFORE bucketing.

Invariants:
- Strictly opt-in and file-driven: with no map configured, calibration is
  the identity function -- scanner behaviour is unchanged by default.
- Deterministic: the map is a static JSON file of (raw, calibrated) knot
  pairs; the same input always yields the same output. No network.
- Severity is never touched -- calibration adjusts confidence only.
- Honest labeling: an invalid or non-monotonic map file raises
  ``ValueError`` rather than being silently ignored; a silently-dropped
  map would mislabel every confidence bucket downstream.

Map file schema (shared with ``Asgard.Heimdall.evaluation.calibration``):

    {"version": 1, "knots": [[raw, calibrated], ...]}

with knot x-values strictly increasing in [0, 1] and y-values
non-decreasing in [0, 1].
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Tuple, Union

#: Environment variable naming the default calibration-map file. Unset (the
#: default) means identity calibration everywhere.
CALIBRATION_MAP_ENV = "HEIMDALL_CALIBRATION_MAP"

#: Schema version this loader understands.
CALIBRATION_MAP_VERSION = 1


@dataclass(frozen=True)
class ConfidenceCalibration:
    """Immutable monotonic raw-confidence -> probability map.

    ``apply`` uses the same step/linear interpolation as
    ``IsotonicCalibrator.predict``: clamp below the first knot and above
    the last, linear interpolation between bracketing knots.
    """

    knots_x: Tuple[float, ...]
    knots_y: Tuple[float, ...]

    def apply(self, raw_score: float) -> float:
        xs, ys = self.knots_x, self.knots_y
        if not xs:
            return float(raw_score)
        r = float(raw_score)
        if r <= xs[0]:
            return ys[0]
        if r >= xs[-1]:
            return ys[-1]
        lo, hi = 0, len(xs) - 1
        while lo < hi - 1:
            mid = (lo + hi) // 2
            if xs[mid] <= r:
                lo = mid
            else:
                hi = mid
        x0, x1 = xs[lo], xs[hi]
        y0, y1 = ys[lo], ys[hi]
        if x1 == x0:
            return y0
        t = (r - x0) / (x1 - x0)
        return y0 + t * (y1 - y0)

    def to_payload(self) -> dict:
        """JSON-serializable map payload (the persisted schema)."""
        return {
            "version": CALIBRATION_MAP_VERSION,
            "knots": [[x, y] for x, y in zip(self.knots_x, self.knots_y)],
        }


def calibration_from_knots(
    knots: Sequence[Sequence[float]],
) -> ConfidenceCalibration:
    """Validate raw knot pairs and build a :class:`ConfidenceCalibration`.

    Raises ``ValueError`` on empty, out-of-range, non-increasing-x, or
    decreasing-y knots -- a corrupt map must never be silently applied.
    """
    if not knots:
        raise ValueError("Calibration map has no knots")
    xs: List[float] = []
    ys: List[float] = []
    for i, pair in enumerate(knots):
        if len(pair) != 2:
            raise ValueError(f"Calibration knot {i} is not a [raw, calibrated] pair")
        x, y = float(pair[0]), float(pair[1])
        if not (0.0 <= x <= 1.0) or not (0.0 <= y <= 1.0):
            raise ValueError(
                f"Calibration knot {i} out of [0, 1] range: ({x}, {y})"
            )
        if xs and x <= xs[-1]:
            raise ValueError(
                f"Calibration knot x-values must be strictly increasing "
                f"(knot {i}: {x} <= {xs[-1]})"
            )
        if ys and y < ys[-1]:
            raise ValueError(
                f"Calibration map must be non-decreasing "
                f"(knot {i}: {y} < {ys[-1]})"
            )
        xs.append(x)
        ys.append(y)
    return ConfidenceCalibration(knots_x=tuple(xs), knots_y=tuple(ys))


def load_calibration_map(path: Union[str, Path]) -> ConfidenceCalibration:
    """Load and validate a persisted calibration map file.

    Raises ``ValueError`` (bad content) or ``OSError`` (unreadable file).
    """
    file_path = Path(path)
    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Calibration map {file_path} is not valid JSON: {exc}")
    if not isinstance(data, dict):
        raise ValueError(f"Calibration map {file_path} must be a JSON object")
    version = data.get("version")
    if version != CALIBRATION_MAP_VERSION:
        raise ValueError(
            f"Calibration map {file_path} has unsupported version {version!r} "
            f"(expected {CALIBRATION_MAP_VERSION})"
        )
    knots = data.get("knots")
    if not isinstance(knots, list):
        raise ValueError(f"Calibration map {file_path} is missing 'knots' list")
    try:
        return calibration_from_knots(knots)
    except ValueError as exc:
        raise ValueError(f"Calibration map {file_path}: {exc}")


# Module-level cache: (resolved env value or None) -> calibration or None.
_default_cache: List[Tuple[Optional[str], Optional[ConfidenceCalibration]]] = []


def default_calibration() -> Optional[ConfidenceCalibration]:
    """Calibration named by ``HEIMDALL_CALIBRATION_MAP``, or ``None``.

    The loaded map is cached per env value; changing the env variable in
    the same process picks up the new file. Errors propagate -- an
    explicitly configured but broken map must fail loudly.
    """
    env_value = os.environ.get(CALIBRATION_MAP_ENV) or None
    if _default_cache and _default_cache[0][0] == env_value:
        return _default_cache[0][1]
    calibration = load_calibration_map(env_value) if env_value else None
    _default_cache.clear()
    _default_cache.append((env_value, calibration))
    return calibration


def calibrate_confidence(
    raw_confidence: Optional[float],
    calibration: Optional[ConfidenceCalibration] = None,
) -> Optional[float]:
    """Convert a raw heuristic confidence into a calibrated probability.

    - ``None`` confidence passes through untouched (unknown stays unknown;
      unresolved is never made confidently clean).
    - With no calibration configured (arg and env both absent), this is
      the identity function.
    - Output is clamped to [0, 1].
    """
    if raw_confidence is None:
        return None
    cal = calibration if calibration is not None else default_calibration()
    if cal is None:
        return float(raw_confidence)
    return max(0.0, min(1.0, cal.apply(float(raw_confidence))))
