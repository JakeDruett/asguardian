"""
Heimdall Injection Detection Service

Service for detecting injection vulnerabilities including SQL injection,
XSS (Cross-Site Scripting), command injection, and other injection patterns.
"""

import ast
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Pattern, Set, Tuple

from Asgard.Heimdall.Security.models.security_models import (
    SecurityScanConfig,
    SecuritySeverity,
    VulnerabilityFinding,
    VulnerabilityReport,
    VulnerabilityType,
)
from Asgard.Heimdall.Security.utilities.security_utils import (
    extract_code_snippet,
    find_line_column,
    is_in_comment_or_docstring,
    is_parameterized_sql,
    read_file_lines,
    scan_directory_for_security,
)


class InjectionPattern:
    """Defines a pattern for detecting injection vulnerabilities."""

    def __init__(
        self,
        name: str,
        pattern: str,
        vuln_type: VulnerabilityType,
        severity: SecuritySeverity,
        title: str,
        description: str,
        cwe_id: str,
        owasp_category: str,
        remediation: str,
        file_types: Optional[Set[str]] = None,
        confidence: float = 0.7,
    ):
        self.name = name
        self.pattern = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
        self.vuln_type = vuln_type
        self.severity = severity
        self.title = title
        self.description = description
        self.cwe_id = cwe_id
        self.owasp_category = owasp_category
        self.remediation = remediation
        self.file_types = file_types or {".py", ".js", ".ts", ".java", ".php", ".rb", ".go"}
        self.confidence = confidence


SQL_INJECTION_PATTERNS: List[InjectionPattern] = [
    InjectionPattern(
        name="sql_string_format",
        pattern=r"""(?:execute|query|cursor\.execute|raw|rawsql|RawSQL)\s*\(\s*[f"'].*(?:\{|\%s|\%\().*["']\s*(?:%|\.format)""",
        vuln_type=VulnerabilityType.SQL_INJECTION,
        severity=SecuritySeverity.CRITICAL,
        title="SQL Injection via String Formatting",
        description="User input is directly interpolated into SQL query using string formatting.",
        cwe_id="CWE-89",
        owasp_category="A03:2021",
        remediation="Use parameterized queries or prepared statements. Never concatenate user input into SQL.",
        confidence=0.85,
    ),
    InjectionPattern(
        name="sql_string_concat",
        pattern=r"""(?:SELECT|INSERT|UPDATE|DELETE|FROM|WHERE|AND|OR)\s*.*['"]\s*\+\s*(?:request|input|params|data|user)""",
        vuln_type=VulnerabilityType.SQL_INJECTION,
        severity=SecuritySeverity.CRITICAL,
        title="SQL Injection via String Concatenation",
        description="User input is concatenated into SQL query string.",
        cwe_id="CWE-89",
        owasp_category="A03:2021",
        remediation="Use parameterized queries with placeholders (?, :param, or $1).",
        confidence=0.8,
    ),
    InjectionPattern(
        name="sql_fstring",
        pattern=r"""(?:execute|query|cursor\.execute)\s*\(\s*f['"]{1,3}.*(?:SELECT|INSERT|UPDATE|DELETE).*\{.*\}""",
        vuln_type=VulnerabilityType.SQL_INJECTION,
        severity=SecuritySeverity.CRITICAL,
        title="SQL Injection via f-string",
        description="Variables are interpolated into SQL using Python f-strings.",
        cwe_id="CWE-89",
        owasp_category="A03:2021",
        remediation="Use parameterized queries instead of f-strings for SQL.",
        file_types={".py"},
        confidence=0.9,
    ),
    InjectionPattern(
        name="sql_percent_format",
        pattern=r"""(?:execute|query|cursor\.execute)\s*\([^)]*["'].*(?:SELECT|INSERT|UPDATE|DELETE).*%[sd].*["']\s*%\s*""",
        vuln_type=VulnerabilityType.SQL_INJECTION,
        severity=SecuritySeverity.CRITICAL,
        title="SQL Injection via Percent Formatting",
        description="SQL query uses percent-style string formatting with user input.",
        cwe_id="CWE-89",
        owasp_category="A03:2021",
        remediation="Replace % formatting with parameterized queries.",
        file_types={".py"},
        confidence=0.85,
    ),
    InjectionPattern(
        name="django_raw_sql",
        pattern=r"""(?:\.raw|\.extra)\s*\([^)]*(?:\{|%|\.format)""",
        vuln_type=VulnerabilityType.SQL_INJECTION,
        severity=SecuritySeverity.HIGH,
        title="Django Raw SQL with User Input",
        description="Django raw() or extra() with potentially unsafe interpolation.",
        cwe_id="CWE-89",
        owasp_category="A03:2021",
        remediation="Use Django ORM methods or pass parameters separately to raw().",
        file_types={".py"},
        confidence=0.75,
    ),
    InjectionPattern(
        name="sqlalchemy_text_format",
        pattern=r"""text\s*\(\s*f?['"]{1,3}.*(?:SELECT|INSERT|UPDATE|DELETE).*(?:\{|%|\.format)""",
        vuln_type=VulnerabilityType.SQL_INJECTION,
        severity=SecuritySeverity.CRITICAL,
        title="SQLAlchemy text() with String Formatting",
        description="SQLAlchemy text() with potentially unsafe string interpolation.",
        cwe_id="CWE-89",
        owasp_category="A03:2021",
        remediation="Use SQLAlchemy bindparams or pass parameters to execute().",
        file_types={".py"},
        confidence=0.85,
    ),
]

