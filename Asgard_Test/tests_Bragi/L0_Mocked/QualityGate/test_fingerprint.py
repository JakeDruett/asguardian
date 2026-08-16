"""
Tests for finding fingerprints (Plan Heimdall-09 §1 / Bragi-06 §3.2).

Fingerprints must be stable across line-shifting refactors (AST anchoring)
and deterministic across repeat computation.
"""

from Asgard.Bragi.QualityGate.fingerprint import (
    compute_fingerprint,
    fingerprint_finding,
    fingerprint_with_anchor,
    is_signed_fingerprint,
    normalize_path,
    normalize_snippet,
    sign_fingerprint,
    unsigned_fingerprint,
)
from Asgard.Bragi.QualityGate.models.quality_gate_models import GateFinding
from Asgard.Bragi.QualityGate.services._differential_engine import (
    ensure_fingerprint,
)


SOURCE = '''
def handler(request):
    query = "SELECT * FROM users WHERE id = %s" % request.args["id"]
    return db.execute(query)
'''

SOURCE_SHIFTED = '''
# A new comment block inserted above.
# Another line.
# And a third, shifting everything down.


def handler(request):
    query = "SELECT * FROM users WHERE id = %s" % request.args["id"]
    return db.execute(query)
'''


class TestPathAndSnippetNormalization:
    def test_normalize_path_posix(self):
        assert normalize_path("src\\pkg\\mod.py") == "src/pkg/mod.py"

    def test_normalize_path_strips_leading_dot_slash(self):
        assert normalize_path("./src/mod.py") == "src/mod.py"

    def test_normalize_snippet_collapses_whitespace(self):
        assert normalize_snippet("a  =\t 1\n") == "a = 1"


class TestAstAnchoredFingerprint:
    def test_deterministic(self):
        fp1 = compute_fingerprint("SQLI", "src/mod.py", source=SOURCE, line=3)
        fp2 = compute_fingerprint("SQLI", "src/mod.py", source=SOURCE, line=3)
        assert fp1 == fp2

    def test_line_shift_immune(self):
        """A refactor that only shifts lines must not churn the fingerprint."""
        fp_before = compute_fingerprint("SQLI", "src/mod.py", source=SOURCE, line=3)
        fp_after = compute_fingerprint(
            "SQLI", "src/mod.py", source=SOURCE_SHIFTED, line=8
        )
        assert fp_before == fp_after

    def test_uses_ast_anchor_for_python(self):
        _, anchor = fingerprint_with_anchor(
            "SQLI", "src/mod.py", source=SOURCE, line=3
        )
        assert anchor == "ast"

    def test_different_rule_different_fingerprint(self):
        fp1 = compute_fingerprint("SQLI", "src/mod.py", source=SOURCE, line=3)
        fp2 = compute_fingerprint("XSS", "src/mod.py", source=SOURCE, line=3)
        assert fp1 != fp2

    def test_different_file_different_fingerprint(self):
        fp1 = compute_fingerprint("SQLI", "src/a.py", source=SOURCE, line=3)
        fp2 = compute_fingerprint("SQLI", "src/b.py", source=SOURCE, line=3)
        assert fp1 != fp2

    def test_changed_function_body_changes_fingerprint(self):
        changed = SOURCE.replace('request.args["id"]', 'request.args["name"]')
        fp1 = compute_fingerprint("SQLI", "src/mod.py", source=SOURCE, line=3)
        fp2 = compute_fingerprint("SQLI", "src/mod.py", source=changed, line=3)
        assert fp1 != fp2


