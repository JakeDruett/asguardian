"""Phase-4 L3 meta-test: every public Pydantic model has L3 contract coverage.

See ``_Docs/Delivered/Planning/TestCoverage/L3_Plan.md``.

A model counts as *covered* when at least one test file under
``Asgard_Test/tests_*/L3_Contract/`` imports it from the module where it is
defined (``from <module> import <Name>`` — aliases and ``import *`` handled).
Matching is on the full dotted module path, so same-named models in different
modules are tracked independently.

Models with no coverage yet must be listed in ``l3_uncovered_allowlist.txt``.
The allowlist is a ratchet: it may only shrink. The test fails if
  (a) a model is neither covered nor allowlisted (new model without L3 tests),
  (b) an allowlist entry refers to a model that no longer exists, or
  (c) an allowlist entry IS now covered (stale entry — remove it).

Deterministic, no network, cwd-independent.
"""

import ast
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
ALLOWLIST_PATH = Path(__file__).resolve().parent / "l3_uncovered_allowlist.txt"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _inventory() -> set:
    """All public pydantic models in Asgard, as dotted 'module.Name' paths."""
    scripts_dir = str(REPO_ROOT / "_scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    from list_pydantic_models import iter_public_models

    return set(iter_public_models())


def _l3_test_files():
    yield from sorted(REPO_ROOT.glob("Asgard_Test/tests_*/L3_Contract/test_*.py"))


def _imports_in(path: Path):
    """Yield ('module', 'name') pairs imported by a test file.

    ``from M import A as B`` yields (M, A); ``from M import *`` yields (M, '*').
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            for alias in node.names:
                yield node.module, alias.name


def _covered_models(inventory: set) -> set:
    star_modules = set()
    pairs = set()
    for test_file in _l3_test_files():
        for module, name in _imports_in(test_file):
            if name == "*":
                star_modules.add(module)
            else:
                pairs.add(f"{module}.{name}")
    covered = inventory & pairs
    for dotted in inventory:
        if dotted.rsplit(".", 1)[0] in star_modules:
            covered.add(dotted)
    return covered


def _allowlist() -> list:
    entries = []
    for line in ALLOWLIST_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            entries.append(line)
    return entries


def test_allowlist_is_sorted_and_unique():
    entries = _allowlist()
    assert entries == sorted(set(entries)), (
        "l3_uncovered_allowlist.txt must be sorted and free of duplicates"
    )


def test_every_public_model_has_l3_coverage_or_is_allowlisted():
    inventory = _inventory()
    assert inventory, "model inventory came back empty — discovery is broken"
    covered = _covered_models(inventory)
    allowlisted = set(_allowlist())

    missing = sorted(inventory - covered - allowlisted)
    assert not missing, (
        "Public pydantic models with no L3 contract coverage and no allowlist "
        "entry (write L3 tests for them; do NOT add to the allowlist — it only "
        "ratchets down):\n  " + "\n  ".join(missing)
    )

    dead = sorted(allowlisted - inventory)
    assert not dead, (
        "Allowlist entries that no longer exist in the codebase — remove them "
        "from l3_uncovered_allowlist.txt:\n  " + "\n  ".join(dead)
    )

    stale = sorted(allowlisted & covered)
    assert not stale, (
        "Allowlist entries that now HAVE L3 coverage — ratchet: remove them "
        "from l3_uncovered_allowlist.txt:\n  " + "\n  ".join(stale)
    )


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
