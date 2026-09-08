"""
TypeScript type checking via tsc.

Orchestrates the TypeScript compiler's own diagnostics rather than
reimplementing type inference in Python. This is the TypeScript analogue of
Asgard.Bragi.Quality.services.type_checker's mypy/Pyright orchestration for
Python: same idea (shell out to the language's own checker, parse its
diagnostics), different language and output format.

Requires a tsconfig.json under the scan path; a project with none is
skipped gracefully (tsc without one only checks a single file at a time,
which is not a useful project-wide check).
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
from Asgard.Bragi.Quality.languages.common.tool_runner import resolve_node_tool, run_tool
from Asgard.Bragi.Quality.languages.node.models.node_toolchain_models import NodeTypecheckConfig

# tsc --pretty false output: "path/to/file.ts(line,col): error TS1234: message"
_DIAGNOSTIC_RE = re.compile(
    r"^(?P<file>.+?)\((?P<line>\d+),(?P<column>\d+)\):\s*(?P<level>error|warning)\s+"
    r"(?P<code>TS\d+):\s*(?P<message>.+)$"
)

_LEVEL_TO_SEVERITY = {"error": ToolSeverity.ERROR, "warning": ToolSeverity.WARNING}

INSTALL_HINT = "Install Node.js (which provides npx) from https://nodejs.org, then add typescript as a devDependency."


class NodeTypecheckAnalyzer:
    """Runs tsc --noEmit over a TypeScript project and normalises the output."""

    def __init__(self, config: Optional[NodeTypecheckConfig] = None) -> None:
        self._config = config or NodeTypecheckConfig()

    def analyze(self, scan_path: Optional[Path] = None) -> ToolReport:
        path = Path(scan_path) if scan_path else self._config.scan_path
        path = path.resolve()
        start = datetime.now()

        report = ToolReport(scan_path=str(path), language="node", tool="tsc")

        if not (path / "tsconfig.json").is_file():
            report.tools_unavailable.append(f"No tsconfig.json found under {path}; skipping tsc.")
            report.scan_duration_seconds = (datetime.now() - start).total_seconds()
            return report

        argv = resolve_node_tool("tsc", path, INSTALL_HINT)
        cmd = argv + ["--noEmit", "--pretty", "false"]

        result = run_tool(cmd, cwd=path, timeout=self._config.timeout_seconds)

        if result.timed_out:
            report.tools_unavailable.append(f"tsc timed out after {self._config.timeout_seconds}s")
            report.tool_failed = True
            report.scan_duration_seconds = (datetime.now() - start).total_seconds()
            return report

        combined_output = result.stdout + result.stderr
        files_seen = set()
        for line in combined_output.splitlines():
            match = _DIAGNOSTIC_RE.match(line.strip())
            if not match:
                continue
            finding = self._finding_from_match(match, path)
            files_seen.add(finding.file_path)
            report.add_finding(finding)
            if self._config.max_findings and report.total_findings >= self._config.max_findings:
                report.tool_failed = True
                report.tools_unavailable.append("tsc finding limit reached; remaining diagnostics are unverified")
                break

        # Exit 1 is also used for startup/configuration failures with no
        # per-file diagnostic. Every nonzero result must explain its failure
        # through parsed errors or remain a failed, unverified invocation.
        if report.error_count == 0 and result.returncode != 0:
            detail_lines = (result.stderr or result.stdout or "").strip().splitlines()
            detail = detail_lines[-1] if detail_lines else "produced no parseable diagnostics"
            report.tools_unavailable.append(f"tsc failed to run (exit {result.returncode}): {detail}")
            report.tool_failed = True

        report.files_analyzed = len(files_seen)
        report.scan_duration_seconds = (datetime.now() - start).total_seconds()
        return report

    @staticmethod
    def _finding_from_match(match: "re.Match", root: Path) -> ToolFinding:
        level = match.group("level")
        file_str = match.group("file")
        try:
            relative_path = str((root / file_str).resolve().relative_to(root))
        except ValueError:
            relative_path = file_str

        message = match.group("message").strip()
        return ToolFinding(
            file_path=relative_path,
            line_number=int(match.group("line")),
            column=int(match.group("column")),
            rule_id=match.group("code"),
            category=ToolCategory.TYPE,
            severity=_LEVEL_TO_SEVERITY.get(level, ToolSeverity.WARNING),
            title=message[:200],
            description=message,
            code_snippet="",
            fix_suggestion="",
            tool="tsc",
        )
