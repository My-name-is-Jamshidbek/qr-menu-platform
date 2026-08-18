"""JWT login, refresh and "who am I".

Tokens never reach the browser: the Next.js server holds them in httpOnly cookies and
calls this API server-side, which is why there is no cookie or session flow here.
"""

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.accounts.models import User
from apps.accounts.serializers import (
    CurrentUserSerializer,
    TokenObtainPairSerializer,
    TokenPairResponseSerializer,
    TokenRefreshResponseSerializer,
    TokenRefreshSerializer,
)
from apps.accounts.throttles import LoginRateThrottle
from apps.common.serializers import ErrorSerializer


@extend_schema(
    tags=["auth"],
    summary="Exchange credentials for a token pair",
    responses={
        status.HTTP_200_OK: TokenPairResponseSerializer,
        status.HTTP_401_UNAUTHORIZED: ErrorSerializer,
    },
)
class TokenObtainView(TokenObtainPairView):
    serializer_class = TokenObtainPairSerializer
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]


@extend_schema(
    tags=["auth"],
    summary="Rotate a refresh token",
    responses={
        status.HTTP_200_OK: TokenRefreshResponseSerializer,
        status.HTTP_401_UNAUTHORIZED: ErrorSerializer,
    },
)
class TokenRefreshApiView(TokenRefreshView):
    serializer_class = TokenRefreshSerializer
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]


@extend_schema(tags=["auth"], summary="The authenticated account")
class CurrentUserView(RetrieveAPIView):
    """`GET /auth/me/` — the object is the requesting user, so there is no lookup."""

    serializer_class = CurrentUserSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]
    queryset = User.objects.none()

    def get_object(self) -> User:
        return self.request.user
