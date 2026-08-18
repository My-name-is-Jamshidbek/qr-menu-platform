"""Role gates used across the admin surface.

Two levels only, matching the data model: `STAFF` may edit the menu, `ADMIN` may also
manage tables and accounts. Keeping both classes here means an endpoint declares its
required role in one line and no view re-implements the check.
"""

from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.accounts.models import Role


class IsStaffRole(BasePermission):
    """Authenticated staff (either role) — the menu-editing surface."""

    message = "This endpoint requires a staff account."

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and user.role in Role.values)


class IsAdminRole(BasePermission):
    """Authenticated administrators — tables and account management."""

    message = "This endpoint requires an administrator account."

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and user.role == Role.ADMIN)
