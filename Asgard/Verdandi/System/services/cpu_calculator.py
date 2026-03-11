"""
CPU Metrics Calculator

Calculates CPU usage and utilization metrics.
"""

from typing import List, Optional

from Asgard.Verdandi.System.models.system_models import CpuMetrics


class CpuMetricsCalculator:
    """
    Calculator for CPU usage metrics.

    Analyzes CPU utilization and provides status assessments.

    Example:
        calc = CpuMetricsCalculator()
        result = calc.analyze(user_percent=45, system_percent=15, idle_percent=40)
        print(f"Total Usage: {result.usage_percent}%")
    """

    WARNING_THRESHOLD = 80.0
    CRITICAL_THRESHOLD = 95.0

    def analyze(
        self,
        user_percent: float,
        system_percent: float,
        idle_percent: float,
        core_count: int = 1,
        iowait_percent: Optional[float] = None,
        per_core_usage: Optional[List[float]] = None,
        load_average_1m: Optional[float] = None,
        load_average_5m: Optional[float] = None,
        load_average_15m: Optional[float] = None,
    ) -> CpuMetrics:
        """
        Analyze CPU usage.

        Args:
            user_percent: User space CPU percentage
            system_percent: System/kernel CPU percentage
            idle_percent: Idle CPU percentage
            core_count: Number of CPU cores
            iowait_percent: I/O wait percentage
            per_core_usage: Per-core usage percentages
            load_average_1m: 1-minute load average
            load_average_5m: 5-minute load average
            load_average_15m: 15-minute load average

        Returns:
            CpuMetrics with analysis
        """
        usage_percent = 100 - idle_percent

        status = self._determine_status(
            usage_percent, iowait_percent, load_average_1m, core_count
        )
        recommendations = self._generate_recommendations(
            usage_percent, iowait_percent, load_average_1m, core_count
        )

        return CpuMetrics(
            usage_percent=round(usage_percent, 2),
            user_percent=round(user_percent, 2),
            system_percent=round(system_percent, 2),
            idle_percent=round(idle_percent, 2),
            iowait_percent=round(iowait_percent, 2) if iowait_percent else None,
            core_count=core_count,
            per_core_usage=per_core_usage,
            load_average_1m=load_average_1m,
            load_average_5m=load_average_5m,
            load_average_15m=load_average_15m,
            status=status,
            recommendations=recommendations,
        )

    def calculate_load_ratio(
        self,
        load_average: float,
        core_count: int,
    ) -> float:
        """
        Calculate load ratio (load average / core count).

        A ratio > 1.0 indicates the system is overloaded.

        Args:
            load_average: Current load average
            core_count: Number of CPU cores

        Returns:
            Load ratio
        """
        if core_count <= 0:
            return 0.0
        return round(load_average / core_count, 2)

    def _determine_status(
        self,
        usage_percent: float,
        iowait_percent: Optional[float],
        load_average: Optional[float],
        core_count: int,
    ) -> str:
        """Determine CPU status."""
        if usage_percent >= self.CRITICAL_THRESHOLD:
            return "critical"
        if usage_percent >= self.WARNING_THRESHOLD:
            return "warning"

        if load_average and core_count > 0:
            load_ratio = load_average / core_count
            if load_ratio > 2.0:
                return "critical"
            if load_ratio > 1.0:
                return "warning"

        if iowait_percent and iowait_percent > 20:
            return "warning"

        return "healthy"

    def _generate_recommendations(
        self,
        usage_percent: float,
        iowait_percent: Optional[float],
        load_average: Optional[float],
        core_count: int,
    ) -> List[str]:
        """Generate CPU recommendations."""
        recommendations = []

        if usage_percent >= self.CRITICAL_THRESHOLD:
            recommendations.append(
                "Critical: CPU usage is very high. Consider scaling up "
                "or optimizing workload."
            )
        elif usage_percent >= self.WARNING_THRESHOLD:
            recommendations.append(
                f"CPU usage is elevated ({usage_percent:.1f}%). "
                "Monitor for potential bottlenecks."
            )

        if iowait_percent and iowait_percent > 20:
            recommendations.append(
                f"High I/O wait ({iowait_percent:.1f}%). "
                "Consider optimizing disk I/O or adding faster storage."
            )

        if load_average and core_count > 0:
            load_ratio = load_average / core_count
            if load_ratio > 1.0:
                recommendations.append(
                    f"Load average ({load_average:.2f}) exceeds core count ({core_count}). "
                    "System may be overloaded."
                )

        return recommendations
