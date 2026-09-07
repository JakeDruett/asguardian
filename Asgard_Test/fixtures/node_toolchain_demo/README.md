# node_toolchain_demo (fixture)

This is a deliberately broken Node project used by
`Asgard_Test/tests_Bragi/L0_Mocked/Quality/Languages/test_node_toolchain_analyzers.py`
to exercise Asgard's Node toolchain-orchestration analysers end to end.

It intentionally carries:

- an outdated, vulnerable `lodash` (`4.17.4`), pinned in `package.json` so that
  `NodeAuditAnalyzer` has a real `npm audit` finding to detect and report as
  `npm-audit::lodash`
- ESLint defects (`eslint.config.js`)
- TypeScript type errors (`type_errors.ts`)

**Do not "fix" the pinned `lodash` version, and do not run `npm audit fix` or
any dependency-update tool against this directory.** Doing so removes the
known vulnerability the test asserts on and breaks
`test_npm_audit_either_finds_the_known_vulnerability_or_reports_offline` (and
any other test relying on this fixture's defects being present). If a newer
or different known vulnerability is ever needed for this fixture, update it
deliberately alongside the test assertions that depend on it, in the same
change.
