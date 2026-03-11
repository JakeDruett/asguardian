"""
Service Map Builder Service

Builds service dependency maps from distributed traces.
"""

from typing import Dict, List, Optional, Sequence, Set, Tuple

from Asgard.Verdandi.APM.models.apm_models import (
    ServiceDependency,
    ServiceMap,
    Span,
    Trace,
)


class ServiceMapBuilder:
    """
    Builder for service dependency maps.

    Analyzes traces to identify service relationships and builds
    a dependency graph showing how services interact.

    Example:
        builder = ServiceMapBuilder()
        service_map = builder.build(traces)
        for dep in service_map.dependencies:
            print(f"{dep.source_service} -> {dep.target_service}")
    """

    def __init__(self):
        """Initialize the service map builder."""
        pass

    def build(
        self,
        traces: Sequence[Trace],
    ) -> ServiceMap:
        """
        Build a service dependency map from traces.

        Args:
            traces: List of traces to analyze

        Returns:
            ServiceMap with services and their dependencies
        """
        if not traces:
            return ServiceMap()

        # Collect all spans
        all_spans: List[Span] = []
        for trace in traces:
            all_spans.extend(trace.spans)

        return self.build_from_spans(all_spans)

    def build_from_spans(
        self,
        spans: Sequence[Span],
    ) -> ServiceMap:
        """
        Build a service dependency map directly from spans.

        Args:
            spans: List of spans to analyze

        Returns:
            ServiceMap with services and their dependencies
        """
        if not spans:
            return ServiceMap()

        # Build span lookup
        span_lookup: Dict[str, Span] = {}
        for span in spans:
            span_lookup[span.span_id] = span

        # Collect all services
        services: Set[str] = set()
        for span in spans:
            services.add(span.service_name)

        # Find dependencies by looking at parent-child relationships
        # across services
        dependency_stats: Dict[Tuple[str, str], Dict] = {}

        for span in spans:
            if span.parent_span_id and span.parent_span_id in span_lookup:
                parent_span = span_lookup[span.parent_span_id]

                # Only count as dependency if services are different
                if parent_span.service_name != span.service_name:
                    key = (parent_span.service_name, span.service_name)

                    if key not in dependency_stats:
                        dependency_stats[key] = {
                            "call_count": 0,
                            "error_count": 0,
                            "latencies": [],
                        }

                    dependency_stats[key]["call_count"] += 1
                    if span.has_error:
                        dependency_stats[key]["error_count"] += 1
                    dependency_stats[key]["latencies"].append(span.duration_ms)

        # Build dependency objects
        dependencies = []
        for (source, target), stats in dependency_stats.items():
            latencies = stats["latencies"]
            avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
            p99_latency = self._percentile(sorted(latencies), 99) if latencies else 0.0

            dependencies.append(
                ServiceDependency(
                    source_service=source,
                    target_service=target,
                    call_count=stats["call_count"],
                    error_count=stats["error_count"],
                    avg_latency_ms=avg_latency,
                    p99_latency_ms=p99_latency,
                )
            )

        # Identify root and leaf services
        callers = set(d.source_service for d in dependencies)
        callees = set(d.target_service for d in dependencies)

        root_services = list(services - callees)  # Services with no inbound calls
        leaf_services = list(services - callers)  # Services with no outbound calls

        return ServiceMap(
            services=sorted(list(services)),
            dependencies=dependencies,
            root_services=sorted(root_services),
            leaf_services=sorted(leaf_services),
            edge_count=len(dependencies),
            service_count=len(services),
        )

    def find_critical_path(
        self,
        trace: Trace,
    ) -> List[Span]:
        """
        Find the critical path in a trace.

        The critical path is the sequence of spans that contribute most
        to the total trace duration.

        Args:
            trace: The trace to analyze

        Returns:
            List of spans forming the critical path
        """
        if not trace.spans:
            return []

        # Build parent-child map
        span_lookup: Dict[str, Span] = {}
        children: Dict[str, List[Span]] = {}

        for span in trace.spans:
            span_lookup[span.span_id] = span
            parent_id = span.parent_span_id or ""
            if parent_id not in children:
                children[parent_id] = []
            children[parent_id].append(span)

        # Find root span
        root_span = trace.root_span
        if root_span is None:
            # Find span with no parent
            for span in trace.spans:
                if span.parent_span_id is None:
                    root_span = span
                    break

        if root_span is None:
            return []

        # Build critical path by following longest children
        critical_path = [root_span]
        current_span = root_span

        while current_span.span_id in children:
            child_spans = children[current_span.span_id]
            if not child_spans:
                break

            # Select the child with the longest duration
            longest_child = max(child_spans, key=lambda s: s.duration_ms)
            critical_path.append(longest_child)
            current_span = longest_child

        return critical_path

    def detect_cycles(
        self,
        service_map: ServiceMap,
    ) -> List[List[str]]:
        """
        Detect cycles in the service dependency graph.

        Args:
            service_map: The service map to analyze

        Returns:
            List of cycles (each cycle is a list of service names)
        """
        # Build adjacency list
        graph: Dict[str, List[str]] = {s: [] for s in service_map.services}
        for dep in service_map.dependencies:
            graph[dep.source_service].append(dep.target_service)

        cycles = []
        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def dfs(node: str, path: List[str]) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    dfs(neighbor, path)
                elif neighbor in rec_stack:
                    # Found a cycle
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    cycles.append(cycle)

            path.pop()
            rec_stack.remove(node)

        for service in service_map.services:
            if service not in visited:
                dfs(service, [])

        return cycles

    def get_downstream_services(
        self,
        service_map: ServiceMap,
        service_name: str,
    ) -> Set[str]:
        """
        Get all services that depend on the given service (downstream).

        Args:
            service_map: The service map to analyze
            service_name: The service to find dependents for

        Returns:
            Set of service names that are downstream
        """
        # Build reverse adjacency list
        reverse_graph: Dict[str, List[str]] = {s: [] for s in service_map.services}
        for dep in service_map.dependencies:
            reverse_graph[dep.target_service].append(dep.source_service)

        # BFS to find all downstream services
        downstream: Set[str] = set()
        queue = [service_name]

        while queue:
            current = queue.pop(0)
            for dependent in reverse_graph.get(current, []):
                if dependent not in downstream:
                    downstream.add(dependent)
                    queue.append(dependent)

        return downstream

    def get_upstream_services(
        self,
        service_map: ServiceMap,
        service_name: str,
    ) -> Set[str]:
        """
        Get all services that the given service depends on (upstream).

        Args:
            service_map: The service map to analyze
            service_name: The service to find dependencies for

        Returns:
            Set of service names that are upstream
        """
        # Build adjacency list
        graph: Dict[str, List[str]] = {s: [] for s in service_map.services}
        for dep in service_map.dependencies:
            graph[dep.source_service].append(dep.target_service)

        # BFS to find all upstream services
        upstream: Set[str] = set()
        queue = [service_name]

        while queue:
            current = queue.pop(0)
            for dependency in graph.get(current, []):
                if dependency not in upstream:
                    upstream.add(dependency)
                    queue.append(dependency)

        return upstream

    def calculate_service_depth(
        self,
        service_map: ServiceMap,
    ) -> Dict[str, int]:
        """
        Calculate the depth of each service in the call hierarchy.

        Root services have depth 0, their direct callees have depth 1, etc.

        Args:
            service_map: The service map to analyze

        Returns:
            Dictionary mapping service name to depth
        """
        # Build adjacency list
        graph: Dict[str, List[str]] = {s: [] for s in service_map.services}
        for dep in service_map.dependencies:
            graph[dep.source_service].append(dep.target_service)

        depths: Dict[str, int] = {}

        # Start BFS from root services
        queue: List[Tuple[str, int]] = [(s, 0) for s in service_map.root_services]

        while queue:
            service, depth = queue.pop(0)

            # Keep the minimum depth if already visited
            if service in depths:
                depths[service] = min(depths[service], depth)
            else:
                depths[service] = depth
                for callee in graph.get(service, []):
                    queue.append((callee, depth + 1))

        # Handle services not reachable from roots
        for service in service_map.services:
            if service not in depths:
                depths[service] = -1  # Unreachable

        return depths

    def _percentile(
        self,
        sorted_values: List[float],
        percentile: float,
    ) -> float:
        """Calculate percentile from sorted values."""
        if not sorted_values:
            return 0.0

        n = len(sorted_values)
        if n == 1:
            return sorted_values[0]

        rank = (percentile / 100) * (n - 1)
        lower_idx = int(rank)
        upper_idx = min(lower_idx + 1, n - 1)
        fraction = rank - lower_idx

        return sorted_values[lower_idx] + fraction * (
            sorted_values[upper_idx] - sorted_values[lower_idx]
        )
