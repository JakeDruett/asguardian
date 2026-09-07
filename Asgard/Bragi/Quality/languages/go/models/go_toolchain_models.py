"""Configuration models for the Go toolchain-orchestrating analysers."""

from pathlib import Path

from pydantic import BaseModel, Field


class GoVetConfig(BaseModel):
    """Configuration for go vet orchestration."""
    scan_path: Path = Field(default_factory=lambda: Path("."))
    timeout_seconds: int = Field(default=180, description="Per-module go vet timeout")
    max_findings: int = Field(default=1000)


class GoBuildConfig(BaseModel):
    """Configuration for go build orchestration."""
    scan_path: Path = Field(default_factory=lambda: Path("."))
    timeout_seconds: int = Field(default=300, description="Per-module go build timeout")
    max_findings: int = Field(default=1000)


class GoFmtConfig(BaseModel):
    """Configuration for gofmt -l orchestration."""
    scan_path: Path = Field(default_factory=lambda: Path("."))
    timeout_seconds: int = Field(default=120, description="Per-module gofmt timeout")
    max_findings: int = Field(default=1000)


class GoTestConfig(BaseModel):
    """Configuration for go test -json orchestration."""
    scan_path: Path = Field(default_factory=lambda: Path("."))
    timeout_seconds: int = Field(default=600, description="Per-module go test timeout")
    max_findings: int = Field(default=1000)


class GoVulnConfig(BaseModel):
    """Configuration for govulncheck orchestration."""
    scan_path: Path = Field(default_factory=lambda: Path("."))
    timeout_seconds: int = Field(default=300, description="Per-module govulncheck timeout")
    max_findings: int = Field(default=1000)
