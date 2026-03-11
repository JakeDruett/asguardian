"""
Freya Console Package

Console message capture module.
Captures JavaScript errors, warnings, and other console output.
"""

from Asgard.Freya.Console.models import (
    ConsoleConfig,
    ConsoleMessage,
    ConsoleMessageType,
    ConsoleReport,
    ConsoleSeverity,
    PageError,
    ResourceError,
)
from Asgard.Freya.Console.services import (
    ConsoleCapture,
)

__all__ = [
    # Models
    "ConsoleConfig",
    "ConsoleMessage",
    "ConsoleMessageType",
    "ConsoleReport",
    "ConsoleSeverity",
    "PageError",
    "ResourceError",
    # Services
    "ConsoleCapture",
]
