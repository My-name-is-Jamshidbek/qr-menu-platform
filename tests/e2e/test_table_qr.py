"""Scanning the QR code on a table.

The sticker encodes `https://<host>/t/<token>`. Following it is the first thing
a guest ever does with this product, so the route has to record the scan, claim
the table in a cookie and put the menu on screen — in one redirect, in a
language the sticker could not have known.
"""

from __future__ import annotations

from collections.abc import Callable

from .api import Table
from .pages import MenuPage

#: Cookie the scan route writes so a later ordering feature knows the table.
TABLE_COOKIE = "table"


def _await_settled(page: MenuPage) -> None:
    """Block until the browser has finished following every redirect."""
    page.wait.until(
        lambda driver: driver.execute_script("return document.readyState;") == "complete",
        "the scan route never finished loading",
    )


def test_a_qr_token_url_redirects_to_the_menu(
    menu_page: MenuPage, make_table: Callable[..., Table]
) -> None:
    """`/t/<token>` lands the guest on the menu."""
    table = make_table(label="E2E terrace")

    menu_page.open(f"/t/{table.token}")
    _await_settled(menu_page)

    assert menu_page.path.endswith("/menu"), (
        f"scanning the code for table {table.number} should end on the menu; "
        f"it ended on {menu_page.path}"
    )
    menu_page.await_products()
    assert menu_page.product_count() > 0, "the menu the scan opened has no dishes on it"


def test_a_scan_claims_the_table_in_a_cookie(
    menu_page: MenuPage, make_table: Callable[..., Table]
) -> None:
    """The redirect carries a `Set-Cookie` naming the table that was scanned."""
    table = make_table()

    menu_page.open(f"/t/{table.token}")
    _await_settled(menu_page)

    names = {cookie["name"] for cookie in menu_page.driver.get_cookies()}
    assert TABLE_COOKIE in names, (
        f"scanning table {table.number} did not claim it; "
        f"the browser ended on {menu_page.path} with cookies {sorted(names)}"
    )


def test_an_unknown_token_does_not_reach_the_menu(menu_page: MenuPage) -> None:
    """A retired or forged sticker gets the unavailable page, not the menu."""
    menu_page.open("/t/00000000-0000-4000-8000-000000000000")
    _await_settled(menu_page)

    assert not menu_page.path.endswith("/menu"), (
        "an unknown table token was treated as a valid scan"
    )
    assert "unavailable" in menu_page.path, (
        f"an unknown token should reach the unavailable page, reached {menu_page.path}"
    )
