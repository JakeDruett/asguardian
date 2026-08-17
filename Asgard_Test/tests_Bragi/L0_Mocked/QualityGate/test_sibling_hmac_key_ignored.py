"""Sibling HMAC .key files cannot forge QualityGate baselines (CH-0051 leftover)."""

import json

from Asgard.Bragi.QualityGate.baseline_store import FingerprintBaselineStore


def test_sibling_key_does_not_validate_planted_baseline(tmp_path, monkeypatch):
    monkeypatch.delenv("ASGARD_QG_HMAC_KEY", raising=False)
    store = FingerprintBaselineStore(project_path=tmp_path)
    planted = {
        "branches": {"main": {"commit": "abc", "fingerprints": ["hideme"]}},
        "hmac": "00" * 32,
    }
    store.store_path.parent.mkdir(parents=True, exist_ok=True)
    store.store_path.write_text(json.dumps(planted))
    store._key_path().write_bytes(b"forged-sibling-key")
    assert store.load("main") is None
