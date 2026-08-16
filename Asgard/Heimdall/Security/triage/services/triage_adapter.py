"""Provider-agnostic triage adapter interface + Mock and Claude implementations.

Importing this module MUST NEVER require the ``anthropic`` package or perform any
network I/O -- the ``anthropic`` SDK is an optional import used only inside
:class:`ClaudeTriageAdapter`, and only when that adapter is actually invoked from the
opt-in path (``enable_assist=True``).

Data leaving the host: constructing and invoking :class:`ClaudeTriageAdapter` sends
redacted finding ``title``, ``description``, and capped ``code_context`` to the
Anthropic Messages API. The default :func:`~Asgard.Heimdall.Security.triage.services.triage_service.triage_findings`
path uses :class:`MockTriageAdapter` (no network) unless a caller explicitly passes a
:class:`ClaudeTriageAdapter`. Secret-like spans are masked before send; model JSON is
treated as untrusted.
"""

from __future__ import annotations

import json
import os
import re
from abc import ABC, abstractmethod
from typing import Any, Callable, Optional, Tuple

from Asgard.Heimdall.Security.triage.models.triage_models import TriageLabel, TriageVerdict
from Asgard.Heimdall.Security.utilities.security_utils import mask_secret

try:  # Optional dependency -- must never be a hard import failure.
    import anthropic  # type: ignore
except ImportError:  # pragma: no cover - exercised implicitly whenever SDK absent
    anthropic = None  # type: ignore


MAX_CODE_CONTEXT_CHARS = 4000

_SYSTEM_INSTRUCTION = (
    "You are assisting a static-analysis triage step. Given a low-confidence "
    "security finding and its surrounding code, return ONLY a JSON object "
    '{"label": "likely_real"|"likely_false_positive"|"needs_human", '
    '"rationale": "<short reason>", "confidence": <0..1 float>}.'
)

_ALLOWED_MODEL_LABELS = frozenset(
    {
        TriageLabel.LIKELY_REAL,
        TriageLabel.LIKELY_FALSE_POSITIVE,
        TriageLabel.NEEDS_HUMAN,
    }
)

_PEM_PRIVATE_KEY = re.compile(
    r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----"
    r".{0,16384}?"
    r"-----END (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----",
    re.DOTALL,
)
_AWS_ACCESS_KEY = re.compile(r"(?:AKIA|ABIA|ACCA)[0-9A-Z]{16}")
_SK_TOKEN = re.compile(r"\bsk-[A-Za-z0-9_-]{16,}")
_BEARER_TOKEN = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-+=/]{16,}")
_SECRET_ASSIGNMENT = re.compile(
    r"(?i)(\b(?:password|passwd|pwd|api[_-]?key|secret(?:[_-]?key)?)\s*[=:]\s*['\"]?)"
    r"([^\s'\"]{4,})"
    r"(['\"]?)"
)
_HEX_KEY_BLOB = re.compile(r"\b[A-Fa-f0-9]{40,}\b")
_B64_KEY_BLOB = re.compile(r"(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{40,}={1,2}(?![A-Za-z0-9+/=])")


def cap_code_context(code_context: str, limit: int = MAX_CODE_CONTEXT_CHARS) -> str:
    """Return ``code_context`` truncated to ``limit`` characters."""
    if not code_context:
        return ""
    text = code_context if isinstance(code_context, str) else str(code_context)
    if len(text) <= limit:
        return text
    return text[:limit]


def _mask_span(match: re.Match[str]) -> str:
    return mask_secret(match.group(0))


def _mask_keylike_blob(match: re.Match[str]) -> str:
    blob = match.group(0)
    if len(set(blob.lower().rstrip("="))) < 8:
        return blob
    return mask_secret(blob)


def _mask_assignment(match: re.Match[str]) -> str:
    return f"{match.group(1)}{mask_secret(match.group(2))}{match.group(3)}"


_SECRET_SPAN_RULES: Tuple[Tuple[re.Pattern[str], Callable[[re.Match[str]], str]], ...] = (
    (_PEM_PRIVATE_KEY, _mask_span),
    (_AWS_ACCESS_KEY, _mask_span),
    (_SK_TOKEN, _mask_span),
    (_BEARER_TOKEN, _mask_span),
    (_SECRET_ASSIGNMENT, _mask_assignment),
    (_HEX_KEY_BLOB, _mask_keylike_blob),
    (_B64_KEY_BLOB, _mask_keylike_blob),
)


def redact_secret_spans(text: str) -> str:
    """Replace secret-like spans with a first/last-4 mask via :func:`mask_secret`."""
    if not text:
        return ""
    redacted = text if isinstance(text, str) else str(text)
    for pattern, replacer in _SECRET_SPAN_RULES:
        redacted = pattern.sub(replacer, redacted)
    return redacted


