"""The staff CRUD surface: role gates, atomic nested translations, uploads, stats."""

from io import BytesIO

import pytest
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.factories import UserFactory
from apps.common.enums import Language
from apps.menu.factories import (
    CategoryFactory,
    ProductFactory,
    ProductImageFactory,
    ProductTranslationFactory,
)
from apps.menu.models import Product, ProductTranslation
from apps.tables.factories import TableScanFactory

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def clean_cache():
    cache.clear()
    yield
    cache.clear()


def _client_for(user) -> APIClient:
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    return client


@pytest.fixture
def staff_client() -> APIClient:
    return _client_for(UserFactory())


@pytest.fixture
def category():
    return CategoryFactory(slug="salads")


def _png_upload(name: str = "dish.png") -> SimpleUploadedFile:
    buffer = BytesIO()
    Image.new("RGB", (1200, 900), "teal").save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


# --------------------------------------------------------------------------- access


def test_anonymous_requests_are_rejected() -> None:
    response = APIClient().get(reverse("menu:admin-product-list"))

    assert response.status_code == 401


def test_a_staff_account_may_edit_the_menu(staff_client) -> None:
    assert staff_client.get(reverse("menu:admin-product-list")).status_code == 200


def test_a_staff_account_may_not_manage_tables(staff_client) -> None:
    response = staff_client.get(reverse("tables:admin-table-list"))

    assert response.status_code == 403


# --------------------------------------------------------------------------- products


def test_creating_a_product_writes_every_translation(staff_client, category) -> None:
    payload = {
        "category": category.pk,
        "price": 30_000,
        "is_available": True,
        "translations": [
            {"language": "uz", "name": "Boss salat", "description": ""},
            {"language": "ru", "name": "Босс салат", "description": ""},
        ],
    }

    response = staff_client.post(reverse("menu:admin-product-list"), payload, format="json")

    assert response.status_code == 201
    product = Product.objects.get(pk=response.json()["id"])
    assert {row.language: row.name for row in product.translations.all()} == {
        "uz": "Boss salat",
        "ru": "Босс салат",
    }


def test_a_created_product_gets_a_slug_from_its_uzbek_name(staff_client, category) -> None:
    payload = {
        "category": category.pk,
        "price": 30_000,
        "translations": [{"language": "uz", "name": "Choʻrba"}],
    }

    body = staff_client.post(reverse("menu:admin-product-list"), payload, format="json").json()

    assert body["slug"] == "chorba"


def test_slugs_stay_unique_across_products_with_the_same_name(staff_client, category) -> None:
    payload = {
        "category": category.pk,
        "price": 30_000,
        "translations": [{"language": "uz", "name": "Lagmon"}],
    }
    url = reverse("menu:admin-product-list")

    first = staff_client.post(url, payload, format="json").json()
    second = staff_client.post(url, payload, format="json").json()

    assert [first["slug"], second["slug"]] == ["lagmon", "lagmon-2"]


def test_a_product_without_an_uzbek_translation_is_rejected(staff_client, category) -> None:
    payload = {
        "category": category.pk,
        "price": 30_000,
        "translations": [{"language": "ru", "name": "Босс салат"}],
    }

    response = staff_client.post(reverse("menu:admin-product-list"), payload, format="json")

    assert response.status_code == 400
    assert "translations" in response.json()["field_errors"]
    assert not Product.objects.exists()


def test_a_duplicate_language_in_one_payload_is_rejected(staff_client, category) -> None:
    payload = {
        "category": category.pk,
        "price": 30_000,
        "translations": [
            {"language": "uz", "name": "One"},
            {"language": "uz", "name": "Two"},
        ],
    }

    response = staff_client.post(reverse("menu:admin-product-list"), payload, format="json")

    assert response.status_code == 400


def test_a_rejected_write_leaves_no_partial_product(staff_client, category) -> None:
    payload = {
        "category": category.pk,
        "price": 1,  # below the model's UZS floor
        "translations": [{"language": "uz", "name": "Cheap"}],
    }

    response = staff_client.post(reverse("menu:admin-product-list"), payload, format="json")

    assert response.status_code == 400
    assert not Product.objects.exists()
    assert not ProductTranslation.objects.exists()


def test_the_list_reports_which_languages_are_missing(staff_client) -> None:
    ProductFactory(slug="boss-salad")

    row = staff_client.get(reverse("menu:admin-product-list")).json()["results"][0]

    assert row["missing_translations"] == ["ru", "en"]
    assert [entry["language"] for entry in row["translations"]] == ["uz"]


def test_patching_translations_replaces_the_whole_set(staff_client) -> None:
    product = ProductFactory(slug="boss-salad", with_uz_translation=False)
    ProductTranslationFactory(product=product, language=Language.UZ, name="Eski")
    ProductTranslationFactory(product=product, language=Language.EN, name="Old")

    response = staff_client.patch(
        reverse("menu:admin-product-detail", args=[product.pk]),
        {"translations": [{"language": "uz", "name": "Yangi"}]},
        format="json",
    )

    assert response.status_code == 200
    assert {row.language: row.name for row in product.translations.all()} == {"uz": "Yangi"}


def test_patching_a_scalar_field_leaves_translations_alone(staff_client) -> None:
    product = ProductFactory(slug="boss-salad")

    response = staff_client.patch(
        reverse("menu:admin-product-detail", args=[product.pk]),
        {"is_available": False},
        format="json",
    )

    assert response.status_code == 200
    product.refresh_from_db()
    assert product.is_available is False
    assert product.translations.count() == 1


