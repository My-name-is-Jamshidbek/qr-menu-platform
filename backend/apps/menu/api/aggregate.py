"""Builds the whole-menu payload from a fixed number of queries.

The dataset is small (~86 products) and the storefront page is statically generated, so
one round trip beats a request per section. The cost of that is that the query plan must
not grow with the data: everything is fetched in five statements — categories, their
names, products, their names, their photos — and the tree is assembled in Python.
"""

from datetime import UTC, datetime
from typing import Any

from apps.menu.models import Category, Product
from apps.menu.serializers import MenuCategorySerializer


def _fetch_categories() -> list[Category]:
    return list(Category.objects.filter(is_active=True).prefetch_related("translations"))


def _fetch_products() -> list[Product]:
    return list(
        Product.objects.filter(is_available=True, category__is_active=True)
        .select_related("category")
        .prefetch_related("translations", "images")
    )


def build_menu(language: str) -> dict[str, Any]:
    """The `GET /menu/` payload as plain JSON-serialisable data."""
    categories = _fetch_categories()
    by_id = {category.pk: category for category in categories}

    roots = [category for category in categories if category.parent_id is None]
    children: dict[int, list[Category]] = {root.pk: [] for root in roots}
    for category in categories:
        if category.parent_id is not None and category.parent_id in children:
            children[category.parent_id].append(category)

    grouped: dict[int, list[Product]] = {root.pk: [] for root in roots}
    for product in _fetch_products():
        category = by_id.get(product.category_id)
        if category is None:
            continue
        # A product hangs off a section directly or off one of its subsections; either
        # way the storefront shows it under the section, tagged with its own slug.
        root_id = category.pk if category.parent_id is None else category.parent_id
        if root_id in grouped:
            grouped[root_id].append(product)

    context = {
        "language": language,
        "children_by_section": children,
        "products_by_section": grouped,
    }

    return {
        "categories": MenuCategorySerializer(roots, many=True, context=context).data,
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }
