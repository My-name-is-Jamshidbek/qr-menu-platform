"""The admin columns staff rely on: Uzbek name, price and translation gaps."""

import pytest
from django.urls import reverse

from apps.accounts.factories import DEFAULT_TEST_PASSWORD, UserFactory
from apps.common.enums import Language
from apps.menu.admin import THIN_SPACE, ProductAdmin
from apps.menu.factories import ProductFactory, ProductTranslationFactory
from apps.menu.models import Product

pytestmark = pytest.mark.django_db


@pytest.fixture
def product_admin() -> ProductAdmin:
    from django.contrib import admin

    return admin.site._registry[Product]


def test_the_list_shows_the_uzbek_name_and_a_grouped_price(product_admin) -> None:
    product = ProductFactory(price=30_000, with_uz_translation__name="Boss salat")

    assert product_admin.name_uz(product) == "Boss salat"
    assert product_admin.price_uzs(product) == f"30{THIN_SPACE}000"


def test_the_missing_translations_column_names_the_gaps(product_admin) -> None:
    product = ProductFactory()

    assert Language.RU.value in product_admin.missing_translations(product)
    assert Language.EN.value in product_admin.missing_translations(product)


def test_a_fully_translated_product_is_marked_complete(product_admin) -> None:
    product = ProductFactory()
    ProductTranslationFactory(product=product, language=Language.RU, name="Босс салат")
    ProductTranslationFactory(product=product, language=Language.EN, name="Boss salad")

    assert "complete" in product_admin.missing_translations(product)


def test_the_product_changelist_renders_and_is_searchable_by_translation(client) -> None:
    UserFactory(username="admin-user", admin=True, is_staff=True)
    client.login(username="admin-user", password=DEFAULT_TEST_PASSWORD)
    ProductFactory(with_uz_translation__name="Boss salat")
    ProductFactory(with_uz_translation__name="Lagmon")

    response = client.get(reverse("admin:menu_product_changelist"), {"q": "Boss"})

    assert response.status_code == 200
    assert b"Boss salat" in response.content
    assert b"Lagmon" not in response.content
