"""
Heimdall Shell Script Analyzer

Regex and text-based static analysis for shell scripts (.sh, .bash, and
files with bash/sh shebangs). Implements security, bug, style, and
portability rules using line-by-line pattern matching.
"""

import re
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from Asgard.Heimdall.Quality.languages.shell.models.shell_models import (
    ShellAnalysisConfig,
    ShellFinding,
    ShellReport,
    ShellRuleCategory,
    ShellSeverity,
)


_SHEBANG_PATTERNS = [
    "#!/bin/bash",
    "#!/bin/sh",
    "#!/usr/bin/env bash",
    "#!/usr/bin/env sh",
]


def _has_shell_shebang(content: str) -> bool:
    """Return True if the first line of content is a recognised bash/sh shebang."""
    first_line = content.split("\n", 1)[0].strip()
    return any(first_line.startswith(shebang) for shebang in _SHEBANG_PATTERNS)


def _make_finding(
    file_path: str,
    line_number: int,
    rule_id: str,
    category: ShellRuleCategory,
    severity: ShellSeverity,
    title: str,
    description: str,
    code_snippet: str = "",
    fix_suggestion: str = "",
) -> ShellFinding:
    """Helper to construct a ShellFinding with consistent field population."""
    return ShellFinding(
        file_path=file_path,
        line_number=line_number,
        rule_id=rule_id,
        category=category,
        severity=severity,
        title=title,
        description=description,
        code_snippet=code_snippet.strip(),
        fix_suggestion=fix_suggestion,
    )


