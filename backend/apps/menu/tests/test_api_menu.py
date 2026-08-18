"""The single-request menu aggregate: shape, fallback, caching and query budget."""

import pytest
from django.core.cache import cache
from django.urls import reverse
from rest_framework.test import APIClient

from apps.common.enums import Language
from apps.menu.api.cache import menu_cache_key
from apps.menu.factories import (
    CategoryFactory,
    CategoryTranslationFactory,
    ProductFactory,
    ProductTranslationFactory,
)

pytestmark = pytest.mark.django_db

# `ATOMIC_REQUESTS` wraps every request in a savepoint pair, and the query capture counts
# both statements, so each budget below is "data queries + 2".
TRANSACTION_STATEMENTS = 2

# categories, category translations, products, product translations, product images.
MENU_QUERY_BUDGET = 5 + TRANSACTION_STATEMENTS


@pytest.fixture(autouse=True)
def clean_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def client() -> APIClient:
    return APIClient()


@pytest.fixture
def menu_url() -> str:
    return reverse("menu:menu")


def _build_section() -> tuple:
    section = CategoryFactory(slug="salads", order=0)
    CategoryTranslationFactory(category=section, language=Language.RU, name="Салаты")
    subsection = CategoryFactory(slug="cold-salads", parent=section, order=1)
    product = ProductFactory(
        slug="boss-salad", category=section, price=30_000, with_uz_translation=False
    )
    ProductTranslationFactory(
        product=product, language=Language.UZ, name="Boss salat", description="Yangi"
    )
    return section, subsection, product


def test_menu_nests_sections_subsections_and_products(client, menu_url) -> None:
    _build_section()

    body = client.get(menu_url).json()

    assert [category["slug"] for category in body["categories"]] == ["salads"]
    section = body["categories"][0]
    assert section["name"] == "Section salads"
    assert [child["slug"] for child in section["children"]] == ["cold-salads"]
    assert section["products"][0] == {
        "slug": "boss-salad",
        "name": "Boss salat",
        "description": "Yangi",
        "is_fallback": False,
        "price": 30_000,
        "category_slug": "salads",
        "image": None,
    }
    assert body["generated_at"].endswith("Z")


def test_subsection_products_are_listed_under_their_section(client, menu_url) -> None:
    section, subsection, _ = _build_section()
    ProductFactory(slug="olivier", category=subsection)

    section_body = client.get(menu_url).json()["categories"][0]

    slugs = {product["slug"]: product["category_slug"] for product in section_body["products"]}
    assert slugs == {"boss-salad": "salads", "olivier": "cold-salads"}


def test_untranslated_strings_fall_back_to_uzbek_and_say_so(client, menu_url) -> None:
    _build_section()

    body = client.get(menu_url, {"lang": Language.EN.value}).json()

    section = body["categories"][0]
    # The section has an English name via neither route, so Uzbek is served and flagged.
    assert section["is_fallback"] is True
    assert section["products"][0]["is_fallback"] is True


def test_a_translated_string_is_not_flagged_as_fallback(client, menu_url) -> None:
    _build_section()

    section = client.get(menu_url, {"lang": Language.RU.value}).json()["categories"][0]

    assert section["name"] == "Салаты"
    assert section["is_fallback"] is False


def test_inactive_categories_and_unavailable_products_are_hidden(client, menu_url) -> None:
    section, _, product = _build_section()
    product.is_available = False
    product.save()
    CategoryFactory(slug="hidden", is_active=False)

    body = client.get(menu_url).json()

    assert [category["slug"] for category in body["categories"]] == ["salads"]
    assert body["categories"][0]["products"] == []


def test_menu_costs_a_fixed_number_of_queries_regardless_of_size(
    client, menu_url, django_assert_num_queries
) -> None:
    section, subsection, _ = _build_section()
    for index in range(12):
        ProductFactory(slug=f"dish-{index}", category=subsection if index % 2 else section)

    cache.clear()
    with django_assert_num_queries(MENU_QUERY_BUDGET):
        response = client.get(menu_url)

    assert response.status_code == 200
    assert len(response.json()["categories"][0]["products"]) == 13


def test_the_second_request_is_served_from_redis(
    client, menu_url, django_assert_num_queries
) -> None:
    _build_section()
    client.get(menu_url)

    with django_assert_num_queries(TRANSACTION_STATEMENTS):
        response = client.get(menu_url)

    assert response.status_code == 200
    assert cache.get(menu_cache_key(Language.UZ.value)) is not None


def test_each_language_is_cached_separately(client, menu_url) -> None:
    _build_section()

    client.get(menu_url, {"lang": Language.RU.value})

    assert cache.get(menu_cache_key(Language.RU.value)) is not None
    assert cache.get(menu_cache_key(Language.UZ.value)) is None


def test_an_unknown_language_is_rejected(client, menu_url) -> None:
    response = client.get(menu_url, {"lang": "de"})

    assert response.status_code == 400
    assert "lang" in response.json()["field_errors"]
