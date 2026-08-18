"""Factories for the menu models.

`CategoryFactory` and `ProductFactory` create the Uzbek translation by default, since
an object without one is invalid as far as the API is concerned. Pass
`with_uz_translation=False` to build the untranslated edge case on purpose.
"""

import factory
from factory.django import DjangoModelFactory, ImageField

from apps.common.enums import Language
from apps.menu.models import (
    Category,
    CategoryTranslation,
    Product,
    ProductImage,
    ProductTranslation,
)


class CategoryTranslationFactory(DjangoModelFactory):
    class Meta:
        model = CategoryTranslation

    category = factory.SubFactory("apps.menu.factories.CategoryFactory")
    language = Language.UZ
    name = factory.Sequence(lambda n: f"Category name {n}")


class CategoryFactory(DjangoModelFactory):
    class Meta:
        model = Category
        skip_postgeneration_save = True

    parent = None
    slug = factory.Sequence(lambda n: f"category-{n}")
    order = factory.Sequence(int)
    is_active = True

    @factory.post_generation
    def with_uz_translation(obj, create: bool, extracted, **kwargs) -> None:
        if create and extracted is not False:
            CategoryTranslationFactory(
                category=obj, language=Language.UZ, name=kwargs.get("name", f"Section {obj.slug}")
            )


class ProductTranslationFactory(DjangoModelFactory):
    class Meta:
        model = ProductTranslation

    product = factory.SubFactory("apps.menu.factories.ProductFactory")
    language = Language.UZ
    name = factory.Sequence(lambda n: f"Product name {n}")
    description = ""


class ProductFactory(DjangoModelFactory):
    class Meta:
        model = Product
        skip_postgeneration_save = True

    category = factory.SubFactory(CategoryFactory)
    slug = factory.Sequence(lambda n: f"product-{n}")
    price = 25_000
    is_available = True
    order = factory.Sequence(int)

    @factory.post_generation
    def with_uz_translation(obj, create: bool, extracted, **kwargs) -> None:
        if create and extracted is not False:
            ProductTranslationFactory(
                product=obj, language=Language.UZ, name=kwargs.get("name", f"Dish {obj.slug}")
            )


class ProductImageFactory(DjangoModelFactory):
    class Meta:
        model = ProductImage

    product = factory.SubFactory(ProductFactory)
    # A real encodable image, so the WebP pipeline runs exactly as it does in production.
    image = ImageField(width=1200, height=900, format="JPEG", filename="dish.jpg")
    alt = ""
    order = factory.Sequence(int)
    is_primary = False
