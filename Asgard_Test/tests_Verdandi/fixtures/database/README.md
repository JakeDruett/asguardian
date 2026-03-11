# Database Performance Test Fixtures

This directory contains database performance metrics for testing Verdandi's database analysis functionality.

## Files

| File | Description | Use Case |
|------|-------------|----------|
| `query_timings.json` | Individual query execution times | Query performance analysis |
| `connection_pool.json` | Connection pool metrics over time | Pool health monitoring |
| `slow_queries.json` | Slow query log with analysis | Performance optimization |

## Fixture Details

### query_timings.json

Sample of 8 queries with varying characteristics:

| Query Type | Count | Performance Pattern |
|------------|-------|---------------------|
| SELECT | 5 | Mix of indexed and full scans |
| INSERT | 1 | Fast single-row insert |
| UPDATE | 1 | Indexed update |
| DELETE | 1 | Indexed multi-row delete |

**Key Metrics:**
- Average execution: 273.85ms
- Median execution: 13.75ms
- P95 execution: 1050.35ms
- Slow query count: 2 (threshold: 500ms)
- Index usage rate: 62.5%

**Slow Queries Identified:**
1. Full table scan on products with LIKE query (850ms)
2. Subquery with inefficient nested SELECT (1250ms)

### connection_pool.json

Pool metrics over 1 hour with 60-second intervals:

**Configuration:**
- Pool size: 100 connections
- Min connections: 10
- Connection timeout: 5000ms
- Idle timeout: 300000ms

**Observed Behavior:**
- Peak utilization: 100%
- Saturation events: 4 occurrences
- Total saturation time: 720 seconds
- Maximum wait time: 4850ms
- Connection errors: 2
- Timeouts: 5

**Expected Status:** Warning (pool saturation detected)

### slow_queries.json

24-hour slow query log with 45 slow queries:

**Top Slow Query Patterns:**
1. Date range ORDER queries on orders table
2. JOIN with GROUP BY on products/reviews
3. Full table scan on audit_log
4. Lock contention on products UPDATE
5. Cleanup DELETE on sessions table

**Analysis Includes:**
- Query execution plans
- Missing index identification
- Lock wait time analysis
- Table-level aggregation
- Pattern categorization

## Usage Examples

### Query Metrics Analysis

```python
from Asgard.Verdandi.Database.services.query_metrics import QueryMetricsAnalyzer
import json

analyzer = QueryMetricsAnalyzer()

with open("query_timings.json") as f:
    data = json.load(f)

result = analyzer.analyze(data["queries"])

print(f"Average execution: {result.average_execution_ms}ms")
print(f"P95 execution: {result.p95_execution_ms}ms")
print(f"Slow query count: {result.slow_query_count}")
print(f"Index usage rate: {result.index_usage_rate}")

for rec in result.recommendations:
    print(f"- {rec}")
```

### Connection Pool Monitoring

```python
from Asgard.Verdandi.Database.services.connection_analyzer import ConnectionPoolAnalyzer

analyzer = ConnectionPoolAnalyzer()

with open("connection_pool.json") as f:
    data = json.load(f)

metrics = analyzer.analyze(data)

print(f"Utilization: {metrics.utilization_percent}%")
print(f"Average wait time: {metrics.average_wait_time_ms}ms")
print(f"Connection errors: {metrics.connection_errors}")

if metrics.waiting_requests > 0:
    print("Warning: Requests waiting for connections")
```

### Slow Query Analysis

```python
from Asgard.Verdandi.Database.services.query_metrics import SlowQueryAnalyzer

analyzer = SlowQueryAnalyzer()

with open("slow_queries.json") as f:
    data = json.load(f)

for query in data["slow_queries"][:5]:
    analysis = analyzer.analyze_query(query)
    print(f"Query: {query['query_hash']}")
    print(f"  Avg time: {query['avg_time_ms']}ms")
    print(f"  Missing indexes: {query.get('missing_indexes', [])}")
    print(f"  Recommendation: {analysis.recommendation}")
```

## Testing Scenarios

1. **Query Performance Metrics**
   - Percentile calculations (p50, p75, p90, p95, p99)
   - Average vs median comparison
   - Query type breakdown

2. **Index Analysis**
   - Index usage detection
   - Missing index identification
   - Scan efficiency calculation

3. **Connection Pool Health**
   - Utilization thresholds
   - Wait time analysis
   - Saturation detection
   - Error rate calculation

4. **Slow Query Detection**
   - Threshold-based identification
   - Pattern recognition
   - Root cause analysis
   - Optimization recommendations

5. **Health Scoring**
   - Overall database health score
   - Component-level scores
   - Status determination (healthy/warning/critical)

## Health Status Thresholds

| Metric | Healthy | Warning | Critical |
|--------|---------|---------|----------|
| Pool Utilization | < 70% | 70-90% | > 90% |
| Avg Wait Time | < 100ms | 100-500ms | > 500ms |
| Slow Query Rate | < 1% | 1-5% | > 5% |
| Index Usage | > 90% | 70-90% | < 70% |
| Error Rate | < 0.1% | 0.1-1% | > 1% |
