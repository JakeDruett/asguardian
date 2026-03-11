"""
Verdandi Network - Network Performance Metrics

This module provides network performance metric calculations including:
- Latency measurements and analysis
- Bandwidth utilization
- DNS timing metrics
- Connection timing

Usage:
    from Asgard.Verdandi.Network import LatencyCalculator

    calc = LatencyCalculator()
    result = calc.analyze([10, 15, 12, 20, 18])
    print(f"P99 Latency: {result.p99_ms}ms")
"""

__version__ = "1.0.0"
__author__ = "Asgard Contributors"

from Asgard.Verdandi.Network.models.network_models import (
    LatencyMetrics,
    BandwidthMetrics,
    DnsMetrics,
    ConnectionMetrics,
)
from Asgard.Verdandi.Network.services.latency_calculator import LatencyCalculator
from Asgard.Verdandi.Network.services.bandwidth_calculator import BandwidthCalculator
from Asgard.Verdandi.Network.services.dns_calculator import DnsCalculator

__all__ = [
    "BandwidthCalculator",
    "BandwidthMetrics",
    "ConnectionMetrics",
    "DnsCalculator",
    "DnsMetrics",
    "LatencyCalculator",
    "LatencyMetrics",
]
