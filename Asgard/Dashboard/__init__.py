"""
Asgard Dashboard Module

Provides a standalone Python web dashboard for browsing Asgard code analysis
results. The dashboard is served by a lightweight HTTP server built on the
Python standard library only (no external web framework required).

Exported classes:
    DashboardConfig  - Configuration model for the dashboard server.
    DashboardServer  - HTTP server that serves the dashboard pages.

Usage:
    from Asgard.Dashboard import DashboardConfig, DashboardServer

    config = DashboardConfig(
        project_path="/path/to/project",
        host="localhost",
        port=8080,
        open_browser=True,
    )
    DashboardServer(config).run()
"""

from Asgard.Dashboard.adapters.web.dashboard_handler import DashboardServer
from Asgard.Dashboard.models.dashboard_models import DashboardConfig

__all__ = [
    "DashboardConfig",
    "DashboardServer",
]
