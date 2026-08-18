"""Menu admin.

The staff who use this screen care about two things the default admin hides: what an
item is called in Uzbek, and which items are still missing a Russian or English name.
Both are first-class columns here, and translations are edited inline so a product is
never saved in a half-translated state by accident.
"""

from django.contrib import admin
from django.db.models import Count, QuerySet
from django.http import HttpRequest
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from apps.common.enums import Language
from apps.menu.models import (
    Category,
    CategoryTranslation,
    Product,
    ProductImage,
    ProductTranslation,
)

THIN_SPACE = "\u2009"


def _uz_name(obj: Category | Product) -> str:
    name, _ = obj.name_for(Language.UZ)
    return name or "—"


class CategoryTranslationInline(admin.TabularInline):
    model = CategoryTranslation
    extra = 1
    max_num = len(Language.choices)
    fields = ["language", "name"]


class ProductTranslationInline(admin.TabularInline):
    model = ProductTranslation
    extra = 1
    max_num = len(Language.choices)
    fields = ["language", "name", "description"]


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ["preview", "image", "alt", "order", "is_primary"]
    readonly_fields = ["preview"]

    @admin.display(description="Preview")
    def preview(self, obj: ProductImage) -> str:
        if not obj.pk or not obj.image:
            return "—"
        return format_html(
            '<img src="{}" style="height:64px;border-radius:4px" alt="" />',
            obj.srcset[400],
        )


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["slug", "name_uz", "parent", "order", "is_active", "product_count"]
    list_filter = ["is_active", "parent"]
    list_editable = ["order", "is_active"]
    search_fields = ["slug", "translations__name"]
    inlines = [CategoryTranslationInline]
    ordering = ["order", "id"]

    def get_queryset(self, request: HttpRequest) -> QuerySet[Category]:
        return (
            super()
            .get_queryset(request)
            .select_related("parent")
            .prefetch_related("translations")
            .annotate(_product_count=Count("products", distinct=True))
        )

    @admin.display(description="Name (uz)")
    def name_uz(self, obj: Category) -> str:
        return _uz_name(obj)

    @admin.display(description="Products", ordering="_product_count")
    def product_count(self, obj: Category) -> int:
        return obj._product_count


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        "slug",
        "name_uz",
        "price_uzs",
        "category",
        "is_available",
        "order",
        "missing_translations",
    ]
    list_filter = ["is_available", "category"]
    list_editable = ["is_available", "order"]
    list_select_related = ["category"]
    search_fields = ["slug", "translations__name", "translations__description"]
    autocomplete_fields = ["category"]
    inlines = [ProductTranslationInline, ProductImageInline]
    ordering = ["order", "id"]
    list_per_page = 50

    def get_queryset(self, request: HttpRequest) -> QuerySet[Product]:
        return (
            super()
            .get_queryset(request)
            .select_related("category")
            .prefetch_related("translations")
            # Deduplicate rows produced by searching across the translations join.
            .distinct()
        )

    @admin.display(description="Name (uz)")
    def name_uz(self, obj: Product) -> str:
        return _uz_name(obj)

    @admin.display(description="Price (UZS)", ordering="price")
    def price_uzs(self, obj: Product) -> str:
        # Grouped with a thin space, the way prices are printed on the menu.
        return f"{obj.price:,}".replace(",", THIN_SPACE)

    @admin.display(description="Missing translations")
    def missing_translations(self, obj: Product) -> str:
        missing = obj.missing_languages
        if not missing:
            # Static markup with no interpolated data, so `mark_safe` is safe here.
            return mark_safe('<span style="color:#1a7f37">complete</span>')
        return format_html('<span style="color:#b35900">{}</span>', ", ".join(missing))


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    """Rarely used directly — images are managed inline — but useful for bulk cleanup."""

    list_display = ["__str__", "product", "order", "is_primary", "width", "height"]
    list_filter = ["is_primary"]
    search_fields = ["product__slug", "alt"]
    autocomplete_fields = ["product"]
    readonly_fields = ["width", "height"]
