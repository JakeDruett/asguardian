"""
Freya Console Models

Pydantic models for JavaScript console message capture
and analysis.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ConsoleMessageType(str, Enum):
    """Types of console messages."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    LOG = "log"
    DEBUG = "debug"
    TRACE = "trace"
    DIR = "dir"
    ASSERT = "assert"
    COUNT = "count"
    TABLE = "table"
    TIME = "time"
    TIME_END = "timeEnd"


class ConsoleSeverity(str, Enum):
    """Severity levels for console messages."""
    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    DEBUG = "debug"


class ConsoleMessage(BaseModel):
    """A single console message."""
    message_type: ConsoleMessageType = Field(..., description="Type of message")
    severity: ConsoleSeverity = Field(..., description="Severity level")
    text: str = Field(..., description="Message text")
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="When message was logged",
    )
    url: Optional[str] = Field(None, description="Source URL")
    line_number: Optional[int] = Field(None, description="Line number")
    column_number: Optional[int] = Field(None, description="Column number")
    stack_trace: Optional[str] = Field(None, description="Stack trace if available")
    args: List[Any] = Field(default_factory=list, description="Additional arguments")


class PageError(BaseModel):
    """A JavaScript error caught on the page."""
    message: str = Field(..., description="Error message")
    name: str = Field("Error", description="Error name/type")
    stack: Optional[str] = Field(None, description="Stack trace")
    url: Optional[str] = Field(None, description="Source URL")
    line_number: Optional[int] = Field(None, description="Line number")
    column_number: Optional[int] = Field(None, description="Column number")
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="When error occurred",
    )


class ResourceError(BaseModel):
    """A failed resource load."""
    url: str = Field(..., description="Resource URL")
    resource_type: str = Field(..., description="Type of resource")
    status: Optional[int] = Field(None, description="HTTP status code")
    error_text: Optional[str] = Field(None, description="Error description")
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="When error occurred",
    )


class ConsoleReport(BaseModel):
    """Complete console message report."""
    url: str = Field(..., description="URL analyzed")
    captured_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    capture_duration_ms: float = Field(0, description="Time spent capturing")

    # Messages by type
    messages: List[ConsoleMessage] = Field(default_factory=list)
    errors: List[PageError] = Field(default_factory=list)
    resource_errors: List[ResourceError] = Field(default_factory=list)

    # Counts
    total_messages: int = Field(0, description="Total console messages")
    error_count: int = Field(0, description="Number of errors")
    warning_count: int = Field(0, description="Number of warnings")
    info_count: int = Field(0, description="Number of info messages")
    log_count: int = Field(0, description="Number of log messages")

    # Analysis
    unique_errors: List[str] = Field(
        default_factory=list, description="Unique error messages"
    )
    error_sources: Dict[str, int] = Field(
        default_factory=dict, description="Error count by source file"
    )

    # Summary
    has_critical_errors: bool = Field(
        False, description="Whether critical errors were found"
    )
    suggestions: List[str] = Field(default_factory=list, description="Suggestions")

    @property
    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return self.error_count > 0 or len(self.errors) > 0

    @property
    def has_issues(self) -> bool:
        """Check if there are any issues (errors or warnings)."""
        return self.error_count > 0 or self.warning_count > 0 or len(self.errors) > 0


class ConsoleConfig(BaseModel):
    """Configuration for console capture."""
    # What to capture
    capture_errors: bool = Field(True, description="Capture error messages")
    capture_warnings: bool = Field(True, description="Capture warning messages")
    capture_info: bool = Field(False, description="Capture info messages")
    capture_logs: bool = Field(False, description="Capture log messages")
    capture_debug: bool = Field(False, description="Capture debug messages")

    # Error handling
    capture_page_errors: bool = Field(True, description="Capture uncaught errors")
    capture_resource_errors: bool = Field(True, description="Capture failed resources")

    # Limits
    max_messages: int = Field(1000, description="Maximum messages to capture")
    max_message_length: int = Field(1000, description="Max length per message")

    # Timing
    wait_time_ms: int = Field(3000, description="Time to wait for messages")
    wait_for_network_idle: bool = Field(True, description="Wait for network idle")

    # Filtering
    ignore_patterns: List[str] = Field(
        default_factory=list, description="Patterns to ignore"
    )
    include_stack_traces: bool = Field(True, description="Include stack traces")

    # Output
    output_format: str = Field("text", description="Output format")
