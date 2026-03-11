"""
Freya Links Models Package

Models for link validation and analysis.
"""

from Asgard.Freya.Links.models.link_models import (
    BrokenLink,
    LinkConfig,
    LinkReport,
    LinkResult,
    LinkSeverity,
    LinkStatus,
    LinkType,
    RedirectChain,
)

__all__ = [
    "BrokenLink",
    "LinkConfig",
    "LinkReport",
    "LinkResult",
    "LinkSeverity",
    "LinkStatus",
    "LinkType",
    "RedirectChain",
]
