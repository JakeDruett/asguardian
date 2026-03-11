"""
Syntax checker service for Heimdall.

Runs syntax and linting checks using external tools like ruff, flake8, pylint, and mypy.
"""

import json
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from Asgard.Heimdall.Quality.models.syntax_models import (
    FileAnalysis,
    LinterType,
    SyntaxConfig,
    SyntaxIssue,
    SyntaxResult,
    SyntaxSeverity,
)


class SyntaxChecker:
    """
    Syntax and linting checker service.

    Uses external linters (ruff, flake8, pylint, mypy) to check code for
    syntax errors, linting violations, and style issues.
    """

    def __init__(self, config: SyntaxConfig):
        """Initialize the syntax checker."""
        self.config = config
        self._available_linters: Optional[List[LinterType]] = None

    def get_available_linters(self) -> List[LinterType]:
        """Check which linters are available on the system."""
        if self._available_linters is not None:
            return self._available_linters

        available = []
        linter_commands = {
            LinterType.RUFF: ["ruff", "--version"],
            LinterType.FLAKE8: ["flake8", "--version"],
            LinterType.PYLINT: ["pylint", "--version"],
            LinterType.MYPY: ["mypy", "--version"],
        }

        for linter, cmd in linter_commands.items():
            try:
                subprocess.run(
                    cmd,
                    capture_output=True,
                    timeout=5,
                    check=False,
                )
                available.append(linter)
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass

        self._available_linters = available
        return available

    def analyze(self) -> SyntaxResult:
        """
        Run syntax analysis on the configured path.

        Returns:
            SyntaxResult with all findings
        """
        start_time = time.time()
        scan_path = Path(self.config.scan_path).resolve()

        if not scan_path.exists():
            raise FileNotFoundError(f"Path not found: {scan_path}")

        # Get files to analyze
        files = self._get_files_to_scan(scan_path)

        # Determine which linters to use
        linters = self._get_linters_to_run()

        # Run linters and collect results
        all_issues: List[SyntaxIssue] = []
        for linter in linters:
            issues = self._run_linter(linter, scan_path, files)
            all_issues.extend(issues)

        # Group issues by file
        file_analyses = self._group_issues_by_file(all_issues, files, scan_path)

        # Filter by severity
        file_analyses = self._filter_by_severity(file_analyses)

        duration = time.time() - start_time

        return SyntaxResult(
            scan_path=str(scan_path),
            scanned_at=datetime.now(),
            scan_duration_seconds=duration,
            config=self.config,
            file_analyses=file_analyses,
        )

    def fix(self) -> Tuple[SyntaxResult, int]:
        """
        Run syntax analysis and fix auto-fixable issues.

        Returns:
            Tuple of (SyntaxResult after fixing, number of fixes applied)
        """
        scan_path = Path(self.config.scan_path).resolve()
        fixes_applied = 0

        # Use ruff for fixing if available
        if LinterType.RUFF in self.get_available_linters():
            fixes_applied = self._run_ruff_fix(scan_path)

        # Re-run analysis to get current state
        result = self.analyze()

        return result, fixes_applied

    def _get_files_to_scan(self, scan_path: Path) -> List[Path]:
        """Get list of files to scan based on config."""
        files = []

        if scan_path.is_file():
            if self._should_include_file(scan_path):
                files.append(scan_path)
        else:
            for ext in self.config.include_extensions:
                pattern = f"**/*{ext}"
                for file_path in scan_path.glob(pattern):
                    if self._should_include_file(file_path):
                        files.append(file_path)

        return sorted(files)

    def _should_include_file(self, file_path: Path) -> bool:
        """Check if a file should be included in analysis."""
        path_str = str(file_path)

        for pattern in self.config.exclude_patterns:
            if pattern in path_str:
                return False

        return True

    def _get_linters_to_run(self) -> List[LinterType]:
        """Determine which linters to run."""
        requested = self.config.linters or [LinterType.RUFF]
        available = self.get_available_linters()

        linters = [l for l in requested if l in available]

        if not linters:
            # Fall back to any available linter
            if LinterType.RUFF in available:
                linters = [LinterType.RUFF]
            elif LinterType.FLAKE8 in available:
                linters = [LinterType.FLAKE8]

        return linters

    def _run_linter(self, linter: LinterType, scan_path: Path, files: List[Path]) -> List[SyntaxIssue]:
        """Run a specific linter and parse its output."""
        if linter == LinterType.RUFF:
            return self._run_ruff(scan_path)
        elif linter == LinterType.FLAKE8:
            return self._run_flake8(scan_path)
        elif linter == LinterType.PYLINT:
            return self._run_pylint(scan_path)
        elif linter == LinterType.MYPY:
            return self._run_mypy(scan_path)
        return []

    def _run_ruff(self, scan_path: Path) -> List[SyntaxIssue]:
        """Run ruff linter and parse output."""
        issues = []

        try:
            # Build exclude args
            exclude_args = []
            for pattern in self.config.exclude_patterns:
                exclude_args.extend(["--exclude", pattern])

            cmd = [
                "ruff", "check",
                str(scan_path),
                "--output-format", "json",
            ] + exclude_args

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                check=False,
            )

            if result.stdout:
                try:
                    findings = json.loads(result.stdout)
                    for finding in findings:
                        severity = self._ruff_severity(finding.get("fix"))
                        issue = SyntaxIssue(
                            file_path=finding.get("filename", ""),
                            line_number=finding.get("location", {}).get("row", 0),
                            column=finding.get("location", {}).get("column", 0),
                            code=finding.get("code", ""),
                            message=finding.get("message", ""),
                            severity=severity,
                            linter=LinterType.RUFF,
                            fixable=finding.get("fix") is not None,
                            suggested_fix=finding.get("fix", {}).get("message") if finding.get("fix") else None,
                        )
                        issues.append(issue)
                except json.JSONDecodeError:
                    pass

        except subprocess.TimeoutExpired:
            pass
        except FileNotFoundError:
            pass

        return issues

    def _run_ruff_fix(self, scan_path: Path) -> int:
        """Run ruff with --fix and return number of fixes."""
        try:
            # Build exclude args
            exclude_args = []
            for pattern in self.config.exclude_patterns:
                exclude_args.extend(["--exclude", pattern])

            cmd = [
                "ruff", "check",
                str(scan_path),
                "--fix",
                "--output-format", "json",
            ] + exclude_args

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                check=False,
            )

            # Count fixes from output
            if result.stdout:
                try:
                    findings = json.loads(result.stdout)
                    return sum(1 for f in findings if f.get("fix"))
                except json.JSONDecodeError:
                    pass

        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        return 0

    def _run_flake8(self, scan_path: Path) -> List[SyntaxIssue]:
        """Run flake8 linter and parse output."""
        issues = []

        try:
            # Build exclude args
            exclude_str = ",".join(self.config.exclude_patterns)

            cmd = [
                "flake8",
                str(scan_path),
                "--format", "%(path)s:%(row)d:%(col)d:%(code)s:%(text)s",
                "--exclude", exclude_str,
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                check=False,
            )

            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue

                parts = line.split(":", 4)
                if len(parts) >= 5:
                    severity = self._flake8_severity(parts[3])
                    issue = SyntaxIssue(
                        file_path=parts[0],
                        line_number=int(parts[1]) if parts[1].isdigit() else 0,
                        column=int(parts[2]) if parts[2].isdigit() else 0,
                        code=parts[3],
                        message=parts[4],
                        severity=severity,
                        linter=LinterType.FLAKE8,
                        fixable=False,
                    )
                    issues.append(issue)

        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        return issues

    def _run_pylint(self, scan_path: Path) -> List[SyntaxIssue]:
        """Run pylint and parse output."""
        issues = []

        try:
            # Build ignore args
            ignore_str = ",".join(self.config.exclude_patterns)

            cmd = [
                "pylint",
                str(scan_path),
                "--output-format", "json",
                "--ignore", ignore_str,
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                check=False,
            )

            if result.stdout:
                try:
                    findings = json.loads(result.stdout)
                    for finding in findings:
                        severity = self._pylint_severity(finding.get("type", ""))
                        issue = SyntaxIssue(
                            file_path=finding.get("path", ""),
                            line_number=finding.get("line", 0),
                            column=finding.get("column", 0),
                            code=finding.get("message-id", ""),
                            message=finding.get("message", ""),
                            severity=severity,
                            linter=LinterType.PYLINT,
                            fixable=False,
                        )
                        issues.append(issue)
                except json.JSONDecodeError:
                    pass

        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        return issues

    def _run_mypy(self, scan_path: Path) -> List[SyntaxIssue]:
        """Run mypy type checker and parse output."""
        issues = []

        try:
            # Build exclude pattern
            exclude_pattern = "|".join(self.config.exclude_patterns)

            cmd = [
                "mypy",
                str(scan_path),
                "--output", "json",
                "--exclude", exclude_pattern,
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                check=False,
            )

            # Parse JSON output
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                try:
                    finding = json.loads(line)
                    severity = self._mypy_severity(finding.get("severity", "error"))
                    issue = SyntaxIssue(
                        file_path=finding.get("file", ""),
                        line_number=finding.get("line", 0),
                        column=finding.get("column", 0),
                        code=finding.get("code", "mypy"),
                        message=finding.get("message", ""),
                        severity=severity,
                        linter=LinterType.MYPY,
                        fixable=False,
                    )
                    issues.append(issue)
                except json.JSONDecodeError:
                    # Fall back to text parsing
                    pass

        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        return issues

    def _ruff_severity(self, fix_info: Optional[dict]) -> SyntaxSeverity:
        """Convert ruff fix info to severity."""
        # Ruff doesn't have severity, classify by code prefix
        return SyntaxSeverity.WARNING

    def _flake8_severity(self, code: str) -> SyntaxSeverity:
        """Convert flake8 code to severity."""
        if code.startswith("E"):
            return SyntaxSeverity.ERROR
        elif code.startswith("W"):
            return SyntaxSeverity.WARNING
        elif code.startswith("F"):
            return SyntaxSeverity.ERROR
        elif code.startswith("C"):
            return SyntaxSeverity.STYLE
        return SyntaxSeverity.INFO

    def _pylint_severity(self, msg_type: str) -> SyntaxSeverity:
        """Convert pylint message type to severity."""
        type_map = {
            "error": SyntaxSeverity.ERROR,
            "fatal": SyntaxSeverity.ERROR,
            "warning": SyntaxSeverity.WARNING,
            "convention": SyntaxSeverity.STYLE,
            "refactor": SyntaxSeverity.INFO,
            "information": SyntaxSeverity.INFO,
        }
        return type_map.get(msg_type.lower(), SyntaxSeverity.WARNING)

    def _mypy_severity(self, severity: str) -> SyntaxSeverity:
        """Convert mypy severity to our severity."""
        severity_map = {
            "error": SyntaxSeverity.ERROR,
            "warning": SyntaxSeverity.WARNING,
            "note": SyntaxSeverity.INFO,
        }
        return severity_map.get(severity.lower(), SyntaxSeverity.ERROR)

    def _group_issues_by_file(
        self,
        issues: List[SyntaxIssue],
        files: List[Path],
        scan_path: Path
    ) -> List[FileAnalysis]:
        """Group issues by file and create FileAnalysis objects."""
        # Create a mapping of absolute path to issues
        issues_by_file: dict[str, List[SyntaxIssue]] = {}
        for issue in issues:
            abs_path = str(Path(issue.file_path).resolve())
            if abs_path not in issues_by_file:
                issues_by_file[abs_path] = []
            issues_by_file[abs_path].append(issue)

        # Create FileAnalysis for each scanned file
        file_analyses = []
        all_files = set(str(f.resolve()) for f in files)

        for file_path_str in all_files:
            file_path = Path(file_path_str)
            try:
                rel_path = str(file_path.relative_to(scan_path))
            except ValueError:
                rel_path = str(file_path)

            file_issues = issues_by_file.get(file_path_str, [])

            fa = FileAnalysis(
                file_path=file_path_str,
                relative_path=rel_path,
                issues=file_issues,
                error_count=sum(1 for i in file_issues if i.severity == SyntaxSeverity.ERROR),
                warning_count=sum(1 for i in file_issues if i.severity == SyntaxSeverity.WARNING),
                info_count=sum(1 for i in file_issues if i.severity == SyntaxSeverity.INFO),
                style_count=sum(1 for i in file_issues if i.severity == SyntaxSeverity.STYLE),
            )
            file_analyses.append(fa)

        # Sort by relative path
        file_analyses.sort(key=lambda x: x.relative_path)

        return file_analyses

    def _filter_by_severity(self, file_analyses: List[FileAnalysis]) -> List[FileAnalysis]:
        """Filter issues by minimum severity."""
        severity_order = [
            SyntaxSeverity.ERROR,
            SyntaxSeverity.WARNING,
            SyntaxSeverity.INFO,
            SyntaxSeverity.STYLE,
        ]

        min_index = severity_order.index(self.config.min_severity)
        allowed_severities = set(severity_order[:min_index + 1])

        if not self.config.include_style:
            allowed_severities.discard(SyntaxSeverity.STYLE)

        for fa in file_analyses:
            fa.issues = [i for i in fa.issues if i.severity in allowed_severities]
            fa.error_count = sum(1 for i in fa.issues if i.severity == SyntaxSeverity.ERROR)
            fa.warning_count = sum(1 for i in fa.issues if i.severity == SyntaxSeverity.WARNING)
            fa.info_count = sum(1 for i in fa.issues if i.severity == SyntaxSeverity.INFO)
            fa.style_count = sum(1 for i in fa.issues if i.severity == SyntaxSeverity.STYLE)

        return file_analyses

    def generate_report(self, result: SyntaxResult, output_format: str = "text") -> str:
        """Generate a formatted report."""
        if output_format == "json":
            return self._generate_json_report(result)
        elif output_format == "markdown":
            return self._generate_markdown_report(result)
        else:
            return self._generate_text_report(result)

    def _generate_text_report(self, result: SyntaxResult) -> str:
        """Generate text format report."""
        lines = []
        lines.append("")
        lines.append("=" * 70)
        lines.append("  HEIMDALL SYNTAX CHECK REPORT")
        lines.append("=" * 70)
        lines.append("")
        lines.append(f"  Scan Path:    {result.scan_path}")
        lines.append(f"  Scanned At:   {result.scanned_at.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"  Duration:     {result.scan_duration_seconds:.2f}s")
        lines.append(f"  Linters:      {', '.join(l.value for l in self._get_linters_to_run())}")
        lines.append("")

        if result.has_issues:
            lines.append("-" * 70)
            lines.append("  ISSUES FOUND")
            lines.append("-" * 70)
            lines.append("")

            # Group by severity
            by_severity = result.get_issues_by_severity()

            for severity in [SyntaxSeverity.ERROR, SyntaxSeverity.WARNING, SyntaxSeverity.INFO]:
                issues = by_severity.get(severity.value, [])
                if issues:
                    lines.append(f"  [{severity.value.upper()}] ({len(issues)} issues)")
                    lines.append("")
                    for issue in issues[:20]:  # Show first 20
                        lines.append(f"    {issue.location}")
                        lines.append(f"      [{issue.code}] {issue.message}")
                        if issue.fixable:
                            lines.append(f"      (auto-fixable)")
                        lines.append("")
                    if len(issues) > 20:
                        lines.append(f"    ... and {len(issues) - 20} more")
                        lines.append("")

        else:
            lines.append("  No syntax issues found!")
            lines.append("")

        lines.append("-" * 70)
        lines.append("  SUMMARY")
        lines.append("-" * 70)
        lines.append("")
        lines.append(f"  Files Scanned:      {result.total_files_scanned}")
        lines.append(f"  Files with Issues:  {result.files_with_issues}")
        lines.append(f"  Total Issues:       {result.total_issues}")
        lines.append(f"    Errors:           {result.total_errors}")
        lines.append(f"    Warnings:         {result.total_warnings}")
        lines.append(f"    Info:             {result.total_info}")
        lines.append(f"    Style:            {result.total_style}")
        lines.append(f"  Compliance Rate:    {result.compliance_rate:.1f}%")

        fixable = result.get_fixable_issues()
        if fixable:
            lines.append(f"  Auto-fixable:       {len(fixable)}")

        lines.append("")
        lines.append("=" * 70)
        lines.append("")

        return "\n".join(lines)

    def _generate_json_report(self, result: SyntaxResult) -> str:
        """Generate JSON format report."""
        output = {
            "scan_path": result.scan_path,
            "scanned_at": result.scanned_at.isoformat(),
            "scan_duration_seconds": result.scan_duration_seconds,
            "linters": [l.value for l in self._get_linters_to_run()],
            "summary": {
                "total_files_scanned": result.total_files_scanned,
                "files_with_issues": result.files_with_issues,
                "total_issues": result.total_issues,
                "errors": result.total_errors,
                "warnings": result.total_warnings,
                "info": result.total_info,
                "style": result.total_style,
                "compliance_rate": round(result.compliance_rate, 2),
                "fixable_count": len(result.get_fixable_issues()),
            },
            "files": [
                {
                    "path": fa.relative_path,
                    "issues": [
                        {
                            "line": i.line_number,
                            "column": i.column,
                            "code": i.code,
                            "message": i.message,
                            "severity": i.severity.value,
                            "linter": i.linter.value,
                            "fixable": i.fixable,
                        }
                        for i in fa.issues
                    ],
                }
                for fa in result.file_analyses
                if fa.has_issues
            ],
        }

        return json.dumps(output, indent=2)

    def _generate_markdown_report(self, result: SyntaxResult) -> str:
        """Generate Markdown format report."""
        lines = []
        lines.append("# Heimdall Syntax Check Report")
        lines.append("")
        lines.append(f"- **Scan Path:** `{result.scan_path}`")
        lines.append(f"- **Scanned At:** {result.scanned_at.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"- **Duration:** {result.scan_duration_seconds:.2f}s")
        lines.append(f"- **Linters:** {', '.join(l.value for l in self._get_linters_to_run())}")
        lines.append("")

        lines.append("## Summary")
        lines.append("")
        lines.append(f"- **Files Scanned:** {result.total_files_scanned}")
        lines.append(f"- **Files with Issues:** {result.files_with_issues}")
        lines.append(f"- **Total Issues:** {result.total_issues}")
        lines.append(f"  - Errors: {result.total_errors}")
        lines.append(f"  - Warnings: {result.total_warnings}")
        lines.append(f"  - Info: {result.total_info}")
        lines.append(f"  - Style: {result.total_style}")
        lines.append(f"- **Compliance Rate:** {result.compliance_rate:.1f}%")
        lines.append(f"- **Auto-fixable:** {len(result.get_fixable_issues())}")
        lines.append("")

        if result.has_issues:
            lines.append("## Issues")
            lines.append("")
            lines.append("| File | Line | Code | Severity | Message |")
            lines.append("|------|------|------|----------|---------|")

            for fa in result.file_analyses:
                for issue in fa.issues[:50]:  # Limit for readability
                    lines.append(
                        f"| `{fa.relative_path}` | {issue.line_number} | "
                        f"{issue.code} | {issue.severity.value.upper()} | {issue.message[:50]} |"
                    )

            if result.total_issues > 50:
                lines.append("")
                lines.append(f"*... and {result.total_issues - 50} more issues*")

        lines.append("")

        return "\n".join(lines)
