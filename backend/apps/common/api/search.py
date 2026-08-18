"""Accent-insensitive, case-insensitive matching for menu search.

Postgres ships an `unaccent` extension, but enabling it needs a superuser `CREATE
EXTENSION` on every environment including throwaway test databases. The same result is
available from the built-in `translate()` function: feed it a folding table and it maps
accented characters to their ASCII base and deletes the Uzbek apostrophe variants
(`translate` drops any character in `from` that has no counterpart in `to`).

The folding table is derived from Unicode decomposition at import time rather than typed
out by hand, so it cannot drift from the `fold()` used on the search term itself.
"""

import unicodedata

from django.db.models import F, Func, TextField, Value
from django.db.models.expressions import Combinable
from django.db.models.functions import Lower

# Latin-1 Supplement through Latin Extended-B: every character there that decomposes to a
# single ASCII letter (é → e, ő → o, ı → i ...).
_LATIN_RANGE = range(0x00C0, 0x0250)

# Russian only needs ё → е; folding й → и would wrongly merge distinct words.
_EXPLICIT_MAP = {"Ё": "Е", "ё": "е"}

# Uzbek Latin writes oʻ/gʻ with several visually identical marks, and staff type whichever
# their keyboard offers. Dropping them entirely makes all spellings match each other.
_DELETED = "'’ʻʼʽ`´"


def _decompose(character: str) -> str | None:
    stripped = "".join(
        part for part in unicodedata.normalize("NFD", character) if not unicodedata.combining(part)
    )
    return stripped if len(stripped) == 1 and stripped.isascii() else None


def _build_folding_table() -> tuple[str, str]:
    sources: list[str] = []
    targets: list[str] = []

    for code_point in _LATIN_RANGE:
        character = chr(code_point)
        folded = _decompose(character)
        if folded is not None and folded != character:
            sources.append(character)
            targets.append(folded)

    for character, folded in _EXPLICIT_MAP.items():
        sources.append(character)
        targets.append(folded)

    # Deleted characters go last: `translate()` removes trailing `from` characters that
    # run past the end of `to`.
    sources.extend(_DELETED)

    return "".join(sources), "".join(targets)


FOLD_FROM, FOLD_TO = _build_folding_table()

_DELETE_TABLE = {ord(character): None for character in _DELETED}
_FOLD_TABLE = {ord(source): target for source, target in zip(FOLD_FROM, FOLD_TO, strict=False)}


def fold(text: str) -> str:
    """Python-side twin of the SQL expression: lowercase, unaccented, apostrophes gone."""
    return text.translate(_FOLD_TABLE).translate(_DELETE_TABLE).lower()


def folded(expression: str | Combinable) -> Lower:
    """SQL expression yielding the folded form of `expression` (a field name or an F)."""
    return Lower(
        Func(
            F(expression) if isinstance(expression, str) else expression,
            Value(FOLD_FROM),
            Value(FOLD_TO),
            function="translate",
            output_field=TextField(),
        )
    )
