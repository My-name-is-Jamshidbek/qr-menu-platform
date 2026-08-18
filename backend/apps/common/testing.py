"""Test helpers shared by the app test suites.

Kept out of a `tests` package so every app can import it regardless of pytest's
per-directory `conftest` scoping.
"""

from collections.abc import Iterator
from pathlib import Path

import pytest


@pytest.fixture
def local_storage(settings, tmp_path: Path) -> Iterator[Path]:
    """Swap S3/MinIO for a throwaway filesystem storage.

    Model tests exercise image writes; pointing them at a temp directory keeps the
    suite hermetic and fast while leaving the S3 wiring test untouched.
    """
    media_root = tmp_path / "media"
    media_root.mkdir()
    settings.MEDIA_ROOT = media_root
    settings.MEDIA_URL = "/media/"
    settings.STORAGES = {
        **settings.STORAGES,
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    }
    yield media_root
