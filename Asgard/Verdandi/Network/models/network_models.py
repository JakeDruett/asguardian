"""
Network Performance Models

Pydantic models for network performance metrics.
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class LatencyMetrics(BaseModel):
    """Network latency metrics."""

    sample_count: int = Field(..., description="Number of samples")
    min_ms: float = Field(..., description="Minimum latency")
    max_ms: float = Field(..., description="Maximum latency")
    mean_ms: float = Field(..., description="Mean latency")
    median_ms: float = Field(..., description="Median latency")
    p90_ms: float = Field(..., description="90th percentile latency")
    p95_ms: float = Field(..., description="95th percentile latency")
    p99_ms: float = Field(..., description="99th percentile latency")
    std_dev_ms: float = Field(..., description="Standard deviation")
    jitter_ms: float = Field(..., description="Latency jitter (variation)")
    packet_loss_percent: Optional[float] = Field(default=None, description="Packet loss")
    status: str = Field(..., description="Status (good, acceptable, poor)")
    recommendations: List[str] = Field(default_factory=list)


class BandwidthMetrics(BaseModel):
    """Bandwidth utilization metrics."""

    upload_mbps: float = Field(..., description="Upload speed in Mbps")
    download_mbps: float = Field(..., description="Download speed in Mbps")
    total_throughput_mbps: float = Field(..., description="Total throughput")
    utilization_percent: Optional[float] = Field(default=None, description="Link utilization")
    capacity_mbps: Optional[float] = Field(default=None, description="Link capacity")
    bytes_sent: int = Field(..., description="Total bytes sent")
    bytes_received: int = Field(..., description="Total bytes received")
    duration_seconds: float = Field(..., description="Measurement duration")
    status: str = Field(..., description="Status")
    recommendations: List[str] = Field(default_factory=list)


class DnsMetrics(BaseModel):
    """DNS resolution metrics."""

    query_count: int = Field(..., description="Number of DNS queries")
    avg_resolution_ms: float = Field(..., description="Average resolution time")
    p95_resolution_ms: float = Field(..., description="95th percentile resolution time")
    max_resolution_ms: float = Field(..., description="Maximum resolution time")
    cache_hit_rate: float = Field(..., description="DNS cache hit rate percentage")
    failure_rate: float = Field(..., description="DNS failure rate percentage")
    by_record_type: Dict[str, Dict[str, float]] = Field(
        default_factory=dict,
        description="Breakdown by record type",
    )
    status: str = Field(..., description="Status")
    recommendations: List[str] = Field(default_factory=list)


class ConnectionMetrics(BaseModel):
    """TCP/HTTP connection metrics."""

    total_connections: int = Field(..., description="Total connections")
    active_connections: int = Field(..., description="Currently active")
    idle_connections: int = Field(..., description="Idle connections")
    avg_connection_time_ms: float = Field(..., description="Avg time to establish")
    avg_ssl_handshake_ms: Optional[float] = Field(default=None, description="Avg SSL handshake")
    connection_reuse_rate: float = Field(..., description="Connection reuse percentage")
    error_rate: float = Field(..., description="Connection error rate")
    timeout_count: int = Field(default=0, description="Connection timeouts")
    status: str = Field(..., description="Status")
    recommendations: List[str] = Field(default_factory=list)
