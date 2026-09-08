"""
Go formatting-drift detection via gofmt -l.

Orchestrates gofmt directly rather than reimplementing Go's canonical
formatting rules. `gofmt -l <dir>` recurses through the directory itself
(unlike `go vet`/`go build`, it needs no `./...` package pattern) and prints
one of two line shapes: a bare relative path for every file whose
formatting differs from gofmt's own output, or a `file:line:col: message`
diagnostic when gofmt cannot even parse a file. Verified against real
gofmt (go1.24.7, this sandbox): both shapes appear in the same run, and a
parse error changes the exit code from 0 (drift found, still exit 0) to 2
-- an unformatted-but-syntactically-valid tree is not an error, but one
gofmt cannot parse is.
"""

import re
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
from Asgard.Bragi.Quality.languages.go.models.go_toolchain_models import GoFmtConfig

INSTALL_HINT = "Install Go from https://go.dev/dl (gofmt ships with the go command)."

_PARSE_ERROR_RE = re.compile(r"^(?P<file>[^\s:][^:]*):(?P<line>\d+):(?P<column>\d+):\s*(?P<message>.+)$")


class GoFmtAnalyzer:
    """Runs gofmt -l over every module found under a scan path and normalises the output."""

    def __init__(self, config: Optional[GoFmtConfig] = None) -> None:
        self._config = config or GoFmtConfig()

    def analyze(self, scan_path: Optional[Path] = None) -> ToolReport:
        """
        Run gofmt -l against every Go module found under scan_path.

        Raises ToolNotAvailableError if gofmt is not on PATH.
        """
        path = Path(scan_path) if scan_path else self._config.scan_path
        path = path.resolve()
        start = datetime.now()

        report = ToolReport(scan_path=str(path), language="go", tool="gofmt")

        gofmt_bin = require_executable("gofmt", path, INSTALL_HINT)

        module_dirs = find_manifest_dirs(path, "go.mod")
        if not module_dirs:
            report.tools_unavailable.append(f"No go.mod found under {path}; skipping gofmt.")
            report.scan_duration_seconds = (datetime.now() - start).total_seconds()
            return report

        report.files_analyzed = len(module_dirs)

        for module_dir in module_dirs:
            self._check_module(gofmt_bin, module_dir, path, report)
            if self._config.max_findings and report.total_findings >= self._config.max_findings:
                break

        report.scan_duration_seconds = (datetime.now() - start).total_seconds()
        return report

    def _check_module(self, gofmt_bin: str, module_dir: Path, root: Path, report: ToolReport) -> None:
        cmd = [gofmt_bin, "-l", "."]
        result = run_tool(cmd, cwd=module_dir, timeout=self._config.timeout_seconds)

        if result.timed_out:
            report.tools_unavailable.append(
                f"gofmt timed out after {self._config.timeout_seconds}s in {module_dir}"
            )
            report.tool_failed = True
            return

        combined = result.stdout + result.stderr
        lines = [line.strip() for line in combined.splitlines() if line.strip()]

        # gofmt -l exits 0 for both "no drift" and "drift found", and only
        # exits non-zero when it could not even parse a file. A nonzero
        # exit with zero lines of output at all means gofmt itself did not
        # run (bad flags, an internal error) and must not read as clean.
        if result.returncode not in (0, 2) or (result.returncode != 0 and not lines):
            detail = lines[-1] if lines else "produced no output"
            report.tools_unavailable.append(
                f"gofmt failed in {module_dir} (exit {result.returncode}): {detail}"
            )
            report.tool_failed = True
            return

        for line in lines:
            match = _PARSE_ERROR_RE.match(line)
            if match:
                self._add_parse_error(match, module_dir, root, report)
            else:
                self._add_drift_finding(line, module_dir, root, report)
            if self._config.max_findings and report.total_findings >= self._config.max_findings:
                report.tool_failed = True
                report.tools_unavailable.append("gofmt finding limit reached; remaining diagnostics are unverified")
                return

    @staticmethod
    def _relative(file_str: str, module_dir: Path, root: Path) -> str:
        try:
            absolute = (module_dir / file_str).resolve()
            return str(absolute.relative_to(root))
        except ValueError:
            return file_str

    def _add_parse_error(self, match: "re.Match", module_dir: Path, root: Path, report: ToolReport) -> None:
        message = match.group("message").strip()
        report.add_finding(
            ToolFinding(
                file_path=self._relative(match.group("file"), module_dir, root),
                line_number=int(match.group("line")),
                column=int(match.group("column")),
                rule_id="gofmt.parse-error",
                category=ToolCategory.BUG,
                severity=ToolSeverity.ERROR,
                title=message[:200],
                description=message,
                code_snippet="",
                fix_suggestion="",
                tool="gofmt",
            )
        )

    def _add_drift_finding(self, file_str: str, module_dir: Path, root: Path, report: ToolReport) -> None:
        relative_path = self._relative(file_str, module_dir, root)
        report.add_finding(
            ToolFinding(
                file_path=relative_path,
                line_number=0,
                column=0,
                rule_id="gofmt.not-formatted",
                category=ToolCategory.STYLE,
                severity=ToolSeverity.WARNING,
                title=f"{relative_path} is not gofmt-formatted",
                description=f"{relative_path} differs from gofmt's canonical formatting.",
                code_snippet="",
                fix_suggestion=f"Run: gofmt -w {file_str}",
                tool="gofmt",
            )
        )
