"""
Language Profile Service (Plan 05 Phase A).

Loader for the YAML profile plane with the documented fallback chain:

    project override (`.asgard_cache/bragi_local_profile.yaml`, Phase B)
        -> language profile (`Bragi/Calibration/profiles/<language>.yaml`)
        -> generic defaults (`Bragi/Calibration/profiles/generic.yaml`)

Missing profile -> generic defaults, never KeyError. Individual missing
thresholds fall through the same chain independently (a local profile that
only overrides `cyclomatic_complexity` still inherits everything else from
the language profile).

The local YAML is unsigned project cache (CH-0027): invalid numerics are
refused entirely; accepted values are re-clamped to +-50% of the
language/generic anchor before they can become the live profile.

Shipped and local YAML that fail schema validation are skipped (CH-0031);
the service still constructs and falls through to generic / in-code defaults.
"""

import logging
import math
from pathlib import Path
from typing import Dict, Optional

import yaml
from pydantic import ValidationError

from Asgard.Bragi.Calibration.models.calibration_models import (
    LANGUAGE_ID_RE,
    LanguageProfile,
    ThresholdSpec,
)

logger = logging.getLogger(__name__)

_PROFILES_DIR = Path(__file__).resolve().parent.parent / "profiles"
_GENERIC_LANGUAGE = "generic"
LOCAL_PROFILE_RELATIVE_PATH = Path(".asgard_cache") / "bragi_local_profile.yaml"
# Unsigned local cache (CH-0027): category weights must stay in (0, 1].
_WEIGHT_MIN_EXCLUSIVE = 0.0
_WEIGHT_MAX = 1.0


def _finite_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _local_override_schema_ok(profile: LanguageProfile) -> bool:
    """Finite numerics, warn <= fail, weight bounds. Fail-closed on anything else."""
    for spec in profile.thresholds.values():
        if not (_finite_number(spec.warn) and _finite_number(spec.fail)):
            return False
        if spec.warn > spec.fail:
            return False
    for value in profile.scalar_thresholds.values():
        if not _finite_number(value):
            return False
    if profile.category_weights:
        for weight in profile.category_weights.values():
            if not _finite_number(weight):
                return False
            if weight <= _WEIGHT_MIN_EXCLUSIVE or weight > _WEIGHT_MAX:
                return False
    return True


def _load_yaml_profile(path: Path) -> Optional[LanguageProfile]:
    """Load a shipped profile YAML. Fail-closed on parse/schema errors (CH-0031)."""
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except (yaml.YAMLError, OSError) as exc:
        logger.warning("skipping unreadable language profile %s: %s", path, exc)
        return None
    if not isinstance(data, dict):
        logger.warning("skipping invalid language profile %s: root is not a mapping", path)
        return None
    try:
        return LanguageProfile.model_validate(data)
    except (TypeError, ValueError, ValidationError) as exc:
        logger.warning("skipping invalid language profile %s: %s", path, exc)
        return None


