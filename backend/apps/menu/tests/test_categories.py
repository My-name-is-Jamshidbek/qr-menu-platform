"""Category tree, translation uniqueness and the Uzbek fallback."""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.common.enums import Language
from apps.menu.factories import CategoryFactory, CategoryTranslationFactory
from apps.menu.models import Category

pytestmark = pytest.mark.django_db


def test_a_subsection_may_hang_off_a_section() -> None:
    section = CategoryFactory()

    subsection = CategoryFactory(parent=section)

    assert subsection.parent == section
    assert section.children.get() == subsection
    assert subsection.is_root is False


def test_a_third_level_is_rejected_by_clean() -> None:
    section = CategoryFactory()
    subsection = CategoryFactory(parent=section)

    with pytest.raises(ValidationError) as error:
        Category(slug="too-deep", parent=subsection).clean()

    assert "two levels" in str(error.value)


def test_a_third_level_cannot_be_saved_even_without_a_form() -> None:
    section = CategoryFactory()
    subsection = CategoryFactory(parent=section)

    with pytest.raises(ValidationError):
        CategoryFactory(parent=subsection)

    assert Category.objects.count() == 2


def test_a_section_with_children_cannot_become_a_subsection() -> None:
    section = CategoryFactory()
    CategoryFactory(parent=section)
    other_section = CategoryFactory()

    section.parent = other_section
    with pytest.raises(ValidationError):
        section.save()


def test_a_category_cannot_be_its_own_parent() -> None:
    category = CategoryFactory()

    category.parent = category
    with pytest.raises(ValidationError):
        category.save()


def test_one_translation_per_language_per_category() -> None:
    category = CategoryFactory()

    with pytest.raises(IntegrityError), transaction.atomic():
        CategoryTranslationFactory(category=category, language=Language.UZ, name="Duplicate")


def test_the_same_language_may_translate_two_categories() -> None:
    CategoryFactory()
    CategoryFactory()

    assert Category.objects.filter(translations__language=Language.UZ).count() == 2


def test_a_missing_language_falls_back_to_uzbek() -> None:
    category = CategoryFactory(with_uz_translation__name="Salatlar")
    CategoryTranslationFactory(category=category, language=Language.RU, name="Салаты")

    assert category.name_for(Language.RU) == ("Салаты", False)
    assert category.name_for(Language.EN) == ("Salatlar", True)
    assert category.missing_languages == [Language.EN.value]


def test_categories_are_ordered_by_manual_order_then_id() -> None:
    second = CategoryFactory(order=5)
    first = CategoryFactory(order=1)

    assert list(Category.objects.all()) == [first, second]