class TestFallbackAnchors:
    def test_snippet_fallback_for_non_python(self):
        """Non-parseable source falls back to whitespace-normalized snippet."""
        js = "function f() { eval(userInput); }"
        fp1, anchor1 = fingerprint_with_anchor(
            "EVAL", "src/app.js", source=js, line=1, snippet="eval(userInput);"
        )
        fp2, anchor2 = fingerprint_with_anchor(
            "EVAL", "src/app.js", line=1, snippet="  eval(userInput);  "
        )
        assert anchor1 == "snippet"
        assert anchor2 == "snippet"
        assert fp1 == fp2

    def test_file_fallback_when_nothing_available(self):
        fp, anchor = fingerprint_with_anchor("RULE", "src/app.go")
        assert anchor == "file"
        assert len(fp) == 64

    def test_windows_and_posix_paths_agree(self):
        fp1 = compute_fingerprint("R", "src\\mod.py", snippet="x = 1")
        fp2 = compute_fingerprint("R", "src/mod.py", snippet="x = 1")
        assert fp1 == fp2

    def test_two_findings_in_one_file_get_distinct_fingerprints(self):
        fp1 = compute_fingerprint("SQLI", "src/app.py", line=3)
        fp2 = compute_fingerprint("SQLI", "src/app.py", line=10)
        assert fp1 != fp2

    def test_two_findings_same_line_differ_by_message(self):
        fp1 = compute_fingerprint("SQLI", "src/app.py", line=3, message="concat")
        fp2 = compute_fingerprint("SQLI", "src/app.py", line=3, message="format")
        assert fp1 != fp2

    def test_empty_snippet_still_uses_line_and_message(self):
        fp_file = compute_fingerprint("SQLI", "src/app.py")
        fp_line = compute_fingerprint("SQLI", "src/app.py", line=3)
        fp_msg = compute_fingerprint("SQLI", "src/app.py", message="sqli")
        assert fp_file != fp_line
        assert fp_file != fp_msg
        assert fp_line != fp_msg


class TestCallerFingerprintTrust:
    def test_unsigned_fingerprint_is_recomputed(self):
        planted = "ab" * 32
        finding = GateFinding(
            rule_id="SQLI", file_path="src/app.py", line=3,
            snippet="db.execute(q)", fingerprint=planted,
        )
        out = ensure_fingerprint(finding)
        assert out.fingerprint != planted
        assert out.fingerprint == fingerprint_finding(finding)

    def test_forged_signed_fingerprint_is_recomputed(self, monkeypatch):
        monkeypatch.setenv("ASGARD_QG_HMAC_KEY", "test-qg-key")
        planted = f"qg1.{'ab' * 32}.{'00' * 32}"
        finding = GateFinding(
            rule_id="SQLI", file_path="src/app.py", line=3,
            snippet="db.execute(q)", fingerprint=planted,
        )
        out = ensure_fingerprint(finding)
        assert out.fingerprint != "ab" * 32
        assert out.fingerprint == fingerprint_finding(finding)

    def test_signed_fingerprint_is_kept(self, monkeypatch):
        monkeypatch.setenv("ASGARD_QG_HMAC_KEY", "test-qg-key")
        digest = compute_fingerprint("SQLI", "src/app.py", line=99, message="kept")
        signed = sign_fingerprint(digest)
        finding = GateFinding(
            rule_id="SQLI", file_path="src/app.py", line=3,
            message="other", fingerprint=signed,
        )
        out = ensure_fingerprint(finding)
        assert is_signed_fingerprint(signed)
        assert unsigned_fingerprint(signed) == digest
        assert out.fingerprint == digest

    def test_signed_fingerprint_without_key_is_recomputed(self, monkeypatch):
        monkeypatch.setenv("ASGARD_QG_HMAC_KEY", "test-qg-key")
        digest = compute_fingerprint("SQLI", "src/app.py", line=99)
        signed = sign_fingerprint(digest)
        monkeypatch.delenv("ASGARD_QG_HMAC_KEY", raising=False)
        finding = GateFinding(
            rule_id="SQLI", file_path="src/app.py", line=3, fingerprint=signed,
        )
        out = ensure_fingerprint(finding)
        assert out.fingerprint == fingerprint_finding(finding)
        assert out.fingerprint != digest
