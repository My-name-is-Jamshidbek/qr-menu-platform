"""Generate a complete, realistic menu with no external dependency.

`import_firestore` needs the third-party Firestore project to be reachable and is a
one-way migration of somebody else's data. This command gives a fresh clone the same
*shape* of catalogue — the identical category tree, trilingual coverage that is
deliberately incomplete, sold-out items, and real WebP images in the bucket — from
data that lives in this repository.

    python manage.py seed_demo             # idempotent: safe to re-run
    python manage.py seed_demo --flush     # rebuild the menu from scratch
    python manage.py seed_demo --no-images # skip image generation and upload

The Russian and English names are missing on roughly half the dishes on purpose: the
fallback rule and the admin's "missing translations" counter are only exercised when
the data is uneven, and the production data is very uneven indeed.
"""

import colorsys
import hashlib
from argparse import ArgumentParser
from dataclasses import dataclass
from io import BytesIO
from typing import Any

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from PIL import Image, ImageDraw, ImageFont

from apps.common.enums import Language
from apps.menu.legacy.categories import CategoryWriter, plan_for
from apps.menu.models import (
    Category,
    Product,
    ProductImage,
    ProductTranslation,
)

# Brand tokens from docs/DESIGN_SYSTEM.md, so seeded placeholders sit inside the
# palette instead of shouting at it.
GROUND_SURFACE = (0x17, 0x15, 0x0F)
GROUND_ELEVATED = (0x21, 0x1D, 0x14)
GOLD_300 = (0xE0, 0xC3, 0x6C)

IMAGE_SIZE = (1600, 1200)


@dataclass(frozen=True, slots=True)
class Dish:
    """One seeded product. Only `uz` is required, exactly as in the real data."""

    slug: str
    category: str
    subcategory: str | None
    price: int
    uz: str
    ru: str = ""
    en: str = ""
    description_uz: str = ""
    is_available: bool = True


