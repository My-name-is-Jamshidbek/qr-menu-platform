"""Recovery of product photos from legacy base64 data URLs.

The old site stored each photo inline in the document as `data:image/jpeg;base64,…`,
which is why the collection is ~15 MB of JSON for 86 dishes. The import decodes the
payload, checks it really is an image, and hands the bytes to `ProductImage`, whose
own `save()` writes the WebP derivatives to object storage.
"""

import binascii
import re
from base64 import b64decode

from django.core.exceptions import ValidationError

from apps.common.images import open_image

# Only the base64 form is accepted; the legacy export has no percent-encoded URLs.
_DATA_URL = re.compile(r"^data:(?P<mime>image/[\w.+-]+);base64,(?P<payload>.+)$", re.DOTALL)


class LegacyImageError(ValueError):
    """The `image` field is missing, malformed, or not a decodable image."""


def decode_data_url(value: str | None) -> bytes:
    """Return the raw bytes behind a base64 image data URL."""
    if not value:
        raise LegacyImageError("no image field")

    match = _DATA_URL.match(value.strip())
    if match is None:
        raise LegacyImageError(f"not a base64 image data URL (starts with {value[:24]!r})")

    try:
        raw = b64decode(match["payload"], validate=True)
    except (binascii.Error, ValueError) as exc:
        raise LegacyImageError(f"undecodable base64 payload: {exc}") from exc

    if not raw:
        raise LegacyImageError("empty image payload")
    return raw


def decode_image(value: str | None) -> tuple[bytes, tuple[int, int]]:
    """Decode and verify a legacy image, returning its bytes and pixel size.

    Verification happens during the read pass rather than at write time so that
    `--dry-run` reports an unusable photo without touching the database or the bucket.
    """
    raw = decode_data_url(value)
    try:
        image = open_image(raw)
    except ValidationError as exc:
        raise LegacyImageError("; ".join(exc.messages)) from exc
    return raw, image.size
