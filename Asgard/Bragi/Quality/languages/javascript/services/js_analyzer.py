"""
Heimdall JavaScript Analyzer

Performs regex-based static analysis on JavaScript and JSX source files.
Because Python's ast module cannot parse JS/TS, all rules are implemented
using line-by-line regular expression matching.
"""

from datetime import datetime
from pathlib import Path
from typing import List, Optional

from Asgard.Bragi.Quality.languages._confined_walk import (
    JS_EXTENSIONS,
    TS_EXTENSIONS,
    iter_language_files,
    matches_exclude,
    read_capped_source,
)
from Asgard.Bragi.Quality.languages.javascript.models.js_models import (
    JSAnalysisConfig,
    JSFinding,
    JSReport,
)
from Asgard.Bragi.Quality.languages.javascript.services._js_rules import (
    check_eqeqeq,
    check_no_alert,
    check_no_debugger,
    check_no_eval,
    check_no_implied_eval,
)
from Asgard.Bragi.Quality.languages.javascript.services._js_security_rules import (
    _SECURITY_RULES,
)
from Asgard.Bragi.Quality.languages.javascript.services._js_style_rules import (
    check_complexity,
    check_max_file_lines,
    check_max_line_length,
    check_no_console,
    check_no_empty_block,
    check_no_trailing_spaces,
    check_no_var,
)


class JSAnalyzer:
    """
    Regex-based static analyzer for JavaScript and JSX files.

    Each public rule method returns a list of JSFinding objects for a single
    file.  The top-level analyze() method discovers files, runs all enabled
    rules, and returns an aggregated JSReport.
    """

    def __init__(self, config: Optional[JSAnalysisConfig] = None) -> None:
        self._config = config or JSAnalysisConfig()

    def analyze(self, scan_path: Optional[str] = None) -> JSReport:
        """
        Analyze all matching source files under scan_path.

        Args:
            scan_path: Optional override for the config scan path.

        Returns:
            JSReport containing all findings.
        """
        start = datetime.now()
        root = Path(scan_path).resolve() if scan_path else self._config.scan_path.resolve()
        report = JSReport(scan_path=str(root), language=self._config.language)

        files = self._discover_files(root)
        report.files_analyzed = len(files)
        max_findings = self._config.max_findings

        for file_path in files:
            if max_findings is not None and report.total_findings >= max_findings:
                break
            source = read_capped_source(
                Path(file_path),
                max_file_lines=self._config.max_file_lines,
            )
            if source is None:
                continue

            for finding in self._analyze_file(
                str(file_path),
                source.lines,
                source.exceeded_line_limit,
            ):
                if max_findings is not None and report.total_findings >= max_findings:
                    break
                report.add_finding(finding)

        report.scan_duration_seconds = (datetime.now() - start).total_seconds()
        return report

    def _discover_files(self, root: Path) -> List[Path]:
        """Return confined files matching the configured extensions."""
        return sorted(
            iter_language_files(
                root,
                include_extensions=self._config.include_extensions,
                exclude_patterns=self._config.exclude_patterns,
                allowed_extensions=JS_EXTENSIONS | TS_EXTENSIONS,
            )
        )

    def _is_excluded(self, path: Path) -> bool:
        """Return True if the path matches any exclusion pattern."""
        return matches_exclude(path, self._config.exclude_patterns)

    def _is_rule_enabled(self, rule_id: str) -> bool:
        """Return True when the rule should be executed."""
        if rule_id in self._config.disabled_rules:
            return False
        if self._config.enabled_rules is not None:
            return rule_id in self._config.enabled_rules
        return True

    def _analyze_file(
        self,
        file_path: str,
        lines: List[str],
        exceeded_line_limit: bool = False,
    ) -> List[JSFinding]:
        """Run all enabled rules against a single file's source lines."""
        findings: List[JSFinding] = []
        findings.extend(check_no_eval(file_path, lines, self._is_rule_enabled("js.no-eval")))
        findings.extend(check_no_implied_eval(file_path, lines, self._is_rule_enabled("js.no-implied-eval")))
        findings.extend(check_no_debugger(file_path, lines, self._is_rule_enabled("js.no-debugger")))
        findings.extend(check_eqeqeq(file_path, lines, self._is_rule_enabled("js.eqeqeq")))
        findings.extend(check_no_alert(file_path, lines, self._is_rule_enabled("js.no-alert")))
        findings.extend(check_no_var(file_path, lines, self._is_rule_enabled("js.no-var")))
        findings.extend(check_no_empty_block(file_path, lines, self._is_rule_enabled("js.no-empty-block")))
        findings.extend(check_no_console(file_path, lines, self._is_rule_enabled("js.no-console")))
        style_lines = list(lines)
        if exceeded_line_limit:
            style_lines.append("")
        findings.extend(check_max_file_lines(
            file_path,
            style_lines,
            self._is_rule_enabled("js.max-file-lines"),
            self._config.max_file_lines,
        ))
        findings.extend(check_complexity(file_path, lines, self._is_rule_enabled("js.complexity"), self._config.max_complexity))
        findings.extend(check_no_trailing_spaces(file_path, lines, self._is_rule_enabled("js.no-trailing-spaces")))
        findings.extend(check_max_line_length(file_path, lines, self._is_rule_enabled("js.max-line-length")))
        for rule_fn in _SECURITY_RULES:
            rule_id = rule_fn.__doc__.split(":")[0].strip() if rule_fn.__doc__ else ""
            findings.extend(rule_fn(file_path, lines, self._is_rule_enabled(rule_id)))
        return findings
