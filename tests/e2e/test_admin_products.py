"""Managing products through the panel."""

from __future__ import annotations

import uuid
from collections.abc import Callable

from .api import AdminApi, Category, Product
from .pages import AdminProductsPage, ProductFormPage


def test_the_add_product_button_is_genuinely_clickable(
    products_page: AdminProductsPage,
) -> None:
    """Nothing overlaps the panel's primary action.

    This is the exact bug the original app shipped: the "add product" button was
    rendered, styled and present in the DOM, and every click landed on an
    element stacked on top of it, so no product could ever be added. A test that
    only asserted the button exists would have passed the whole time — hence the
    `elementFromPoint` check, which asks the browser what is actually painted at
    the middle of the button.
    """
    products_page.open_products("uz")

    target = products_page.hit_target(AdminProductsPage.CREATE_BUTTON)

    assert target["resolved"], "nothing at all is painted where the add-product button is"
    assert target["isSelf"] or target["isDescendant"], (
        "the add-product button is covered: a click at its centre would hit "
        f"{target['description']} instead"
    )
    assert target["isSelf"], (
        "the add-product button's own hit area is taken by a child element "
        f"({target['description']}); the click target is not the button itself"
    )

    # A control the pointer can reach but that is too small to hit on a phone is
    # only half usable; the design system sets a 44x44 minimum.
    box = products_page.find(AdminProductsPage.CREATE_BUTTON).rect
    assert box["width"] >= 44 and box["height"] >= 44, (
        f"the add-product button is {box['width']}x{box['height']}, below the 44x44 minimum"
    )


def test_the_add_product_button_opens_the_creation_form(
    products_page: AdminProductsPage,
) -> None:
    """Clicking it really navigates, not just passes a hit test."""
    products_page.open_products("uz")

    products_page.start_create()

    assert products_page.path.endswith("/admin/products/new")
    assert products_page.is_present(ProductFormPage.FORM)


def test_create_edit_and_delete_a_product_through_the_panel(
    products_page: AdminProductsPage,
    product_form: ProductFormPage,
    admin_api: AdminApi,
    fixture_category: Category,
) -> None:
    """The full lifecycle a staff member performs, end to end.

    The product is created through the UI rather than a fixture precisely so
    that the create path is under test; the API client is used only to confirm
    what the UI claims, and to clean up if an assertion stops the test before
    the delete step.
    """
    token = uuid.uuid4().hex[:8]
    original_name = f"E2E lifecycle dish {token}"
    edited_name = f"E2E lifecycle dish edited {token}"
    created_id: int | None = None

    try:
        # ---------------------------------------------------------- create
        products_page.open_products("uz")
        products_page.start_create()

        product_form.await_form()
        product_form.choose_category(fixture_category.names["uz"])
        product_form.set_price(42_000)
        product_form.set_name("uz", original_name)
        product_form.set_name("ru", f"E2E lifecycle dish ru {token}")
        product_form.save()

        product_form.wait.until(
            lambda driver: "created=1" in driver.current_url,
            "saving a new product did not open its edit screen",
        )
        # Taken from the URL the panel redirected to, before anything else is
        # asserted: whatever fails below, the `finally` block can still clean up.
        created_id = int(product_form.path.split("/products/")[1].split("?")[0])
        product_form.await_form()

        assert product_form.heading() == original_name
        stored = admin_api.find_product_by_name(
            original_name, category_slug=fixture_category.slug
        )
        assert stored is not None, "the panel reported a save the API does not know about"
        assert stored["id"] == created_id
        assert stored["price"] == 42_000
        assert stored["category"] == fixture_category.id

        # ------------------------------------------------------------ edit
        product_form.set_name("uz", edited_name)
        product_form.set_price(43_500)
        status = product_form.save_and_await_status()
        assert status, "the form saved without confirming anything"

        product_form.driver.refresh()
        product_form.await_form()
        assert product_form.name_value("uz") == edited_name, (
            "the edited name did not survive a reload"
        )
        assert product_form.price_value() == "43500"

        reloaded = admin_api.get_product(created_id)
        assert reloaded is not None
        assert reloaded["price"] == 43_500
        assert any(row["name"] == edited_name for row in reloaded["translations"])

        # The edit must reach guests, not only the panel.
        products_page.open("/uz/menu")
        products_page.wait.until(
            lambda driver: edited_name in driver.page_source,
            "the edited dish never appeared on the public menu",
        )

        # ---------------------------------------------------------- delete
        product_form.open(f"/uz/admin/products/{created_id}")
        product_form.await_form()
        product_form.delete()

        product_form.wait.until(
            lambda driver: "deleted=1" in driver.current_url,
            "confirming the deletion did not return to the product list",
        )
        assert admin_api.get_product(created_id) is None, (
            "the panel reported a deletion the API did not perform"
        )
        created_id = None
    finally:
        if created_id is not None:
            admin_api.delete_product(created_id)


def test_the_list_shows_a_product_created_through_the_api(
    products_page: AdminProductsPage, make_product: Callable[..., Product]
) -> None:
    """The panel's server-side search finds a dish by name."""
    product = make_product()

    products_page.open_products("uz")
    products_page.search_for(product.names["uz"])

    assert product.names["uz"] in products_page.row_names()


def test_deleting_a_product_asks_for_confirmation_first(
    products_page: AdminProductsPage,
    product_form: ProductFormPage,
    admin_api: AdminApi,
    make_product: Callable[..., Product],
) -> None:
    """Destruction is never one click away, and the dialog names the dish."""
    product = make_product()

    product_form.open(f"/uz/admin/products/{product.id}")
    product_form.await_form()

    product_form.click(ProductFormPage.DELETE)
    dialog = product_form.confirm_dialog()

    assert product.names["uz"] in dialog.text, (
        "the confirmation dialog does not say which dish is about to be deleted"
    )
    assert admin_api.get_product(product.id) is not None, (
        "opening the confirmation dialog already deleted the product"
    )
