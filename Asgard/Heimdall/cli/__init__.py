"""
Heimdall CLI Package

Command-line interface for code quality analysis, security scanning, performance profiling,
OOP metrics, dependency analysis, architecture validation, and test coverage analysis.

This package provides a modular CLI structure with separate modules for each command group:
- quality: Code quality analysis
- security: Security vulnerability analysis
- performance: Performance analysis
- oop: Object-oriented metrics
- dependencies: Dependency analysis
- architecture: Architecture validation
- coverage: Test coverage analysis
"""

from Asgard.Heimdall.cli.main import main, create_parser

__all__ = ["main", "create_parser"]
