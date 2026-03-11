"""
System Performance Models

Pydantic models for system performance metrics.
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class MemoryMetrics(BaseModel):
    """Memory usage metrics."""

    total_bytes: int = Field(..., description="Total memory in bytes")
    used_bytes: int = Field(..., description="Used memory in bytes")
    available_bytes: int = Field(..., description="Available memory in bytes")
    usage_percent: float = Field(..., description="Usage percentage")
    swap_total_bytes: Optional[int] = Field(default=None, description="Total swap space")
    swap_used_bytes: Optional[int] = Field(default=None, description="Used swap space")
    swap_percent: Optional[float] = Field(default=None, description="Swap usage percentage")
    status: str = Field(..., description="Status (healthy, warning, critical)")
    recommendations: List[str] = Field(default_factory=list)


class CpuMetrics(BaseModel):
    """CPU usage metrics."""

    usage_percent: float = Field(..., description="Overall CPU usage percentage")
    user_percent: float = Field(..., description="User space CPU percentage")
    system_percent: float = Field(..., description="System/kernel CPU percentage")
    idle_percent: float = Field(..., description="Idle CPU percentage")
    iowait_percent: Optional[float] = Field(default=None, description="I/O wait percentage")
    core_count: int = Field(..., description="Number of CPU cores")
    per_core_usage: Optional[List[float]] = Field(default=None, description="Per-core usage")
    load_average_1m: Optional[float] = Field(default=None, description="1-minute load average")
    load_average_5m: Optional[float] = Field(default=None, description="5-minute load average")
    load_average_15m: Optional[float] = Field(default=None, description="15-minute load average")
    status: str = Field(..., description="Status (healthy, warning, critical)")
    recommendations: List[str] = Field(default_factory=list)


class IoMetrics(BaseModel):
    """I/O performance metrics."""

    read_bytes_per_sec: float = Field(..., description="Read throughput in bytes/sec")
    write_bytes_per_sec: float = Field(..., description="Write throughput in bytes/sec")
    read_ops_per_sec: float = Field(..., description="Read operations per second")
    write_ops_per_sec: float = Field(..., description="Write operations per second")
    total_iops: float = Field(..., description="Total IOPS")
    total_throughput_mbps: float = Field(..., description="Total throughput in MB/s")
    avg_read_latency_ms: Optional[float] = Field(default=None, description="Avg read latency")
    avg_write_latency_ms: Optional[float] = Field(default=None, description="Avg write latency")
    queue_depth: Optional[float] = Field(default=None, description="Average queue depth")
    utilization_percent: Optional[float] = Field(default=None, description="Disk utilization")
    status: str = Field(..., description="Status (healthy, warning, critical)")
    recommendations: List[str] = Field(default_factory=list)


class ResourceUtilization(BaseModel):
    """Combined resource utilization summary."""

    memory: MemoryMetrics = Field(..., description="Memory metrics")
    cpu: CpuMetrics = Field(..., description="CPU metrics")
    io: Optional[IoMetrics] = Field(default=None, description="I/O metrics")
    overall_health_score: float = Field(..., ge=0, le=100, description="Overall score")
    overall_status: str = Field(..., description="Overall status")
    bottleneck: Optional[str] = Field(default=None, description="Primary bottleneck")
    recommendations: List[str] = Field(default_factory=list)
