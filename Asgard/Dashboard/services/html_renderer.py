"""
Asgard Dashboard HTML Renderer

Generates all HTML pages for the web dashboard using Python f-strings only.
No external templating library is used.
"""

from pathlib import Path
from typing import List

from Asgard.Dashboard.models.dashboard_models import DashboardState, IssueSummaryData, RatingData


_EMBEDDED_CSS = """
* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

body {
    font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    background: #f5f6fa;
    color: #2d3748;
    display: flex;
    min-height: 100vh;
}

/* Sidebar */
.sidebar {
    width: 220px;
    min-width: 220px;
    background: #1a202c;
    color: #e2e8f0;
    display: flex;
    flex-direction: column;
    padding: 0;
    position: fixed;
    top: 0;
    left: 0;
    height: 100vh;
    z-index: 100;
}

.sidebar-header {
    padding: 24px 20px 16px 20px;
    border-bottom: 1px solid #2d3748;
}

.sidebar-header h1 {
    font-size: 1.1rem;
    font-weight: 700;
    color: #63b3ed;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}

.sidebar-project {
    font-size: 0.78rem;
    color: #718096;
    margin-top: 6px;
    word-break: break-all;
}

.sidebar-nav {
    flex: 1;
    padding: 16px 0;
}

.sidebar-nav a {
    display: block;
    padding: 10px 20px;
    color: #a0aec0;
    text-decoration: none;
    font-size: 0.9rem;
    border-left: 3px solid transparent;
    transition: background 0.15s, color 0.15s;
}

.sidebar-nav a:hover {
    background: #2d3748;
    color: #e2e8f0;
}

.sidebar-nav a.active {
    background: #2d3748;
    color: #63b3ed;
    border-left-color: #63b3ed;
    font-weight: 600;
}

.sidebar-footer {
    padding: 16px 20px;
    border-top: 1px solid #2d3748;
}

.sidebar-footer a {
    display: inline-block;
    padding: 7px 14px;
    background: #2b6cb0;
    color: #e2e8f0;
    text-decoration: none;
    border-radius: 5px;
    font-size: 0.82rem;
    font-weight: 600;
}

.sidebar-footer a:hover {
    background: #3182ce;
}

/* Main content */
.main-content {
    margin-left: 220px;
    flex: 1;
    padding: 32px 36px;
    max-width: 1200px;
}

.page-title {
    font-size: 1.5rem;
    font-weight: 700;
    margin-bottom: 24px;
    color: #1a202c;
}

/* Cards grid */
.cards-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 18px;
    margin-bottom: 32px;
}

.card {
    background: #fff;
    border-radius: 8px;
    padding: 20px 22px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.08);
}

.card-label {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #718096;
    margin-bottom: 8px;
}

.card-value {
    font-size: 2rem;
    font-weight: 700;
    line-height: 1;
}

.card-value.small {
    font-size: 1.4rem;
}

.card-sub {
    font-size: 0.8rem;
    color: #718096;
    margin-top: 6px;
}

/* Rating badges */
.rating-badge {
    display: inline-block;
    width: 48px;
    height: 48px;
    border-radius: 8px;
    line-height: 48px;
    text-align: center;
    font-size: 1.5rem;
    font-weight: 700;
    color: #fff;
}

.rating-A { background: #2ecc71; }
.rating-B { background: #27ae60; }
.rating-C { background: #f39c12; }
.rating-D { background: #e67e22; }
.rating-E { background: #e74c3c; }
.rating-unknown { background: #95a5a6; }

/* Quality gate badge */
.gate-badge {
    display: inline-block;
    padding: 10px 28px;
    border-radius: 6px;
    font-size: 1.2rem;
    font-weight: 700;
    color: #fff;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}

.gate-passed { background: #27ae60; }
.gate-failed { background: #e74c3c; }
.gate-unknown { background: #95a5a6; }
.gate-warning { background: #f39c12; }

/* Section heading */
.section-title {
    font-size: 1rem;
    font-weight: 700;
    color: #2d3748;
    margin: 28px 0 14px 0;
}

/* Table */
.table-wrap {
    background: #fff;
    border-radius: 8px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.08);
    overflow: hidden;
    margin-bottom: 24px;
}

table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.87rem;
}

thead th {
    background: #2d3748;
    color: #e2e8f0;
    padding: 10px 14px;
    text-align: left;
    font-weight: 600;
    font-size: 0.82rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}

tbody tr:nth-child(even) {
    background: #f7fafc;
}

tbody tr:hover {
    background: #ebf8ff;
}

tbody td {
    padding: 9px 14px;
    border-bottom: 1px solid #e2e8f0;
    vertical-align: middle;
}

/* Severity badges */
.sev-badge {
    display: inline-block;
    padding: 2px 9px;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 700;
    color: #fff;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}

.sev-critical { background: #e74c3c; }
.sev-high { background: #e67e22; }
.sev-medium { background: #f39c12; }
.sev-low { background: #3498db; }
.sev-info { background: #95a5a6; }

/* Status badges */
.status-badge {
    display: inline-block;
    padding: 2px 9px;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}

.status-open { background: #fef3cd; color: #856404; }
.status-confirmed { background: #fde8e8; color: #991b1b; }
.status-resolved { background: #d1fae5; color: #065f46; }
.status-closed { background: #e5e7eb; color: #374151; }
.status-false_positive { background: #e0e7ff; color: #3730a3; }
.status-wont_fix { background: #f3f4f6; color: #6b7280; }

/* Filter bar */
.filter-bar {
    display: flex;
    align-items: center;
    gap: 14px;
    margin-bottom: 20px;
    flex-wrap: wrap;
}

.filter-bar label {
    font-size: 0.85rem;
    font-weight: 600;
    color: #4a5568;
}

.filter-bar select {
    padding: 6px 12px;
    border: 1px solid #cbd5e0;
    border-radius: 5px;
    font-size: 0.85rem;
    background: #fff;
    color: #2d3748;
    cursor: pointer;
}

.filter-bar button {
    padding: 6px 16px;
    background: #3182ce;
    color: #fff;
    border: none;
    border-radius: 5px;
    font-size: 0.85rem;
    font-weight: 600;
    cursor: pointer;
}

.filter-bar button:hover {
    background: #2b6cb0;
}

/* Pagination info */
.pagination-info {
    font-size: 0.82rem;
    color: #718096;
    margin-bottom: 10px;
}

/* Bar chart */
.bar-chart {
    background: #fff;
    border-radius: 8px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.08);
    padding: 20px 24px;
    margin-bottom: 24px;
}

.bar-chart-title {
    font-size: 0.88rem;
    font-weight: 700;
    color: #4a5568;
    margin-bottom: 14px;
}

.bar-row {
    display: flex;
    align-items: center;
    margin-bottom: 8px;
    gap: 10px;
}

.bar-label {
    min-width: 110px;
    font-size: 0.78rem;
    color: #718096;
    text-align: right;
    flex-shrink: 0;
}

.bar-outer {
    flex: 1;
    background: #e2e8f0;
    border-radius: 4px;
    height: 18px;
    overflow: hidden;
}

.bar-inner {
    height: 100%;
    border-radius: 4px;
    background: #3182ce;
    transition: width 0.3s;
}

.bar-value {
    min-width: 36px;
    font-size: 0.78rem;
    font-weight: 700;
    color: #2d3748;
}

/* Timestamp */
.ts {
    font-size: 0.78rem;
    color: #a0aec0;
}

/* Error page */
.error-container {
    max-width: 480px;
    margin: 80px auto;
    background: #fff;
    border-radius: 8px;
    padding: 36px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    text-align: center;
}

.error-title {
    font-size: 1.3rem;
    font-weight: 700;
    color: #e74c3c;
    margin-bottom: 14px;
}

.error-message {
    font-size: 0.92rem;
    color: #4a5568;
    line-height: 1.6;
}
"""


