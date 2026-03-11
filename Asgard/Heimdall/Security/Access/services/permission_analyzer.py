"""
Heimdall Permission Analyzer Service

Service for detecting permission-related issues in route handlers.
"""

import ast
import re
import time
from pathlib import Path
from typing import List, Optional, Set

from Asgard.Heimdall.Security.Access.models.access_models import (
    AccessConfig,
    AccessFinding,
    AccessFindingType,
    AccessReport,
)
from Asgard.Heimdall.Security.Access.utilities.decorator_utils import (
    extract_decorators,
    find_route_handlers,
    has_auth_decorator,
    RouteHandler,
)
from Asgard.Heimdall.Security.models.security_models import SecuritySeverity
from Asgard.Heimdall.Security.utilities.security_utils import (
    extract_code_snippet,
    scan_directory_for_security,
)


class PermissionAnalyzer:
    """
    Analyzes route handlers for missing authentication and permission checks.

    Detects:
    - Routes without authentication decorators
    - Sensitive endpoints without proper access control
    - Missing role checks on admin endpoints
    """

    def __init__(self, config: Optional[AccessConfig] = None):
        """
        Initialize the permission analyzer.

        Args:
            config: Access control configuration. Uses defaults if not provided.
        """
        self.config = config or AccessConfig()

    def scan(self, scan_path: Optional[Path] = None) -> AccessReport:
        """
        Scan the specified path for permission issues.

        Args:
            scan_path: Root path to scan. Uses config path if not provided.

        Returns:
            AccessReport containing all findings
        """
        path = scan_path or self.config.scan_path
        path = Path(path).resolve()

        if not path.exists():
            raise FileNotFoundError(f"Scan path does not exist: {path}")

        start_time = time.time()

        report = AccessReport(scan_path=str(path))

        for file_path in scan_directory_for_security(
            path,
            exclude_patterns=self.config.exclude_patterns,
            include_extensions=[".py"],
        ):
            report.total_files_scanned += 1
            findings, routes_info = self._scan_file(file_path, path)

            report.total_routes_analyzed += routes_info["total"]
            report.routes_with_auth += routes_info["with_auth"]
            report.routes_without_auth += routes_info["without_auth"]

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

    def _scan_file(self, file_path: Path, root_path: Path) -> tuple:
        """
        Scan a single file for permission issues.

        Args:
            file_path: Path to the file to scan
            root_path: Root path for relative path calculation

        Returns:
            Tuple of (findings list, routes info dict)
        """
        findings: List[AccessFinding] = []
        routes_info = {"total": 0, "with_auth": 0, "without_auth": 0}

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except (IOError, OSError):
            return findings, routes_info

        lines = content.split("\n")

        route_handlers = find_route_handlers(content, self.config.route_decorators)

        for handler in route_handlers:
            routes_info["total"] += 1

            has_auth = has_auth_decorator(handler.decorators, self.config.auth_decorators)

            if has_auth:
                routes_info["with_auth"] += 1
            else:
                routes_info["without_auth"] += 1

                is_sensitive = self._is_sensitive_endpoint(handler)

                if is_sensitive:
                    severity = SecuritySeverity.HIGH
                    title = "Sensitive Endpoint Missing Authentication"
                    description = (
                        f"The endpoint '{handler.endpoint or handler.function_name}' "
                        "appears to handle sensitive operations but has no authentication decorator."
                    )
                else:
                    severity = SecuritySeverity.MEDIUM
                    title = "Route Handler Missing Authentication"
                    description = (
                        f"The route handler '{handler.function_name}' "
                        "does not have an authentication decorator."
                    )

                code_snippet = extract_code_snippet(lines, handler.line_number)

                finding = AccessFinding(
                    file_path=str(file_path.relative_to(root_path)),
                    line_number=handler.line_number,
                    finding_type=AccessFindingType.MISSING_AUTH_CHECK,
                    severity=severity,
                    title=title,
                    description=description,
                    code_snippet=code_snippet,
                    endpoint=handler.endpoint,
                    function_name=handler.function_name,
                    cwe_id="CWE-862",
                    confidence=0.8 if is_sensitive else 0.6,
                    remediation=(
                        "Add an authentication decorator such as @login_required, "
                        "@jwt_required, or implement proper access control middleware."
                    ),
                    references=[
                        "https://cwe.mitre.org/data/definitions/862.html",
                        "https://owasp.org/Top10/A01_2021-Broken_Access_Control/",
                    ],
                )

                findings.append(finding)

        admin_findings = self._check_admin_routes(content, lines, file_path, root_path)
        findings.extend(admin_findings)

        return findings, routes_info

    def _is_sensitive_endpoint(self, handler: RouteHandler) -> bool:
        """
        Check if a route handler is for a sensitive endpoint.

        Args:
            handler: RouteHandler to check

        Returns:
            True if the endpoint appears to be sensitive
        """
        check_strings = [
            handler.function_name.lower(),
            (handler.endpoint or "").lower(),
        ]

        for check_str in check_strings:
            for keyword in self.config.sensitive_endpoints:
                if keyword in check_str:
                    return True

        if handler.http_method in ("POST", "PUT", "DELETE", "PATCH"):
            return True

        return False

    def _check_admin_routes(
        self,
        content: str,
        lines: List[str],
        file_path: Path,
        root_path: Path,
    ) -> List[AccessFinding]:
        """
        Check for admin routes without proper role checks.

        Args:
            content: File content
            lines: File lines
            file_path: Path to file
            root_path: Root path

        Returns:
            List of findings for admin route issues
        """
        findings = []

        admin_patterns = [
            r"@.*route\s*\(\s*['\"][^'\"]*admin[^'\"]*['\"]",
            r"@router\.(?:get|post|put|delete)\s*\(\s*['\"][^'\"]*admin[^'\"]*['\"]",
            r"def\s+admin_\w+\s*\(",
        ]

        for pattern_str in admin_patterns:
            pattern = re.compile(pattern_str, re.IGNORECASE)

            for match in pattern.finditer(content):
                line_number = content[:match.start()].count("\n") + 1

                context_start = max(0, match.start() - 200)
                context_end = min(len(content), match.end() + 500)
                context = content[context_start:context_end]

                has_role_check = any(
                    decorator in context.lower()
                    for decorator in ["admin_required", "require_admin", "is_admin", "role"]
                )

                if not has_role_check:
                    code_snippet = extract_code_snippet(lines, line_number)

                    finding = AccessFinding(
                        file_path=str(file_path.relative_to(root_path)),
                        line_number=line_number,
                        finding_type=AccessFindingType.MISSING_ROLE_CHECK,
                        severity=SecuritySeverity.HIGH,
                        title="Admin Endpoint Without Role Check",
                        description="An admin endpoint was found without explicit role verification.",
                        code_snippet=code_snippet,
                        cwe_id="CWE-285",
                        confidence=0.75,
                        remediation=(
                            "Add role verification using @admin_required decorator or "
                            "explicit role checking logic."
                        ),
                        references=[
                            "https://cwe.mitre.org/data/definitions/285.html",
                        ],
                    )

                    findings.append(finding)

        return findings

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