XSS_PATTERNS: List[InjectionPattern] = [
    InjectionPattern(
        name="xss_innerhtml",
        pattern=r"""\.innerHTML\s*=\s*(?:(?!['"`]<).)*(?:request|params|input|data|user|query)""",
        vuln_type=VulnerabilityType.XSS,
        severity=SecuritySeverity.HIGH,
        title="XSS via innerHTML",
        description="User input is assigned to innerHTML without sanitization.",
        cwe_id="CWE-79",
        owasp_category="A03:2021",
        remediation="Use textContent instead of innerHTML, or sanitize with DOMPurify.",
        file_types={".js", ".jsx", ".ts", ".tsx"},
        confidence=0.8,
    ),
    InjectionPattern(
        name="xss_document_write",
        pattern=r"""document\.write\s*\([^)]*(?:request|params|input|data|user|query|location|url)""",
        vuln_type=VulnerabilityType.XSS,
        severity=SecuritySeverity.HIGH,
        title="XSS via document.write",
        description="User input passed to document.write without sanitization.",
        cwe_id="CWE-79",
        owasp_category="A03:2021",
        remediation="Avoid document.write. Use DOM methods and sanitize input.",
        file_types={".js", ".jsx", ".ts", ".tsx", ".html"},
        confidence=0.85,
    ),
    InjectionPattern(
        name="xss_eval",
        pattern=r"""eval\s*\([^)]*(?:request|params|input|data|user|query|location)""",
        vuln_type=VulnerabilityType.XSS,
        severity=SecuritySeverity.CRITICAL,
        title="Code Injection via eval",
        description="User input passed to eval() function.",
        cwe_id="CWE-95",
        owasp_category="A03:2021",
        remediation="Never use eval with user input. Use JSON.parse for data parsing.",
        file_types={".js", ".jsx", ".ts", ".tsx"},
        confidence=0.9,
    ),
    InjectionPattern(
        name="xss_dangerously_set",
        pattern=r"""dangerouslySetInnerHTML\s*=\s*\{\s*\{\s*__html\s*:\s*(?!['"`]<)""",
        vuln_type=VulnerabilityType.XSS,
        severity=SecuritySeverity.HIGH,
        title="React dangerouslySetInnerHTML with Dynamic Content",
        description="React dangerouslySetInnerHTML used with potentially unsanitized content.",
        cwe_id="CWE-79",
        owasp_category="A03:2021",
        remediation="Sanitize content with DOMPurify before using dangerouslySetInnerHTML.",
        file_types={".js", ".jsx", ".ts", ".tsx"},
        confidence=0.75,
    ),
    InjectionPattern(
        name="xss_template_unescaped",
        pattern=r"""\{\{\{\s*.*(?:request|params|input|data|user|body)\.""",
        vuln_type=VulnerabilityType.XSS,
        severity=SecuritySeverity.HIGH,
        title="Unescaped Template Variable",
        description="Template uses unescaped variable that may contain user input.",
        cwe_id="CWE-79",
        owasp_category="A03:2021",
        remediation="Use escaped template syntax or sanitize user input.",
        file_types={".html", ".hbs", ".handlebars", ".mustache"},
        confidence=0.7,
    ),
    InjectionPattern(
        name="xss_jinja_safe",
        pattern=r"""\{\{.*\|\s*safe\s*\}\}""",
        vuln_type=VulnerabilityType.XSS,
        severity=SecuritySeverity.MEDIUM,
        title="Jinja2 safe Filter Usage",
        description="Jinja2 safe filter bypasses HTML escaping - ensure content is sanitized.",
        cwe_id="CWE-79",
        owasp_category="A03:2021",
        remediation="Only use |safe with content that is already sanitized or trusted.",
        file_types={".html", ".jinja", ".jinja2"},
        confidence=0.6,
    ),
    InjectionPattern(
        name="xss_jquery_html",
        pattern=r"""\$\([^)]+\)\.html\s*\([^)]*(?:request|params|input|data|user|query)""",
        vuln_type=VulnerabilityType.XSS,
        severity=SecuritySeverity.HIGH,
        title="XSS via jQuery .html()",
        description="User input passed to jQuery .html() method.",
        cwe_id="CWE-79",
        owasp_category="A03:2021",
        remediation="Use .text() for text content, or sanitize HTML before using .html().",
        file_types={".js", ".jsx", ".ts", ".tsx"},
        confidence=0.8,
    ),
]

