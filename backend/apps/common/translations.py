"""Translation lookup with a single, shared fallback rule.

Every translated model stores its strings in a side table keyed by language. Rather
than repeat "try the requested language, else Uzbek" in each serializer, the rule
lives here once and models expose it through `TranslatableMixin`.
"""

from collections.abc import Iterable
from typing import Protocol

from django.db import models

from apps.common.enums import Language


class HasLanguage(Protocol):
    language: str


def resolve_translation[T: HasLanguage](
    translations: Iterable[T], language: str
) -> tuple[T | None, bool]:
    """Pick the translation for `language`, falling back to Uzbek.

    Returns `(translation, is_fallback)`. `is_fallback` is True only when a row was
    found in a language other than the one asked for. When nothing at all exists the
    result is `(None, False)` — the caller decides what an untranslated object means.
    """
    fallback_code = Language.fallback().value
    fallback: T | None = None

    for translation in translations:
        if translation.language == language:
            return translation, False
        if translation.language == fallback_code:
            fallback = translation

    if fallback is not None:
        return fallback, True
    return None, False


class TranslatableMixin(models.Model):
    """Adds fallback-aware accessors to a model with a `translations` reverse relation.

    Callers should `prefetch_related("translations")`; the lookup then runs in Python
    and costs no extra query per object.
    """

    class Meta:
        abstract = True

    def translation_for(self, language: str) -> tuple[models.Model | None, bool]:
        return resolve_translation(self.translations.all(), language)

    def name_for(self, language: str) -> tuple[str, bool]:
        """`(name, is_fallback)`; an empty name when the object has no translation."""
        translation, is_fallback = self.translation_for(language)
        if translation is None:
            return "", False
        return translation.name, is_fallback

    @property
    def missing_languages(self) -> list[str]:
        """Language codes with no translation row, in `Language` declaration order."""
        present = {translation.language for translation in self.translations.all()}
        return [code for code in Language.values if code not in present]
