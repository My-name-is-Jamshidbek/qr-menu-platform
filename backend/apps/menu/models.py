"""Menu schema: a two-level category tree, products priced in whole UZS units, and
per-product images stored as WebP derivatives.

Translations live in side tables (`CategoryTranslation`, `ProductTranslation`) instead
of JSON columns so that "which products have no Russian name?" is a single query.
"""

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver

from apps.common.enums import Language
from apps.common.images import (
    DERIVATIVE_WIDTHS,
    build_derivatives,
    derivative_name,
    open_image,
    validate_upload_size,
)
from apps.common.models import TimeStampedModel
from apps.common.translations import TranslatableMixin

MIN_PRICE_UZS = 100


class Category(TranslatableMixin, TimeStampedModel):
    """A menu section, or a subsection when `parent` is set.

    The tree is deliberately capped at two levels: the printed menu has sections and
    subsections and nothing deeper, and a bounded depth keeps the single-request menu
    endpoint a fixed number of queries.
    """

    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="children",
    )
    slug = models.SlugField(max_length=80, unique=True)
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "id"]
        verbose_name_plural = "categories"
        indexes = [models.Index(fields=["parent", "order"], name="category_parent_order_idx")]

    def __str__(self) -> str:
        return self.slug

    @property
    def is_root(self) -> bool:
        return self.parent_id is None

    def clean(self) -> None:
        """Forbid self-parenting and any tree deeper than two levels."""
        super().clean()
        if self.parent_id is None:
            return

        if self.pk and self.parent_id == self.pk:
            raise ValidationError({"parent": "A category cannot be its own parent."})

        if self.parent.parent_id is not None:
            raise ValidationError(
                {"parent": "The category tree is limited to two levels: section and subsection."}
            )

        if self.pk and self.children.exists():
            raise ValidationError(
                {"parent": "This category has subcategories, so it cannot become one itself."}
            )

    def save(self, *args, **kwargs):
        # The depth rule is a data invariant, not merely a form rule, so enforce it on
        # every write instead of only where a ModelForm happens to call `clean()`.
        self.clean()
        return super().save(*args, **kwargs)


class CategoryTranslation(TimeStampedModel):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="translations")
    language = models.CharField(max_length=2, choices=Language.choices)
    name = models.CharField(max_length=120)

    class Meta:
        ordering = ["language"]
        constraints = [
            models.UniqueConstraint(
                fields=["category", "language"], name="unique_category_translation"
            )
        ]

    def __str__(self) -> str:
        return f"{self.category.slug} [{self.language}]"


class Product(TranslatableMixin, TimeStampedModel):
    """A single menu item.

    `price` is an integer count of UZS. The currency has no practical minor unit, so integers
    remove rounding error and the class of bugs that comes with floating point money.
    """

    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    slug = models.SlugField(max_length=120, unique=True)
    price = models.PositiveIntegerField(
        validators=[MinValueValidator(MIN_PRICE_UZS)],
        help_text="Price in UZS, whole units only.",
    )
    is_available = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        indexes = [
            models.Index(fields=["category", "order"], name="product_category_order_idx"),
            models.Index(fields=["is_available"], name="product_is_available_idx"),
        ]
        constraints = [
            # The legacy dataset contains near-zero prices; the floor is a data rule, so
            # the database enforces it too and not just the form layer.
            models.CheckConstraint(
                condition=models.Q(price__gte=MIN_PRICE_UZS), name="product_price_minimum"
            )
        ]

    def __str__(self) -> str:
        return self.slug

    def description_for(self, language: str) -> tuple[str, bool]:
        """`(description, is_fallback)`, empty string when untranslated."""
        translation, is_fallback = self.translation_for(language)
        if translation is None:
            return "", False
        return translation.description, is_fallback

    @property
    def primary_image(self) -> "ProductImage | None":
        """The flagged primary image, else the first by display order."""
        images = list(self.images.all())
        for image in images:
            if image.is_primary:
                return image
        return images[0] if images else None


class ProductTranslation(TimeStampedModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="translations")
    language = models.CharField(max_length=2, choices=Language.choices)
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["language"]
        constraints = [
            models.UniqueConstraint(
                fields=["product", "language"], name="unique_product_translation"
            )
        ]
        indexes = [models.Index(fields=["language", "name"], name="product_translation_name_idx")]

    def __str__(self) -> str:
        return f"{self.product.slug} [{self.language}]"


