"""Image pipeline: WebP derivatives, intrinsic size, the single-primary rule and cleanup."""

from io import BytesIO

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from PIL import Image

from apps.common.enums import Language
from apps.common.images import DERIVATIVE_WIDTHS
from apps.menu.factories import ProductFactory, ProductImageFactory
from apps.menu.models import ProductImage

pytestmark = pytest.mark.django_db


def _open_derivative(image: ProductImage, width: int) -> Image.Image:
    with image.image.storage.open(image.derivative_keys[width]) as handle:
        return Image.open(BytesIO(handle.read()))


def test_saving_an_image_writes_one_webp_per_width(local_storage) -> None:
    image = ProductImageFactory()

    for width in DERIVATIVE_WIDTHS:
        derivative = _open_derivative(image, width)
        assert derivative.format == "WEBP"
        # The source is 1200px wide, so the 1600 variant is not upscaled.
        assert derivative.width == min(width, 1200)


def test_the_original_intrinsic_size_is_recorded(local_storage) -> None:
    image = ProductImageFactory()

    assert (image.width, image.height) == (1200, 900)
    assert ProductImage.objects.get(pk=image.pk).width == 1200


def test_srcset_exposes_a_url_per_width(local_storage) -> None:
    image = ProductImageFactory()

    srcset = image.srcset

    assert set(srcset) == set(DERIVATIVE_WIDTHS)
    for width, url in srcset.items():
        assert url.endswith(f"-{width}.webp")


def test_derivatives_are_not_rewritten_when_only_metadata_changes(local_storage) -> None:
    image = ProductImageFactory()
    key = image.derivative_keys[800]
    original_size = image.image.storage.size(key)

    image.alt = "Boss salad"
    image.save()

    assert image.image.storage.size(key) == original_size
    assert image.derivative_keys[800] == key


def test_derivatives_can_be_rebuilt_from_the_stored_original(local_storage) -> None:
    image = ProductImageFactory()
    image.image.storage.delete(image.derivative_keys[400])

    image.regenerate_derivatives()

    assert _open_derivative(image, 400).width == 400


def test_a_product_may_have_only_one_primary_image(local_storage) -> None:
    product = ProductFactory()
    ProductImageFactory(product=product, is_primary=True)

    with pytest.raises(IntegrityError), transaction.atomic():
        ProductImageFactory(product=product, is_primary=True)


def test_two_products_may_each_have_a_primary_image(local_storage) -> None:
    ProductImageFactory(product=ProductFactory(), is_primary=True)
    ProductImageFactory(product=ProductFactory(), is_primary=True)

    assert ProductImage.objects.filter(is_primary=True).count() == 2


def test_non_primary_images_are_unconstrained(local_storage) -> None:
    product = ProductFactory()
    ProductImageFactory(product=product)
    ProductImageFactory(product=product)

    assert product.images.count() == 2


def test_the_primary_image_is_preferred_over_display_order(local_storage) -> None:
    product = ProductFactory()
    ProductImageFactory(product=product, order=0)
    primary = ProductImageFactory(product=product, order=5, is_primary=True)

    assert product.primary_image == primary


def test_deleting_an_image_removes_every_stored_object(local_storage) -> None:
    image = ProductImageFactory()
    storage = image.image.storage
    keys = [image.image.name, *image.derivative_keys.values()]
    assert all(storage.exists(key) for key in keys)

    image.delete()

    assert not any(storage.exists(key) for key in keys)


def test_deleting_a_product_cascades_to_its_image_files(local_storage) -> None:
    image = ProductImageFactory()
    storage = image.image.storage
    key = image.derivative_keys[800]

    image.product.delete()

    assert not storage.exists(key)


def test_a_file_that_is_not_an_image_is_rejected(local_storage) -> None:
    upload = SimpleUploadedFile("payload.png", b"#!/bin/sh\nrm -rf /", content_type="image/png")

    with pytest.raises(ValidationError):
        ProductImageFactory(image=upload)


def test_alt_text_falls_back_to_the_translated_product_name(local_storage) -> None:
    product = ProductFactory(with_uz_translation__name="Boss salat")
    image = ProductImageFactory(product=product, alt="")

    assert image.alt_for(Language.EN) == "Boss salat"

    image.alt = "Plated salad"
    assert image.alt_for(Language.EN) == "Plated salad"
