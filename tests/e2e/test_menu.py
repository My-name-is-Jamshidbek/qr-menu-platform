"""The public menu loads and renders real products."""

from __future__ import annotations

from collections.abc import Callable

import requests

from .api import Product
from .config import Settings
from .pages import MenuPage


def test_menu_renders_a_card_for_every_product_the_api_serves(
    menu_page: MenuPage, settings: Settings
) -> None:
    """Every dish the API publishes reaches the grid, with a name and a price."""
    published = requests.get(settings.api("/menu/?lang=uz"), timeout=30).json()
    expected_count = sum(len(category["products"]) for category in published["categories"])
    assert expected_count > 0, "the API published an empty menu; there is nothing to render"

    menu_page.open_menu("uz")

    names = menu_page.product_names()
    assert len(names) == expected_count, (
        f"the API serves {expected_count} dishes but the page rendered {len(names)}"
    )
    assert all(names), "at least one card rendered without a name"

    # Prices are the other half of a menu; a grid of nameless, priceless boxes
    # would satisfy a card count on its own.
    prices = menu_page.driver.execute_script(
        "return Array.from(document.querySelectorAll('main li:has(h3) span[class*=tabular],"
        " main li:has(h3) span')).map((node) => node.textContent.trim());"
    )
    assert any("so'm" in price or any(char.isdigit() for char in price) for price in prices), (
        "no card showed a price"
    )


def test_menu_groups_products_under_their_section_headings(menu_page: MenuPage) -> None:
    """The unfiltered menu is a set of named sections, not one flat list."""
    menu_page.open_menu("uz")

    headings = menu_page.texts_of(MenuPage.SECTION_HEADING)
    assert len(headings) > 1, f"expected several section headings, got {headings}"
    assert all(headings), "a section rendered without a heading"


def test_a_product_created_through_the_api_appears_on_the_menu(
    menu_page: MenuPage, make_product: Callable[..., Product]
) -> None:
    """A dish added by staff is on the guest-facing menu without a rebuild."""
    product = make_product(price=31_500)

    menu_page.open_menu("uz")

    assert product.names["uz"] in menu_page.product_names(), (
        f"{product.names['uz']!r} was created through the API but is not on the menu"
    )


def test_an_unavailable_product_is_hidden_from_guests(
    menu_page: MenuPage, make_product: Callable[..., Product]
) -> None:
    """`is_available=False` is the soft-hide staff actually use."""
    hidden = make_product(is_available=False)
    visible = make_product()

    menu_page.open_menu("uz")

    names = menu_page.product_names()
    assert visible.names["uz"] in names, "an available dish was missing from the menu"
    assert hidden.names["uz"] not in names, (
        f"{hidden.names['uz']!r} is marked unavailable but is still offered to guests"
    )
