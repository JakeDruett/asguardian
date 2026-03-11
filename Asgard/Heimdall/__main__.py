"""
Heimdall CLI entry point.

This module allows running Heimdall as a module:
    python -m Heimdall --help
    python -m Heimdall quality analyze ./src
    python -m Heimdall audit ./src
"""

from Asgard.Heimdall.cli import main

if __name__ == "__main__":
    main()
