"""Tests for the legacy Firestore migration.

The fixture reproduces the first page of the real collection — document ids, names,
prices and category strings are copied verbatim from a snapshot of the live endpoint,
including the rows that made the quarantine rules necessary: two "5 so'm" desserts,
bread filed under beverages, and Russian/English fields pre-filled with a copy of the
Uzbek text. Only the images are substituted, because a faithful copy would put 2 MB of
base64 in this file to prove something a 4x4 JPEG proves just as well.

Nothing here touches the network: the API is exercised through a stub session and the
command is driven with `--source`.
"""

import csv
import json
from base64 import b64encode
from io import BytesIO, StringIO

import pytest
from django.core.management import call_command
from PIL import Image

from apps.common.enums import Language
from apps.menu.legacy import quality
from apps.menu.legacy.categories import UnknownCategory, plan_for
from apps.menu.legacy.firestore import (
    FirestoreCollection,
    FirestoreError,
    decode_document,
    decode_value,
    load_documents,
)
from apps.menu.legacy.identity import legacy_key, legacy_slug
from apps.menu.legacy.images import LegacyImageError, decode_data_url, decode_image
from apps.menu.models import Category, Product, ProductImage, ProductTranslation

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")

# (id, category, subcategory, price, names, descriptions) — real values, real ids.
# fmt: off
SNAPSHOT = [
    ("0PVjqxg3N5ffO8dd1M45", "salads", None, 30000,
     {"uz": "Boss salat", "ru": "Boss salat", "en": "Boss salat"}, None),
    ("0S4b81lUNfm6bLi1E6DN", "national", "quyuq", 60000,
     {"uz": "Go'sht say", "ru": "Go'sht say", "en": "Go'sht say"}, None),
    ("0jHZ0mkLgW19txs101kl", "beverages", "beer", 16000,
     {"uz": "Sarbast", "ru": "Sarbast", "en": "Sarbast"}, None),
    ("3FeP2KsitKp5uaXG2MLb", "beverages", None, 6000,
     {"uz": "Choʻrak", "ru": "Choʻrak", "en": "Choʻrak"}, None),
    ("3ayb2tSgovlgtXLcLWgX", "beverages", "soft", 8000,
     {"uz": "Fuse tea 05", "ru": "Fuse tea", "en": "Fuse tea"}, None),
    ("50FUSPkLWyuqA6ISfFqk", "desserts", None, 20000,
     {"uz": "Non asarti", "ru": "Non asarti", "en": "Non asarti"}, None),
    ("5aHzCwC5O9rXUJtyRwBU", "desserts", None, 5,
     {"uz": "O'rim sirniy palichka", "ru": "O'rim sirniy palichka",
      "en": "O'rim sirniy palichka"}, None),
    ("5k1kJSVVhtsAnEognEDf", "salads", None, 30000,
     {"uz": "Yaponskiy", "ru": "Yaponskiy", "en": "Yaponskiy"}, None),
    ("5zToAJNJXXMjSxGhrBuE", "desserts", None, 5,
     {"uz": "Sirniy palichka", "ru": "Sirniy palichka", "en": "Sirniy palichka"}, None),
    ("6nkpuqrUJsWp4S8szfp6", "beverages", "soft", 10,
     {"uz": "Pepsi balnishnik", "ru": "Pepsi balnishnik", "en": "Pepsi balnishnik"}, None),
    ("7BmkIcXRn0RiA5JINcjg", "salads", None, 10000,
     {"uz": "Sveji salat", "ru": "Свежи салат", "en": "Fresh salat"},
     {"uz": "Eng zoʻr tam", "ru": "Лучший там", "en": "The best taste"}),
    ("7ahniqp3deAwQ0HZoapC", "beverages", None, 4000,
     {"uz": "Buhanka", "ru": "Buhanka", "en": "Buhanka"}, None),
]
# fmt: on

