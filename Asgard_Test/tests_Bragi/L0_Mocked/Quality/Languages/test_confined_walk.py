"""CH-0042: language analyzers must confine walks and honor advertised limits."""

import tempfile
from pathlib import Path

from Asgard.Bragi.Quality.languages._confined_walk import (
    DEFAULT_MAX_LINE_CHARS,
    JS_EXTENSIONS,
    collect_regex_findings,
    iter_language_files,
    normalize_extensions,
    read_capped_source,
)
from Asgard.Bragi.Quality.languages.java.models.java_models import JavaScanConfig
from Asgard.Bragi.Quality.languages.java.services.java_analyzer import JavaAnalyzer
from Asgard.Bragi.Quality.languages.javascript.models.js_models import JSAnalysisConfig
from Asgard.Bragi.Quality.languages.javascript.services.js_analyzer import JSAnalyzer
from Asgard.Bragi.Quality.languages.shell.models.shell_models import ShellAnalysisConfig
from Asgard.Bragi.Quality.languages.shell.services.shell_analyzer import ShellAnalyzer
from Asgard.Bragi.Quality.languages.typescript.services.ts_analyzer import TSAnalyzer


def _layout_escape(tmpdir: Path, inside_name: str, outside_name: str, body: str):
    root = tmpdir / "scan"
    outside = tmpdir / "outside"
    root.mkdir()
    outside.mkdir()
    (root / inside_name).write_text("const x = 1;\n" if inside_name.endswith(".js") else body)
    (outside / outside_name).write_text(body)
    (root / "escape").symlink_to(outside)
    (root / f"link_{outside_name}").symlink_to(outside / outside_name)
    return root, outside


class TestNormalizeExtensions:
    def test_drops_wildcards_and_unknown(self):
        assert normalize_extensions([".js", "*", "", ".exe", ".."], JS_EXTENSIONS) == {".js"}

    def test_adds_dot_and_lowercases(self):
        assert normalize_extensions(["JS", ".JsX"], JS_EXTENSIONS) == {".js", ".jsx"}


class TestIterLanguageFiles:
    def test_dir_symlink_escape_not_yielded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, outside = _layout_escape(
                Path(tmp), "app.js", "secret.js", 'eval("outside");\n'
            )
            files = list(
                iter_language_files(
                    root,
                    include_extensions=[".js"],
                    allowed_extensions=JS_EXTENSIONS,
                )
            )
            names = {path.name for path in files}
            assert names == {"app.js"}
            assert all(path.resolve().is_relative_to(root.resolve()) for path in files)
            assert not any(path.is_symlink() for path in files)
            assert (outside / "secret.js").resolve() not in {p.resolve() for p in files}

    def test_exclude_patterns_honored(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "ok.js").write_text("const x = 1;\n")
            vendor = root / "node_modules"
            vendor.mkdir()
            (vendor / "evil.js").write_text('eval("x");\n')
            (root / "bundle.min.js").write_text('eval("x");\n')
            files = list(
                iter_language_files(
                    root,
                    include_extensions=[".js"],
                    exclude_patterns=["node_modules", "*.min.js"],
                    allowed_extensions=JS_EXTENSIONS,
                )
            )
            assert {path.name for path in files} == {"ok.js"}

    def test_cycle_dir_symlink_does_not_recurse(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "ok.js").write_text("const x = 1;\n")
            (root / "loop").symlink_to(root)
            files = list(
                iter_language_files(
                    root,
                    include_extensions=[".js"],
                    allowed_extensions=JS_EXTENSIONS,
                )
            )
            assert [path.name for path in files] == ["ok.js"]


