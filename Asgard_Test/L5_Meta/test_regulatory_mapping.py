"""
L5 Regulatory-Mapping Meta-Test.

Enforces two invariants across the whole L5 layer:

1. Every test class in any ``*/L5_Compliance/test_*.py`` file maps to a
   regulatory reference (CWE / WCAG / CIS, plus the documented OWASP-Axx
   and SRE-* extensions) via ``l5_reference_manifest.yaml``. A new L5
   suite without a manifest entry fails here by design.

2. The known-bad fixture library (``Asgard_Test/L5_known_bad``) and its
   README manifest stay in sync: every fixture on disk is listed, every
   listed fixture exists, and every fixture directory is named after a CWE.
"""

import ast
import re
from pathlib import Path

import yaml

from Asgard_Test.L5_Meta.l5_fixtures import LIBRARY_ROOT

ASGARD_TEST_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = Path(__file__).resolve().parent / "l5_reference_manifest.yaml"

#: CWE / WCAG / CIS references, plus documented OWASP / SRE extensions.
REFERENCE_RE = re.compile(
    r"^(CWE-\d+"
    r"|WCAG-\d+\.\d+(\.\d+)?"
    r"|CIS-[A-Za-z0-9][A-Za-z0-9.\-]*"
    r"|OWASP-A\d{2}"
    r"|SRE-[A-Za-z][A-Za-z0-9]*)$"
)

CWE_DIR_RE = re.compile(r"^CWE-\d+_[a-z0-9_]+$")


def _load_manifest() -> dict:
    with open(MANIFEST_PATH, encoding="utf-8") as handle:
        manifest = yaml.safe_load(handle)
    assert isinstance(manifest, dict) and manifest, "Empty L5 reference manifest"
    return manifest


def _l5_test_classes() -> dict:
    """Map '<relpath>::<ClassName>' -> file path for all L5 test classes."""
    classes: dict = {}
    for path in sorted(ASGARD_TEST_ROOT.glob("*/L5_Compliance/test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        relative = path.relative_to(ASGARD_TEST_ROOT).as_posix()
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
                classes[f"{relative}::{node.name}"] = path
    return classes


class TestRegulatoryMapping:
    """Every L5 test class must map to a CWE/WCAG/CIS reference."""

    def test_manifest_exists_and_is_wellformed(self) -> None:
        manifest = _load_manifest()
        bad = {k: v for k, v in manifest.items()
               if not (isinstance(v, str) and REFERENCE_RE.match(v))}
        assert not bad, f"Malformed regulatory references: {bad}"

    def test_every_l5_class_has_a_reference(self) -> None:
        manifest = _load_manifest()
        classes = _l5_test_classes()
        assert classes, "No L5_Compliance test classes discovered"
        unmapped = sorted(set(classes) - set(manifest))
        assert not unmapped, (
            "L5 test classes missing a CWE/WCAG/CIS reference in "
            f"{MANIFEST_PATH.name}: {unmapped}"
        )

    def test_no_stale_manifest_entries(self) -> None:
        manifest = _load_manifest()
        classes = _l5_test_classes()
        stale = sorted(set(manifest) - set(classes))
        assert not stale, f"Manifest entries with no matching L5 class: {stale}"


class TestKnownBadLibraryIntegrity:
    """Fixture library and its README manifest must stay in sync."""

    @staticmethod
    def _fixtures_on_disk() -> set:
        return {
            p.relative_to(LIBRARY_ROOT).as_posix()
            for p in LIBRARY_ROOT.rglob("*")
            if p.is_file() and p.name not in {"README.md", ".gitignore"}
        }

    @staticmethod
    def _fixtures_in_readme() -> set:
        readme = (LIBRARY_ROOT / "README.md").read_text(encoding="utf-8")
        rows = re.findall(r"^\| (CWE-\d+_[^ |]+/[^ |]+) \|", readme, re.MULTILINE)
        return set(rows)

    def test_library_is_nonempty(self) -> None:
        assert len(self._fixtures_on_disk()) >= 15

    def test_every_fixture_dir_is_cwe_named(self) -> None:
        bad = [d.name for d in LIBRARY_ROOT.iterdir()
               if d.is_dir() and not CWE_DIR_RE.match(d.name)]
        assert not bad, f"Fixture directories not named CWE-<id>_<slug>: {bad}"

    def test_every_fixture_listed_in_readme(self) -> None:
        missing = sorted(self._fixtures_on_disk() - self._fixtures_in_readme())
        assert not missing, f"Fixtures on disk missing from README manifest: {missing}"

    def test_no_phantom_readme_rows(self) -> None:
        phantom = sorted(self._fixtures_in_readme() - self._fixtures_on_disk())
        assert not phantom, f"README manifest rows without a fixture file: {phantom}"

    def test_every_fixture_header_names_its_cwe(self) -> None:
        """Text fixtures must carry the CWE of their directory in a header."""
        failures = []
        for relative in sorted(self._fixtures_on_disk()):
            cwe = relative.split("_", 1)[0]  # e.g. 'CWE-89'
            text = (LIBRARY_ROOT / relative).read_text(encoding="utf-8")
            if cwe not in text and not relative.endswith((".json",)):
                failures.append(relative)
        assert not failures, f"Fixtures missing their CWE header comment: {failures}"
