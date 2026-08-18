"""Enumerations shared by more than one app."""

from django.db import models


class Language(models.TextChoices):
    """Languages the menu is published in.

    `UZ` is the fallback: when a translation is missing the API serves the Uzbek
    value and flags the parent object with `is_fallback`.
    """

    UZ = "uz", "O'zbekcha"
    RU = "ru", "Русский"
    EN = "en", "English"

    @classmethod
    def fallback(cls) -> "Language":
        return cls.UZ
