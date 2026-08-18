"""Tables admin.

Tables are printed objects, so the list is built around the two questions staff ask:
which token does this table's QR carry, and is anyone actually scanning it.
"""

from django.contrib import admin
from django.db.models import Count, Max, QuerySet
from django.http import HttpRequest
from django.utils.html import format_html

from apps.tables.models import Table, TableScan


@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ["number", "label", "is_active", "token_short", "scan_count", "last_scan"]
    list_filter = ["is_active"]
    list_editable = ["label", "is_active"]
    search_fields = ["number", "label", "token"]
    readonly_fields = ["token", "created_at", "updated_at"]
    ordering = ["number"]

    def get_queryset(self, request: HttpRequest) -> QuerySet[Table]:
        return (
            super()
            .get_queryset(request)
            .annotate(_scan_count=Count("scans"), _last_scan=Max("scans__scanned_at"))
        )

    @admin.display(description="Token")
    def token_short(self, obj: Table) -> str:
        # The full UUID is on the detail page; the list only needs enough to match a
        # printed QR sheet against a row.
        return format_html("<code>{}…</code>", str(obj.token)[:8])

    @admin.display(description="Scans", ordering="_scan_count")
    def scan_count(self, obj: Table) -> int:
        return obj._scan_count

    @admin.display(description="Last scan", ordering="_last_scan")
    def last_scan(self, obj: Table):
        return obj._last_scan


@admin.register(TableScan)
class TableScanAdmin(admin.ModelAdmin):
    """Read-only analytics log: rows are written by the scan endpoint, never by hand."""

    list_display = ["table", "scanned_at", "locale", "user_agent"]
    list_filter = ["locale", "table"]
    search_fields = ["table__number", "user_agent"]
    date_hierarchy = "scanned_at"
    list_select_related = ["table"]

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: TableScan | None = None) -> bool:
        return False
