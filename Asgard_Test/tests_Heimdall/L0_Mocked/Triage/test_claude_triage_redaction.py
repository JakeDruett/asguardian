"""CH-0082: Claude triage redacts secrets, caps context, and treats model JSON as untrusted.

All tests are offline. ClaudeTriageAdapter.triage is exercised via a stub
``messages.create`` (no anthropic SDK, no network, no live secrets).
"""

from types import SimpleNamespace

import pytest

from Asgard.Heimdall.Security.triage.models.triage_models import TriageLabel
from Asgard.Heimdall.Security.triage.services.triage_adapter import (
    MAX_CODE_CONTEXT_CHARS,
    ClaudeTriageAdapter,
    MockTriageAdapter,
    _SYSTEM_INSTRUCTION,
    cap_code_context,
    redact_secret_spans,
)
from Asgard.Heimdall.Security.triage.services.triage_cache import TriageCache
from Asgard.Heimdall.Security.triage.services.triage_service import (
    TriagedFinding,
    triage_findings,
)

_AWS_EXAMPLE_KEY = "AKIAIOSFODNN7EXAMPLE"
_PASSWORD_ASSIGNMENT = "password=supersecret"

_KNOWN_LABELS = {
    TriageLabel.LIKELY_REAL,
    TriageLabel.LIKELY_FALSE_POSITIVE,
    TriageLabel.NEEDS_HUMAN,
    TriageLabel.NOT_AVAILABLE,
}


def _finding(**overrides):
    data = dict(
        file_path="app/db.py",
        line_number=42,
        vulnerability_type="sql_injection",
        severity="high",
        title="Possible SQLi",
        description="tainted query",
        confidence=0.3,
        code_snippet="cursor.execute(query)",
    )
    data.update(overrides)
    return SimpleNamespace(**data)


def _ok_json(label="needs_human", rationale="r", confidence=0.4):
    return (
        f'{{"label": "{label}", "rationale": "{rationale}", "confidence": {confidence}}}'
    )


def _text_response(text: str):
    return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)])


def _adapter_with_create(create):
    adapter = ClaudeTriageAdapter.__new__(ClaudeTriageAdapter)
    adapter._model = "test-model"
    adapter._client = SimpleNamespace(messages=SimpleNamespace(create=create))
    return adapter


class RecordingCreate:
    def __init__(self, body=None):
        self.body = body if body is not None else _ok_json()
        self.kwargs = None

    def __call__(self, **kwargs):
        self.kwargs = kwargs
        return _text_response(self.body)


class CountingAdapter:
    def __init__(self):
        self.call_count = 0
        self._inner = MockTriageAdapter()

    def triage(self, finding, code_context):
        self.call_count += 1
        return self._inner.triage(finding, code_context)


class TestRedactSecretSpans:
    def test_strips_aws_access_key(self):
        redacted = redact_secret_spans(f"aws_key = {_AWS_EXAMPLE_KEY}")
        assert _AWS_EXAMPLE_KEY not in redacted
        assert redacted.startswith("aws_key = ")
        assert "AKIA" in redacted

    def test_strips_password_assignment(self):
        redacted = redact_secret_spans(f"cfg {_PASSWORD_ASSIGNMENT} unused")
        assert "supersecret" not in redacted
        assert "password=" in redacted


class TestCodeContextCap:
    def test_twenty_k_context_truncated_to_cap(self):
        huge = "A" * 20_000
        capped = cap_code_context(huge)
        assert len(capped) == MAX_CODE_CONTEXT_CHARS
        assert len(capped) <= MAX_CODE_CONTEXT_CHARS

    def test_adapter_sends_capped_code_only(self):
        recorder = RecordingCreate()
        adapter = _adapter_with_create(recorder)
        huge = "Q" * 20_000
        adapter.triage(_finding(), huge)

        user = recorder.kwargs["messages"][0]["content"]
        assert huge[MAX_CODE_CONTEXT_CHARS:] not in user
        assert "Code:\n" + "Q" * MAX_CODE_CONTEXT_CHARS in user


