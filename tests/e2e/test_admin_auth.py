"""Signing in to the staff panel."""

from __future__ import annotations

from collections.abc import Callable

from selenium.webdriver.chrome.webdriver import WebDriver

from .api import ACCESS_COOKIE, REFRESH_COOKIE
from .config import Settings
from .pages import AdminLoginPage, AdminProductsPage


def test_login_rejects_bad_credentials(
    login_page: AdminLoginPage, settings: Settings, reset_login_throttle: Callable[[], None]
) -> None:
    """A wrong password reports a failure and grants no session."""
    login_page.open_login("uz")

    login_page.sign_in(settings.admin_username, "definitely-not-the-password")

    message = login_page.error_message()
    assert message, "the form accepted a bad password without saying anything"
    assert "/admin/login" in login_page.path, (
        f"a rejected sign-in navigated away from the login screen to {login_page.path}"
    )

    cookies = {cookie["name"] for cookie in login_page.driver.get_cookies()}
    assert ACCESS_COOKIE not in cookies and REFRESH_COOKIE not in cookies, (
        "a rejected sign-in still wrote a session cookie"
    )


def test_login_does_not_reveal_whether_the_account_exists(
    login_page: AdminLoginPage, settings: Settings, reset_login_throttle: Callable[[], None]
) -> None:
    """An unknown user and a wrong password fail identically."""
    login_page.open_login("uz")
    login_page.sign_in(settings.admin_username, "definitely-not-the-password")
    wrong_password = login_page.error_message()

    reset_login_throttle()
    login_page.open_login("uz")
    login_page.sign_in("no-such-user-at-all", "definitely-not-the-password")
    unknown_user = login_page.error_message()

    assert wrong_password == unknown_user, (
        "the two failures are worded differently, which enumerates accounts: "
        f"{wrong_password!r} vs {unknown_user!r}"
    )


def test_login_accepts_good_credentials_and_opens_the_panel(
    login_page: AdminLoginPage,
    settings: Settings,
    reset_login_throttle: Callable[[], None],
) -> None:
    """Correct credentials land on the panel with an httpOnly session."""
    login_page.open_login("uz")

    login_page.sign_in(settings.admin_username, settings.admin_password)

    login_page.wait.until(
        lambda driver: "/admin/login" not in driver.current_url,
        "a correct sign-in never left the login screen",
    )
    assert "/admin" in login_page.path, f"signing in landed on {login_page.path}"
    assert not login_page.has_error()

    cookies = {cookie["name"]: cookie for cookie in login_page.driver.get_cookies()}
    assert ACCESS_COOKIE in cookies and REFRESH_COOKIE in cookies, (
        f"no session cookies after a successful sign-in: {sorted(cookies)}"
    )
    assert all(cookies[name]["httpOnly"] for name in (ACCESS_COOKIE, REFRESH_COOKIE)), (
        "the JWTs are readable by page scripts; they must stay httpOnly"
    )


def test_the_panel_redirects_an_anonymous_visitor_to_the_login_screen(
    login_page: AdminLoginPage,
) -> None:
    """The panel is guarded, and remembers where the visitor was going."""
    login_page.open("/uz/admin/products")

    login_page.find(AdminLoginPage.SUBMIT)
    assert "/uz/admin/login" in login_page.path, (
        f"an anonymous visitor reached {login_page.path} instead of the login screen"
    )
    assert "next=" in login_page.path, "the login screen did not keep the requested route"


def test_a_signed_in_visitor_reaches_the_product_list(
    signed_in_driver: WebDriver, settings: Settings
) -> None:
    """A session cookie is all the panel needs."""
    page = AdminProductsPage(signed_in_driver, settings.web_url, settings.wait_timeout)

    page.open_products("uz")

    assert page.path == "/uz/admin/products"
    assert page.is_present(AdminProductsPage.CREATE_BUTTON)
