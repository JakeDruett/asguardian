"""
Local Percentile Calibrator (Plan 05 Phase B).

DEEPTHINK_02's "ultimate evolution": compute this project's own empirical
CDF per metric and derive P90/P95 anchors, guardrailed so a uniformly bad
codebase cannot normalize its own rot.

Pure computation - callers supply the raw per-function/per-file metric
samples (typically from Quality's metric extraction, PRODUCTION context
only via `Bragi.common.context_classifier`, generated excluded). This
module has no scanning/I-O responsibility of its own beyond writing the
resulting profile YAML.
"""

import math
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import yaml

from Asgard.Bragi.Calibration.models.calibration_models import (
    CalibrationRun,
    LanguageProfile,
    ThresholdSpec,
)
from Asgard.Bragi.Calibration.services.profile_service import LOCAL_PROFILE_RELATIVE_PATH

# Guardrails (Plan 05 Sec.3.2).
MIN_SAMPLE_SIZE = 200
CLAMP_FRACTION = 0.5  # local thresholds clamp to +-50% of the language profile value


def percentile(samples: Sequence[float], pct: float) -> float:
    """
    Nearest-rank percentile (pct in [0, 100]) over a sorted copy of `samples`.

    Deterministic: no interpolation-order ambiguity, stable across runs for
    the same input multiset.
    """
    if not samples:
        return 0.0
    ordered = sorted(samples)
    if pct <= 0:
        return ordered[0]
    if pct >= 100:
        return ordered[-1]
    rank = math.ceil((pct / 100.0) * len(ordered))
    rank = max(1, min(rank, len(ordered)))
    return ordered[rank - 1]


def _clamp(local_value: float, anchor_value: float, fraction: float = CLAMP_FRACTION) -> float:
    """Clamp `local_value` to within +-fraction of `anchor_value`.

    Applied at generate time and again when loading a local profile YAML
    (CH-0027): unsigned cache cannot bypass the rot guard.
    """
    if anchor_value <= 0:
        return local_value
    lo = anchor_value * (1.0 - fraction)
    hi = anchor_value * (1.0 + fraction)
    return min(max(local_value, lo), hi)


def clamp_profile_to_anchor(
    local: LanguageProfile,
    anchor: LanguageProfile,
    fraction: float = CLAMP_FRACTION,
) -> LanguageProfile:
    """Re-apply `_clamp` to every local numeric against `anchor`.

    Thresholds/scalars without an anchor pass through unchanged (callers
    must already have schema-validated them). After clamp, `warn` is
    never greater than `fail`.
    """
    thresholds: Dict[str, ThresholdSpec] = {}
    for metric_id, spec in local.thresholds.items():
        if metric_id in anchor.thresholds:
            anchor_spec = anchor.thresholds[metric_id]
            fail = _clamp(spec.fail, anchor_spec.fail, fraction)
            warn = _clamp(spec.warn, anchor_spec.warn, fraction)
            if warn > fail:
                warn = fail
            thresholds[metric_id] = ThresholdSpec(warn=warn, fail=fail)
        else:
            warn, fail = spec.warn, spec.fail
            if warn > fail:
                warn = fail
            thresholds[metric_id] = ThresholdSpec(warn=warn, fail=fail)

    scalars: Dict[str, float] = {}
    for metric_id, value in local.scalar_thresholds.items():
        if metric_id in anchor.scalar_thresholds:
            scalars[metric_id] = _clamp(value, anchor.scalar_thresholds[metric_id], fraction)
        elif metric_id in anchor.thresholds:
            scalars[metric_id] = _clamp(value, anchor.thresholds[metric_id].fail, fraction)
        else:
            scalars[metric_id] = value

    weights = local.category_weights
    if weights and anchor.category_weights:
        clamped_weights: Dict[str, float] = {}
        for key, value in weights.items():
            anchor_w = anchor.category_weights.get(key)
            if anchor_w is not None and anchor_w > 0:
                clamped_weights[key] = _clamp(value, anchor_w, fraction)
            else:
                clamped_weights[key] = value
        weights = clamped_weights

    return LanguageProfile(
        language=local.language,
        provenance=local.provenance,
        thresholds=thresholds,
        scalar_thresholds=scalars,
        severity_confidence=local.severity_confidence,
        category_weights=weights,
    )


