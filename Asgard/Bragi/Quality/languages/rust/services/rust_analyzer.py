"""Main Rust analyzer — entry point for Heimdall quality scanning."""

from pathlib import Path
from typing import List, Optional

from Asgard.Bragi.Quality.languages._confined_walk import (
    RUST_EXTENSIONS,
    collect_regex_findings,
    read_capped_source,
)
from Asgard.Bragi.Quality.languages.rust.models.rust_models import (
    RustFinding,
    RustReport,
    RustScanConfig,
)
from Asgard.Bragi.Quality.languages.rust.services._rust_rules import (
    check_unsafe_block,
    check_unwrap_in_production,
    check_transmute,
    check_raw_pointer_deref,
    check_command_injection,
    check_hardcoded_credentials,
    check_integer_overflow,
    check_path_traversal,
)

_RULES = [
    check_unsafe_block,
    check_unwrap_in_production,
    check_transmute,
    check_raw_pointer_deref,
    check_command_injection,
    check_hardcoded_credentials,
    check_integer_overflow,
    check_path_traversal,
]


class RustAnalyzer:
    """Analyses Rust source files for security and quality issues."""

    def __init__(self, config: Optional[RustScanConfig] = None) -> None:
        self._config = config or RustScanConfig()

    def analyze(self, scan_path: Optional[str] = None) -> RustReport:
        """Analyze all Rust files under scan_path and return a RustReport."""
        path = Path(scan_path) if scan_path else self._config.scan_path
        report = RustReport(scan_path=str(path))
        report.findings.extend(self._scan(path, self._config))
        return report

    def analyze_file(self, file_path: Path) -> List[RustFinding]:
        if file_path.suffix.lower() not in RUST_EXTENSIONS:
            return []
        source = read_capped_source(file_path, max_file_lines=self._config.max_file_lines)
        if source is None:
            return []
        findings: List[RustFinding] = []
        for rule in _RULES:
            findings.extend(rule(str(file_path), source.lines, enabled=True))
        return findings

    def analyze_directory(self, scan_path: Path, config: Optional[RustScanConfig] = None) -> List[RustFinding]:
        cfg = config or RustScanConfig(scan_path=scan_path)
        return self._scan(scan_path, cfg)

    def _scan(self, scan_path: Path, cfg: RustScanConfig) -> List[RustFinding]:
        return collect_regex_findings(
            scan_path,
            include_extensions=cfg.include_extensions,
            exclude_patterns=cfg.exclude_patterns,
            allowed_extensions=RUST_EXTENSIONS,
            max_file_lines=cfg.max_file_lines,
            max_findings=cfg.max_findings,
            rules=_RULES,
            enabled_for=lambda rule_id: cfg.rules.get(rule_id, True),
        )
