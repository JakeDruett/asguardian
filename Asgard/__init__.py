"""
Asgard - Universal Development Tools Suite

Named after the realm of the Norse gods, Asgard is a comprehensive
suite of development and quality assurance tools. Like the mythical realm
that houses the great halls of the Aesir, Asgard houses the tools that
watch over and forge your codebase.

Subpackages:
    Heimdall: Code quality control and static analysis (the watchman)
    Freya: Visual and UI testing (the goddess of beauty)
    Forseti: API and schema specification (the god of justice/contracts)
    Verdandi: Runtime performance metrics (the Norn of the present)
    Volundr: Infrastructure generation (the master smith)
"""

__version__ = "1.0.0"
__author__ = "Asgard Contributors"

# Package metadata
PACKAGE_INFO = {
    "name": "Asgard",
    "version": __version__,
    "description": "Universal Development Tools Suite",
    "sub_packages": [
        "Heimdall",
        "Freya",
        "Forseti",
        "Verdandi",
        "Volundr",
    ],
}

# Lazy imports for subpackages - available when needed
__all__ = [
    "Heimdall",
    "Freya",
    "Forseti",
    "Verdandi",
    "Volundr",
    "PACKAGE_INFO",
    "__version__",
]