# Rows the snapshot cannot supply: the collection has no empty-name or corrupt-image
# document today, but the command promises to survive both.
BROKEN_IMAGE_ID = "ZZbrokenImage00000001"
NO_NAME_ID = "ZZmissingName0000002"
UNKNOWN_CATEGORY_ID = "ZZunknownCategory003"

EXPECTED_IMPORTED = 9
EXPECTED_QUARANTINED = 6
EXPECTED_NEEDS_REVIEW = 3


def sample_image(width: int = 64, height: int = 48) -> bytes:
    image = Image.new("RGB", (width, height), (200, 160, 60))
    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    return buffer.getvalue()


def data_url(raw: bytes) -> str:
    return "data:image/jpeg;base64," + b64encode(raw).decode("ascii")


def _map(values: dict[str, str] | None) -> dict:
    values = values or {"uz": "", "ru": "", "en": ""}
    return {"mapValue": {"fields": {k: {"stringValue": v} for k, v in values.items()}}}


def document(
    legacy_id: str,
    category: str | None,
    subcategory: str | None,
    price: int | None,
    names: dict[str, str] | None,
    descriptions: dict[str, str] | None = None,
    image: str | None = None,
) -> dict:
    """Build one document in Firestore's typed-value JSON encoding."""
    fields: dict = {
        "name": _map(names),
        "info": _map(descriptions),
        "image": {"stringValue": data_url(sample_image()) if image is None else image},
        "createdAt": {"timestampValue": "2026-07-23T13:15:40.473Z"},
    }
    if category is not None:
        fields["category"] = {"stringValue": category}
    if subcategory is not None:
        fields["subcategory"] = {"stringValue": subcategory}
    if price is not None:
        fields["price"] = {"integerValue": str(price)}
    return {
        "name": f"projects/orginal-boss-kafe/databases/(default)/documents/menu_items/{legacy_id}",
        "fields": fields,
    }


@pytest.fixture
def snapshot() -> list[dict]:
    """The real first page plus the three failure modes it does not contain."""
    documents = [document(*row) for row in SNAPSHOT]
    documents.append(
        document(BROKEN_IMAGE_ID, "salads", None, 12000, {"uz": "Buzuq rasm"}, image="not-an-image")
    )
    documents.append(document(NO_NAME_ID, "salads", None, 12000, {"uz": "  ", "ru": "Салат"}))
    documents.append(document(UNKNOWN_CATEGORY_ID, "pizza", None, 12000, {"uz": "Pitsa"}))
    return documents


@pytest.fixture
def source(tmp_path, snapshot) -> str:
    path = tmp_path / "menu_items.json"
    path.write_text(json.dumps({"documents": snapshot}), encoding="utf-8")
    return str(path)


@pytest.fixture
def report_path(tmp_path) -> str:
    return str(tmp_path / "import_report.csv")


def run_import(source: str, report_path: str, **options) -> str:
    """Run the command with its output captured, and hand the output back."""
    out = StringIO()
    call_command("import_firestore", source=source, report=report_path, stdout=out, **options)
    return out.getvalue()


