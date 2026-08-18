"""Serializers for authentication and the current-account endpoint."""

from rest_framework import serializers
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer as BaseTokenObtainPairSerializer,
)
from rest_framework_simplejwt.serializers import (
    TokenRefreshSerializer as BaseTokenRefreshSerializer,
)

from apps.accounts.models import User

# One message for "no such user" and for "wrong password" alike: telling the two apart
# turns the login form into an account-enumeration oracle.
INVALID_CREDENTIALS = "Invalid username or password."


class TokenObtainPairSerializer(BaseTokenObtainPairSerializer):
    """Username/password exchange for an access + refresh pair."""

    default_error_messages = {"no_active_account": INVALID_CREDENTIALS}


class TokenRefreshSerializer(BaseTokenRefreshSerializer):
    """Refresh exchange. Rotation is on, so the response carries a new refresh too."""


class TokenPairResponseSerializer(serializers.Serializer):
    """Response body of `POST /auth/token/` (documentation only)."""

    access = serializers.CharField()
    refresh = serializers.CharField()


class TokenRefreshResponseSerializer(serializers.Serializer):
    """Response body of `POST /auth/token/refresh/` (documentation only)."""

    access = serializers.CharField()
    refresh = serializers.CharField(
        help_text="Rotated refresh token; the previous one is blacklisted."
    )


class CurrentUserSerializer(serializers.ModelSerializer):
    """The authenticated account, as the Next.js server needs it for its session."""

    class Meta:
        model = User
        fields = ["id", "username", "role"]
        read_only_fields = fields
