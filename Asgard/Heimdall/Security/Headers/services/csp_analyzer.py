"""
Heimdall CSP Analyzer Service

Service for analyzing Content-Security-Policy configurations.
"""

import re
import time
from pathlib import Path
from typing import List, Optional

from Asgard.Heimdall.Security.Headers.models.header_models import (
    HeaderConfig,
    HeaderFinding,
    HeaderFindingType,
    HeaderReport,
)
from Asgard.Heimdall.Security.Headers.utilities.csp_parser import (
    ParsedCSP,
    extract_csp_from_code,
    parse_csp,
)
from Asgard.Heimdall.Security.models.security_models import SecuritySeverity
from Asgard.Heimdall.Security.utilities.security_utils import (
    extract_code_snippet,
    find_line_column,
    scan_directory_for_security,
)


class CSPAnalyzer:
    """
    Analyzes Content-Security-Policy configurations.

    Detects:
    - unsafe-inline usage
    - unsafe-eval usage
    - Wildcard sources
    - Missing directives
    - Weak CSP configurations
    """

    def __init__(self, config: Optional[HeaderConfig] = None):
        """
        Initialize the CSP analyzer.

        Args:
            config: Header configuration. Uses defaults if not provided.
        """
        self.config = config or HeaderConfig()

    def scan(self, scan_path: Optional[Path] = None) -> HeaderReport:
        """
        Scan the specified path for CSP security issues.

        Args:
            scan_path: Root path to scan. Uses config path if not provided.

        Returns:
            HeaderReport containing all findings
        """
        path = scan_path or self.config.scan_path
        path = Path(path).resolve()

        if not path.exists():
            raise FileNotFoundError(f"Scan path does not exist: {path}")

        start_time = time.time()

        report = HeaderReport(scan_path=str(path))

        for file_path in scan_directory_for_security(
            path,
            exclude_patterns=self.config.exclude_patterns,
            include_extensions=[".py", ".js", ".ts", ".conf", ".yaml", ".yml", ".json", ".html"],
        ):
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

    def _scan_file(self, file_path: Path, root_path: Path) -> List[HeaderFinding]:
        """
        Scan a single file for CSP issues.

        Args:
            file_path: Path to the file to scan
            root_path: Root path for relative path calculation

        Returns:
            List of header findings in the file
        """
        findings: List[HeaderFinding] = []

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except (IOError, OSError):
            return findings

        lines = content.split("\n")

        csp_occurrences = extract_csp_from_code(content)

        for line_number, csp_value in csp_occurrences:
            parsed_csp = parse_csp(csp_value)
            csp_findings = self._analyze_csp(parsed_csp, line_number, csp_value, lines, file_path, root_path)
            findings.extend(csp_findings)

        inline_findings = self._check_inline_patterns(content, lines, file_path, root_path)
        findings.extend(inline_findings)

        return findings

    def _analyze_csp(
        self,
        csp: ParsedCSP,
        line_number: int,
        csp_value: str,
        lines: List[str],
        file_path: Path,
        root_path: Path,
    ) -> List[HeaderFinding]:
        """
        Analyze a parsed CSP for security issues.

        Args:
            csp: Parsed CSP object
            line_number: Line number where CSP was found
            csp_value: Raw CSP value
            lines: File lines
            file_path: Path to file
            root_path: Root path

        Returns:
            List of findings
        """
        findings = []
        code_snippet = extract_code_snippet(lines, line_number)

        for directive_name, directive in csp.directives.items():
            if directive.has_unsafe_inline:
                findings.append(HeaderFinding(
                    file_path=str(file_path.relative_to(root_path)),
                    line_number=line_number,
                    finding_type=HeaderFindingType.CSP_UNSAFE_INLINE,
                    severity=SecuritySeverity.HIGH,
                    title=f"CSP {directive_name} Uses unsafe-inline",
                    description=f"The {directive_name} directive allows 'unsafe-inline' which defeats CSP protection against XSS.",
                    code_snippet=code_snippet,
                    header_name="Content-Security-Policy",
                    header_value=csp_value[:200] if len(csp_value) > 200 else csp_value,
                    cwe_id="CWE-79",
                    confidence=0.9,
                    remediation=f"Remove 'unsafe-inline' from {directive_name}. Use nonces or hashes for inline scripts/styles.",
                    references=[
                        "https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP",
                        "https://cwe.mitre.org/data/definitions/79.html",
                    ],
                ))

            if directive.has_unsafe_eval:
                findings.append(HeaderFinding(
                    file_path=str(file_path.relative_to(root_path)),
                    line_number=line_number,
                    finding_type=HeaderFindingType.CSP_UNSAFE_EVAL,
                    severity=SecuritySeverity.HIGH,
                    title=f"CSP {directive_name} Uses unsafe-eval",
                    description=f"The {directive_name} directive allows 'unsafe-eval' which permits eval() and similar methods.",
                    code_snippet=code_snippet,
                    header_name="Content-Security-Policy",
                    header_value=csp_value[:200] if len(csp_value) > 200 else csp_value,
                    cwe_id="CWE-95",
                    confidence=0.9,
                    remediation=f"Remove 'unsafe-eval' from {directive_name}. Refactor code to avoid eval(), Function(), and similar.",
                    references=[
                        "https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP",
                        "https://cwe.mitre.org/data/definitions/95.html",
                    ],
                ))

            if directive.has_wildcard:
                findings.append(HeaderFinding(
                    file_path=str(file_path.relative_to(root_path)),
                    line_number=line_number,
                    finding_type=HeaderFindingType.CSP_WILDCARD_SOURCE,
                    severity=SecuritySeverity.MEDIUM,
                    title=f"CSP {directive_name} Uses Wildcard Source",
                    description=f"The {directive_name} directive uses wildcard (*) which allows loading from any origin.",
                    code_snippet=code_snippet,
                    header_name="Content-Security-Policy",
                    header_value=csp_value[:200] if len(csp_value) > 200 else csp_value,
                    cwe_id="CWE-693",
                    confidence=0.85,
                    remediation=f"Replace wildcard in {directive_name} with specific trusted origins.",
                    references=[
                        "https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP",
                    ],
                ))

        for missing_directive in csp.missing_recommended_directives:
            if missing_directive in self.config.required_csp_directives:
                findings.append(HeaderFinding(
                    file_path=str(file_path.relative_to(root_path)),
                    line_number=line_number,
                    finding_type=HeaderFindingType.CSP_MISSING_DIRECTIVE,
                    severity=SecuritySeverity.MEDIUM,
                    title=f"CSP Missing {missing_directive} Directive",
                    description=f"The Content-Security-Policy is missing the recommended {missing_directive} directive.",
                    code_snippet=code_snippet,
                    header_name="Content-Security-Policy",
                    header_value=csp_value[:200] if len(csp_value) > 200 else csp_value,
                    cwe_id="CWE-693",
                    confidence=0.7,
                    remediation=f"Add the {missing_directive} directive to your CSP policy.",
                    references=[
                        "https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP",
                    ],
                ))

        return findings

    def _check_inline_patterns(
        self,
        content: str,
        lines: List[str],
        file_path: Path,
        root_path: Path,
    ) -> List[HeaderFinding]:
        """
        Check for patterns that suggest CSP issues.

        Args:
            content: File content
            lines: File lines
            file_path: Path to file
            root_path: Root path

        Returns:
            List of findings
        """
        findings = []

        weak_csp_patterns = [
            (r"default-src\s+['\"]?\*['\"]?", "default-src allows all sources"),
            (r"script-src\s+['\"]?\*['\"]?", "script-src allows all sources"),
            (r"Content-Security-Policy[^;]*['\"]?unsafe-inline['\"]?[^;]*script", "CSP allows inline scripts"),
        ]

        for pattern, issue_desc in weak_csp_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                line_number, column = find_line_column(content, match.start())

                if self._is_in_comment(lines, line_number):
                    continue

                code_snippet = extract_code_snippet(lines, line_number)

                findings.append(HeaderFinding(
                    file_path=str(file_path.relative_to(root_path)),
                    line_number=line_number,
                    column_start=column,
                    column_end=column + len(match.group(0)),
                    finding_type=HeaderFindingType.WEAK_CSP,
                    severity=SecuritySeverity.HIGH,
                    title="Weak Content-Security-Policy",
                    description=f"Content-Security-Policy has a weak configuration: {issue_desc}.",
                    code_snippet=code_snippet,
                    header_name="Content-Security-Policy",
                    cwe_id="CWE-693",
                    confidence=0.8,
                    remediation="Strengthen the CSP by using specific sources and removing unsafe directives.",
                    references=[
                        "https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP",
                        "https://csp-evaluator.withgoogle.com/",
                    ],
                ))

        return findings

    def _is_in_comment(self, lines: List[str], line_number: int) -> bool:
        """Check if a line is inside a comment."""
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

    def analyze_csp_string(self, csp_string: str) -> List[str]:
        """
        Analyze a CSP string and return issues.

        Args:
            csp_string: The CSP header value

        Returns:
            List of issue descriptions
        """
        parsed = parse_csp(csp_string)
        issues = []

        for directive_name, unsafe_value in parsed.unsafe_directives:
            issues.append(f"{directive_name} contains {unsafe_value}")

        for missing in parsed.missing_recommended_directives:
            issues.append(f"Missing recommended directive: {missing}")

        return issues
