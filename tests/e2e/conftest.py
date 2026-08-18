"""Fixtures for the BOSS KAFE end-to-end suite.

Two rules shape everything here:

* a test owns its data — every category, product and table a test relies on is
  created through the API and removed again afterwards, so the suite is
  repeatable and the order it runs in does not matter; and
* nothing sleeps — waiting is always an explicit `WebDriverWait` on the
  condition the test actually cares about.
"""

from __future__ import annotations

import random
import shutil
import subprocess
import uuid
from collections.abc import Callable, Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
import redis
import requests
from selenium.webdriver.chrome.webdriver import WebDriver

from .api import AdminApi, ApiError, Category, Product, Table, open_panel_session
from .browser import chromium
from .config import Settings, load_settings
from .pages import AdminLoginPage, AdminProductsPage, MenuPage, ProductFormPage

#: Routes `next dev` compiles on first request. Warming them before the browser
#: arrives keeps a compile out of the first test's timing, and stops a recompile
#: from invalidating chunks a live tab is holding.
WARMUP_ROUTES = (
    "/uz/menu",
    "/ru/menu",
    "/en/menu",
    "/uz/admin/login",
    "/uz/admin",
    "/uz/admin/products",
    "/uz/admin/products/new",
)

#: Django caches DRF throttle counters under this prefix.
LOGIN_THROTTLE_PATTERN = "*throttle_login*"

#: Table numbers the suite claims. `Table.number` is a PositiveSmallInt, so the
#: range has to stay under 32767 while still being well clear of anything a real
#: cafe would print on a table.
TABLE_NUMBER_MIN = 20_000
TABLE_NUMBER_MAX = 32_000


# --------------------------------------------------------------------- config


@pytest.fixture(scope="session")
def settings() -> Settings:
    """Suite configuration, resolved from the environment once."""
    return load_settings()


@pytest.fixture(scope="session", autouse=True)
def clean_temp_root(settings: Settings) -> Iterator[None]:
    """Start and finish with an empty scratch directory for browser profiles."""
    shutil.rmtree(settings.temp_dir, ignore_errors=True)
    settings.temp_dir.mkdir(parents=True, exist_ok=True)
    yield
    shutil.rmtree(settings.temp_dir, ignore_errors=True)


@pytest.fixture(scope="session")
def unique_suffix() -> str:
    """Short token making this run's data distinguishable from any other's."""
    return uuid.uuid4().hex[:8]


# ------------------------------------------------------------------- the stack


@pytest.fixture(scope="session", autouse=True)
def running_stack(settings: Settings) -> None:
    """Fail fast, with a usable message, when the stack is not up."""
    for label, url in (
        ("API", settings.api("/menu/?lang=uz")),
        ("front end", settings.web("/uz/menu")),
    ):
        try:
            response = requests.get(url, timeout=30)
        except requests.RequestException as error:
            pytest.exit(f"The {label} at {url} is unreachable: {error}", returncode=1)
        if response.status_code != 200:
            pytest.exit(f"The {label} at {url} answered {response.status_code}", returncode=1)


@pytest.fixture(scope="session", autouse=True)
def warm_routes(settings: Settings, running_stack: None) -> None:
    """Compile every route the suite visits before the first browser starts."""
    for route in WARMUP_ROUTES:
        requests.get(settings.web(route), timeout=settings.page_load_timeout)


@pytest.fixture(scope="session")
def throttle_cache(settings: Settings) -> Iterator[redis.Redis]:
    """Connection to the cache the API keeps its throttle counters in."""
    client = redis.Redis.from_url(settings.redis_url)
    try:
        yield client
    finally:
        client.close()


@pytest.fixture
def reset_login_throttle(throttle_cache: redis.Redis) -> Callable[[], None]:
    """Clear the API's 5/min login throttle.

    Rate limiting is covered by the backend's own tests. Here it is only an
    obstacle: a suite that signs in more than five times a minute would start
    failing for a reason that has nothing to do with what it is asserting.
    """

    def reset() -> None:
        for key in throttle_cache.scan_iter(match=LOGIN_THROTTLE_PATTERN):
            throttle_cache.delete(key)

    reset()
    return reset


# ----------------------------------------------------------------- API access