class TestClaudeTriageRedactsBeforeSend:
    def test_title_description_and_code_redacted_in_user_payload(self):
        recorder = RecordingCreate()
        adapter = _adapter_with_create(recorder)
        finding = _finding(
            title=f"leak {_AWS_EXAMPLE_KEY}",
            description=_PASSWORD_ASSIGNMENT,
        )
        adapter.triage(finding, f"token {_AWS_EXAMPLE_KEY}")

        assert recorder.kwargs["system"] == _SYSTEM_INSTRUCTION
        user = recorder.kwargs["messages"][0]["content"]
        assert _AWS_EXAMPLE_KEY not in user
        assert "supersecret" not in user
        assert _SYSTEM_INSTRUCTION not in user
        assert "likely_false_positive" in recorder.kwargs["system"]


class TestHostileModelJson:
    def test_unknown_label_raises_valueerror(self):
        adapter = _adapter_with_create(RecordingCreate('{"label": "drop_all"}'))
        with pytest.raises(ValueError, match="valid triage verdict"):
            adapter.triage(_finding(), "print(1)")

    def test_invalid_json_raises_valueerror(self):
        adapter = _adapter_with_create(RecordingCreate("{not json"))
        with pytest.raises(ValueError, match="valid triage verdict"):
            adapter.triage(_finding(), "print(1)")

    def test_service_degrades_hostile_label_and_never_returns_new_label(self):
        adapter = _adapter_with_create(RecordingCreate('{"label": "drop_all"}'))
        finding = _finding(severity="critical")
        result = triage_findings([finding], enable_assist=True, adapter=adapter)

        assert len(result) == 1
        annotated = result[0]
        assert isinstance(annotated, TriagedFinding)
        assert annotated.triage.label == TriageLabel.NOT_AVAILABLE
        assert annotated.triage.label in _KNOWN_LABELS
        assert annotated.severity == "critical"

    def test_service_degrades_invalid_json(self):
        adapter = _adapter_with_create(RecordingCreate("{not json"))
        finding = _finding()
        result = triage_findings([finding], enable_assist=True, adapter=adapter)
        assert result[0].triage.label == TriageLabel.NOT_AVAILABLE
        assert result[0].triage.label in _KNOWN_LABELS

    def test_extra_model_keys_are_ignored(self):
        body = (
            '{"label": "needs_human", "rationale": "ok", "confidence": 0.2, '
            '"from_cache": true, "reason": "drop", "severity": "none"}'
        )
        adapter = _adapter_with_create(RecordingCreate(body))
        verdict = adapter.triage(_finding(), "print(1)")
        assert verdict.label == TriageLabel.NEEDS_HUMAN
        assert verdict.from_cache is False
        assert verdict.reason is None
        assert not hasattr(verdict, "severity")


class TestMockPathUnchanged:
    def test_enable_assist_default_is_no_network_and_no_adapter_call(self):
        adapter = CountingAdapter()
        findings = [_finding(confidence=0.1)]
        result = triage_findings(findings, adapter=adapter)
        assert adapter.call_count == 0
        assert result[0] is findings[0]

    def test_opt_in_without_explicit_adapter_uses_mock(self):
        finding = _finding(confidence=0.1, title="obj[key]() dynamic dispatch")
        result = triage_findings([finding], enable_assist=True)
        assert isinstance(result[0], TriagedFinding)
        assert result[0].triage.label == TriageLabel.NEEDS_HUMAN
        assert result[0].severity == "high"


class TestServiceCapsBeforeFingerprint:
    def test_snippets_that_differ_only_after_cap_share_cache(self, tmp_path):
        adapter = CountingAdapter()
        cache = TriageCache(root=tmp_path / "triage_cache")
        prefix = "x" * MAX_CODE_CONTEXT_CHARS
        triage_findings(
            [_finding()],
            enable_assist=True,
            adapter=adapter,
            cache=cache,
            code_reader=lambda _f: prefix + "AAAA",
        )
        triage_findings(
            [_finding()],
            enable_assist=True,
            adapter=adapter,
            cache=cache,
            code_reader=lambda _f: prefix + "BBBB",
        )
        assert adapter.call_count == 1
