"""
Freya Security Header Models

Pydantic models for security header analysis including CSP,
HSTS, and other security-related HTTP headers.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SecurityHeaderSeverity(str, Enum):
    """Security issue severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class SecurityHeaderStatus(str, Enum):
    """Status of a security header."""
    PRESENT = "present"
    MISSING = "missing"
    INVALID = "invalid"
    WEAK = "weak"


class SecurityHeader(BaseModel):
    """A single security header with analysis."""
    name: str = Field(..., description="Header name")
    value: Optional[str] = Field(None, description="Header value")
    status: SecurityHeaderStatus = Field(..., description="Header status")
    is_secure: bool = Field(True, description="Whether configuration is secure")
    issues: List[str] = Field(default_factory=list, description="Issues found")
    recommendations: List[str] = Field(
        default_factory=list, description="Recommendations"
    )


class CSPDirective(BaseModel):
    """A single CSP directive."""
    name: str = Field(..., description="Directive name")
    values: List[str] = Field(default_factory=list, description="Directive values")
    has_unsafe_inline: bool = Field(False, description="Contains 'unsafe-inline'")
    has_unsafe_eval: bool = Field(False, description="Contains 'unsafe-eval'")
    allows_any: bool = Field(False, description="Allows any source (*)")
    issues: List[str] = Field(default_factory=list, description="Issues with directive")


class CSPReport(BaseModel):
    """Detailed CSP analysis report."""
    raw_value: Optional[str] = Field(None, description="Raw CSP header value")
    is_present: bool = Field(False, description="Whether CSP is present")
    is_report_only: bool = Field(False, description="Whether CSP is report-only")

    # Parsed directives
    directives: List[CSPDirective] = Field(default_factory=list)

    # Key directive analysis
    default_src: Optional[CSPDirective] = Field(None)
    script_src: Optional[CSPDirective] = Field(None)
    style_src: Optional[CSPDirective] = Field(None)
    img_src: Optional[CSPDirective] = Field(None)
    connect_src: Optional[CSPDirective] = Field(None)
    frame_src: Optional[CSPDirective] = Field(None)
    font_src: Optional[CSPDirective] = Field(None)
    object_src: Optional[CSPDirective] = Field(None)
    base_uri: Optional[CSPDirective] = Field(None)
    form_action: Optional[CSPDirective] = Field(None)
    frame_ancestors: Optional[CSPDirective] = Field(None)

    # Analysis summary
    uses_nonces: bool = Field(False, description="Uses nonce-based approach")
    uses_hashes: bool = Field(False, description="Uses hash-based approach")
    uses_strict_dynamic: bool = Field(False, description="Uses 'strict-dynamic'")

    # Issues
    critical_issues: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)

    # Score
    security_score: float = Field(0, description="CSP security score 0-100")

    @property
    def has_issues(self) -> bool:
        """Check if there are critical issues."""
        return len(self.critical_issues) > 0


class SecurityHeaderReport(BaseModel):
    """Complete security header analysis report."""
    url: str = Field(..., description="URL analyzed")
    analyzed_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    # Individual headers
    content_security_policy: Optional[SecurityHeader] = Field(None)
    strict_transport_security: Optional[SecurityHeader] = Field(None)
    x_frame_options: Optional[SecurityHeader] = Field(None)
    x_content_type_options: Optional[SecurityHeader] = Field(None)
    x_xss_protection: Optional[SecurityHeader] = Field(None)
    referrer_policy: Optional[SecurityHeader] = Field(None)
    permissions_policy: Optional[SecurityHeader] = Field(None)
    cross_origin_opener_policy: Optional[SecurityHeader] = Field(None)
    cross_origin_embedder_policy: Optional[SecurityHeader] = Field(None)
    cross_origin_resource_policy: Optional[SecurityHeader] = Field(None)

    # CSP detailed analysis
    csp_report: Optional[CSPReport] = Field(None)

    # HSTS details
    hsts_max_age: Optional[int] = Field(None, description="HSTS max-age in seconds")
    hsts_include_subdomains: bool = Field(False)
    hsts_preload: bool = Field(False)

    # Overall assessment
    security_score: float = Field(0, description="Overall security score 0-100")
    security_grade: str = Field("F", description="Security grade A-F")
    total_headers_checked: int = Field(0)
    headers_present: int = Field(0)
    headers_missing: int = Field(0)
    headers_weak: int = Field(0)

    # Issues summary
    critical_issues: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)

    # Metadata
    analysis_duration_ms: float = Field(0)
    all_headers: Dict[str, str] = Field(
        default_factory=dict, description="All response headers"
    )

    @property
    def has_issues(self) -> bool:
        """Check if there are any issues."""
        return len(self.critical_issues) > 0 or len(self.warnings) > 0


class SecurityIssue(BaseModel):
    """A single security issue found."""
    header: str = Field(..., description="Related header")
    severity: SecurityHeaderSeverity = Field(..., description="Issue severity")
    description: str = Field(..., description="Issue description")
    impact: str = Field(..., description="Security impact")
    recommendation: str = Field(..., description="How to fix")
    reference_url: Optional[str] = Field(None, description="Reference documentation")


class SecurityConfig(BaseModel):
    """Configuration for security header analysis."""
    # Which headers to check
    check_csp: bool = Field(True, description="Check Content-Security-Policy")
    check_hsts: bool = Field(True, description="Check Strict-Transport-Security")
    check_frame_options: bool = Field(True, description="Check X-Frame-Options")
    check_content_type_options: bool = Field(True, description="Check X-Content-Type-Options")
    check_xss_protection: bool = Field(True, description="Check X-XSS-Protection")
    check_referrer_policy: bool = Field(True, description="Check Referrer-Policy")
    check_permissions_policy: bool = Field(True, description="Check Permissions-Policy")
    check_cross_origin: bool = Field(True, description="Check Cross-Origin policies")

    # HSTS requirements
    min_hsts_max_age: int = Field(
        31536000, description="Minimum HSTS max-age (1 year in seconds)"
    )
    require_hsts_subdomains: bool = Field(True, description="Require includeSubDomains")
    require_hsts_preload: bool = Field(False, description="Require preload")

    # CSP requirements
    allow_unsafe_inline: bool = Field(False, description="Allow 'unsafe-inline' in CSP")
    allow_unsafe_eval: bool = Field(False, description="Allow 'unsafe-eval' in CSP")
    allow_wildcard_sources: bool = Field(False, description="Allow * sources in CSP")

    # Output
    output_format: str = Field("text", description="Output format")
