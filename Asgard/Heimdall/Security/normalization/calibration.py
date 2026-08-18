"""
Persisted confidence-calibration map (Heimdall plan 10 s4, concrete
change #3): the normalization engine loads a fitted isotonic map (produced
by ``heimdall eval corpus --save-calibration``) and converts raw heuristic
confidence scores into empirical probabilities BEFORE bucketing.

The map is a trust root: it shifts confidence buckets for every subsequent
scan. Writes and loads are confined to CWD or ``HEIMDALL_CALIBRATION_DIR``.
When ``HEIMDALL_CALIBRATION_HMAC_KEY`` is set, the JSON is HMAC-SHA256
signed on write and verified on load; unsigned or rewritten maps raise.

Invariants:
- Strictly opt-in and file-driven: with no map configured, calibration is
  the identity function -- scanner behaviour is unchanged by default.
- Deterministic: the map is a static JSON file of (raw, calibrated) knot
  pairs; the same input always yields the same output. No network.
- Severity is never touched -- calibration adjusts confidence only.
- Honest labeling: an invalid, unconfined, or HMAC-invalid map file raises
  ``ValueError`` rather than being silently ignored; a silently-dropped
  map would mislabel every confidence bucket downstream.

Map file schema (shared with ``Asgard.Heimdall.evaluation.calibration``):

    {"version": 1, "knots": [[raw, calibrated], ...], "hmac"?: "<hex>"}

with knot x-values strictly increasing in [0, 1] and y-values
non-decreasing in [0, 1].
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Tuple, Union

#: Environment variable naming the default calibration-map file. Unset (the
#: default) means identity calibration everywhere.
CALIBRATION_MAP_ENV = "HEIMDALL_CALIBRATION_MAP"

#: Optional HMAC-SHA256 key for the map (trust root). When set, save signs
#: and load rejects unsigned or rewritten knots.
CALIBRATION_HMAC_ENV = "HEIMDALL_CALIBRATION_HMAC_KEY"

#: Optional jail root for map writes/loads. Unset = process CWD.
CALIBRATION_DIR_ENV = "HEIMDALL_CALIBRATION_DIR"

#: Schema version this loader understands.
CALIBRATION_MAP_VERSION = 1

_JAIL_ERROR = "calibration map path must stay under the calibration directory"
_HMAC_ERROR = "calibration map HMAC is missing or invalid"
_SYMLINK_ERROR = "calibration map path must not be a symlink"


def calibration_jail(jail: Union[str, Path, None] = None) -> Path:
    """Jail root: explicit *jail*, else ``HEIMDALL_CALIBRATION_DIR``, else CWD."""
    if jail is not None:
        return Path(jail).resolve()
    env = os.environ.get(CALIBRATION_DIR_ENV, "").strip()
    if env:
        return Path(env).resolve()
    return Path.cwd().resolve()


def confine_calibration_path(
    path: Union[str, Path],
    *,
    jail: Union[str, Path, None] = None,
) -> Path:
    """Resolve *path* under CWD or an explicit calibration directory.

    Rejects ``..`` components and destinations that resolve outside the
    jail. The map is a trust root; callers must not read or write it
    outside that tree.
    """
    raw = Path(path)
    if not str(raw) or ".." in raw.parts:
        raise ValueError(_JAIL_ERROR)
    root = calibration_jail(jail)
    candidate = raw if raw.is_absolute() else root / raw
    if candidate.is_symlink():
        raise ValueError(_SYMLINK_ERROR)
    try:
        dest = candidate.resolve()
    except OSError as exc:
        raise ValueError("calibration map path could not be resolved") from exc
    if not dest.is_relative_to(root):
        raise ValueError(_JAIL_ERROR)
    return dest


def _hmac_key() -> Optional[bytes]:
    env = os.environ.get(CALIBRATION_HMAC_ENV, "").strip()
    if not env:
        return None
    return env.encode("utf-8")


def _unsigned_payload(data: dict) -> dict:
    return {
        "version": data.get("version"),
        "knots": data.get("knots"),
    }


def _sign_payload(data: dict, key: bytes) -> str:
    canonical = json.dumps(
        _unsigned_payload(data),
        sort_keys=True,
        separators=(",", ":"),
    )
    return hmac.new(key, canonical.encode("utf-8"), hashlib.sha256).hexdigest()


def _verify_hmac(data: dict) -> None:
    """Require a matching HMAC. Unsigned maps are never trusted."""
    key = _hmac_key()
    expected = data.get("hmac")
    if key is None:
        raise ValueError(_HMAC_ERROR)
    if not isinstance(expected, str) or not hmac.compare_digest(
        expected, _sign_payload(data, key)
    ):
        raise ValueError(_HMAC_ERROR)


def write_calibration_map(
    path: Union[str, Path],
    payload: dict,
    *,
    jail: Union[str, Path, None] = None,
) -> Path:
    """Jail *path*, optionally HMAC-sign *payload*, and write mode ``0o600``."""
    dest = confine_calibration_path(path, jail=jail)
    if dest.is_symlink():
        raise ValueError(_SYMLINK_ERROR)
    dest.parent.mkdir(parents=True, exist_ok=True)
    body = {
        "version": payload.get("version"),
        "knots": payload.get("knots"),
    }
    key = _hmac_key()
    if key is not None:
        body["hmac"] = _sign_payload(body, key)
    raw = (json.dumps(body, indent=2, sort_keys=True) + "\n").encode("utf-8")
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(dest, flags, 0o600)
        try:
            os.write(fd, raw)
        finally:
            os.close(fd)
        os.chmod(dest, 0o600)
    except OSError as exc:
        raise ValueError(f"calibration map could not be written: {exc}") from exc
    return dest


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


def load_calibration_map(
    path: Union[str, Path],
    *,
    jail: Union[str, Path, None] = None,
) -> ConfidenceCalibration:
    """Load and validate a persisted calibration map file.

    Confines *path* to CWD or ``HEIMDALL_CALIBRATION_DIR``. When
    ``HEIMDALL_CALIBRATION_HMAC_KEY`` is set, unsigned or rewritten maps
    raise ``ValueError``. Also raises ``ValueError`` (bad content) or
    ``OSError`` (unreadable file).
    """
    file_path = confine_calibration_path(path, jail=jail)
    if file_path.is_symlink():
        raise ValueError(_SYMLINK_ERROR)
    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Calibration map {file_path} is not valid JSON: {exc}")
    if not isinstance(data, dict):
        raise ValueError(f"Calibration map {file_path} must be a JSON object")
    _verify_hmac(data)
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
