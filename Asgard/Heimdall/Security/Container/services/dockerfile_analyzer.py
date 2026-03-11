"""
Heimdall Dockerfile Analyzer Service

Service for detecting security issues in Dockerfiles.
"""

import fnmatch
import re
import time
from pathlib import Path
from typing import List, Optional

from Asgard.Heimdall.Security.Container.models.container_models import (
    ContainerConfig,
    ContainerFinding,
    ContainerFindingType,
    ContainerReport,
)
from Asgard.Heimdall.Security.Container.utilities.dockerfile_parser import (
    DockerfileInstruction,
    extract_code_snippet,
    extract_env_vars,
    extract_exposed_ports,
    find_copy_add_instructions,
    find_run_commands,
    has_healthcheck,
    has_user_instruction,
    parse_dockerfile,
    parse_stages,
)
from Asgard.Heimdall.Security.models.security_models import SecuritySeverity


class DockerfilePattern:
    """Defines a pattern for detecting Dockerfile security issues."""

    def __init__(
        self,
        name: str,
        pattern: str,
        finding_type: ContainerFindingType,
        severity: SecuritySeverity,
        title: str,
        description: str,
        cwe_id: str,
        remediation: str,
        confidence: float = 0.7,
        instruction_filter: Optional[str] = None,
    ):
        self.name = name
        self.pattern = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
        self.finding_type = finding_type
        self.severity = severity
        self.title = title
        self.description = description
        self.cwe_id = cwe_id
        self.remediation = remediation
        self.confidence = confidence
        self.instruction_filter = instruction_filter


DOCKERFILE_PATTERNS: List[DockerfilePattern] = [
    DockerfilePattern(
        name="chmod_777",
        pattern=r"chmod\s+777",
        finding_type=ContainerFindingType.CHMOD_777,
        severity=SecuritySeverity.HIGH,
        title="Chmod 777 Permission",
        description="Setting file permissions to 777 allows any user to read, write, and execute the file.",
        cwe_id="CWE-732",
        remediation="Use more restrictive permissions. For executables, use 755 or 750. For files, use 644 or 640.",
        confidence=0.95,
        instruction_filter="RUN",
    ),
    DockerfilePattern(
        name="apt_install_sudo",
        pattern=r"apt(?:-get)?\s+install\s+.*\bsudo\b",
        finding_type=ContainerFindingType.APT_INSTALL_SUDO,
        severity=SecuritySeverity.MEDIUM,
        title="Sudo Installed in Container",
        description="Installing sudo in a container can enable privilege escalation attacks.",
        cwe_id="CWE-269",
        remediation="Avoid installing sudo. Use multi-stage builds or run commands as the appropriate user directly.",
        confidence=0.85,
        instruction_filter="RUN",
    ),
    DockerfilePattern(
        name="curl_pipe_bash",
        pattern=r"curl\s+[^|]*\|\s*(?:bash|sh)",
        finding_type=ContainerFindingType.CURL_PIPE_BASH,
        severity=SecuritySeverity.HIGH,
        title="Curl Piped to Shell",
        description="Piping curl output directly to a shell is dangerous and can execute malicious code.",
        cwe_id="CWE-94",
        remediation="Download scripts first, verify their contents or checksums, then execute them.",
        confidence=0.9,
        instruction_filter="RUN",
    ),
    DockerfilePattern(
        name="wget_pipe_bash",
        pattern=r"wget\s+[^|]*\|\s*(?:bash|sh)",
        finding_type=ContainerFindingType.CURL_PIPE_BASH,
        severity=SecuritySeverity.HIGH,
        title="Wget Piped to Shell",
        description="Piping wget output directly to a shell is dangerous and can execute malicious code.",
        cwe_id="CWE-94",
        remediation="Download scripts first, verify their contents or checksums, then execute them.",
        confidence=0.9,
        instruction_filter="RUN",
    ),
]


