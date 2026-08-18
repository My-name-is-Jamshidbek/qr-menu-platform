"""Data-quality rules applied to legacy rows before they reach the database.

The legacy collection was edited by hand for two years with no validation, so it
contains prices of "5 so'm", keyboard-mash translations, and bread filed under
beverages. Two outcomes are possible:

* `QUARANTINED` — the row cannot become a valid `Product` and is not imported.
* `NEEDS_REVIEW` — the row imports but is hidden (`is_available=False`) until a
  human confirms it.

Every rule is a pure function over already-decoded values so it can be tested
without Django, and every rejection carries a machine-readable `reason` that ends up
in the CSV report.
"""

import re
import unicodedata
from dataclasses import dataclass
from enum import StrEnum

from apps.common.enums import Language
from apps.menu.models import MIN_PRICE_UZS


class Status(StrEnum):
    QUARANTINED = "QUARANTINED"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class Reason(StrEnum):
    """Why a row was rejected or flagged. Stable strings — they are report columns."""

    MISSING_UZ_NAME = "missing_uz_name"
    PRICE_TOO_LOW = "price_too_low"
    PRICE_MISSING = "price_missing"
    INVALID_IMAGE = "invalid_image"
    UNKNOWN_CATEGORY = "unknown_category"
    UNKNOWN_SUBCATEGORY = "unknown_subcategory"
    CATEGORY_MISMATCH = "category_mismatch"
    SUSPICIOUS_TEXT = "suspicious_text"
    DUPLICATE_DOCUMENT = "duplicate_document"


@dataclass(frozen=True, slots=True)
class Issue:
    status: Status
    reason: Reason
    detail: str = ""


# Uzbek Latin writes o' and g' with the modifier letters ʻ and ʼ, but the legacy
# admin let people type ASCII quotes and backticks. Fold them all together before
# comparing two strings, or "Cho'rak" and "Choʻrak" read as different dishes.
_APOSTROPHES = dict.fromkeys(map(ord, "‘’ʻʼ`´′"), "'")
_WHITESPACE = re.compile(r"\s+")


def normalize(text: str | None) -> str:
    """Trim and collapse whitespace, preserving the author's own spelling."""
    if not text:
        return ""
    return _WHITESPACE.sub(" ", unicodedata.normalize("NFC", text)).strip()


def comparison_key(text: str | None) -> str:
    """Casefolded, apostrophe-folded form used only to compare two strings."""
    return normalize(text).translate(_APOSTROPHES).casefold()


_VOWELS = frozenset("aeiouаеёиоуыэюяў")
_WORD = re.compile(r"[^\W\d_]+", re.UNICODE)


def tokens(text: str | None) -> list[str]:
    """Lowercase word tokens, with o'/g' folded into plain letters.

    The apostrophe is dropped rather than treated as a separator so that "Choʻrak"
    yields `chorak` and not `cho` + `rak`.
    """
    folded = normalize(text).translate(_APOSTROPHES).replace("'", "").casefold()
    return _WORD.findall(folded)


def looks_like_noise(text: str) -> bool:
    """True when a string reads as keyboard mash rather than a dish name.

    The legacy export contains rows whose Russian name is "Jhvz" and whose English
    name is "!jgcjf!x". The test is deliberately blunt — a word of three or more
    letters with no vowel in it — because the alternative (a dictionary) would be a
    far larger dependency than the problem deserves.
    """
    normalized = normalize(text)
    if not normalized:
        return False

    words = tokens(normalized)
    if not words:
        # Nothing but punctuation and digits, e.g. "!!!" — certainly not a name.
        return True
    return any(len(word) >= 3 and not (_VOWELS & set(word)) for word in words)


# Words that pin a dish to a part of the menu. The value is the set of legacy
# category slugs where the word is unremarkable; anywhere else it is a filing error.
# Kept small and specific: a broad lexicon would flag half the menu and be ignored.
_CATEGORY_HINTS: dict[str, frozenset[str]] = {
    # Bakery items were filed under beverages because the old admin had no bread
    # section and "beverages" happened to be first in the dropdown.
    "non": frozenset(),
    "chorak": frozenset(),
    "buhanka": frozenset(),
    "patir": frozenset(),
    "lavash": frozenset(),
    # Sweets.
    "shakalad": frozenset({"desserts"}),
    "shokolad": frozenset({"desserts"}),
    "muzqaymoq": frozenset({"desserts"}),
    "morojniy": frozenset({"desserts"}),
    "tort": frozenset({"desserts"}),
    # Drinks.
    "chay": frozenset({"beverages"}),
    "cola": frozenset({"beverages"}),
    "pepsi": frozenset({"beverages"}),
    "fanta": frozenset({"beverages"}),
    "ayron": frozenset({"beverages"}),
    "sharbat": frozenset({"beverages"}),
    "moxito": frozenset({"beverages"}),
    "salat": frozenset({"salads"}),
}

