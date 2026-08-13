"""
Plan 10 s4 residual: persisted calibration map — save/load round-trip,
validation, and application by the normalization engine before bucketing.
"""

import json

import pytest

from Asgard.Heimdall.evaluation.calibration import (
    IsotonicCalibrator,
    load_calibrator,
)
from Asgard.Heimdall.Security.normalization.calibration import (
    CALIBRATION_MAP_ENV,
    CALIBRATION_MAP_VERSION,
    ConfidenceCalibration,
    calibrate_confidence,
    calibration_from_knots,
    default_calibration,
    load_calibration_map,
)
from Asgard.Heimdall.Security.normalization.priority import confidence_bucket


@pytest.fixture(autouse=True)
def _clear_env_and_cache(monkeypatch):
    monkeypatch.delenv(CALIBRATION_MAP_ENV, raising=False)
    from Asgard.Heimdall.Security.normalization import calibration as mod
    mod._default_cache.clear()
    yield
    mod._default_cache.clear()


def _overconfident_records():
    # Scorer says 0.9 but only ~50% are true positives.
    records = []
    for i in range(20):
        records.append((0.9, i % 2 == 0))
    for i in range(20):
        records.append((0.2, i % 10 == 0))
    return records


class TestRoundTrip:
    def test_save_load_roundtrip_predictions_match(self, tmp_path):
        records = _overconfident_records()
        cal = IsotonicCalibrator().fit(
            [r[0] for r in records], [r[1] for r in records]
        )
        path = tmp_path / "map.json"
        cal.save_map(path)

        loaded = load_calibrator(path)
        for raw in (0.0, 0.1, 0.2, 0.5, 0.9, 1.0):
            assert loaded.predict(raw) == pytest.approx(cal.predict(raw))

        norm_map = load_calibration_map(path)
        for raw in (0.0, 0.3, 0.9):
            assert norm_map.apply(raw) == pytest.approx(cal.predict(raw))

    def test_saved_schema(self, tmp_path):
        records = _overconfident_records()
        cal = IsotonicCalibrator().fit(
            [r[0] for r in records], [r[1] for r in records]
        )
        path = tmp_path / "map.json"
        cal.save_map(path)
        data = json.loads(path.read_text())
        assert data["version"] == CALIBRATION_MAP_VERSION
        assert all(len(k) == 2 for k in data["knots"])

    def test_unfitted_save_refused(self, tmp_path):
        with pytest.raises(ValueError):
            IsotonicCalibrator().save_map(tmp_path / "empty.json")

    def test_from_map(self):
        cal = IsotonicCalibrator.from_map([(0.2, 0.1), (0.9, 0.5)])
        assert cal.predict(0.9) == pytest.approx(0.5)
        assert cal.predict(0.05) == pytest.approx(0.1)  # clamp below


class TestValidation:
    def test_empty_knots_rejected(self):
        with pytest.raises(ValueError):
            calibration_from_knots([])

    def test_non_increasing_x_rejected(self):
        with pytest.raises(ValueError):
            calibration_from_knots([[0.5, 0.3], [0.5, 0.4]])

    def test_decreasing_y_rejected(self):
        with pytest.raises(ValueError):
            calibration_from_knots([[0.2, 0.5], [0.8, 0.3]])

    def test_out_of_range_rejected(self):
        with pytest.raises(ValueError):
            calibration_from_knots([[0.2, 1.5]])

    def test_bad_version_rejected(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text(json.dumps({"version": 99, "knots": [[0.1, 0.1]]}))
        with pytest.raises(ValueError):
            load_calibration_map(path)

    def test_invalid_json_rejected(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("{not json")
        with pytest.raises(ValueError):
            load_calibration_map(path)


class TestApplication:
    def test_identity_without_map(self):
        assert calibrate_confidence(0.73) == pytest.approx(0.73)
        assert calibrate_confidence(None) is None
        assert default_calibration() is None

    def test_explicit_calibration_applied(self):
        cal = ConfidenceCalibration(knots_x=(0.2, 0.9), knots_y=(0.1, 0.5))
        # Overconfident 0.9 raw becomes 0.5 calibrated -> bucket drops
        # from "certain" to "probable".
        calibrated = calibrate_confidence(0.9, cal)
        assert calibrated == pytest.approx(0.5)
        assert confidence_bucket(0.9) == "certain"
        assert confidence_bucket(calibrated) == "probable"

    def test_interpolation_between_knots(self):
        cal = ConfidenceCalibration(knots_x=(0.0, 1.0), knots_y=(0.0, 0.5))
        assert cal.apply(0.5) == pytest.approx(0.25)

    def test_env_map_picked_up_and_cached(self, tmp_path, monkeypatch):
        path = tmp_path / "map.json"
        path.write_text(json.dumps(
            {"version": 1, "knots": [[0.0, 0.0], [1.0, 0.5]]}
        ))
        monkeypatch.setenv(CALIBRATION_MAP_ENV, str(path))
        assert calibrate_confidence(1.0) == pytest.approx(0.5)
        # Cached instance reused for the same env value.
        assert default_calibration() is default_calibration()

    def test_env_broken_map_fails_loudly(self, tmp_path, monkeypatch):
        path = tmp_path / "broken.json"
        path.write_text("[]")
        monkeypatch.setenv(CALIBRATION_MAP_ENV, str(path))
        with pytest.raises(ValueError):
            calibrate_confidence(0.5)

    def test_output_clamped(self):
        cal = ConfidenceCalibration(knots_x=(0.0, 1.0), knots_y=(0.0, 1.0))
        assert calibrate_confidence(1.7, cal) == 1.0
        assert calibrate_confidence(-0.5, cal) == 0.0


class TestDispatchWiring:
    def test_dispatch_entry_buckets_calibrated(self, tmp_path, monkeypatch):
        from Asgard.Heimdall.cli.handlers._security_dispatch import _entry

        path = tmp_path / "map.json"
        path.write_text(json.dumps(
            {"version": 1, "knots": [[0.0, 0.0], [1.0, 0.5]]}
        ))
        monkeypatch.setenv(CALIBRATION_MAP_ENV, str(path))
        from Asgard.Heimdall.Security.normalization import calibration as mod
        mod._default_cache.clear()

        entry = _entry(
            rule_id="r", severity="high", confidence=0.95,
            file_path="a.py", line=1, message="m", cwe="CWE-1",
            context_tag="production", modifier=1.0,
        )
        # Raw 0.95 would be "certain"; calibrated 0.475 is "possible".
        assert entry["confidence"].lower().startswith("possible")

    def test_dispatch_entry_identity_without_map(self):
        from Asgard.Heimdall.cli.handlers._security_dispatch import _entry
        entry = _entry(
            rule_id="r", severity="high", confidence=0.95,
            file_path="a.py", line=1, message="m", cwe="CWE-1",
            context_tag="production", modifier=1.0,
        )
        assert entry["confidence"].lower().startswith("certain")
