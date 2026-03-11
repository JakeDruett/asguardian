"""
Heimdall CLI

Command-line interface for code quality analysis, security scanning, performance profiling,
OOP metrics, dependency analysis, architecture validation, and test coverage analysis.

This module serves as the main entry point for the Heimdall CLI.
The implementation is organized into modular subpackages under cli/.

Usage:
    python -m Heimdall --help
    python -m Heimdall quality analyze ./src
    python -m Heimdall quality file-length ./src
    python -m Heimdall quality complexity ./src
    python -m Heimdall quality duplication ./src
    python -m Heimdall quality smells ./src
    python -m Heimdall quality debt ./src
    python -m Heimdall quality maintainability ./src
    python -m Heimdall quality env-fallback ./src
    python -m Heimdall quality lazy-imports ./src
    python -m Heimdall security scan ./src
    python -m Heimdall security secrets ./src
    python -m Heimdall security dependencies ./src
    python -m Heimdall security vulnerabilities ./src
    python -m Heimdall security crypto ./src
    python -m Heimdall security access ./src
    python -m Heimdall security auth ./src
    python -m Heimdall security headers ./src
    python -m Heimdall security tls ./src
    python -m Heimdall security container ./src
    python -m Heimdall security infra ./src
    python -m Heimdall performance scan ./src
    python -m Heimdall performance memory ./src
    python -m Heimdall performance cpu ./src
    python -m Heimdall performance database ./src
    python -m Heimdall performance cache ./src
    python -m Heimdall oop analyze ./src
    python -m Heimdall oop coupling ./src
    python -m Heimdall oop cohesion ./src
    python -m Heimdall oop inheritance ./src
    python -m Heimdall dependencies analyze ./src
    python -m Heimdall dependencies cycles ./src
    python -m Heimdall dependencies modularity ./src
    python -m Heimdall architecture analyze ./src
    python -m Heimdall architecture solid ./src
    python -m Heimdall architecture layers ./src
    python -m Heimdall architecture patterns ./src
    python -m Heimdall coverage analyze ./src
    python -m Heimdall coverage gaps ./src
    python -m Heimdall coverage suggestions ./src
    python -m Heimdall syntax check ./src
    python -m Heimdall syntax fix ./src
    python -m Heimdall requirements check ./src
    python -m Heimdall requirements sync ./src
    python -m Heimdall licenses check ./src
    python -m Heimdall logic duplication ./src
    python -m Heimdall logic patterns ./src
    python -m Heimdall logic complexity ./src
    python -m Heimdall logic audit ./src
    python -m Heimdall audit ./src

Architecture:
    cli/
    ├── __init__.py      - Package exports
    ├── main.py          - Main entry point and parser creation (~350 lines)
    ├── common.py        - Shared utilities and argument helpers (~450 lines)
    └── handlers.py      - Command handler implementations (~850 lines)
"""

# Re-export from the modular CLI package
from Asgard.Heimdall.cli.main import main, create_parser

__all__ = ["main", "create_parser"]

if __name__ == "__main__":
    main()