COMMAND_INJECTION_PATTERNS: List[InjectionPattern] = [
    InjectionPattern(
        name="cmd_os_system",
        pattern=r"""os\.system\s*\([^)]*(?:\{|%|\.format|\+\s*(?:request|input|params|data|user))""",
        vuln_type=VulnerabilityType.COMMAND_INJECTION,
        severity=SecuritySeverity.CRITICAL,
        title="Command Injection via os.system",
        description="User input passed to os.system without sanitization.",
        cwe_id="CWE-78",
        owasp_category="A03:2021",
        remediation="Use subprocess with shell=False and pass arguments as a list.",
        file_types={".py"},
        confidence=0.9,
    ),
    InjectionPattern(
        name="cmd_subprocess_shell",
        pattern=r"""subprocess\.(?:call|run|Popen)\s*\([^)]*shell\s*=\s*True[^)]*(?:\{|%|\.format|\+\s*(?:request|input|params|data|user))""",
        vuln_type=VulnerabilityType.COMMAND_INJECTION,
        severity=SecuritySeverity.CRITICAL,
        title="Command Injection via subprocess with shell=True",
        description="subprocess with shell=True and user input.",
        cwe_id="CWE-78",
        owasp_category="A03:2021",
        remediation="Use shell=False and pass command as a list of arguments.",
        file_types={".py"},
        confidence=0.9,
    ),
    InjectionPattern(
        name="cmd_exec",
        pattern=r"""(?:exec|eval)\s*\([^)]*(?:request|input|params|data|user|args)""",
        vuln_type=VulnerabilityType.COMMAND_INJECTION,
        severity=SecuritySeverity.CRITICAL,
        title="Code Execution via exec/eval",
        description="User input passed to exec() or eval() function.",
        cwe_id="CWE-95",
        owasp_category="A03:2021",
        remediation="Never use exec/eval with user input. Find safer alternatives.",
        file_types={".py"},
        confidence=0.85,
    ),
    InjectionPattern(
        name="cmd_shell_exec",
        pattern=r"""(?:shell_exec|system|passthru|exec|popen)\s*\([^)]*\$_(?:GET|POST|REQUEST)""",
        vuln_type=VulnerabilityType.COMMAND_INJECTION,
        severity=SecuritySeverity.CRITICAL,
        title="PHP Command Injection",
        description="User input from superglobals passed to shell execution function.",
        cwe_id="CWE-78",
        owasp_category="A03:2021",
        remediation="Use escapeshellarg() and escapeshellcmd() for any shell arguments.",
        file_types={".php"},
        confidence=0.9,
    ),
]

