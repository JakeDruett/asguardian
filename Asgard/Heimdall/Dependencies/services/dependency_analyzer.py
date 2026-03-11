"""
Heimdall Dependency Analyzer Service

Unified analyzer that combines all dependency analysis features.
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional

from Asgard.Heimdall.Dependencies.models.dependency_models import (
    CircularDependency,
    DependencyConfig,
    DependencyReport,
    DependencySeverity,
    ModularityMetrics,
    ModuleDependencies,
)
from Asgard.Heimdall.Dependencies.services.import_analyzer import ImportAnalyzer
from Asgard.Heimdall.Dependencies.services.graph_builder import GraphBuilder
from Asgard.Heimdall.Dependencies.services.cycle_detector import CycleDetector
from Asgard.Heimdall.Dependencies.services.modularity_analyzer import ModularityAnalyzer


class DependencyAnalyzer:
    """
    Unified dependency analyzer combining all analysis features.

    Provides comprehensive dependency analysis including:
    - Import mapping
    - Dependency graph construction
    - Circular dependency detection
    - Modularity analysis
    """

    def __init__(self, config: Optional[DependencyConfig] = None):
        """Initialize the dependency analyzer."""
        self.config = config or DependencyConfig()

        # Initialize sub-analyzers
        self.import_analyzer = ImportAnalyzer(self.config)
        self.graph_builder = GraphBuilder(self.config)
        self.cycle_detector = CycleDetector(self.config)
        self.modularity_analyzer = ModularityAnalyzer(self.config)

    def analyze(self, scan_path: Optional[Path] = None) -> DependencyReport:
        """
        Perform complete dependency analysis.

        Args:
            scan_path: Root path to scan

        Returns:
            DependencyReport with all findings
        """
        path = scan_path or self.config.scan_path
        path = Path(path).resolve()

        if not path.exists():
            raise FileNotFoundError(f"Scan path does not exist: {path}")

        start_time = time.time()

        # Analyze imports
        modules = self.import_analyzer.analyze(path)

        # Detect cycles
        cycles = self.cycle_detector.detect(path)

        # Analyze modularity
        modularity = self.modularity_analyzer.analyze(path)

        # Build reverse graph for afferent coupling
        graph = {m.module_name: m.all_dependencies for m in modules}
        reverse = self._build_reverse_graph(graph)

        # Update modules with afferent coupling
        for module in modules:
            module.afferent_coupling = len(reverse.get(module.module_name, set()))
            if module.afferent_coupling + module.efferent_coupling > 0:
                module.instability = module.efferent_coupling / (
                    module.afferent_coupling + module.efferent_coupling
                )

        # Build report
        report = DependencyReport(
            scan_path=str(path),
        )

        # Add modules
        for module in modules:
            report.add_module(module)

            # Check for high coupling
            if module.efferent_coupling > self.config.max_dependencies:
                module.severity = DependencySeverity.HIGH
                report.high_coupling_modules.append(module)
            elif module.afferent_coupling > self.config.max_dependents:
                module.severity = DependencySeverity.MODERATE
                report.high_coupling_modules.append(module)

        # Add cycles
        for cycle in cycles:
            report.add_cycle(cycle)

        # Add modularity
        report.modularity = modularity

        report.scan_duration_seconds = time.time() - start_time

        return report

    def _build_reverse_graph(
        self, graph: Dict[str, set]
    ) -> Dict[str, set]:
        """Build a reverse dependency graph."""
        reverse = {module: set() for module in graph}

        for module, deps in graph.items():
            for dep in deps:
                if dep in reverse:
                    reverse[dep].add(module)

        return reverse

    def analyze_file(self, file_path: Path) -> Optional[ModuleDependencies]:
        """
        Analyze dependencies for a single file.

        Args:
            file_path: Path to the Python file

        Returns:
            ModuleDependencies for the file
        """
        return self.import_analyzer.analyze_file(file_path)

    def get_cycles(self, scan_path: Optional[Path] = None) -> List[CircularDependency]:
        """
        Get circular dependencies only.

        Args:
            scan_path: Root path to scan

        Returns:
            List of circular dependencies
        """
        return self.cycle_detector.detect(scan_path)

    def has_cycles(self, scan_path: Optional[Path] = None) -> bool:
        """
        Quick check for circular dependencies.

        Args:
            scan_path: Root path to scan

        Returns:
            True if cycles exist
        """
        return self.cycle_detector.has_cycles(scan_path)

    def get_modularity(self, scan_path: Optional[Path] = None) -> ModularityMetrics:
        """
        Get modularity metrics only.

        Args:
            scan_path: Root path to scan

        Returns:
            ModularityMetrics
        """
        return self.modularity_analyzer.analyze(scan_path)

    def generate_report(
        self, result: DependencyReport, format: str = "text", direction: str = "LR"
    ) -> str:
        """
        Generate a formatted report.

        Args:
            result: DependencyReport to format
            format: Output format ("text", "json", "markdown", "mermaid", "graphviz")
            direction: Graph direction for mermaid/graphviz formats (LR, TB, RL, BT)

        Returns:
            Formatted report string
        """
        if format == "json":
            return self._generate_json_report(result)
        elif format == "markdown":
            return self._generate_markdown_report(result)
        elif format == "mermaid":
            return self._generate_mermaid_report(result, direction)
        elif format == "graphviz":
            return self._generate_graphviz_report(result, direction)
        else:
            return self._generate_text_report(result)

    def _collect_violation_sets(
        self, result: DependencyReport
    ) -> tuple:
        """
        Collect sets of violation nodes and edges for graph highlighting.

        Returns:
            Tuple of (cycle_nodes, high_coupling_nodes, cycle_edges) where:
            - cycle_nodes: set of module names involved in any cycle
            - high_coupling_nodes: set of module names with high coupling
            - cycle_edges: set of (source, target) tuples that are part of cycles
        """
        cycle_nodes: set = set()
        cycle_edges: set = set()
        for cycle in result.circular_dependencies:
            modules_in_cycle = cycle.cycle
            for module in modules_in_cycle:
                cycle_nodes.add(module)
            for i in range(len(modules_in_cycle)):
                src = modules_in_cycle[i]
                tgt = modules_in_cycle[(i + 1) % len(modules_in_cycle)]
                cycle_edges.add((src, tgt))

        high_coupling_nodes: set = set()
        for module in result.high_coupling_modules:
            high_coupling_nodes.add(module.module_name)

        return cycle_nodes, high_coupling_nodes, cycle_edges

    def _generate_mermaid_report(self, result: DependencyReport, direction: str = "LR") -> str:
        """
        Generate Mermaid flowchart report with architectural violations highlighted.

        Nodes involved in circular dependencies are styled with red fill.
        High-coupling nodes are styled with orange fill.
        Edges that are part of cycles are rendered as thick red arrows.

        Args:
            result: DependencyReport containing modules and violations
            direction: Flowchart direction (LR, TB, RL, BT)

        Returns:
            Mermaid flowchart string
        """
        cycle_nodes, high_coupling_nodes, cycle_edges = self._collect_violation_sets(result)

        lines = [f"flowchart {direction}"]

        node_ids: dict = {}
        for idx, module in enumerate(sorted(m.module_name for m in result.modules)):
            node_id = f"n{idx}"
            node_ids[module] = node_id
            lines.append(f'  {node_id}["{module}"]')

        lines.append("")

        violation_link_indices: list = []
        link_index = 0

        for module in sorted(m.module_name for m in result.modules):
            src_id = node_ids[module]
            module_data = result.get_module(module)
            if not module_data:
                continue
            for dep in sorted(module_data.all_dependencies):
                if dep not in node_ids:
                    continue
                tgt_id = node_ids[dep]
                if (module, dep) in cycle_edges:
                    lines.append(f"  {src_id} ==> {tgt_id}")
                    violation_link_indices.append(link_index)
                else:
                    lines.append(f"  {src_id} --> {tgt_id}")
                link_index += 1

        lines.append("")

        if cycle_nodes:
            for node_name in sorted(cycle_nodes):
                if node_name in node_ids:
                    nid = node_ids[node_name]
                    lines.append(f"  style {nid} fill:#ff4444,color:#fff,stroke:#cc0000")

        if high_coupling_nodes:
            for node_name in sorted(high_coupling_nodes):
                if node_name in node_ids and node_name not in cycle_nodes:
                    nid = node_ids[node_name]
                    lines.append(f"  style {nid} fill:#ff8c00,color:#fff,stroke:#cc6600")

        if violation_link_indices:
            lines.append(f"  linkStyle {','.join(str(i) for i in violation_link_indices)} stroke:#ff0000,stroke-width:3px")

        lines.append("")
        lines.append(f"%% Cycles: {result.total_cycles}  High-coupling: {len(result.high_coupling_modules)}")

        return "\n".join(lines)

    def _generate_graphviz_report(self, result: DependencyReport, direction: str = "LR") -> str:
        """
        Generate Graphviz DOT report with architectural violations highlighted.

        Nodes involved in circular dependencies are filled red.
        High-coupling nodes are filled orange.
        Edges that are part of cycles are rendered in red with a bold penwidth.

        Args:
            result: DependencyReport containing modules and violations
            direction: rankdir value (LR, TB, RL, BT)

        Returns:
            Graphviz DOT string
        """
        cycle_nodes, high_coupling_nodes, cycle_edges = self._collect_violation_sets(result)

        lines = ["digraph dependencies {"]
        lines.append(f"  rankdir={direction};")
        lines.append("  node [shape=box, style=filled, fillcolor=lightblue];")
        lines.append("")

        for module in sorted(m.module_name for m in result.modules):
            node_id = module.replace(".", "_")
            if module in cycle_nodes:
                lines.append(
                    f'  "{node_id}" [label="{module}", fillcolor="#ff4444", fontcolor=white, '
                    f'tooltip="VIOLATION: circular dependency"];'
                )
            elif module in high_coupling_nodes:
                lines.append(
                    f'  "{node_id}" [label="{module}", fillcolor="#ff8c00", fontcolor=white, '
                    f'tooltip="WARNING: high coupling"];'
                )
            else:
                lines.append(f'  "{node_id}" [label="{module}"];')

        lines.append("")

        for module in sorted(m.module_name for m in result.modules):
            module_data = result.get_module(module)
            if not module_data:
                continue
            src_id = module.replace(".", "_")
            for dep in sorted(module_data.all_dependencies):
                tgt_id = dep.replace(".", "_")
                if (module, dep) in cycle_edges:
                    lines.append(
                        f'  "{src_id}" -> "{tgt_id}" [color=red, penwidth=2.0, '
                        f'tooltip="VIOLATION: part of circular dependency"];'
                    )
                else:
                    lines.append(f'  "{src_id}" -> "{tgt_id}";')

        lines.append("")
        lines.append(
            f'  // Cycles: {result.total_cycles}  '
            f'High-coupling: {len(result.high_coupling_modules)}'
        )
        lines.append("}")

        return "\n".join(lines)

    def _generate_text_report(self, result: DependencyReport) -> str:
        """Generate text format report."""
        lines = []
        lines.append("")
        lines.append("=" * 70)
        lines.append("  HEIMDALL DEPENDENCY ANALYSIS REPORT")
        lines.append("=" * 70)
        lines.append("")
        lines.append(f"  Scan Path:    {result.scan_path}")
        lines.append(f"  Scanned At:   {result.scanned_at.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"  Duration:     {result.scan_duration_seconds:.2f}s")
        lines.append("")
        lines.append(f"  Total Modules:      {result.total_modules}")
        lines.append(f"  Total Dependencies: {result.total_dependencies}")
        lines.append("")

        # Circular dependencies
        if result.has_cycles:
            lines.append("-" * 70)
            lines.append("  CIRCULAR DEPENDENCIES")
            lines.append("-" * 70)
            lines.append("")

            for cycle in result.circular_dependencies:
                lines.append(f"  [{cycle.severity.value.upper()}] {cycle.as_string}")
                lines.append("")

        # High coupling modules
        if result.high_coupling_modules:
            lines.append("-" * 70)
            lines.append("  HIGH COUPLING MODULES")
            lines.append("-" * 70)
            lines.append("")

            for module in result.high_coupling_modules:
                lines.append(f"  {module.module_name}")
                lines.append(f"    Afferent (Ca): {module.afferent_coupling}")
                lines.append(f"    Efferent (Ce): {module.efferent_coupling}")
                lines.append(f"    Instability:   {module.instability:.2f}")
                lines.append("")

        # Modularity
        lines.append("-" * 70)
        lines.append("  MODULARITY METRICS")
        lines.append("-" * 70)
        lines.append("")
        lines.append(f"  Modularity Score:   {result.modularity.modularity_score:.2f}")
        lines.append(f"  Clusters Found:     {len(result.modularity.clusters)}")
        lines.append(f"  Average Afferent:   {result.modularity.average_afferent:.2f}")
        lines.append(f"  Average Efferent:   {result.modularity.average_efferent:.2f}")
        lines.append(f"  Stable Modules:     {len(result.modularity.stable_modules)}")
        lines.append(f"  Unstable Modules:   {len(result.modularity.unstable_modules)}")
        lines.append("")

        # Summary
        lines.append("-" * 70)
        lines.append("  SUMMARY")
        lines.append("-" * 70)
        lines.append("")

        if result.has_cycles:
            lines.append(f"  [!] Found {result.total_cycles} circular dependencies")
        else:
            lines.append("  [OK] No circular dependencies found")

        if result.high_coupling_modules:
            lines.append(f"  [!] Found {len(result.high_coupling_modules)} high coupling modules")
        else:
            lines.append("  [OK] No high coupling modules found")

        lines.append("")
        lines.append("=" * 70)

        return "\n".join(lines)

    def _generate_json_report(self, result: DependencyReport) -> str:
        """Generate JSON format report."""
        output = {
            "scan_path": result.scan_path,
            "scanned_at": result.scanned_at.isoformat(),
            "scan_duration_seconds": result.scan_duration_seconds,
            "summary": {
                "total_modules": result.total_modules,
                "total_dependencies": result.total_dependencies,
                "total_cycles": result.total_cycles,
                "has_cycles": result.has_cycles,
            },
            "circular_dependencies": [
                {
                    "cycle": cycle.cycle,
                    "length": cycle.cycle_length,
                    "severity": cycle.severity.value,
                }
                for cycle in result.circular_dependencies
            ],
            "modularity": {
                "score": result.modularity.modularity_score,
                "clusters": len(result.modularity.clusters),
                "average_afferent": result.modularity.average_afferent,
                "average_efferent": result.modularity.average_efferent,
                "stable_modules": result.modularity.stable_modules,
                "unstable_modules": result.modularity.unstable_modules,
            },
            "modules": [
                {
                    "name": m.module_name,
                    "file": m.relative_path,
                    "dependencies": list(m.all_dependencies),
                    "afferent_coupling": m.afferent_coupling,
                    "efferent_coupling": m.efferent_coupling,
                    "instability": round(m.instability, 2),
                }
                for m in result.modules
            ],
        }

        return json.dumps(output, indent=2)

    def _generate_markdown_report(self, result: DependencyReport) -> str:
        """Generate Markdown format report."""
        lines = []
        lines.append("# Heimdall Dependency Analysis Report")
        lines.append("")
        lines.append(f"- **Scan Path:** `{result.scan_path}`")
        lines.append(f"- **Scanned At:** {result.scanned_at.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"- **Duration:** {result.scan_duration_seconds:.2f}s")
        lines.append("")
        lines.append("## Summary")
        lines.append("")
        lines.append(f"- **Total Modules:** {result.total_modules}")
        lines.append(f"- **Total Dependencies:** {result.total_dependencies}")
        lines.append(f"- **Circular Dependencies:** {result.total_cycles}")
        lines.append("")

        if result.has_cycles:
            lines.append("## Circular Dependencies")
            lines.append("")
            lines.append("| Cycle | Length | Severity |")
            lines.append("|-------|--------|----------|")

            for cycle in result.circular_dependencies:
                lines.append(
                    f"| {cycle.as_string} | {cycle.cycle_length} | "
                    f"{cycle.severity.value.upper()} |"
                )

            lines.append("")

        lines.append("## Modularity Metrics")
        lines.append("")
        lines.append(f"- **Modularity Score:** {result.modularity.modularity_score:.2f}")
        lines.append(f"- **Clusters:** {len(result.modularity.clusters)}")
        lines.append(f"- **Average Afferent:** {result.modularity.average_afferent:.2f}")
        lines.append(f"- **Average Efferent:** {result.modularity.average_efferent:.2f}")
        lines.append("")

        return "\n".join(lines)
