"""Field and serializer shapes shared by every app.

Some of these carry behaviour (the UTC datetime field); the rest exist so the OpenAPI
schema describes hand-built payloads as precisely as the model-backed ones.
"""

from datetime import UTC, timezone

from rest_framework import serializers


class UtcDateTimeField(serializers.DateTimeField):
    """ISO 8601 in UTC, whatever `TIME_ZONE` the server runs in.

    The project's `TIME_ZONE` is Asia/Tashkent, so DRF would otherwise render `+05:00`
    offsets; the API contract promises UTC, and one timezone across every consumer is
    one class of date bug the frontend never has to think about.
    """

    def default_timezone(self) -> timezone:
        # DRF converts every rendered value into this zone; overriding it here is the
        # supported hook, and it covers parsing naive input too.
        return UTC


class ErrorSerializer(serializers.Serializer):
    """The single error envelope produced by `apps.common.exceptions`."""

    detail = serializers.CharField()
    code = serializers.CharField()
    field_errors = serializers.DictField(
        child=serializers.ListField(child=serializers.CharField()),
        help_text="Per-field messages; empty for non-validation failures.",
    )


class ImageSerializer(serializers.Serializer):
    """A product photo and its WebP derivatives, identical everywhere it appears."""

    alt = serializers.CharField()
    width = serializers.IntegerField()
    height = serializers.IntegerField()
    src = serializers.URLField(help_text="The 800px derivative, used as the plain `src`.")
    srcset = serializers.DictField(
        child=serializers.URLField(),
        help_text="Derivative URL keyed by rendered width in pixels.",
    )
