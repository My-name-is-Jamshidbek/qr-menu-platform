"""Stable per-document identity carried across the migration.

The import must be re-runnable, so every imported row needs an anchor that survives
a second run even if the shop renames the dish. The new schema has no `legacy_id`
column, so the anchor is folded into the product slug as a fixed-width suffix:

    Firestore id "0PVjqxg3N5ffO8dd1M45"  ->  slug "boss-salat-h4qk2xzp"

The suffix is a hash, not the raw id: Firestore ids are case sensitive and slugs are
not, so lowercasing the id would risk collisions and produce noisier URLs.

Should `Product` ever gain a real `legacy_id` field, `find_by_legacy_id` is the only
call site that needs to change.
"""

import base64
import hashlib

from django.utils.text import slugify

# 5 bytes encode to exactly 8 unpadded base32 characters, all of them slug safe.
_KEY_BYTES = 5
KEY_LENGTH = 8

# Leave room for the "-" plus the key inside Product.slug's 120 characters.
MAX_NAME_LENGTH = 120 - KEY_LENGTH - 1


def legacy_key(legacy_id: str) -> str:
    """Short, lowercase, slug-safe fingerprint of a Firestore document id."""
    digest = hashlib.blake2s(legacy_id.encode("utf-8"), digest_size=_KEY_BYTES).digest()
    return base64.b32encode(digest).decode("ascii").rstrip("=").lower()


def legacy_slug(legacy_id: str, name: str) -> str:
    """Deterministic product slug: readable name plus the identity suffix.

    Falls back to a bare key when the name transliterates to nothing (Cyrillic-only
    names slugify to an empty string), so the result is never just a dangling dash.
    """
    key = legacy_key(legacy_id)
    stem = slugify(name)[:MAX_NAME_LENGTH].strip("-")
    return f"{stem}-{key}" if stem else key


def slug_suffix(slug: str) -> str:
    """The identity suffix of a slug, or an empty string when it carries none."""
    tail = slug.rsplit("-", 1)[-1]
    return tail if len(tail) == KEY_LENGTH else ""
