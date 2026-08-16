"""CH-0019: Markdown table cells must not carry raw pipes or HTML."""

from Asgard.Bragi.common._md_cell import md_cell


def test_md_cell_escapes_pipe_backtick_and_html():
    assert "|" not in md_cell("a|b") or "\\|" in md_cell("a|b")
    assert md_cell("a|b") == "a\\|b"
    assert "`" not in md_cell("x`y")
    assert md_cell("<img src=x>") == "&lt;img src=x&gt;"
    assert "\n" not in md_cell("a\nb")
    assert md_cell("abcdef", max_len=3) == "abc"
