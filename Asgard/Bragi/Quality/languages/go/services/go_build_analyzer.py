"""
Go compile-failure detection via go build.

Orchestrates the real Go compiler rather than guessing at compilability from
source patterns. This is deliberately narrow: it exists to make a module
that does not compile an unmistakable, always-non-zero finding -- the
GAIA/Keryx checkout is a live example, since its go.mod's `replace
gaia/lexicon => ../Lexicon/LexiconGo` only resolves from inside a GAIA
checkout that has Lexicon cloned as its sibling, and reports a real,
parseable file:line:col diagnostic per import site when that path is
missing rather than some opaque tooling error.

Every build output is discarded into a throwaway temp directory (`go build
-o <tmp>/ ./...`) rather than the scanned tree's own working directory,
since `go build` without `-o` writes a real executable per `main` package
into the current directory as a side effect -- running this analyser must
never leave build artifacts inside a project it only scanned.
"""

import shutil
import tempfile
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
from Asgard.Bragi.Quality.languages.go.models.go_toolchain_models import GoBuildConfig
from Asgard.Bragi.Quality.languages.go.services._go_diagnostics import parse_diagnostics

INSTALL_HINT = "Install Go from https://go.dev/dl"


class GoBuildAnalyzer:
    """Runs go build over every module found under a scan path and normalises the output."""

    def __init__(self, config: Optional[GoBuildConfig] = None) -> None:
        self._config = config or GoBuildConfig()

    def analyze(self, scan_path: Optional[Path] = None) -> ToolReport:
        """
        Run go build against every Go module found under scan_path.

        Raises ToolNotAvailableError if go is not on PATH.
        """
        path = Path(scan_path) if scan_path else self._config.scan_path
        path = path.resolve()
        start = datetime.now()

        report = ToolReport(scan_path=str(path), language="go", tool="go-build")

        go_bin = require_executable("go", path, INSTALL_HINT)

        module_dirs = find_manifest_dirs(path, "go.mod")
        if not module_dirs:
            report.tools_unavailable.append(f"No go.mod found under {path}; skipping go build.")
            report.scan_duration_seconds = (datetime.now() - start).total_seconds()
            return report

        report.files_analyzed = len(module_dirs)

        for module_dir in module_dirs:
            self._build_module(go_bin, module_dir, path, report)
            if self._config.max_findings and report.total_findings >= self._config.max_findings:
                break

        report.scan_duration_seconds = (datetime.now() - start).total_seconds()
        return report

    def _build_module(self, go_bin: str, module_dir: Path, root: Path, report: ToolReport) -> None:
        discard_dir = tempfile.mkdtemp(prefix="asguardian-go-build-")
        try:
            cmd = [go_bin, "build", "-o", discard_dir + "/", "./..."]
            result = run_tool(cmd, cwd=module_dir, timeout=self._config.timeout_seconds)
        finally:
            shutil.rmtree(discard_dir, ignore_errors=True)

        if result.timed_out:
            report.tools_unavailable.append(
                f"go build timed out after {self._config.timeout_seconds}s in {module_dir}"
            )
            report.tool_failed = True
            return

        combined = result.stdout + result.stderr
        diagnostics = parse_diagnostics(combined, module_dir, root)

        # A successful build exits 0 with no output. Any other exit code
        # with zero parsed diagnostics -- a malformed go.mod, an unresolved
        # `replace` directive whose message has no file:line:col shape --
        # is a genuine compile failure that must not be reported as clean
        # just because it did not fit the per-file diagnostic pattern.
        if result.returncode != 0:
            if not diagnostics:
                detail_lines = combined.strip().splitlines()
                detail = detail_lines[-1] if detail_lines else "produced no parseable diagnostics"
                report.tools_unavailable.append(
                    f"go build failed in {module_dir} (exit {result.returncode}): {detail}"
                )
                report.tool_failed = True
                return
            for diagnostic in diagnostics:
                report.add_finding(
                    ToolFinding(
                        file_path=diagnostic.file_path,
                        line_number=diagnostic.line_number,
                        column=diagnostic.column,
                        rule_id="go-build",
                        category=ToolCategory.BUG,
                        severity=ToolSeverity.ERROR,
                        title=f"Compile error: {diagnostic.message[:180]}",
                        description=diagnostic.message,
                        code_snippet="",
                        fix_suggestion="",
                        tool="go-build",
                    )
                )
                if self._config.max_findings and report.total_findings >= self._config.max_findings:
                    return
