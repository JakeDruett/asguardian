"""
Asgard Dashboard HTML Renderer - Page rendering functions.

Issues and history page rendering extracted from html_renderer.py.
"""

from typing import List

from Asgard.Dashboard.models.dashboard_models import DashboardState
from Asgard.Dashboard.services._html_helpers import (
    esc,
    gate_badge,
    rating_badge,
    rating_to_score,
    severity_badge,
    status_badge,
    truncate_path,
)


def render_issues_content(
    state: DashboardState,
    status_filter: str,
    severity_filter: str,
) -> str:
    """Build the issues page HTML content fragment."""
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
  <td>{severity_badge(severity_str)}</td>
  <td>{esc(issue.get("issue_type", ""))}</td>
  <td title="{esc(file_path)}">{esc(truncate_path(file_path))}</td>
  <td>{esc(line_number)}</td>
  <td>{esc(issue.get("rule_id", ""))}</td>
  <td>{status_badge(status_str)}</td>
  <td class="ts">{esc(first_detected)}</td>
  <td>{esc(issue.get("assigned_to", "") or "")}</td>
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

    return f"""
<h2 class="page-title">Issues</h2>
{filter_bar}
{pagination_html}
{table_html}
"""


def render_history_content(state: DashboardState) -> str:
    """Build the history page HTML content fragment."""
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
        score = rating_to_score(overall)

        rows_html += f"""<tr>
  <td class="ts">{esc(ts_display)}</td>
  <td><code>{esc(commit_short)}</code></td>
  <td>{gate_badge(gate_status) if gate_status else ""}</td>
  <td>{rating_badge(maint)}</td>
  <td>{rating_badge(reli)}</td>
  <td>{rating_badge(sec)}</td>
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
        score = rating_to_score(overall)
        bar_pct = int((score / max_score) * 100)

        chart_items.append(f"""<div class="bar-row">
  <div class="bar-label">{esc(ts_label)}</div>
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

    return f"""
<h2 class="page-title">History</h2>
{chart_html}
<div class="section-title">Analysis Snapshots</div>
{table_html}
"""
