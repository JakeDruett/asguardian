"""
Heimdall JavaScript Analyzer

Regex and text-based static analysis for JavaScript and JSX files.
Implements rules across bug detection, code smell, complexity, and style categories.
Since JavaScript cannot be parsed with Python's ast module, all rules use
regex pattern matching applied line-by-line or across the full file text.
"""

import re
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from Asgard.Heimdall.Quality.languages.javascript.models.js_models import (
    JSAnalysisConfig,
    JSFinding,
    JSReport,
    JSRuleCategory,
    JSSeverity,
)


_DEFAULT_EXTENSIONS = [".js", ".jsx"]
_TEST_FILE_PATTERNS = ["test", "spec", "__tests__", ".test.", ".spec."]


def _is_test_file(file_path: str) -> bool:
    """Return True if the file path looks like a test file."""
    lower = file_path.lower()
    return any(pattern in lower for pattern in _TEST_FILE_PATTERNS)


def _make_finding(
    file_path: str,
    line_number: int,
    rule_id: str,
    category: JSRuleCategory,
    severity: JSSeverity,
    title: str,
    description: str,
    code_snippet: str = "",
    fix_suggestion: str = "",
    column: int = 0,
) -> JSFinding:
    """Helper to construct a JSFinding with consistent field population."""
    return JSFinding(
        file_path=file_path,
        line_number=line_number,
        column=column,
        rule_id=rule_id,
        category=category,
        severity=severity,
        title=title,
        description=description,
        code_snippet=code_snippet.strip(),
        fix_suggestion=fix_suggestion,
    )


