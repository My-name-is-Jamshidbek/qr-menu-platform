"""Redis caching of the menu aggregate.

One key per language, all of them under the `menu:` namespace so a single pattern
delete drops the lot when anything in the menu changes.
"""

import logging

from django.core.cache import cache

logger = logging.getLogger(__name__)

MENU_CACHE_NAMESPACE = "menu"
MENU_CACHE_PATTERN = f"{MENU_CACHE_NAMESPACE}:*"
MENU_CACHE_TTL_SECONDS = 300


def menu_cache_key(language: str) -> str:
    return f"{MENU_CACHE_NAMESPACE}:{language}"


def invalidate_menu_cache() -> int:
    """Drop every `menu:*` key. Returns the number of keys removed."""
    delete_pattern = getattr(cache, "delete_pattern", None)
    if delete_pattern is None:  # pragma: no cover - only a non-Redis backend lands here
        logger.warning("Cache backend has no delete_pattern; clearing the whole cache.")
        cache.clear()
        return 0
    return delete_pattern(MENU_CACHE_PATTERN) or 0
