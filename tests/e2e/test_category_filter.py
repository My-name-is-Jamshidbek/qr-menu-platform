"""Category filtering lives in the URL, not in component state.

This is the defect the rewrite exists to fix: in the original app the selected
category was `useState`, so a filtered view could not be linked to or shared,
the back button skipped it and a reload dropped the guest back to "everything".
"""

from __future__ import annotations

from collections.abc import Callable

from .api import Category, Product
from .pages import MenuPage


def test_choosing_a_category_changes_the_url_and_the_result_set(
    menu_page: MenuPage,
    fixture_category: Category,
    make_product: Callable[..., Product],
) -> None:
    """Clicking a filter navigates, and the grid narrows to that section."""
    mine = make_product()
    target = f"/uz/menu/{fixture_category.slug}"

    menu_page.open_menu("uz")
    everything = menu_page.product_names()
    assert len(everything) > 1, "the unfiltered menu needs more than one dish to narrow"

    menu_page.click_category(target)

    assert menu_page.path == target, "the filter did not put the section in the URL"
    filtered = menu_page.product_names()
    assert filtered == [mine.names["uz"]], (
        f"the section should hold exactly its own dish, got {filtered}"
    )
    assert len(filtered) < len(everything), "the filter did not narrow the result set"
    assert menu_page.heading() == fixture_category.names["uz"], (
        "the heading did not follow the selected section"
    )
    assert menu_page.active_category_path() == target, (
        "the selected filter is not marked aria-current"
    )


def test_a_filtered_url_survives_a_reload(
    menu_page: MenuPage,
    fixture_category: Category,
    make_product: Callable[..., Product],
) -> None:
    """Opening the filtered URL directly shows the filtered menu."""
    mine = make_product()
    target = f"/uz/menu/{fixture_category.slug}"

    menu_page.open(target)
    menu_page.await_products()

    assert menu_page.product_names() == [mine.names["uz"]]
    assert menu_page.heading() == fixture_category.names["uz"]


def test_the_back_button_returns_to_the_previous_filter(
    menu_page: MenuPage,
    fixture_category: Category,
    make_product: Callable[..., Product],
) -> None:
    """Each filter is a history entry, so back means back one section."""
    make_product()

    menu_page.open_menu("uz")
    unfiltered_count = menu_page.product_count()

    menu_page.click_category(f"/uz/menu/{fixture_category.slug}")
    assert menu_page.product_count() < unfiltered_count

    menu_page.driver.back()
    menu_page.wait_for_path("/uz/menu")
    menu_page.await_products()

    assert menu_page.product_count() == unfiltered_count, (
        "going back did not restore the unfiltered menu"
    )


def test_a_subcategory_narrows_the_section_further(
    menu_page: MenuPage,
    fixture_category: Category,
    fixture_subcategory: Category,
    make_product: Callable[..., Product],
) -> None:
    """A subsection is a third URL segment with its own result set."""
    in_section = make_product()
    in_subsection = make_product(category_id=fixture_subcategory.id)

    menu_page.open_menu("uz", fixture_category.slug)
    assert set(menu_page.product_names()) == {
        in_section.names["uz"],
        in_subsection.names["uz"],
    }, "a section should include the dishes of its subsections"

    subsection_path = f"/uz/menu/{fixture_category.slug}/{fixture_subcategory.slug}"
    menu_page.click_category(subsection_path)

    assert menu_page.path == subsection_path
    assert menu_page.product_names() == [in_subsection.names["uz"]], (
        "the subsection should hold only its own dish"
    )


def test_an_unknown_category_is_a_404_rather_than_a_silent_fallback(
    menu_page: MenuPage,
) -> None:
    """A typo must not quietly serve "everything" with a 200."""
    menu_page.open("/uz/menu/no-such-section")

    menu_page.wait.until(
        lambda driver: not driver.find_elements(*MenuPage.CARD),
        "an unknown section still rendered the full menu",
    )
    assert not menu_page.is_present(MenuPage.CARD)