class JSAnalyzer:
    """
    Regex-based static analyzer for JavaScript and JSX files.

    Usage:
        config = JSAnalysisConfig(scan_path=Path("./src"))
        analyzer = JSAnalyzer(config)
        report = analyzer.analyze(Path("./src"))
    """

    def __init__(self, config: Optional[JSAnalysisConfig] = None):
        """
        Initialise the JavaScript analyzer.

        Args:
            config: Analysis configuration. Defaults to JSAnalysisConfig() with default values.
        """
        self._config = config or JSAnalysisConfig()

    def analyze(self, scan_path: Optional[Path] = None) -> JSReport:
        """
        Scan a directory tree for JavaScript files and apply all enabled rules.

        Args:
            scan_path: Root path to scan. Falls back to config.scan_path.

        Returns:
            JSReport containing all findings.
        """
        root = Path(scan_path) if scan_path else self._config.scan_path
        root = root.resolve()

        start_time = time.monotonic()
        report = JSReport(
            scan_path=str(root),
            language="javascript",
            scanned_at=datetime.now(),
        )

        extensions = self._config.include_extensions or _DEFAULT_EXTENSIONS
        files = self._collect_files(root, extensions)

        for file_path in files:
            findings = self._analyze_file(file_path)
            for finding in findings:
                report.add_finding(finding)

        report.files_analyzed = len(files)
        report.scan_duration_seconds = time.monotonic() - start_time
        return report

    def _collect_files(self, root: Path, extensions: List[str]) -> List[Path]:
        """Collect all files matching the given extensions, excluding configured patterns."""
        collected: List[Path] = []
        exclude = self._config.exclude_patterns

        for ext in extensions:
            for file_path in root.rglob(f"*{ext}"):
                path_str = str(file_path)
                if any(pattern in path_str for pattern in exclude):
                    continue
                collected.append(file_path)

        return sorted(collected)

    def _analyze_file(self, file_path: Path) -> List[JSFinding]:
        """Run all enabled rules against a single file."""
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return []

        lines = content.splitlines()
        path_str = str(file_path)
        findings: List[JSFinding] = []

        findings.extend(self._rule_no_undef_comparison(path_str, lines))
        findings.extend(self._rule_use_strict_equality(path_str, lines))
        findings.extend(self._rule_no_eval(path_str, lines))
        findings.extend(self._rule_no_implied_eval(path_str, lines))
        if not _is_test_file(path_str):
            findings.extend(self._rule_no_console(path_str, lines))
        findings.extend(self._rule_no_debugger(path_str, lines))
        findings.extend(self._rule_no_alert(path_str, lines))
        findings.extend(self._rule_var_declaration(path_str, lines))
        findings.extend(self._rule_no_empty_function(path_str, lines))
        findings.extend(self._rule_prefer_const(path_str, lines))
        findings.extend(self._rule_max_lines_per_function(path_str, lines))
        findings.extend(self._rule_max_file_lines(path_str, lines))
        findings.extend(self._rule_no_unused_vars(path_str, lines))
        findings.extend(self._rule_complexity(path_str, lines))
        findings.extend(self._rule_semi(path_str, lines))
        findings.extend(self._rule_eol_last(path_str, content))

        return findings

    # --- Bug Detection Rules ---

    def _rule_no_undef_comparison(self, file_path: str, lines: List[str]) -> List[JSFinding]:
        """js.no-undef-comparison: Comparing with undefined using == instead of ===."""
        if not self._config.is_rule_enabled("js.no-undef-comparison"):
            return []
        findings = []
        pattern = re.compile(r'(?:==\s*undefined|undefined\s*==)[^=]')
        for i, line in enumerate(lines, start=1):
            if pattern.search(line):
                findings.append(_make_finding(
                    file_path=file_path,
                    line_number=i,
                    rule_id="js.no-undef-comparison",
                    category=JSRuleCategory.BUG,
                    severity=JSSeverity.WARNING,
                    title="Loose undefined comparison",
                    description="Use === instead of == when comparing with undefined to avoid unexpected type coercion.",
                    code_snippet=line,
                    fix_suggestion="Replace == undefined with === undefined (or use typeof check).",
                ))
        return findings

    def _rule_use_strict_equality(self, file_path: str, lines: List[str]) -> List[JSFinding]:
        """js.use-strict-equality: Using == or != instead of === or !==."""
        if not self._config.is_rule_enabled("js.use-strict-equality"):
            return []
        findings = []
        # Match == or != but not === or !==, and not <= >= ==
        pattern = re.compile(r'(?<![=!<>])(?:==|!=)(?!=)')
        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("*"):
                continue
            if pattern.search(line):
                findings.append(_make_finding(
                    file_path=file_path,
                    line_number=i,
                    rule_id="js.use-strict-equality",
                    category=JSRuleCategory.BUG,
                    severity=JSSeverity.WARNING,
                    title="Loose equality operator",
                    description="Use === and !== instead of == and != to avoid unexpected type coercion.",
                    code_snippet=line,
                    fix_suggestion="Replace == with === and != with !==.",
                ))
        return findings

    def _rule_no_eval(self, file_path: str, lines: List[str]) -> List[JSFinding]:
        """js.no-eval: Use of eval() is a security risk."""
        if not self._config.is_rule_enabled("js.no-eval"):
            return []
        findings = []
        pattern = re.compile(r'\beval\s*\(')
        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("*"):
                continue
            if pattern.search(line):
                findings.append(_make_finding(
                    file_path=file_path,
                    line_number=i,
                    rule_id="js.no-eval",
                    category=JSRuleCategory.SECURITY,
                    severity=JSSeverity.ERROR,
                    title="Use of eval()",
                    description="eval() is a security risk and should never be used. It executes arbitrary code.",
                    code_snippet=line,
                    fix_suggestion="Refactor to avoid eval(). Use JSON.parse() for JSON, or restructure logic.",
                ))
        return findings

    def _rule_no_implied_eval(self, file_path: str, lines: List[str]) -> List[JSFinding]:
        """js.no-implied-eval: setTimeout/setInterval with string literal as first argument."""
        if not self._config.is_rule_enabled("js.no-implied-eval"):
            return []
        findings = []
        pattern = re.compile(r'(?:setTimeout|setInterval)\s*\(\s*["\']')
        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("*"):
                continue
            if pattern.search(line):
                findings.append(_make_finding(
                    file_path=file_path,
                    line_number=i,
                    rule_id="js.no-implied-eval",
                    category=JSRuleCategory.SECURITY,
                    severity=JSSeverity.WARNING,
                    title="Implied eval via setTimeout/setInterval",
                    description=(
                        "Passing a string to setTimeout or setInterval causes an implied eval, "
                        "which is a security risk."
                    ),
                    code_snippet=line,
                    fix_suggestion="Pass a function reference instead of a string literal.",
                ))
        return findings

    def _rule_no_console(self, file_path: str, lines: List[str]) -> List[JSFinding]:
        """js.no-console: console.log/warn/error calls in non-test files."""
        if not self._config.is_rule_enabled("js.no-console"):
            return []
        findings = []
        pattern = re.compile(r'\bconsole\.(log|warn|error|debug|info)\s*\(')
        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("*"):
                continue
            if pattern.search(line):
                findings.append(_make_finding(
                    file_path=file_path,
                    line_number=i,
                    rule_id="js.no-console",
                    category=JSRuleCategory.CODE_SMELL,
                    severity=JSSeverity.INFO,
                    title="console statement",
                    description="console statements should not be present in production code.",
                    code_snippet=line,
                    fix_suggestion="Remove console statement or replace with a proper logging library.",
                ))
        return findings

    def _rule_no_debugger(self, file_path: str, lines: List[str]) -> List[JSFinding]:
        """js.no-debugger: debugger; statement in code."""
        if not self._config.is_rule_enabled("js.no-debugger"):
            return []
        findings = []
        pattern = re.compile(r'\bdebugger\s*;')
        for i, line in enumerate(lines, start=1):
            if pattern.search(line):
                findings.append(_make_finding(
                    file_path=file_path,
                    line_number=i,
                    rule_id="js.no-debugger",
                    category=JSRuleCategory.BUG,
                    severity=JSSeverity.ERROR,
                    title="debugger statement",
                    description="debugger statements must be removed before committing code.",
                    code_snippet=line,
                    fix_suggestion="Remove the debugger statement.",
                ))
        return findings

    def _rule_no_alert(self, file_path: str, lines: List[str]) -> List[JSFinding]:
        """js.no-alert: alert() or window.alert() calls."""
        if not self._config.is_rule_enabled("js.no-alert"):
            return []
        findings = []
        pattern = re.compile(r'(?:\bwindow\.)?\balert\s*\(')
        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("*"):
                continue
            if pattern.search(line):
                findings.append(_make_finding(
                    file_path=file_path,
                    line_number=i,
                    rule_id="js.no-alert",
                    category=JSRuleCategory.CODE_SMELL,
                    severity=JSSeverity.WARNING,
                    title="alert() usage",
                    description="alert() is disruptive UI and should not be used in production code.",
                    code_snippet=line,
                    fix_suggestion="Replace alert() with a proper notification component or modal.",
                ))
        return findings

    # --- Code Smell Rules ---

    def _rule_var_declaration(self, file_path: str, lines: List[str]) -> List[JSFinding]:
        """js.var-declaration: Use of var instead of let/const."""
        if not self._config.is_rule_enabled("js.var-declaration"):
            return []
        findings = []
        pattern = re.compile(r'\bvar\s+')
        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("*"):
                continue
            if pattern.search(line):
                findings.append(_make_finding(
                    file_path=file_path,
                    line_number=i,
                    rule_id="js.var-declaration",
                    category=JSRuleCategory.CODE_SMELL,
                    severity=JSSeverity.WARNING,
                    title="var declaration",
                    description="Use let or const instead of var. var has function scope and hoisting which can cause bugs.",
                    code_snippet=line,
                    fix_suggestion="Replace var with const (if not reassigned) or let (if reassigned).",
                ))
        return findings

    def _rule_no_empty_function(self, file_path: str, lines: List[str]) -> List[JSFinding]:
        """js.no-empty-function: Empty function bodies."""
        if not self._config.is_rule_enabled("js.no-empty-function"):
            return []
        findings = []
        # Named functions: function foo() {}
        named_pattern = re.compile(r'\bfunction\s+\w+\s*\([^)]*\)\s*\{\s*\}')
        # Arrow functions with empty body: => {}
        arrow_pattern = re.compile(r'=>\s*\{\s*\}')
        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("*"):
                continue
            if named_pattern.search(line) or arrow_pattern.search(line):
                findings.append(_make_finding(
                    file_path=file_path,
                    line_number=i,
                    rule_id="js.no-empty-function",
                    category=JSRuleCategory.CODE_SMELL,
                    severity=JSSeverity.INFO,
                    title="Empty function body",
                    description="Empty function bodies are likely unfinished implementations or dead code.",
                    code_snippet=line,
                    fix_suggestion="Either implement the function body or remove the function if it is unused.",
                ))
        return findings

    def _rule_prefer_const(self, file_path: str, lines: List[str]) -> List[JSFinding]:
        """js.prefer-const: Flag let declarations as INFO (prefer const where possible)."""
        if not self._config.is_rule_enabled("js.prefer-const"):
            return []
        findings = []
        pattern = re.compile(r'\blet\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=')
        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("*"):
                continue
            match = pattern.search(line)
            if match:
                var_name = match.group(1)
                # Check if the variable is reassigned anywhere else in the file
                reassignment_pattern = re.compile(
                    r'\b' + re.escape(var_name) + r'\s*(?:\+|-|\*|/|%|\|\||&&)?='
                )
                content = "\n".join(lines)
                reassignments = reassignment_pattern.findall(content)
                # More than one match means it was reassigned at least once after declaration
                if len(reassignments) <= 1:
                    findings.append(_make_finding(
                        file_path=file_path,
                        line_number=i,
                        rule_id="js.prefer-const",
                        category=JSRuleCategory.CODE_SMELL,
                        severity=JSSeverity.INFO,
                        title="Prefer const over let",
                        description=f"'{var_name}' is declared with let but does not appear to be reassigned.",
                        code_snippet=line,
                        fix_suggestion=f"Change 'let {var_name}' to 'const {var_name}' if not reassigned.",
                    ))
        return findings

    def _rule_max_lines_per_function(self, file_path: str, lines: List[str]) -> List[JSFinding]:
        """js.max-lines-per-function: Approximate function line count check."""
        if not self._config.is_rule_enabled("js.max-lines-per-function"):
            return []
        findings = []
        max_lines = self._config.max_function_lines
        func_pattern = re.compile(r'\bfunction\s*\*?\s*\w*\s*\([^)]*\)\s*\{')

        i = 0
        while i < len(lines):
            match = func_pattern.search(lines[i])
            if match:
                func_start = i + 1
                brace_depth = lines[i].count("{") - lines[i].count("}")
                j = i + 1
                while j < len(lines) and brace_depth > 0:
                    brace_depth += lines[j].count("{") - lines[j].count("}")
                    j += 1
                func_lines = j - i
                if func_lines > max_lines:
                    findings.append(_make_finding(
                        file_path=file_path,
                        line_number=func_start,
                        rule_id="js.max-lines-per-function",
                        category=JSRuleCategory.CODE_SMELL,
                        severity=JSSeverity.WARNING,
                        title="Function too long",
                        description=(
                            f"Function is approximately {func_lines} lines long, "
                            f"exceeding the maximum of {max_lines}."
                        ),
                        code_snippet=lines[i],
                        fix_suggestion="Break the function into smaller, more focused functions.",
                    ))
                i = j
            else:
                i += 1
        return findings

    def _rule_max_file_lines(self, file_path: str, lines: List[str]) -> List[JSFinding]:
        """js.max-file-lines: File exceeds maximum line count."""
        if not self._config.is_rule_enabled("js.max-file-lines"):
            return []
        max_lines = self._config.max_file_lines
        if len(lines) > max_lines:
            return [_make_finding(
                file_path=file_path,
                line_number=1,
                rule_id="js.max-file-lines",
                category=JSRuleCategory.CODE_SMELL,
                severity=JSSeverity.WARNING,
                title="File too long",
                description=(
                    f"File has {len(lines)} lines, exceeding the maximum of {max_lines}."
                ),
                code_snippet="",
                fix_suggestion="Split the file into smaller, more focused modules.",
            )]
        return []

    def _rule_no_unused_vars(self, file_path: str, lines: List[str]) -> List[JSFinding]:
        """js.no-unused-vars: Variables declared but never used elsewhere in the file."""
        if not self._config.is_rule_enabled("js.no-unused-vars"):
            return []
        findings = []
        content = "\n".join(lines)
        decl_pattern = re.compile(r'\b(?:const|let|var)\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=')

        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("*"):
                continue
            for match in decl_pattern.finditer(line):
                var_name = match.group(1)
                # Count all occurrences of this identifier in the file
                usage_pattern = re.compile(r'\b' + re.escape(var_name) + r'\b')
                usages = usage_pattern.findall(content)
                # One occurrence is the declaration itself
                if len(usages) <= 1:
                    findings.append(_make_finding(
                        file_path=file_path,
                        line_number=i,
                        rule_id="js.no-unused-vars",
                        category=JSRuleCategory.CODE_SMELL,
                        severity=JSSeverity.WARNING,
                        title="Unused variable",
                        description=f"Variable '{var_name}' is declared but never used.",
                        code_snippet=line,
                        fix_suggestion=f"Remove the declaration of '{var_name}' or use it.",
                    ))
        return findings

    # --- Complexity Rules ---

    def _rule_complexity(self, file_path: str, lines: List[str]) -> List[JSFinding]:
        """js.complexity: Approximate cyclomatic complexity per function."""
        if not self._config.is_rule_enabled("js.complexity"):
            return []
        findings = []
        max_complexity = self._config.max_complexity
        func_pattern = re.compile(r'\bfunction\s*\*?\s*\w*\s*\([^)]*\)\s*\{')
        complexity_tokens = re.compile(
            r'\b(?:if|else\s+if|for|while|case|catch)\b|&&|\|\||\?(?!:)'
        )

        i = 0
        while i < len(lines):
            match = func_pattern.search(lines[i])
            if match:
                func_start = i + 1
                brace_depth = lines[i].count("{") - lines[i].count("}")
                complexity = 1
                j = i + 1
                while j < len(lines) and brace_depth > 0:
                    brace_depth += lines[j].count("{") - lines[j].count("}")
                    complexity += len(complexity_tokens.findall(lines[j]))
                    j += 1
                if complexity > max_complexity:
                    findings.append(_make_finding(
                        file_path=file_path,
                        line_number=func_start,
                        rule_id="js.complexity",
                        category=JSRuleCategory.COMPLEXITY,
                        severity=JSSeverity.WARNING,
                        title="High cyclomatic complexity",
                        description=(
                            f"Function has an approximate cyclomatic complexity of {complexity}, "
                            f"exceeding the threshold of {max_complexity}."
                        ),
                        code_snippet=lines[i],
                        fix_suggestion="Refactor into smaller functions to reduce complexity.",
                    ))
                i = j
            else:
                i += 1
        return findings

    # --- Style Rules ---

    def _rule_semi(self, file_path: str, lines: List[str]) -> List[JSFinding]:
        """js.semi: Lines that appear to be missing a terminating semicolon."""
        if not self._config.is_rule_enabled("js.semi"):
            return []
        findings = []
        # Lines that should end with semicolon: not ending in { } , ; or being blank/comments
        missing_semi_pattern = re.compile(
            r'^(?!\s*(?://|/\*|\*|$)).*[a-zA-Z0-9_$\'"`\])]$'
        )
        for i, line in enumerate(lines, start=1):
            stripped = line.rstrip()
            if not stripped:
                continue
            if stripped.endswith(("{", "}", ",", ";", ":", "(")):
                continue
            if stripped.strip().startswith(("//", "*", "/*", "import ", "export ")):
                continue
            if missing_semi_pattern.match(stripped):
                findings.append(_make_finding(
                    file_path=file_path,
                    line_number=i,
                    rule_id="js.semi",
                    category=JSRuleCategory.STYLE,
                    severity=JSSeverity.INFO,
                    title="Missing semicolon",
                    description="Line may be missing a terminating semicolon.",
                    code_snippet=line,
                    fix_suggestion="Add a semicolon at the end of the statement.",
                ))
        return findings

    def _rule_eol_last(self, file_path: str, content: str) -> List[JSFinding]:
        """js.eol-last: File does not end with a newline character."""
        if not self._config.is_rule_enabled("js.eol-last"):
            return []
        if content and not content.endswith("\n"):
            return [_make_finding(
                file_path=file_path,
                line_number=content.count("\n") + 1,
                rule_id="js.eol-last",
                category=JSRuleCategory.STYLE,
                severity=JSSeverity.INFO,
                title="Missing newline at end of file",
                description="Files should end with a newline character.",
                code_snippet="",
                fix_suggestion="Add a newline at the end of the file.",
            )]
        return []