def _verdict_from_model_json(text: str) -> TriageVerdict:
    """Parse model output as an allowlisted :class:`TriageVerdict`.

    Extra JSON keys are ignored. Invalid JSON or an unknown label raises
    ``ValueError`` so callers can degrade to ``NOT_AVAILABLE``.
    """
    try:
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError("model output is not a JSON object")
        label = TriageLabel(data["label"])
        if label not in _ALLOWED_MODEL_LABELS:
            raise ValueError(f"model label is not an allowed triage label: {label!r}")
        rationale = str(data.get("rationale", ""))
        confidence = float(data.get("confidence", 0.0))
        return TriageVerdict(label=label, rationale=rationale, confidence=confidence)
    except Exception as exc:
        raise ValueError(
            f"untrusted model JSON is not a valid triage verdict: {exc}"
        ) from exc


class TriageAdapter(ABC):
    """Abstract interface for a pluggable LLM-assisted triage backend.

    Implementations are advisory-only: a verdict returned here is never used to
    drop a finding, change its severity, or auto-suppress it (that invariant is
    enforced by ``triage_service.triage_findings``, not by adapters).
    """

    @abstractmethod
    def triage(self, finding: Any, code_context: str) -> TriageVerdict:
        """Return a :class:`TriageVerdict` for a single finding + surrounding code.

        Implementations should raise on unrecoverable failure; callers are
        responsible for catching exceptions and degrading to NOT_AVAILABLE.
        """
        raise NotImplementedError


class MockTriageAdapter(TriageAdapter):
    """Deterministic offline adapter for tests. Makes no network calls.

    Verdict is derived from a simple, deterministic rule so tests can assert
    exact output: findings whose ``title``/``description``/``vulnerability_type``
    contains "constant" or "literal" are labelled likely-false-positive; all
    others are labelled needs-human. This is intentionally simplistic -- it
    exists only to exercise the annotate/never-drop plumbing in tests.
    """

    def __init__(self, fixed_label: Optional[TriageLabel] = None, calls: Optional[list] = None):
        self.fixed_label = fixed_label
        # Optional call-spy list; each triage() call appends (finding, code_context).
        self.calls = calls if calls is not None else []

    def triage(self, finding: Any, code_context: str) -> TriageVerdict:
        self.calls.append((finding, code_context))
        if self.fixed_label is not None:
            label = self.fixed_label
        else:
            text = " ".join(
                str(getattr(finding, attr, "") or "")
                for attr in ("title", "description", "vulnerability_type")
            ).lower()
            if "constant" in text or "literal" in text:
                label = TriageLabel.LIKELY_FALSE_POSITIVE
            else:
                label = TriageLabel.NEEDS_HUMAN
        return TriageVerdict(
            label=label,
            rationale="mock adapter deterministic verdict (offline, no network)",
            confidence=0.5,
        )


class ClaudeTriageAdapter(TriageAdapter):
    """Real triage adapter backed by the Anthropic Messages API.

    Optional dependency: requires the ``anthropic`` package to be installed and
    ``ANTHROPIC_API_KEY`` to be set in the environment. Neither is required to
    import this module or the rest of the ``triage`` package -- construction
    (not import) is where the SDK is actually needed, and callers should treat
    a missing SDK/key as a normal degrade-to-``not_available`` path, not a
    crash.

    When constructed and invoked this adapter sends redacted finding title,
    description, and capped code context to Anthropic. The default triage path
    does not construct this class (it uses :class:`MockTriageAdapter`).
    """

    # Per the claude-api skill's "Current Models" table (cached 2026-06-24):
    # default flagship model id absent an explicit user override.
    # verify model id
    MODEL_ID = "claude-opus-4-8"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        if anthropic is None:
            raise RuntimeError(
                "assist unavailable (SDK not installed): the 'anthropic' package "
                "is not installed; run `pip install anthropic` to enable "
                "ClaudeTriageAdapter, or continue using MockTriageAdapter."
            )
        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError(
                "assist unavailable: ANTHROPIC_API_KEY is not set in the environment."
            )
        self._client = anthropic.Anthropic(api_key=key)
        self._model = model or self.MODEL_ID

    def triage(self, finding: Any, code_context: str) -> TriageVerdict:
        title = redact_secret_spans(str(getattr(finding, "title", "") or ""))
        description = redact_secret_spans(str(getattr(finding, "description", "") or ""))
        snippet = redact_secret_spans(cap_code_context(str(code_context or "")))
        user_payload = f"Finding: {title} - {description}\nCode:\n{snippet}\n"
        response = self._client.messages.create(
            model=self._model,
            max_tokens=256,
            system=_SYSTEM_INSTRUCTION,
            messages=[{"role": "user", "content": user_payload}],
        )
        text = "".join(
            block.text for block in response.content if getattr(block, "type", None) == "text"
        )
        return _verdict_from_model_json(text)
