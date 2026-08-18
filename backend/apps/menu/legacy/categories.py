"""Mapping from the legacy flat `category` + `subcategory` pair to the new tree.

The old data had two independent string columns with no table behind them, spelled in
a mix of Uzbek and English (`national`/`quyuq`). This module is the single place where
those strings are given meaning, names in all three languages, and a display order.

Category names are authored here rather than derived from the source: the legacy
collection never stored a category label at all, so there is nothing to translate and
nothing is being invented about a *product*.
"""

from dataclasses import dataclass, field

from apps.common.enums import Language
from apps.menu.models import Category, CategoryTranslation


@dataclass(frozen=True, slots=True)
class CategorySpec:
    """One node of the target tree, with its name in every supported language."""

    slug: str
    names: dict[str, str]
    children: dict[str, "CategorySpec"] = field(default_factory=dict)


def _spec(slug: str, uz: str, ru: str, en: str, children: dict | None = None) -> CategorySpec:
    return CategorySpec(
        slug=slug,
        names={Language.UZ: uz, Language.RU: ru, Language.EN: en},
        children=children or {},
    )


# Keyed by the legacy `category` string; inner keys are the legacy `subcategory`.
# `grill` never appears in the current export but was a valid legacy slug, so it is
# mapped rather than left to fail the import if an older backup is replayed.
LEGACY_TREE: dict[str, CategorySpec] = {
    "national": _spec(
        "national",
        "Milliy taomlar",
        "Национальная кухня",
        "National dishes",
        {
            "quyuq": _spec("main-courses", "Quyuq taomlar", "Вторые блюда", "Main courses"),
            "suyuq": _spec("soups", "Suyuq taomlar", "Супы", "Soups"),
        },
    ),
    "grill": _spec("grill", "Grill", "Гриль", "Grill"),
    "appetizers": _spec("appetizers", "Gazaklar", "Закуски", "Appetizers"),
    "salads": _spec("salads", "Salatlar", "Салаты", "Salads"),
    "desserts": _spec("desserts", "Shirinliklar", "Десерты", "Desserts"),
    "beverages": _spec(
        "beverages",
        "Ichimliklar",
        "Напитки",
        "Beverages",
        {
            "soft": _spec(
                "soft-drinks", "Alkogolsiz ichimliklar", "Безалкогольные напитки", "Soft drinks"
            ),
            "beer": _spec("beer", "Pivo", "Пиво", "Beer"),
        },
    ),
}

# Display order of the root sections, savoury first and drinks last, as printed.
ROOT_ORDER: tuple[str, ...] = tuple(LEGACY_TREE)


class UnknownCategory(LookupError):
    """The legacy `category` string has no mapping."""


@dataclass(frozen=True, slots=True)
class CategoryPlan:
    """Where a legacy row lands: a root section and optionally a subsection."""

    root: CategorySpec
    child: CategorySpec | None = None
    child_order: int = 0
    unknown_subcategory: str | None = None

    @property
    def target(self) -> CategorySpec:
        return self.child or self.root

    @property
    def root_order(self) -> int:
        return ROOT_ORDER.index(self.root.slug)


def plan_for(category: str | None, subcategory: str | None) -> CategoryPlan:
    """Resolve a legacy pair to a target node without touching the database.

    An unrecognised subcategory is not fatal — the product lands on the root section
    and the caller flags it for review — but an unrecognised category is, because
    there is no sensible parent to fall back to.
    """
    root = LEGACY_TREE.get((category or "").strip().lower())
    if root is None:
        raise UnknownCategory(category or "")

    key = (subcategory or "").strip().lower()
    if not key:
        return CategoryPlan(root=root)
    if key not in root.children:
        return CategoryPlan(root=root, unknown_subcategory=key)
    return CategoryPlan(
        root=root,
        child=root.children[key],
        child_order=list(root.children).index(key),
    )


class CategoryWriter:
    """Creates the tree nodes an import actually needs, once each.

    Nodes are created lazily so the resulting menu has no empty sections, and the
    instance caches by slug so a run of 86 products issues a handful of queries.
    """

    def __init__(self) -> None:
        self._cache: dict[str, Category] = {}

    def ensure(self, plan: CategoryPlan) -> Category:
        root = self._ensure_spec(plan.root, parent=None, order=plan.root_order)
        if plan.child is None:
            return root
        return self._ensure_spec(plan.child, parent=root, order=plan.child_order)

    def _ensure_spec(self, spec: CategorySpec, parent: Category | None, order: int) -> Category:
        cached = self._cache.get(spec.slug)
        if cached is not None:
            return cached

        category, created = Category.objects.get_or_create(
            slug=spec.slug,
            defaults={"parent": parent, "order": order},
        )
        if created:
            CategoryTranslation.objects.bulk_create(
                CategoryTranslation(category=category, language=language, name=name)
                for language, name in spec.names.items()
            )
        self._cache[spec.slug] = category
        return category
