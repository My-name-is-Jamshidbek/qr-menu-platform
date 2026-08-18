"""Product pricing, translation uniqueness and deletion rules."""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError

from apps.common.enums import Language
from apps.menu.factories import CategoryFactory, ProductFactory, ProductTranslationFactory
from apps.menu.models import MIN_PRICE_UZS, Product

pytestmark = pytest.mark.django_db


def test_a_price_below_the_floor_fails_validation() -> None:
    product = ProductFactory.build(category=CategoryFactory(), price=5)

    with pytest.raises(ValidationError) as error:
        product.full_clean(exclude=["slug"])

    assert "price" in error.value.message_dict


def test_the_database_also_refuses_a_price_below_the_floor() -> None:
    # The legacy dataset carries near-zero prices; a bulk import must not slip them past
    # the form layer.
    with pytest.raises(IntegrityError), transaction.atomic():
        Product.objects.create(category=CategoryFactory(), slug="cheap", price=5)


def test_the_floor_itself_is_allowed() -> None:
    product = ProductFactory(price=MIN_PRICE_UZS)

    product.full_clean(exclude=["slug"])
    assert Product.objects.get(pk=product.pk).price == MIN_PRICE_UZS


def test_one_translation_per_language_per_product() -> None:
    product = ProductFactory()

    with pytest.raises(IntegrityError), transaction.atomic():
        ProductTranslationFactory(product=product, language=Language.UZ, name="Duplicate")


def test_name_and_description_fall_back_to_uzbek() -> None:
    product = ProductFactory(with_uz_translation__name="Boss salat")
    ProductTranslationFactory(
        product=product, language=Language.RU, name="Босс салат", description="Свежий"
    )

    assert product.name_for(Language.RU) == ("Босс салат", False)
    assert product.description_for(Language.RU) == ("Свежий", False)
    assert product.name_for(Language.EN) == ("Boss salat", True)
    assert product.missing_languages == [Language.EN.value]


def test_an_untranslated_product_reports_no_name_and_no_fallback() -> None:
    product = ProductFactory(with_uz_translation=False)

    assert product.name_for(Language.UZ) == ("", False)
    assert product.missing_languages == [
        Language.UZ.value,
        Language.RU.value,
        Language.EN.value,
    ]


def test_a_category_holding_products_cannot_be_deleted() -> None:
    product = ProductFactory()

    with pytest.raises(ProtectedError):
        product.category.delete()


def test_products_are_ordered_by_manual_order_then_id() -> None:
    category = CategoryFactory()
    second = ProductFactory(category=category, order=9)
    first = ProductFactory(category=category, order=2)

    assert list(Product.objects.all()) == [first, second]
