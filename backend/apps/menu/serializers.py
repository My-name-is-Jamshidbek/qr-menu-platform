"""Serializers for the public menu and the staff-facing admin surface.

The public serializers are deliberately plain `Serializer` subclasses reading already
prefetched relations: they never touch the database themselves, which is what lets the
whole menu be rendered from one fixed set of queries and then cached as JSON.
"""

from typing import Any

from django.db import transaction
from django.utils.text import slugify
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.common.api.search import fold
from apps.common.enums import Language
from apps.common.serializers import ImageSerializer, UtcDateTimeField
from apps.menu.models import (
    Category,
    CategoryTranslation,
    Product,
    ProductImage,
    ProductTranslation,
)

# The width the plain `src` attribute points at; the rest live in `srcset`.
DEFAULT_SRC_WIDTH = 800

REQUIRED_LANGUAGE = Language.fallback().value


def serialize_image(image: ProductImage, product_name: str) -> dict[str, Any]:
    """The one image shape the whole API returns."""
    srcset = {str(width): url for width, url in image.srcset.items()}
    return {
        "alt": image.alt or product_name,
        "width": image.width,
        "height": image.height,
        "src": srcset[str(DEFAULT_SRC_WIDTH)],
        "srcset": srcset,
    }


def unique_slug(model: type, name: str, prefix: str, exclude_pk: int | None = None) -> str:
    """A stable, unique slug derived from a (possibly non-Latin) display name."""
    base = slugify(fold(name)) or prefix
    candidate = base
    suffix = 2
    queryset = model.objects.all()
    if exclude_pk is not None:
        queryset = queryset.exclude(pk=exclude_pk)
    while queryset.filter(slug=candidate).exists():
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate


# --------------------------------------------------------------------------- public


class LocalisedMixin:
    """Shared `(name, description, is_fallback)` resolution for a translated object."""

    def _translation(self, instance) -> tuple[Any, bool]:
        language = self.context["language"]
        return instance.translation_for(language)

    def get_name(self, instance) -> str:
        translation, _ = self._translation(instance)
        return translation.name if translation else ""

    def get_is_fallback(self, instance) -> bool:
        _, is_fallback = self._translation(instance)
        return is_fallback


class SubcategorySerializer(LocalisedMixin, serializers.Serializer):
    """A second-level category: a label only, its products hang off the section."""

    slug = serializers.SlugField()
    name = serializers.SerializerMethodField()
    is_fallback = serializers.SerializerMethodField()


class PublicProductSerializer(LocalisedMixin, serializers.Serializer):
    """A product as the storefront reads it, in one language with Uzbek fallback."""

    slug = serializers.SlugField()
    name = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    is_fallback = serializers.SerializerMethodField()
    price = serializers.IntegerField()
    category_slug = serializers.SlugField(source="category.slug")
    image = serializers.SerializerMethodField()

    def get_description(self, product: Product) -> str:
        translation, _ = self._translation(product)
        return translation.description if translation else ""

    @extend_schema_field(ImageSerializer(allow_null=True))
    def get_image(self, product: Product) -> dict[str, Any] | None:
        image = product.primary_image
        if image is None:
            return None
        return serialize_image(image, self.get_name(product))


class ProductDetailSerializer(PublicProductSerializer):
    """One product with every photo, for the product page."""

    images = serializers.SerializerMethodField()

    @extend_schema_field(ImageSerializer(many=True))
    def get_images(self, product: Product) -> list[dict[str, Any]]:
        name = self.get_name(product)
        return [serialize_image(image, name) for image in product.images.all()]


class MenuCategorySerializer(LocalisedMixin, serializers.Serializer):
    """A top-level section with its subsections and every product beneath it.

    Children and products come from lookup tables in the context rather than from the
    instance's related managers: the aggregate has already loaded both in bulk, and
    touching `category.products` here would reintroduce a query per section.
    """

    slug = serializers.SlugField()
    name = serializers.SerializerMethodField()
    is_fallback = serializers.SerializerMethodField()
    children = serializers.SerializerMethodField()
    products = serializers.SerializerMethodField()

    @extend_schema_field(SubcategorySerializer(many=True))
    def get_children(self, category) -> list[dict[str, Any]]:
        rows = self.context["children_by_section"].get(category.pk, [])
        return SubcategorySerializer(rows, many=True, context=self.context).data

    @extend_schema_field(PublicProductSerializer(many=True))
    def get_products(self, category) -> list[dict[str, Any]]:
        rows = self.context["products_by_section"].get(category.pk, [])
        return PublicProductSerializer(rows, many=True, context=self.context).data


class MenuSerializer(serializers.Serializer):
    """The whole menu aggregate returned by `GET /menu/`."""

    categories = MenuCategorySerializer(many=True)
    generated_at = serializers.DateTimeField()


# --------------------------------------------------------------------------- admin


class ProductTranslationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductTranslation
        fields = ["language", "name", "description"]
        extra_kwargs = {"description": {"required": False, "allow_blank": True}}


class CategoryTranslationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoryTranslation
        fields = ["language", "name"]


class AdminProductImageSerializer(serializers.ModelSerializer):
    """A stored photo with its derivative URLs, as the admin UI lists them."""

    srcset = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ["id", "alt", "order", "is_primary", "width", "height", "srcset"]
        read_only_fields = ["width", "height"]

    @extend_schema_field(serializers.DictField(child=serializers.URLField()))
    def get_srcset(self, image: ProductImage) -> dict[str, str]:
        return {str(width): url for width, url in image.srcset.items()}


