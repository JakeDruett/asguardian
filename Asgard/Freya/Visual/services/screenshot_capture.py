"""
Freya Screenshot Capture

Captures screenshots with device emulation, full-page support,
element targeting, and various configuration options.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from playwright.async_api import async_playwright, Page, Browser

from Asgard.Freya.Visual.models.visual_models import (
    ScreenshotConfig,
    ScreenshotResult,
    DeviceConfig,
    COMMON_DEVICES,
)


class ScreenshotCapture:
    """
    Screenshot capture service.

    Captures full-page, viewport, and element screenshots
    with device emulation support.
    """

    def __init__(self, output_directory: str = "./screenshots"):
        """
        Initialize the Screenshot Capture service.

        Args:
            output_directory: Directory to save screenshots
        """
        self.output_directory = Path(output_directory)
        self.output_directory.mkdir(parents=True, exist_ok=True)

    async def capture_full_page(
        self,
        url: str,
        filename: Optional[str] = None,
        config: Optional[ScreenshotConfig] = None
    ) -> ScreenshotResult:
        """
        Capture a full-page screenshot.

        Args:
            url: URL to capture
            filename: Output filename (auto-generated if not provided)
            config: Screenshot configuration

        Returns:
            ScreenshotResult with capture details
        """
        if config is None:
            config = ScreenshotConfig(full_page=True)
        else:
            config = config.model_copy(update={"full_page": True})

        return await self._capture(url, filename, config)

    async def capture_viewport(
        self,
        url: str,
        filename: Optional[str] = None,
        config: Optional[ScreenshotConfig] = None
    ) -> ScreenshotResult:
        """
        Capture a viewport screenshot.

        Args:
            url: URL to capture
            filename: Output filename
            config: Screenshot configuration

        Returns:
            ScreenshotResult with capture details
        """
        if config is None:
            config = ScreenshotConfig(full_page=False)
        else:
            config = config.model_copy(update={"full_page": False})

        return await self._capture(url, filename, config)

    async def capture_element(
        self,
        url: str,
        selector: str,
        filename: Optional[str] = None,
        config: Optional[ScreenshotConfig] = None
    ) -> ScreenshotResult:
        """
        Capture a screenshot of a specific element.

        Args:
            url: URL to capture
            selector: CSS selector for the element
            filename: Output filename
            config: Screenshot configuration

        Returns:
            ScreenshotResult with capture details
        """
        if config is None:
            config = ScreenshotConfig(full_page=False)

        return await self._capture_element(url, selector, filename, config)

    async def capture_with_devices(
        self,
        url: str,
        devices: list[str],
        filename_prefix: Optional[str] = None
    ) -> list[ScreenshotResult]:
        """
        Capture screenshots across multiple devices.

        Args:
            url: URL to capture
            devices: List of device names from COMMON_DEVICES
            filename_prefix: Prefix for filenames

        Returns:
            List of ScreenshotResult for each device
        """
        results = []

        for device_name in devices:
            if device_name not in COMMON_DEVICES:
                continue

            config = ScreenshotConfig(
                full_page=True,
                device=device_name,
            )

            prefix = filename_prefix or self._url_to_filename(url)
            filename = f"{prefix}_{device_name}.png"

            result = await self._capture(url, filename, config)
            results.append(result)

        return results

    async def _capture(
        self,
        url: str,
        filename: Optional[str],
        config: ScreenshotConfig
    ) -> ScreenshotResult:
        """Internal capture implementation."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            url_part = self._url_to_filename(url)
            filename = f"{url_part}_{timestamp}.{config.format}"

        file_path = self.output_directory / filename

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)

            context_options = {}

            if config.device and config.device in COMMON_DEVICES:
                device = COMMON_DEVICES[config.device]
                context_options = {
                    "viewport": {"width": device.width, "height": device.height},
                    "device_scale_factor": device.device_scale_factor,
                    "is_mobile": device.is_mobile,
                    "has_touch": device.has_touch,
                }
                if device.user_agent:
                    context_options["user_agent"] = device.user_agent
            elif config.custom_device:
                device = config.custom_device
                context_options = {
                    "viewport": {"width": device.width, "height": device.height},
                    "device_scale_factor": device.device_scale_factor,
                    "is_mobile": device.is_mobile,
                    "has_touch": device.has_touch,
                }
                if device.user_agent:
                    context_options["user_agent"] = device.user_agent

            context = await browser.new_context(**context_options)
            page = await context.new_page()

            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)

                if config.wait_for_selector:
                    await page.wait_for_selector(config.wait_for_selector, timeout=10000)

                if config.wait_for_timeout > 0:
                    await page.wait_for_timeout(config.wait_for_timeout)

                for selector in config.hide_selectors:
                    await page.evaluate(f"""
                        () => {{
                            const elements = document.querySelectorAll("{selector}");
                            elements.forEach(el => el.style.visibility = 'hidden');
                        }}
                    """)

                screenshot_options = {
                    "path": str(file_path),
                    "full_page": config.full_page,
                    "type": config.format,
                }

                if config.format == "jpeg":
                    screenshot_options["quality"] = config.quality

                if config.clip:
                    screenshot_options["clip"] = config.clip

                await page.screenshot(**screenshot_options)

                viewport = page.viewport_size
                width = viewport["width"] if viewport else 1920
                height = viewport["height"] if viewport else 1080

                if config.full_page:
                    dimensions = await page.evaluate("""
                        () => ({
                            width: document.documentElement.scrollWidth,
                            height: document.documentElement.scrollHeight
                        })
                    """)
                    width = dimensions["width"]
                    height = dimensions["height"]

            finally:
                await browser.close()

        file_size = os.path.getsize(file_path)

        return ScreenshotResult(
            url=url,
            file_path=str(file_path),
            width=width,
            height=height,
            device=config.device,
            captured_at=datetime.now().isoformat(),
            file_size_bytes=file_size,
            metadata={
                "full_page": config.full_page,
                "format": config.format,
            }
        )

    async def _capture_element(
        self,
        url: str,
        selector: str,
        filename: Optional[str],
        config: ScreenshotConfig
    ) -> ScreenshotResult:
        """Capture a specific element."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            selector_part = selector.replace(" ", "_").replace(".", "_")[:20]
            filename = f"element_{selector_part}_{timestamp}.{config.format}"

        file_path = self.output_directory / filename

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)

                if config.wait_for_timeout > 0:
                    await page.wait_for_timeout(config.wait_for_timeout)

                element = await page.wait_for_selector(selector, timeout=10000)

                if element is None:
                    raise ValueError(f"Element not found: {selector}")

                screenshot_options = {
                    "path": str(file_path),
                    "type": config.format,
                }

                if config.format == "jpeg":
                    screenshot_options["quality"] = config.quality

                await element.screenshot(**screenshot_options)

                box = await element.bounding_box()
                width = int(box["width"]) if box else 0
                height = int(box["height"]) if box else 0

            finally:
                await browser.close()

        file_size = os.path.getsize(file_path)

        return ScreenshotResult(
            url=url,
            file_path=str(file_path),
            width=width,
            height=height,
            device=config.device,
            captured_at=datetime.now().isoformat(),
            file_size_bytes=file_size,
            metadata={
                "element_selector": selector,
                "format": config.format,
            }
        )

    def _url_to_filename(self, url: str) -> str:
        """Convert URL to safe filename."""
        url = url.replace("https://", "").replace("http://", "")
        url = url.replace("/", "_").replace(":", "_").replace("?", "_")
        url = url.replace("&", "_").replace("=", "_")
        return url[:50]