class DockerfileAnalyzer:
    """
    Analyzes Dockerfiles for security issues.

    Detects:
    - Running as root (missing USER directive)
    - Using :latest tag
    - Secrets in ENV variables
    - Exposed sensitive ports
    - chmod 777
    - apt-get install sudo
    - curl | bash patterns
    - Missing HEALTHCHECK
    - ADD instead of COPY
    """

    def __init__(self, config: Optional[ContainerConfig] = None):
        """
        Initialize the Dockerfile analyzer.

        Args:
            config: Container security configuration. Uses defaults if not provided.
        """
        self.config = config or ContainerConfig()
        self.patterns = DOCKERFILE_PATTERNS

    def scan(self, scan_path: Optional[Path] = None) -> ContainerReport:
        """
        Scan the specified path for Dockerfile security issues.

        Args:
            scan_path: Root path to scan. Uses config path if not provided.

        Returns:
            ContainerReport containing all findings
        """
        path = scan_path or self.config.scan_path
        path = Path(path).resolve()

        if not path.exists():
            raise FileNotFoundError(f"Scan path does not exist: {path}")

        start_time = time.time()

        report = ContainerReport(scan_path=str(path))

        dockerfiles = self._find_dockerfiles(path)

        for dockerfile_path in dockerfiles:
            report.total_files_scanned += 1
            report.dockerfiles_analyzed += 1
            findings = self._analyze_dockerfile(dockerfile_path, path)

            for finding in findings:
                if self._severity_meets_threshold(finding.severity):
                    report.add_finding(finding)
                    report.dockerfile_issues += 1

        report.scan_duration_seconds = time.time() - start_time

        report.findings.sort(
            key=lambda f: (
                self._severity_order(f.severity),
                f.file_path,
                f.line_number,
            )
        )

        return report

    def _find_dockerfiles(self, root_path: Path) -> List[Path]:
        """
        Find all Dockerfiles in the given path.

        Args:
            root_path: Root directory to search

        Returns:
            List of paths to Dockerfiles
        """
        dockerfiles: List[Path] = []

        def _is_excluded(path: Path) -> bool:
            for pattern in self.config.exclude_patterns:
                if fnmatch.fnmatch(path.name, pattern):
                    return True
                if any(fnmatch.fnmatch(part, pattern) for part in path.parts):
                    return True
            return False

        def _matches_dockerfile_pattern(name: str) -> bool:
            for pattern in self.config.dockerfile_names:
                if fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(name.lower(), pattern.lower()):
                    return True
            return False

        def _scan_recursive(current_path: Path) -> None:
            try:
                for entry in current_path.iterdir():
                    if _is_excluded(entry):
                        continue

                    if entry.is_dir():
                        _scan_recursive(entry)
                    elif entry.is_file():
                        if _matches_dockerfile_pattern(entry.name):
                            dockerfiles.append(entry)
            except PermissionError:
                pass

        _scan_recursive(root_path)
        return dockerfiles

    def _analyze_dockerfile(self, file_path: Path, root_path: Path) -> List[ContainerFinding]:
        """
        Analyze a single Dockerfile for security issues.

        Args:
            file_path: Path to the Dockerfile
            root_path: Root path for relative path calculation

        Returns:
            List of container security findings
        """
        findings: List[ContainerFinding] = []

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except (IOError, OSError):
            return findings

        lines = content.split("\n")
        instructions = parse_dockerfile(content)
        stages = parse_stages(content)

        relative_path = str(file_path.relative_to(root_path))

        findings.extend(self._check_root_user(instructions, lines, relative_path))
        findings.extend(self._check_latest_tag(stages, lines, relative_path))
        findings.extend(self._check_secrets_in_env(instructions, lines, relative_path))
        findings.extend(self._check_exposed_ports(instructions, lines, relative_path))
        findings.extend(self._check_add_instead_of_copy(instructions, lines, relative_path))
        findings.extend(self._check_missing_healthcheck(instructions, lines, relative_path))
        findings.extend(self._check_run_patterns(instructions, lines, relative_path))

        return findings

    def _check_root_user(
        self,
        instructions: List[DockerfileInstruction],
        lines: List[str],
        file_path: str
    ) -> List[ContainerFinding]:
        """Check if container runs as root."""
        findings: List[ContainerFinding] = []

        if not has_user_instruction(instructions):
            last_from = None
            for instr in instructions:
                if instr.instruction == "FROM":
                    last_from = instr

            if last_from:
                findings.append(ContainerFinding(
                    file_path=file_path,
                    line_number=last_from.line_number,
                    finding_type=ContainerFindingType.ROOT_USER,
                    severity=SecuritySeverity.HIGH,
                    title="Container Running as Root",
                    description="Container runs as root user. This increases the attack surface and potential damage from container escape.",
                    code_snippet=extract_code_snippet(lines, last_from.line_number),
                    instruction="FROM",
                    cwe_id="CWE-250",
                    confidence=0.85,
                    remediation="Add a USER instruction to run the container as a non-root user.",
                    references=[
                        "https://docs.docker.com/engine/security/rootless/",
                        "https://cwe.mitre.org/data/definitions/250.html",
                    ],
                ))

        return findings

    def _check_latest_tag(
        self,
        stages: List,
        lines: List[str],
        file_path: str
    ) -> List[ContainerFinding]:
        """Check for usage of :latest tag."""
        findings: List[ContainerFinding] = []

        for stage in stages:
            if stage.tag is None or stage.tag.lower() == "latest":
                findings.append(ContainerFinding(
                    file_path=file_path,
                    line_number=stage.start_line,
                    finding_type=ContainerFindingType.LATEST_TAG,
                    severity=SecuritySeverity.MEDIUM,
                    title="Using :latest Tag",
                    description=f"Image '{stage.base_image}' uses :latest tag or no tag. This makes builds non-reproducible and may introduce unexpected changes.",
                    code_snippet=extract_code_snippet(lines, stage.start_line),
                    instruction="FROM",
                    cwe_id="CWE-829",
                    confidence=0.9,
                    remediation="Pin images to specific version tags or digest hashes for reproducible builds.",
                    references=[
                        "https://docs.docker.com/engine/reference/builder/#from",
                    ],
                ))

        return findings

    def _check_secrets_in_env(
        self,
        instructions: List[DockerfileInstruction],
        lines: List[str],
        file_path: str
    ) -> List[ContainerFinding]:
        """Check for secrets in ENV instructions."""
        findings: List[ContainerFinding] = []

        env_vars = extract_env_vars(instructions)

        for instr in instructions:
            if instr.instruction == "ENV":
                for pattern in self.config.secret_env_patterns:
                    if re.search(pattern, instr.arguments, re.IGNORECASE):
                        if "=" in instr.arguments:
                            findings.append(ContainerFinding(
                                file_path=file_path,
                                line_number=instr.line_number,
                                finding_type=ContainerFindingType.SECRETS_IN_IMAGE,
                                severity=SecuritySeverity.CRITICAL,
                                title="Secret in ENV Instruction",
                                description="Hardcoded secret found in ENV instruction. Secrets are visible in image history and layers.",
                                code_snippet=extract_code_snippet(lines, instr.line_number),
                                instruction="ENV",
                                cwe_id="CWE-798",
                                confidence=0.85,
                                remediation="Use build arguments with --build-arg, Docker secrets, or environment variables at runtime instead.",
                                references=[
                                    "https://docs.docker.com/engine/swarm/secrets/",
                                    "https://cwe.mitre.org/data/definitions/798.html",
                                ],
                            ))
                        break

        return findings

    def _check_exposed_ports(
        self,
        instructions: List[DockerfileInstruction],
        lines: List[str],
        file_path: str
    ) -> List[ContainerFinding]:
        """Check for exposed sensitive ports."""
        findings: List[ContainerFinding] = []

        if not self.config.check_ports:
            return findings

        ports = extract_exposed_ports(instructions)

        for port, line_number in ports:
            if port in self.config.sensitive_ports:
                findings.append(ContainerFinding(
                    file_path=file_path,
                    line_number=line_number,
                    finding_type=ContainerFindingType.EXPOSED_PORTS,
                    severity=SecuritySeverity.MEDIUM,
                    title=f"Sensitive Port {port} Exposed",
                    description=f"Port {port} is exposed. This port is commonly associated with sensitive services.",
                    code_snippet=extract_code_snippet(lines, line_number),
                    instruction="EXPOSE",
                    cwe_id="CWE-200",
                    confidence=0.7,
                    remediation="Consider if this port needs to be exposed. Use Docker networks for internal communication.",
                    references=[
                        "https://docs.docker.com/network/",
                    ],
                ))

        return findings

    def _check_add_instead_of_copy(
        self,
        instructions: List[DockerfileInstruction],
        lines: List[str],
        file_path: str
    ) -> List[ContainerFinding]:
        """Check for ADD used instead of COPY."""
        findings: List[ContainerFinding] = []

        for instr in instructions:
            if instr.instruction == "ADD":
                args = instr.arguments.lower()
                if not (args.startswith("http://") or args.startswith("https://") or ".tar" in args):
                    findings.append(ContainerFinding(
                        file_path=file_path,
                        line_number=instr.line_number,
                        finding_type=ContainerFindingType.ADD_INSTEAD_OF_COPY,
                        severity=SecuritySeverity.LOW,
                        title="ADD Used Instead of COPY",
                        description="ADD has extra features (URL download, tar extraction) that make it less predictable. Use COPY for simple file copies.",
                        code_snippet=extract_code_snippet(lines, instr.line_number),
                        instruction="ADD",
                        cwe_id="CWE-829",
                        confidence=0.8,
                        remediation="Use COPY instead of ADD for copying local files. ADD is only needed for URL downloads or tar extraction.",
                        references=[
                            "https://docs.docker.com/develop/develop-images/dockerfile_best-practices/#add-or-copy",
                        ],
                    ))

        return findings

    def _check_missing_healthcheck(
        self,
        instructions: List[DockerfileInstruction],
        lines: List[str],
        file_path: str
    ) -> List[ContainerFinding]:
        """Check for missing HEALTHCHECK instruction."""
        findings: List[ContainerFinding] = []

        if not has_healthcheck(instructions):
            last_line = len(lines)
            findings.append(ContainerFinding(
                file_path=file_path,
                line_number=last_line,
                finding_type=ContainerFindingType.MISSING_HEALTHCHECK,
                severity=SecuritySeverity.LOW,
                title="Missing HEALTHCHECK Instruction",
                description="No HEALTHCHECK instruction found. Health checks help Docker detect when a container is unhealthy.",
                code_snippet="",
                instruction=None,
                cwe_id="CWE-693",
                confidence=0.7,
                remediation="Add a HEALTHCHECK instruction to verify the container is functioning correctly.",
                references=[
                    "https://docs.docker.com/engine/reference/builder/#healthcheck",
                ],
            ))

        return findings

    def _check_run_patterns(
        self,
        instructions: List[DockerfileInstruction],
        lines: List[str],
        file_path: str
    ) -> List[ContainerFinding]:
        """Check RUN instructions for security patterns."""
        findings: List[ContainerFinding] = []

        run_instructions = find_run_commands(instructions)

        for instr in run_instructions:
            for pattern in self.patterns:
                if pattern.instruction_filter and pattern.instruction_filter != instr.instruction:
                    continue

                match = pattern.pattern.search(instr.arguments)
                if match:
                    findings.append(ContainerFinding(
                        file_path=file_path,
                        line_number=instr.line_number,
                        finding_type=pattern.finding_type,
                        severity=pattern.severity,
                        title=pattern.title,
                        description=pattern.description,
                        code_snippet=extract_code_snippet(lines, instr.line_number),
                        instruction="RUN",
                        cwe_id=pattern.cwe_id,
                        confidence=pattern.confidence,
                        remediation=pattern.remediation,
                        references=[
                            f"https://cwe.mitre.org/data/definitions/{pattern.cwe_id.replace('CWE-', '')}.html",
                        ],
                    ))

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