def _truncate_path(file_path: str, components: int = 3) -> str:
    """Return the last N path components of a file path."""
    parts = Path(file_path).parts
    if len(parts) <= components:
        return file_path
    return "/".join(parts[-components:])


def _rating_badge(letter: str) -> str:
    """Return an HTML rating badge for a letter grade."""
    safe = letter.upper() if letter and letter.upper() in ("A", "B", "C", "D", "E") else "unknown"
    return f'<span class="rating-badge rating-{safe}">{letter or "?"}</span>'


def _severity_badge(severity: str) -> str:
    """Return an HTML severity badge."""
    low = severity.lower()
    return f'<span class="sev-badge sev-{low}">{severity.upper()}</span>'


def _status_badge(status: str) -> str:
    """Return an HTML status badge."""
    low = status.lower()
    label = status.replace("_", " ").title()
    return f'<span class="status-badge status-{low}">{label}</span>'


def _gate_badge(status: str) -> str:
    """Return an HTML quality gate badge."""
    low = (status or "unknown").lower()
    label = (status or "Unknown").upper()
    return f'<span class="gate-badge gate-{low}">{label}</span>'


def _rating_to_score(letter: str) -> int:
    """Convert a letter rating to a numeric score for charting."""
    mapping = {"A": 100, "B": 80, "C": 60, "D": 40, "E": 20}
    return mapping.get((letter or "").upper(), 0)