class TestReadCappedSource:
    def test_truncates_file_over_max_file_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "big.js"
            path.write_text("\n".join(f"const a{i} = {i};" for i in range(20)) + "\neval('late');\n")
            source = read_capped_source(path, max_file_lines=5)
            assert source is not None
            assert len(source.lines) == 5
            assert source.exceeded_line_limit is True
            assert all("eval" not in line for line in source.lines)

    def test_caps_line_length_before_return(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "long.js"
            path.write_text(("x" * 8000) + 'eval("x");\n')
            source = read_capped_source(path, max_line_chars=64)
            assert source is not None
            assert len(source.lines) == 1
            assert len(source.lines[0]) == 64
            assert "eval" not in source.lines[0]

    def test_skips_file_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "real.js"
            target.write_text('eval("x");\n')
            link = root / "alias.js"
            link.symlink_to(target)
            assert read_capped_source(link) is None


class TestJSAnalyzerConfinement:
    def test_dir_symlink_escape_not_scanned(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, _outside = _layout_escape(
                Path(tmp), "app.js", "secret.js", 'eval("outside");\n'
            )
            (root / "app.js").write_text("const x = 1;\n")
            config = JSAnalysisConfig(
                enabled_rules=["js.no-eval"],
                exclude_patterns=["node_modules"],
            )
            report = JSAnalyzer(config).analyze(scan_path=str(root))
            assert report.files_analyzed == 1
            assert "js.no-eval" not in {f.rule_id for f in report.findings}
            assert not any("secret.js" in f.file_path for f in report.findings)

    def test_exclude_patterns_honored(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "app.js").write_text('eval("inside");\n')
            hidden = root / "node_modules"
            hidden.mkdir()
            (hidden / "evil.js").write_text('eval("hidden");\n')
            config = JSAnalysisConfig(enabled_rules=["js.no-eval"])
            report = JSAnalyzer(config).analyze(scan_path=str(root))
            assert report.files_analyzed == 1
            assert all("node_modules" not in f.file_path for f in report.findings)
            assert any("app.js" in f.file_path for f in report.findings)

    def test_huge_file_not_fully_regexed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            early = "const x = 1;\n"
            late = 'eval("late");\n'
            (root / "big.js").write_text(early + ("const y = 2;\n" * 10) + late)
            config = JSAnalysisConfig(
                enabled_rules=["js.no-eval"],
                max_file_lines=3,
            )
            report = JSAnalyzer(config).analyze(scan_path=str(root))
            assert "js.no-eval" not in {f.rule_id for f in report.findings}

    def test_max_findings_stops_adding(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.js").write_text('eval("a");\n')
            (root / "b.js").write_text('eval("b");\n')
            (root / "c.js").write_text('eval("c");\n')
            config = JSAnalysisConfig(enabled_rules=["js.no-eval"], max_findings=1)
            report = JSAnalyzer(config).analyze(scan_path=str(root))
            assert report.total_findings == 1
            assert len(report.findings) == 1


class TestJavaAnalyzerConfinement:
    def test_dir_symlink_escape_not_scanned(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            root = tmpdir / "scan"
            outside = tmpdir / "outside"
            root.mkdir()
            outside.mkdir()
            (root / "Safe.java").write_text("class Safe {}\n")
            (outside / "Leak.java").write_text(
                'class Leak { void f() { stmt.execute("SELECT " + x); } }\n'
            )
            (root / "escape").symlink_to(outside)
            config = JavaScanConfig(exclude_patterns=["vendor"])
            report = JavaAnalyzer(config).analyze(scan_path=str(root))
            assert not any("Leak.java" in f.file_path for f in report.findings)
            assert not any("sql-injection" == f.rule_id for f in report.findings)

    def test_exclude_patterns_honored(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "Ok.java").write_text(
                'class Ok { void f() { stmt.execute("SELECT " + x); } }\n'
            )
            vendor = root / "vendor"
            vendor.mkdir()
            (vendor / "Bad.java").write_text(
                'class Bad { void f() { stmt.execute("SELECT " + y); } }\n'
            )
            config = JavaScanConfig(exclude_patterns=["vendor"])
            report = JavaAnalyzer(config).analyze(scan_path=str(root))
            assert all("vendor" not in f.file_path for f in report.findings)
            assert any(f.rule_id == "java.sql-injection" for f in report.findings)

    def test_huge_file_not_fully_regexed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            body = "class Huge {\n" + ("    int x;\n" * 8) + '    void f() { stmt.execute("SELECT " + z); }\n}\n'
            (root / "Huge.java").write_text(body)
            config = JavaScanConfig(exclude_patterns=[], max_file_lines=3)
            report = JavaAnalyzer(config).analyze(scan_path=str(root))
            assert not any(f.rule_id == "java.sql-injection" for f in report.findings)

    def test_max_findings_stops_adding(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("A", "B", "C"):
                (root / f"{name}.java").write_text(
                    f'class {name} {{ void f() {{ stmt.execute("SELECT " + x); }} }}\n'
                )
            config = JavaScanConfig(exclude_patterns=[], max_findings=1)
            report = JavaAnalyzer(config).analyze(scan_path=str(root))
            assert report.total_findings == 1


class TestShellAnalyzerConfinement:
    def test_shebang_walk_skips_dir_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            root = tmpdir / "scan"
            outside = tmpdir / "outside"
            root.mkdir()
            outside.mkdir()
            (root / "ok.sh").write_text("#!/bin/bash\nset -eu\necho ok\n")
            (outside / "leak").write_text("#!/bin/bash\nset -eu\neval $cmd\n")
            (root / "escape").symlink_to(outside)
            config = ShellAnalysisConfig(
                also_check_shebangs=True,
                enabled_rules=["shell.eval-injection"],
            )
            report = ShellAnalyzer(config).analyze(scan_path=str(root))
            assert not any("leak" in f.file_path for f in report.findings)
            assert "shell.eval-injection" not in {f.rule_id for f in report.findings}


class TestTSAnalyzerConfinement:
    def test_dir_symlink_escape_not_scanned(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            root = tmpdir / "scan"
            outside = tmpdir / "outside"
            root.mkdir()
            outside.mkdir()
            (root / "app.ts").write_text("const x: number = 1;\n")
            (outside / "secret.ts").write_text('eval("outside");\n')
            (root / "escape").symlink_to(outside)
            config = JSAnalysisConfig(enabled_rules=["js.no-eval"], language="typescript")
            report = TSAnalyzer(config).analyze(scan_path=str(root))
            assert report.files_analyzed == 1
            assert "js.no-eval" not in {f.rule_id for f in report.findings}


def test_collect_regex_findings_respects_max_findings():
    def _rule(file_path, lines, enabled=True):
        return ["hit"] if enabled else []

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "a.js").write_text("x\n")
        (root / "b.js").write_text("y\n")
        findings = collect_regex_findings(
            root,
            include_extensions=[".js"],
            exclude_patterns=[],
            allowed_extensions=JS_EXTENSIONS,
            max_file_lines=10,
            max_findings=1,
            rules=[_rule],
            enabled_for=lambda _rid: True,
        )
        assert findings == ["hit"]


def test_default_max_line_chars_is_bounded():
    assert DEFAULT_MAX_LINE_CHARS <= 8192
