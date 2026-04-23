"""
Asgard Dashboard Server - re-export shim.

The DashboardServer implementation has been moved to its canonical location
in the web adapter layer at:
    Asgard.Dashboard.adapters.web.dashboard_handler

This module re-exports DashboardServer to preserve backward compatibility
for any code that imported from the old services path.
"""

from Asgard.Dashboard.adapters.web.dashboard_handler import DashboardServer

__all__ = [
    "DashboardServer",
]
