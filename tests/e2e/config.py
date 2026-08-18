"""Environment-driven configuration for the end-to-end suite.

Everything the suite needs to reach the running stack is read from the
environment, with defaults matching `.env.hostdev`. Nothing is hardcoded in a
test, so the same suite runs against a developer's local stack and against CI.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# `tests/e2e/config.py` -> `tests/e2e` -> `tests` -> repository root.
REPO_ROOT = Path(__file__).resolve().parents[2]


def _env(name: str, default: str) -> str:
    """Read `name`, falling back to `default` when unset or blank."""
    value = os.environ.get(name, "").strip()
    return value or default


def _env_int(name: str, default: int) -> int:
    return int(_env(name, str(default)))


def _env_bool(name: str, default: bool) -> bool:
    return _env(name, "1" if default else "0").lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    """Resolved suite configuration."""

    web_url: str
    """Origin of the Next.js front end, e.g. `http://localhost:3100`."""

    api_url: str
    """Base path of the Django API, e.g. `http://localhost:8100/api/v1`."""

    admin_username: str
    admin_password: str

    redis_url: str
    """Where the API keeps its throttle counters. Used to reset the login
    throttle between tests, which is rate limited to 5/min per IP."""

    backend_dir: Path
    """Django project root, used only to provision the test account once."""

    backend_python: Path
    """Interpreter that can import the Django project."""

    provision_admin: bool
    """Create the test account through `manage.py` when it cannot sign in."""

    headless: bool
    wait_timeout: int
    """Seconds an explicit wait polls before failing."""

    page_load_timeout: int

    desktop_viewport: tuple[int, int]
    mobile_viewport: tuple[int, int]

    screenshot_dir: Path
    temp_dir: Path

    chrome_binary: str
    chromedriver_binary: str

    def web(self, path: str) -> str:
        """Absolute front-end URL for a root-relative `path`."""
        return f"{self.web_url}{path}"

    def api(self, path: str) -> str:
        """Absolute API URL for a path relative to the API base."""
        return f"{self.api_url}{path}"


def load_settings() -> Settings:
    """Build `Settings` from the environment."""
    return Settings(
        web_url=_env("E2E_WEB_URL", "http://localhost:3100").rstrip("/"),
        api_url=_env("E2E_API_URL", "http://localhost:8100/api/v1").rstrip("/"),
        admin_username=_env("E2E_ADMIN_USERNAME", "e2e-admin"),
        admin_password=_env("E2E_ADMIN_PASSWORD", "e2e-password-123"),
        redis_url=_env("REDIS_URL", "redis://localhost:6382/0"),
        backend_dir=Path(_env("E2E_BACKEND_DIR", str(REPO_ROOT / "backend"))),
        backend_python=Path(
            _env("E2E_BACKEND_PYTHON", str(REPO_ROOT / "backend" / ".venv" / "bin" / "python"))
        ),
        provision_admin=_env_bool("E2E_PROVISION_ADMIN", True),
        headless=_env_bool("E2E_HEADLESS", True),
        wait_timeout=_env_int("E2E_WAIT_TIMEOUT", 30),
        page_load_timeout=_env_int("E2E_PAGE_LOAD_TIMEOUT", 120),
        desktop_viewport=(1440, 900),
        mobile_viewport=(390, 844),
        screenshot_dir=Path(
            _env("E2E_SCREENSHOT_DIR", str(REPO_ROOT / "screenshots" / "failures"))
        ),
        # Deliberately not `/tmp`: a Chromium profile per test fills a small
        # `/tmp` partition within one run, and a full `/tmp` kills the renderer
        # mid-test with an unhelpful "tab crashed".
        temp_dir=Path(_env("E2E_TEMP_DIR", str(Path(__file__).resolve().parent / ".tmp"))),
        chrome_binary=_env("E2E_CHROME_BINARY", "/usr/bin/chromium"),
        chromedriver_binary=_env("E2E_CHROMEDRIVER", "/usr/bin/chromedriver"),
    )