PATH_TRAVERSAL_PATTERNS: List[InjectionPattern] = [
    InjectionPattern(
        name="path_traversal_open",
        pattern=r"""open\s*\([^)]*(?:\{|%|\.format|\+)\s*[^)]*(?:request|input|params|data|user|filename|path)""",
        vuln_type=VulnerabilityType.PATH_TRAVERSAL,
        severity=SecuritySeverity.HIGH,
        title="Path Traversal via open()",
        description="User input used in file path without proper sanitization.",
        cwe_id="CWE-22",
        owasp_category="A01:2021",
        remediation="Validate and sanitize file paths. Use os.path.basename() and whitelist allowed directories.",
        file_types={".py"},
        confidence=0.75,
    ),
    InjectionPattern(
        name="path_traversal_send_file",
        pattern=r"""send_file\s*\([^)]*(?:\{|%|\.format|\+)\s*[^)]*(?:request|input|params|data|user|filename|path)""",
        vuln_type=VulnerabilityType.PATH_TRAVERSAL,
        severity=SecuritySeverity.HIGH,
        title="Path Traversal in File Download",
        description="User input used in send_file path without sanitization.",
        cwe_id="CWE-22",
        owasp_category="A01:2021",
        remediation="Validate paths against allowed directories. Never allow ../ in paths.",
        file_types={".py"},
        confidence=0.8,
    ),
]