class ProductImage(TimeStampedModel):
    """An uploaded photo plus its generated WebP variants.

    The original is kept (it is the source for regenerating variants); the API serves
    only the derivatives, whose keys are `<base_key>-<width>.webp`.
    """

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="products/%Y/%m/")
    alt = models.CharField(max_length=200, blank=True)
    order = models.PositiveSmallIntegerField(default=0)
    is_primary = models.BooleanField(default=False)
    # Intrinsic size of the original, so the frontend can reserve space and avoid CLS.
    width = models.PositiveIntegerField(default=0, editable=False)
    height = models.PositiveIntegerField(default=0, editable=False)

    class Meta:
        ordering = ["order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["product"],
                condition=models.Q(is_primary=True),
                name="one_primary_image",
            )
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remembering the name already in the database lets `save()` tell a fresh upload
        # from a metadata edit, so variants are rebuilt only when the bytes changed. A
        # brand-new instance has nothing stored yet, hence the empty string.
        self._persisted_image_name = ""

    @classmethod
    def from_db(cls, db, field_names, values):
        instance = super().from_db(db, field_names, values)
        instance._persisted_image_name = instance.image.name or ""
        return instance

    def __str__(self) -> str:
        return self.image.name or f"image #{self.pk}"

    @property
    def base_key(self) -> str:
        """Storage key of the original without its extension."""
        name = self.image.name or ""
        return name.rsplit(".", 1)[0] if "." in name.rsplit("/", 1)[-1] else name

    @property
    def derivative_keys(self) -> dict[int, str]:
        base = self.base_key
        return {width: derivative_name(base, width) for width in DERIVATIVE_WIDTHS}

    @property
    def srcset(self) -> dict[int, str]:
        """Public URL per width, ready to be rendered as a `srcset` attribute."""
        storage = self.image.storage
        return {width: storage.url(key) for width, key in self.derivative_keys.items()}

    def alt_for(self, language: str) -> str:
        """Explicit alt text, else the product's translated name."""
        if self.alt:
            return self.alt
        name, _ = self.product.name_for(language)
        return name

    def save(self, *args, **kwargs):
        raw = self._read_new_upload()
        if raw is not None:
            source = open_image(raw)
            self.width, self.height = source.size

        super().save(*args, **kwargs)

        if raw is not None:
            self._write_derivatives(source)
            self._persisted_image_name = self.image.name

    def _read_new_upload(self) -> bytes | None:
        """Bytes of a newly attached file, or None when the file is unchanged.

        The bytes are pulled into memory before the parent save consumes the stream;
        uploads are capped at 8 MB, so this stays bounded.
        """
        if not self.image or self.image.name == self._persisted_image_name:
            return None

        validate_upload_size(self.image.size)
        self.image.open()
        self.image.file.seek(0)
        return self.image.file.read()

    def _write_derivatives(self, source) -> None:
        storage = self.image.storage
        for width, content in build_derivatives(source).items():
            key = derivative_name(self.base_key, width)
            # Storage is configured not to overwrite, which would otherwise rename the
            # variant and break the deterministic srcset keys.
            if storage.exists(key):
                storage.delete(key)
            storage.save(key, content)

    def regenerate_derivatives(self) -> None:
        """Rebuild every WebP variant from the stored original."""
        with self.image.storage.open(self.image.name) as handle:
            source = open_image(handle.read())
        self.width, self.height = source.size
        self._write_derivatives(source)
        super().save(update_fields=["width", "height", "updated_at"])


@receiver(post_delete, sender=ProductImage, dispatch_uid="product_image_storage_cleanup")
def delete_product_image_files(sender, instance: ProductImage, **kwargs) -> None:
    """Drop the original and every derivative when the row goes away.

    Cascades from a deleted product land here too, so no orphan objects are left
    paying for storage in the bucket.
    """
    if not instance.image:
        return

    storage = instance.image.storage
    for key in (instance.image.name, *instance.derivative_keys.values()):
        if key and storage.exists(key):
            storage.delete(key)