def test_deleting_a_product_removes_it(staff_client) -> None:
    product = ProductFactory(slug="boss-salad")

    response = staff_client.delete(reverse("menu:admin-product-detail", args=[product.pk]))

    assert response.status_code == 204
    assert not Product.objects.filter(pk=product.pk).exists()


# --------------------------------------------------------------------------- images


def test_uploading_an_image_stores_three_webp_widths(staff_client, local_storage) -> None:
    product = ProductFactory(slug="boss-salad")

    response = staff_client.post(
        reverse("menu:admin-product-image-create", args=[product.pk]),
        {"image": _png_upload(), "alt": "Boss salad"},
        format="multipart",
    )

    assert response.status_code == 201
    image = product.images.get()
    assert (image.width, image.height) == (1200, 900)
    for key in image.derivative_keys.values():
        assert image.image.storage.exists(key)


def test_the_first_upload_becomes_the_primary_image(staff_client, local_storage) -> None:
    product = ProductFactory(slug="boss-salad")

    staff_client.post(
        reverse("menu:admin-product-image-create", args=[product.pk]),
        {"image": _png_upload()},
        format="multipart",
    )

    assert product.images.get().is_primary is True


def test_a_new_primary_image_demotes_the_previous_one(staff_client, local_storage) -> None:
    product = ProductFactory(slug="boss-salad")
    incumbent = ProductImageFactory(product=product, is_primary=True)

    response = staff_client.post(
        reverse("menu:admin-product-image-create", args=[product.pk]),
        {"image": _png_upload("second.png"), "is_primary": True},
        format="multipart",
    )

    assert response.status_code == 201
    incumbent.refresh_from_db()
    assert incumbent.is_primary is False
    assert product.images.filter(is_primary=True).count() == 1


def test_uploading_a_non_image_is_rejected(staff_client, local_storage) -> None:
    product = ProductFactory(slug="boss-salad")

    response = staff_client.post(
        reverse("menu:admin-product-image-create", args=[product.pk]),
        {"image": SimpleUploadedFile("evil.png", b"#!/bin/sh\n", content_type="image/png")},
        format="multipart",
    )

    assert response.status_code == 400
    assert not product.images.exists()


def test_uploading_against_an_unknown_product_is_a_404(staff_client, local_storage) -> None:
    response = staff_client.post(
        reverse("menu:admin-product-image-create", args=[9999]),
        {"image": _png_upload()},
        format="multipart",
    )

    assert response.status_code == 404


def test_deleting_an_image_drops_its_derivatives(staff_client, local_storage) -> None:
    product = ProductFactory(slug="boss-salad")
    image = ProductImageFactory(product=product)
    keys = list(image.derivative_keys.values())

    response = staff_client.delete(
        reverse("menu:admin-product-image-destroy", args=[product.pk, image.pk])
    )

    assert response.status_code == 204
    assert not any(image.image.storage.exists(key) for key in keys)


# --------------------------------------------------------------------------- categories


def test_creating_a_category_writes_its_translations(staff_client) -> None:
    response = staff_client.post(
        reverse("menu:admin-category-list"),
        {
            "order": 1,
            "translations": [
                {"language": "uz", "name": "Salatlar"},
                {"language": "ru", "name": "Салаты"},
            ],
        },
        format="json",
    )

    assert response.status_code == 201
    assert response.json()["slug"] == "salatlar"
    assert response.json()["missing_translations"] == ["en"]


def test_a_third_level_category_is_rejected(staff_client) -> None:
    section = CategoryFactory(slug="salads")
    subsection = CategoryFactory(slug="cold-salads", parent=section)

    response = staff_client.post(
        reverse("menu:admin-category-list"),
        {"parent": subsection.pk, "translations": [{"language": "uz", "name": "Deeper"}]},
        format="json",
    )

    assert response.status_code == 400
    assert "parent" in response.json()["field_errors"]


def test_deleting_a_category_with_products_is_a_conflict(staff_client, category) -> None:
    ProductFactory(category=category)

    response = staff_client.delete(reverse("menu:admin-category-detail", args=[category.pk]))

    assert response.status_code == 409
    assert response.json()["code"] == "category_in_use"


def test_an_empty_category_can_be_deleted(staff_client, category) -> None:
    response = staff_client.delete(reverse("menu:admin-category-detail", args=[category.pk]))

    assert response.status_code == 204


# --------------------------------------------------------------------------- stats


def test_stats_count_products_translation_gaps_and_recent_scans(staff_client) -> None:
    complete = ProductFactory(slug="complete")
    ProductTranslationFactory(product=complete, language=Language.RU, name="Полный")
    ProductTranslationFactory(product=complete, language=Language.EN, name="Complete")
    ProductFactory(slug="partial", is_available=False)
    TableScanFactory()

    body = staff_client.get(reverse("menu:admin-stats")).json()

    assert body["product_count"] == 2
    assert body["available_product_count"] == 1
    assert body["missing_translation_count"] == 1
    assert body["scans_last_7_days"] == 1


def test_timestamps_are_rendered_in_utc(staff_client) -> None:
    """The server runs in Asia/Tashkent; the contract promises UTC to every consumer."""
    product = ProductFactory(slug="boss-salad")

    body = staff_client.get(reverse("menu:admin-product-detail", args=[product.pk])).json()

    assert body["created_at"].endswith("Z")
    assert body["updated_at"].endswith("Z")
