"""
Terraform Configuration Validator Service

Validates Terraform configurations for best practices,
security issues, and common misconfigurations.
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


class TerraformValidator:
    """Validates Terraform configurations."""

    # HCL block patterns
    RESOURCE_PATTERN = re.compile(r'resource\s+"([^"]+)"\s+"([^"]+)"\s*{', re.MULTILINE)
    DATA_PATTERN = re.compile(r'data\s+"([^"]+)"\s+"([^"]+)"\s*{', re.MULTILINE)
    VARIABLE_PATTERN = re.compile(r'variable\s+"([^"]+)"\s*{', re.MULTILINE)
    OUTPUT_PATTERN = re.compile(r'output\s+"([^"]+)"\s*{', re.MULTILINE)
    MODULE_PATTERN = re.compile(r'module\s+"([^"]+)"\s*{', re.MULTILINE)
    PROVIDER_PATTERN = re.compile(r'provider\s+"([^"]+)"\s*{', re.MULTILINE)
    TERRAFORM_PATTERN = re.compile(r'terraform\s*{', re.MULTILINE)

    # Sensitive variable patterns
    SENSITIVE_PATTERNS = [
        "password", "secret", "key", "token", "api_key", "apikey",
        "auth", "credential", "private", "cert", "ssh",
    ]

    def __init__(self, context: Optional[ValidationContext] = None):
        """
        Initialize the Terraform validator.

        Args:
            context: Validation context with settings
        """
        self.context = context or ValidationContext()

    def validate_file(self, file_path: str) -> ValidationReport:
        """
        Validate a Terraform configuration file.

        Args:
            file_path: Path to the .tf file

        Returns:
            ValidationReport with results
        """
        start_time = time.time()
        results: List[ValidationResult] = []

        if not os.path.exists(file_path):
            results.append(ValidationResult(
                rule_id="file-not-found",
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
                rule_id="file-read-error",
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
        Validate all Terraform files in a directory.

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
                rule_id="directory-not-found",
                message=f"Directory not found: {directory}",
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.SYNTAX,
            ))
            return self._build_report([], results, start_time)

        # Find all .tf files
        for file_path in path.rglob("*.tf"):
            files_validated.append(str(file_path))
            file_results = self.validate_file(str(file_path))
            results.extend(file_results.results)

        # Module-level validation
        results.extend(self._validate_module_structure(directory, files_validated))

        return self._build_report(files_validated, results, start_time)

    def _validate_content(self, content: str, file_path: str) -> List[ValidationResult]:
        """Validate Terraform file content."""
        results: List[ValidationResult] = []
        lines = content.split("\n")

        # Check for terraform block in main files
        if "main.tf" in file_path or file_path.endswith("/main.tf"):
            if not self.TERRAFORM_PATTERN.search(content):
                results.append(ValidationResult(
                    rule_id="missing-terraform-block",
                    message="main.tf should contain a terraform {} block",
                    severity=ValidationSeverity.WARNING,
                    category=ValidationCategory.BEST_PRACTICE,
                    file_path=file_path,
                ))

        # Validate resources
        for match in self.RESOURCE_PATTERN.finditer(content):
            resource_type = match.group(1)
            resource_name = match.group(2)
            line_num = content[:match.start()].count("\n") + 1
            results.extend(self._validate_resource(
                content, resource_type, resource_name, file_path, line_num
            ))

        # Validate variables
        for match in self.VARIABLE_PATTERN.finditer(content):
            var_name = match.group(1)
            line_num = content[:match.start()].count("\n") + 1
            results.extend(self._validate_variable(
                content, var_name, file_path, line_num, match.start()
            ))

        # Validate outputs
        for match in self.OUTPUT_PATTERN.finditer(content):
            output_name = match.group(1)
            line_num = content[:match.start()].count("\n") + 1
            results.extend(self._validate_output(
                content, output_name, file_path, line_num, match.start()
            ))

        # Validate modules
        for match in self.MODULE_PATTERN.finditer(content):
            module_name = match.group(1)
            line_num = content[:match.start()].count("\n") + 1
            results.extend(self._validate_module_call(
                content, module_name, file_path, line_num, match.start()
            ))

        # Check for hardcoded credentials
        results.extend(self._check_hardcoded_credentials(content, file_path, lines))

        # Check for deprecated syntax
        results.extend(self._check_deprecated_syntax(content, file_path, lines))

        return results

    def _validate_resource(
        self,
        content: str,
        resource_type: str,
        resource_name: str,
        file_path: str,
        line_num: int,
    ) -> List[ValidationResult]:
        """Validate a resource block."""
        results: List[ValidationResult] = []

        # Check naming convention
        if not re.match(r'^[a-z][a-z0-9_]*$', resource_name):
            results.append(ValidationResult(
                rule_id="resource-naming",
                message=f"Resource name '{resource_name}' should use snake_case",
                severity=ValidationSeverity.WARNING,
                category=ValidationCategory.BEST_PRACTICE,
                file_path=file_path,
                line_number=line_num,
                resource_name=resource_name,
            ))

        # Check for common security issues by resource type
        if resource_type == "aws_security_group":
            results.extend(self._validate_aws_security_group(
                content, resource_name, file_path, line_num
            ))
        elif resource_type == "aws_s3_bucket":
            results.extend(self._validate_aws_s3_bucket(
                content, resource_name, file_path, line_num
            ))
        elif resource_type == "aws_iam_policy":
            results.extend(self._validate_aws_iam_policy(
                content, resource_name, file_path, line_num
            ))

        return results

    def _validate_aws_security_group(
        self, content: str, name: str, file_path: str, line_num: int
    ) -> List[ValidationResult]:
        """Validate AWS security group resource."""
        results: List[ValidationResult] = []

        # Check for overly permissive ingress
        if '0.0.0.0/0' in content and ('ingress' in content.lower()):
            results.append(ValidationResult(
                rule_id="sg-open-ingress",
                message=f"Security group '{name}' allows ingress from 0.0.0.0/0",
                severity=ValidationSeverity.WARNING,
                category=ValidationCategory.SECURITY,
                file_path=file_path,
                line_number=line_num,
                resource_name=name,
                suggestion="Restrict ingress to specific CIDR blocks",
            ))

        # Check for all ports open
        if 'from_port = 0' in content and 'to_port = 65535' in content:
            results.append(ValidationResult(
                rule_id="sg-all-ports",
                message=f"Security group '{name}' opens all ports",
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.SECURITY,
                file_path=file_path,
                line_number=line_num,
                resource_name=name,
            ))

        return results

    def _validate_aws_s3_bucket(
        self, content: str, name: str, file_path: str, line_num: int
    ) -> List[ValidationResult]:
        """Validate AWS S3 bucket resource."""
        results: List[ValidationResult] = []

        # Note: These checks are simplified; real validation would parse the HCL properly
        if 'versioning' not in content.lower():
            results.append(ValidationResult(
                rule_id="s3-no-versioning",
                message=f"S3 bucket '{name}' may not have versioning enabled",
                severity=ValidationSeverity.INFO,
                category=ValidationCategory.BEST_PRACTICE,
                file_path=file_path,
                line_number=line_num,
                resource_name=name,
                suggestion="Consider enabling versioning for data protection",
            ))

        if 'server_side_encryption' not in content.lower() and 'aws_s3_bucket_server_side_encryption_configuration' not in content:
            results.append(ValidationResult(
                rule_id="s3-no-encryption",
                message=f"S3 bucket '{name}' may not have encryption configured",
                severity=ValidationSeverity.WARNING,
                category=ValidationCategory.SECURITY,
                file_path=file_path,
                line_number=line_num,
                resource_name=name,
                suggestion="Enable server-side encryption",
            ))

        return results

    def _validate_aws_iam_policy(
        self, content: str, name: str, file_path: str, line_num: int
    ) -> List[ValidationResult]:
        """Validate AWS IAM policy resource."""
        results: List[ValidationResult] = []

        # Check for wildcard actions
        if '"Action": "*"' in content or "'Action': '*'" in content or 'Action = "*"' in content:
            results.append(ValidationResult(
                rule_id="iam-wildcard-action",
                message=f"IAM policy '{name}' uses wildcard (*) action",
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.SECURITY,
                file_path=file_path,
                line_number=line_num,
                resource_name=name,
                suggestion="Use specific actions instead of wildcard",
            ))

        # Check for wildcard resources
        if '"Resource": "*"' in content or "'Resource': '*'" in content or 'Resource = "*"' in content:
            results.append(ValidationResult(
                rule_id="iam-wildcard-resource",
                message=f"IAM policy '{name}' uses wildcard (*) resource",
                severity=ValidationSeverity.WARNING,
                category=ValidationCategory.SECURITY,
                file_path=file_path,
                line_number=line_num,
                resource_name=name,
                suggestion="Scope resources to specific ARNs",
            ))

        return results

    def _validate_variable(
        self, content: str, var_name: str, file_path: str, line_num: int, start_pos: int
    ) -> List[ValidationResult]:
        """Validate a variable block."""
        results: List[ValidationResult] = []

        # Extract variable block content
        block_content = self._extract_block(content, start_pos)

        # Check for description
        if 'description' not in block_content:
            results.append(ValidationResult(
                rule_id="variable-no-description",
                message=f"Variable '{var_name}' missing description",
                severity=ValidationSeverity.WARNING,
                category=ValidationCategory.MAINTAINABILITY,
                file_path=file_path,
                line_number=line_num,
                suggestion="Add a description for documentation",
            ))

        # Check for type
        if 'type' not in block_content:
            results.append(ValidationResult(
                rule_id="variable-no-type",
                message=f"Variable '{var_name}' missing type constraint",
                severity=ValidationSeverity.WARNING,
                category=ValidationCategory.BEST_PRACTICE,
                file_path=file_path,
                line_number=line_num,
                suggestion="Add a type constraint for better validation",
            ))

        # Check if sensitive variable should be marked sensitive
        if any(p in var_name.lower() for p in self.SENSITIVE_PATTERNS):
            if 'sensitive' not in block_content or 'sensitive = true' not in block_content:
                results.append(ValidationResult(
                    rule_id="variable-not-sensitive",
                    message=f"Variable '{var_name}' appears to be sensitive but not marked as such",
                    severity=ValidationSeverity.WARNING,
                    category=ValidationCategory.SECURITY,
                    file_path=file_path,
                    line_number=line_num,
                    suggestion="Add 'sensitive = true' to the variable",
                ))

        return results

    def _validate_output(
        self, content: str, output_name: str, file_path: str, line_num: int, start_pos: int
    ) -> List[ValidationResult]:
        """Validate an output block."""
        results: List[ValidationResult] = []

        block_content = self._extract_block(content, start_pos)

        # Check for description
        if 'description' not in block_content:
            results.append(ValidationResult(
                rule_id="output-no-description",
                message=f"Output '{output_name}' missing description",
                severity=ValidationSeverity.INFO,
                category=ValidationCategory.MAINTAINABILITY,
                file_path=file_path,
                line_number=line_num,
            ))

        # Check if sensitive output should be marked sensitive
        if any(p in output_name.lower() for p in self.SENSITIVE_PATTERNS):
            if 'sensitive' not in block_content or 'sensitive = true' not in block_content:
                results.append(ValidationResult(
                    rule_id="output-not-sensitive",
                    message=f"Output '{output_name}' appears to be sensitive but not marked as such",
                    severity=ValidationSeverity.WARNING,
                    category=ValidationCategory.SECURITY,
                    file_path=file_path,
                    line_number=line_num,
                    suggestion="Add 'sensitive = true' to the output",
                ))

        return results

    def _validate_module_call(
        self, content: str, module_name: str, file_path: str, line_num: int, start_pos: int
    ) -> List[ValidationResult]:
        """Validate a module call block."""
        results: List[ValidationResult] = []

        block_content = self._extract_block(content, start_pos)

        # Check for source
        if 'source' not in block_content:
            results.append(ValidationResult(
                rule_id="module-no-source",
                message=f"Module '{module_name}' missing source",
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.SCHEMA,
                file_path=file_path,
                line_number=line_num,
            ))

        # Check for version pinning (for registry modules)
        if 'registry.terraform.io' in block_content or ('source' in block_content and 'version' not in block_content):
            # Only warn if it looks like a registry module
            source_match = re.search(r'source\s*=\s*"([^"]+)"', block_content)
            if source_match:
                source = source_match.group(1)
                # Registry modules don't start with ./ or ../ or have :// in them
                if not source.startswith('./') and not source.startswith('../') and '://' not in source:
                    if 'version' not in block_content:
                        results.append(ValidationResult(
                            rule_id="module-no-version",
                            message=f"Module '{module_name}' should pin version for registry module",
                            severity=ValidationSeverity.WARNING,
                            category=ValidationCategory.BEST_PRACTICE,
                            file_path=file_path,
                            line_number=line_num,
                            suggestion="Add version constraint for reproducible builds",
                        ))

        return results

    def _validate_module_structure(
        self, directory: str, files: List[str]
    ) -> List[ValidationResult]:
        """Validate module-level structure."""
        results: List[ValidationResult] = []
        file_names = [os.path.basename(f) for f in files]

        # Check for recommended files
        if "main.tf" not in file_names:
            results.append(ValidationResult(
                rule_id="missing-main-tf",
                message="Module missing main.tf file",
                severity=ValidationSeverity.INFO,
                category=ValidationCategory.BEST_PRACTICE,
                file_path=directory,
            ))

        if "variables.tf" not in file_names:
            results.append(ValidationResult(
                rule_id="missing-variables-tf",
                message="Module missing variables.tf file",
                severity=ValidationSeverity.INFO,
                category=ValidationCategory.BEST_PRACTICE,
                file_path=directory,
            ))

        if "outputs.tf" not in file_names:
            results.append(ValidationResult(
                rule_id="missing-outputs-tf",
                message="Module missing outputs.tf file",
                severity=ValidationSeverity.INFO,
                category=ValidationCategory.BEST_PRACTICE,
                file_path=directory,
            ))

        return results

    def _check_hardcoded_credentials(
        self, content: str, file_path: str, lines: List[str]
    ) -> List[ValidationResult]:
        """Check for hardcoded credentials."""
        results: List[ValidationResult] = []

        # Patterns that might indicate hardcoded secrets
        patterns = [
            (r'access_key\s*=\s*"[A-Z0-9]{20}"', "AWS access key"),
            (r'secret_key\s*=\s*"[A-Za-z0-9/+=]{40}"', "AWS secret key"),
            (r'password\s*=\s*"[^"]+"', "hardcoded password"),
            (r'api_key\s*=\s*"[^"]+"', "hardcoded API key"),
        ]

        for i, line in enumerate(lines):
            for pattern, description in patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    results.append(ValidationResult(
                        rule_id="hardcoded-credential",
                        message=f"Possible {description} found",
                        severity=ValidationSeverity.ERROR,
                        category=ValidationCategory.SECURITY,
                        file_path=file_path,
                        line_number=i + 1,
                        suggestion="Use variables or environment variables for sensitive values",
                    ))

        return results

    def _check_deprecated_syntax(
        self, content: str, file_path: str, lines: List[str]
    ) -> List[ValidationResult]:
        """Check for deprecated Terraform syntax."""
        results: List[ValidationResult] = []

        # Check for interpolation-only expressions (deprecated in 0.12+)
        for i, line in enumerate(lines):
            if re.search(r'=\s*"\$\{[^}]+\}"$', line.strip()):
                results.append(ValidationResult(
                    rule_id="deprecated-interpolation",
                    message="Unnecessary interpolation syntax (deprecated in Terraform 0.12+)",
                    severity=ValidationSeverity.INFO,
                    category=ValidationCategory.BEST_PRACTICE,
                    file_path=file_path,
                    line_number=i + 1,
                    suggestion="Use direct reference instead of interpolation",
                ))

        return results

    def _extract_block(self, content: str, start_pos: int) -> str:
        """Extract a block's content from the start position."""
        brace_count = 0
        started = False
        end_pos = start_pos

        for i in range(start_pos, len(content)):
            char = content[i]
            if char == '{':
                brace_count += 1
                started = True
            elif char == '}':
                brace_count -= 1
                if started and brace_count == 0:
                    end_pos = i + 1
                    break

        return content[start_pos:end_pos]

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
        info_count = sum(1 for r in results if r.severity == ValidationSeverity.INFO)

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
            file_info = sum(1 for r in file_results if r.severity == ValidationSeverity.INFO)
            file_summaries.append(FileValidationSummary(
                file_path=fp,
                error_count=file_errors,
                warning_count=file_warnings,
                info_count=file_info,
                passed=file_errors == 0,
            ))

        report_id = hashlib.sha256(str(results).encode()).hexdigest()[:16]

        return ValidationReport(
            id=f"terraform-validation-{report_id}",
            title="Terraform Configuration Validation",
            validator="TerraformValidator",
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
