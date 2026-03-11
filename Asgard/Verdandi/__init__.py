"""
Verdandi - Runtime Performance Metrics

Named after the Norse Norn who measures the present moment at the Well of Urd.
Like its namesake who weaves the threads of fate in the now, Verdandi measures
and calculates runtime performance metrics as they happen.

Subpackages:
- Web: Core Web Vitals, navigation timing, resource timing
- Database: Query performance, throughput, connection metrics
- System: Memory, CPU, I/O performance metrics
- Network: Latency, bandwidth, DNS timing
- Cache: Hit ratios, eviction rates, fill rates
- Analysis: Percentiles, Apdex scores, SLA compliance, trending
- APM: Application Performance Monitoring with span/trace analysis
- SLO: Service Level Objective management and error budgets
- Anomaly: Anomaly detection and baseline comparison
- Tracing: Distributed trace parsing and critical path analysis
- Trend: Performance trend analysis and forecasting

Usage:
    python -m Verdandi --help
    python -m Verdandi web vitals <data_file>
    python -m Verdandi apm analyze <traces>
    python -m Verdandi slo calculate <metrics>
    python -m Verdandi anomaly detect <data>
    python -m Verdandi trend analyze <metrics>

Programmatic Usage:
    from Asgard.Verdandi.Web import CoreWebVitalsCalculator
    from Asgard.Verdandi.Analysis import PercentileCalculator, ApdexCalculator
    from Asgard.Verdandi.APM import SpanAnalyzer, TraceAggregator
    from Asgard.Verdandi.SLO import ErrorBudgetCalculator, BurnRateAnalyzer
    from Asgard.Verdandi.Anomaly import StatisticalDetector, RegressionDetector
    from Asgard.Verdandi.Trend import TrendAnalyzer, ForecastCalculator

    # Calculate Core Web Vitals ratings
    calculator = CoreWebVitalsCalculator()
    vitals = calculator.calculate(lcp_ms=2100, fid_ms=50, cls=0.05)
    print(f"LCP Rating: {vitals.lcp_rating}")

    # Calculate percentiles
    percentile_calc = PercentileCalculator()
    p99 = percentile_calc.calculate_percentile(response_times, 99)
    print(f"P99 Response Time: {p99}ms")
"""

__version__ = "2.0.0"
__author__ = "Asgard Contributors"

PACKAGE_INFO = {
    "name": "Verdandi",
    "version": __version__,
    "description": "Runtime performance metrics package",
    "author": __author__,
    "sub_packages": [
        "Web - Core Web Vitals, navigation timing, resource timing",
        "Database - Query performance, throughput, connection metrics",
        "System - Memory, CPU, I/O performance metrics",
        "Network - Latency, bandwidth, DNS timing",
        "Cache - Hit ratios, eviction rates, fill rates",
        "Analysis - Percentiles, Apdex scores, SLA compliance, trending",
        "APM - Application Performance Monitoring with span/trace analysis",
        "SLO - Service Level Objective management and error budgets",
        "Anomaly - Anomaly detection and baseline comparison",
        "Tracing - Distributed trace parsing and critical path analysis",
        "Trend - Performance trend analysis and forecasting",
    ]
}

from . import Web
from . import Database
from . import System
from . import Network
from . import Cache
from . import Analysis
from . import APM
from . import SLO
from . import Anomaly
from . import Tracing
from . import Trend

from Asgard.Verdandi.Analysis import (
    ApdexCalculator,
    ApdexConfig,
    ApdexResult,
    PercentileCalculator,
    PercentileResult,
    SLAChecker,
    SLAConfig,
    SLAResult,
)

from Asgard.Verdandi.Web import (
    CoreWebVitalsCalculator,
    WebVitalsResult,
    VitalsRating,
)

from Asgard.Verdandi.APM import (
    SpanAnalyzer,
    TraceAggregator,
    ServiceMapBuilder,
)

from Asgard.Verdandi.SLO import (
    ErrorBudgetCalculator,
    SLITracker,
    BurnRateAnalyzer,
)

from Asgard.Verdandi.Anomaly import (
    StatisticalDetector,
    BaselineComparator,
    RegressionDetector,
)

from Asgard.Verdandi.Tracing import (
    TraceParser,
    CriticalPathAnalyzer,
)

from Asgard.Verdandi.Trend import (
    TrendAnalyzer,
    ForecastCalculator,
)

__all__ = [
    # Subpackages
    "Web",
    "Database",
    "System",
    "Network",
    "Cache",
    "Analysis",
    "APM",
    "SLO",
    "Anomaly",
    "Tracing",
    "Trend",
    # Analysis
    "ApdexCalculator",
    "ApdexConfig",
    "ApdexResult",
    "PercentileCalculator",
    "PercentileResult",
    "SLAChecker",
    "SLAConfig",
    "SLAResult",
    # Web
    "CoreWebVitalsCalculator",
    "WebVitalsResult",
    "VitalsRating",
    # APM
    "SpanAnalyzer",
    "TraceAggregator",
    "ServiceMapBuilder",
    # SLO
    "ErrorBudgetCalculator",
    "SLITracker",
    "BurnRateAnalyzer",
    # Anomaly
    "StatisticalDetector",
    "BaselineComparator",
    "RegressionDetector",
    # Tracing
    "TraceParser",
    "CriticalPathAnalyzer",
    # Trend
    "TrendAnalyzer",
    "ForecastCalculator",
]
