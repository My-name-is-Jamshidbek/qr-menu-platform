"""Unit tests for the language fallback rule, with no database involved."""

from dataclasses import dataclass

from apps.common.enums import Language
from apps.common.translations import resolve_translation


@dataclass
class FakeTranslation:
    language: str
    name: str


def test_exact_language_wins_and_is_not_a_fallback() -> None:
    rows = [FakeTranslation("uz", "Salat"), FakeTranslation("ru", "Салат")]

    translation, is_fallback = resolve_translation(rows, "ru")

    assert translation.name == "Салат"
    assert is_fallback is False


def test_missing_language_falls_back_to_uzbek_and_is_flagged() -> None:
    rows = [FakeTranslation("uz", "Salat"), FakeTranslation("ru", "Салат")]

    translation, is_fallback = resolve_translation(rows, "en")

    assert translation.name == "Salat"
    assert is_fallback is True


def test_no_translation_at_all_returns_nothing_without_claiming_a_fallback() -> None:
    translation, is_fallback = resolve_translation([], "en")

    assert translation is None
    assert is_fallback is False


def test_fallback_is_uzbek() -> None:
    assert Language.fallback() == Language.UZ