class LanguageProfileService:
    """
    Resolves per-language thresholds through the fallback chain.

    Usage:
        service = LanguageProfileService(project_path=Path("."))
        cc_warn = service.threshold("python", "cyclomatic_complexity").warn
        wmc = service.scalar("python", "wmc")
    """

    def __init__(
        self,
        project_path: Optional[Path] = None,
        profiles_dir: Optional[Path] = None,
    ):
        self.project_path = Path(project_path or Path.cwd())
        self.profiles_dir = profiles_dir or _PROFILES_DIR
        self._cache: Dict[str, LanguageProfile] = {}
        self._generic = self._load_language(_GENERIC_LANGUAGE) or LanguageProfile(
            language=_GENERIC_LANGUAGE, provenance="in-code fallback (no generic.yaml found)"
        )
        self._local: Optional[LanguageProfile] = self._load_local_override()

    def _load_language(self, language: str) -> Optional[LanguageProfile]:
        if language in self._cache:
            return self._cache[language]
        if not isinstance(language, str) or not LANGUAGE_ID_RE.fullmatch(language):
            return None
        try:
            root = Path(self.profiles_dir).resolve()
            path = (Path(self.profiles_dir) / f"{language}.yaml").resolve()
        except (OSError, ValueError):
            return None
        if not path.is_relative_to(root):
            return None
        profile = _load_yaml_profile(path)
        if profile is not None:
            self._cache[language] = profile
        return profile

    def _anchor_for(self, language: str) -> LanguageProfile:
        """Language profile over generic defaults, with no local override."""
        language_profile = self._load_language(language) or LanguageProfile(
            language=language, provenance="no dedicated profile; using generic defaults"
        )
        merged_thresholds = dict(self._generic.thresholds)
        merged_thresholds.update(language_profile.thresholds)
        merged_scalars = dict(self._generic.scalar_thresholds)
        merged_scalars.update(language_profile.scalar_thresholds)
        merged_severity = dict(self._generic.severity_confidence)
        merged_severity.update(language_profile.severity_confidence)
        return LanguageProfile(
            language=language,
            provenance=language_profile.provenance or self._generic.provenance,
            thresholds=merged_thresholds,
            scalar_thresholds=merged_scalars,
            severity_confidence=merged_severity,
            category_weights=language_profile.category_weights or self._generic.category_weights,
        )

    @staticmethod
    def _clamp_local(local: LanguageProfile, anchor: LanguageProfile) -> LanguageProfile:
        # Lazy: local_calibrator imports LOCAL_PROFILE_RELATIVE_PATH from this module.
        from Asgard.Bragi.Calibration.services.local_calibrator import clamp_profile_to_anchor

        return clamp_profile_to_anchor(local, anchor)

    def _load_local_override(self) -> Optional[LanguageProfile]:
        """Load unsigned project cache; refuse invalid numerics, re-clamp survivors."""
        path = self.project_path / LOCAL_PROFILE_RELATIVE_PATH
        if path.is_symlink() or not path.is_file():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except (yaml.YAMLError, OSError):
            return None
        if not isinstance(data, dict):
            return None
        try:
            profile = LanguageProfile.model_validate(data)
        except (TypeError, ValueError, ValidationError) as exc:
            logger.warning("skipping invalid local profile %s: %s", path, exc)
            return None
        if not isinstance(profile.language, str) or not LANGUAGE_ID_RE.fullmatch(profile.language):
            return None
        if not _local_override_schema_ok(profile):
            return None
        return self._clamp_local(profile, self._anchor_for(profile.language))

    def resolve(self, language: str) -> LanguageProfile:
        """
        Merged profile for a language: local override values win, then the
        language profile, then generic defaults. Never raises - an unknown
        language returns the generic profile relabeled.

        Local YAML is re-clamped to +-50% of this language/generic anchor
        so a planted cache cannot normalize its own rot (CH-0027).
        """
        anchor = self._anchor_for(language)
        if self._local is None:
            return LanguageProfile(
                language=language,
                provenance=anchor.provenance,
                thresholds=dict(anchor.thresholds),
                scalar_thresholds=dict(anchor.scalar_thresholds),
                severity_confidence=dict(anchor.severity_confidence),
                category_weights=anchor.category_weights,
            )

        local = self._clamp_local(self._local, anchor)
        merged_thresholds = dict(anchor.thresholds)
        merged_thresholds.update(local.thresholds)
        merged_scalars = dict(anchor.scalar_thresholds)
        merged_scalars.update(local.scalar_thresholds)
        merged_severity = dict(anchor.severity_confidence)
        merged_severity.update(local.severity_confidence)
        category_weights = local.category_weights or anchor.category_weights
        return LanguageProfile(
            language=language,
            provenance=local.provenance or anchor.provenance,
            thresholds=merged_thresholds,
            scalar_thresholds=merged_scalars,
            severity_confidence=merged_severity,
            category_weights=category_weights,
        )

    def threshold(self, language: str, metric_id: str) -> ThresholdSpec:
        """Resolve a warn/fail threshold, falling through to generic defaults."""
        profile = self.resolve(language)
        if metric_id in profile.thresholds:
            return profile.thresholds[metric_id]
        if metric_id in self._generic.thresholds:
            return self._generic.thresholds[metric_id]
        raise KeyError(f"No threshold '{metric_id}' in any profile (language={language})")

    def scalar(self, language: str, metric_id: str, default: Optional[float] = None) -> Optional[float]:
        """Resolve a scalar threshold; returns `default` (None by default) when absent anywhere."""
        profile = self.resolve(language)
        if metric_id in profile.scalar_thresholds:
            return profile.scalar_thresholds[metric_id]
        return self._generic.scalar_thresholds.get(metric_id, default)