def read_report(report_path: str) -> list[dict[str, str]]:
    with open(report_path, encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


# --------------------------------------------------------------------------- decoding


def test_decode_value_handles_every_type_the_export_uses():
    assert decode_value({"stringValue": "Somsa"}) == "Somsa"
    assert decode_value({"integerValue": "30000"}) == 30000
    assert decode_value({"nullValue": None}) is None
    assert decode_value({"mapValue": {"fields": {"uz": {"stringValue": "Choy"}}}}) == {"uz": "Choy"}


def test_decode_value_rejects_an_unknown_type():
    with pytest.raises(FirestoreError, match="Unsupported"):
        decode_value({"geoPointValue": {"latitude": 41.3, "longitude": 69.2}})


def test_decode_document_takes_the_id_from_the_resource_path(snapshot):
    decoded = decode_document(snapshot[0])
    assert decoded.id == "0PVjqxg3N5ffO8dd1M45"
    assert decoded.integer("price") == 30000
    assert decoded.text_map("name")["uz"] == "Boss salat"


def test_load_documents_accepts_a_saved_response(source):
    assert len(load_documents(source)) == len(SNAPSHOT) + 3


class StubSession:
    """A `requests.Session` stand-in that serves a fixed list of pages."""

    def __init__(self, pages: list[dict]) -> None:
        self.pages = pages
        self.calls: list[dict] = []

    def get(self, url, params, timeout):
        self.calls.append(params)
        index = int(params.get("pageToken", "0"))
        return _StubResponse(self.pages[index])


class _StubResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


def test_collection_follows_every_page(snapshot):
    session = StubSession(
        [
            {"documents": snapshot[:5], "nextPageToken": "1"},
            {"documents": snapshot[5:10], "nextPageToken": "2"},
            {"documents": snapshot[10:]},
        ]
    )
    collection = FirestoreCollection("p", "menu_items", page_size=5, session=session)

    documents = list(collection)

    assert len(documents) == len(snapshot)
    assert [call.get("pageToken") for call in session.calls] == [None, "1", "2"]


def test_collection_stops_when_a_page_token_repeats(snapshot):
    session = StubSession([{"documents": snapshot[:1], "nextPageToken": "0"}])
    collection = FirestoreCollection("p", "menu_items", session=session)

    with pytest.raises(FirestoreError, match="Pagination stalled"):
        list(collection)


# --------------------------------------------------------------------------- identity


def test_legacy_slug_is_stable_and_readable():
    assert legacy_slug("0PVjqxg3N5ffO8dd1M45", "Boss salat").startswith("boss-salat-")


def test_legacy_slug_survives_a_rename():
    key = legacy_key("0PVjqxg3N5ffO8dd1M45")
    assert legacy_slug("0PVjqxg3N5ffO8dd1M45", "Boss salat").endswith(key)
    assert legacy_slug("0PVjqxg3N5ffO8dd1M45", "Boss salad 2.0").endswith(key)


def test_legacy_slug_falls_back_to_the_key_alone():
    # A Cyrillic-only name slugifies to nothing; the slug must still be valid.
    assert legacy_slug("abc", "Салат") == legacy_key("abc")


def test_legacy_keys_differ_per_document():
    assert legacy_key("0PVjqxg3N5ffO8dd1M45") != legacy_key("0PVjqxg3N5ffO8dd1M46")


# ---------------------------------------------------------------------------- quality


@pytest.mark.parametrize("text", ["Jhvz", "!jgcjf!x", "Kbvs gjv", "!!!"])
def test_keyboard_mash_is_detected(text):
    assert quality.looks_like_noise(text)


@pytest.mark.parametrize(
    "text",
    ["Boss salat", "Choʻrak", "O'rdak shashlik", "Свежи салат", "Fresh salat", "Cola 0.5"],
)
def test_real_names_are_not_flagged_as_noise(text):
    assert not quality.looks_like_noise(text)


def test_translations_copied_from_uzbek_are_treated_as_absent():
    drafts, issues = quality.build_translations(
        {"uz": "Boss salat", "ru": "Boss salat", "en": "Boss salat"}, {}
    )
    assert [draft.language for draft in drafts] == [Language.UZ]
    assert issues == []


def test_apostrophe_spelling_does_not_count_as_a_translation():
    drafts, _ = quality.build_translations({"uz": "Choʻrak", "ru": "Cho'rak"}, {})
    assert [draft.language for draft in drafts] == [Language.UZ]


def test_genuine_translations_are_kept_with_their_descriptions():
    drafts, issues = quality.build_translations(
        {"uz": "Sveji salat", "ru": "Свежи салат", "en": "Fresh salat"},
        {"uz": "Eng zoʻr tam", "ru": "Лучший там", "en": "The best taste"},
    )
    assert {draft.language for draft in drafts} == {Language.UZ, Language.RU, Language.EN}
    assert next(d for d in drafts if d.language == Language.RU).description == "Лучший там"
    assert issues == []


def test_a_translated_description_keeps_a_language_whose_name_was_copied():
    drafts, _ = quality.build_translations(
        {"uz": "Somsa", "ru": "Somsa"}, {"uz": "Tandirda", "ru": "В тандыре"}
    )
    russian = next(draft for draft in drafts if draft.language == Language.RU)
    assert (russian.name, russian.description) == ("Somsa", "В тандыре")


def test_mashed_translations_are_dropped_and_flagged():
    drafts, issues = quality.build_translations({"uz": "Uyg'ur kabob", "ru": "Jhvz"}, {})
    assert [draft.language for draft in drafts] == [Language.UZ]
    assert [issue.reason for issue in issues] == [quality.Reason.SUSPICIOUS_TEXT]


def test_bread_in_beverages_is_flagged_for_review():
    issues = quality.category_issues("Choʻrak", "beverages", None)
    assert [issue.status for issue in issues] == [quality.Status.NEEDS_REVIEW]
    assert issues[0].reason is quality.Reason.CATEGORY_MISMATCH


def test_lager_outside_the_beer_subcategory_is_flagged():
    assert quality.category_issues("Platina latina piva", "beverages", "soft")
    assert not quality.category_issues("Sarbast", "beverages", "beer")


def test_a_correctly_filed_dish_raises_nothing():
    assert quality.category_issues("Boss salat", "salads", None) == []
    assert quality.category_issues("Limon chay", "beverages", "soft") == []


@pytest.mark.parametrize("price", [5, 10, 99])
def test_near_zero_prices_are_quarantined(price):
    issues = quality.price_issues(price)
    assert [issue.status for issue in issues] == [quality.Status.QUARANTINED]
    assert issues[0].reason is quality.Reason.PRICE_TOO_LOW


def test_a_valid_price_raises_nothing():
    assert quality.price_issues(30000) == []


def test_a_missing_price_is_quarantined():
    assert quality.price_issues(None)[0].reason is quality.Reason.PRICE_MISSING


# ----------------------------------------------------------------------- categories


def test_the_legacy_pair_maps_onto_two_levels():
    plan = plan_for("national", "quyuq")
    assert (plan.root.slug, plan.target.slug) == ("national", "main-courses")


def test_a_row_without_a_subcategory_lands_on_the_section():
    plan = plan_for("salads", None)
    assert plan.child is None and plan.target.slug == "salads"


def test_an_unmapped_subcategory_falls_back_to_the_section():
    plan = plan_for("beverages", "smoothie")
    assert plan.target.slug == "beverages"
    assert plan.unknown_subcategory == "smoothie"


def test_an_unmapped_category_is_fatal():
    with pytest.raises(UnknownCategory):
        plan_for("pizza", None)


# --------------------------------------------------------------------------- images


def test_a_data_url_round_trips():
    raw = sample_image()
    assert decode_data_url(data_url(raw)) == raw


@pytest.mark.parametrize(
    "value", [None, "", "https://example.test/a.jpg", "data:image/jpeg;base64,%%"]
)
def test_unusable_image_fields_are_rejected(value):
    with pytest.raises(LegacyImageError):
        decode_data_url(value)


def test_a_data_url_holding_something_other_than_an_image_is_rejected():
    with pytest.raises(LegacyImageError):
        decode_image(data_url(b"#!/bin/sh\nrm -rf /"))


def test_decode_image_reports_the_pixel_size():
    _, size = decode_image(data_url(sample_image(64, 48)))
    assert size == (64, 48)


# -------------------------------------------------------------------- command: read


@pytest.mark.django_db
def test_dry_run_writes_nothing_but_still_reports(source, report_path, local_storage):
    run_import(source, report_path, dry_run=True)

    assert Product.objects.count() == 0
    assert Category.objects.count() == 0
    assert len(read_report(report_path)) > 0


@pytest.mark.django_db
def test_limit_stops_after_n_documents(source, report_path, local_storage):
    run_import(source, report_path, limit=3)

    assert Product.objects.count() == 3


# ------------------------------------------------------------------- command: write


@pytest.mark.django_db
def test_import_creates_the_expected_products(source, report_path, local_storage):
    run_import(source, report_path)

    assert Product.objects.count() == EXPECTED_IMPORTED
    assert Product.objects.filter(slug__startswith="boss-salat-").exists()


@pytest.mark.django_db
def test_quarantined_rows_never_reach_the_database(source, report_path, local_storage):
    run_import(source, report_path)

    slugs = set(Product.objects.values_list("slug", flat=True))
    for legacy_id in (BROKEN_IMAGE_ID, NO_NAME_ID, UNKNOWN_CATEGORY_ID):
        assert not any(slug.endswith(legacy_key(legacy_id)) for slug in slugs)
    assert not Product.objects.filter(price__lt=100).exists()


@pytest.mark.django_db
def test_the_category_tree_is_two_levels_and_lazily_created(source, report_path, local_storage):
    run_import(source, report_path)

    assert set(Category.objects.filter(parent__isnull=True).values_list("slug", flat=True)) == {
        "national",
        "salads",
        "beverages",
        "desserts",
    }
    assert set(Category.objects.filter(parent__isnull=False).values_list("slug", flat=True)) == {
        "main-courses",
        "beer",
        "soft-drinks",
    }
    assert Category.objects.get(slug="soft-drinks").parent.slug == "beverages"
    # `grill` and `appetizers` are mapped but unused by this page: no empty sections.
    assert not Category.objects.filter(slug__in=["grill", "appetizers"]).exists()


@pytest.mark.django_db
def test_category_translations_cover_all_three_languages(source, report_path, local_storage):
    run_import(source, report_path)

    salads = Category.objects.get(slug="salads")
    assert {t.language: t.name for t in salads.translations.all()} == {
        "uz": "Salatlar",
        "ru": "Салаты",
        "en": "Salads",
    }


@pytest.mark.django_db
def test_only_genuine_translations_are_stored(source, report_path, local_storage):
    run_import(source, report_path)

    copied = Product.objects.get(slug__startswith="boss-salat-")
    assert [t.language for t in copied.translations.all()] == [Language.UZ]

    translated = Product.objects.get(slug__startswith="sveji-salat-")
    assert {t.language for t in translated.translations.all()} == {"uz", "ru", "en"}
    assert translated.translations.get(language="ru").name == "Свежи салат"
    assert translated.translations.get(language="en").description == "The best taste"


@pytest.mark.django_db
def test_a_partly_translated_row_keeps_only_the_language_it_has(source, report_path, local_storage):
    run_import(source, report_path)

    # "Fuse tea 05" (uz) is shortened to "Fuse tea" in both other languages.
    product = Product.objects.get(slug__startswith="fuse-tea-05-")
    assert {t.language for t in product.translations.all()} == {"uz", "ru", "en"}
    assert product.name_for("ru") == ("Fuse tea", False)


@pytest.mark.django_db
def test_misfiled_rows_are_imported_but_hidden(source, report_path, local_storage):
    run_import(source, report_path)

    hidden = set(Product.objects.filter(is_available=False).values_list("slug", flat=True))
    assert {slug.rsplit("-", 1)[0] for slug in hidden} == {"chorak", "buhanka", "non-asarti"}


@pytest.mark.django_db
def test_the_primary_image_is_stored_with_its_webp_derivatives(source, report_path, local_storage):
    run_import(source, report_path)

    image = ProductImage.objects.get(product__slug__startswith="boss-salat-")
    assert image.is_primary
    assert (image.width, image.height) == (64, 48)
    storage = image.image.storage
    assert storage.exists(image.image.name)
    for key in image.derivative_keys.values():
        assert key.endswith(".webp")
        assert storage.exists(key)


@pytest.mark.django_db
def test_every_imported_product_has_exactly_one_primary_image(source, report_path, local_storage):
    run_import(source, report_path)

    assert ProductImage.objects.filter(is_primary=True).count() == EXPECTED_IMPORTED


# --------------------------------------------------------------- command: idempotency


@pytest.mark.django_db
def test_running_twice_changes_nothing(source, report_path, local_storage):
    run_import(source, report_path)
    before = sorted(Product.objects.values_list("slug", "price", "category__slug"))
    image_count = ProductImage.objects.count()

    run_import(source, report_path)

    assert Product.objects.count() == EXPECTED_IMPORTED
    assert sorted(Product.objects.values_list("slug", "price", "category__slug")) == before
    assert ProductImage.objects.count() == image_count
    assert ProductTranslation.objects.filter(product__slug__startswith="boss-salat-").count() == 1


@pytest.mark.django_db
def test_a_second_run_updates_a_changed_price_without_moving_the_slug(
    tmp_path, snapshot, report_path, local_storage
):
    first = tmp_path / "first.json"
    first.write_text(json.dumps({"documents": snapshot}), encoding="utf-8")
    run_import(str(first), report_path)
    original_slug = Product.objects.get(slug__startswith="boss-salat-").slug

    repriced = document("0PVjqxg3N5ffO8dd1M45", "salads", None, 45000, {"uz": "Boss salati"})
    second = tmp_path / "second.json"
    second.write_text(json.dumps({"documents": [repriced]}), encoding="utf-8")
    run_import(str(second), report_path)

    product = Product.objects.get(slug=original_slug)
    assert product.price == 45000
    assert Product.objects.count() == EXPECTED_IMPORTED


@pytest.mark.django_db
def test_a_language_dropped_upstream_loses_its_translation_row(
    tmp_path, report_path, local_storage
):
    trilingual = document(
        "7BmkIcXRn0RiA5JINcjg",
        "salads",
        None,
        10000,
        {"uz": "Sveji salat", "ru": "Свежи салат", "en": "Fresh salat"},
    )
    path = tmp_path / "one.json"
    path.write_text(json.dumps({"documents": [trilingual]}), encoding="utf-8")
    run_import(str(path), report_path)
    assert ProductTranslation.objects.count() == 3

    uz_only = document("7BmkIcXRn0RiA5JINcjg", "salads", None, 10000, {"uz": "Sveji salat"})
    path.write_text(json.dumps({"documents": [uz_only]}), encoding="utf-8")
    run_import(str(path), report_path)

    assert [t.language for t in ProductTranslation.objects.all()] == [Language.UZ]


# -------------------------------------------------------------------- command: report


@pytest.mark.django_db
def test_the_report_lists_every_rejected_and_flagged_row(source, report_path, local_storage):
    run_import(source, report_path)
    rows = read_report(report_path)

    quarantined = [row for row in rows if row["status"] == "QUARANTINED"]
    flagged = [row for row in rows if row["status"] == "NEEDS_REVIEW"]

    assert len(quarantined) == EXPECTED_QUARANTINED
    assert len(flagged) == EXPECTED_NEEDS_REVIEW
    assert {row["reason"] for row in quarantined} == {
        "price_too_low",
        "invalid_image",
        "missing_uz_name",
        "unknown_category",
    }
    assert {row["reason"] for row in flagged} == {"category_mismatch"}


@pytest.mark.django_db
def test_the_report_carries_the_values_the_row_was_judged_on(source, report_path, local_storage):
    run_import(source, report_path)

    rows = {row["name_uz"]: row for row in read_report(report_path)}
    cheap = rows["Sirniy palichka"]
    assert (cheap["status"], cheap["reason"], cheap["price"]) == (
        "QUARANTINED",
        "price_too_low",
        "5",
    )
    assert cheap["category"] == "desserts"
    assert "100" in cheap["detail"]


@pytest.mark.django_db
def test_quarantined_rows_are_listed_first(source, report_path, local_storage):
    """The rows somebody has to re-enter by hand are at the top of the spreadsheet."""
    run_import(source, report_path)

    statuses = [row["status"] for row in read_report(report_path)]
    assert (
        statuses
        == ["QUARANTINED"] * EXPECTED_QUARANTINED + ["NEEDS_REVIEW"] * EXPECTED_NEEDS_REVIEW
    )
