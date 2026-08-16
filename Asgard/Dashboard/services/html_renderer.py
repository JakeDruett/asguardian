"""
Asgard Dashboard HTML Renderer

Generates HTML pages for the web dashboard using Python f-strings only.
"""

from pathlib import Path

from Asgard.Dashboard.models.dashboard_models import DashboardState
from Asgard.Dashboard.services._html_helpers import (
    esc,
    gate_badge,
    rating_badge,
)
from Asgard.Dashboard.services._html_renderer_pages import (
    render_history_content,
    render_issues_content,
)
from Asgard.Dashboard.services._html_templates import EMBEDDED_CSS


class HtmlRenderer:
    """Generates HTML pages for the Asgard web dashboard."""

    def render_page(
        self,
        title: str,
        content: str,
        active_page: str,
        project_path: str,
    ) -> str:
        """Wrap content in a full HTML document with sidebar navigation."""
        project_label = esc(Path(project_path).name or project_path)
        project_attr = esc(project_path)
        title = esc(title)

        def nav_link(href: str, label: str, page_key: str) -> str:
            css_class = "active" if active_page == page_key else ""
            return f'<a href="{href}" class="{css_class}">{label}</a>'

        nav_html = (
            nav_link("/", "Overview", "overview")
            + nav_link("/issues", "Issues", "issues")
            + nav_link("/history", "History", "history")
        )

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} - Asgard Dashboard</title>
<style>
{EMBEDDED_CSS}
</style>
</head>
<body>
<nav class="sidebar">
  <div class="sidebar-header">
    <h1>Asgard</h1>
    <div class="sidebar-project" title="{project_attr}">{project_label}</div>
  </div>
  <div class="sidebar-nav">
    {nav_html}
  </div>
  <div class="sidebar-footer">
    <a href="/refresh">Refresh</a>
  </div>
</nav>
<main class="main-content">
  {content}
</main>
<script>
(function() {{
  var selects = document.querySelectorAll('.filter-form select');
  selects.forEach(function(sel) {{
    sel.addEventListener('change', function() {{
      sel.closest('form').submit();
    }});
  }});
}})();
</script>
</body>
</html>"""

    def render_overview(self, state: DashboardState) -> str:
        """Render the overview page with quality gate, ratings, and issue summary."""
        gate_status = state.quality_gate_status or "unknown"
        gate_html = gate_badge(gate_status)

        ts_html = ""
        if state.last_analyzed:
            ts_html = f'<p class="ts" style="margin-top:8px;">Last analyzed: {state.last_analyzed.strftime("%Y-%m-%d %H:%M:%S")}</p>'

        ratings_html = ""
        if state.ratings:
            r = state.ratings
            ratings_html = f"""
<div class="section-title">Quality Ratings</div>
<div class="cards-grid">
  <div class="card">
    <div class="card-label">Maintainability</div>
    <div>{rating_badge(r.maintainability)}</div>
  </div>
  <div class="card">
    <div class="card-label">Reliability</div>
    <div>{rating_badge(r.reliability)}</div>
  </div>
  <div class="card">
    <div class="card-label">Security</div>
    <div>{rating_badge(r.security)}</div>
  </div>
  <div class="card">
    <div class="card-label">Overall</div>
    <div>{rating_badge(r.overall)}</div>
  </div>
</div>"""

        s = state.issue_summary
        issue_cards = f"""
<div class="section-title">Issue Summary</div>
<div class="cards-grid">
  <div class="card">
    <div class="card-label">Total Issues</div>
    <div class="card-value">{s.total}</div>
  </div>
  <div class="card">
    <div class="card-label">Open</div>
    <div class="card-value" style="color:#e67e22;">{s.open}</div>
  </div>
  <div class="card">
    <div class="card-label">Confirmed</div>
    <div class="card-value" style="color:#e74c3c;">{s.confirmed}</div>
  </div>
  <div class="card">
    <div class="card-label">Critical</div>
    <div class="card-value" style="color:#e74c3c;">{s.critical}</div>
  </div>
  <div class="card">
    <div class="card-label">High</div>
    <div class="card-value" style="color:#e67e22;">{s.high}</div>
  </div>
  <div class="card">
    <div class="card-label">Medium</div>
    <div class="card-value" style="color:#f39c12;">{s.medium}</div>
  </div>
  <div class="card">
    <div class="card-label">Low</div>
    <div class="card-value" style="color:#3498db;">{s.low}</div>
  </div>
</div>"""

        content = f"""
<h2 class="page-title">Overview</h2>
<div class="section-title">Quality Gate</div>
<div class="card" style="display:inline-block;margin-bottom:28px;">
  {gate_html}
  {ts_html}
</div>
{ratings_html}
{issue_cards}
"""
        return self.render_page("Overview", content, "overview", state.project_path)

    def render_issues(
        self,
        state: DashboardState,
        status_filter: str,
        severity_filter: str,
    ) -> str:
        """Render the issues page with filter bar and paginated issues table."""
        content = render_issues_content(state, status_filter, severity_filter)
        return self.render_page("Issues", content, "issues", state.project_path)

    def render_history(self, state: DashboardState) -> str:
        """Render the history page with snapshot table and quality score chart."""
        content = render_history_content(state)
        return self.render_page("History", content, "history", state.project_path)

    def render_error(self, message: str) -> str:
        """Render a simple error page."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Error - Asgard Dashboard</title>
<style>
body {{ font-family: system-ui, sans-serif; background: #f5f6fa; }}
{EMBEDDED_CSS}
</style>
</head>
<body style="display:block;">
<div class="error-container">
  <div class="error-title">Dashboard Error</div>
  <div class="error-message">{esc(message)}</div>
  <p style="margin-top:20px;"><a href="/" style="color:#3182ce;">Return to Overview</a></p>
</div>
</body>
</html>"""