def calibrate(
    language: str,
    metric_samples: Dict[str, List[float]],
    anchor_profile: LanguageProfile,
    min_sample_size: int = MIN_SAMPLE_SIZE,
) -> "tuple[Optional[LanguageProfile], CalibrationRun]":
    """
    Compute a local profile from raw metric samples.

    Refuses (returns `(None, run_with_refused=True)`) when every metric's
    sample count is below `min_sample_size` - a partial sample for one
    metric among several measured ones is fine; total starvation is not.

    Each derived P95 anchor is clamped to +-50% of the corresponding
    language-profile threshold's `fail` value (or scalar value) so a
    uniformly bad codebase cannot normalize its own rot into "clean".
    """
    total_samples = sum(len(v) for v in metric_samples.values())
    if total_samples < min_sample_size:
        run = CalibrationRun(
            sample_size=total_samples, language=language, refused=True,
            refusal_reason=(
                f"insufficient sample: {total_samples} data point(s) collected, "
                f"minimum {min_sample_size} required"
            ),
        )
        return None, run

    thresholds: Dict[str, ThresholdSpec] = {}
    scalars: Dict[str, float] = {}
    clamped_metrics: List[str] = []

    for metric_id, samples in metric_samples.items():
        if not samples:
            continue
        p95 = percentile(samples, 95)
        p90 = percentile(samples, 90)

        anchor_fail = None
        if metric_id in anchor_profile.thresholds:
            anchor_fail = anchor_profile.thresholds[metric_id].fail
        elif metric_id in anchor_profile.scalar_thresholds:
            anchor_fail = anchor_profile.scalar_thresholds[metric_id]

        clamped_p95 = p95
        if anchor_fail is not None:
            clamped_p95 = _clamp(p95, anchor_fail)
            if clamped_p95 != p95:
                clamped_metrics.append(metric_id)

        if metric_id in anchor_profile.thresholds:
            warn = p90 if p90 <= clamped_p95 else clamped_p95
            thresholds[metric_id] = ThresholdSpec(warn=warn, fail=clamped_p95)
        else:
            scalars[metric_id] = clamped_p95

    n = total_samples
    profile = LanguageProfile(
        language=language,
        provenance=f"local P95, {datetime.now().date().isoformat()}, n={n}",
        thresholds=thresholds,
        scalar_thresholds=scalars,
    )
    run = CalibrationRun(
        sample_size=n, language=language, refused=False, clamped_metrics=clamped_metrics,
    )
    return profile, run


def _confine_project_path(
    project_path: Optional[Path] = None,
    root: Optional[Path] = None,
) -> Path:
    """Resolve *project_path* to *root* (default cwd) or a descendant.

    Refuses ``..`` in any path component and absolute paths that do not
    resolve under *root*.
    """
    jail = Path(root or Path.cwd()).resolve()
    raw = Path(project_path) if project_path is not None else Path()
    if ".." in raw.parts:
        raise ValueError("project_path must stay under the current working directory")
    candidate = raw if raw.is_absolute() else jail / raw
    try:
        resolved = candidate.resolve()
    except OSError as exc:
        raise ValueError("project_path could not be resolved") from exc
    if not resolved.is_relative_to(jail):
        raise ValueError("project_path must stay under the current working directory")
    return resolved


def write_local_profile(profile: LanguageProfile, project_path: Optional[Path] = None) -> Path:
    """Persist a calibrated profile to `.asgard_cache/bragi_local_profile.yaml`."""
    root = Path.cwd().resolve()
    project_path = _confine_project_path(project_path, root=root)
    dest = project_path / LOCAL_PROFILE_RELATIVE_PATH
    if dest.is_symlink():
        raise ValueError("local profile destination must not be a symlink")
    try:
        resolved_dest = dest.resolve()
    except OSError as exc:
        raise ValueError("local profile destination could not be resolved") from exc
    if not resolved_dest.is_relative_to(root):
        raise ValueError("local profile destination must stay under the current working directory")
    dest.parent.mkdir(parents=True, exist_ok=True)
    payload = profile.model_dump(mode="json", exclude_none=True)
    with open(dest, "w", encoding="utf-8") as f:
        yaml.safe_dump(payload, f, sort_keys=True, default_flow_style=False)
    return dest
