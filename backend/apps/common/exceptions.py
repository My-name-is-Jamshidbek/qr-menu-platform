"""A single error shape for the whole API.

Every failure is rendered as::

    {"detail": str, "code": str, "field_errors": {field: [str, ...]}}

DRF's own payloads vary (a bare string, a list, a dict of field lists); this handler
normalises them so the frontend has exactly one branch to write.
"""

from typing import Any

from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


def _flatten(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, dict):
        return [text for nested in value.values() for text in _flatten(nested)]
    return [str(value)]


def api_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    data = response.data
    code = getattr(exc, "default_code", "error")
    field_errors: dict[str, list[str]] = {}

    if isinstance(data, dict):
        detail = data.get("detail")
        if detail is None:
            field_errors = {key: _flatten(value) for key, value in data.items()}
            detail = "Validation failed."
        else:
            code = getattr(detail, "code", code)
            detail = str(detail)
    else:
        detail = "; ".join(_flatten(data))

    response.data = {
        "detail": str(detail),
        "code": str(code),
        "field_errors": field_errors,
    }
    return response
