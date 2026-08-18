"""Switching language changes the interface and the dish copy together."""

from __future__ import annotations

from collections.abc import Callable

from .api import Product
from .pages import MenuPage


def test_the_language_switch_changes_both_chrome_and_product_copy(
    menu_page: MenuPage, make_product: Callable[..., Product]
) -> None:
    """Russian swaps the navigation labels and the dish names in one step.

    Chrome alone would pass with untranslated content, and content alone would
    pass with an English menu bar, so both halves are asserted together.
    """
    product = make_product(
        names={
            "uz": "E2E translated dish uz",
            "ru": "E2E translated dish ru",
            "en": "E2E translated dish en",
        }
    )

    menu_page.open_menu("uz")
    uz_nav = menu_page.header_nav_labels()
    assert product.names["uz"] in menu_page.product_names()

    menu_page.switch_language("ru")

    assert menu_page.path.startswith("/ru/menu"), "the switch did not change the locale segment"

    ru_nav = menu_page.header_nav_labels()
    assert ru_nav != uz_nav, f"the navigation labels did not change language: {ru_nav}"

    ru_names = menu_page.product_names()
    assert product.names["ru"] in ru_names, "the dish kept its Uzbek name on the Russian menu"
    assert product.names["uz"] not in ru_names, "the Uzbek name is still being served in Russian"


def test_switching_language_keeps_the_guest_on_the_same_filtered_route(
    menu_page: MenuPage, make_product: Callable[..., Product], fixture_category
) -> None:
    """`/uz/menu/<section>` becomes `/ru/menu/<section>`, not the home page."""
    make_product()
    menu_page.open_menu("uz", fixture_category.slug)

    menu_page.switch_language("en")

    assert menu_page.path == f"/en/menu/{fixture_category.slug}", (
        f"the language switch lost the filter, landing on {menu_page.path}"
    )
    assert menu_page.heading() == fixture_category.names["en"], (
        "the section heading was not translated"
    )


def test_every_language_is_reachable_from_the_header(menu_page: MenuPage) -> None:
    """All three locales are offered, each as a real link."""
    menu_page.open_menu("uz")

    offered = {
        link.get_attribute("hreflang") for link in menu_page.find_all(MenuPage.LOCALE_LINKS)
    }
    assert offered == {"uz", "ru", "en"}, f"expected three languages, found {offered}"


def test_a_dish_without_a_translation_falls_back_to_uzbek(
    menu_page: MenuPage, make_product: Callable[..., Product]
) -> None:
    """A missing Russian name serves the Uzbek one rather than an empty card."""
    product = make_product(names={"uz": "E2E untranslated dish"})

    menu_page.open_menu("ru")

    assert product.names["uz"] in menu_page.product_names(), (
        "a dish with no Russian translation vanished from the Russian menu"
    )
