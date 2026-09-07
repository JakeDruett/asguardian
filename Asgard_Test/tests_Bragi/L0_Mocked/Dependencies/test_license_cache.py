"""
Tests for the license disk cache (Plan 03 Phase D / CH-0032):
`.asgard_cache/bragi_license_cache.json` is HMAC-signed and keyed by
name@version. Planted unsigned cache must not steer policy.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from Asgard.Bragi.Dependencies.models.license_models import LicenseConfig
from Asgard.Bragi.Dependencies.services._license_cache import (
    CACHE_RELATIVE_PATH,
    CACHE_VERSION,
    HMAC_ENV,
    LicenseDiskCache,
    default_use_cache,
    entry_key,
)
from Asgard.Bragi.Dependencies.services.license_checker import LicenseChecker


@pytest.fixture
def license_hmac(monkeypatch):
    monkeypatch.setenv(HMAC_ENV, "test-license-cache-key")


def _plant_unsigned(scan_path: Path, packages: dict, version: str = CACHE_VERSION):
    path = scan_path / CACHE_RELATIVE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "version": version,
        "packages": packages,
    }))
    return path


class TestLicenseDiskCache:
    def test_put_get_roundtrip(self, tmp_path, license_hmac):
        cache = LicenseDiskCache(tmp_path, expiry_days=7)
        cache.put("Requests", {"version": "2.28.0", "license_name": "Apache-2.0"})
        record = cache.get("requests", "2.28.0")
        assert record["license_name"] == "Apache-2.0"

    def test_get_requires_version(self, tmp_path, license_hmac):
        cache = LicenseDiskCache(tmp_path, expiry_days=7)
        cache.put("pkg", {"version": "1.0.0", "license_name": "MIT"})
        assert cache.get("pkg") is None
        assert cache.get("pkg", "2.0.0") is None
        assert cache.get("pkg", "1.0.0")["license_name"] == "MIT"

    def test_put_without_version_is_ignored(self, tmp_path, license_hmac):
        cache = LicenseDiskCache(tmp_path, expiry_days=7)
        cache.put("pkg", {"license_name": "MIT"})
        assert cache.get("pkg", "1.0.0") is None

    def test_persists_across_instances(self, tmp_path, license_hmac):
        first = LicenseDiskCache(tmp_path, expiry_days=7)
        first.put("pkg", {"version": "1.0.0", "license_name": "MIT"})
        first.save()
        assert (tmp_path / CACHE_RELATIVE_PATH).exists()
        payload = json.loads((tmp_path / CACHE_RELATIVE_PATH).read_text())
        assert payload.get("hmac")
        assert entry_key("pkg", "1.0.0") in payload["packages"]
        second = LicenseDiskCache(tmp_path, expiry_days=7)
        assert second.get("pkg", "1.0.0")["license_name"] == "MIT"

    def test_persists_across_instances_without_env_hmac_key(self, tmp_path, monkeypatch):
        """Cross-process cache hit with no ASGARD_LICENSE_HMAC_KEY set at all --
        the persisted sibling .key file must be what makes verification work.
        Before the fix, each instance minted its own os.urandom(32) key, so
        `second`'s HMAC check on `first`'s cache always failed.
        """
        monkeypatch.delenv(HMAC_ENV, raising=False)
        first = LicenseDiskCache(tmp_path, expiry_days=7)
        first.put("pkg", {"version": "1.0.0", "license_name": "MIT"})
        first.save()

        cache_file = tmp_path / CACHE_RELATIVE_PATH
        key_file = cache_file.with_name(cache_file.name + ".key")
        assert key_file.exists()
        assert len(key_file.read_bytes()) == 32

        second = LicenseDiskCache(tmp_path, expiry_days=7)
        record = second.get("pkg", "1.0.0")
        assert record is not None
        assert record["license_name"] == "MIT"

    def test_expiry_honours_cache_expiry_days(self, tmp_path, license_hmac):
        cache = LicenseDiskCache(tmp_path, expiry_days=7)
        cache.put("pkg", {"version": "1.0.0", "license_name": "MIT"})
        cache.save()
        fresh = LicenseDiskCache(
            tmp_path, expiry_days=7,
            now=datetime.now() + timedelta(days=6))
        assert fresh.get("pkg", "1.0.0") is not None
        stale = LicenseDiskCache(
            tmp_path, expiry_days=7,
            now=datetime.now() + timedelta(days=8))
        assert stale.get("pkg", "1.0.0") is None

    def test_corrupt_cache_treated_as_empty(self, tmp_path, license_hmac):
        path = tmp_path / CACHE_RELATIVE_PATH
        path.parent.mkdir(parents=True)
        path.write_text("{not json")
        cache = LicenseDiskCache(tmp_path, expiry_days=7)
        assert cache.get("anything", "1.0.0") is None

    def test_unsigned_planted_cache_is_ignored(self, tmp_path, license_hmac):
        _plant_unsigned(tmp_path, {
            entry_key("evil-gpl-pkg", "1.0.0"): {
                "version": "1.0.0",
                "license_name": "MIT",
                "source": "pypi",
                "fetched_at": datetime.now().isoformat(),
            }
        })
        cache = LicenseDiskCache(tmp_path, expiry_days=7)
        assert cache.get("evil-gpl-pkg", "1.0.0") is None

    def test_name_only_legacy_key_is_ignored(self, tmp_path, license_hmac):
        cache = LicenseDiskCache(tmp_path, expiry_days=7)
        cache.put("pkg", {"version": "1.0.0", "license_name": "MIT"})
        cache.save()
        data = json.loads((tmp_path / CACHE_RELATIVE_PATH).read_text())
        record = data["packages"].pop(entry_key("pkg", "1.0.0"))
        data["packages"]["pkg"] = record
        (tmp_path / CACHE_RELATIVE_PATH).write_text(json.dumps(data))
        loaded = LicenseDiskCache(tmp_path, expiry_days=7)
        assert loaded.get("pkg", "1.0.0") is None

    def test_rewritten_license_without_hmac_is_ignored(self, tmp_path, license_hmac):
        cache = LicenseDiskCache(tmp_path, expiry_days=7)
        cache.put("pkg", {"version": "1.0.0", "license_name": "GPL-3.0",
                          "source": "pypi"})
        cache.save()
        data = json.loads((tmp_path / CACHE_RELATIVE_PATH).read_text())
        data["packages"][entry_key("pkg", "1.0.0")]["license_name"] = "MIT"
        (tmp_path / CACHE_RELATIVE_PATH).write_text(json.dumps(data))
        loaded = LicenseDiskCache(tmp_path, expiry_days=7)
        assert loaded.get("pkg", "1.0.0") is None

    def test_schema_invalid_record_is_ignored(self, tmp_path, license_hmac):
        cache = LicenseDiskCache(tmp_path, expiry_days=7)
        cache.put("pkg", {"version": "1.0.0", "license_name": "MIT"})
        cache.save()
        data = json.loads((tmp_path / CACHE_RELATIVE_PATH).read_text())
        data["packages"][entry_key("pkg", "1.0.0")]["license_name"] = ["not", "a", "str"]
        # Re-sign so HMAC passes and schema is the only gate.
        from Asgard.Bragi.Dependencies.services._license_cache import LicenseDiskCache as LDC
        signer = LDC(tmp_path)
        body = {"version": data["version"], "packages": data["packages"]}
        key = signer._hmac_key(create=False)
        data["hmac"] = signer._sign(body, key)
        (tmp_path / CACHE_RELATIVE_PATH).write_text(json.dumps(data))
        loaded = LicenseDiskCache(tmp_path, expiry_days=7)
        assert loaded.get("pkg", "1.0.0") is None


class TestCheckerUsesLocalMetadataAndCache:
    def test_installed_package_resolved_without_network(self, tmp_path, monkeypatch):
        (tmp_path / "requirements.txt").write_text("pytest>=7\n")
        checker = LicenseChecker(LicenseConfig(scan_path=tmp_path, use_cache=False))

        def boom(*a, **k):
            raise AssertionError("network fallback must not be hit")
        monkeypatch.setattr(checker, "_get_license_from_pypi", boom)

        result = checker.analyze()
        assert result.total_packages == 1
        assert result.packages[0].source == "installed"
        assert result.packages[0].version

    def test_analyze_writes_and_reuses_disk_cache(self, tmp_path, monkeypatch, license_hmac):
        (tmp_path / "requirements.txt").write_text("pytest>=7\n")
        LicenseChecker(LicenseConfig(scan_path=tmp_path, use_cache=True)).analyze()
        assert (tmp_path / CACHE_RELATIVE_PATH).exists()

        checker = LicenseChecker(LicenseConfig(scan_path=tmp_path, use_cache=True))

        def boom(*a, **k):
            raise AssertionError("cached package must not re-resolve")
        monkeypatch.setattr(checker, "_get_license_from_installed", boom)
        monkeypatch.setattr(checker, "_get_license_from_pypi", boom)
        result = checker.analyze()
        assert result.total_packages == 1

    def test_use_cache_false_writes_nothing(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("pytest>=7\n")
        checker = LicenseChecker(LicenseConfig(scan_path=tmp_path,
                                               use_cache=False))
        checker.analyze()
        assert not (tmp_path / CACHE_RELATIVE_PATH).exists()

    def test_unknown_package_falls_back_to_pypi_parallel(self, tmp_path, monkeypatch):
        (tmp_path / "requirements.txt").write_text(
            "no-such-pkg-a==1.0\nno-such-pkg-b==1.0\n")
        checker = LicenseChecker(LicenseConfig(
            scan_path=tmp_path, enable_network=True, use_cache=False))
        calls = []

        def fake_pypi(name):
            calls.append(name)
            return None
        monkeypatch.setattr(checker, "_get_license_from_pypi", fake_pypi)
        result = checker.analyze()
        assert sorted(calls) == ["no-such-pkg-a", "no-such-pkg-b"]
        assert all(p.source == "not_found" for p in result.packages)

    def test_pypi_not_called_when_network_disabled(self, tmp_path, monkeypatch):
        (tmp_path / "requirements.txt").write_text("no-such-pkg-offline==1.0\n")
        checker = LicenseChecker(LicenseConfig(scan_path=tmp_path, use_cache=False))

        def boom(*a, **k):
            raise AssertionError("PyPI must stay gated behind enable_network")
        monkeypatch.setattr(checker, "_get_license_from_pypi", boom)
        result = checker.analyze()
        assert result.packages[0].source == "network_disabled"
        # Deterministic ordering: sorted by name.
        assert [p.package_name for p in result.packages] == sorted(
            p.package_name for p in result.packages)


class TestPlantedCacheCannotBypassPolicy:
    def test_unsigned_planted_cache_does_not_allow_prohibited(self, tmp_path, license_hmac):
        (tmp_path / "requirements.txt").write_text("evil-gpl-pkg==1.0.0\n")
        _plant_unsigned(tmp_path, {
            entry_key("evil-gpl-pkg", "1.0.0"): {
                "version": "1.0.0",
                "license_name": "MIT",
                "source": "pypi",
                "fetched_at": datetime.now().isoformat(),
            }
        })
        result = LicenseChecker(LicenseConfig(
            scan_path=tmp_path, use_cache=True, enable_network=False,
        )).analyze()
        pkg = result.packages[0]
        assert pkg.package_name == "evil-gpl-pkg"
        assert pkg.license_name != "MIT"
        assert pkg.is_allowed is False
        assert pkg.verdict != "allowed"
        assert pkg.source == "network_disabled"

    def test_legacy_name_only_planted_cache_is_not_trusted(self, tmp_path, license_hmac):
        (tmp_path / "requirements.txt").write_text("evil-gpl-pkg==1.0.0\n")
        _plant_unsigned(tmp_path, {
            "evil-gpl-pkg": {
                "version": "1.0.0",
                "license_name": "MIT",
                "source": "pypi",
                "fetched_at": datetime.now().isoformat(),
            }
        }, version="1.0.0")
        result = LicenseChecker(LicenseConfig(
            scan_path=tmp_path, use_cache=True, enable_network=False,
        )).analyze()
        pkg = result.packages[0]
        assert pkg.license_name != "MIT"
        assert pkg.verdict != "allowed"
        assert pkg.source == "network_disabled"

    def test_signed_cache_is_reused_for_same_version(self, tmp_path, license_hmac, monkeypatch):
        (tmp_path / "requirements.txt").write_text("evil-gpl-pkg==1.0.0\n")
        cache = LicenseDiskCache(tmp_path, expiry_days=7)
        cache.put("evil-gpl-pkg", {
            "version": "1.0.0",
            "license_name": "MIT",
            "source": "pypi",
        })
        cache.save()
        checker = LicenseChecker(LicenseConfig(
            scan_path=tmp_path, use_cache=True, enable_network=False,
        ))

        def boom(*a, **k):
            raise AssertionError("signed same-version cache must be used")
        monkeypatch.setattr(checker, "_get_license_from_installed", boom)
        monkeypatch.setattr(checker, "_get_license_from_pypi", boom)
        result = checker.analyze()
        assert result.packages[0].license_name == "MIT"
        assert result.packages[0].is_allowed is True

    def test_signed_cache_does_not_apply_to_other_version(
        self, tmp_path, license_hmac, monkeypatch,
    ):
        (tmp_path / "requirements.txt").write_text("evil-gpl-pkg==2.0.0\n")
        cache = LicenseDiskCache(tmp_path, expiry_days=7)
        cache.put("evil-gpl-pkg", {
            "version": "1.0.0",
            "license_name": "MIT",
            "source": "pypi",
        })
        cache.save()
        result = LicenseChecker(LicenseConfig(
            scan_path=tmp_path, use_cache=True, enable_network=False,
        )).analyze()
        pkg = result.packages[0]
        assert pkg.license_name != "MIT"
        assert pkg.source == "network_disabled"


class TestUseCacheCiDefault:
    def test_default_use_cache_false_in_ci(self, monkeypatch):
        monkeypatch.setenv("CI", "true")
        assert default_use_cache() is False
        assert LicenseConfig().use_cache is False

    def test_default_use_cache_true_outside_ci(self, monkeypatch):
        for name in (
            "CI", "GITHUB_ACTIONS", "GITLAB_CI", "TF_BUILD",
            "CIRCLECI", "JENKINS_URL", "BUILDKITE",
        ):
            monkeypatch.delenv(name, raising=False)
        assert default_use_cache() is True
        assert LicenseConfig().use_cache is True
