"""
Freya - Main entry point for command-line execution.

Usage:
    python -m Freya --help
    python -m Freya accessibility audit <url>
    python -m Freya visual capture <url>
    python -m Freya responsive breakpoints <url>
    python -m Freya test <url>
"""

from Asgard.Freya.cli import main

if __name__ == "__main__":
    main()
