"""CHC-0006: common baseline fuzzy empty message is not a file+type wildcard."""

from Asgard.common._baseline_models import BaselineEntry


def test_empty_stored_message_is_not_fuzzy_wildcard():
    entry = BaselineEntry(
        item_id="1",
        item_type="secret",
        location="a.py:1",
        message="",
    )
    assert entry.matches("a.py:2", "secret", message="real finding", fuzzy=True) is False


def test_empty_query_does_not_match_stored_message():
    entry = BaselineEntry(
        item_id="1",
        item_type="secret",
        location="a.py:1",
        message="real finding",
    )
    assert entry.matches("a.py:1", "secret", message="", fuzzy=True) is False
    assert entry.matches("a.py:1", "secret", message="   ", fuzzy=True) is False


def test_usable_fuzzy_messages_still_match():
    entry = BaselineEntry(
        item_id="1",
        item_type="secret",
        location="a.py:1",
        message="hello world",
    )
    assert entry.matches("a.py:9", "secret", message="hello world extra", fuzzy=True) is True
