"""
Tests for the HTML report generator and quality dashboard builder.

L0 behavior tests using lightweight report doubles (SimpleNamespace) —
asserts document structure, escaping, thresholds, and card/section logic.
"""

from types import SimpleNamespace

from Asgard.Reporting.html_generator import HTMLReportGenerator, ScoreCard


def _typing_report(**overrides):
    defaults = dict(
        scan_path="/repo",
        coverage_percentage=90.0,
        threshold=80.0,
        total_functions=10,
        fully_annotated=9,
        is_passing=True,
        files_scanned=3,
        files_analyzed=[],
        unannotated_functions=[],
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class TestBuildingBlocks:
    def setup_method(self):
        self.gen = HTMLReportGenerator(title="T")

    def test_wrap_html_is_complete_document(self):
        html = self.gen._wrap_html("<p>hi</p>", "Page")
        assert html.startswith("<!DOCTYPE html>")
        assert "<title>Page</title>" in html
        assert "<p>hi</p>" in html
        assert html.rstrip().endswith("</html>")

    def test_header_includes_subtitle_when_given(self):
        header = self.gen._generate_header("sub")
        assert "<div class='meta'>sub</div>" in header
        assert "Generated:" in header

    def test_header_omits_subtitle_when_empty(self):
        assert self.gen._generate_header("").count("class='meta'") == 1

    def test_score_card_status_class(self):
        card = ScoreCard("Cov", "90%", "lbl", "warning")
        html = self.gen._generate_score_card(card)
        assert '<div class="score warning">90%</div>' in html

    def test_dashboard_contains_all_cards(self):
        cards = [ScoreCard("A", "1", "x"), ScoreCard("B", "2", "y")]
        html = self.gen._generate_dashboard(cards)
        assert html.count('<div class="card">') == 2

    def test_table_renders_headers_and_rows(self):
        html = self.gen._generate_table(["H1", "H2"], [["a", "b"]], "Ttl")
        assert "<th>H1</th><th>H2</th>" in html
        assert "<td>a</td><td>b</td>" in html
        assert "<h2>Ttl</h2>" in html

    def test_table_without_title(self):
        assert "<h2>" not in self.gen._generate_table(["H"], [])

    def test_severity_badge_lowercases_class(self):
        badge = self.gen._generate_severity_badge("HIGH")
        assert 'severity-high' in badge
        assert ">HIGH<" in badge

    def test_code_block_escapes_and_highlights(self):
        html = self.gen._generate_code_block("if a<b:\n    pass", highlight_line=1)
        assert "a&lt;b" in html
        assert 'class="highlight"' in html

    def test_file_list_items(self):
        html = self.gen._generate_file_list([("a.py", 3)], "Files")
        assert 'a.py' in html and '>3<' in html

    def test_progress_bar_status_thresholds(self):
        assert 'fill good' in self.gen._generate_progress_bar(85)
        assert 'fill warning' in self.gen._generate_progress_bar(60)
        assert 'fill bad' in self.gen._generate_progress_bar(10)

    def test_progress_bar_zero_max_is_zero_percent(self):
        html = self.gen._generate_progress_bar(5, max_value=0)
        assert "width: 0%" in html

    def test_progress_bar_capped_at_100(self):
        assert "width: 100" in self.gen._generate_progress_bar(150, max_value=100)


class TestTypingReport:
    def setup_method(self):
        self.gen = HTMLReportGenerator(title="Asgard")

    def test_passing_report_shows_pass(self):
        html = self.gen.generate_typing_report(_typing_report())
        assert ">PASS<" in html
        assert "Type Coverage - Asgard" in html

    def test_failing_report_shows_fail(self):
        html = self.gen.generate_typing_report(
            _typing_report(is_passing=False, coverage_percentage=40.0))
        assert ">FAIL<" in html

    def test_unannotated_functions_listed(self):
        func = SimpleNamespace(
            relative_path="m.py", qualified_name="m.f", line_number=3,
            missing_parameter_names=["a", "b", "c", "d"],
            has_return_annotation=False, severity="high",
        )
        html = self.gen.generate_typing_report(
            _typing_report(unannotated_functions=[func]))
        assert "m.f" in html
        assert "a, b, c..." in html  # truncated after 3 params

    def test_files_analyzed_table(self):
        f = SimpleNamespace(relative_path="low.py", total_functions=4,
                            fully_annotated=1, coverage_percentage=25.0)
        html = self.gen.generate_typing_report(_typing_report(files_analyzed=[f]))
        assert "low.py" in html
        assert "25.0%" in html


class TestQualityDashboard:
    def setup_method(self):
        self.gen = HTMLReportGenerator(title="Asgard")

    def test_no_reports_yields_empty_dashboard(self):
        html = self.gen.generate_quality_dashboard()
        assert "Quality Dashboard" in html
        assert '<div class="card">' not in html

    def test_quality_result_card_status(self):
        good = SimpleNamespace(files_over_threshold=[])
        html = self.gen.generate_quality_dashboard(quality_result=good)
        assert '<div class="score good">0</div>' in html

        bad = SimpleNamespace(files_over_threshold=list(range(6)))
        html = self.gen.generate_quality_dashboard(quality_result=bad)
        assert '<div class="score bad">6</div>' in html

    def test_typing_card_status_follows_is_passing(self):
        report = _typing_report(is_passing=False, coverage_percentage=42.0)
        html = self.gen.generate_quality_dashboard(typing_report=report)
        assert '<div class="score bad">42%</div>' in html

    def test_datetime_and_forbidden_cards(self):
        dt = SimpleNamespace(total_violations=2)
        fb = SimpleNamespace(total_violations=0)
        html = self.gen.generate_quality_dashboard(
            datetime_report=dt, forbidden_report=fb)
        assert "Datetime Issues" in html
        assert "Forbidden Imports" in html
        assert '<div class="score bad">2</div>' in html
        assert '<div class="score good">0</div>' in html

    def test_complexity_section_lists_offenders_only(self):
        offender = SimpleNamespace(
            name="huge", line_number=10, cyclomatic_complexity=25,
            cognitive_complexity=30, cyclomatic_severity="critical",
        )
        fine = SimpleNamespace(
            name="tiny", line_number=1, cyclomatic_complexity=2,
            cognitive_complexity=1, cyclomatic_severity="low",
        )
        result = SimpleNamespace(
            total_violations=1, has_violations=True,
            file_analyses=[SimpleNamespace(file_path="/repo/big.py",
                                           functions=[offender, fine])],
        )
        html = self.gen.generate_quality_dashboard(complexity_result=result)
        assert "Complex Functions" in html
        assert "huge" in html
        assert "tiny" not in html

    def test_smell_section_truncates_long_descriptions(self):
        smell = SimpleNamespace(
            file_path="/repo/s.py", smell_type="GodClass", line_number=5,
            description="d" * 100, severity="medium",
        )
        report = SimpleNamespace(total_smells=1, has_smells=True, smells=[smell])
        html = self.gen.generate_quality_dashboard(smell_report=report)
        assert ("d" * 60 + "...") in html
        assert ("d" * 61) not in html
