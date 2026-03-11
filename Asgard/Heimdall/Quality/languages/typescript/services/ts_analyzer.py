"""
Heimdall TypeScript Analyzer

Extends the JavaScript analyzer with TypeScript-specific rules.
Scans .ts and .tsx files, applying all JS rules (adapted for TypeScript)
plus additional TypeScript-specific rules such as no-explicit-any,
strict-null-checks, prefer-interface, and no-any-cast.
"""

import re
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from Asgard.Heimdall.Quality.languages.javascript.models.js_models import (
    JSFinding,
    JSReport,
    JSRuleCategory,
    JSSeverity,
)
from Asgard.Heimdall.Quality.languages.javascript.services.js_analyzer import (
    JSAnalyzer,
    _make_finding,
)
from Asgard.Heimdall.Quality.languages.typescript.models.ts_models import TSAnalysisConfig


_DEFAULT_TS_EXTENSIONS = [".ts", ".tsx"]


class TSAnalyzer(JSAnalyzer):
    """
    Regex-based static analyzer for TypeScript and TSX files.

    Inherits all JavaScript rules and adds TypeScript-specific rules:
    - ts.no-explicit-any
    - ts.no-implicit-any
    - ts.strict-null-checks
    - ts.prefer-interface
    - ts.no-any-cast
    - ts.explicit-return-type

    Usage:
        config = TSAnalysisConfig(scan_path=Path("./src"))
        analyzer = TSAnalyzer(config)
        report = analyzer.analyze(Path("./src"))
    """

    def __init__(self, config: Optional[TSAnalysisConfig] = None):
        """
        Initialise the TypeScript analyzer.

        Args:
            config: TypeScript analysis configuration. Defaults to TSAnalysisConfig().
        """
        super().__init__(config or TSAnalysisConfig())

    def analyze(self, scan_path: Optional[Path] = None) -> JSReport:
        """
        Scan a directory tree for TypeScript files and apply all enabled rules.

        Args:
            scan_path: Root path to scan. Falls back to config.scan_path.

        Returns:
            JSReport containing all findings, with language set to 'typescript'.
        """
        root = Path(scan_path) if scan_path else self._config.scan_path
        root = root.resolve()

        start_time = time.monotonic()
        report = JSReport(
            scan_path=str(root),
            language="typescript",
            scanned_at=datetime.now(),
        )

        extensions = self._config.include_extensions or _DEFAULT_TS_EXTENSIONS
        files = self._collect_files(root, extensions)

        for file_path in files:
            findings = self._analyze_ts_file(file_path)
            for finding in findings:
                report.add_finding(finding)

        report.files_analyzed = len(files)
        report.scan_duration_seconds = time.monotonic() - start_time
        return report

    def _analyze_ts_file(self, file_path: Path) -> List[JSFinding]:
        """Run all JS rules plus TypeScript-specific rules against a single file."""
        # Run base JS analysis first
        findings = self._analyze_file(file_path)

        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return findings

        lines = content.splitlines()
        path_str = str(file_path)

        findings.extend(self._rule_ts_no_explicit_any(path_str, lines))
        findings.extend(self._rule_ts_no_implicit_any(path_str, lines))
        findings.extend(self._rule_ts_strict_null_checks(path_str, lines))
        findings.extend(self._rule_ts_prefer_interface(path_str, lines))
        findings.extend(self._rule_ts_no_any_cast(path_str, lines))
        findings.extend(self._rule_ts_explicit_return_type(path_str, lines))

        return findings

    # --- TypeScript-specific Rules ---

    def _rule_ts_no_explicit_any(self, file_path: str, lines: List[str]) -> List[JSFinding]:
        """ts.no-explicit-any: Use of : any type annotation."""
        if not self._config.is_rule_enabled("ts.no-explicit-any"):
            return []
        findings = []
        pattern = re.compile(r':\s*any\b')
        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("*"):
                continue
            if pattern.search(line):
                findings.append(_make_finding(
                    file_path=file_path,
                    line_number=i,
                    rule_id="ts.no-explicit-any",
                    category=JSRuleCategory.CODE_SMELL,
                    severity=JSSeverity.WARNING,
                    title="Explicit any type",
                    description=(
                        "Using 'any' defeats the purpose of TypeScript's type system. "
                        "Prefer a more specific type."
                    ),
                    code_snippet=line,
                    fix_suggestion="Replace 'any' with a more specific type or use 'unknown' for truly unknown types.",
                ))
        return findings

    def _rule_ts_no_implicit_any(self, file_path: str, lines: List[str]) -> List[JSFinding]:
        """ts.no-implicit-any: Function parameters without type annotations."""
        if not self._config.is_rule_enabled("ts.no-implicit-any"):
            return []
        findings = []
        # Match function parameters: look for identifiers in parameter list without a colon-type
        # Pattern: function foo(param, other) - params without ': type'
        func_pattern = re.compile(r'\bfunction\s+\w+\s*\(([^)]+)\)')
        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("*"):
                continue
            match = func_pattern.search(line)
            if match:
                params_str = match.group(1)
                # Split params and check each for type annotation
                params = [p.strip() for p in params_str.split(",") if p.strip()]
                for param in params:
                    # Remove default values and destructuring complexity
                    param_name = param.split("=")[0].strip()
                    # If no colon, it lacks a type annotation
                    if ":" not in param_name and param_name and not param_name.startswith("{") and not param_name.startswith("["):
                        findings.append(_make_finding(
                            file_path=file_path,
                            line_number=i,
                            rule_id="ts.no-implicit-any",
                            category=JSRuleCategory.CODE_SMELL,
                            severity=JSSeverity.INFO,
                            title="Parameter missing type annotation",
                            description=(
                                f"Parameter '{param_name}' has no type annotation and will be implicitly typed as any."
                            ),
                            code_snippet=line,
                            fix_suggestion=f"Add a type annotation: '{param_name}: <type>'.",
                        ))
                        break  # Report once per function line
        return findings

    def _rule_ts_strict_null_checks(self, file_path: str, lines: List[str]) -> List[JSFinding]:
        """ts.strict-null-checks: Using ! non-null assertion operator."""
        if not self._config.is_rule_enabled("ts.strict-null-checks"):
            return []
        findings = []
        # Match identifier! followed by . or other access
        pattern = re.compile(r'[a-zA-Z_$][a-zA-Z0-9_$]*!\s*\.')
        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("*"):
                continue
            if pattern.search(line):
                findings.append(_make_finding(
                    file_path=file_path,
                    line_number=i,
                    rule_id="ts.strict-null-checks",
                    category=JSRuleCategory.BUG,
                    severity=JSSeverity.WARNING,
                    title="Non-null assertion operator",
                    description=(
                        "Using the non-null assertion operator (!) suppresses null checks "
                        "and can cause runtime errors if the value is null or undefined."
                    ),
                    code_snippet=line,
                    fix_suggestion="Add a proper null check instead of using the non-null assertion operator.",
                ))
        return findings

    def _rule_ts_prefer_interface(self, file_path: str, lines: List[str]) -> List[JSFinding]:
        """ts.prefer-interface: Use of type X = { } instead of interface X { }."""
        if not self._config.is_rule_enabled("ts.prefer-interface"):
            return []
        findings = []
        pattern = re.compile(r'\btype\s+\w+\s*=\s*\{')
        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("*"):
                continue
            if pattern.search(line):
                findings.append(_make_finding(
                    file_path=file_path,
                    line_number=i,
                    rule_id="ts.prefer-interface",
                    category=JSRuleCategory.CODE_SMELL,
                    severity=JSSeverity.INFO,
                    title="Prefer interface over type alias for object types",
                    description=(
                        "Object type aliases (type X = {}) are less extendable than interfaces. "
                        "Prefer interface X {} for object shapes."
                    ),
                    code_snippet=line,
                    fix_suggestion="Convert 'type X = { ... }' to 'interface X { ... }'.",
                ))
        return findings

    def _rule_ts_no_any_cast(self, file_path: str, lines: List[str]) -> List[JSFinding]:
        """ts.no-any-cast: Casting to any using 'as any'."""
        if not self._config.is_rule_enabled("ts.no-any-cast"):
            return []
        findings = []
        pattern = re.compile(r'\bas\s+any\b')
        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("*"):
                continue
            if pattern.search(line):
                findings.append(_make_finding(
                    file_path=file_path,
                    line_number=i,
                    rule_id="ts.no-any-cast",
                    category=JSRuleCategory.CODE_SMELL,
                    severity=JSSeverity.WARNING,
                    title="Cast to any",
                    description=(
                        "Casting a value to 'any' bypasses TypeScript's type safety. "
                        "Use a more specific type assertion."
                    ),
                    code_snippet=line,
                    fix_suggestion="Replace 'as any' with a proper type assertion or restructure the code.",
                ))
        return findings

    def _rule_ts_explicit_return_type(self, file_path: str, lines: List[str]) -> List[JSFinding]:
        """ts.explicit-return-type: Exported functions without explicit return type annotation."""
        if not self._config.is_rule_enabled("ts.explicit-return-type"):
            return []
        findings = []
        # Match exported function declarations: export function foo(...) without ): ReturnType
        # Pattern: export function name(params) { - no colon before brace
        exported_func_pattern = re.compile(r'\bexport\s+(?:default\s+)?(?:async\s+)?function\s+\w*\s*\([^)]*\)\s*\{')
        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("*"):
                continue
            if exported_func_pattern.search(line):
                # Check if there is a return type annotation: ): type before {
                has_return_type = re.search(r'\)\s*:\s*\w', line)
                if not has_return_type:
                    findings.append(_make_finding(
                        file_path=file_path,
                        line_number=i,
                        rule_id="ts.explicit-return-type",
                        category=JSRuleCategory.CODE_SMELL,
                        severity=JSSeverity.WARNING,
                        title="Missing explicit return type on exported function",
                        description=(
                            "Exported functions should have an explicit return type annotation "
                            "to serve as a clear contract for callers."
                        ),
                        code_snippet=line,
                        fix_suggestion="Add a return type annotation: 'function name(params): ReturnType { ... }'.",
                    ))
        return findings
