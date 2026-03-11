"""
Database Performance Models

Pydantic models for database performance metrics.
"""

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class QueryType(str, Enum):
    """Database query type."""

    SELECT = "select"
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"
    OTHER = "other"


class QueryMetricsInput(BaseModel):
    """Input data for query metrics analysis."""

    query_id: Optional[str] = Field(default=None, description="Query identifier")
    query_type: QueryType = Field(..., description="Type of query")
    execution_time_ms: float = Field(..., description="Query execution time in ms")
    rows_examined: int = Field(default=0, description="Number of rows examined")
    rows_affected: int = Field(default=0, description="Number of rows affected")
    used_index: bool = Field(default=True, description="Whether query used an index")
    timestamp: Optional[str] = Field(default=None, description="Query timestamp")


class QueryMetricsResult(BaseModel):
    """Result of query metrics analysis."""

    total_queries: int = Field(..., description="Total queries analyzed")
    average_execution_ms: float = Field(..., description="Average execution time")
    median_execution_ms: float = Field(..., description="Median execution time")
    p95_execution_ms: float = Field(..., description="95th percentile execution time")
    p99_execution_ms: float = Field(..., description="99th percentile execution time")
    max_execution_ms: float = Field(..., description="Maximum execution time")
    min_execution_ms: float = Field(..., description="Minimum execution time")
    by_type: Dict[str, Dict[str, float]] = Field(
        default_factory=dict,
        description="Breakdown by query type",
    )
    slow_query_count: int = Field(..., description="Count of slow queries")
    slow_query_threshold_ms: float = Field(..., description="Threshold for slow queries")
    index_usage_rate: float = Field(..., description="Percentage of queries using indexes")
    scan_rate: float = Field(..., description="Avg rows examined per row affected")
    recommendations: List[str] = Field(
        default_factory=list,
        description="Performance recommendations",
    )


class ConnectionPoolMetrics(BaseModel):
    """Connection pool metrics."""

    pool_size: int = Field(..., description="Total pool size")
    active_connections: int = Field(..., description="Currently active connections")
    idle_connections: int = Field(..., description="Idle connections")
    waiting_requests: int = Field(..., description="Requests waiting for connection")
    utilization_percent: float = Field(..., description="Pool utilization percentage")
    average_wait_time_ms: float = Field(..., description="Average wait time for connection")
    max_wait_time_ms: float = Field(..., description="Maximum wait time observed")
    connection_errors: int = Field(default=0, description="Connection error count")
    timeout_count: int = Field(default=0, description="Connection timeout count")


class TransactionMetrics(BaseModel):
    """Transaction performance metrics."""

    total_transactions: int = Field(..., description="Total transactions")
    committed: int = Field(..., description="Successfully committed")
    rolled_back: int = Field(..., description="Rolled back")
    average_duration_ms: float = Field(..., description="Average transaction duration")
    p95_duration_ms: float = Field(..., description="95th percentile duration")
    deadlock_count: int = Field(default=0, description="Deadlock occurrences")
    lock_wait_time_ms: float = Field(default=0, description="Total lock wait time")
    commit_rate: float = Field(..., description="Commit success rate percentage")


class DatabaseHealthResult(BaseModel):
    """Overall database health assessment."""

    health_score: float = Field(..., ge=0, le=100, description="Health score 0-100")
    status: str = Field(..., description="Overall status (healthy, degraded, critical)")
    query_metrics: Optional[QueryMetricsResult] = Field(default=None)
    connection_metrics: Optional[ConnectionPoolMetrics] = Field(default=None)
    transaction_metrics: Optional[TransactionMetrics] = Field(default=None)
    throughput_qps: float = Field(..., description="Queries per second")
    error_rate: float = Field(..., description="Error rate percentage")
    recommendations: List[str] = Field(
        default_factory=list,
        description="Health recommendations",
    )
