"""
Freya HTML Reporter

Generates HTML reports from test results.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from Asgard.Freya.Integration.models.integration_models import (
    ReportConfig,
    ReportFormat,
    TestSeverity,
    UnifiedTestReport,
)


class HTMLReporter:
    """
    HTML report generation service.

    Generates styled HTML reports from test results.
    """

    def __init__(self, config: Optional[ReportConfig] = None):
        """
        Initialize the HTML Reporter.

        Args:
            config: Report configuration
        """
        self.config = config

    def generate(
        self,
        report: UnifiedTestReport,
        output_path: str,
        title: Optional[str] = None
    ) -> str:
        """
        Generate an HTML report.

        Args:
            report: Unified test report
            output_path: Output file path
            title: Optional report title

        Returns:
            Path to generated report
        """
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        html_content = self._build_html(report, title or "Freya Test Report")

        with open(output, "w", encoding="utf-8") as f:
            f.write(html_content)

        return str(output)

    def generate_json(self, report: UnifiedTestReport, output_path: str) -> str:
        """Generate JSON report."""
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        with open(output, "w", encoding="utf-8") as f:
            json.dump(report.model_dump(), f, indent=2, default=str)

        return str(output)

    def generate_junit(self, report: UnifiedTestReport, output_path: str) -> str:
        """Generate JUnit XML report for CI/CD."""
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        xml_content = self._build_junit_xml(report)

        with open(output, "w", encoding="utf-8") as f:
            f.write(xml_content)

        return str(output)

    def _build_html(self, report: UnifiedTestReport, title: str) -> str:
        """Build complete HTML report."""
        css = self._get_css()
        js = self._get_javascript()

        accessibility_html = self._build_results_section(
            "Accessibility",
            report.accessibility_results,
            report.accessibility_score
        )
        visual_html = self._build_results_section(
            "Visual",
            report.visual_results,
            report.visual_score
        )
        responsive_html = self._build_results_section(
            "Responsive",
            report.responsive_results,
            report.responsive_score
        )

        screenshots_html = self._build_screenshots_section(report.screenshots)

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>{css}</style>
</head>
<body>
    <header>
        <h1>{title}</h1>
        <div class="meta">
            <span>URL: <a href="{report.url}" target="_blank">{report.url}</a></span>
            <span>Tested: {report.tested_at}</span>
            <span>Duration: {report.duration_ms}ms</span>
        </div>
    </header>

    <main>
        <section class="summary">
            <h2>Summary</h2>
            <div class="score-grid">
                <div class="score-card overall">
                    <div class="score-value">{report.overall_score:.0f}</div>
                    <div class="score-label">Overall Score</div>
                </div>
                <div class="score-card">
                    <div class="score-value">{report.accessibility_score:.0f}</div>
                    <div class="score-label">Accessibility</div>
                </div>
                <div class="score-card">
                    <div class="score-value">{report.visual_score:.0f}</div>
                    <div class="score-label">Visual</div>
                </div>
                <div class="score-card">
                    <div class="score-value">{report.responsive_score:.0f}</div>
                    <div class="score-label">Responsive</div>
                </div>
            </div>

            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-value">{report.total_tests}</div>
                    <div class="stat-label">Total Tests</div>
                </div>
                <div class="stat-card passed">
                    <div class="stat-value">{report.passed}</div>
                    <div class="stat-label">Passed</div>
                </div>
                <div class="stat-card failed">
                    <div class="stat-value">{report.failed}</div>
                    <div class="stat-label">Failed</div>
                </div>
            </div>

            <div class="severity-grid">
                <div class="severity-card critical">
                    <span class="count">{report.critical_count}</span>
                    <span class="label">Critical</span>
                </div>
                <div class="severity-card serious">
                    <span class="count">{report.serious_count}</span>
                    <span class="label">Serious</span>
                </div>
                <div class="severity-card moderate">
                    <span class="count">{report.moderate_count}</span>
                    <span class="label">Moderate</span>
                </div>
                <div class="severity-card minor">
                    <span class="count">{report.minor_count}</span>
                    <span class="label">Minor</span>
                </div>
            </div>
        </section>

        {accessibility_html}
        {visual_html}
        {responsive_html}
        {screenshots_html}
    </main>

    <footer>
        <p>Generated by Freya - Visual Testing Framework</p>
    </footer>

    <script>{js}</script>
</body>
</html>"""
        return html

    def _build_results_section(self, category: str, results: list, score: float) -> str:
        """Build HTML section for a category."""
        if not results:
            return ""

        passed = [r for r in results if r.passed]
        failed = [r for r in results if not r.passed]

        rows = []
        for result in failed:
            severity_class = result.severity.value if result.severity else "moderate"
            wcag_html = f'<span class="wcag">{result.wcag_reference}</span>' if result.wcag_reference else ""

            rows.append(f"""
            <tr class="result-row {severity_class}">
                <td><span class="severity-badge {severity_class}">{severity_class}</span></td>
                <td>{result.test_name}</td>
                <td>{result.message} {wcag_html}</td>
                <td><code>{result.element_selector or '-'}</code></td>
                <td>{result.suggested_fix or '-'}</td>
            </tr>""")

        for result in passed:
            rows.append(f"""
            <tr class="result-row passed">
                <td><span class="severity-badge passed">pass</span></td>
                <td>{result.test_name}</td>
                <td>{result.message}</td>
                <td>-</td>
                <td>-</td>
            </tr>""")

        return f"""
        <section class="results-section" id="{category.lower()}">
            <h2>
                {category}
                <span class="section-score">{score:.0f}/100</span>
            </h2>
            <table class="results-table">
                <thead>
                    <tr>
                        <th>Severity</th>
                        <th>Test</th>
                        <th>Message</th>
                        <th>Element</th>
                        <th>Suggested Fix</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
        </section>"""

    def _build_screenshots_section(self, screenshots: dict) -> str:
        """Build screenshots gallery section."""
        if not screenshots:
            return ""

        items = []
        for name, path in screenshots.items():
            items.append(f"""
            <div class="screenshot-item">
                <img src="{path}" alt="{name}" loading="lazy">
                <div class="screenshot-label">{name}</div>
            </div>""")

        return f"""
        <section class="screenshots-section" id="screenshots">
            <h2>Screenshots</h2>
            <div class="screenshot-gallery">
                {''.join(items)}
            </div>
        </section>"""

    def _get_css(self) -> str:
        """Get CSS styles for report."""
        return """
        :root {
            --color-primary: #2563eb;
            --color-success: #16a34a;
            --color-warning: #ca8a04;
            --color-error: #dc2626;
            --color-critical: #7c2d12;
            --color-bg: #f8fafc;
            --color-card: #ffffff;
            --color-text: #1e293b;
            --color-muted: #64748b;
            --color-border: #e2e8f0;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--color-bg);
            color: var(--color-text);
            line-height: 1.6;
        }

        header {
            background: var(--color-primary);
            color: white;
            padding: 2rem;
        }

        header h1 {
            margin-bottom: 0.5rem;
        }

        header .meta {
            display: flex;
            gap: 2rem;
            opacity: 0.9;
        }

        header a {
            color: white;
        }

        main {
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }

        section {
            background: var(--color-card);
            border-radius: 8px;
            padding: 1.5rem;
            margin-bottom: 2rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }

        h2 {
            margin-bottom: 1rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .section-score {
            font-size: 1rem;
            color: var(--color-muted);
        }

        .score-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 1rem;
            margin-bottom: 1.5rem;
        }

        .score-card {
            text-align: center;
            padding: 1.5rem;
            background: var(--color-bg);
            border-radius: 8px;
        }

        .score-card.overall {
            background: var(--color-primary);
            color: white;
        }

        .score-value {
            font-size: 2.5rem;
            font-weight: bold;
        }

        .score-label {
            font-size: 0.875rem;
            opacity: 0.8;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 1rem;
            margin-bottom: 1.5rem;
        }

        .stat-card {
            text-align: center;
            padding: 1rem;
            background: var(--color-bg);
            border-radius: 8px;
        }

        .stat-card.passed {
            border-left: 4px solid var(--color-success);
        }

        .stat-card.failed {
            border-left: 4px solid var(--color-error);
        }

        .stat-value {
            font-size: 1.5rem;
            font-weight: bold;
        }

        .severity-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 1rem;
        }

        .severity-card {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.75rem 1rem;
            border-radius: 8px;
            background: var(--color-bg);
        }

        .severity-card.critical {
            border-left: 4px solid var(--color-critical);
        }

        .severity-card.serious {
            border-left: 4px solid var(--color-error);
        }

        .severity-card.moderate {
            border-left: 4px solid var(--color-warning);
        }

        .severity-card.minor {
            border-left: 4px solid var(--color-muted);
        }

        .severity-card .count {
            font-weight: bold;
            font-size: 1.25rem;
        }

        .results-table {
            width: 100%;
            border-collapse: collapse;
        }

        .results-table th,
        .results-table td {
            padding: 0.75rem;
            text-align: left;
            border-bottom: 1px solid var(--color-border);
        }

        .results-table th {
            background: var(--color-bg);
            font-weight: 600;
        }

        .severity-badge {
            display: inline-block;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
        }

        .severity-badge.critical {
            background: var(--color-critical);
            color: white;
        }

        .severity-badge.serious {
            background: var(--color-error);
            color: white;
        }

        .severity-badge.moderate {
            background: var(--color-warning);
            color: white;
        }

        .severity-badge.minor {
            background: var(--color-muted);
            color: white;
        }

        .severity-badge.passed {
            background: var(--color-success);
            color: white;
        }

        .wcag {
            display: inline-block;
            padding: 0.125rem 0.375rem;
            background: var(--color-bg);
            border-radius: 4px;
            font-size: 0.75rem;
            margin-left: 0.5rem;
        }

        code {
            background: var(--color-bg);
            padding: 0.125rem 0.375rem;
            border-radius: 4px;
            font-size: 0.875rem;
        }

        .screenshot-gallery {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 1rem;
        }

        .screenshot-item {
            border: 1px solid var(--color-border);
            border-radius: 8px;
            overflow: hidden;
        }

        .screenshot-item img {
            width: 100%;
            height: auto;
        }

        .screenshot-label {
            padding: 0.5rem;
            background: var(--color-bg);
            text-align: center;
            font-size: 0.875rem;
        }

        footer {
            text-align: center;
            padding: 2rem;
            color: var(--color-muted);
        }

        @media (max-width: 768px) {
            .score-grid,
            .stats-grid,
            .severity-grid {
                grid-template-columns: repeat(2, 1fr);
            }

            header .meta {
                flex-direction: column;
                gap: 0.5rem;
            }

            .results-table {
                display: block;
                overflow-x: auto;
            }
        }
        """

    def _get_javascript(self) -> str:
        """Get JavaScript for interactivity."""
        return """
        document.addEventListener('DOMContentLoaded', function() {
            // Add click handlers for expandable rows
            const rows = document.querySelectorAll('.result-row');
            rows.forEach(row => {
                row.addEventListener('click', function() {
                    this.classList.toggle('expanded');
                });
            });
        });
        """

    def _build_junit_xml(self, report: UnifiedTestReport) -> str:
        """Build JUnit XML format for CI/CD integration."""
        test_cases = []

        all_results = (
            report.accessibility_results +
            report.visual_results +
            report.responsive_results
        )

        for result in all_results:
            if result.passed:
                test_cases.append(
                    f'    <testcase name="{result.test_name}" classname="{result.category.value}"/>'
                )
            else:
                severity = result.severity.value if result.severity else "moderate"
                message = result.message.replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')
                test_cases.append(f'''    <testcase name="{result.test_name}" classname="{result.category.value}">
      <failure type="{severity}" message="{message}">
{result.suggested_fix or ''}
      </failure>
    </testcase>''')

        return f'''<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="Freya Tests" tests="{report.total_tests}" failures="{report.failed}" timestamp="{report.tested_at}">
{chr(10).join(test_cases)}
</testsuite>'''
