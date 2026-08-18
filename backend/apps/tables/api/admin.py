"""Table administration and QR artwork. Administrator role only."""

from django.http import Http404, HttpResponse
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdminRole
from apps.common.serializers import ErrorSerializer
from apps.tables.api.qr import qr_sheet_pdf, table_qr_svg
from apps.tables.models import Table
from apps.tables.serializers import AdminTableSerializer


class AdminTableMixin:
    permission_classes = [IsAdminRole]
    serializer_class = AdminTableSerializer
    queryset = Table.objects.all()


@extend_schema(tags=["admin-tables"])
class AdminTableListCreateView(AdminTableMixin, ListCreateAPIView):
    pass


@extend_schema(tags=["admin-tables"])
class AdminTableDetailView(AdminTableMixin, RetrieveUpdateDestroyAPIView):
    http_method_names = ["get", "patch", "delete", "head", "options"]


@extend_schema(
    tags=["admin-tables"],
    summary="One table's QR code as SVG",
    responses={
        (200, "image/svg+xml"): OpenApiResponse(
            response={"type": "string", "format": "binary"}, description="SVG document."
        ),
        404: ErrorSerializer,
    },
)
class TableQrSvgView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request: Request, pk: int) -> HttpResponse:
        table = Table.objects.filter(pk=pk).first()
        if table is None:
            raise Http404("No table matches the given id.")
        response = HttpResponse(table_qr_svg(table), content_type="image/svg+xml")
        response["Content-Disposition"] = f'inline; filename="table-{table.number}.svg"'
        return response


@extend_schema(
    tags=["admin-tables"],
    summary="Printable sheet of every active table's QR code",
    responses={
        (200, "application/pdf"): OpenApiResponse(
            response={"type": "string", "format": "binary"}, description="A4 PDF sheet."
        )
    },
)
class TableQrSheetView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request: Request) -> HttpResponse:
        tables = list(Table.objects.filter(is_active=True))
        response = HttpResponse(qr_sheet_pdf(tables), content_type="application/pdf")
        response["Content-Disposition"] = 'inline; filename="table-qr-sheet.pdf"'
        return response
