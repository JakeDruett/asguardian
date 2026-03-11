"""
Heimdall Security Hotspot Detector Service

Detects security-sensitive code patterns in Python source files using AST
analysis and regular expressions. Hotspots are not confirmed vulnerabilities
but areas that require manual security review.

Detected categories:
1. Cookie Configuration - insecure cookie settings
2. Cryptographic Code - crypto module usage (flag for review)
3. Dynamic Code Execution - eval, exec, compile, __import__
4. Regex DoS (ReDoS) - complex nested quantifier patterns
5. XML External Entity (XXE) - XML parsing without explicit entity disabling
6. Pickle/Deserialization - unsafe deserialization calls
7. SSRF - HTTP calls with potentially user-supplied URLs
8. Random Number Generation - use of random module for security operations
9. Permission / Authorization Checks - os.chmod, os.access usage
10. HTTP Request Without TLS Verification - verify=False in requests calls
"""

import ast
import fnmatch
import os
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from Asgard.Heimdall.Security.Hotspots.models.hotspot_models import (
    HotspotCategory,
    HotspotConfig,
    HotspotReport,
    ReviewPriority,
    ReviewStatus,
    SecurityHotspot,
)

# Regex patterns used for hotspot detection
_RE_SECURE_FALSE = re.compile(r"\bsecure\s*=\s*False", re.IGNORECASE)
_RE_HTTPONLY_FALSE = re.compile(r"\bhttponly\s*=\s*False", re.IGNORECASE)
_RE_VERIFY_FALSE = re.compile(r"\bverify\s*=\s*False")
_RE_NESTED_QUANTIFIER = re.compile(r"[*+?{][*+?{]|(?:\([^)]*[*+?]\)[*+?{])")
_RE_YAML_LOAD_UNSAFE = re.compile(r"\byaml\.load\s*\((?!.*Loader\s*=\s*yaml\.SafeLoader)")


