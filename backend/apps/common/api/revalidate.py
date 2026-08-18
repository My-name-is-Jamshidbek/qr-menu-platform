"""Fire-and-forget cache-busting ping to the Next.js frontend.

A staff edit must be visible on the statically generated menu within a couple of
seconds, which the frontend achieves with tag-based ISR revalidation. The API tells it
when to do that — but a slow or dead frontend must never make an admin write hang, so
the request runs on a daemon thread with a hard timeout and every failure is swallowed
into the log.
"""

import logging
import threading

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

REVALIDATE_PATH = "/api/revalidate"
MENU_TAG = "menu"


def _endpoint() -> str:
    return f"{settings.FRONTEND_URL.rstrip('/')}{REVALIDATE_PATH}"


def post_revalidate(tags: list[str]) -> bool:
    """POST the tags to the frontend. Returns True on a 2xx, never raises."""
    try:
        response = requests.post(
            _endpoint(),
            json={"tags": tags},
            headers={"X-Revalidate-Secret": settings.REVALIDATE_SECRET},
            timeout=settings.REVALIDATE_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        logger.warning("Revalidation ping to %s failed: %s", _endpoint(), exc)
        return False

    if response.status_code >= 400:
        logger.warning(
            "Revalidation ping to %s returned HTTP %s", _endpoint(), response.status_code
        )
        return False

    logger.info("Revalidated frontend tags %s", tags)
    return True


def revalidate_async(tags: list[str]) -> threading.Thread:
    """Start `post_revalidate` on a daemon thread and return immediately.

    The thread is returned only so tests can join it; callers ignore it.
    """
    thread = threading.Thread(
        target=post_revalidate,
        args=(list(tags),),
        name="revalidate-frontend",
        daemon=True,
    )
    thread.start()
    return thread