# fmt: off  (the dish table reads as a table; one argument per line would bury it)
DISHES: tuple[Dish, ...] = (
    # --- national / main courses
    Dish(
        "qazon-kabob",
        "national",
        "quyuq",
        200_000,
        "Qazon kabob",
        "Казан-кабоб",
        "Qazan Kebab",
        "Qozonda dimlangan qo'zichoq go'shti va kartoshka.",
    ),
    Dish(
        "mangal-kabob",
        "national",
        "quyuq",
        230_000,
        "Mangal kabob",
        "Мангал-кабоб",
        "Grilled Kebab",
    ),
    Dish("qaymoqli-kabob", "national", "quyuq", 230_000, "Qaymoqli kabob"),
    Dish("uygur-kabob", "national", "quyuq", 230_000, "Uyg'ur kabob"),
    Dish(
        "turk-kofte",
        "national",
        "quyuq",
        180_000,
        "Turk kofte",
        "Турецкие котлеты",
        "Turkish Köfte",
    ),
    Dish(
        "ribeye-steak",
        "national",
        "quyuq",
        250_000,
        "Ribay steyk",
        "Стейк рибай",
        "Ribeye Steak",
        "Bir kecha marinadlangan mramorli mol go'shti.",
    ),
    Dish(
        "saryogda-til",
        "national",
        "quyuq",
        200_000,
        "Saryog'da til",
        "Язык в сливочном масле",
        "Beef Tongue in Butter",
    ),
    Dish("tovuq-saryog", "national", "quyuq", 165_000, "Saryog'li tovuq"),
    Dish("gosht-say", "national", "quyuq", 60_000, "Go'sht say"),
    Dish(
        "boss-asarti",
        "national",
        "quyuq",
        340_000,
        "Boss asarti",
        "Ассорти «Босс»",
        "Boss Platter",
        "To'rt kishilik aralash kabob laganda.",
    ),
    # --- national / soups
    Dish(
        "mastava",
        "national",
        "suyuq",
        25_000,
        "Mastava",
        "Мастава",
        "Mastava Soup",
        "Guruch, sabzavot va mol go'shtidan tayyorlangan issiq sho'rva.",
    ),
    Dish("osma-shorva", "national", "suyuq", 25_000, "Osma sho'rva", "Суп «Осма»", "Osma Soup"),
    Dish("teftel-shorva", "national", "suyuq", 25_000, "Teftel sho'rva"),
    # --- appetizers
    Dish(
        "somsa",
        "appetizers",
        None,
        10_000,
        "Somsa",
        "Самса",
        "Samsa",
        "Tandirda pishirilgan qo'y go'shtli somsa.",
    ),
    Dish(
        "tovuq-qanot",
        "appetizers",
        None,
        12_000,
        "Tovuq qanot",
        "Куриные крылышки",
        "Chicken Wings",
    ),
    Dish("oq-baliq", "appetizers", None, 55_000, "Oq baliq"),
    Dish("setka-baliq", "appetizers", None, 85_000, "Setka baliq"),
    Dish("rulet-shashlik", "appetizers", None, 25_000, "Rulet shashlik"),
    Dish("ordak-shashlik", "appetizers", None, 30_000, "O'rdak shashlik", is_available=False),
    # --- grill
    Dish(
        "mol-shashlik",
        "grill",
        None,
        32_000,
        "Mol go'sht shashlik",
        "Шашлык из говядины",
        "Beef Skewer",
    ),
    Dish(
        "tovuq-shashlik",
        "grill",
        None,
        26_000,
        "Tovuq shashlik",
        "Шашлык из курицы",
        "Chicken Skewer",
    ),
    Dish("jigar-shashlik", "grill", None, 24_000, "Jigar shashlik"),
    Dish(
        "sabzavot-grill",
        "grill",
        None,
        20_000,
        "Grilda sabzavot",
        "Овощи на гриле",
        "Grilled Vegetables",
        "Mavsumiy sabzavotlar, zaytun moyi va rayhon.",
    ),
    # --- salads
    Dish(
        "achichuk",
        "salads",
        None,
        10_000,
        "Achchiq-chuchuk",
        "Ачик-чучук",
        "Achichuk Salad",
        "Pomidor, piyoz va achchiq qalampir.",
    ),
    Dish("boss-salad", "salads", None, 30_000, "Boss salat", "Салат «Босс»", "Boss Salad"),
    Dish("caesar", "salads", None, 30_000, "Sezar", "Цезарь", "Caesar Salad"),
    Dish("french-salad", "salads", None, 30_000, "Fransuzcha salat"),
    Dish("vitamin-salad", "salads", None, 25_000, "Vitamin salat"),
    Dish("baqlajon-rulet", "salads", None, 30_000, "Baqlajon rulet"),
    Dish("qatiq", "salads", None, 5_000, "Qatiq", "Катык", "Yoghurt"),
    # --- desserts
    Dish("muzqaymoq", "desserts", None, 10_000, "Muzqaymoq", "Мороженое", "Ice Cream"),
    Dish("chak-chak", "desserts", None, 18_000, "Chak-chak"),
    Dish(
        "napoleon", "desserts", None, 22_000, "Napoleon torti", "Торт «Наполеон»", "Napoleon Cake"
    ),
    Dish(
        "meva-asarti",
        "desserts",
        None,
        80_000,
        "Meva asarti",
        "Фруктовое ассорти",
        "Fruit Platter",
        "Mavsumiy mevalar katta laganda.",
    ),
    # --- beverages / soft
    Dish("kok-choy", "beverages", "soft", 12_000, "Ko'k choy", "Зелёный чай", "Green Tea"),
    Dish("limon-choy", "beverages", "soft", 20_000, "Limonli choy", "Чай с лимоном", "Lemon Tea"),
    Dish("mevali-choy", "beverages", "soft", 25_000, "Mevali choy"),
    Dish("ayron", "beverages", "soft", 8_000, "Ayron", "Айран", "Ayran"),
    Dish("mokhito-kivi", "beverages", "soft", 35_000, "Kivili moxito"),
    Dish("cola-05", "beverages", "soft", 8_000, "Cola 0.5"),
    # --- beverages / beer
    Dish("sarbast", "beverages", "beer", 16_000, "Sarbast", "Сарбаст", "Sarbast Lager"),
    Dish("tuborg", "beverages", "beer", 17_000, "Tuborg", "Туборг", "Tuborg"),
)
# fmt: on


