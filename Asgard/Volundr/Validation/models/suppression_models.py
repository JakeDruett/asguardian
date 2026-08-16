"""
Reified Suppression Models.

Suppressions are the ONLY sanctioned way to relax a Volundr rule.
Each suppression is scoped (rule x target), justified (non-empty reason),
and time-boxed (expires required on YAML/file load). Suppressed rules emit
ZERO warnings (warning-annihilation contract) and the rendered artifact
carries a machine-readable receipt.

YAML/file loads reject unrestricted target ``*``, require expiry, and
fail-closed in CI unless the document carries a valid HMAC
(``ASGARD_SUPPRESSION_HMAC_KEY``). HMAC is optional outside CI.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from datetime import date
from fnmatch import fnmatchcase
from typing import List, Optional

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, Field, field_validator


HMAC_ENV = "ASGARD_SUPPRESSION_HMAC_KEY"
_CI_ENV_VARS = (
    "CI",
    "GITHUB_ACTIONS",
    "GITLAB_CI",
    "TF_BUILD",
    "CIRCLECI",
    "JENKINS_URL",
    "BUILDKITE",
)
_FALSEY = frozenset({"", "0", "false", "no", "off"})
_GLOB_METACHARS = frozenset("*?[")


def running_in_ci() -> bool:
    """True when a standard CI indicator env var is set to a truthy value."""
    for name in _CI_ENV_VARS:
        raw = os.environ.get(name, "").strip().lower()
        if raw and raw not in _FALSEY:
            return True
    return False


def is_unrestricted_target(target: str) -> bool:
    """True if ``target`` is ``*`` or another glob that matches every name."""
    value = (target or "").strip()
    if not value:
        return False
    if value == "*":
        return True
    return (
        fnmatchcase("a", value)
        and fnmatchcase("b", value)
        and fnmatchcase("", value)
    )


def _file_target_forbidden(target: str) -> bool:
    """File-loaded targets must be exact (no glob metacharacters)."""
    value = (target or "").strip()
    return (not value) or is_unrestricted_target(value) or any(
        ch in value for ch in _GLOB_METACHARS
    )


def sign_suppressions(suppressions: List["Suppression"], key: str) -> str:
    """HMAC-SHA256 hex digest of the canonical suppression list."""
    payload = [item.model_dump(mode="json") for item in suppressions]
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hmac.new(
        key.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256
    ).hexdigest()


class Suppression(BaseModel):
    """A single scoped, justified rule suppression."""

    rule: str = Field(description="Rule ID being suppressed (must match a known rule)")
    target: str = Field(description="Container/resource/step name (exact; no '*')")
    reason: str = Field(description="Non-empty human justification (ticket ref etc.)")
    expires: Optional[date] = Field(
        default=None, description="Expiry date; required on YAML/file load"
    )

    @field_validator("rule", "target")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("must be a non-empty string")
        return v.strip()

    @field_validator("reason")
    @classmethod
    def _reason_required(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError(
                "suppression requires a non-empty reason (justification is mandatory)"
            )
        return v.strip()

    def is_expired(self, today: Optional[date] = None) -> bool:
        if self.expires is None:
            return False
        return (today or date.today()) > self.expires

    def receipt_annotation_key(self) -> str:
        """K8s annotation key receipt: volundr.asgard/suppress-<rule>."""
        return f"volundr.asgard/suppress-{self.rule}"

    def receipt_comment(self) -> str:
        """Comment receipt for Dockerfile/HCL/pipeline YAML."""
        return f"# volundr:suppress={self.rule} {self.reason}"


class SuppressionSet(BaseModel):
    """A collection of suppressions, loadable from YAML."""

    suppressions: List[Suppression] = Field(default_factory=list)

    @classmethod
    def from_yaml(
        cls,
        text: str,
        *,
        require_signature: Optional[bool] = None,
    ) -> "SuppressionSet":
        """Parse a suppressions YAML document.

        Accepts either a top-level ``suppressions:`` list or a bare list.
        Missing rule/target/reason refuses to compile (ValidationError).
        File-loaded rules require ``expires`` and an exact target (no ``*``).
        In CI, a valid HMAC is required when the set is non-empty.
        """
        data = yaml.safe_load(text) or {}
        provided_mac: Optional[str] = None
        if isinstance(data, dict):
            raw_mac = data.get("hmac", data.get("signature"))
            provided_mac = raw_mac if isinstance(raw_mac, str) else None
            data = {
                k: v for k, v in data.items() if k not in ("hmac", "signature")
            }
        if isinstance(data, list):
            data = {"suppressions": data}
        instance = cls.model_validate(data)
        instance._enforce_file_policy()
        instance._enforce_signature(provided_mac, require_signature)
        return instance

    @classmethod
    def from_file(
        cls,
        path: str,
        *,
        require_signature: Optional[bool] = None,
    ) -> "SuppressionSet":
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_yaml(f.read(), require_signature=require_signature)

    def _enforce_file_policy(self) -> None:
        for suppression in self.suppressions:
            if _file_target_forbidden(suppression.target):
                raise ValueError(
                    "suppression target must be exact (no glob '*'): "
                    f"{suppression.target!r}"
                )
            if suppression.expires is None:
                raise ValueError(
                    f"suppression of '{suppression.rule}' for "
                    f"'{suppression.target}' requires expires"
                )

    def _enforce_signature(
        self,
        provided_mac: Optional[str],
        require_signature: Optional[bool],
    ) -> None:
        must_sign = (
            running_in_ci() if require_signature is None else require_signature
        )
        if not self.suppressions:
            return
        if not must_sign and not provided_mac:
            return
        key = os.environ.get(HMAC_ENV, "").strip()
        if not key:
            raise ValueError(
                "unsigned suppressions refused "
                f"(set {HMAC_ENV} or sign the file)"
            )
        expected = sign_suppressions(self.suppressions, key)
        if not provided_mac or not hmac.compare_digest(provided_mac, expected):
            raise ValueError("unsigned or rewritten suppressions refused")

    def __iter__(self):
        return iter(self.suppressions)

    def __len__(self) -> int:
        return len(self.suppressions)
