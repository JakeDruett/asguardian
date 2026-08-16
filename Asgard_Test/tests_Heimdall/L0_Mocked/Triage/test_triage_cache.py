"""HMAC/schema tests for the opt-in triage verdict cache (CH-0081).

Planted unsigned JSON must not forge ``likely_false_positive``.
"""

import json
import stat
from types import SimpleNamespace

import pytest

from Asgard.Heimdall.Security.triage.models.triage_models import TriageLabel, TriageVerdict
from Asgard.Heimdall.Security.triage.services.triage_cache import (
    HMAC_ENV,
    TriageCache,
    fingerprint,
)


def _finding(**overrides):
    data = dict(
        file_path="app/db.py",
        line_number=42,
        vulnerability_type="sql_injection",
        title="Possible SQLi",
        description="tainted query",
        code_snippet="cursor.execute(query)",
    )
    data.update(overrides)
    return SimpleNamespace(**data)


def _verdict(label=TriageLabel.NEEDS_HUMAN, rationale="ok", confidence=0.5):
    return TriageVerdict(label=label, rationale=rationale, confidence=confidence)


def _hex_key(seed="a"):
    return (seed * 64)[:64]


@pytest.fixture
def triage_hmac(monkeypatch):
    monkeypatch.setenv(HMAC_ENV, "test-triage-cache-key")


class TestTriageCacheIntegrity:
    def test_set_get_roundtrip(self, tmp_path, triage_hmac):
        cache = TriageCache(root=tmp_path)
        key = fingerprint(_finding(), "cursor.execute(query)")
        cache.set(key, _verdict(TriageLabel.LIKELY_REAL, "real", 0.8))
        hit = cache.get(key)
        assert hit is not None
        assert hit.label == TriageLabel.LIKELY_REAL
        assert hit.rationale == "real"
        assert hit.confidence == 0.8
        assert hit.from_cache is True

    def test_unsigned_planted_verdict_is_ignored(self, tmp_path, triage_hmac):
        cache = TriageCache(root=tmp_path)
        key = fingerprint(_finding(), "cursor.execute(query)")
        tmp_path.mkdir(parents=True, exist_ok=True)
        tmp_path.chmod(0o700)
        (tmp_path / f"{key}.json").write_text(json.dumps({
            "label": "likely_false_positive",
            "rationale": "planted",
            "confidence": 1.0,
        }))
        assert cache.get(key) is None

    def test_legacy_bare_verdict_json_is_not_trusted(self, tmp_path, triage_hmac):
        cache = TriageCache(root=tmp_path)
        key = _hex_key("b")
        cache.set(key, _verdict())
        path = tmp_path / f"{key}.json"
        path.write_text(json.dumps({
            "label": "likely_false_positive",
            "rationale": "legacy unsigned",
            "confidence": 1.0,
            "from_cache": True,
        }))
        assert cache.get(key) is None

    def test_rewritten_verdict_without_resigning_is_rejected(self, tmp_path, triage_hmac):
        cache = TriageCache(root=tmp_path)
        key = _hex_key("c")
        cache.set(key, _verdict(TriageLabel.LIKELY_REAL, "real"))
        path = tmp_path / f"{key}.json"
        data = json.loads(path.read_text())
        data["verdict"]["label"] = "likely_false_positive"
        path.write_text(json.dumps(data))
        assert cache.get(key) is None

    def test_signed_entry_copied_to_other_key_is_rejected(self, tmp_path, triage_hmac):
        cache = TriageCache(root=tmp_path)
        src = _hex_key("d")
        dst = _hex_key("e")
        cache.set(src, _verdict(TriageLabel.LIKELY_FALSE_POSITIVE, "fp"))
        (tmp_path / f"{dst}.json").write_bytes((tmp_path / f"{src}.json").read_bytes())
        assert cache.get(dst) is None

    def test_hostile_cache_key_does_not_escape(self, tmp_path, triage_hmac):
        cache = TriageCache(root=tmp_path / "triage")
        cache.set("../x", _verdict())
        cache.set("/tmp/x", _verdict())
        cache.set(".." + "a" * 62, _verdict())
        written = [p for p in (tmp_path / "triage").glob("**/*") if p.is_file()]
        assert written == []
        assert cache.get("../x") is None
        assert cache.get("not-hex") is None

    def test_cache_dir_is_0700_and_files_0600(self, tmp_path, triage_hmac):
        root = tmp_path / "triage"
        cache = TriageCache(root=root)
        key = _hex_key("f")
        cache.set(key, _verdict())
        assert stat.S_IMODE(root.stat().st_mode) == 0o700
        assert stat.S_IMODE((root / f"{key}.json").stat().st_mode) == 0o600

    def test_schema_invalid_verdict_is_not_cached(self, tmp_path, triage_hmac):
        cache = TriageCache(root=tmp_path)
        key = _hex_key("1")
        cache.set(key, SimpleNamespace(label="not-a-label", rationale="x", confidence=0.1, reason=None))
        cache.set(key, SimpleNamespace(label=TriageLabel.NEEDS_HUMAN, rationale="x", confidence=9.0, reason=None))
        assert cache.get(key) is None
        assert list(tmp_path.glob("*.json")) == []

    def test_hmac_mismatch_without_env_key_is_a_miss(self, tmp_path, monkeypatch):
        monkeypatch.delenv(HMAC_ENV, raising=False)
        cache = TriageCache(root=tmp_path)
        key = _hex_key("2")
        cache.set(key, _verdict(TriageLabel.LIKELY_FALSE_POSITIVE))
        assert cache.get(key) is not None
        (tmp_path / f"{key}.json").write_text(json.dumps({
            "version": "1",
            "key": key,
            "verdict": {
                "label": "likely_false_positive",
                "rationale": "planted after key exists",
                "confidence": 1.0,
                "from_cache": False,
            },
            "hmac": "00" * 32,
        }))
        assert cache.get(key) is None