class Command(BaseCommand):
    help = "Seed a realistic demo menu that needs no third-party data source."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete every existing product and category first.",
        )
        parser.add_argument(
            "--no-images",
            action="store_true",
            help="Skip placeholder generation and upload (much faster, no bucket needed).",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        if options["flush"]:
            self._flush()

        created, updated = self._seed(with_images=not options["no_images"])

        self.stdout.write("")
        self.stdout.write(f"categories   {Category.objects.count():>4}")
        self.stdout.write(f"products     {Product.objects.count():>4}")
        self.stdout.write(f"created      {created:>4}")
        self.stdout.write(f"updated      {updated:>4}")
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(DISHES)} dishes across {Category.objects.count()} categories."
            )
        )

    @transaction.atomic
    def _flush(self) -> None:
        """Drop the menu. Images are removed from the bucket by the post-delete signal."""
        Product.objects.all().delete()
        # Children first: `parent` is PROTECT. Translations cascade.
        Category.objects.filter(parent__isnull=False).delete()
        Category.objects.all().delete()
        self.stdout.write(self.style.WARNING("Flushed the existing menu."))

    def _seed(self, *, with_images: bool) -> tuple[int, int]:
        categories = CategoryWriter()
        order: dict[int, int] = {}
        created_count = 0
        updated_count = 0

        for dish in DISHES:
            category = categories.ensure(plan_for(dish.category, dish.subcategory))
            order[category.pk] = order.get(category.pk, 0) + 1
            if self._save(dish, category, order[category.pk], with_images=with_images):
                created_count += 1
            else:
                updated_count += 1

        return created_count, updated_count

    @transaction.atomic
    def _save(self, dish: Dish, category: Category, order: int, *, with_images: bool) -> bool:
        product, created = Product.objects.update_or_create(
            slug=dish.slug,
            defaults={
                "category": category,
                "price": dish.price,
                "is_available": dish.is_available,
                "order": order,
            },
        )

        for language, name in self._names(dish).items():
            ProductTranslation.objects.update_or_create(
                product=product,
                language=language,
                defaults={
                    "name": name,
                    "description": dish.description_uz if language == Language.UZ else "",
                },
            )

        if created and with_images:
            ProductImage(
                product=product,
                image=ContentFile(placeholder_image(dish.slug, dish.uz), name=f"{dish.slug}.webp"),
                alt="",
                is_primary=True,
                order=0,
            ).save()

        self.stdout.write(f"  {'+' if created else '~'} {dish.slug}")
        return created

    @staticmethod
    def _names(dish: Dish) -> dict[str, str]:
        """Only the languages this dish actually has, Uzbek always included."""
        names = {Language.UZ.value: dish.uz}
        if dish.ru:
            names[Language.RU.value] = dish.ru
        if dish.en:
            names[Language.EN.value] = dish.en
        return names


def placeholder_image(seed: str, label: str) -> bytes:
    """Render a deterministic branded placeholder photo as WebP bytes.

    A per-dish hue keeps the seeded menu from looking like one repeated tile, while
    staying inside the dark warm ground the design system specifies. The gradient is
    drawn tiny and upscaled: a per-pixel loop at 1600x1200 would dominate the runtime
    of the whole command.
    """
    digest = hashlib.blake2s(seed.encode("utf-8"), digest_size=4).digest()
    hue = digest[0] / 255
    accent = tuple(round(channel * 255) for channel in colorsys.hsv_to_rgb(hue, 0.45, 0.42))

    small = Image.new("RGB", (16, 12))
    pixels = small.load()
    for y in range(small.height):
        for x in range(small.width):
            t = (x / (small.width - 1) + y / (small.height - 1)) / 2
            pixels[x, y] = tuple(
                round(GROUND_SURFACE[i] + (accent[i] + GROUND_ELEVATED[i] - GROUND_SURFACE[i]) * t)
                for i in range(3)
            )

    image = small.resize(IMAGE_SIZE, Image.Resampling.BICUBIC)
    draw = ImageDraw.Draw(image)
    draw.text(
        (IMAGE_SIZE[0] / 2, IMAGE_SIZE[1] / 2),
        _monogram(label),
        font=ImageFont.load_default(size=320),
        fill=GOLD_300,
        anchor="mm",
    )

    buffer = BytesIO()
    image.save(buffer, format="WEBP", quality=82, method=4)
    return buffer.getvalue()


def _monogram(label: str) -> str:
    """Up to two initials, e.g. "Qazon kabob" -> "QK"."""
    initials = [word[0].upper() for word in label.split() if word[:1].isalpha()]
    return "".join(initials[:2]) or "?"
