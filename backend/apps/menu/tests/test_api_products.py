"""The paginated product list, its search and category filters, and product detail."""

import pytest
from django.core.cache import cache
from django.urls import reverse
from rest_framework.test import APIClient

from apps.common.enums import Language
from apps.menu.factories import (
    CategoryFactory,
    ProductFactory,
    ProductImageFactory,
    ProductTranslationFactory,
)

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def clean_cache():
    """Throttle counters share the menu cache; a clean slate keeps runs independent."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def client() -> APIClient:
    return APIClient()


@pytest.fixture
def list_url() -> str:
    return reverse("menu:product-list")


def _product(slug: str, name: str, description: str = "", **kwargs):
    product = ProductFactory(slug=slug, with_uz_translation=False, **kwargs)
    ProductTranslationFactory(
        product=product, language=Language.UZ, name=name, description=description
    )
    return product


def test_list_is_paginated_with_the_contract_envelope(client, list_url) -> None:
    for index in range(25):
        _product(f"dish-{index}", f"Dish {index}")

    body = client.get(list_url).json()

    assert body["count"] == 25
    assert len(body["results"]) == 20
    assert body["next"] is not None
    assert body["previous"] is None


def test_page_size_is_capped_at_one_hundred(client, list_url) -> None:
    for index in range(5):
        _product(f"dish-{index}", f"Dish {index}")

    body = client.get(list_url, {"page_size": 500}).json()

    assert len(body["results"]) == 5


def test_unavailable_products_are_not_listed(client, list_url) -> None:
    _product("visible", "Visible")
    _product("sold-out", "Sold out", is_available=False)

    slugs = [product["slug"] for product in client.get(list_url).json()["results"]]

    assert slugs == ["visible"]


def test_search_matches_the_name_case_insensitively(client, list_url) -> None:
    _product("boss-salad", "Boss salat")
    _product("lagman", "Lagmon")

    body = client.get(list_url, {"search": "SALAT"}).json()

    assert [product["slug"] for product in body["results"]] == ["boss-salad"]


def test_search_matches_the_description(client, list_url) -> None:
    _product("boss-salad", "Boss salat", description="Pomidor va bodring")
    _product("lagman", "Lagmon")

    body = client.get(list_url, {"search": "bodring"}).json()

    assert [product["slug"] for product in body["results"]] == ["boss-salad"]


def test_search_ignores_accents_and_apostrophe_variants(client, list_url) -> None:
    _product("shurpa", "Choʻrba")

    hits = [
        [row["slug"] for row in client.get(list_url, {"search": term}).json()["results"]]
        for term in ("chorba", "cho'rba", "CHOʻRBA")
    ]

    assert hits == [["shurpa"], ["shurpa"], ["shurpa"]]


def test_search_is_scoped_to_the_requested_language(client, list_url) -> None:
    product = _product("boss-salad", "Boss salat")
    ProductTranslationFactory(product=product, language=Language.RU, name="Босс салат")

    russian = client.get(list_url, {"lang": "ru", "search": "салат"}).json()
    uzbek = client.get(list_url, {"lang": "uz", "search": "салат"}).json()

    assert russian["count"] == 1
    assert uzbek["count"] == 0


def test_a_product_matching_name_and_description_appears_once(client, list_url) -> None:
    _product("plov", "Plov", description="Plov, osh")

    body = client.get(list_url, {"search": "plov"}).json()

    assert body["count"] == 1


def test_category_filter_accepts_a_section_and_includes_its_subsections(client, list_url) -> None:
    section = CategoryFactory(slug="salads")
    subsection = CategoryFactory(slug="cold-salads", parent=section)
    _product("boss-salad", "Boss salat", category=section)
    _product("olivier", "Olivye", category=subsection)
    _product("lagman", "Lagmon")

    section_hits = client.get(list_url, {"category": "salads"}).json()
    subsection_hits = client.get(list_url, {"category": "cold-salads"}).json()

    assert {row["slug"] for row in section_hits["results"]} == {"boss-salad", "olivier"}
    assert {row["slug"] for row in subsection_hits["results"]} == {"olivier"}


def test_detail_returns_every_image(client, local_storage) -> None:
    product = _product("boss-salad", "Boss salat")
    ProductImageFactory(product=product, is_primary=True, alt="Boss salad")
    ProductImageFactory(product=product)

    body = client.get(reverse("menu:product-detail", args=["boss-salad"])).json()

    assert body["slug"] == "boss-salad"
    assert len(body["images"]) == 2
    assert body["image"]["alt"] == "Boss salad"
    assert set(body["image"]["srcset"]) == {"400", "800", "1600"}
    assert body["image"]["src"] == body["image"]["srcset"]["800"]
    assert body["image"]["width"] == 1200


def test_an_image_without_alt_text_borrows_the_product_name(client, local_storage) -> None:
    product = _product("boss-salad", "Boss salat")
    ProductImageFactory(product=product, is_primary=True, alt="")

    body = client.get(reverse("menu:product-detail", args=["boss-salad"])).json()

    assert body["image"]["alt"] == "Boss salat"


def test_detail_404s_for_an_unavailable_product(client) -> None:
    _product("sold-out", "Sold out", is_available=False)

    response = client.get(reverse("menu:product-detail", args=["sold-out"]))

    assert response.status_code == 404
    assert response.json()["detail"]


def test_an_unknown_language_is_rejected_on_the_list(client, list_url) -> None:
    response = client.get(list_url, {"lang": "fr"})

    assert response.status_code == 400
