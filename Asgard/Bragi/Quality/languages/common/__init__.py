"""Language-agnostic toolchain-orchestration abstraction.

Shared by every Heimdall quality analyser that works by shelling out to an
ecosystem's own mature tool (cargo clippy, cargo audit, ESLint, npm audit,
tsc) rather than reimplementing analysis in Python. See tool_models.py for
the shared finding/report shape and tool_runner.py for the shared subprocess
and tool-discovery helpers.
"""
