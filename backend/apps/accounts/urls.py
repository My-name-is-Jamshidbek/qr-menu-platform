"""Authentication routes, mounted at `/api/v1/auth/`."""

from django.urls import path

from apps.accounts.api.auth import CurrentUserView, TokenObtainView, TokenRefreshApiView

app_name = "accounts"

urlpatterns = [
    path("token/", TokenObtainView.as_view(), name="token-obtain"),
    path("token/refresh/", TokenRefreshApiView.as_view(), name="token-refresh"),
    path("me/", CurrentUserView.as_view(), name="me"),
]
