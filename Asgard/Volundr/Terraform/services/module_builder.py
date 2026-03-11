"""
Terraform Module Builder Service

Generates comprehensive Terraform modules with best practices,
documentation, testing frameworks, and multi-cloud provider support.
"""

import hashlib
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from Asgard.Volundr.Terraform.models.terraform_models import (
    CloudProvider,
    GeneratedModule,
    ModuleComplexity,
    ModuleConfig,
)


class ModuleBuilder:
    """Generates Terraform modules from configuration."""

    PROVIDER_SOURCES = {
        CloudProvider.AWS: ("hashicorp/aws", ">= 5.0"),
        CloudProvider.AZURE: ("hashicorp/azurerm", ">= 3.0"),
        CloudProvider.GCP: ("hashicorp/google", ">= 4.0"),
        CloudProvider.KUBERNETES: ("hashicorp/kubernetes", ">= 2.0"),
        CloudProvider.HELM: ("hashicorp/helm", ">= 2.0"),
        CloudProvider.VAULT: ("hashicorp/vault", ">= 3.0"),
    }

    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize the module builder.

        Args:
            output_dir: Directory for saving generated modules
        """
        self.output_dir = output_dir or "modules"

    def generate(self, config: ModuleConfig) -> GeneratedModule:
        """
        Generate a complete Terraform module based on the provided configuration.

        Args:
            config: Module configuration

        Returns:
            GeneratedModule with all generated files
        """
        config_json = config.model_dump_json()
        config_hash = hashlib.sha256(config_json.encode()).hexdigest()[:16]
        module_id = f"{config.name}-{config_hash}"

        module_files: Dict[str, str] = {}
        module_files["main.tf"] = self._generate_main_tf(config)
        module_files["variables.tf"] = self._generate_variables_tf(config)
        module_files["outputs.tf"] = self._generate_outputs_tf(config)
        module_files["versions.tf"] = self._generate_versions_tf(config)

        if config.locals:
            module_files["locals.tf"] = self._generate_locals_tf(config)

        documentation = self._generate_documentation(config)
        module_files["README.md"] = documentation

        examples = self._generate_examples(config)
        tests = self._generate_tests(config)

        validation_results = self._validate_module(module_files, config)
        best_practice_score = self._calculate_best_practice_score(module_files, config)

        return GeneratedModule(
            id=module_id,
            config_hash=config_hash,
            module_files=module_files,
            documentation=documentation,
            examples=examples,
            tests=tests,
            validation_results=validation_results,
            best_practice_score=best_practice_score,
            created_at=datetime.now(),
        )

    def _generate_main_tf(self, config: ModuleConfig) -> str:
        """Generate the main Terraform configuration file."""
        content: List[str] = []

        if config.locals:
            content.append("locals {")
            for key, value in config.locals.items():
                if isinstance(value, str):
                    content.append(f'  {key} = "{value}"')
                else:
                    content.append(f"  {key} = {json.dumps(value)}")
            content.append("}")
            content.append("")

        for data_source in config.data_sources:
            content.extend(self._generate_data_source_block(data_source, config))
            content.append("")

        for resource in config.resources:
            content.extend(self._generate_resource_block(resource, config))
            content.append("")

        return "\n".join(content)

    def _generate_variables_tf(self, config: ModuleConfig) -> str:
        """Generate the variables.tf file."""
        content: List[str] = []

        for var in config.variables:
            content.append(f'variable "{var.name}" {{')
            content.append(f'  description = "{var.description}"')
            content.append(f"  type        = {var.type}")

            if var.default is not None:
                if isinstance(var.default, str):
                    content.append(f'  default     = "{var.default}"')
                elif isinstance(var.default, bool):
                    content.append(f"  default     = {str(var.default).lower()}")
                else:
                    content.append(f"  default     = {json.dumps(var.default)}")

            if var.validation:
                content.append("  validation {")
                content.append(f"    condition     = {var.validation}")
                content.append(f'    error_message = "Invalid value for {var.name}."')
                content.append("  }")

            if var.sensitive:
                content.append("  sensitive   = true")

            content.append("}")
            content.append("")

        return "\n".join(content)

    def _generate_outputs_tf(self, config: ModuleConfig) -> str:
        """Generate the outputs.tf file."""
        content: List[str] = []

        for output in config.outputs:
            content.append(f'output "{output.name}" {{')
            content.append(f'  description = "{output.description}"')
            content.append(f"  value       = {output.value}")

            if output.sensitive:
                content.append("  sensitive   = true")

            content.append("}")
            content.append("")

        return "\n".join(content)

    def _generate_versions_tf(self, config: ModuleConfig) -> str:
        """Generate the versions.tf file with provider requirements."""
        content: List[str] = []

        content.append("terraform {")
        content.append(f'  required_version = "{config.terraform_version}"')
        content.append("")
        content.append("  required_providers {")

        source, version = self.PROVIDER_SOURCES.get(
            config.provider, ("hashicorp/null", ">= 3.0")
        )
        content.append(f"    {config.provider.value} = {{")
        content.append(f'      source  = "{source}"')
        content.append(f'      version = "{version}"')
        content.append("    }")

        for provider, version in config.required_providers.items():
            content.append(f"    {provider} = {{")
            content.append(f'      source  = "hashicorp/{provider}"')
            content.append(f'      version = "{version}"')
            content.append("    }")

        content.append("  }")
        content.append("}")

        return "\n".join(content)

    def _generate_locals_tf(self, config: ModuleConfig) -> str:
        """Generate the locals.tf file."""
        content: List[str] = []

        content.append("locals {")

        if config.tags:
            content.append("  common_tags = {")
            for key, value in config.tags.items():
                content.append(f'    "{key}" = "{value}"')
            content.append("  }")
            content.append("")

        for key, value in config.locals.items():
            if key != "common_tags":
                if isinstance(value, str):
                    content.append(f'  {key} = "{value}"')
                else:
                    content.append(f"  {key} = {json.dumps(value, indent=2)}")

        content.append("}")

        return "\n".join(content)

    def _generate_data_source_block(self, data_source: str, config: ModuleConfig) -> List[str]:
        """Generate a data source block based on the provider and category."""
        lines: List[str] = []

        if config.provider == CloudProvider.AWS:
            if "vpc" in data_source.lower():
                lines.extend([
                    'data "aws_vpc" "default" {',
                    "  default = true",
                    "}",
                ])
            elif "subnet" in data_source.lower():
                lines.extend([
                    'data "aws_subnets" "default" {',
                    "  filter {",
                    '    name   = "vpc-id"',
                    "    values = [data.aws_vpc.default.id]",
                    "  }",
                    "}",
                ])
            elif "ami" in data_source.lower():
                lines.extend([
                    'data "aws_ami" "latest" {',
                    "  most_recent = true",
                    '  owners      = ["amazon"]',
                    "",
                    "  filter {",
                    '    name   = "name"',
                    '    values = ["amzn2-ami-hvm-*-x86_64-gp2"]',
                    "  }",
                    "}",
                ])
        elif config.provider == CloudProvider.AZURE:
            if "resource_group" in data_source.lower():
                lines.extend([
                    'data "azurerm_resource_group" "main" {',
                    "  name = var.resource_group_name",
                    "}",
                ])
        elif config.provider == CloudProvider.GCP:
            if "project" in data_source.lower():
                lines.extend([
                    'data "google_project" "current" {',
                    "}",
                ])

        return lines

    def _generate_resource_block(self, resource: str, config: ModuleConfig) -> List[str]:
        """Generate a resource block based on the provider and category."""
        lines: List[str] = []
        tags_ref = "local.common_tags" if config.tags else "var.tags"

        if config.provider == CloudProvider.AWS:
            if "instance" in resource.lower():
                lines.extend([
                    'resource "aws_instance" "main" {',
                    "  ami           = data.aws_ami.latest.id",
                    "  instance_type = var.instance_type",
                    "  subnet_id     = data.aws_subnets.default.ids[0]",
                    "",
                    f"  tags = merge({tags_ref}, {{",
                    "    Name = var.instance_name",
                    "  })",
                    "}",
                ])
            elif "s3" in resource.lower():
                lines.extend([
                    'resource "aws_s3_bucket" "main" {',
                    "  bucket = var.bucket_name",
                    "",
                    f"  tags = {tags_ref}",
                    "}",
                    "",
                    'resource "aws_s3_bucket_versioning" "main" {',
                    "  bucket = aws_s3_bucket.main.id",
                    "  versioning_configuration {",
                    '    status = "Enabled"',
                    "  }",
                    "}",
                    "",
                    'resource "aws_s3_bucket_server_side_encryption_configuration" "main" {',
                    "  bucket = aws_s3_bucket.main.id",
                    "",
                    "  rule {",
                    "    apply_server_side_encryption_by_default {",
                    '      sse_algorithm = "AES256"',
                    "    }",
                    "  }",
                    "}",
                ])
            elif "vpc" in resource.lower():
                lines.extend([
                    'resource "aws_vpc" "main" {',
                    "  cidr_block           = var.vpc_cidr",
                    "  enable_dns_hostnames = true",
                    "  enable_dns_support   = true",
                    "",
                    f"  tags = merge({tags_ref}, {{",
                    '    Name = "${var.name_prefix}-vpc"',
                    "  })",
                    "}",
                ])
        elif config.provider == CloudProvider.AZURE:
            if "resource_group" in resource.lower():
                lines.extend([
                    'resource "azurerm_resource_group" "main" {',
                    "  name     = var.resource_group_name",
                    "  location = var.location",
                    "",
                    "  tags = var.tags",
                    "}",
                ])
            elif "virtual_network" in resource.lower():
                lines.extend([
                    'resource "azurerm_virtual_network" "main" {',
                    '  name                = "${var.name_prefix}-vnet"',
                    "  address_space       = [var.vnet_cidr]",
                    "  location            = azurerm_resource_group.main.location",
                    "  resource_group_name = azurerm_resource_group.main.name",
                    "",
                    "  tags = var.tags",
                    "}",
                ])
        elif config.provider == CloudProvider.GCP:
            if "compute_instance" in resource.lower():
                lines.extend([
                    'resource "google_compute_instance" "main" {',
                    "  name         = var.instance_name",
                    "  machine_type = var.machine_type",
                    "  zone         = var.zone",
                    "",
                    "  boot_disk {",
                    "    initialize_params {",
                    "      image = var.image",
                    "    }",
                    "  }",
                    "",
                    "  network_interface {",
                    '    network = "default"',
                    "    access_config {}",
                    "  }",
                    "",
                    "  labels = var.labels",
                    "}",
                ])

        return lines

    def _generate_documentation(self, config: ModuleConfig) -> str:
        """Generate comprehensive README.md documentation."""
        content: List[str] = []

        content.extend([
            f"# {config.name.replace('_', ' ').title()}",
            "",
            config.description or f"Terraform module for {config.category.value} resources on {config.provider.value.upper()}.",
            "",
            "## Overview",
            "",
            f"This Terraform module creates {config.category.value} resources on {config.provider.value.upper()}.",
            f"It follows best practices for {config.complexity.value} deployments.",
            "",
            "## Usage",
            "",
            "```hcl",
            f'module "{config.name}" {{',
            f'  source = "./{config.name}"',
            "",
        ])

        for var in config.variables[:5]:
            if var.default is not None:
                if isinstance(var.default, str):
                    content.append(f'  {var.name} = "{var.default}"')
                else:
                    content.append(f"  {var.name} = {json.dumps(var.default)}")
            else:
                content.append(f'  {var.name} = "your-value-here"')

        content.extend([
            "}",
            "```",
            "",
            "## Requirements",
            "",
            "| Name | Version |",
            "|------|---------|",
            f"| terraform | {config.terraform_version} |",
        ])

        source, version = self.PROVIDER_SOURCES.get(config.provider, ("hashicorp/null", ">= 3.0"))
        content.append(f"| {config.provider.value} | {version} |")

        for provider, version in config.required_providers.items():
            content.append(f"| {provider} | {version} |")

        content.extend([
            "",
            "## Inputs",
            "",
            "| Name | Description | Type | Default | Required |",
            "|------|-------------|------|---------|----------|",
        ])

        for var in config.variables:
            default_val = "n/a" if var.default is None else str(var.default)
            required = "yes" if var.default is None else "no"
            content.append(f"| {var.name} | {var.description} | `{var.type}` | `{default_val}` | {required} |")

        content.extend([
            "",
            "## Outputs",
            "",
            "| Name | Description |",
            "|------|-------------|",
        ])

        for output in config.outputs:
            content.append(f"| {output.name} | {output.description} |")

        content.extend([
            "",
            "## Examples",
            "",
            "See the `examples/` directory for complete usage examples.",
            "",
            "## Security Considerations",
            "",
            "- All resources are created with security best practices",
            "- Sensitive values are marked appropriately",
            "- Network security groups follow least privilege principle",
            "",
            f"## Version: {config.version}",
        ])

        return "\n".join(content)

    def _generate_examples(self, config: ModuleConfig) -> Dict[str, str]:
        """Generate example configurations."""
        examples: Dict[str, str] = {}

        basic_example: List[str] = [
            f'module "{config.name}_basic" {{',
            '  source = "../../"',
            "",
        ]

        for var in config.variables:
            if var.default is None:
                if "name" in var.name.lower():
                    basic_example.append(f'  {var.name} = "example-{config.name}"')
                elif var.type == "string":
                    basic_example.append(f'  {var.name} = "example-value"')
                elif var.type == "number":
                    basic_example.append(f"  {var.name} = 1")
                elif var.type == "bool":
                    basic_example.append(f"  {var.name} = true")

        basic_example.append("}")
        examples["basic"] = "\n".join(basic_example)

        if config.complexity in [ModuleComplexity.COMPLEX, ModuleComplexity.ENTERPRISE]:
            advanced_example: List[str] = [
                f'module "{config.name}_advanced" {{',
                '  source = "../../"',
                "",
            ]

            for var in config.variables:
                if var.default is not None:
                    if isinstance(var.default, str):
                        advanced_example.append(f'  {var.name} = "advanced-{var.default}"')
                    else:
                        advanced_example.append(f"  {var.name} = {json.dumps(var.default)}")
                else:
                    advanced_example.append(f'  {var.name} = "advanced-example"')

            advanced_example.append("}")
            examples["advanced"] = "\n".join(advanced_example)

        return examples

    def _generate_tests(self, config: ModuleConfig) -> Dict[str, str]:
        """Generate test configurations."""
        tests: Dict[str, str] = {}

        output_name = config.outputs[0].name if config.outputs else "id"
        terratest_content = f'''package test

import (
    "testing"
    "github.com/gruntwork-io/terratest/modules/terraform"
    "github.com/stretchr/testify/assert"
)

func Test{config.name.replace("_", "").title()}Basic(t *testing.T) {{
    terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{{
        TerraformDir: "../examples/basic",
    }})

    defer terraform.Destroy(t, terraformOptions)
    terraform.InitAndApply(t, terraformOptions)

    output := terraform.Output(t, terraformOptions, "{output_name}")
    assert.NotEmpty(t, output)
}}
'''
        tests["terratest"] = terratest_content

        kitchen_yml = f'''---
driver:
  name: terraform
  variable_files:
    - testing.tfvars

provisioner:
  name: terraform

verifier:
  name: terraform
  format: junit

platforms:
  - name: {config.provider.value}

suites:
  - name: {config.name}
    driver:
      root_module_directory: test/fixtures/{config.name}
    verifier:
      color: false
      fail_fast: false
      systems:
        - name: {config.name}
          backend: local
'''
        tests["kitchen"] = kitchen_yml

        return tests

    def _validate_module(self, module_files: Dict[str, str], config: ModuleConfig) -> List[str]:
        """Validate the generated module for common issues."""
        issues: List[str] = []

        required_files = ["main.tf", "variables.tf", "outputs.tf", "versions.tf"]
        for file in required_files:
            if file not in module_files:
                issues.append(f"Missing required file: {file}")

        if "variables.tf" in module_files:
            variables_content = module_files["variables.tf"]
            for var in config.variables:
                if f'variable "{var.name}"' not in variables_content:
                    issues.append(f"Variable {var.name} not found in variables.tf")

        if "outputs.tf" in module_files:
            outputs_content = module_files["outputs.tf"]
            for output in config.outputs:
                if f'output "{output.name}"' not in outputs_content:
                    issues.append(f"Output {output.name} not found in outputs.tf")

        if "main.tf" in module_files:
            main_content = module_files["main.tf"]
            if config.provider == CloudProvider.AWS:
                if "aws_s3_bucket" in main_content and "server_side_encryption" not in main_content:
                    issues.append("S3 bucket missing encryption configuration")
                if "aws_security_group" in main_content and "0.0.0.0/0" in main_content:
                    issues.append("Security group allows access from 0.0.0.0/0")

        return issues

    def _calculate_best_practice_score(self, module_files: Dict[str, str], config: ModuleConfig) -> float:
        """Calculate a best practice score for the generated module."""
        score = 0.0
        max_score = 0.0

        max_score += 25
        required_files = ["main.tf", "variables.tf", "outputs.tf", "versions.tf", "README.md"]
        present_files = sum(1 for file in required_files if file in module_files)
        score += (present_files / len(required_files)) * 25

        max_score += 20
        if config.variables:
            documented_vars = sum(1 for var in config.variables if var.description)
            score += (documented_vars / len(config.variables)) * 20
        else:
            score += 20

        max_score += 15
        if config.outputs:
            documented_outputs = sum(1 for output in config.outputs if output.description)
            score += (documented_outputs / len(config.outputs)) * 15
        else:
            score += 15

        max_score += 15
        if "versions.tf" in module_files:
            versions_content = module_files["versions.tf"]
            if "required_version" in versions_content:
                score += 8
            if "required_providers" in versions_content:
                score += 7

        max_score += 15
        if "main.tf" in module_files:
            main_content = module_files["main.tf"]
            if config.provider == CloudProvider.AWS:
                if "encryption" in main_content or "kms" in main_content:
                    score += 8
                if "0.0.0.0/0" not in main_content:
                    score += 7
            else:
                score += 15

        max_score += 10
        if "README.md" in module_files:
            readme_content = module_files["README.md"]
            if len(readme_content) > 1000:
                score += 10
            elif len(readme_content) > 500:
                score += 5

        return (score / max_score) * 100 if max_score > 0 else 0.0

    def save_to_directory(self, module: GeneratedModule, output_dir: Optional[str] = None) -> str:
        """
        Save generated module files to a directory structure.

        Args:
            module: Generated module to save
            output_dir: Override output directory

        Returns:
            Path to the saved module directory
        """
        target_dir = output_dir or self.output_dir
        module_dir = os.path.join(target_dir, module.id)
        os.makedirs(module_dir, exist_ok=True)

        for filename, content in module.module_files.items():
            file_path = os.path.join(module_dir, filename)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

        if module.examples:
            examples_dir = os.path.join(module_dir, "examples")
            os.makedirs(examples_dir, exist_ok=True)
            for example_name, content in module.examples.items():
                example_dir = os.path.join(examples_dir, example_name)
                os.makedirs(example_dir, exist_ok=True)
                with open(os.path.join(example_dir, "main.tf"), "w", encoding="utf-8") as f:
                    f.write(content)

        if module.tests:
            tests_dir = os.path.join(module_dir, "test")
            os.makedirs(tests_dir, exist_ok=True)
            for test_name, content in module.tests.items():
                if test_name == "terratest":
                    with open(os.path.join(tests_dir, "main_test.go"), "w", encoding="utf-8") as f:
                        f.write(content)
                elif test_name == "kitchen":
                    with open(os.path.join(tests_dir, ".kitchen.yml"), "w", encoding="utf-8") as f:
                        f.write(content)

        return module_dir
