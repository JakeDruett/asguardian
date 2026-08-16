"""Dashboard bind / expose gate (CH-0056)."""

import pytest

from Asgard.Dashboard.adapters.web.dashboard_handler import DashboardServer
from Asgard.Dashboard.models.dashboard_models import DashboardConfig


def test_refuses_wildcard_bind_without_expose():
    config = DashboardConfig(
        host="0.0.0.0",
        project_path=".",
        expose=False,
        open_browser=False,
    )
    with pytest.raises(ValueError, match="expose"):
        DashboardServer(config).run()