def _provision_admin_account(settings: Settings) -> bool:
    """Create the suite's staff account through Django. Returns success.

    The API has no endpoint for creating users — by design — so the one piece of
    state the suite cannot bootstrap over HTTP is bootstrapped here instead, and
    only when signing in has already failed.
    """
    if not settings.provision_admin or not settings.backend_python.exists():
        return False

    script = (
        "from django.contrib.auth import get_user_model\n"
        "User = get_user_model()\n"
        f"user, _ = User.objects.get_or_create(username={settings.admin_username!r})\n"
        "user.role = 'ADMIN'\n"
        "user.is_staff = True\n"
        "user.is_superuser = True\n"
        f"user.set_password({settings.admin_password!r})\n"
        "user.save()\n"
    )
    result = subprocess.run(
        [str(settings.backend_python), "manage.py", "shell", "-c", script],
        cwd=settings.backend_dir,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    return result.returncode == 0


@pytest.fixture(scope="session")
def admin_api(settings: Settings, running_stack: None) -> AdminApi:
    """Authenticated API client shared by the data fixtures."""
    client = AdminApi(settings=settings)
    try:
        client.sign_in()
    except Exception:  # noqa: BLE001 - retried below with a provisioned account
        if not _provision_admin_account(settings):
            pytest.exit(
                "Cannot sign in as "
                f"{settings.admin_username!r} and could not provision the account. "
                "Set E2E_ADMIN_USERNAME / E2E_ADMIN_PASSWORD to an existing ADMIN "
                "user, or point E2E_BACKEND_PYTHON at the backend interpreter.",
                returncode=1,
            )
        client.sign_in()
    return client


# ------------------------------------------------------------------- test data


@pytest.fixture(scope="session")
def fixture_category(admin_api: AdminApi, unique_suffix: str) -> Iterator[Category]:
    """A top-level category owned by this run, removed when it finishes."""
    category = admin_api.create_category(
        names={
            "uz": f"E2E section uz {unique_suffix}",
            "ru": f"E2E section ru {unique_suffix}",
            "en": f"E2E section en {unique_suffix}",
        },
        slug=f"e2e-section-{unique_suffix}",
        # Last in the menu, so the fixtures never displace the real sections.
        order=999,
    )
    try:
        yield category
    finally:
        # A test that created a product through the UI and then failed before
        # its own cleanup would otherwise leave the category undeletable, and
        # the stray dish would follow the next run into every menu assertion.
        for stray in admin_api.list_products(category_slug=category.slug):
            admin_api.delete_product(stray["id"])
        admin_api.delete_category(category.id)


@pytest.fixture(scope="session")
def fixture_subcategory(
    admin_api: AdminApi, fixture_category: Category, unique_suffix: str
) -> Iterator[Category]:
    """A subsection of `fixture_category`, for the two-level filter test."""
    subcategory = admin_api.create_category(
        names={
            "uz": f"E2E subsection uz {unique_suffix}",
            "ru": f"E2E subsection ru {unique_suffix}",
            "en": f"E2E subsection en {unique_suffix}",
        },
        parent=fixture_category.id,
        slug=f"e2e-subsection-{unique_suffix}",
    )
    try:
        yield subcategory
    finally:
        for stray in admin_api.list_products(category_slug=subcategory.slug):
            admin_api.delete_product(stray["id"])
        admin_api.delete_category(subcategory.id)


@pytest.fixture
def make_product(
    admin_api: AdminApi, fixture_category: Category
) -> Iterator[Callable[..., Product]]:
    """Factory creating products that are deleted when the test ends."""
    created: list[Product] = []

    def factory(
        *,
        names: dict[str, str] | None = None,
        category_id: int | None = None,
        price: int = 25_000,
        descriptions: dict[str, str] | None = None,
        is_available: bool = True,
    ) -> Product:
        token = uuid.uuid4().hex[:8]
        product = admin_api.create_product(
            category_id=category_id if category_id is not None else fixture_category.id,
            names=names
            or {
                "uz": f"E2E dish uz {token}",
                "ru": f"E2E dish ru {token}",
                "en": f"E2E dish en {token}",
            },
            price=price,
            descriptions=descriptions,
            is_available=is_available,
        )
        created.append(product)
        return product

    try:
        yield factory
    finally:
        for product in created:
            admin_api.delete_product(product.id)


@pytest.fixture
def make_table(admin_api: AdminApi) -> Iterator[Callable[..., Table]]:
    """Factory creating tables that are deleted when the test ends."""
    created: list[Table] = []

    def factory(label: str = "E2E table") -> Table:
        # `number` is unique, so a collision with a leftover row is retried
        # rather than failing the test that asked for a table.
        last_error: Exception | None = None
        for _ in range(10):
            number = random.randint(TABLE_NUMBER_MIN, TABLE_NUMBER_MAX)
            try:
                table = admin_api.create_table(number=number, label=label)
            except ApiError as error:
                last_error = error
                continue
            created.append(table)
            return table
        raise AssertionError(f"could not claim a free table number: {last_error}")

    try:
        yield factory
    finally:
        for table in created:
            admin_api.delete_table(table.id)


# --------------------------------------------------------------------- browser


@pytest.fixture
def driver(settings: Settings, warm_routes: None) -> Iterator[WebDriver]:
    """A desktop-sized headless Chromium, fresh for this test."""
    with chromium(settings, settings.desktop_viewport) as instance:
        yield instance


@pytest.fixture
def mobile_driver(settings: Settings, warm_routes: None) -> Iterator[WebDriver]:
    """A headless Chromium whose viewport is exactly 390x844."""
    with chromium(settings, settings.mobile_viewport) as instance:
        yield instance


@pytest.fixture(scope="session")
def panel_cookies(settings: Settings, admin_api: AdminApi) -> dict[str, str]:
    """The panel's httpOnly session cookies, obtained once for the whole run."""
    return open_panel_session(settings)


@pytest.fixture
def signed_in_driver(
    driver: WebDriver, settings: Settings, panel_cookies: dict[str, str]
) -> WebDriver:
    """A driver already holding a staff session.

    Tests about the panel's *contents* should not each replay the sign-in form:
    that is what `test_admin_auth.py` is for, and repeating it would trip the
    API's login throttle.
    """
    # A cookie can only be set for an origin the browser is already on.
    driver.get(settings.web("/uz/menu"))
    for name, value in panel_cookies.items():
        driver.add_cookie(
            {
                "name": name,
                "value": value,
                "domain": "localhost",
                "path": "/",
                "httpOnly": True,
                # Matches how the front end writes them; browsers accept a
                # Secure cookie on localhost, which they treat as trustworthy.
                "secure": True,
            }
        )
    return driver


# ---------------------------------------------------------------- page objects


@pytest.fixture
def menu_page(driver: WebDriver, settings: Settings) -> MenuPage:
    """Page object for the public menu."""
    return MenuPage(driver, settings.web_url, settings.wait_timeout)


@pytest.fixture
def mobile_menu_page(mobile_driver: WebDriver, settings: Settings) -> MenuPage:
    """The public menu, on a phone-sized viewport."""
    return MenuPage(mobile_driver, settings.web_url, settings.wait_timeout)


@pytest.fixture
def login_page(driver: WebDriver, settings: Settings) -> AdminLoginPage:
    """Page object for the sign-in screen, with no session in the browser."""
    return AdminLoginPage(driver, settings.web_url, settings.wait_timeout)


@pytest.fixture
def products_page(signed_in_driver: WebDriver, settings: Settings) -> AdminProductsPage:
    """Page object for the product list, already signed in."""
    return AdminProductsPage(signed_in_driver, settings.web_url, settings.wait_timeout)


@pytest.fixture
def product_form(signed_in_driver: WebDriver, settings: Settings) -> ProductFormPage:
    """Page object for the product form, already signed in."""
    return ProductFormPage(signed_in_driver, settings.web_url, settings.wait_timeout)


# ------------------------------------------------------- screenshot on failure


def _safe_name(nodeid: str) -> str:
    """Turn a pytest node id into something a filesystem accepts."""
    return "".join(character if character.isalnum() else "-" for character in nodeid).strip("-")


def _live_driver(item: pytest.Item) -> WebDriver | None:
    """The browser this test was driving, if it had one."""
    for name in ("mobile_driver", "signed_in_driver", "driver"):
        candidate = getattr(item, "funcargs", {}).get(name)
        if candidate is not None:
            return candidate
    return None


def _capture_failure(item: pytest.Item) -> None:
    """Write a screenshot and the page source for a failed browser test."""
    instance = _live_driver(item)
    if instance is None:
        return

    settings = load_settings()
    settings.screenshot_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d-%H%M%S")
    stem: Path = settings.screenshot_dir / f"{stamp}-{_safe_name(item.nodeid)}"

    try:
        instance.save_screenshot(f"{stem}.png")
        stem.with_suffix(".html").write_text(instance.page_source, encoding="utf-8")
    except Exception as error:  # noqa: BLE001 - a crashed browser cannot be photographed
        print(f"\nCould not capture failure artefacts for {item.nodeid}: {error}")
    else:
        print(f"\nFailure screenshot: {stem}.png")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(  # type: ignore[no-untyped-def]
    item: pytest.Item, call: pytest.CallInfo[Any]
):
    """Photograph the page as soon as a test fails.

    Capturing here rather than in a fixture matters: an autouse fixture is torn
    down after the `driver` fixture it would need, so by the time it ran the
    browser would already be gone and every screenshot would be a connection
    error.
    """
    outcome = yield
    report = outcome.get_result()
    setattr(item, f"report_{report.when}", report)

    if report.failed and report.when in {"setup", "call"}:
        _capture_failure(item)
