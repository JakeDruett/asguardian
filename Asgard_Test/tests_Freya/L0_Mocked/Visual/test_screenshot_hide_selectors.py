"""CH-0074: hide_selectors must not be interpolated into page.evaluate JS."""

import json
from unittest.mock import patch

import pytest

from Asgard.Freya.Visual.models.visual_models import ScreenshotConfig
from Asgard.Freya.Visual.services._screenshot_capture_helpers import (
    HIDE_SELECTOR_JS,
    capture,
    encode_hide_selector,
)
from Asgard.Freya.Visual.services.screenshot_capture import ScreenshotCapture

# Classic JS-string breakout if interpolated as querySelectorAll("{selector}")
HOSTILE = 'div"); alert(1); //'


def test_encode_hide_selector_json_roundtrip():
    encoded = encode_hide_selector(HOSTILE)
    assert json.loads(encoded) == HOSTILE
    assert encoded == json.dumps(HOSTILE)


def test_hide_script_does_not_contain_selector():
    assert HOSTILE not in HIDE_SELECTOR_JS
    assert '");' not in HIDE_SELECTOR_JS
    assert "JSON.parse" in HIDE_SELECTOR_JS
    assert "querySelectorAll(selector)" in HIDE_SELECTOR_JS


def test_hide_script_is_static_across_payloads():
    for payload in (HOSTILE, ".ad", "a[href*=\"x\"]", "'); throw 1;//"):
        assert payload not in HIDE_SELECTOR_JS
        assert encode_hide_selector(payload) != HIDE_SELECTOR_JS


@pytest.mark.L0
@pytest.mark.asyncio
async def test_capture_passes_hostile_selector_as_evaluate_arg(
    temp_output_dir, mock_async_playwright, mock_page,
):
    config = ScreenshotConfig(hide_selectors=[HOSTILE, ".ad"])

    with patch(
        "Asgard.Freya.Visual.services._screenshot_capture_helpers.async_playwright",
        mock_async_playwright,
    ), patch("os.path.getsize", return_value=12345):
        await capture(
            url="https://example.com",
            filename="test.png",
            config=config,
            output_directory=temp_output_dir,
        )

    hide_calls = [
        c
        for c in mock_page.evaluate.call_args_list
        if c.args and "querySelectorAll" in str(c.args[0])
    ]
    assert len(hide_calls) == 2

    scripts = [c.args[0] for c in hide_calls]
    args = [c.args[1] for c in hide_calls]

    assert all(script == HIDE_SELECTOR_JS for script in scripts)
    assert all(HOSTILE not in script for script in scripts)
    assert all('");' not in script for script in scripts)
    assert json.loads(args[0]) == HOSTILE
    assert json.loads(args[1]) == ".ad"


@pytest.mark.L0
@pytest.mark.asyncio
async def test_screenshot_capture_hides_via_encoded_arg(
    temp_output_dir, mock_async_playwright, mock_page,
):
    capture_svc = ScreenshotCapture(output_directory=str(temp_output_dir))
    config = ScreenshotConfig(hide_selectors=[HOSTILE])

    with patch(
        "Asgard.Freya.Visual.services._screenshot_capture_helpers.async_playwright",
        mock_async_playwright,
    ), patch("os.path.getsize", return_value=12345):
        await capture_svc._capture(
            url="https://example.com",
            filename="test.png",
            config=config,
        )

    hide_calls = [
        c
        for c in mock_page.evaluate.call_args_list
        if c.args and "JSON.parse" in str(c.args[0])
    ]
    assert hide_calls
    expression, encoded = hide_calls[0].args[0], hide_calls[0].args[1]
    assert HOSTILE not in expression
    assert json.loads(encoded) == HOSTILE
