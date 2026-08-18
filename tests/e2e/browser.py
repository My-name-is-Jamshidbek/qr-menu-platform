"""Headless Chromium factory.

One browser per test. A shared browser is cheaper, but `next dev` recompiles a
route the first time it is visited and swaps its chunk graph underneath any tab
that is still holding the old one — which surfaces as a `ChunkLoadError` and,
shortly after, a dead renderer. A fresh profile per test costs about a second
and removes that whole class of flake.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

from .config import Settings

#: Flags that make Chromium behave in a sandbox with no outbound internet.
#:
#: The networking ones are not cosmetic: with component updates, sync and GCM
#: registration enabled, Chromium blocks on requests that never resolve here and
#: the renderer is eventually torn down mid-test.
BASE_ARGUMENTS = (
    "--no-sandbox",
    "--disable-gpu",
    "--disable-dev-shm-usage",
    "--disable-background-networking",
    "--disable-component-update",
    "--disable-sync",
    "--disable-default-apps",
    "--disable-extensions",
    "--disable-client-side-phishing-detection",
    "--disable-domain-reliability",
    "--no-first-run",
    "--no-default-browser-check",
    "--no-pings",
    "--metrics-recording-only",
    "--hide-scrollbars",
    # Chromium reaches for gnome-keyring/kwallet on Linux otherwise, which is
    # not running here and takes the browser down with it on a password form.
    "--password-store=basic",
    "--use-mock-keychain",
    "--disable-features=Translate,OptimizationHints,MediaRouter,InterestFeedContentSuggestions",
)

#: Window Chromium is launched with. Real viewports are set over CDP afterwards,
#: because headless Chromium refuses to shrink its window below a few hundred
#: pixels and would silently give a phone test a tablet viewport.
LAUNCH_WINDOW = (1440, 900)


@contextmanager
def chromium(settings: Settings, viewport: tuple[int, int]) -> Iterator[webdriver.Chrome]:
    """Yield a Chromium driver whose viewport is exactly `viewport`."""
    settings.temp_dir.mkdir(parents=True, exist_ok=True)

    profile = Path(tempfile.mkdtemp(prefix="profile-", dir=settings.temp_dir))

    options = Options()
    options.binary_location = settings.chrome_binary
    if settings.headless:
        options.add_argument("--headless=new")
    for argument in BASE_ARGUMENTS:
        options.add_argument(argument)
    options.add_argument(f"--window-size={LAUNCH_WINDOW[0]},{LAUNCH_WINDOW[1]}")
    options.add_argument(f"--user-data-dir={profile}")
    options.add_experimental_option(
        "prefs",
        {"credentials_enable_service": False, "profile.password_manager_enabled": False},
    )

    # Chromium also creates its own scoped directories through `TMPDIR`,
    # independently of `--user-data-dir`, so the variable has to be redirected
    # too rather than only the profile flag.
    environment = {**os.environ, "TMPDIR": str(settings.temp_dir)}

    driver = webdriver.Chrome(
        service=Service(settings.chromedriver_binary, env=environment), options=options
    )
    try:
        width, height = viewport
        driver.execute_cdp_cmd(
            "Emulation.setDeviceMetricsOverride",
            {
                "width": width,
                "height": height,
                # A scale factor above 1 makes a full-page screenshot of the
                # 100-dish menu large enough to take the renderer with it.
                "deviceScaleFactor": 1,
                # `mobile: false` keeps the visual and layout viewports equal,
                # so `document.documentElement.clientWidth` really is `width`
                # and an overflow assertion measures the page, not the emulator.
                "mobile": False,
            },
        )
        driver.set_page_load_timeout(settings.page_load_timeout)
        yield driver
    finally:
        try:
            driver.quit()
        except Exception:  # noqa: BLE001 - a crashed browser must not mask the test's own failure
            pass
        shutil.rmtree(profile, ignore_errors=True)