class InjectionDetectionService:
    """
    Detects injection vulnerabilities in source code.

    Supports detection of:
    - SQL Injection
    - Cross-Site Scripting (XSS)
    - Command Injection
    - Path Traversal
    - Code Injection
    """

    def __init__(self, config: Optional[SecurityScanConfig] = None):
        """
        Initialize the injection detection service.

        Args:
            config: Security scan configuration. Uses defaults if not provided.
        """
        self.config = config or SecurityScanConfig()
        self.patterns: List[InjectionPattern] = (
            SQL_INJECTION_PATTERNS +
            XSS_PATTERNS +
            COMMAND_INJECTION_PATTERNS +
            PATH_TRAVERSAL_PATTERNS
        )

    def scan(self, scan_path: Optional[Path] = None) -> VulnerabilityReport:
        """
        Scan the specified path for injection vulnerabilities.

        Args:
            scan_path: Root path to scan. Uses config path if not provided.

        Returns:
            VulnerabilityReport containing all findings
        """
        path = scan_path or self.config.scan_path
        path = Path(path).resolve()

        if not path.exists():
            raise FileNotFoundError(f"Scan path does not exist: {path}")

        start_time = time.time()

        report = VulnerabilityReport(
            scan_path=str(path),
        )

        for file_path in scan_directory_for_security(
            path,
            exclude_patterns=self.config.exclude_patterns,
            include_extensions=self.config.include_extensions,
        ):
            if str(file_path) in self.config.ignore_paths:
                continue

            report.total_files_scanned += 1
            findings = self._scan_file(file_path, path)

            for finding in findings:
                if self._severity_meets_threshold(finding.severity):
                    report.add_finding(finding)

        report.scan_duration_seconds = time.time() - start_time

        report.findings.sort(
            key=lambda f: (
                self._severity_order(f.severity),
                f.file_path,
                f.line_number,
            )
        )

        return report

    def _scan_file(self, file_path: Path, root_path: Path) -> List[VulnerabilityFinding]:
        """
        Scan a single file for injection vulnerabilities.

        Args:
            file_path: Path to the file to scan
            root_path: Root path for relative path calculation

        Returns:
            List of vulnerability findings in the file
        """
        findings: List[VulnerabilityFinding] = []

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except (IOError, OSError):
            return findings

        lines = content.split("\n")
        file_ext = file_path.suffix.lower()

        for pattern in self.patterns:
            if pattern.file_types and file_ext not in pattern.file_types:
                continue

            for match in pattern.pattern.finditer(content):
                line_number, column = find_line_column(content, match.start())

                # Skip matches in comments or docstrings
                if is_in_comment_or_docstring(content, lines, line_number, match.start(), file_ext):
                    continue

                # For SQL injection patterns, check if it's actually using parameterized queries
                if pattern.vuln_type == VulnerabilityType.SQL_INJECTION:
                    # Get more context around the match
                    context_start = max(0, match.start() - 50)
                    context_end = min(len(content), match.end() + 200)
                    context = content[context_start:context_end]

                    if is_parameterized_sql(match.group(0), context):
                        continue

                code_snippet = extract_code_snippet(lines, line_number)

                finding = VulnerabilityFinding(
                    file_path=str(file_path.relative_to(root_path)),
                    line_number=line_number,
                    column_start=column,
                    column_end=column + len(match.group(0)),
                    vulnerability_type=pattern.vuln_type,
                    severity=pattern.severity,
                    title=pattern.title,
                    description=pattern.description,
                    code_snippet=code_snippet,
                    cwe_id=pattern.cwe_id,
                    owasp_category=pattern.owasp_category,
                    confidence=pattern.confidence,
                    remediation=pattern.remediation,
                    references=[
                        f"https://cwe.mitre.org/data/definitions/{pattern.cwe_id.replace('CWE-', '')}.html",
                        f"https://owasp.org/Top10/{pattern.owasp_category}/",
                    ],
                )

                findings.append(finding)

        # Run AST-based deserialization and SSRF detection for Python files
        if file_ext == ".py":
            deser_findings = self.detect_insecure_deserialization(file_path, content)
            for f in deser_findings:
                try:
                    f.file_path = str(file_path.relative_to(root_path))
                except ValueError:
                    pass
                findings.append(f)

            ssrf_findings = self.detect_ssrf(file_path, content)
            for f in ssrf_findings:
                try:
                    f.file_path = str(file_path.relative_to(root_path))
                except ValueError:
                    pass
                findings.append(f)

        return findings

    def _is_in_comment(self, lines: List[str], line_number: int) -> bool:
        """
        Check if a line is inside a comment.

        Args:
            lines: List of file lines
            line_number: Line number to check (1-indexed)

        Returns:
            True if the line is a comment
        """
        if line_number < 1 or line_number > len(lines):
            return False

        line = lines[line_number - 1].strip()

        if line.startswith("#") or line.startswith("//") or line.startswith("*"):
            return True

        if line.startswith("'''") or line.startswith('"""'):
            return True

        return False

    def _severity_meets_threshold(self, severity: str) -> bool:
        """Check if a severity level meets the configured threshold."""
        severity_order = {
            SecuritySeverity.INFO.value: 0,
            SecuritySeverity.LOW.value: 1,
            SecuritySeverity.MEDIUM.value: 2,
            SecuritySeverity.HIGH.value: 3,
            SecuritySeverity.CRITICAL.value: 4,
        }

        min_level = severity_order.get(self.config.min_severity, 1)
        finding_level = severity_order.get(severity, 1)

        return finding_level >= min_level

    def _severity_order(self, severity: str) -> int:
        """Get sort order for severity (critical first)."""
        order = {
            SecuritySeverity.CRITICAL.value: 0,
            SecuritySeverity.HIGH.value: 1,
            SecuritySeverity.MEDIUM.value: 2,
            SecuritySeverity.LOW.value: 3,
            SecuritySeverity.INFO.value: 4,
        }
        return order.get(severity, 5)

    def detect_insecure_deserialization(
        self,
        file_path: Path,
        source_code: str,
    ) -> List[VulnerabilityFinding]:
        """
        Detect insecure deserialization patterns in a single source file.

        Checks for dangerous deserialization functions: pickle, marshal, unsafe yaml,
        jsonpickle, shelve, and dill.

        Args:
            file_path: Path to the source file being analyzed.
            source_code: Source code content of the file.

        Returns:
            List of VulnerabilityFinding objects for insecure deserialization patterns.
        """
        findings: List[VulnerabilityFinding] = []

        if file_path.suffix.lower() != ".py":
            return findings

        lines = source_code.splitlines()

        try:
            tree = ast.parse(source_code, filename=str(file_path))
        except SyntaxError:
            return findings

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            func_chain = ""
            if isinstance(node.func, ast.Attribute):
                parts = []
                current: ast.AST = node.func
                while isinstance(current, ast.Attribute):
                    parts.append(current.attr)
                    current = current.value
                if isinstance(current, ast.Name):
                    parts.append(current.id)
                parts.reverse()
                func_chain = ".".join(parts)
            elif isinstance(node.func, ast.Name):
                func_chain = node.func.id

            line_number = node.lineno
            code_snippet = lines[line_number - 1].strip() if 0 < line_number <= len(lines) else ""

            if func_chain in ("pickle.loads", "pickle.load"):
                findings.append(VulnerabilityFinding(
                    file_path=str(file_path),
                    line_number=line_number,
                    vulnerability_type=VulnerabilityType.INSECURE_DESERIALIZATION,
                    severity=SecuritySeverity.CRITICAL,
                    title="Insecure Deserialization via pickle",
                    description=(
                        "pickle.loads/pickle.load deserializes arbitrary Python objects "
                        "and can execute arbitrary code when processing untrusted data."
                    ),
                    code_snippet=code_snippet,
                    cwe_id="CWE-502",
                    owasp_category="A08:2021",
                    confidence=0.95,
                    remediation=(
                        "Never deserialize data from untrusted sources using pickle. "
                        "Use safe formats such as JSON with schema validation."
                    ),
                    references=["https://cwe.mitre.org/data/definitions/502.html"],
                ))

            elif func_chain in ("marshal.loads", "marshal.load"):
                findings.append(VulnerabilityFinding(
                    file_path=str(file_path),
                    line_number=line_number,
                    vulnerability_type=VulnerabilityType.INSECURE_DESERIALIZATION,
                    severity=SecuritySeverity.HIGH,
                    title="Insecure Deserialization via marshal",
                    description=(
                        "marshal.loads/marshal.load can deserialize arbitrary code objects "
                        "and should not be used with untrusted input."
                    ),
                    code_snippet=code_snippet,
                    cwe_id="CWE-502",
                    owasp_category="A08:2021",
                    confidence=0.9,
                    remediation=(
                        "Avoid marshal for deserialization of untrusted data. "
                        "Use JSON with strict validation instead."
                    ),
                    references=["https://cwe.mitre.org/data/definitions/502.html"],
                ))

            elif func_chain == "yaml.unsafe_load":
                findings.append(VulnerabilityFinding(
                    file_path=str(file_path),
                    line_number=line_number,
                    vulnerability_type=VulnerabilityType.INSECURE_DESERIALIZATION,
                    severity=SecuritySeverity.CRITICAL,
                    title="Insecure YAML Deserialization via yaml.unsafe_load",
                    description=(
                        "yaml.unsafe_load can deserialize arbitrary Python objects "
                        "and execute arbitrary code from YAML input."
                    ),
                    code_snippet=code_snippet,
                    cwe_id="CWE-502",
                    owasp_category="A08:2021",
                    confidence=0.95,
                    remediation=(
                        "Replace yaml.unsafe_load with yaml.safe_load or "
                        "yaml.load(data, Loader=yaml.SafeLoader)."
                    ),
                    references=["https://cwe.mitre.org/data/definitions/502.html"],
                ))

            elif func_chain == "yaml.load":
                loader_arg: Optional[str] = None
                for kw in node.keywords:
                    if kw.arg == "Loader":
                        if isinstance(kw.value, ast.Attribute):
                            loader_arg = kw.value.attr
                        elif isinstance(kw.value, ast.Name):
                            loader_arg = kw.value.id
                        break
                if loader_arg is None and len(node.args) >= 2:
                    arg2 = node.args[1]
                    if isinstance(arg2, ast.Attribute):
                        loader_arg = arg2.attr
                    elif isinstance(arg2, ast.Name):
                        loader_arg = arg2.id

                safe_loaders = {"SafeLoader", "BaseLoader", "FullLoader"}
                if loader_arg not in safe_loaders:
                    findings.append(VulnerabilityFinding(
                        file_path=str(file_path),
                        line_number=line_number,
                        vulnerability_type=VulnerabilityType.INSECURE_DESERIALIZATION,
                        severity=SecuritySeverity.HIGH,
                        title="Insecure YAML Deserialization via yaml.load without SafeLoader",
                        description=(
                            "yaml.load called without a safe Loader can deserialize arbitrary "
                            "Python objects and execute code from YAML input."
                        ),
                        code_snippet=code_snippet,
                        cwe_id="CWE-502",
                        owasp_category="A08:2021",
                        confidence=0.85,
                        remediation=(
                            "Specify Loader=yaml.SafeLoader: yaml.load(data, Loader=yaml.SafeLoader) "
                            "or use yaml.safe_load(data)."
                        ),
                        references=["https://cwe.mitre.org/data/definitions/502.html"],
                    ))

            elif func_chain == "jsonpickle.decode":
                findings.append(VulnerabilityFinding(
                    file_path=str(file_path),
                    line_number=line_number,
                    vulnerability_type=VulnerabilityType.INSECURE_DESERIALIZATION,
                    severity=SecuritySeverity.HIGH,
                    title="Insecure Deserialization via jsonpickle.decode",
                    description=(
                        "jsonpickle.decode can instantiate arbitrary Python objects "
                        "from JSON-encoded data, enabling code execution from untrusted input."
                    ),
                    code_snippet=code_snippet,
                    cwe_id="CWE-502",
                    owasp_category="A08:2021",
                    confidence=0.9,
                    remediation=(
                        "Use standard json.loads for untrusted data. "
                        "If jsonpickle is required, validate the source of the data strictly."
                    ),
                    references=["https://cwe.mitre.org/data/definitions/502.html"],
                ))

            elif func_chain == "shelve.open":
                findings.append(VulnerabilityFinding(
                    file_path=str(file_path),
                    line_number=line_number,
                    vulnerability_type=VulnerabilityType.INSECURE_DESERIALIZATION,
                    severity=SecuritySeverity.MEDIUM,
                    title="Potentially Insecure Deserialization via shelve.open",
                    description=(
                        "shelve uses pickle internally to serialize/deserialize objects. "
                        "If the shelf file path comes from user input, this can be exploited."
                    ),
                    code_snippet=code_snippet,
                    cwe_id="CWE-502",
                    owasp_category="A08:2021",
                    confidence=0.6,
                    remediation=(
                        "Ensure the shelf file path is not user-controlled. "
                        "Consider using a safer storage format for user-accessible data."
                    ),
                    references=["https://cwe.mitre.org/data/definitions/502.html"],
                ))

            elif func_chain in ("dill.loads", "dill.load"):
                findings.append(VulnerabilityFinding(
                    file_path=str(file_path),
                    line_number=line_number,
                    vulnerability_type=VulnerabilityType.INSECURE_DESERIALIZATION,
                    severity=SecuritySeverity.CRITICAL,
                    title="Insecure Deserialization via dill",
                    description=(
                        "dill.loads/dill.load can serialize and deserialize virtually any Python "
                        "object including lambdas and closures, enabling arbitrary code execution "
                        "from untrusted data. dill is more dangerous than pickle."
                    ),
                    code_snippet=code_snippet,
                    cwe_id="CWE-502",
                    owasp_category="A08:2021",
                    confidence=0.95,
                    remediation=(
                        "Never deserialize data from untrusted sources using dill. "
                        "Use safe formats such as JSON with schema validation."
                    ),
                    references=["https://cwe.mitre.org/data/definitions/502.html"],
                ))

        return findings

    def detect_ssrf(
        self,
        file_path: Path,
        source_code: str,
    ) -> List[VulnerabilityFinding]:
        """
        Detect SSRF (Server-Side Request Forgery) patterns in a single source file.

        Uses AST analysis to identify HTTP client calls where the URL argument
        is a variable or expression rather than a string literal.

        Args:
            file_path: Path to the source file being analyzed.
            source_code: Source code content of the file.

        Returns:
            List of VulnerabilityFinding objects for potential SSRF patterns.
        """
        findings: List[VulnerabilityFinding] = []

        if file_path.suffix.lower() != ".py":
            return findings

        lines = source_code.splitlines()

        try:
            tree = ast.parse(source_code, filename=str(file_path))
        except SyntaxError:
            return findings

        HTTP_CALL_PATTERNS: Dict[str, int] = {
            "requests.get": 0,
            "requests.post": 0,
            "requests.put": 0,
            "requests.delete": 0,
            "requests.patch": 0,
            "requests.head": 0,
            "requests.options": 0,
            "requests.request": 1,
            "session.get": 0,
            "session.post": 0,
            "session.put": 0,
            "session.delete": 0,
            "session.patch": 0,
            "session.request": 1,
            "urllib.request.urlopen": 0,
            "urlopen": 0,
            "httpx.get": 0,
            "httpx.post": 0,
            "httpx.put": 0,
            "httpx.delete": 0,
            "httpx.patch": 0,
            "httpx.request": 1,
            "aiohttp.ClientSession.get": 0,
            "aiohttp.ClientSession.post": 0,
            "aiohttp.request": 1,
        }

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            func_chain = ""
            if isinstance(node.func, ast.Attribute):
                parts: List[str] = []
                current: ast.AST = node.func
                while isinstance(current, ast.Attribute):
                    parts.append(current.attr)
                    current = current.value
                if isinstance(current, ast.Name):
                    parts.append(current.id)
                parts.reverse()
                func_chain = ".".join(parts)
            elif isinstance(node.func, ast.Name):
                func_chain = node.func.id

            url_arg_pos: Optional[int] = None
            for pattern, pos in HTTP_CALL_PATTERNS.items():
                if func_chain == pattern:
                    url_arg_pos = pos
                    break

            if url_arg_pos is None:
                continue

            url_node: Optional[ast.AST] = None
            for kw in node.keywords:
                if kw.arg == "url":
                    url_node = kw.value
                    break

            if url_node is None and len(node.args) > url_arg_pos:
                url_node = node.args[url_arg_pos]

            if url_node is None:
                continue

            if isinstance(url_node, ast.Constant) and isinstance(url_node.value, str):
                continue

            line_number = node.lineno
            code_snippet = lines[line_number - 1].strip() if 0 < line_number <= len(lines) else ""

            if isinstance(url_node, ast.JoinedStr):
                severity = SecuritySeverity.MEDIUM
                url_desc = "an f-string expression"
            else:
                severity = SecuritySeverity.HIGH
                url_desc = "a variable or non-literal expression"

            findings.append(VulnerabilityFinding(
                file_path=str(file_path),
                line_number=line_number,
                vulnerability_type=VulnerabilityType.SSRF,
                severity=severity,
                title="Potential Server-Side Request Forgery (SSRF)",
                description=(
                    f"HTTP client call '{func_chain}' uses {url_desc} as the URL. "
                    "If this value originates from user input, an attacker may be able to "
                    "cause the server to make requests to arbitrary internal or external hosts."
                ),
                code_snippet=code_snippet,
                cwe_id="CWE-918",
                owasp_category="A10:2021",
                confidence=0.65,
                remediation=(
                    "Validate and allowlist URLs before making outbound requests. "
                    "Never use user-controlled data directly as a request URL. "
                    "Use an allowlist of permitted domains and reject requests to internal networks."
                ),
                references=[
                    "https://cwe.mitre.org/data/definitions/918.html",
                    "https://owasp.org/Top10/A10_2021-Server-Side_Request_Forgery_%28SSRF%29/",
                ],
            ))

        return findings

    def scan_for_sql_injection(self, scan_path: Optional[Path] = None) -> VulnerabilityReport:
        """
        Scan specifically for SQL injection vulnerabilities.

        Args:
            scan_path: Root path to scan

        Returns:
            VulnerabilityReport with SQL injection findings only
        """
        original_patterns = self.patterns
        self.patterns = SQL_INJECTION_PATTERNS

        try:
            report = self.scan(scan_path)
        finally:
            self.patterns = original_patterns

        return report

    def scan_for_xss(self, scan_path: Optional[Path] = None) -> VulnerabilityReport:
        """
        Scan specifically for XSS vulnerabilities.

        Args:
            scan_path: Root path to scan

        Returns:
            VulnerabilityReport with XSS findings only
        """
        original_patterns = self.patterns
        self.patterns = XSS_PATTERNS

        try:
            report = self.scan(scan_path)
        finally:
            self.patterns = original_patterns

        return report

    def scan_for_command_injection(self, scan_path: Optional[Path] = None) -> VulnerabilityReport:
        """
        Scan specifically for command injection vulnerabilities.

        Args:
            scan_path: Root path to scan

        Returns:
            VulnerabilityReport with command injection findings only
        """
        original_patterns = self.patterns
        self.patterns = COMMAND_INJECTION_PATTERNS + PATH_TRAVERSAL_PATTERNS

        try:
            report = self.scan(scan_path)
        finally:
            self.patterns = original_patterns

        return report
