"""Tests for the Plan 05 language-profile fallback chain."""

import math
import textwrap

import pytest

from Asgard.Bragi.Calibration.services.profile_service import LanguageProfileService


class TestFallbackChain:
    def test_known_language_resolves(self):
        service = LanguageProfileService()
        profile = service.resolve("python")
        assert profile.language == "python"
        assert "cyclomatic_complexity" in profile.thresholds

    def test_unknown_language_falls_back_to_generic_never_keyerror(self):
        service = LanguageProfileService()
        profile = service.resolve("cobol")
        assert profile.language == "cobol"
        assert "cyclomatic_complexity" in profile.thresholds  # inherited from generic

    def test_threshold_lookup_never_raises_for_known_metric(self):
        service = LanguageProfileService()
        spec = service.threshold("python", "cyclomatic_complexity")
        assert spec.warn == 10

    def test_threshold_lookup_raises_for_truly_unknown_metric(self):
        service = LanguageProfileService()
        with pytest.raises(KeyError):
            service.threshold("python", "nonexistent_metric_xyz")

    def test_scalar_lookup_returns_default_when_absent(self):
        service = LanguageProfileService()
        assert service.scalar("python", "nonexistent_scalar", default=42.0) == 42.0

    def test_go_has_wider_thresholds_than_python(self):
        service = LanguageProfileService()
        go_cc = service.threshold("go", "cyclomatic_complexity")
        py_cc = service.threshold("python", "cyclomatic_complexity")
        assert go_cc.warn > py_cc.warn

    @pytest.mark.parametrize(
        "language", ["java", "csharp", "cpp", "ruby", "php", "rust", "shell"]
    )
    def test_new_language_profile_loads_and_resolves(self, language):
        service = LanguageProfileService()
        profile = service.resolve(language)
        assert profile.language == language
        assert "cyclomatic_complexity" in profile.thresholds
        assert "cognitive_complexity" in profile.thresholds
        assert profile.scalar_thresholds.get("wmc") is not None
        assert profile.provenance  # never blank - always carries provenance

    def test_rust_has_wider_thresholds_than_generic_like_go(self):
        service = LanguageProfileService()
        rust_cc = service.threshold("rust", "cyclomatic_complexity")
        py_cc = service.threshold("python", "cyclomatic_complexity")
        assert rust_cc.warn > py_cc.warn

    def test_shell_has_tighter_thresholds_than_generic(self):
        service = LanguageProfileService()
        shell_cc = service.threshold("shell", "cyclomatic_complexity")
        py_cc = service.threshold("python", "cyclomatic_complexity")
        assert shell_cc.warn < py_cc.warn

    def test_java_and_csharp_statically_compiled_dead_code_confidence_is_high(self):
        service = LanguageProfileService()
        java_profile = service.resolve("java")
        csharp_profile = service.resolve("csharp")
        assert java_profile.severity_confidence["global_dead_code"] == "HIGH"
        assert csharp_profile.severity_confidence["global_dead_code"] == "HIGH"

    def test_ruby_and_php_dynamic_dead_code_confidence_is_low(self):
        service = LanguageProfileService()
        ruby_profile = service.resolve("ruby")
        php_profile = service.resolve("php")
        assert ruby_profile.severity_confidence["global_dead_code"] == "LOW"
        assert php_profile.severity_confidence["global_dead_code"] == "LOW"


def _plant_local_profile(tmp_path, body: str) -> None:
    cache_dir = tmp_path / ".asgard_cache"
    cache_dir.mkdir()
    (cache_dir / "bragi_local_profile.yaml").write_text(textwrap.dedent(body), encoding="utf-8")


class TestLocalOverride:
    def test_local_profile_overrides_language_profile(self, tmp_path):
        _plant_local_profile(tmp_path, """\
            language: local
            provenance: "local P95, 2026-01-01, n=500"
            thresholds:
              cyclomatic_complexity: {warn: 8, fail: 16}
        """)
        service = LanguageProfileService(project_path=tmp_path)
        profile = service.resolve("python")
        assert profile.thresholds["cyclomatic_complexity"].warn == 8
        assert "local P95" in profile.provenance
        # Untouched metrics still inherit from the language profile.
        assert "cognitive_complexity" in profile.thresholds

    def test_no_local_profile_is_a_noop(self, tmp_path):
        service = LanguageProfileService(project_path=tmp_path)
        profile = service.resolve("python")
        assert profile.thresholds["cyclomatic_complexity"].warn == 10


