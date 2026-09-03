"""
Go correctness checking via go vet.

Orchestrates the Go toolchain's own static analyser rather than
reimplementing its checks (Printf format-verb mismatches, unreachable code,
struct tags, lock-by-value, and the rest of the standard vet analyzer suite)
in Python. Complements, rather than replaces, GoAnalyzer (the existing
regex-based scanner in this package): go vet has real type information and
catches classes of bug no regex rule can, while the regex scanner catches
project-specific security patterns (hardcoded credentials, command
injection) go vet has no opinion on.

Output format verified against real `go vet` (go1.24.7, this sandbox): a
`# <import path>` header per package with diagnostics, followed by
`<file>:<line>:<col>: <message>` lines -- parsed by
Asgard.Bragi.Quality.languages.go.services._go_diagnostics, shared with
GoBuildAnalyzer since both tools emit the identical shape.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional

from Asgard.Bragi.Quality.languages.common.tool_models import (
    ToolCategory,
    ToolFinding,
    ToolReport,
    ToolSeverity,
)
from Asgard.Bragi.Quality.languages.common.tool_runner import (
    find_manifest_dirs,
    require_executable,
    run_tool,
)
from Asgard.Bragi.Quality.languages.go.models.go_toolchain_models import GoVetConfig
from Asgard.Bragi.Quality.languages.go.services._go_diagnostics import parse_diagnostics

INSTALL_HINT = "Install Go from https://go.dev/dl (go vet ships with the go command)."


class GoVetAnalyzer:
    """Runs go vet over every module found under a scan path and normalises the output."""

    def __init__(self, config: Optional[GoVetConfig] = None) -> None:
        self._config = config or GoVetConfig()

    def analyze(self, scan_path: Optional[Path] = None) -> ToolReport:
        """
        Run go vet against every Go module found under scan_path.

        Raises ToolNotAvailableError if go is not on PATH.
        """
        path = Path(scan_path) if scan_path else self._config.scan_path
        path = path.resolve()
        start = datetime.now()

        report = ToolReport(scan_path=str(path), language="go", tool="go-vet")

        go_bin = require_executable("go", path, INSTALL_HINT)

        module_dirs = find_manifest_dirs(path, "go.mod")
        if not module_dirs:
            report.tools_unavailable.append(f"No go.mod found under {path}; skipping go vet.")
            report.scan_duration_seconds = (datetime.now() - start).total_seconds()
            return report

        report.files_analyzed = len(module_dirs)

        for module_dir in module_dirs:
            self._vet_module(go_bin, module_dir, path, report)
            if self._config.max_findings and report.total_findings >= self._config.max_findings:
                break

        report.scan_duration_seconds = (datetime.now() - start).total_seconds()
        return report

    def _vet_module(self, go_bin: str, module_dir: Path, root: Path, report: ToolReport) -> None:
        cmd = [go_bin, "vet", "./..."]
        result = run_tool(cmd, cwd=module_dir, timeout=self._config.timeout_seconds)

        if result.timed_out:
            report.tools_unavailable.append(
                f"go vet timed out after {self._config.timeout_seconds}s in {module_dir}"
            )
            report.tool_failed = True
            return

        # go vet writes diagnostics to stderr; stdout is normally empty.
        combined = result.stdout + result.stderr
        diagnostics = parse_diagnostics(combined, module_dir, root)

        # A clean vet run exits 0 with no output. Any other exit code with
        # zero parsed diagnostics means go vet itself did not complete a
        # real check (a malformed go.mod, a missing dependency it could not
        # even load) rather than that the module has no findings, and must
        # not be reported as a clean scan.
        if not diagnostics and result.returncode != 0:
            detail_lines = combined.strip().splitlines()
            detail = detail_lines[-1] if detail_lines else "produced no parseable diagnostics"
            report.tools_unavailable.append(
                f"go vet failed in {module_dir} (exit {result.returncode}): {detail}"
            )
            report.tool_failed = True
            return

        for diagnostic in diagnostics:
            report.add_finding(
                ToolFinding(
                    file_path=diagnostic.file_path,
                    line_number=diagnostic.line_number,
                    column=diagnostic.column,
                    rule_id="go-vet",
                    category=ToolCategory.BUG,
                    severity=ToolSeverity.ERROR,
                    title=diagnostic.message[:200],
                    description=diagnostic.message,
                    code_snippet="",
                    fix_suggestion="",
                    tool="go-vet",
                )
            )
            if self._config.max_findings and report.total_findings >= self._config.max_findings:
                return
