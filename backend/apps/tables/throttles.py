"""Throttling for the public table-scan endpoint."""

from rest_framework.request import Request
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.views import APIView


class TableScanThrottle(SimpleRateThrottle):
    """30/hour per table token.

    Keyed on the token rather than the client IP on purpose: a whole table of guests
    shares one NAT address, and the thing worth protecting is the scan analytics of a
    single table from being flooded.
    """

    scope = "table_scan"

    def get_cache_key(self, request: Request, view: APIView) -> str | None:
        token = view.kwargs.get("token")
        if token is None:  # pragma: no cover - the URL always supplies it
            return None
        return self.cache_format % {"scope": self.scope, "ident": token}
