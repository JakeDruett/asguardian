"""
Meta-tests for the ``neutral_tmp`` fixture (MasterPlan Phase 1.1).

Demonstrates the temp-dir path trap honestly, WITHOUT weakening the
test-context suppression engine:

* Scanners suppress/downgrade findings in files whose *path* classifies as
  test context (``Asgard.Heimdall.Security.context.test_context``). That
  suppression is correct and intended for real test code.
* The trap: a known-bad security fixture that a test writes to disk for
  scanning can land under a test-shaped path (a ``tests/`` segment plus a
  ``test_*.py`` filename — e.g. under a ``--basetemp`` pointed at a tests
  tree, or simply because the test builds a "realistic" project layout).
  The scanner then mutes the finding and the test silently stops testing
  what it thinks it tests.
* ``neutral_tmp`` (shared conftest) yields a directory whose absolute path
  contains no test-like tokens, so path-based classification is always
  PRODUCTION for fixtures beneath it.

The suppression behavior itself is asserted as CORRECT here (the
test-shaped copy IS suppressed by default and retained under
``include_test_context=True``) — these tests document the mechanism, they
do not fight it.
"""

from Asgard.Heimdall.cli.handlers._security_dispatch import run_dispatch_scan
from Asgard.Heimdall.Security.context.test_context import (
    ContextTag,
    classify_file_context,
)

# Known-bad fixture: module-level pickle.loads (rule L2.pickle_load).
# Deliberately contains NO test_* functions / asserts / fixture decorators,
# so AST-level TEST_FUNCTION tainting cannot fire — any suppression observed
# below is driven purely by the file's PATH.
_KNOWN_BAD = "import pickle\nresult = pickle.loads(payload)\n"

_RULE = "L2.pickle_load"


def _rule_hits(entries):
    return [e for e in entries if e["rule_id"] == _RULE]


class TestNeutralTmpPathIsNeutral:
    def test_path_has_no_test_like_tokens(self, neutral_tmp):
        assert "test" not in str(neutral_tmp).lower()
        assert "spec" not in str(neutral_tmp).lower()

    def test_files_beneath_it_classify_as_production(self, neutral_tmp):
        f = neutral_tmp / "app.py"
        assert classify_file_context(str(f)) is ContextTag.PRODUCTION


class TestTempDirTrap:
    def test_known_bad_fixture_flagged_under_neutral_path(self, neutral_tmp):
        (neutral_tmp / "app.py").write_text(_KNOWN_BAD)
        entries = run_dispatch_scan(neutral_tmp)
        assert _rule_hits(entries), (
            "known-bad fixture under a neutral path must be flagged"
        )

    def test_same_fixture_suppressed_under_test_shaped_path(self, neutral_tmp):
        """
        The trap, demonstrated: byte-identical known-bad code, but the file
        sits at <dir>/tests/test_app.py — a test-shaped path. Default scans
        suppress it (correct for real test code; silently fatal for a
        security fixture a test meant to scan).
        """
        tests_dir = neutral_tmp / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_app.py").write_text(_KNOWN_BAD)

        assert classify_file_context(str(tests_dir / "test_app.py")) is ContextTag.TEST_UNIT
        assert _rule_hits(run_dispatch_scan(neutral_tmp)) == [], (
            "test-context suppression is intended behavior — if this ever "
            "fires by default, the suppression engine changed"
        )
        # Suppressed findings are retained, not deleted: visible on opt-in.
        included = run_dispatch_scan(neutral_tmp, include_test_context=True)
        assert _rule_hits(included), (
            "suppressed findings must survive under include_test_context"
        )

    def test_neutral_vs_test_shaped_same_fixture_side_by_side(self, neutral_tmp):
        """Same content, two paths: only the neutral one is flagged by default."""
        (neutral_tmp / "app.py").write_text(_KNOWN_BAD)
        tests_dir = neutral_tmp / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_app.py").write_text(_KNOWN_BAD)

        hits = _rule_hits(run_dispatch_scan(neutral_tmp))
        assert hits
        assert all("tests" not in h["file_path"].rsplit("/", 2)[-2] for h in hits)
        assert all(h["file_path"].endswith("app.py") for h in hits)
        assert not any(h["file_path"].endswith("test_app.py") for h in hits)


class TestPytestTmpPathBehaviorDocumented:
    def test_bare_tmp_path_currently_classifies_production(self, tmp_path):
        """
        Honest note: pytest's tmp_path (…/pytest-N/test_<name>0/) does NOT
        trip the current word-boundary classifier by itself. The exposure is
        (a) any test-shaped segment/filename created beneath it, and (b)
        ``--basetemp`` overrides that put a tests/ segment (or any naive
        substring "test" heuristic — the path always contains "pytest") into
        every fixture path. neutral_tmp removes the whole class of hazard.
        """
        assert classify_file_context(str(tmp_path / "app.py")) is ContextTag.PRODUCTION
        assert "test" in str(tmp_path).lower()  # why substring heuristics trip