# Alcohol needs the subcategory too: it belongs under beverages, but specifically
# under `beer`, and the export files lager as a soft drink.
_ALCOHOL_WORDS = frozenset({"piva", "pivo", "beer", "sarbast", "tubork", "tuborg"})
_ALCOHOL_SUBCATEGORY = "beer"


def category_issues(name_uz: str, category: str, subcategory: str | None) -> list[Issue]:
    """Flag a product whose name contradicts the section it was filed under."""
    words = set(tokens(name_uz))
    category = (category or "").strip().lower()
    subcategory = (subcategory or "").strip().lower()
    issues: list[Issue] = []

    for word in sorted(words & _CATEGORY_HINTS.keys()):
        expected = _CATEGORY_HINTS[word]
        if category not in expected:
            where = " or ".join(sorted(expected)) if expected else "no current section"
            issues.append(
                Issue(
                    Status.NEEDS_REVIEW,
                    Reason.CATEGORY_MISMATCH,
                    f"'{word}' suggests {where}, filed under '{category}'",
                )
            )

    if words & _ALCOHOL_WORDS and subcategory != _ALCOHOL_SUBCATEGORY:
        issues.append(
            Issue(
                Status.NEEDS_REVIEW,
                Reason.CATEGORY_MISMATCH,
                f"alcoholic drink filed under '{subcategory or category}'",
            )
        )
    return issues


@dataclass(frozen=True, slots=True)
class TranslationDraft:
    """A `ProductTranslation` that is about to be written."""

    language: str
    name: str
    description: str


def build_translations(
    names: dict[str, str], descriptions: dict[str, str]
) -> tuple[list[TranslationDraft], list[Issue]]:
    """Decide which languages genuinely have content.

    The legacy admin pre-filled `ru` and `en` with a copy of the Uzbek text, so about
    three quarters of the catalogue only *looks* trilingual. A copy is treated as an
    absent translation — the API's fallback then serves the Uzbek text and the admin
    can report the real coverage gap. A language is kept when either its name or its
    description differs from the Uzbek one; the row is never fabricated.
    """
    uz_name = normalize(names.get(Language.UZ))
    uz_description = normalize(descriptions.get(Language.UZ))
    drafts = [TranslationDraft(Language.UZ, uz_name, uz_description)]
    issues: list[Issue] = []

    if looks_like_noise(uz_name):
        issues.append(Issue(Status.NEEDS_REVIEW, Reason.SUSPICIOUS_TEXT, f"uz name {uz_name!r}"))

    for language in (Language.RU, Language.EN):
        name = normalize(names.get(language))
        description = normalize(descriptions.get(language))
        distinct_name = bool(name) and comparison_key(name) != comparison_key(uz_name)
        distinct_description = bool(description) and comparison_key(description) != comparison_key(
            uz_description
        )

        if not (distinct_name or distinct_description):
            continue

        if looks_like_noise(name) or looks_like_noise(description):
            # Mash is worse than a missing translation: the fallback would have shown
            # readable Uzbek. Drop it and make someone look at the row.
            issues.append(
                Issue(Status.NEEDS_REVIEW, Reason.SUSPICIOUS_TEXT, f"{language} name {name!r}")
            )
            continue

        drafts.append(TranslationDraft(language, name or uz_name, description))

    return drafts, issues


def price_issues(price: int | None) -> list[Issue]:
    """Reject the "5 so'm" rows the old admin accepted without a validator."""
    if price is None:
        return [Issue(Status.QUARANTINED, Reason.PRICE_MISSING, "no price field")]
    if price < MIN_PRICE_UZS:
        return [
            Issue(
                Status.QUARANTINED,
                Reason.PRICE_TOO_LOW,
                f"{price} UZS is below the {MIN_PRICE_UZS} UZS floor",
            )
        ]
    return []
