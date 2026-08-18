"""Smoke test on a 390x844 phone viewport.

Most traffic arrives by scanning a QR code at a table, so the phone is the
primary device, not an afterthought. 390x844 is the iPhone 12/13/14 viewport.
"""

from __future__ import annotations

from collections.abc import Callable

from .api import Product
from .config import Settings
from .pages import MenuPage


def test_the_viewport_really_is_390_by_844(
    mobile_menu_page: MenuPage, settings: Settings
) -> None:
    """Guard the emulation itself, so the rest of this module means something."""
    mobile_menu_page.open_menu("uz")

    viewport = mobile_menu_page.viewport()
    assert (viewport["width"], viewport["height"]) == settings.mobile_viewport, (
        f"expected a {settings.mobile_viewport} viewport, measured "
        f"{(viewport['width'], viewport['height'])}"
    )


def test_the_menu_renders_and_is_searchable_on_a_phone(
    mobile_menu_page: MenuPage, make_product: Callable[..., Product]
) -> None:
    """The core guest journey works at phone width."""
    product = make_product(names={"uz": "E2E phone dish"})

    mobile_menu_page.open_menu("uz")
    assert mobile_menu_page.product_count() > 0, "the phone menu rendered no dishes"

    mobile_menu_page.search("phone dish")

    assert product.names["uz"] in mobile_menu_page.product_names()


def test_the_grid_is_a_single_column_on_a_phone(mobile_menu_page: MenuPage) -> None:
    """The design system calls for one column below 640px."""
    mobile_menu_page.open_menu("uz")

    cards = mobile_menu_page.find_all(MenuPage.CARD)
    assert len(cards) >= 2, "need at least two cards to tell a column from a row"

    first, second = cards[0].rect, cards[1].rect
    assert second["y"] >= first["y"] + first["height"] - 1, (
        "two cards share a row; the phone grid is not a single column"
    )


def test_the_page_does_not_scroll_sideways_on_a_phone(mobile_menu_page: MenuPage) -> None:
    """Nothing may push the document wider than the screen.

    Horizontal page scroll on a phone is not cosmetic: it drags fixed elements
    out of reach and makes vertical scrolling skid sideways. The category strip
    is meant to scroll *inside itself*, which is why this asserts on the
    document rather than on any one element.
    """
    mobile_menu_page.open_menu("uz")

    viewport = mobile_menu_page.viewport()
    overflow = viewport["scrollWidth"] - viewport["width"]
    if overflow > 0:
        offenders = mobile_menu_page.elements_overflowing_horizontally()
        summary = "; ".join(
            f"<{item['tag']} class={item['classes']!r}> spans {item['left']}..{item['right']}"
            for item in offenders[:4]
        )
        raise AssertionError(
            f"the page is {overflow}px wider than the {viewport['width']}px viewport "
            f"and scrolls sideways. Overflowing elements: {summary}"
        )


def test_the_language_switch_is_reachable_on_a_phone(mobile_menu_page: MenuPage) -> None:
    """Every language pill must be on screen and hittable at 390px."""
    mobile_menu_page.open_menu("uz")

    width = mobile_menu_page.viewport()["width"]
    for link in mobile_menu_page.find_all(MenuPage.LOCALE_LINKS):
        locale = link.get_attribute("hreflang")
        box = link.rect
        assert box["x"] >= 0 and box["x"] + box["width"] <= width, (
            f"the {locale} language pill sits at "
            f"{round(box['x'])}..{round(box['x'] + box['width'])}, outside the {width}px screen"
        )
