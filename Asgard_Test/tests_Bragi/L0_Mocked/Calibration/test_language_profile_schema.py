"""CH-0030: LanguageProfile language and numeric fields are constrained."""

import math

import pytest
from pydantic import ValidationError

from Asgard.Bragi.Calibration.models.calibration_models import (
    LanguageProfile,
    ThresholdSpec,
)


def test_language_must_match_shipped_profile_pattern():
    LanguageProfile(language="python")
    with pytest.raises(ValidationError):
        LanguageProfile(language="../etc")
    with pytest.raises(ValidationError):
        LanguageProfile(language="Python")


def test_threshold_must_be_finite_and_ordered():
    ThresholdSpec(warn=1.0, fail=2.0)
    with pytest.raises(ValidationError):
        ThresholdSpec(warn=math.inf, fail=1.0)
    with pytest.raises(ValidationError):
        ThresholdSpec(warn=3.0, fail=1.0)


def test_category_weights_must_be_positive_finite():
    LanguageProfile(language="python", category_weights={"a": 1.5})
    with pytest.raises(ValidationError):
        LanguageProfile(language="python", category_weights={"a": 0})
    with pytest.raises(ValidationError):
        LanguageProfile(language="python", category_weights={"a": float("nan")})
