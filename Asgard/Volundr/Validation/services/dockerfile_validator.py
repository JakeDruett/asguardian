"""
Dockerfile Validator Service

Validates Dockerfiles for best practices, security issues,
and common misconfigurations (hadolint-style).
"""

import hashlib
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from Asgard.Volundr.Validation.models.validation_models import (
    ValidationReport,
    ValidationResult,
    ValidationSeverity,
    ValidationCategory,
    ValidationContext,
    FileValidationSummary,
)


class DockerfileValidator:
    """Validates Dockerfiles for best practices."""

    # Instruction patterns
    FROM_PATTERN = re.compile(r'^FROM\s+(.+?)(?:\s+AS\s+(\w+))?$', re.IGNORECASE)
    RUN_PATTERN = re.compile(r'^RUN\s+(.+)$', re.IGNORECASE | re.DOTALL)
    COPY_PATTERN = re.compile(r'^COPY\s+(.+)$', re.IGNORECASE)
    ADD_PATTERN = re.compile(r'^ADD\s+(.+)$', re.IGNORECASE)
    ENV_PATTERN = re.compile(r'^ENV\s+(.+)$', re.IGNORECASE)
    EXPOSE_PATTERN = re.compile(r'^EXPOSE\s+(.+)$', re.IGNORECASE)
    USER_PATTERN = re.compile(r'^USER\s+(.+)$', re.IGNORECASE)
    WORKDIR_PATTERN = re.compile(r'^WORKDIR\s+(.+)$', re.IGNORECASE)
    CMD_PATTERN = re.compile(r'^CMD\s+(.+)$', re.IGNORECASE)
    ENTRYPOINT_PATTERN = re.compile(r'^ENTRYPOINT\s+(.+)$', re.IGNORECASE)
    HEALTHCHECK_PATTERN = re.compile(r'^HEALTHCHECK\s+(.+)$', re.IGNORECASE)
    LABEL_PATTERN = re.compile(r'^LABEL\s+(.+)$', re.IGNORECASE)
    ARG_PATTERN = re.compile(r'^ARG\s+(.+)$', re.IGNORECASE)

    # Common insecure base images
    INSECURE_IMAGES = {
        "python:latest",
        "node:latest",
        "ruby:latest",
        "php:latest",
        "java:latest",
        "nginx:latest",
    }

    def __init__(self, context: Optional[ValidationContext] = None):
        """
        Initialize the Dockerfile validator.

        Args:
            context: Validation context with settings
        """
        self.context = context or ValidationContext()

    def validate_file(self, file_path: str) -> ValidationReport:
        """
        Validate a Dockerfile.

        Args:
            file_path: Path to the Dockerfile

        Returns:
            ValidationReport with results
        """
        start_time = time.time()
        results: List[ValidationResult] = []

        if not os.path.exists(file_path):
            results.append(ValidationResult(
                rule_id="DL0001",
                message=f"File not found: {file_path}",
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.SYNTAX,
                file_path=file_path,
            ))
            return self._build_report([file_path], results, start_time)

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            results.append(ValidationResult(
                rule_id="DL0002",
                message=f"Error reading file: {e}",
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.SYNTAX,
                file_path=file_path,
            ))
            return self._build_report([file_path], results, start_time)

        results.extend(self._validate_content(content, file_path))
        return self._build_report([file_path], results, start_time)

    def validate_directory(self, directory: str) -> ValidationReport:
        """
        Validate all Dockerfiles in a directory.

        Args:
            directory: Directory path

        Returns:
            ValidationReport with results
        """
        start_time = time.time()
        results: List[ValidationResult] = []
        files_validated: List[str] = []

        path = Path(directory)
        if not path.exists():
            results.append(ValidationResult(
                rule_id="DL0001",
                message=f"Directory not found: {directory}",
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.SYNTAX,
            ))
            return self._build_report([], results, start_time)

        # Find Dockerfiles
        for file_path in path.rglob("Dockerfile*"):
            files_validated.append(str(file_path))
            file_results = self.validate_file(str(file_path))
            results.extend(file_results.results)

        return self._build_report(files_validated, results, start_time)

    def validate_content(self, content: str, source: str = "Dockerfile") -> ValidationReport:
        """
        Validate Dockerfile content.

        Args:
            content: Dockerfile content
            source: Source identifier

        Returns:
            ValidationReport with results
        """
        start_time = time.time()
        results = self._validate_content(content, source)
        return self._build_report([source], results, start_time)

    def _validate_content(self, content: str, file_path: str) -> List[ValidationResult]:
        """Validate Dockerfile content."""
        results: List[ValidationResult] = []
        lines = content.split("\n")

        # Track state
        has_from = False
        has_user = False
        has_healthcheck = False
        last_user = "root"
        from_count = 0
        run_commands: List[Tuple[int, str]] = []
        copy_commands: List[Tuple[int, str]] = []

        # Process each line
        line_num = 0
        current_instruction = ""

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Skip comments and empty lines
            if not stripped or stripped.startswith("#"):
                continue

            # Handle line continuation
            if stripped.endswith("\\"):
                current_instruction += stripped[:-1] + " "
                continue
            else:
                current_instruction += stripped
                instruction = current_instruction
                current_instruction = ""
                line_num = i + 1

            # Validate instruction
            results.extend(self._validate_instruction(
                instruction, file_path, line_num,
                has_from, last_user, run_commands, copy_commands
            ))

            # Update state
            if self.FROM_PATTERN.match(instruction):
                has_from = True
                from_count += 1
            elif self.USER_PATTERN.match(instruction):
                has_user = True
                match = self.USER_PATTERN.match(instruction)
                if match:
                    last_user = match.group(1).strip()
            elif self.HEALTHCHECK_PATTERN.match(instruction):
                has_healthcheck = True
            elif self.RUN_PATTERN.match(instruction):
                match = self.RUN_PATTERN.match(instruction)
                if match:
                    run_commands.append((line_num, match.group(1)))
            elif self.COPY_PATTERN.match(instruction):
                match = self.COPY_PATTERN.match(instruction)
                if match:
                    copy_commands.append((line_num, match.group(1)))

        # Global checks
        if not has_from:
            results.append(ValidationResult(
                rule_id="DL3000",
                message="Dockerfile must start with a FROM instruction",
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.SYNTAX,
                file_path=file_path,
            ))

        if not has_user and from_count > 0:
            results.append(ValidationResult(
                rule_id="DL3002",
                message="Last USER should not be root",
                severity=ValidationSeverity.WARNING,
                category=ValidationCategory.SECURITY,
                file_path=file_path,
                suggestion="Add USER instruction with non-root user",
            ))

        if last_user.lower() == "root" and has_user:
            results.append(ValidationResult(
                rule_id="DL3002",
                message="Last USER should not be root",
                severity=ValidationSeverity.WARNING,
                category=ValidationCategory.SECURITY,
                file_path=file_path,
                suggestion="Change to a non-root user before CMD/ENTRYPOINT",
            ))

        if not has_healthcheck and from_count > 0:
            results.append(ValidationResult(
                rule_id="DL3055",
                message="No HEALTHCHECK defined",
                severity=ValidationSeverity.INFO,
                category=ValidationCategory.BEST_PRACTICE,
                file_path=file_path,
                suggestion="Add HEALTHCHECK instruction for container health monitoring",
            ))

        # Check for consolidation opportunities
        results.extend(self._check_run_consolidation(run_commands, file_path))

        return results

    def _validate_instruction(
        self,
        instruction: str,
        file_path: str,
        line_num: int,
        has_from: bool,
        last_user: str,
        run_commands: List[Tuple[int, str]],
        copy_commands: List[Tuple[int, str]],
    ) -> List[ValidationResult]:
        """Validate a single Dockerfile instruction."""
        results: List[ValidationResult] = []

        # FROM instruction
        from_match = self.FROM_PATTERN.match(instruction)
        if from_match:
            image = from_match.group(1).strip()

            # Check for :latest tag
            if ":latest" in image or (":" not in image and "@" not in image):
                results.append(ValidationResult(
                    rule_id="DL3007",
                    message=f"Using latest or untagged image: {image}",
                    severity=ValidationSeverity.WARNING,
                    category=ValidationCategory.BEST_PRACTICE,
                    file_path=file_path,
                    line_number=line_num,
                    suggestion="Pin to a specific version tag",
                ))

            # Check for insecure base images
            if image.lower() in self.INSECURE_IMAGES:
                results.append(ValidationResult(
                    rule_id="DL3008",
                    message=f"Consider using a more specific or slim variant: {image}",
                    severity=ValidationSeverity.INFO,
                    category=ValidationCategory.BEST_PRACTICE,
                    file_path=file_path,
                    line_number=line_num,
                    suggestion="Use -slim or -alpine variant for smaller images",
                ))

            return results

        # Check for instructions before FROM
        if not has_from:
            if not instruction.upper().startswith("ARG"):
                results.append(ValidationResult(
                    rule_id="DL3001",
                    message="Only ARG instructions may appear before FROM",
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.SYNTAX,
                    file_path=file_path,
                    line_number=line_num,
                ))
                return results

        # RUN instruction
        run_match = self.RUN_PATTERN.match(instruction)
        if run_match:
            cmd = run_match.group(1)
            results.extend(self._validate_run_instruction(cmd, file_path, line_num))
            return results

        # COPY instruction
        copy_match = self.COPY_PATTERN.match(instruction)
        if copy_match:
            args = copy_match.group(1)
            results.extend(self._validate_copy_instruction(args, file_path, line_num))
            return results

        # ADD instruction
        add_match = self.ADD_PATTERN.match(instruction)
        if add_match:
            args = add_match.group(1)
            # ADD should generally be replaced with COPY
            if not any(x in args for x in ["http://", "https://", ".tar", ".gz", ".bz2", ".xz"]):
                results.append(ValidationResult(
                    rule_id="DL3020",
                    message="Use COPY instead of ADD for files and folders",
                    severity=ValidationSeverity.WARNING,
                    category=ValidationCategory.BEST_PRACTICE,
                    file_path=file_path,
                    line_number=line_num,
                    suggestion="Replace ADD with COPY unless you need auto-extraction",
                ))
            return results

        # EXPOSE instruction
        expose_match = self.EXPOSE_PATTERN.match(instruction)
        if expose_match:
            ports = expose_match.group(1)
            for port in ports.split():
                port_num = port.replace("/tcp", "").replace("/udp", "")
                try:
                    if int(port_num) < 1024 and last_user.lower() != "root":
                        results.append(ValidationResult(
                            rule_id="DL3011",
                            message=f"Privileged port {port_num} requires root or CAP_NET_BIND_SERVICE",
                            severity=ValidationSeverity.INFO,
                            category=ValidationCategory.SECURITY,
                            file_path=file_path,
                            line_number=line_num,
                        ))
                except ValueError:
                    pass
            return results

        # WORKDIR instruction
        workdir_match = self.WORKDIR_PATTERN.match(instruction)
        if workdir_match:
            path = workdir_match.group(1)
            if not path.startswith("/"):
                results.append(ValidationResult(
                    rule_id="DL3000",
                    message="WORKDIR should use absolute path",
                    severity=ValidationSeverity.WARNING,
                    category=ValidationCategory.BEST_PRACTICE,
                    file_path=file_path,
                    line_number=line_num,
                ))
            return results

        # CMD instruction
        cmd_match = self.CMD_PATTERN.match(instruction)
        if cmd_match:
            cmd = cmd_match.group(1)
            # Check for exec form
            if not cmd.strip().startswith("["):
                results.append(ValidationResult(
                    rule_id="DL3025",
                    message="Use JSON notation for CMD",
                    severity=ValidationSeverity.INFO,
                    category=ValidationCategory.BEST_PRACTICE,
                    file_path=file_path,
                    line_number=line_num,
                    suggestion='Use CMD ["executable", "param1", "param2"]',
                ))
            return results

        return results

    def _validate_run_instruction(
        self, cmd: str, file_path: str, line_num: int
    ) -> List[ValidationResult]:
        """Validate a RUN instruction."""
        results: List[ValidationResult] = []
        cmd_lower = cmd.lower()

        # Check for apt-get without -y
        if "apt-get install" in cmd_lower and " -y" not in cmd_lower and "-y " not in cmd_lower:
            results.append(ValidationResult(
                rule_id="DL3014",
                message="Use apt-get with -y flag",
                severity=ValidationSeverity.WARNING,
                category=ValidationCategory.BEST_PRACTICE,
                file_path=file_path,
                line_number=line_num,
            ))

        # Check for apt-get without rm lists
        if "apt-get" in cmd_lower and "rm -rf /var/lib/apt/lists" not in cmd_lower:
            if "apt-get update" in cmd_lower or "apt-get install" in cmd_lower:
                results.append(ValidationResult(
                    rule_id="DL3009",
                    message="Delete apt-get lists after installing packages",
                    severity=ValidationSeverity.INFO,
                    category=ValidationCategory.BEST_PRACTICE,
                    file_path=file_path,
                    line_number=line_num,
                    suggestion="Add && rm -rf /var/lib/apt/lists/*",
                ))

        # Check for pip install without --no-cache-dir
        if "pip install" in cmd_lower and "--no-cache-dir" not in cmd_lower:
            results.append(ValidationResult(
                rule_id="DL3042",
                message="Avoid cache when installing packages",
                severity=ValidationSeverity.INFO,
                category=ValidationCategory.BEST_PRACTICE,
                file_path=file_path,
                line_number=line_num,
                suggestion="Add --no-cache-dir to pip install",
            ))

        # Check for curl without fail flag
        if "curl " in cmd_lower and " -f" not in cmd_lower and "--fail" not in cmd_lower:
            results.append(ValidationResult(
                rule_id="DL4001",
                message="Use curl with -f flag to fail on HTTP errors",
                severity=ValidationSeverity.WARNING,
                category=ValidationCategory.RELIABILITY,
                file_path=file_path,
                line_number=line_num,
                suggestion="Add -f or --fail to curl command",
            ))

        # Check for wget without output file
        if "wget " in cmd_lower and " -O " not in cmd_lower and " --output-document" not in cmd_lower:
            results.append(ValidationResult(
                rule_id="DL4002",
                message="Consider using wget with -O to specify output file",
                severity=ValidationSeverity.INFO,
                category=ValidationCategory.BEST_PRACTICE,
                file_path=file_path,
                line_number=line_num,
            ))

        # Check for sudo usage
        if "sudo " in cmd_lower:
            results.append(ValidationResult(
                rule_id="DL3004",
                message="Do not use sudo as it leads to unpredictable behavior",
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.SECURITY,
                file_path=file_path,
                line_number=line_num,
                suggestion="Use USER instruction to switch users instead",
            ))

        # Check for yum without clean
        if "yum install" in cmd_lower and "yum clean" not in cmd_lower:
            results.append(ValidationResult(
                rule_id="DL3032",
                message="yum clean all missing after yum install",
                severity=ValidationSeverity.INFO,
                category=ValidationCategory.BEST_PRACTICE,
                file_path=file_path,
                line_number=line_num,
            ))

        # Check for npm install without ci for production
        if "npm install" in cmd_lower and "npm ci" not in cmd_lower:
            results.append(ValidationResult(
                rule_id="DL3016",
                message="Consider using npm ci instead of npm install for reproducible builds",
                severity=ValidationSeverity.INFO,
                category=ValidationCategory.BEST_PRACTICE,
                file_path=file_path,
                line_number=line_num,
            ))

        return results

    def _validate_copy_instruction(
        self, args: str, file_path: str, line_num: int
    ) -> List[ValidationResult]:
        """Validate a COPY instruction."""
        results: List[ValidationResult] = []

        # Check for copying everything
        if ". ." in args or "./ ./" in args or ". /" in args:
            results.append(ValidationResult(
                rule_id="DL3045",
                message="Copying entire context may include unnecessary files",
                severity=ValidationSeverity.INFO,
                category=ValidationCategory.BEST_PRACTICE,
                file_path=file_path,
                line_number=line_num,
                suggestion="Use .dockerignore and copy specific files/directories",
            ))

        # Check for --chown usage (good practice)
        if "--chown" not in args:
            results.append(ValidationResult(
                rule_id="DL3046",
                message="Consider using --chown to set file ownership",
                severity=ValidationSeverity.HINT,
                category=ValidationCategory.BEST_PRACTICE,
                file_path=file_path,
                line_number=line_num,
            ))

        return results

    def _check_run_consolidation(
        self, run_commands: List[Tuple[int, str]], file_path: str
    ) -> List[ValidationResult]:
        """Check if RUN commands can be consolidated."""
        results: List[ValidationResult] = []

        # If more than 5 separate RUN commands, suggest consolidation
        if len(run_commands) > 5:
            results.append(ValidationResult(
                rule_id="DL3059",
                message=f"Multiple RUN instructions ({len(run_commands)}) could be consolidated",
                severity=ValidationSeverity.INFO,
                category=ValidationCategory.BEST_PRACTICE,
                file_path=file_path,
                suggestion="Combine related RUN commands with && to reduce layers",
            ))

        return results

    def _build_report(
        self,
        files: List[str],
        results: List[ValidationResult],
        start_time: float,
    ) -> ValidationReport:
        """Build validation report."""
        duration_ms = int((time.time() - start_time) * 1000)

        error_count = sum(1 for r in results if r.severity == ValidationSeverity.ERROR)
        warning_count = sum(1 for r in results if r.severity == ValidationSeverity.WARNING)
        info_count = sum(1 for r in results if r.severity in (ValidationSeverity.INFO, ValidationSeverity.HINT))

        score = 100.0
        score -= error_count * 10
        score -= warning_count * 3
        score -= info_count * 1
        score = max(0.0, score)

        file_summaries = []
        results_by_file: Dict[str, List[ValidationResult]] = {}
        for result in results:
            fp = result.file_path or "(no file)"
            if fp not in results_by_file:
                results_by_file[fp] = []
            results_by_file[fp].append(result)

        for fp in files:
            file_results = results_by_file.get(fp, [])
            file_errors = sum(1 for r in file_results if r.severity == ValidationSeverity.ERROR)
            file_warnings = sum(1 for r in file_results if r.severity == ValidationSeverity.WARNING)
            file_info = sum(1 for r in file_results if r.severity in (ValidationSeverity.INFO, ValidationSeverity.HINT))
            file_summaries.append(FileValidationSummary(
                file_path=fp,
                error_count=file_errors,
                warning_count=file_warnings,
                info_count=file_info,
                passed=file_errors == 0,
            ))

        report_id = hashlib.sha256(str(results).encode()).hexdigest()[:16]

        return ValidationReport(
            id=f"dockerfile-validation-{report_id}",
            title="Dockerfile Validation",
            validator="DockerfileValidator",
            results=results,
            file_summaries=file_summaries,
            total_files=len(files),
            total_errors=error_count,
            total_warnings=warning_count,
            total_info=info_count,
            passed=error_count == 0,
            score=score,
            duration_ms=duration_ms,
            context=self.context,
        )