class HtmlRenderer:
    """
    Generates HTML pages for the Asgard web dashboard.

    All rendering is done with Python f-strings. No external templating library is used.
    """

    def render_page(
        self,
        title: str,
        content: str,
        active_page: str,
        project_path: str,
    ) -> str:
        """
        Wrap content in a full HTML document with sidebar navigation and embedded CSS.

        Args:
            title: Page title shown in the browser tab.
            content: HTML fragment for the main content area.
            active_page: One of 'overview', 'issues', 'history'.
            project_path: Project path displayed in the sidebar.

        Returns:
            Complete HTML document as a string.
        """
        project_label = Path(project_path).name or project_path

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
{_EMBEDDED_CSS}
</style>
</head>
<body>
<nav class="sidebar">
  <div class="sidebar-header">
    <h1>Asgard</h1>
    <div class="sidebar-project" title="{project_path}">{project_label}</div>
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
        """
        Render the overview page with quality gate, ratings, and issue summary cards.

        Args:
            state: DashboardState populated by DataCollector.

        Returns:
            Complete HTML document string.
        """
        gate_status = state.quality_gate_status or "unknown"
        gate_html = _gate_badge(gate_status)

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
    <div>{_rating_badge(r.maintainability)}</div>
  </div>
  <div class="card">
    <div class="card-label">Reliability</div>
    <div>{_rating_badge(r.reliability)}</div>
  </div>
  <div class="card">
    <div class="card-label">Security</div>
    <div>{_rating_badge(r.security)}</div>
  </div>
  <div class="card">
    <div class="card-label">Overall</div>
    <div>{_rating_badge(r.overall)}</div>
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
        """
        Render the issues page with filter bar and paginated issues table.

        Args:
            state: DashboardState populated by DataCollector.
            status_filter: Active status filter value ('all' or a specific status string).
            severity_filter: Active severity filter value ('all' or a specific severity string).

        Returns:
            Complete HTML document string.
        """
        issues = state.recent_issues

        if status_filter and status_filter != "all":
            issues = [i for i in issues if str(i.get("status", "")).lower() == status_filter.lower()]

        if severity_filter and severity_filter != "all":
            issues = [i for i in issues if str(i.get("severity", "")).lower() == severity_filter.lower()]

        total_count = len(issues)
        page_issues = issues[:50]

        status_options = [
            ("all", "All Statuses"),
            ("open", "Open"),
            ("confirmed", "Confirmed"),
            ("resolved", "Resolved"),
            ("false_positive", "False Positive"),
            ("wont_fix", "Wont Fix"),
        ]
        severity_options = [
            ("all", "All Severities"),
            ("critical", "Critical"),
            ("high", "High"),
            ("medium", "Medium"),
            ("low", "Low"),
            ("info", "Info"),
        ]

        def build_options(options: list, current: str) -> str:
            parts = []
            for val, label in options:
                selected = ' selected' if val == current else ''
                parts.append(f'<option value="{val}"{selected}>{label}</option>')
            return "".join(parts)

        status_opts_html = build_options(status_options, status_filter or "all")
        severity_opts_html = build_options(severity_options, severity_filter or "all")

        filter_bar = f"""
<form method="get" action="/issues" class="filter-bar filter-form">
  <label for="status-filter">Status:</label>
  <select name="status" id="status-filter">
    {status_opts_html}
  </select>
  <label for="severity-filter">Severity:</label>
  <select name="severity" id="severity-filter">
    {severity_opts_html}
  </select>
  <button type="submit">Filter</button>
</form>"""

        pagination_html = ""
        if total_count > 50:
            pagination_html = f'<div class="pagination-info">Showing 1-50 of {total_count}</div>'
        elif total_count == 0:
            pagination_html = '<div class="pagination-info">No issues match the current filters.</div>'
        else:
            pagination_html = f'<div class="pagination-info">Showing {total_count} issue{"s" if total_count != 1 else ""}</div>'

        rows_html = ""
        for issue in page_issues:
            severity_str = str(issue.get("severity", ""))
            status_str = str(issue.get("status", ""))
            file_path = str(issue.get("file_path", ""))
            line_number = issue.get("line_number", "")
            first_detected = issue.get("first_detected", "")
            if first_detected and "T" in str(first_detected):
                first_detected = str(first_detected).split("T")[0]

            rows_html += f"""<tr>
  <td>{_severity_badge(severity_str)}</td>
  <td>{issue.get("issue_type", "")}</td>
  <td title="{file_path}">{_truncate_path(file_path)}</td>
  <td>{line_number}</td>
  <td>{issue.get("rule_id", "")}</td>
  <td>{_status_badge(status_str)}</td>
  <td class="ts">{first_detected}</td>
  <td>{issue.get("assigned_to", "") or ""}</td>
</tr>"""

        table_html = f"""
<div class="table-wrap">
  <table>
    <thead>
      <tr>
        <th>Severity</th>
        <th>Type</th>
        <th>File</th>
        <th>Line</th>
        <th>Rule</th>
        <th>Status</th>
        <th>First Detected</th>
        <th>Assigned To</th>
      </tr>
    </thead>
    <tbody>
      {rows_html if rows_html else '<tr><td colspan="8" style="text-align:center;color:#718096;padding:20px;">No issues found.</td></tr>'}
    </tbody>
  </table>
</div>"""

        content = f"""
<h2 class="page-title">Issues</h2>
{filter_bar}
{pagination_html}
{table_html}
"""
        return self.render_page("Issues", content, "issues", state.project_path)

    def render_history(self, state: DashboardState) -> str:
        """
        Render the history page with snapshot table and a CSS quality score bar chart.

        Args:
            state: DashboardState populated by DataCollector.

        Returns:
            Complete HTML document string.
        """
        snapshots = state.snapshots

        rows_html = ""
        for snap in snapshots:
            ts = snap.get("scan_timestamp", "")
            if ts and "T" in str(ts):
                ts_display = str(ts).replace("T", " ").split(".")[0]
            else:
                ts_display = str(ts) if ts else ""

            commit = snap.get("git_commit", "") or ""
            commit_short = commit[:8] if commit else ""
            gate_status = snap.get("quality_gate_status", "") or ""
            ratings = snap.get("ratings") or {}

            maint = ratings.get("maintainability", "?")
            reli = ratings.get("reliability", "?")
            sec = ratings.get("security", "?")
            overall = ratings.get("overall", "?")
            score = _rating_to_score(overall)

            rows_html += f"""<tr>
  <td class="ts">{ts_display}</td>
  <td><code>{commit_short}</code></td>
  <td>{_gate_badge(gate_status) if gate_status else ""}</td>
  <td>{_rating_badge(maint)}</td>
  <td>{_rating_badge(reli)}</td>
  <td>{_rating_badge(sec)}</td>
  <td><strong>{score}</strong></td>
</tr>"""

        table_html = f"""
<div class="table-wrap">
  <table>
    <thead>
      <tr>
        <th>Date</th>
        <th>Commit</th>
        <th>Gate</th>
        <th>Maintainability</th>
        <th>Reliability</th>
        <th>Security</th>
        <th>Quality Score</th>
      </tr>
    </thead>
    <tbody>
      {rows_html if rows_html else '<tr><td colspan="7" style="text-align:center;color:#718096;padding:20px;">No snapshots recorded yet.</td></tr>'}
    </tbody>
  </table>
</div>"""

        chart_snapshots = snapshots[:10]
        chart_items: List[str] = []
        max_score = 100

        for snap in reversed(chart_snapshots):
            ts = snap.get("scan_timestamp", "")
            ts_label = str(ts).split("T")[0] if ts and "T" in str(ts) else str(ts)[:10]
            ratings = snap.get("ratings") or {}
            overall = ratings.get("overall", "?")
            score = _rating_to_score(overall)
            bar_pct = int((score / max_score) * 100)

            chart_items.append(f"""<div class="bar-row">
  <div class="bar-label">{ts_label}</div>
  <div class="bar-outer">
    <div class="bar-inner" style="width:{bar_pct}%;"></div>
  </div>
  <div class="bar-value">{score}</div>
</div>""")

        chart_html = ""
        if chart_items:
            chart_html = f"""
<div class="bar-chart">
  <div class="bar-chart-title">Quality Score Trend (last {len(chart_items)} runs, A=100 to E=20)</div>
  {"".join(chart_items)}
</div>"""

        content = f"""
<h2 class="page-title">History</h2>
{chart_html}
<div class="section-title">Analysis Snapshots</div>
{table_html}
"""
        return self.render_page("History", content, "history", state.project_path)

    def render_error(self, message: str) -> str:
        """
        Render a simple error page.

        Args:
            message: Error message to display.

        Returns:
            Complete HTML document string.
        """
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Error - Asgard Dashboard</title>
<style>
body {{ font-family: system-ui, sans-serif; background: #f5f6fa; }}
{_EMBEDDED_CSS}
</style>
</head>
<body style="display:block;">
<div class="error-container">
  <div class="error-title">Dashboard Error</div>
  <div class="error-message">{message}</div>
  <p style="margin-top:20px;"><a href="/" style="color:#3182ce;">Return to Overview</a></p>
</div>
</body>
</html>"""
