"""
Cache Performance Models

Pydantic models for cache performance metrics.
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class CacheMetrics(BaseModel):
    """Cache performance metrics."""

    total_requests: int = Field(..., description="Total cache requests")
    hits: int = Field(..., description="Cache hits")
    misses: int = Field(..., description="Cache misses")
    hit_rate_percent: float = Field(..., description="Hit rate percentage")
    miss_rate_percent: float = Field(..., description="Miss rate percentage")
    avg_hit_latency_ms: Optional[float] = Field(default=None, description="Avg hit latency")
    avg_miss_latency_ms: Optional[float] = Field(default=None, description="Avg miss latency")
    latency_savings_ms: Optional[float] = Field(default=None, description="Latency saved by cache")
    size_bytes: Optional[int] = Field(default=None, description="Current cache size")
    max_size_bytes: Optional[int] = Field(default=None, description="Maximum cache size")
    fill_percent: Optional[float] = Field(default=None, description="Cache fill percentage")
    status: str = Field(..., description="Status (excellent, good, fair, poor)")
    recommendations: List[str] = Field(default_factory=list)


class EvictionMetrics(BaseModel):
    """Cache eviction metrics."""

    total_evictions: int = Field(..., description="Total evictions")
    eviction_rate_per_sec: float = Field(..., description="Evictions per second")
    eviction_percent: float = Field(..., description="Eviction percentage of total ops")
    by_reason: Dict[str, int] = Field(
        default_factory=dict,
        description="Evictions by reason (ttl, lru, size, manual)",
    )
    avg_entry_age_seconds: Optional[float] = Field(
        default=None,
        description="Avg age of evicted entries",
    )
    premature_evictions: int = Field(
        default=0,
        description="Entries evicted before natural expiry",
    )
    status: str = Field(..., description="Status")
    recommendations: List[str] = Field(default_factory=list)


class CacheEfficiency(BaseModel):
    """Overall cache efficiency assessment."""

    efficiency_score: float = Field(..., ge=0, le=100, description="Efficiency score 0-100")
    hit_rate_percent: float = Field(..., description="Hit rate")
    memory_efficiency_percent: float = Field(..., description="Memory utilization efficiency")
    latency_improvement_factor: Optional[float] = Field(
        default=None,
        description="How much faster hits are vs misses",
    )
    cost_savings_percent: Optional[float] = Field(
        default=None,
        description="Estimated cost savings from caching",
    )
    optimal_size_bytes: Optional[int] = Field(
        default=None,
        description="Recommended cache size",
    )
    status: str = Field(..., description="Overall status")
    recommendations: List[str] = Field(default_factory=list)