class TestLocalOverrideIntegrity:
    """CH-0027: planted local YAML cannot bypass the rot-guard clamp."""

    def test_extreme_fail_is_clamped(self, tmp_path):
        _plant_local_profile(tmp_path, """\
            language: python
            provenance: "planted extreme fail"
            thresholds:
              cyclomatic_complexity: {warn: 10, fail: 1000}
        """)
        service = LanguageProfileService(project_path=tmp_path)
        spec = service.threshold("python", "cyclomatic_complexity")
        assert spec.fail <= 20 * 1.5 + 1e-9
        assert spec.fail >= 20 * 0.5 - 1e-9
        assert spec.warn <= spec.fail

    def test_extreme_scalar_is_clamped(self, tmp_path):
        _plant_local_profile(tmp_path, """\
            language: python
            provenance: "planted extreme scalar"
            scalar_thresholds:
              wmc: 10000
        """)
        service = LanguageProfileService(project_path=tmp_path)
        wmc = service.scalar("python", "wmc")
        assert wmc is not None
        assert wmc <= 20 * 1.5 + 1e-9
        assert wmc >= 20 * 0.5 - 1e-9

    def test_go_anchor_cannot_bypass_python_clamp(self, tmp_path):
        # Go's fail is 30, so +-50% allows 45. That must not become python's live fail.
        _plant_local_profile(tmp_path, """\
            language: go
            provenance: "planted go-wide fail"
            thresholds:
              cyclomatic_complexity: {warn: 15, fail: 45}
        """)
        service = LanguageProfileService(project_path=tmp_path)
        spec = service.threshold("python", "cyclomatic_complexity")
        assert spec.fail <= 20 * 1.5 + 1e-9

    def test_extreme_weights_are_refused(self, tmp_path):
        _plant_local_profile(tmp_path, """\
            language: python
            provenance: "planted extreme weights"
            thresholds:
              cyclomatic_complexity: {warn: 8, fail: 16}
            category_weights:
              reliability: 1.0e9
              maintainability: 0.3
              comprehensibility: 0.1
        """)
        service = LanguageProfileService(project_path=tmp_path)
        profile = service.resolve("python")
        assert profile.thresholds["cyclomatic_complexity"].warn == 10
        assert profile.thresholds["cyclomatic_complexity"].fail == 20
        assert not profile.category_weights
        assert "planted extreme weights" not in (profile.provenance or "")

    def test_zero_weight_is_refused(self, tmp_path):
        _plant_local_profile(tmp_path, """\
            language: python
            provenance: "planted zero weight"
            category_weights:
              reliability: 0
              maintainability: 0.5
              comprehensibility: 0.5
        """)
        service = LanguageProfileService(project_path=tmp_path)
        profile = service.resolve("python")
        assert not profile.category_weights
        assert "planted zero weight" not in (profile.provenance or "")

    def test_nan_fail_does_not_become_live_profile(self, tmp_path):
        _plant_local_profile(tmp_path, """\
            language: python
            provenance: "planted nan"
            thresholds:
              cyclomatic_complexity: {warn: 10, fail: .nan}
        """)
        service = LanguageProfileService(project_path=tmp_path)
        spec = service.threshold("python", "cyclomatic_complexity")
        assert spec.warn == 10
        assert spec.fail == 20
        assert math.isfinite(spec.fail)

    def test_inf_fail_does_not_become_live_profile(self, tmp_path):
        _plant_local_profile(tmp_path, """\
            language: python
            provenance: "planted inf"
            thresholds:
              cyclomatic_complexity: {warn: 10, fail: .inf}
        """)
        service = LanguageProfileService(project_path=tmp_path)
        spec = service.threshold("python", "cyclomatic_complexity")
        assert spec.fail == 20
        assert math.isfinite(spec.fail)

    def test_warn_greater_than_fail_is_refused(self, tmp_path):
        _plant_local_profile(tmp_path, """\
            language: python
            provenance: "planted inverted"
            thresholds:
              cyclomatic_complexity: {warn: 50, fail: 10}
        """)
        service = LanguageProfileService(project_path=tmp_path)
        spec = service.threshold("python", "cyclomatic_complexity")
        assert spec.warn == 10
        assert spec.fail == 20
        profile = service.resolve("python")
        assert "planted inverted" not in (profile.provenance or "")


class TestLanguagePathJail:
    """CH-0026: language is an allowlisted stem, never a path join operand."""

    def _jail_service(self, tmp_path):
        profiles = tmp_path / "profiles"
        profiles.mkdir()
        (profiles / "generic.yaml").write_text(textwrap.dedent("""\
            language: generic
            provenance: test-generic
            thresholds:
              cyclomatic_complexity: {warn: 10, fail: 20}
        """))
        (profiles / "python.yaml").write_text(textwrap.dedent("""\
            language: python
            provenance: test-python
            thresholds:
              cyclomatic_complexity: {warn: 10, fail: 20}
        """))
        poison = tmp_path / "x.yaml"
        poison.write_text(textwrap.dedent("""\
            language: pwned
            provenance: poison
            thresholds:
              cyclomatic_complexity: {warn: 1, fail: 2}
        """))
        service = LanguageProfileService(project_path=tmp_path, profiles_dir=profiles)
        return service, poison

    def test_relative_traversal_falls_back_to_generic(self, tmp_path):
        service, _poison = self._jail_service(tmp_path)
        profile = service.resolve("../x")
        assert profile.thresholds["cyclomatic_complexity"].warn == 10
        assert profile.provenance != "poison"

    def test_absolute_path_falls_back_to_generic(self, tmp_path):
        service, poison = self._jail_service(tmp_path)
        profile = service.resolve("/tmp/x")
        assert profile.thresholds["cyclomatic_complexity"].warn == 10
        outside = service.resolve(str(poison.with_suffix("")))
        assert outside.thresholds["cyclomatic_complexity"].warn == 10
        assert outside.provenance != "poison"

    def test_valid_shipped_language_still_loads(self):
        service = LanguageProfileService()
        profile = service.resolve("python")
        assert profile.language == "python"
        assert profile.thresholds["cyclomatic_complexity"].warn == 10