class ShellAnalyzer:
    """
    Regex-based static analyzer for shell scripts.

    Detects security vulnerabilities, common bugs, style issues, and
    portability problems in bash and sh scripts.

    Usage:
        config = ShellAnalysisConfig(scan_path=Path("./scripts"))
        analyzer = ShellAnalyzer(config)
        report = analyzer.analyze(Path("./scripts"))
    """

    def __init__(self, config: Optional[ShellAnalysisConfig] = None):
        """
        Initialise the shell analyzer.

        Args:
            config: Analysis configuration. Defaults to ShellAnalysisConfig() with default values.
        """
        self._config = config or ShellAnalysisConfig()

    def analyze(self, scan_path: Optional[Path] = None) -> ShellReport:
        """
        Scan a directory tree for shell scripts and apply all enabled rules.

        Args:
            scan_path: Root path to scan. Falls back to config.scan_path.

        Returns:
            ShellReport containing all findings.
        """
        root = Path(scan_path) if scan_path else self._config.scan_path
        root = root.resolve()

        start_time = time.monotonic()
        report = ShellReport(
            scan_path=str(root),
            scanned_at=datetime.now(),
        )

        files = self._collect_files(root)
        for file_path in files:
            findings = self._analyze_file(file_path)
            for finding in findings:
                report.add_finding(finding)

        report.files_analyzed = len(files)
        report.scan_duration_seconds = time.monotonic() - start_time
        return report

    def _collect_files(self, root: Path) -> List[Path]:
        """Collect all shell files: by extension, and optionally by shebang."""
        exclude = self._config.exclude_patterns
        collected: List[Path] = []
        seen: set = set()

        for ext in self._config.include_extensions:
            for file_path in root.rglob(f"*{ext}"):
                path_str = str(file_path)
                if any(pattern in path_str for pattern in exclude):
                    continue
                if path_str not in seen:
                    seen.add(path_str)
                    collected.append(file_path)

        if self._config.also_check_shebangs:
            for file_path in root.rglob("*"):
                if not file_path.is_file():
                    continue
                path_str = str(file_path)
                if path_str in seen:
                    continue
                if any(pattern in path_str for pattern in exclude):
                    continue
                # Only check files with no extension
                if file_path.suffix:
                    continue
                try:
                    content = file_path.read_text(encoding="utf-8", errors="replace")
                    if _has_shell_shebang(content):
                        seen.add(path_str)
                        collected.append(file_path)
                except OSError:
                    continue

        return sorted(collected)

    def _analyze_file(self, file_path: Path) -> List[ShellFinding]:
        """Run all enabled rules against a single shell file."""
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return []

        lines = content.splitlines()
        path_str = str(file_path)
        findings: List[ShellFinding] = []

        # Security rules
        findings.extend(self._rule_eval_injection(path_str, lines))
        findings.extend(self._rule_unquoted_variable_in_command(path_str, lines))
        findings.extend(self._rule_curl_insecure(path_str, lines))
        findings.extend(self._rule_wget_no_check(path_str, lines))
        findings.extend(self._rule_hardcoded_password(path_str, lines))
        findings.extend(self._rule_command_injection(path_str, lines))
        findings.extend(self._rule_sudo_without_sudoers(path_str, lines))

        # Bug rules
        findings.extend(self._rule_unquoted_variable(path_str, lines))
        findings.extend(self._rule_use_dollar_star(path_str, lines))
        findings.extend(self._rule_missing_exit_on_error(path_str, content))
        findings.extend(self._rule_missing_unset_error(path_str, content))
        findings.extend(self._rule_cd_without_check(path_str, lines))
        findings.extend(self._rule_comparison_without_brackets(path_str, lines))

        # Style rules
        findings.extend(self._rule_use_double_brackets(path_str, lines))
        findings.extend(self._rule_function_definition(path_str, lines))
        findings.extend(self._rule_trailing_whitespace(path_str, lines))
        findings.extend(self._rule_long_line(path_str, lines))

        return findings

    # --- Security Rules ---

    def _rule_eval_injection(self, file_path: str, lines: List[str]) -> List[ShellFinding]:
        """shell.eval-injection: eval with a variable — potential code injection."""
        if not self._config.is_rule_enabled("shell.eval-injection"):
            return []
        findings = []
        pattern = re.compile(r'\beval\s+\$')
        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if pattern.search(line):
                findings.append(_make_finding(
                    file_path=file_path,
                    line_number=i,
                    rule_id="shell.eval-injection",
                    category=ShellRuleCategory.SECURITY,
                    severity=ShellSeverity.ERROR,
                    title="eval with variable input (potential injection)",
                    description=(
                        "Using eval with a variable can execute arbitrary code if the variable "
                        "contains attacker-controlled input."
                    ),
                    code_snippet=line,
                    fix_suggestion="Avoid eval entirely. Refactor to use functions or arrays instead.",
                ))
        return findings

    def _rule_unquoted_variable_in_command(self, file_path: str, lines: List[str]) -> List[ShellFinding]:
        """shell.unquoted-variable-in-command: Unquoted variable in rm -rf command."""
        if not self._config.is_rule_enabled("shell.unquoted-variable-in-command"):
            return []
        findings = []
        # rm -rf $VAR without quotes
        pattern = re.compile(r'\brm\b.*\$[A-Za-z_][A-Za-z0-9_]*\b(?!\s*")')
        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if pattern.search(line):
                # Make sure the variable is not quoted
                if '"$' not in line:
                    findings.append(_make_finding(
                        file_path=file_path,
                        line_number=i,
                        rule_id="shell.unquoted-variable-in-command",
                        category=ShellRuleCategory.SECURITY,
                        severity=ShellSeverity.WARNING,
                        title="Unquoted variable in rm command",
                        description=(
                            "Using an unquoted variable with rm can cause word splitting or "
                            "unexpected file deletion if the variable contains spaces or globs."
                        ),
                        code_snippet=line,
                        fix_suggestion='Quote the variable: rm -rf "$DIR".',
                    ))
        return findings

    def _rule_curl_insecure(self, file_path: str, lines: List[str]) -> List[ShellFinding]:
        """shell.curl-insecure: curl with -k or --insecure flag."""
        if not self._config.is_rule_enabled("shell.curl-insecure"):
            return []
        findings = []
        pattern = re.compile(r'\bcurl\b.*(?:-k\b|--insecure\b)')
        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if pattern.search(line):
                findings.append(_make_finding(
                    file_path=file_path,
                    line_number=i,
                    rule_id="shell.curl-insecure",
                    category=ShellRuleCategory.SECURITY,
                    severity=ShellSeverity.WARNING,
                    title="curl with TLS verification disabled",
                    description=(
                        "Using curl -k or --insecure disables TLS certificate verification, "
                        "making the connection vulnerable to man-in-the-middle attacks."
                    ),
                    code_snippet=line,
                    fix_suggestion="Remove -k/--insecure and ensure the server certificate is valid.",
                ))
        return findings

    def _rule_wget_no_check(self, file_path: str, lines: List[str]) -> List[ShellFinding]:
        """shell.wget-no-check: wget with --no-check-certificate."""
        if not self._config.is_rule_enabled("shell.wget-no-check"):
            return []
        findings = []
        pattern = re.compile(r'\bwget\b.*--no-check-certificate\b')
        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if pattern.search(line):
                findings.append(_make_finding(
                    file_path=file_path,
                    line_number=i,
                    rule_id="shell.wget-no-check",
                    category=ShellRuleCategory.SECURITY,
                    severity=ShellSeverity.WARNING,
                    title="wget with certificate verification disabled",
                    description=(
                        "Using wget --no-check-certificate disables TLS certificate verification, "
                        "making the connection vulnerable to man-in-the-middle attacks."
                    ),
                    code_snippet=line,
                    fix_suggestion="Remove --no-check-certificate and ensure the server certificate is valid.",
                ))
        return findings

    def _rule_hardcoded_password(self, file_path: str, lines: List[str]) -> List[ShellFinding]:
        """shell.hardcoded-password: Sensitive variable assigned a literal value."""
        if not self._config.is_rule_enabled("shell.hardcoded-password"):
            return []
        findings = []
        pattern = re.compile(
            r'\b(?:PASSWORD|PASSWD|SECRET|API_KEY|TOKEN|PRIVATE_KEY)\s*=\s*(?!"\$|\'?\$)["\']?[^$\s\'"][^\s]*'
        )
        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if pattern.search(line):
                findings.append(_make_finding(
                    file_path=file_path,
                    line_number=i,
                    rule_id="shell.hardcoded-password",
                    category=ShellRuleCategory.SECURITY,
                    severity=ShellSeverity.ERROR,
                    title="Hardcoded credential or secret",
                    description=(
                        "A sensitive variable appears to be assigned a hardcoded literal value. "
                        "Credentials should never be hardcoded in scripts."
                    ),
                    code_snippet=line,
                    fix_suggestion="Read credentials from environment variables or a secrets manager.",
                ))
        return findings

    def _rule_command_injection(self, file_path: str, lines: List[str]) -> List[ShellFinding]:
        """shell.command-injection: Backtick command substitution with variable input."""
        if not self._config.is_rule_enabled("shell.command-injection"):
            return []
        findings = []
        # Backtick substitution containing a variable
        pattern = re.compile(r'`[^`]*\$[A-Za-z_][A-Za-z0-9_]*[^`]*`')
        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if pattern.search(line):
                findings.append(_make_finding(
                    file_path=file_path,
                    line_number=i,
                    rule_id="shell.command-injection",
                    category=ShellRuleCategory.SECURITY,
                    severity=ShellSeverity.WARNING,
                    title="Backtick command substitution with variable",
                    description=(
                        "Using backtick command substitution with variable input can lead to "
                        "command injection if the variable contains attacker-controlled data."
                    ),
                    code_snippet=line,
                    fix_suggestion="Use $(command) instead of backticks and validate/sanitize input variables.",
                ))
        return findings

    def _rule_sudo_without_sudoers(self, file_path: str, lines: List[str]) -> List[ShellFinding]:
        """shell.sudo-without-sudoers: sudo usage flagged for review."""
        if not self._config.is_rule_enabled("shell.sudo-without-sudoers"):
            return []
        findings = []
        pattern = re.compile(r'\bsudo\s+')
        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if pattern.search(line):
                findings.append(_make_finding(
                    file_path=file_path,
                    line_number=i,
                    rule_id="shell.sudo-without-sudoers",
                    category=ShellRuleCategory.SECURITY,
                    severity=ShellSeverity.INFO,
                    title="sudo usage requires review",
                    description=(
                        "Script uses sudo. Ensure the command is safe, necessary, and that "
                        "sudoers permissions are properly configured."
                    ),
                    code_snippet=line,
                    fix_suggestion="Review sudo usage and ensure it is limited to the minimum required privileges.",
                ))
        return findings

    # --- Bug Rules ---

    def _rule_unquoted_variable(self, file_path: str, lines: List[str]) -> List[ShellFinding]:
        """shell.unquoted-variable: Variable used without double quotes (word splitting risk)."""
        if not self._config.is_rule_enabled("shell.unquoted-variable"):
            return []
        findings = []
        # Match $VAR not preceded or followed by quotes in common argument positions
        # Simple heuristic: $VAR at start of a word that is not inside "..."
        pattern = re.compile(r'(?<!")(?<!\$)\$[A-Za-z_][A-Za-z0-9_]*\b(?!")')
        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            # Skip lines that are purely variable assignments
            if re.match(r'^[A-Za-z_][A-Za-z0-9_]*=', stripped):
                continue
            if pattern.search(line):
                findings.append(_make_finding(
                    file_path=file_path,
                    line_number=i,
                    rule_id="shell.unquoted-variable",
                    category=ShellRuleCategory.BUG,
                    severity=ShellSeverity.WARNING,
                    title="Unquoted variable reference",
                    description=(
                        "Unquoted variables are subject to word splitting and glob expansion, "
                        "which can cause unexpected behavior."
                    ),
                    code_snippet=line,
                    fix_suggestion='Quote the variable: "$VAR" instead of $VAR.',
                ))
        return findings

    def _rule_use_dollar_star(self, file_path: str, lines: List[str]) -> List[ShellFinding]:
        """shell.use-dollar-star: $* instead of "$@" loses argument boundaries."""
        if not self._config.is_rule_enabled("shell.use-dollar-star"):
            return []
        findings = []
        pattern = re.compile(r'\$\*')
        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if pattern.search(line):
                findings.append(_make_finding(
                    file_path=file_path,
                    line_number=i,
                    rule_id="shell.use-dollar-star",
                    category=ShellRuleCategory.BUG,
                    severity=ShellSeverity.WARNING,
                    title="Use of $* instead of \"$@\"",
                    description=(
                        '$* does not preserve argument boundaries with spaces. '
                        'Use "$@" to correctly pass all arguments.'
                    ),
                    code_snippet=line,
                    fix_suggestion='Replace $* with "$@".',
                ))
        return findings

    def _rule_missing_exit_on_error(self, file_path: str, content: str) -> List[ShellFinding]:
        """shell.missing-exit-on-error: Script does not have set -e or set -o errexit."""
        if not self._config.is_rule_enabled("shell.missing-exit-on-error"):
            return []
        errexit_pattern = re.compile(r'\bset\s+.*-[a-zA-Z]*e[a-zA-Z]*\b|\bset\s+-o\s+errexit\b')
        if not errexit_pattern.search(content):
            return [_make_finding(
                file_path=file_path,
                line_number=1,
                rule_id="shell.missing-exit-on-error",
                category=ShellRuleCategory.BUG,
                severity=ShellSeverity.INFO,
                title="Missing set -e (exit on error)",
                description=(
                    "Script does not use 'set -e' or 'set -o errexit'. Without this, "
                    "failed commands are silently ignored."
                ),
                code_snippet="",
                fix_suggestion="Add 'set -e' near the top of the script after the shebang.",
            )]
        return []

    def _rule_missing_unset_error(self, file_path: str, content: str) -> List[ShellFinding]:
        """shell.missing-unset-error: Script does not have set -u or set -o nounset."""
        if not self._config.is_rule_enabled("shell.missing-unset-error"):
            return []
        nounset_pattern = re.compile(r'\bset\s+.*-[a-zA-Z]*u[a-zA-Z]*\b|\bset\s+-o\s+nounset\b')
        if not nounset_pattern.search(content):
            return [_make_finding(
                file_path=file_path,
                line_number=1,
                rule_id="shell.missing-unset-error",
                category=ShellRuleCategory.BUG,
                severity=ShellSeverity.INFO,
                title="Missing set -u (treat unset variables as errors)",
                description=(
                    "Script does not use 'set -u' or 'set -o nounset'. Without this, "
                    "references to unset variables expand to empty string silently."
                ),
                code_snippet="",
                fix_suggestion="Add 'set -u' near the top of the script after the shebang.",
            )]
        return []

    def _rule_cd_without_check(self, file_path: str, lines: List[str]) -> List[ShellFinding]:
        """shell.cd-without-check: cd command without error handling."""
        if not self._config.is_rule_enabled("shell.cd-without-check"):
            return []
        findings = []
        # cd without || or && following it on the same line
        cd_pattern = re.compile(r'\bcd\s+\S')
        safe_cd_pattern = re.compile(r'\bcd\s+.*(?:\|\||&&|;)')
        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if cd_pattern.search(line) and not safe_cd_pattern.search(line):
                findings.append(_make_finding(
                    file_path=file_path,
                    line_number=i,
                    rule_id="shell.cd-without-check",
                    category=ShellRuleCategory.BUG,
                    severity=ShellSeverity.WARNING,
                    title="cd without error check",
                    description=(
                        "If cd fails, subsequent commands will run in the wrong directory. "
                        "Always check cd return value."
                    ),
                    code_snippet=line,
                    fix_suggestion="Use: cd /path || exit 1  or  cd /path && do_something.",
                ))
        return findings

    def _rule_comparison_without_brackets(self, file_path: str, lines: List[str]) -> List[ShellFinding]:
        """shell.comparison-without-brackets: if condition without [ ] or [[ ]]."""
        if not self._config.is_rule_enabled("shell.comparison-without-brackets"):
            return []
        findings = []
        # if $var == value without brackets
        pattern = re.compile(r'\bif\s+\$[A-Za-z_][A-Za-z0-9_]*\s*[=!<>]')
        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if pattern.search(line):
                findings.append(_make_finding(
                    file_path=file_path,
                    line_number=i,
                    rule_id="shell.comparison-without-brackets",
                    category=ShellRuleCategory.BUG,
                    severity=ShellSeverity.ERROR,
                    title="Comparison without test brackets",
                    description=(
                        "String comparison outside [ ] or [[ ]] does not work as expected in shell."
                    ),
                    code_snippet=line,
                    fix_suggestion='Use: if [[ "$VAR" == "value" ]]; then',
                ))
        return findings

    # --- Style Rules ---

    def _rule_use_double_brackets(self, file_path: str, lines: List[str]) -> List[ShellFinding]:
        """shell.use-double-brackets: [ ] instead of [[ ]] for conditionals."""
        if not self._config.is_rule_enabled("shell.use-double-brackets"):
            return []
        findings = []
        # Match single bracket test: if [ or while [  but not [[
        pattern = re.compile(r'\bif\s+\[(?!\[)|\bwhile\s+\[(?!\[)')
        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if pattern.search(line):
                findings.append(_make_finding(
                    file_path=file_path,
                    line_number=i,
                    rule_id="shell.use-double-brackets",
                    category=ShellRuleCategory.STYLE,
                    severity=ShellSeverity.INFO,
                    title="Use [[ ]] instead of [ ] for conditionals",
                    description=(
                        "The [[ ]] construct is safer and more powerful than [ ]. "
                        "It handles word splitting and provides regex matching."
                    ),
                    code_snippet=line,
                    fix_suggestion="Replace [ condition ] with [[ condition ]].",
                ))
        return findings

    def _rule_function_definition(self, file_path: str, lines: List[str]) -> List[ShellFinding]:
        """shell.function-definition: Using 'function foo()' instead of 'foo()' (non-POSIX)."""
        if not self._config.is_rule_enabled("shell.function-definition"):
            return []
        findings = []
        pattern = re.compile(r'^\s*function\s+\w+\s*\(\s*\)')
        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if pattern.match(line):
                findings.append(_make_finding(
                    file_path=file_path,
                    line_number=i,
                    rule_id="shell.function-definition",
                    category=ShellRuleCategory.PORTABILITY,
                    severity=ShellSeverity.INFO,
                    title="Non-POSIX function definition style",
                    description=(
                        "The 'function foo()' syntax is a bashism. For POSIX portability use 'foo()' instead."
                    ),
                    code_snippet=line,
                    fix_suggestion="Replace 'function foo()' with 'foo()'.",
                ))
        return findings

    def _rule_trailing_whitespace(self, file_path: str, lines: List[str]) -> List[ShellFinding]:
        """shell.trailing-whitespace: Lines with trailing whitespace."""
        if not self._config.is_rule_enabled("shell.trailing-whitespace"):
            return []
        findings = []
        for i, line in enumerate(lines, start=1):
            if line != line.rstrip() and line.rstrip():
                findings.append(_make_finding(
                    file_path=file_path,
                    line_number=i,
                    rule_id="shell.trailing-whitespace",
                    category=ShellRuleCategory.STYLE,
                    severity=ShellSeverity.INFO,
                    title="Trailing whitespace",
                    description="Line has trailing whitespace characters.",
                    code_snippet=line,
                    fix_suggestion="Remove trailing whitespace.",
                ))
        return findings

    def _rule_long_line(self, file_path: str, lines: List[str]) -> List[ShellFinding]:
        """shell.long-line: Lines exceeding 120 characters."""
        if not self._config.is_rule_enabled("shell.long-line"):
            return []
        findings = []
        max_length = 120
        for i, line in enumerate(lines, start=1):
            if len(line.rstrip()) > max_length:
                findings.append(_make_finding(
                    file_path=file_path,
                    line_number=i,
                    rule_id="shell.long-line",
                    category=ShellRuleCategory.STYLE,
                    severity=ShellSeverity.INFO,
                    title="Line too long",
                    description=f"Line is {len(line.rstrip())} characters, exceeding the 120-character limit.",
                    code_snippet=line[:120] + "...",
                    fix_suggestion="Break the line using line continuation (\\) or restructure the command.",
                ))
        return findings
