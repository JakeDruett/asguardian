"""
Freya Links Package

Link validation module.
Detects broken links and redirect chains on web pages.
"""

from Asgard.Freya.Links.models import (
    BrokenLink,
    LinkConfig,
    LinkReport,
    LinkResult,
    LinkSeverity,
    LinkStatus,
    LinkType,
    RedirectChain,
)
from Asgard.Freya.Links.services import (
    LinkValidator,
)

__all__ = [
    # Models
    "BrokenLink",
    "LinkConfig",
    "LinkReport",
    "LinkResult",
    "LinkSeverity",
    "LinkStatus",
    "LinkType",
    "RedirectChain",
    # Services
    "LinkValidator",
]
