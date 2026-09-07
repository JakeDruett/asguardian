"""
Heimdall Graph Visualizer Service

Renders a dependency graph to an image using matplotlib. Kept out of
graph_builder.py deliberately: matplotlib is not a core runtime dependency of
asguardian, only of this optional rendering path (the "viz" extra). Importing
this module requires `pip install asguardian[viz]`; importing graph_builder,
Dependencies, or Quality does not.
"""

from pathlib import Path
from typing import Optional, Tuple

import matplotlib.pyplot as plt
import networkx as nx

from Asgard.Bragi.Dependencies.services.graph_builder import GraphBuilder


class GraphVisualizer:
    """Renders a GraphBuilder's dependency graph to an image file or screen."""

    def __init__(self, builder: GraphBuilder):
        """Initialise the visualizer around an existing GraphBuilder."""
        self.builder = builder

    def visualize(
        self,
        scan_path: Optional[Path] = None,
        output_path: Optional[Path] = None,
        figsize: Tuple[int, int] = (12, 8),
    ) -> None:
        """
        Visualize the dependency graph using matplotlib.

        Args:
            scan_path: Root path to scan
            output_path: Path to save the image
            figsize: Figure size (width, height)
        """
        graph = self.builder.build_graph(scan_path)

        fig, ax = plt.subplots(figsize=figsize)

        # Use spring layout for positioning
        pos = nx.spring_layout(graph, k=2, iterations=50)

        # Draw the graph
        nx.draw(
            graph,
            pos,
            ax=ax,
            with_labels=True,
            node_color="lightblue",
            node_size=2000,
            font_size=8,
            font_weight="bold",
            arrows=True,
            arrowsize=15,
            edge_color="gray",
            alpha=0.7,
        )

        ax.set_title("Module Dependencies")

        if output_path:
            plt.savefig(output_path, dpi=150, bbox_inches="tight")
            plt.close()
        else:
            plt.show()
