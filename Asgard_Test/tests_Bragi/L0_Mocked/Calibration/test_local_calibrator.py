"""Tests for the Plan 05 local percentile calibrator."""

from pathlib import Path

import pytest

from Asgard.Bragi.Calibration.models.calibration_models import LanguageProfile, ThresholdSpec
from Asgard.Bragi.Calibration.services.local_calibrator import (
    MIN_SAMPLE_SIZE,
    calibrate,
    percentile,
    write_local_profile,
)
from Asgard.Bragi.Calibration.services.profile_service import LOCAL_PROFILE_RELATIVE_PATH


class TestPercentile:
    def test_p95_of_known_distribution(self):
        samples = list(range(1, 101))  # 1..100
        assert percentile(samples, 95) == 95

    def test_p50_median(self):
        samples = [1, 2, 3, 4, 5]
        assert percentile(samples, 50) == 3

    def test_empty_samples(self):
        assert percentile([], 95) == 0.0


class TestCalibrate:
    ANCHOR = LanguageProfile(
        language="python",
        thresholds={"cyclomatic_complexity": ThresholdSpec(warn=10, fail=20)},
    )

    def test_refuses_below_minimum_sample(self):
        samples = {"cyclomatic_complexity": [float(i) for i in range(10)]}
        profile, run = calibrate("python", samples, self.ANCHOR)
        assert profile is None
        assert run.refused is True
        assert "insufficient sample" in run.refusal_reason

    def test_accepts_sufficient_sample_and_derives_p95(self):
        samples = {"cyclomatic_complexity": [float(i) for i in range(1, MIN_SAMPLE_SIZE + 1)]}
        profile, run = calibrate("python", samples, self.ANCHOR)
        assert profile is not None
        assert run.refused is False
        assert run.sample_size == MIN_SAMPLE_SIZE
        assert "local P95" in profile.provenance

    def test_clamp_engages_for_pathological_codebase(self):
        # Every function has CC=40, far beyond anchor fail=20; clamp must
        # cap the local threshold at 20 * 1.5 = 30 (not let it normalize
        # to 40 and silently declare the codebase clean).
        samples = {"cyclomatic_complexity": [40.0] * MIN_SAMPLE_SIZE}
        profile, run = calibrate("python", samples, self.ANCHOR)
        assert profile is not None
        assert "cyclomatic_complexity" in run.clamped_metrics
        assert profile.thresholds["cyclomatic_complexity"].fail <= 20 * 1.5 + 1e-9

    def test_determinism_same_input_same_output(self):
        samples = {"cyclomatic_complexity": [float(i % 30) for i in range(MIN_SAMPLE_SIZE)]}
        p1, _ = calibrate("python", samples, self.ANCHOR)
        p2, _ = calibrate("python", samples, self.ANCHOR)
        assert p1.model_dump() == p2.model_dump()


def _calibrated_profile():
    samples = {"cyclomatic_complexity": [float(i) for i in range(1, MIN_SAMPLE_SIZE + 1)]}
    profile, _ = calibrate("python", samples, TestCalibrate.ANCHOR)
    return profile


class TestWriteLocalProfile:
    def test_writes_to_asgard_cache(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        out_path = write_local_profile(_calibrated_profile(), project_path=tmp_path)
        assert out_path.exists()
        assert out_path.name == "bragi_local_profile.yaml"
        assert out_path.parent.name == ".asgard_cache"

    def test_write_under_cwd_still_works(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        out_path = write_local_profile(_calibrated_profile())
        assert out_path.exists()
        assert out_path == tmp_path / LOCAL_PROFILE_RELATIVE_PATH
        assert out_path.read_text(encoding="utf-8")

    def test_project_path_outside_root_raises_and_writes_nothing(self, tmp_path, monkeypatch):
        jail = tmp_path / "jail"
        jail.mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()
        monkeypatch.chdir(jail)
        expected = outside / LOCAL_PROFILE_RELATIVE_PATH
        with pytest.raises(ValueError, match="current working directory"):
            write_local_profile(_calibrated_profile(), project_path=outside)
        assert not expected.exists()
        assert not expected.parent.exists()

    def test_parent_escape_raises(self, tmp_path, monkeypatch):
        jail = tmp_path / "jail"
        jail.mkdir()
        monkeypatch.chdir(jail)
        expected = tmp_path / LOCAL_PROFILE_RELATIVE_PATH
        with pytest.raises(ValueError, match="current working directory"):
            write_local_profile(_calibrated_profile(), project_path=Path(".."))
        with pytest.raises(ValueError, match="current working directory"):
            write_local_profile(_calibrated_profile(), project_path=Path("../outside"))
        assert not expected.exists()

    def test_dest_symlink_is_refused(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cache = tmp_path / ".asgard_cache"
        cache.mkdir()
        target = tmp_path / "elsewhere.yaml"
        target.write_text("untouched\n", encoding="utf-8")
        dest = tmp_path / LOCAL_PROFILE_RELATIVE_PATH
        dest.symlink_to(target)
        with pytest.raises(ValueError, match="symlink"):
            write_local_profile(_calibrated_profile())
        assert dest.is_symlink()
        assert target.read_text(encoding="utf-8") == "untouched\n"
