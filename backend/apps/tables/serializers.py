"""Serializers for QR scans and table administration."""

from rest_framework import serializers

from apps.common.enums import Language
from apps.common.serializers import UtcDateTimeField
from apps.tables.api.qr import scan_url
from apps.tables.models import Table


class TableScanRequestSerializer(serializers.Serializer):
    """Optional context a scanning client may report about itself.

    The field is named `language` rather than after the `locale` column so it shares one
    enum with the rest of the schema instead of minting a near-duplicate.
    """

    language = serializers.ChoiceField(choices=Language.choices, required=False)


class TableScanResponseSerializer(serializers.Serializer):
    """All a guest's device needs: which table it just claimed."""

    table_number = serializers.IntegerField()


class AdminTableSerializer(serializers.ModelSerializer):
    """A table as the admin UI edits it, plus the URL its QR code resolves to."""

    scan_url = serializers.SerializerMethodField()
    created_at = UtcDateTimeField(read_only=True)
    updated_at = UtcDateTimeField(read_only=True)

    class Meta:
        model = Table
        fields = [
            "id",
            "number",
            "token",
            "label",
            "is_active",
            "scan_url",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["token", "created_at", "updated_at"]

    def get_scan_url(self, table: Table) -> str:
        return scan_url(table)
