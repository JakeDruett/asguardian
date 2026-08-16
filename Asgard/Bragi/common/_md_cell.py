"""Markdown table-cell sanitizer (CH-0019)."""

import html


def md_cell(value: object, max_len: int | None = None) -> str:
    """Escape pipes, backticks, and control chars for a Markdown table cell."""
    text = "" if value is None else str(value)
    text = text.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    text = "".join(ch if ord(ch) >= 32 else " " for ch in text)
    text = text.replace("|", "\\|").replace("`", "'")
    text = html.escape(text, quote=False)
    if max_len is not None:
        text = text[:max_len]
    return text
