# Line Coverage Baseline — 2026-08-13 (MasterPlan Phase 2.4)

Measured per module with `python3 -m pytest Asgard_Test/tests_<Module> -q
--cov=Asgard/<Module> --cov-report=term` (pytest-cov 7.1.0, branch off main
at 69a8d43). Each module's own test tree only — cross-package (L2) and perf
(L8) suites excluded, so these are conservative lower bounds.

## Per-module baseline

| Module    | Stmts  | Miss  | Coverage | Notes |
|-----------|-------:|------:|---------:|-------|
| MCP       |    286 |   134 |  53.15%  | worst; `_mcp_tools.py` at 20% |
| Bragi     | 24,585 | 8,232 |  66.52%  | largest module |
| Reporting |    746 |   239 |  67.96%  | formatters nearly untested |
| Forseti   | 15,517 | 4,798 |  69.08%  | 28 collection errors under `-p no:benchmark` (benchmark fixtures); count from that run |
| Dashboard |    312 |    89 |  71.47%  | small |
| Freya     | 10,431 | 2,793 |  73.22%  | slow suite (~12.5 min) |
| Volundr   |  7,655 | 1,901 |  75.17%  | |
| Verdandi  |  8,390 | 1,639 |  80.46%  | meets 80% bar |
| Heimdall  |    see note    |   —      | run exceeded the measurement time-box (>20 min); re-measure separately |

## Worst substantive gaps selected for uplift (this wave)

CLI arg-plumbing and `__init__` re-export files were excluded from selection.

1. **MCP tool implementations** — `Asgard/MCP/server/_mcp_tools.py` (20.00%, 108/135 lines missed). All 8 MCP tool handlers were untested.
2. **Reporting: GitHub Actions formatting** — `github_formatter.py` (40.78%) + `_github_format_helpers.py` (17.31%).
3. **Reporting: HTML report generation** — `html_generator.py` (35.82%) + `_html_report_builders.py` (8.57%).

## Bugs found by the new tests (fixed in this branch)

Writing behavior-asserting tests against `_mcp_tools.py` exposed that its
defensive `getattr(..., default)` style was silently masking wrong field
names — the tools "worked" but returned empty/zero data:

- `tool_security_scan`: read `report.findings` / `total_findings` /
  `findings_by_severity`, none of which exist on `SecurityReport` — always
  returned 0 findings. Now reads `total_issues`, severity counts, and
  findings from `vulnerability_report` / `secrets_report`.
- `tool_list_issues`: called `IssueTracker.list_issues()` (method does not
  exist — runtime `AttributeError`) with `IssueFilter(project_path=...,
  statuses=..., limit=...)` (none are IssueFilter fields). Now calls
  `get_issues(project_path, IssueFilter(status=[...]))` and applies the
  limit by slicing.
- `tool_quality_analyze`: read `result.total_files` / `total_violations` /
  `violations_by_severity` (not `AnalysisResult` fields) — always 0/0/{}.
  Now reads `total_files_scanned`, `len(violations)`,
  `get_violations_by_severity()`.
- `tool_quality_gate`: read `cr.metric` / `cr.status` / `cr.threshold`
  directly on `ConditionResult` (they live on `cr.condition`, and `passed`
  is tri-state) — conditions always serialized as empty strings. Now maps
  `passed True/False/None` to `passed/failed/not_evaluated` honestly.

## Before / after (this wave)

| Area | Before | After |
|------|-------:|------:|
| MCP module total | 53.15% | 90.14% |
| — `MCP/server/_mcp_tools.py` | 20.00% | 97.90% |
| Reporting module total | 67.96% | 91.96% |
| — `Reporting/github_formatter.py` | 40.78% | 100.00% |
| — `Reporting/_github_format_helpers.py` | 17.31% | 100.00% |
| — `Reporting/html_generator.py` | 35.82% | 100.00% |
| — `Reporting/_html_report_builders.py` | 8.57% | 100.00% |

New tests: `Asgard_Test/tests_MCP/test_mcp_tools.py` (28),
`Asgard_Test/tests_Reporting/L0_Mocked/test_github_formatter.py` (24),
`Asgard_Test/tests_Reporting/L0_Mocked/test_html_generator.py` (23).

## Remaining worst gaps (next candidates)

- Bragi 66.52% — by far the largest absolute miss count (8,232 lines).
- Forseti 69.08% — plus 28 collection errors when benchmark plugin disabled.
- Heimdall — needs a bounded re-measure (suite runtime > 20 min with cov).
- `Reporting/History/services/_history_db.py` (0%, 2 stmts) and the PR
  decorators (76–80%) are the residual Reporting gaps.
