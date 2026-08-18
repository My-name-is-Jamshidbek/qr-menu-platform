"""Development settings: verbose errors, browsable schema, relaxed transport security."""

from .base import *  # noqa: F403
from .base import REST_FRAMEWORK, SPECTACULAR_SETTINGS

DEBUG = True

# The dev stack is reached over plain HTTP on localhost.
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Serve the interactive schema UI while developing.
SPECTACULAR_SETTINGS = {**SPECTACULAR_SETTINGS, "SERVE_INCLUDE_SCHEMA": True}

# Keep the browsable API available for manual poking, JSON stays the default renderer.
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ),
}

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
