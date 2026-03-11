"""
Freya Link Models

Pydantic models for link validation including broken links,
redirect chains, and link analysis.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class LinkStatus(str, Enum):
    """Status of a link."""
    OK = "ok"
    BROKEN = "broken"
    REDIRECT = "redirect"
    TIMEOUT = "timeout"
    ERROR = "error"
    SKIPPED = "skipped"


class LinkType(str, Enum):
    """Type of link."""
    INTERNAL = "internal"
    EXTERNAL = "external"
    ANCHOR = "anchor"
    MAILTO = "mailto"
    TEL = "tel"
    JAVASCRIPT = "javascript"
    OTHER = "other"


class LinkSeverity(str, Enum):
    """Severity of link issues."""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class LinkResult(BaseModel):
    """Result of checking a single link."""
    url: str = Field(..., description="The link URL")
    source_url: str = Field(..., description="Page where link was found")
    link_text: Optional[str] = Field(None, description="Link text content")
    link_type: LinkType = Field(..., description="Type of link")
    status: LinkStatus = Field(..., description="Link status")

    # HTTP details
    status_code: Optional[int] = Field(None, description="HTTP status code")
    final_url: Optional[str] = Field(None, description="Final URL after redirects")
    redirect_chain: List[str] = Field(
        default_factory=list, description="Redirect chain"
    )
    redirect_count: int = Field(0, description="Number of redirects")

    # Timing
    response_time_ms: Optional[float] = Field(None, description="Response time in ms")

    # Issues
    error_message: Optional[str] = Field(None, description="Error message if failed")
    is_broken: bool = Field(False, description="Whether link is broken")

    # Context
    element_html: Optional[str] = Field(None, description="HTML of the link element")
    anchor_exists: Optional[bool] = Field(
        None, description="Whether anchor target exists (for # links)"
    )


class BrokenLink(BaseModel):
    """A broken link found during validation."""
    url: str = Field(..., description="The broken URL")
    source_url: str = Field(..., description="Page containing the link")
    link_text: Optional[str] = Field(None, description="Link text")
    status_code: Optional[int] = Field(None, description="HTTP status code")
    error_message: Optional[str] = Field(None, description="Error description")
    severity: LinkSeverity = Field(..., description="Issue severity")
    suggested_fix: str = Field(..., description="How to fix")


class RedirectChain(BaseModel):
    """A redirect chain found during validation."""
    start_url: str = Field(..., description="Starting URL")
    final_url: str = Field(..., description="Final destination URL")
    chain: List[str] = Field(default_factory=list, description="All URLs in chain")
    chain_length: int = Field(0, description="Number of redirects")
    source_url: str = Field(..., description="Page containing the link")
    is_temporary: bool = Field(False, description="Contains temporary redirects")
    total_time_ms: float = Field(0, description="Total redirect time")


class LinkReport(BaseModel):
    """Complete link validation report."""
    url: str = Field(..., description="Base URL analyzed")
    analyzed_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    analysis_duration_ms: float = Field(0, description="Analysis duration")

    # All results
    results: List[LinkResult] = Field(default_factory=list)

    # Statistics
    total_links: int = Field(0, description="Total links found")
    internal_links: int = Field(0, description="Internal links")
    external_links: int = Field(0, description="External links")
    anchor_links: int = Field(0, description="Anchor links")

    # Status breakdown
    ok_count: int = Field(0, description="OK links")
    broken_count: int = Field(0, description="Broken links")
    redirect_count: int = Field(0, description="Links with redirects")
    timeout_count: int = Field(0, description="Timed out links")
    error_count: int = Field(0, description="Error links")
    skipped_count: int = Field(0, description="Skipped links")

    # Issues found
    broken_links: List[BrokenLink] = Field(default_factory=list)
    redirect_chains: List[RedirectChain] = Field(default_factory=list)

    # Analysis
    unique_domains: List[str] = Field(
        default_factory=list, description="Unique external domains"
    )
    slow_links: List[str] = Field(
        default_factory=list, description="Links over 1 second"
    )

    # Summary
    health_score: float = Field(0, description="Link health score 0-100")
    suggestions: List[str] = Field(default_factory=list, description="Suggestions")

    @property
    def has_broken_links(self) -> bool:
        """Check if there are broken links."""
        return self.broken_count > 0

    @property
    def has_issues(self) -> bool:
        """Check if there are any issues."""
        return self.broken_count > 0 or len(self.redirect_chains) > 0


class LinkConfig(BaseModel):
    """Configuration for link validation."""
    # What to check
    check_internal: bool = Field(True, description="Check internal links")
    check_external: bool = Field(True, description="Check external links")
    check_anchors: bool = Field(True, description="Check anchor links")

    # Skip patterns
    skip_mailto: bool = Field(True, description="Skip mailto: links")
    skip_tel: bool = Field(True, description="Skip tel: links")
    skip_javascript: bool = Field(True, description="Skip javascript: links")
    skip_patterns: List[str] = Field(
        default_factory=list, description="URL patterns to skip"
    )

    # Limits
    max_links: int = Field(500, description="Maximum links to check")
    max_redirects: int = Field(10, description="Maximum redirects to follow")
    timeout_ms: int = Field(10000, description="Timeout per link in ms")
    concurrent_requests: int = Field(10, description="Concurrent requests")

    # Redirect handling
    report_redirects: bool = Field(True, description="Report redirect chains")
    min_redirect_chain: int = Field(2, description="Minimum redirects to report")

    # Reporting
    include_ok_links: bool = Field(False, description="Include OK links in report")
    output_format: str = Field("text", description="Output format")
