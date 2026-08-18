"""Resolution of the `?lang=` query parameter.

Every public endpoint is language-aware and every one of them rejects an unknown code
with 400 rather than silently falling back, so a typo in the frontend surfaces during
development instead of shipping an Uzbek page to a Russian guest.
"""

from django.http import HttpRequest
from drf_spectacular.utils import OpenApiParameter
from rest_framework.exceptions import ValidationError

from apps.common.enums import Language

LANGUAGE_QUERY_PARAM = "lang"

LANGUAGE_PARAMETER = OpenApiParameter(
    name=LANGUAGE_QUERY_PARAM,
    type=str,
    location=OpenApiParameter.QUERY,
    required=False,
    enum=list(Language.values),
    default=Language.fallback().value,
    description="Language of the returned strings. Falls back to Uzbek per field.",
)


def resolve_language(request: HttpRequest) -> str:
    """The requested language code, defaulting to Uzbek.

    Raises `ValidationError` (HTTP 400) for anything outside `Language`.
    """
    raw = request.GET.get(LANGUAGE_QUERY_PARAM)
    if raw is None or raw == "":
        return Language.fallback().value

    if raw not in Language.values:
        supported = ", ".join(Language.values)
        raise ValidationError(
            {LANGUAGE_QUERY_PARAM: [f"Unsupported language. Use one of: {supported}."]}
        )

    return raw
