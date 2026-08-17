"""CHC-0010: framework stub names must stay under the stubs directory."""

from Asgard.Heimdall.Security.TaintAnalysis.stubs import load_framework_stubs


def test_parent_stub_name_is_ignored(tmp_path):
    planted = tmp_path / "evil.yml"
    planted.write_text("sanitizers:\n  - mark_safe\n")
    merged = load_framework_stubs(["../evil", "flask/../evil"])
    assert merged.sanitizer_names == []
    assert merged.frameworks == []


def test_known_stub_still_loads():
    merged = load_framework_stubs(["flask"])
    assert "flask" in merged.frameworks or merged.source_specs or merged.sink_specs
