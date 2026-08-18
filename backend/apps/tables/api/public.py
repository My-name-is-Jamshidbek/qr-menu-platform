"""The one public table endpoint: recording a QR scan."""

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.serializers import ErrorSerializer
from apps.tables.models import USER_AGENT_MAX_LENGTH, Table, TableScan
from apps.tables.serializers import TableScanRequestSerializer, TableScanResponseSerializer
from apps.tables.throttles import TableScanThrottle


@extend_schema(
    tags=["tables"],
    summary="Record a QR scan and resolve the table number",
    request=TableScanRequestSerializer,
    responses={
        200: TableScanResponseSerializer,
        404: ErrorSerializer,
        429: ErrorSerializer,
    },
)
class TableScanView(APIView):
    """`POST /tables/{token}/scan/`.

    An unknown *or* inactive token is a 404 with the same body, so a retired token
    cannot be told apart from a fabricated one.
    """

    permission_classes = [AllowAny]
    authentication_classes: list = []
    throttle_classes = [TableScanThrottle]

    def post(self, request: Request, token: str) -> Response:
        serializer = TableScanRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        table = get_object_or_404(Table, token=token, is_active=True)
        TableScan.objects.create(
            table=table,
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:USER_AGENT_MAX_LENGTH],
            locale=serializer.validated_data.get("language", ""),
        )
        return Response(TableScanResponseSerializer({"table_number": table.number}).data)