_GENERIC_PROFILE_YAML = """\
    language: generic
    provenance: test-generic
    thresholds:
      cyclomatic_complexity: {warn: 10, fail: 20}
    scalar_thresholds:
      wmc: 20
"""


def _write_profiles_dir(tmp_path, files: dict):
    profiles = tmp_path / "profiles"
    profiles.mkdir()
    for name, body in files.items():
        (profiles / name).write_text(textwrap.dedent(body), encoding="utf-8")
    return profiles


class TestInvalidProfileDoesNotAbortConstruction:
    """CH-0031: schema-invalid YAML is skipped; the service still constructs."""

    def test_bundled_thresholds_list_falls_back_to_generic(self, tmp_path):
        profiles = _write_profiles_dir(
            tmp_path,
            {
                "generic.yaml": _GENERIC_PROFILE_YAML,
                "python.yaml": """\
                    language: python
                    provenance: poisoned-list-thresholds
                    thresholds: []
                """,
            },
        )
        service = LanguageProfileService(project_path=tmp_path, profiles_dir=profiles)
        profile = service.resolve("python")
        assert profile.language == "python"
        assert profile.thresholds["cyclomatic_complexity"].warn == 10
        assert profile.thresholds["cyclomatic_complexity"].fail == 20
        assert "poisoned-list-thresholds" not in (profile.provenance or "")

    def test_bundled_bad_enum_falls_back_to_generic(self, tmp_path):
        profiles = _write_profiles_dir(
            tmp_path,
            {
                "generic.yaml": _GENERIC_PROFILE_YAML,
                "python.yaml": """\
                    language: python
                    provenance: poisoned-bad-enum
                    thresholds:
                      cyclomatic_complexity: {warn: 1, fail: 2}
                    severity_confidence:
                      global_dead_code: NOT_A_SEVERITY
                """,
            },
        )
        service = LanguageProfileService(project_path=tmp_path, profiles_dir=profiles)
        profile = service.resolve("python")
        assert profile.language == "python"
        assert profile.thresholds["cyclomatic_complexity"].warn == 10
        assert profile.thresholds["cyclomatic_complexity"].fail == 20
        assert "poisoned-bad-enum" not in (profile.provenance or "")

    def test_invalid_generic_yaml_uses_incode_defaults(self, tmp_path):
        profiles = _write_profiles_dir(
            tmp_path,
            {
                "generic.yaml": """\
                    language: generic
                    provenance: poisoned-generic
                    thresholds: []
                """,
                "python.yaml": """\
                    language: python
                    provenance: test-python
                    thresholds:
                      cyclomatic_complexity: {warn: 11, fail: 21}
                """,
            },
        )
        service = LanguageProfileService(project_path=tmp_path, profiles_dir=profiles)
        profile = service.resolve("python")
        assert profile.language == "python"
        assert profile.thresholds["cyclomatic_complexity"].warn == 11
        assert "poisoned-generic" not in (profile.provenance or "")

    def test_only_poisoned_generic_still_constructs(self, tmp_path):
        profiles = _write_profiles_dir(
            tmp_path,
            {
                "generic.yaml": """\
                    language: generic
                    provenance: poisoned-generic
                    thresholds: []
                """,
            },
        )
        service = LanguageProfileService(project_path=tmp_path, profiles_dir=profiles)
        profile = service.resolve("cobol")
        assert profile.language == "cobol"
        assert profile.thresholds == {}

    def test_local_thresholds_list_is_skipped(self, tmp_path):
        _plant_local_profile(
            tmp_path,
            """\
            language: python
            provenance: "planted list thresholds"
            thresholds: []
            """,
        )
        service = LanguageProfileService(project_path=tmp_path)
        profile = service.resolve("python")
        assert profile.thresholds["cyclomatic_complexity"].warn == 10
        assert profile.thresholds["cyclomatic_complexity"].fail == 20
        assert "planted list thresholds" not in (profile.provenance or "")

    def test_local_bad_enum_is_skipped(self, tmp_path):
        _plant_local_profile(
            tmp_path,
            """\
            language: python
            provenance: "planted bad enum"
            thresholds:
              cyclomatic_complexity: {warn: 8, fail: 16}
            severity_confidence:
              global_dead_code: NOT_A_SEVERITY
            """,
        )
        service = LanguageProfileService(project_path=tmp_path)
        profile = service.resolve("python")
        assert profile.thresholds["cyclomatic_complexity"].warn == 10
        assert profile.thresholds["cyclomatic_complexity"].fail == 20
        assert "planted bad enum" not in (profile.provenance or "")
        assert profile.severity_confidence.get("global_dead_code") != "NOT_A_SEVERITY"
