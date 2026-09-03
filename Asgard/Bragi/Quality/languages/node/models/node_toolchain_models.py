"""Configuration models for the Node toolchain-orchestrating analysers."""

from pathlib import Path
from typing import List

from pydantic import BaseModel, Field


class NodeLintConfig(BaseModel):
    """Configuration for ESLint orchestration."""
    scan_path: Path = Field(default_factory=lambda: Path("."))
    timeout_seconds: int = Field(default=300)
    extra_args: List[str] = Field(default_factory=list)
    max_findings: int = Field(default=1000)


class NodeAuditConfig(BaseModel):
    """Configuration for npm audit orchestration."""
    scan_path: Path = Field(default_factory=lambda: Path("."))
    timeout_seconds: int = Field(default=180)
    max_findings: int = Field(default=1000)


class NodeTypecheckConfig(BaseModel):
    """Configuration for tsc orchestration."""
    scan_path: Path = Field(default_factory=lambda: Path("."))
    timeout_seconds: int = Field(default=300)
    max_findings: int = Field(default=1000)
