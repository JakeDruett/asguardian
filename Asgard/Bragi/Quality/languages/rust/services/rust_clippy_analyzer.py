"""
Rust quality analysis via cargo clippy.

Orchestrates the Rust toolchain's own linter rather than reimplementing
clippy's several hundred lints in Python. Clippy's `--message-format=json`
output is normalised into the shared ToolReport/ToolFinding shape (see
Asgard.Bragi.Quality.languages.common.tool_models) used by every
toolchain-orchestrating analyser, so ratings, gates, and issue tracking work
identically regardless of language.

Complements, rather than replaces, RustAnalyzer (the existing regex-based
scanner in this package): clippy catches correctness/style/performance lints
that require real type information and borrow-checking, which no regex rule
can reliably approximate; the regex scanner catches project-specific
security patterns (hardcoded credentials, command injection via untyped
string concatenation) that clippy has no opinion on.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from Asgard.Bragi.Quality.languages.common.tool_models import (
    ToolCategory,
    ToolFinding,
    ToolReport,
    ToolSeverity,
)
from Asgard.Bragi.Quality.languages.common.tool_runner import (
    ToolNotAvailableError,
    find_manifest_dirs,
    require_executable,
    run_tool,
)
from Asgard.Bragi.Quality.languages.rust.models.rust_toolchain_models import RustClippyConfig

_CLIPPY_SECURITY_LINTS = frozenset({
    "clippy::mem_forget",
    "clippy::transmute_ptr_to_ref",
    "clippy::transmute_int_to_bool",
    "clippy::unsound_collection_transmute",
    "clippy::cast_ptr_alignment",
    "clippy::not_unsafe_ptr_arg_deref",
})

_CLIPPY_PERFORMANCE_PREFIXES = ("clippy::perf",)

_LEVEL_TO_SEVERITY = {
    "error": ToolSeverity.ERROR,
    "warning": ToolSeverity.WARNING,
}


class RustClippyAnalyzer:
    """Runs cargo clippy over one or more crates and normalises the output."""

    def __init__(self, config: Optional[RustClippyConfig] = None) -> None:
        self._config = config or RustClippyConfig()

    def analyze(self, scan_path: Optional[Path] = None) -> ToolReport:
        """
        Run cargo clippy against every crate found under scan_path.

        Raises ToolNotAvailableError if cargo is not on PATH.
        """
        path = Path(scan_path) if scan_path else self._config.scan_path
        path = path.resolve()
        start = datetime.now()

        report = ToolReport(scan_path=str(path), language="rust", tool="cargo-clippy")

        cargo_bin = require_executable(
            "cargo",
            path,
            "Install Rust via https://rustup.rs (this also installs cargo and clippy).",
        )

        crate_dirs = find_manifest_dirs(path, "Cargo.toml")
        if not crate_dirs:
            report.tools_unavailable.append(f"No Cargo.toml found under {path}; skipping cargo clippy.")
            report.scan_duration_seconds = (datetime.now() - start).total_seconds()
            return report

        report.files_analyzed = len(crate_dirs)

        for crate_dir in crate_dirs:
            self._analyze_crate(cargo_bin, crate_dir, path, report)
            if self._config.max_findings and report.total_findings >= self._config.max_findings:
                break

        report.scan_duration_seconds = (datetime.now() - start).total_seconds()
        return report

    def _analyze_crate(self, cargo_bin: str, crate_dir: Path, root: Path, report: ToolReport) -> None:
        cmd = [cargo_bin, "clippy", "--message-format=json", "--all-targets"]
        cmd.extend(self._config.extra_args)

        result = run_tool(cmd, cwd=crate_dir, timeout=self._config.timeout_seconds)

        if result.timed_out:
            report.tools_unavailable.append(
                f"cargo clippy timed out after {self._config.timeout_seconds}s in {crate_dir}"
            )
            report.tool_failed = True
            return

        if not result.stdout and result.returncode not in (0, 101):
            detail = (result.stderr or "unknown error").strip().splitlines()[-1:] or ["unknown error"]
            report.tools_unavailable.append(
                f"cargo clippy failed to run in {crate_dir}: {detail[0]}"
            )
            report.tool_failed = True
            return

        # cargo clippy --all-targets re-checks a binary crate once per target
        # (lib, bin, tests, examples) and emits the same diagnostic under each
        # target that shares the file, so de-duplicate on identity rather than
        # dropping --all-targets and losing coverage of test/example code.
        seen: set = set()
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if payload.get("reason") != "compiler-message":
                continue
            finding = self._finding_from_message(payload.get("message") or {}, crate_dir, root)
            if finding is None:
                continue
            identity = (finding.rule_id, finding.file_path, finding.line_number, finding.column)
            if identity in seen:
                continue
            seen.add(identity)
            report.add_finding(finding)
            if self._config.max_findings and report.total_findings >= self._config.max_findings:
                return

    def _finding_from_message(self, message: dict, crate_dir: Path, root: Path) -> Optional[ToolFinding]:
        level = message.get("level", "")
        severity = _LEVEL_TO_SEVERITY.get(level)
        if severity is None:
            return None

        spans = message.get("spans") or []
        primary = next((s for s in spans if s.get("is_primary")), spans[0] if spans else None)

        file_path = crate_dir.name
        line_number = 0
        column = 0
        code_snippet = ""
        if primary:
            file_name = primary.get("file_name", "")
            absolute = (crate_dir / file_name).resolve()
            try:
                file_path = str(absolute.relative_to(root))
            except ValueError:
                file_path = str(absolute)
            line_number = primary.get("line_start", 0) or 0
            column = primary.get("column_start", 0) or 0
            text_entries = primary.get("text") or []
            if text_entries:
                code_snippet = (text_entries[0].get("text") or "").strip()

        code = (message.get("code") or {}).get("code") or ""
        rule_id = code if code else f"rustc.{level}"

        return ToolFinding(
            file_path=file_path,
            line_number=line_number,
            column=column,
            rule_id=rule_id,
            category=self._category_for(rule_id),
            severity=severity,
            title=message.get("message", "")[:200],
            description=message.get("rendered") or message.get("message", ""),
            code_snippet=code_snippet,
            fix_suggestion="",
            tool="cargo-clippy",
        )

    @staticmethod
    def _category_for(rule_id: str) -> ToolCategory:
        if rule_id in _CLIPPY_SECURITY_LINTS or "unsafe" in rule_id:
            return ToolCategory.SECURITY
        if any(rule_id.startswith(prefix) for prefix in _CLIPPY_PERFORMANCE_PREFIXES):
            return ToolCategory.CODE_SMELL
        if not rule_id.startswith("clippy::"):
            return ToolCategory.BUG
        return ToolCategory.CODE_SMELL