class TranslationWriteMixin:
    """Atomic create/update of a translated object together with its translation rows.

    A half-written product — saved, but with the Russian name lost to a validation error
    on the second row — is worse than a rejected request, so the whole payload lands
    inside one transaction and the Uzbek row is mandatory.
    """

    translation_model: type
    translation_field: str
    slug_prefix: str

    def validate_translations(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        languages = [row["language"] for row in rows]
        if len(languages) != len(set(languages)):
            raise serializers.ValidationError("Each language may appear only once.")
        if self.partial and not rows:
            return rows
        if REQUIRED_LANGUAGE not in languages:
            raise serializers.ValidationError(f"A '{REQUIRED_LANGUAGE}' translation is required.")
        return rows

    def _write_translations(self, instance, rows: list[dict[str, Any]]) -> None:
        self.translation_model.objects.filter(**{self.translation_field: instance}).delete()
        self.translation_model.objects.bulk_create(
            [self.translation_model(**{self.translation_field: instance}, **row) for row in rows]
        )

    @transaction.atomic
    def create(self, validated_data: dict[str, Any]):
        rows = validated_data.pop("translations")
        primary = next(row for row in rows if row["language"] == REQUIRED_LANGUAGE)
        validated_data.setdefault(
            "slug",
            unique_slug(self.Meta.model, primary["name"], self.slug_prefix),
        )
        instance = super().create(validated_data)
        self._write_translations(instance, rows)
        return instance

    @transaction.atomic
    def update(self, instance, validated_data: dict[str, Any]):
        rows = validated_data.pop("translations", None)
        instance = super().update(instance, validated_data)
        if rows is not None:
            self._write_translations(instance, rows)
        return instance


class AdminProductSerializer(TranslationWriteMixin, serializers.ModelSerializer):
    """Full product record: every translation, the gaps, and the stored photos."""

    translations = ProductTranslationSerializer(many=True)
    missing_translations = serializers.SerializerMethodField()
    images = AdminProductImageSerializer(many=True, read_only=True)
    created_at = UtcDateTimeField(read_only=True)
    updated_at = UtcDateTimeField(read_only=True)

    translation_model = ProductTranslation
    translation_field = "product"
    slug_prefix = "product"

    class Meta:
        model = Product
        fields = [
            "id",
            "category",
            "slug",
            "price",
            "is_available",
            "order",
            "translations",
            "missing_translations",
            "images",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]
        extra_kwargs = {"slug": {"required": False}}

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_missing_translations(self, product: Product) -> list[str]:
        return product.missing_languages


class AdminCategorySerializer(TranslationWriteMixin, serializers.ModelSerializer):
    """A section or subsection with all of its names."""

    translations = CategoryTranslationSerializer(many=True)
    missing_translations = serializers.SerializerMethodField()
    product_count = serializers.IntegerField(read_only=True)
    created_at = UtcDateTimeField(read_only=True)
    updated_at = UtcDateTimeField(read_only=True)

    translation_model = CategoryTranslation
    translation_field = "category"
    slug_prefix = "category"

    class Meta:
        model = Category
        fields = [
            "id",
            "parent",
            "slug",
            "order",
            "is_active",
            "translations",
            "missing_translations",
            "product_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]
        extra_kwargs = {"slug": {"required": False}}

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_missing_translations(self, category: Category) -> list[str]:
        return category.missing_languages

    def validate_parent(self, parent: Category | None) -> Category | None:
        """Mirror the model's two-level rule as a 400 instead of a 500.

        `Category.save()` enforces the same invariant, but it raises Django's
        `ValidationError`, which DRF would surface as a server error.
        """
        if parent is None:
            return parent
        if self.instance is not None and parent.pk == self.instance.pk:
            raise serializers.ValidationError("A category cannot be its own parent.")
        if parent.parent_id is not None:
            raise serializers.ValidationError(
                "The category tree is limited to two levels: section and subsection."
            )
        if self.instance is not None and self.instance.children.exists():
            raise serializers.ValidationError(
                "This category has subcategories, so it cannot become one itself."
            )
        return parent


class ProductImageUploadSerializer(serializers.ModelSerializer):
    """Multipart upload; the model turns the original into three WebP widths."""

    image = serializers.ImageField(write_only=True)

    class Meta:
        model = ProductImage
        fields = ["id", "image", "alt", "order", "is_primary", "width", "height"]
        read_only_fields = ["width", "height"]

    @transaction.atomic
    def create(self, validated_data: dict[str, Any]) -> ProductImage:
        product = validated_data["product"]
        if validated_data.get("is_primary"):
            # The database allows a single primary per product; demote the incumbent
            # instead of failing the upload with a constraint error.
            product.images.filter(is_primary=True).update(is_primary=False)
        elif not product.images.exists():
            validated_data["is_primary"] = True
        return super().create(validated_data)


class StatsSerializer(serializers.Serializer):
    """Dashboard counters for the admin home screen."""

    product_count = serializers.IntegerField()
    available_product_count = serializers.IntegerField()
    category_count = serializers.IntegerField()
    missing_translation_count = serializers.IntegerField(
        help_text="Products lacking at least one of the three languages."
    )
    scans_last_7_days = serializers.IntegerField()
