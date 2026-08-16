"""Heimdall Config Secrets Scanner -- detects hardcoded secrets in config files (YAML, JSON, TOML, INI)."""

import configparser
import fnmatch
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import tomllib

import yaml  # type: ignore[import-untyped]

from Asgard.Heimdall.Security.models.config_secrets_models import (
    ConfigSecretFinding,
    ConfigSecretSeverity,
    ConfigSecretType,
    ConfigSecretsConfig,
    ConfigSecretsReport,
)
from Asgard.Heimdall.Security.services._config_secrets_helpers import (
    flatten_dict,
    is_credential_key,
    is_placeholder,
    mask_value,
    shannon_entropy,
)
from Asgard.Heimdall.Security.services._config_secrets_report import (
    generate_json_report,
    generate_markdown_report,
    generate_text_report,
)
from Asgard.Heimdall.Security.utilities._scan_utils import (
    is_confined_scan_path,
    iter_confined_files,
)


class ConfigSecretsScanner:
    """Scans configuration files for hardcoded secrets and credentials."""

    def __init__(self, config: Optional[ConfigSecretsConfig] = None):
        self.config = config or ConfigSecretsConfig()

    def analyze(self, path: Path) -> ConfigSecretsReport:
        """Analyze a file or directory for hardcoded secrets."""
        if not path.exists():
            raise FileNotFoundError(f"Path does not exist: {path}")
        start_time = datetime.now()
        report = ConfigSecretsReport(scan_path=str(path))
        if path.is_file():
            if is_confined_scan_path(path, path.parent):
                for finding in self._analyze_file(path, path.parent):
                    report.add_finding(finding)
                report.files_scanned = 1
        else:
            self._analyze_directory(path, report)
        report.scan_duration_seconds = (datetime.now() - start_time).total_seconds()
        file_finding_counts: Dict[str, int] = defaultdict(int)
        for finding in report.detected_findings:
            file_finding_counts[finding.file_path] += 1
        report.most_problematic_files = sorted(
            file_finding_counts.items(), key=lambda x: x[1], reverse=True,
        )[:10]
        return report

    def _analyze_file(self, file_path: Path, root_path: Path) -> List[ConfigSecretFinding]:
        """Analyze a single config file for hardcoded secrets."""
        suffix = file_path.suffix.lower()
        try:
            if suffix in (".yaml", ".yml"):
                findings = self._analyze_yaml(file_path)
            elif suffix == ".json":
                findings = self._analyze_json(file_path)
            elif suffix == ".toml":
                findings = self._analyze_toml(file_path)
            elif suffix in (".ini", ".cfg", ".conf"):
                findings = self._analyze_ini(file_path)
            else:
                return []
            for finding in findings:
                try:
                    finding.relative_path = str(file_path.relative_to(root_path))
                except ValueError:
                    finding.relative_path = file_path.name
            return [
                f for f in findings
                if self._severity_level(f.severity) >= self._severity_level(self.config.severity_filter)
            ]
        except Exception:
            return []

    def _check_value(self, file_path: Path, key: str, value: Any, context_path: str) -> List[ConfigSecretFinding]:
        """Check a key/value pair for potential secrets."""
        findings: List[ConfigSecretFinding] = []
        if not isinstance(value, str):
            return findings
        str_value = value.strip()
        if not str_value or is_placeholder(str_value):
            return findings
        file_path_str = str(file_path.absolute())
        if is_credential_key(key, self.config.credential_key_names):
            masked = mask_value(str_value)
            findings.append(ConfigSecretFinding(
                file_path=file_path_str, key_name=key, masked_value=masked,
                secret_type=ConfigSecretType.CREDENTIAL_KEY,
                severity=ConfigSecretSeverity.CRITICAL, context_path=context_path,
                context_description=f"Key '{key}' at path '{context_path}' has a credential-like name with a non-placeholder value: {masked}",
            ))
            return findings
        if len(str_value) >= self.config.entropy_min_length:
            entropy = shannon_entropy(str_value)
            if entropy > self.config.entropy_threshold:
                masked = mask_value(str_value)
                findings.append(ConfigSecretFinding(
                    file_path=file_path_str, key_name=key, masked_value=masked,
                    secret_type=ConfigSecretType.HIGH_ENTROPY_STRING,
                    severity=ConfigSecretSeverity.MEDIUM, entropy=round(entropy, 2),
                    context_path=context_path,
                    context_description=f"Key '{key}' at path '{context_path}' contains a high-entropy string (entropy={entropy:.2f}) that may be a secret: {masked}",
                ))
        return findings

    def _analyze_yaml(self, file_path: Path) -> List[ConfigSecretFinding]:
        try:
            data = yaml.safe_load(file_path.read_text(encoding="utf-8"))
            if data is None:
                return []
            return self._scan_data(file_path, data)
        except Exception:
            return []

    def _analyze_json(self, file_path: Path) -> List[ConfigSecretFinding]:
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
            return self._scan_data(file_path, data)
        except Exception:
            return []

    def _analyze_toml(self, file_path: Path) -> List[ConfigSecretFinding]:
        try:
            data = tomllib.loads(file_path.read_bytes().decode("utf-8"))
            return self._scan_data(file_path, data)
        except Exception:
            return []

    def _analyze_ini(self, file_path: Path) -> List[ConfigSecretFinding]:
        findings = []
        try:
            parser = configparser.ConfigParser()
            parser.read(str(file_path), encoding="utf-8")
            for section in parser.sections():
                for key, value in parser.items(section):
                    findings.extend(self._check_value(file_path, key, value, f"{section}.{key}"))
            for key, value in parser.defaults().items():
                findings.extend(self._check_value(file_path, key, value, f"DEFAULT.{key}"))
        except Exception:
            pass
        return findings

    def _scan_data(self, file_path: Path, data: Any) -> List[ConfigSecretFinding]:
        findings = []
        for context_path, key, value in flatten_dict(data):
            findings.extend(self._check_value(file_path, key, value, context_path))
        return findings

    def _analyze_directory(self, directory: Path, report: ConfigSecretsReport) -> None:
        files_scanned = 0

        def _skip(path: Path) -> bool:
            return any(
                self._matches_pattern(path.name, p) for p in self.config.exclude_patterns
            )

        for file_path in iter_confined_files(directory, should_skip=_skip):
            if not self._should_analyze_file(file_path.name):
                continue
            for finding in self._analyze_file(file_path, directory):
                report.add_finding(finding)
            files_scanned += 1
        report.files_scanned = files_scanned

    def _should_analyze_file(self, filename: str) -> bool:
        return any(filename.endswith(ext) for ext in self.config.include_extensions)

    def _matches_pattern(self, name: str, pattern: str) -> bool:
        return fnmatch.fnmatch(name, pattern)

    def _severity_level(self, severity) -> int:
        if isinstance(severity, str):
            severity = ConfigSecretSeverity(severity)
        levels = {
            ConfigSecretSeverity.LOW: 1, ConfigSecretSeverity.MEDIUM: 2,
            ConfigSecretSeverity.HIGH: 3, ConfigSecretSeverity.CRITICAL: 4,
        }
        return levels.get(severity, 1)

    def generate_report(self, report: ConfigSecretsReport, output_format: str = "text") -> str:
        """Generate formatted config secrets report."""
        format_lower = output_format.lower()
        if format_lower == "json":
            return generate_json_report(report)
        elif format_lower in ("markdown", "md"):
            return generate_markdown_report(report)
        elif format_lower == "text":
            return generate_text_report(report)
        raise ValueError(f"Unsupported format: {output_format}. Use: text, json, markdown")