class HotspotDetector:
    """
    Detects security-sensitive code patterns requiring manual review.

    Uses AST analysis combined with regex scanning to identify patterns
    across ten hotspot categories aligned with OWASP Top 10 and CWE Top 25.

    Usage:
        detector = HotspotDetector()
        report = detector.scan(Path("./src"))

        print(f"Total hotspots: {report.total_hotspots}")
        for hotspot in report.hotspots:
            print(f"  [{hotspot.review_priority}] {hotspot.title} at {hotspot.file_path}:{hotspot.line_number}")
    """

    def __init__(self, config: Optional[HotspotConfig] = None):
        """
        Initialize the hotspot detector.

        Args:
            config: Configuration for the detector. If None, uses defaults.
        """
        self.config = config or HotspotConfig()

    def scan(self, scan_path: Path) -> HotspotReport:
        """
        Scan a directory for security hotspots.

        Args:
            scan_path: Path to directory to analyze

        Returns:
            HotspotReport with all detected hotspots

        Raises:
            FileNotFoundError: If scan_path does not exist
        """
        if not scan_path.exists():
            raise FileNotFoundError(f"Path does not exist: {scan_path}")

        start_time = datetime.now()
        report = HotspotReport(scan_path=str(scan_path))

        for root, dirs, files in os.walk(scan_path):
            root_path = Path(root)

            dirs[:] = [
                d for d in dirs
                if not any(self._matches_pattern(d, p) for p in self.config.exclude_patterns)
            ]

            for file in files:
                if not self._should_analyze_file(file):
                    continue

                file_path = root_path / file
                try:
                    hotspots = self._analyze_file(file_path)
                    for hotspot in hotspots:
                        if self._meets_min_priority(hotspot.review_priority):
                            report.add_hotspot(hotspot)
                except Exception:
                    pass

        report.scan_duration_seconds = (datetime.now() - start_time).total_seconds()

        return report

    def _analyze_file(self, file_path: Path) -> List[SecurityHotspot]:
        """Analyze a single file for hotspots using AST and regex."""
        try:
            source = file_path.read_text(encoding="utf-8")
        except Exception:
            return []

        hotspots: List[SecurityHotspot] = []
        lines = source.splitlines()
        str_path = str(file_path)

        # AST-based detection
        try:
            tree = ast.parse(source)
            hotspots.extend(self._detect_ast_hotspots(tree, str_path, lines))
        except SyntaxError:
            pass

        # Regex-based detection on raw source lines
        hotspots.extend(self._detect_regex_hotspots(lines, str_path))

        return hotspots

    def _detect_ast_hotspots(
        self, tree: ast.AST, file_path: str, lines: List[str]
    ) -> List[SecurityHotspot]:
        """Perform AST-based hotspot detection."""
        hotspots: List[SecurityHotspot] = []

        for node in ast.walk(tree):
            # Dynamic code execution: eval, exec, compile, __import__
            if HotspotCategory.DYNAMIC_EXECUTION in self.config.enabled_categories:
                if isinstance(node, ast.Call):
                    func_name = self._get_call_name(node)
                    if func_name in ("eval", "exec", "compile", "__import__"):
                        snippet = self._get_line(lines, node.lineno)
                        hotspots.append(SecurityHotspot(
                            file_path=file_path,
                            line_number=node.lineno,
                            category=HotspotCategory.DYNAMIC_EXECUTION,
                            review_priority=ReviewPriority.HIGH,
                            title=f"Dynamic code execution: {func_name}()",
                            description=(
                                f"Call to '{func_name}()' executes arbitrary code. "
                                "Ensure the input is never derived from user-controlled data."
                            ),
                            code_snippet=snippet,
                            review_guidance=(
                                "Verify the argument cannot be influenced by external input. "
                                "Consider replacing with safer alternatives such as ast.literal_eval "
                                "for data parsing."
                            ),
                            review_status=ReviewStatus.TO_REVIEW,
                            owasp_category="A03:Injection",
                            cwe_id="CWE-94",
                        ))

            # Pickle / insecure deserialization
            if HotspotCategory.INSECURE_DESERIALIZATION in self.config.enabled_categories:
                if isinstance(node, ast.Call):
                    func_name = self._get_call_name(node)
                    if func_name in ("pickle.loads", "pickle.load", "marshal.loads", "marshal.load"):
                        snippet = self._get_line(lines, node.lineno)
                        hotspots.append(SecurityHotspot(
                            file_path=file_path,
                            line_number=node.lineno,
                            category=HotspotCategory.INSECURE_DESERIALIZATION,
                            review_priority=ReviewPriority.HIGH,
                            title=f"Insecure deserialization: {func_name}()",
                            description=(
                                f"'{func_name}()' deserializes untrusted data which can "
                                "lead to arbitrary code execution."
                            ),
                            code_snippet=snippet,
                            review_guidance=(
                                "Verify the data source is trusted and cannot be tampered with. "
                                "Consider using JSON or another safer serialization format."
                            ),
                            review_status=ReviewStatus.TO_REVIEW,
                            owasp_category="A08:Software and Data Integrity Failures",
                            cwe_id="CWE-502",
                        ))

            # Cryptographic module usage
            if HotspotCategory.CRYPTO_USAGE in self.config.enabled_categories:
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in ("hashlib", "hmac", "cryptography", "Crypto"):
                            hotspots.append(SecurityHotspot(
                                file_path=file_path,
                                line_number=node.lineno,
                                category=HotspotCategory.CRYPTO_USAGE,
                                review_priority=ReviewPriority.LOW,
                                title=f"Cryptographic module import: {alias.name}",
                                description=(
                                    f"Import of '{alias.name}' detected. Review cryptographic "
                                    "implementation for algorithm strength and correct usage."
                                ),
                                code_snippet=self._get_line(lines, node.lineno),
                                review_guidance=(
                                    "Ensure strong algorithms are used (SHA-256+, AES-128+). "
                                    "Avoid MD5, SHA-1 for security-sensitive operations. "
                                    "Ensure keys and IVs are generated securely."
                                ),
                                review_status=ReviewStatus.TO_REVIEW,
                                owasp_category="A02:Cryptographic Failures",
                                cwe_id="CWE-327",
                            ))
                if isinstance(node, ast.ImportFrom):
                    if node.module and node.module.split(".")[0] in ("hashlib", "hmac", "cryptography", "Crypto"):
                        hotspots.append(SecurityHotspot(
                            file_path=file_path,
                            line_number=node.lineno,
                            category=HotspotCategory.CRYPTO_USAGE,
                            review_priority=ReviewPriority.LOW,
                            title=f"Cryptographic module import: {node.module}",
                            description=(
                                f"Import from '{node.module}' detected. Review cryptographic "
                                "implementation for algorithm strength and correct usage."
                            ),
                            code_snippet=self._get_line(lines, node.lineno),
                            review_guidance=(
                                "Ensure strong algorithms are used (SHA-256+, AES-128+). "
                                "Avoid MD5, SHA-1 for security-sensitive operations."
                            ),
                            review_status=ReviewStatus.TO_REVIEW,
                            owasp_category="A02:Cryptographic Failures",
                            cwe_id="CWE-327",
                        ))

            # XML External Entity (XXE)
            if HotspotCategory.XXE in self.config.enabled_categories:
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in ("xml.etree.ElementTree", "xml.etree", "lxml", "minidom"):
                            hotspots.append(SecurityHotspot(
                                file_path=file_path,
                                line_number=node.lineno,
                                category=HotspotCategory.XXE,
                                review_priority=ReviewPriority.MEDIUM,
                                title=f"XML parsing library imported: {alias.name}",
                                description=(
                                    f"Import of '{alias.name}' detected. XML parsers may be "
                                    "vulnerable to XXE attacks if external entity processing is enabled."
                                ),
                                code_snippet=self._get_line(lines, node.lineno),
                                review_guidance=(
                                    "Disable external entity processing. For lxml, use "
                                    "etree.XMLParser(resolve_entities=False). For xml.etree, "
                                    "external entities are disabled by default in Python 3.8+."
                                ),
                                review_status=ReviewStatus.TO_REVIEW,
                                owasp_category="A05:Security Misconfiguration",
                                cwe_id="CWE-611",
                            ))
                if isinstance(node, ast.ImportFrom):
                    if node.module and any(
                        node.module.startswith(m) for m in ("xml.etree", "lxml", "xml.dom.minidom")
                    ):
                        hotspots.append(SecurityHotspot(
                            file_path=file_path,
                            line_number=node.lineno,
                            category=HotspotCategory.XXE,
                            review_priority=ReviewPriority.MEDIUM,
                            title=f"XML parsing module imported: {node.module}",
                            description=(
                                f"Import from '{node.module}' detected. Verify external entity "
                                "processing is disabled."
                            ),
                            code_snippet=self._get_line(lines, node.lineno),
                            review_guidance=(
                                "Ensure external entity resolution is disabled for all XML parsing. "
                                "Use defusedxml library for untrusted XML input."
                            ),
                            review_status=ReviewStatus.TO_REVIEW,
                            owasp_category="A05:Security Misconfiguration",
                            cwe_id="CWE-611",
                        ))

            # Insecure random
            if HotspotCategory.INSECURE_RANDOM in self.config.enabled_categories:
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name == "random":
                            hotspots.append(SecurityHotspot(
                                file_path=file_path,
                                line_number=node.lineno,
                                category=HotspotCategory.INSECURE_RANDOM,
                                review_priority=ReviewPriority.MEDIUM,
                                title="Use of random module (not cryptographically secure)",
                                description=(
                                    "The 'random' module uses a pseudo-random number generator "
                                    "unsuitable for security-sensitive operations."
                                ),
                                code_snippet=self._get_line(lines, node.lineno),
                                review_guidance=(
                                    "If used for security-sensitive operations (tokens, passwords, "
                                    "session IDs), replace with the 'secrets' module."
                                ),
                                review_status=ReviewStatus.TO_REVIEW,
                                owasp_category="A02:Cryptographic Failures",
                                cwe_id="CWE-338",
                            ))
                if isinstance(node, ast.ImportFrom):
                    if node.module == "random":
                        hotspots.append(SecurityHotspot(
                            file_path=file_path,
                            line_number=node.lineno,
                            category=HotspotCategory.INSECURE_RANDOM,
                            review_priority=ReviewPriority.MEDIUM,
                            title="Import from random module (not cryptographically secure)",
                            description=(
                                "Import from 'random' module detected. The random module is not "
                                "suitable for security-sensitive operations."
                            ),
                            code_snippet=self._get_line(lines, node.lineno),
                            review_guidance=(
                                "Replace with 'secrets' module for security-sensitive operations."
                            ),
                            review_status=ReviewStatus.TO_REVIEW,
                            owasp_category="A02:Cryptographic Failures",
                            cwe_id="CWE-338",
                        ))

            # Permission checks
            if HotspotCategory.PERMISSION_CHECK in self.config.enabled_categories:
                if isinstance(node, ast.Call):
                    func_name = self._get_call_name(node)
                    if func_name in ("os.chmod", "os.access", "os.chown"):
                        snippet = self._get_line(lines, node.lineno)
                        hotspots.append(SecurityHotspot(
                            file_path=file_path,
                            line_number=node.lineno,
                            category=HotspotCategory.PERMISSION_CHECK,
                            review_priority=ReviewPriority.LOW,
                            title=f"Permission management call: {func_name}()",
                            description=(
                                f"Call to '{func_name}()' modifies or checks file permissions. "
                                "Verify that permissions are set securely and not too permissive."
                            ),
                            code_snippet=snippet,
                            review_guidance=(
                                "Ensure file permissions follow the principle of least privilege. "
                                "Avoid world-writable (0o777) or overly permissive modes."
                            ),
                            review_status=ReviewStatus.TO_REVIEW,
                            owasp_category="A01:Broken Access Control",
                            cwe_id="CWE-269",
                        ))

            # SSRF detection: requests.get/post/put/delete/request with variable URL
            if HotspotCategory.SSRF in self.config.enabled_categories:
                if isinstance(node, ast.Call):
                    func_name = self._get_call_name(node)
                    ssrf_funcs = (
                        "requests.get", "requests.post", "requests.put",
                        "requests.delete", "requests.request", "requests.patch",
                        "urllib.request.urlopen", "urllib.urlopen",
                    )
                    if func_name in ssrf_funcs:
                        # Check if first argument is a variable (Name node), not a constant
                        if node.args and isinstance(node.args[0], ast.Name):
                            snippet = self._get_line(lines, node.lineno)
                            hotspots.append(SecurityHotspot(
                                file_path=file_path,
                                line_number=node.lineno,
                                category=HotspotCategory.SSRF,
                                review_priority=ReviewPriority.HIGH,
                                title=f"Potential SSRF: {func_name}() with variable URL",
                                description=(
                                    f"'{func_name}()' is called with a variable URL argument. "
                                    "If the URL originates from user input, this may be vulnerable to SSRF."
                                ),
                                code_snippet=snippet,
                                review_guidance=(
                                    "Validate and whitelist allowed URL schemes and hosts. "
                                    "Reject requests to internal IP ranges (RFC 1918). "
                                    "Use an allow-list of permitted external hosts."
                                ),
                                review_status=ReviewStatus.TO_REVIEW,
                                owasp_category="A10:Server-Side Request Forgery",
                                cwe_id="CWE-918",
                            ))

        return hotspots

    def _detect_regex_hotspots(
        self, lines: List[str], file_path: str
    ) -> List[SecurityHotspot]:
        """Perform regex-based hotspot detection on raw source lines."""
        hotspots: List[SecurityHotspot] = []

        for line_num, line in enumerate(lines, start=1):
            # Cookie configuration: secure=False or httponly=False
            if HotspotCategory.COOKIE_CONFIG in self.config.enabled_categories:
                if _RE_SECURE_FALSE.search(line):
                    hotspots.append(SecurityHotspot(
                        file_path=file_path,
                        line_number=line_num,
                        category=HotspotCategory.COOKIE_CONFIG,
                        review_priority=ReviewPriority.MEDIUM,
                        title="Cookie set with secure=False",
                        description=(
                            "Cookie is set with secure=False. This allows the cookie to be "
                            "transmitted over unencrypted HTTP connections."
                        ),
                        code_snippet=line.strip(),
                        review_guidance=(
                            "Set secure=True on all cookies to ensure they are only sent "
                            "over HTTPS. Also set httponly=True to prevent JavaScript access."
                        ),
                        review_status=ReviewStatus.TO_REVIEW,
                        owasp_category="A07:Identification and Authentication Failures",
                        cwe_id="CWE-614",
                    ))

                if _RE_HTTPONLY_FALSE.search(line):
                    hotspots.append(SecurityHotspot(
                        file_path=file_path,
                        line_number=line_num,
                        category=HotspotCategory.COOKIE_CONFIG,
                        review_priority=ReviewPriority.MEDIUM,
                        title="Cookie set with httponly=False",
                        description=(
                            "Cookie is set with httponly=False. This allows JavaScript to access "
                            "the cookie, increasing XSS risk."
                        ),
                        code_snippet=line.strip(),
                        review_guidance=(
                            "Set httponly=True on session cookies to prevent JavaScript access "
                            "and mitigate XSS attacks."
                        ),
                        review_status=ReviewStatus.TO_REVIEW,
                        owasp_category="A07:Identification and Authentication Failures",
                        cwe_id="CWE-1004",
                    ))

            # TLS verification disabled
            if HotspotCategory.TLS_VERIFICATION in self.config.enabled_categories:
                if _RE_VERIFY_FALSE.search(line):
                    hotspots.append(SecurityHotspot(
                        file_path=file_path,
                        line_number=line_num,
                        category=HotspotCategory.TLS_VERIFICATION,
                        review_priority=ReviewPriority.LOW,
                        title="TLS certificate verification disabled (verify=False)",
                        description=(
                            "TLS certificate verification is disabled. This allows connections to "
                            "servers with invalid or self-signed certificates."
                        ),
                        code_snippet=line.strip(),
                        review_guidance=(
                            "Enable TLS verification (verify=True or use a custom CA bundle). "
                            "If a self-signed certificate is needed, provide it via verify='/path/to/ca.crt'."
                        ),
                        review_status=ReviewStatus.TO_REVIEW,
                        owasp_category="A02:Cryptographic Failures",
                        cwe_id="CWE-295",
                    ))

            # ReDoS: complex nested quantifiers in regex strings
            if HotspotCategory.REGEX_DOS in self.config.enabled_categories:
                # Only check lines that appear to contain re.compile or re.match etc.
                if "re.compile" in line or "re.match" in line or "re.search" in line or "re.fullmatch" in line:
                    if _RE_NESTED_QUANTIFIER.search(line):
                        hotspots.append(SecurityHotspot(
                            file_path=file_path,
                            line_number=line_num,
                            category=HotspotCategory.REGEX_DOS,
                            review_priority=ReviewPriority.LOW,
                            title="Potentially vulnerable regex pattern (ReDoS risk)",
                            description=(
                                "Regex pattern contains nested quantifiers which may cause "
                                "catastrophic backtracking on certain inputs."
                            ),
                            code_snippet=line.strip(),
                            review_guidance=(
                                "Review the regex pattern for nested quantifiers such as (a+)+ or (a*)*. "
                                "Consider using atomic groups or possessive quantifiers if available, "
                                "or rewrite to avoid ambiguity."
                            ),
                            review_status=ReviewStatus.TO_REVIEW,
                            owasp_category="A04:Insecure Design",
                            cwe_id="CWE-1333",
                        ))

            # Pickle/yaml unsafe deserialization via regex
            if HotspotCategory.INSECURE_DESERIALIZATION in self.config.enabled_categories:
                if _RE_YAML_LOAD_UNSAFE.search(line):
                    hotspots.append(SecurityHotspot(
                        file_path=file_path,
                        line_number=line_num,
                        category=HotspotCategory.INSECURE_DESERIALIZATION,
                        review_priority=ReviewPriority.HIGH,
                        title="Unsafe yaml.load() without SafeLoader",
                        description=(
                            "yaml.load() without Loader=yaml.SafeLoader can execute arbitrary "
                            "Python code embedded in YAML input."
                        ),
                        code_snippet=line.strip(),
                        review_guidance=(
                            "Replace yaml.load(data) with yaml.safe_load(data) or "
                            "yaml.load(data, Loader=yaml.SafeLoader) to prevent code execution."
                        ),
                        review_status=ReviewStatus.TO_REVIEW,
                        owasp_category="A08:Software and Data Integrity Failures",
                        cwe_id="CWE-502",
                    ))

        return hotspots

    def _get_call_name(self, node: ast.Call) -> str:
        """Extract a dotted name string from a Call node's func attribute."""
        func = node.func
        if isinstance(func, ast.Name):
            return func.id
        elif isinstance(func, ast.Attribute):
            parts = []
            current = func
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
            return ".".join(reversed(parts))
        return ""

    def _get_line(self, lines: List[str], line_number: int) -> str:
        """Safely retrieve a source line by 1-based line number."""
        if 1 <= line_number <= len(lines):
            return lines[line_number - 1].strip()
        return ""

    def _meets_min_priority(self, priority: ReviewPriority) -> bool:
        """Check whether a hotspot meets the configured minimum priority."""
        order = {
            ReviewPriority.HIGH: 3,
            ReviewPriority.MEDIUM: 2,
            ReviewPriority.LOW: 1,
        }
        min_order = order.get(self.config.min_priority, 1)
        hotspot_order = order.get(priority, 1)
        if isinstance(priority, str):
            hotspot_order = order.get(ReviewPriority(priority), 1)
        return hotspot_order >= min_order

    def _should_analyze_file(self, filename: str) -> bool:
        """Determine whether a file should be analyzed."""
        has_valid_ext = any(filename.endswith(ext) for ext in self.config.include_extensions)
        if not has_valid_ext:
            return False

        if any(self._matches_pattern(filename, p) for p in self.config.exclude_patterns):
            return False

        if not self.config.include_tests:
            if filename.startswith("test_") or filename.endswith("_test.py"):
                return False

        return True

    def _matches_pattern(self, name: str, pattern: str) -> bool:
        """Check if a name matches an exclude glob pattern."""
        return fnmatch.fnmatch(name, pattern)
