"""Search narrows the dishes already on the page."""

from __future__ import annotations

from collections.abc import Callable

from .api import Product
from .pages import MenuPage


def test_search_narrows_the_grid_to_matching_dishes(
    menu_page: MenuPage, make_product: Callable[..., Product]
) -> None:
    """Typing a dish's name leaves that dish and drops the rest."""
    wanted = make_product(
        names={"uz": "E2E searchable marker uz", "ru": "E2E searchable marker ru"}
    )
    other = make_product(names={"uz": "E2E unrelated dish uz", "ru": "E2E unrelated dish ru"})

    menu_page.open_menu("uz")
    before = menu_page.product_count()

    menu_page.search("searchable marker")

    names = menu_page.product_names()
    assert wanted.names["uz"] in names, "the matching dish was filtered out"
    assert other.names["uz"] not in names, "a non-matching dish survived the search"
    assert len(names) < before, f"search did not narrow anything: {before} -> {len(names)}"
    assert str(len(names)) in menu_page.result_summary(), (
        "the live region does not announce the number of matches"
    )


def test_search_is_case_insensitive(
    menu_page: MenuPage, make_product: Callable[..., Product]
) -> None:
    """Guests do not capitalise; neither should the match."""
    wanted = make_product(names={"uz": "E2E Mixed Case Dish"})

    menu_page.open_menu("uz")
    menu_page.search("mixed case")

    assert wanted.names["uz"] in menu_page.product_names()


def test_search_matches_the_description_as_well_as_the_name(
    menu_page: MenuPage, make_product: Callable[..., Product]
) -> None:
    """The API contract has search cover name and description alike."""
    wanted = make_product(
        names={"uz": "E2E described dish"},
        descriptions={"uz": "Served with roasted aubergine"},
    )

    menu_page.open_menu("uz")
    menu_page.search("aubergine")

    assert wanted.names["uz"] in menu_page.product_names(), (
        "a dish whose description matched was not returned"
    )


def test_a_search_with_no_matches_shows_an_empty_state_rather_than_a_blank_page(
    menu_page: MenuPage,
) -> None:
    """Nothing found is a message, not an empty grid."""
    menu_page.open_menu("uz")

    menu_page.search("zzzqweasdnothingmatchesthis")

    assert menu_page.product_count() == 0, "a nonsense query still matched dishes"
    body = menu_page.text_of(MenuPage.css("main"))
    assert "zzzqweasdnothingmatchesthis" in body, (
        "the empty state does not echo what the guest searched for"
    )


def test_clearing_the_search_restores_the_full_menu(
    menu_page: MenuPage, make_product: Callable[..., Product]
) -> None:
    """Emptying the field brings every dish back."""
    make_product()

    menu_page.open_menu("uz")
    before = menu_page.product_count()

    menu_page.search("E2E")
    assert menu_page.product_count() < before

    menu_page.search("")
    menu_page.wait.until(
        lambda _: menu_page.product_count() == before,
        "clearing the search did not restore the full menu",
    )
