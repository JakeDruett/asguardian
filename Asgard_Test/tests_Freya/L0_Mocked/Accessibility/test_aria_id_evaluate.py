"""CH-0070: ARIA ID refs are evaluate arguments, not JS source."""

from inspect import getsource
from unittest.mock import AsyncMock

import pytest

from Asgard.Freya.Accessibility.services._aria_validator_checks_part2 import (
    _ID_EXISTS_JS,
    validate_aria_ids,
)


QUOTED_ID = 'heading");alert(1)//'


def test_id_exists_script_is_static():
    assert "{id_ref}" not in _ID_EXISTS_JS
    assert "getElementById(id)" in _ID_EXISTS_JS
    source = getsource(validate_aria_ids)
    assert 'getElementById("{id_ref}")' not in source
    assert "page.evaluate(_ID_EXISTS_JS, id_ref)" in source


@pytest.mark.asyncio
async def test_quoted_id_is_evaluate_argument_not_source():
    element = AsyncMock()
    element.get_attribute = AsyncMock(
        side_effect=[QUOTED_ID, None, None, None],
    )
    page = AsyncMock()
    page.query_selector_all = AsyncMock(return_value=[element])

    captured: list[tuple[object, tuple]] = []

    async def capture_evaluate(script, *args, **kwargs):
        captured.append((script, args))
        if script is _ID_EXISTS_JS or (
            isinstance(script, str) and "getElementById" in script
        ):
            return False
        return "#element"

    page.evaluate = AsyncMock(side_effect=capture_evaluate)

    violations = await validate_aria_ids(page)

    id_calls = [
        (script, args)
        for script, args in captured
        if script is _ID_EXISTS_JS
        or (isinstance(script, str) and "getElementById" in script)
    ]
    assert id_calls
    for script, args in id_calls:
        assert QUOTED_ID not in str(script)
        assert args == (QUOTED_ID,)

    assert len(violations) == 1
    assert QUOTED_ID in violations[0].description


@pytest.mark.asyncio
async def test_quoted_id_existing_target_is_not_a_violation():
    element = AsyncMock()
    element.get_attribute = AsyncMock(
        side_effect=[QUOTED_ID, None, None, None],
    )
    page = AsyncMock()
    page.query_selector_all = AsyncMock(return_value=[element])
    page.evaluate = AsyncMock(return_value=True)

    violations = await validate_aria_ids(page)

    assert violations == []
    page.evaluate.assert_awaited()
    script, id_arg = page.evaluate.await_args.args
    assert script is _ID_EXISTS_JS
    assert id_arg == QUOTED_ID
    assert QUOTED_ID not in script
