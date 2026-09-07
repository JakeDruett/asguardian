"""Configuration models for the Rust toolchain-orchestrating analysers."""

from pathlib import Path
from typing import List

from pydantic import BaseModel, Field


class RustClippyConfig(BaseModel):
    """Configuration for cargo clippy orchestration."""
    scan_path: Path = Field(default_factory=lambda: Path("."))
    timeout_seconds: int = Field(default=300, description="Per-crate clippy timeout")
    extra_args: List[str] = Field(
        default_factory=list,
        description="Extra arguments appended after 'cargo clippy --message-format=json'",
    )
    max_findings: int = Field(default=1000)


class RustAuditConfig(BaseModel):
    """Configuration for cargo-audit orchestration."""
    scan_path: Path = Field(default_factory=lambda: Path("."))
    timeout_seconds: int = Field(default=180)
    max_findings: int = Field(default=1000)
