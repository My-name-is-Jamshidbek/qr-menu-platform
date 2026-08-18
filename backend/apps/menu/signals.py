"""Cache invalidation for every menu write.

Any change to a product, its translations, its photos or a category makes the cached
menu aggregate stale, and also makes the statically generated storefront pages stale.
Both are dealt with here so no view has to remember to do it.

The work is deferred to `transaction.on_commit`: `ATOMIC_REQUESTS` wraps each request in
a transaction, and dropping the cache before that commits would let a concurrent read
repopulate it from the pre-write snapshot.

The receivers are connected on import. They are wired up from `apps.menu.urls`, which
the root URLconf loads, because the app config for this app is owned elsewhere.
"""

import logging

from django.db import transaction
from django.db.models.signals import post_delete, post_save

from apps.common.api.revalidate import MENU_TAG, revalidate_async
from apps.menu.api.cache import invalidate_menu_cache
from apps.menu.models import (
    Category,
    CategoryTranslation,
    Product,
    ProductImage,
    ProductTranslation,
)

logger = logging.getLogger(__name__)

INVALIDATING_MODELS = (
    Product,
    ProductTranslation,
    ProductImage,
    Category,
    CategoryTranslation,
)


def flush_menu() -> None:
    """Drop the cached aggregate and tell the frontend to revalidate its ISR tags."""
    dropped = invalidate_menu_cache()
    logger.debug("Menu cache invalidated (%s keys)", dropped)
    revalidate_async([MENU_TAG])


def schedule_menu_flush() -> None:
    transaction.on_commit(flush_menu)


def invalidate_on_menu_write(sender, **kwargs) -> None:
    schedule_menu_flush()


for _model in INVALIDATING_MODELS:
    _name = _model.__name__
    post_save.connect(
        invalidate_on_menu_write, sender=_model, dispatch_uid=f"menu_cache_save_{_name}"
    )
    post_delete.connect(
        invalidate_on_menu_write, sender=_model, dispatch_uid=f"menu_cache_delete_{_name}"
    )
