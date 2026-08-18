"""Table routes: the public scan hit and the administrator surface."""

from django.urls import path

from apps.tables.api.admin import (
    AdminTableDetailView,
    AdminTableListCreateView,
    TableQrSheetView,
    TableQrSvgView,
)
from apps.tables.api.public import TableScanView

app_name = "tables"

urlpatterns = [
    path("tables/<uuid:token>/scan/", TableScanView.as_view(), name="scan"),
    # The literal sheet route is declared before `<int:pk>` so "qr-sheet.pdf" is never
    # read as a table id.
    path("admin/tables/qr-sheet.pdf", TableQrSheetView.as_view(), name="admin-table-qr-sheet"),
    path("admin/tables/", AdminTableListCreateView.as_view(), name="admin-table-list"),
    path("admin/tables/<int:pk>/", AdminTableDetailView.as_view(), name="admin-table-detail"),
    path("admin/tables/<int:pk>/qr.svg", TableQrSvgView.as_view(), name="admin-table-qr"),
]
