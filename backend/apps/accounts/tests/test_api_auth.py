"""JWT login, rotation and the current-account endpoint."""

import pytest
from django.core.cache import cache
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.factories import DEFAULT_TEST_PASSWORD, UserFactory
from apps.accounts.models import Role
from apps.accounts.serializers import INVALID_CREDENTIALS

pytestmark = pytest.mark.django_db

LOGIN_RATE_LIMIT = 5


@pytest.fixture(autouse=True)
def clean_cache():
    """Login throttle counters live in Redis; reset them between tests."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def client() -> APIClient:
    return APIClient()


@pytest.fixture
def token_url() -> str:
    return reverse("accounts:token-obtain")


def _login(client: APIClient, url: str, **overrides):
    payload = {"username": "staff-user", "password": DEFAULT_TEST_PASSWORD, **overrides}
    return client.post(url, payload, format="json")


def test_valid_credentials_return_an_access_and_refresh_pair(client, token_url) -> None:
    UserFactory(username="staff-user")

    response = _login(client, token_url)

    assert response.status_code == 200
    assert set(response.json()) == {"access", "refresh"}


def test_a_wrong_password_and_an_unknown_user_look_identical(client, token_url) -> None:
    UserFactory(username="staff-user")

    wrong_password = _login(client, token_url, password="not-the-password")
    unknown_user = _login(client, token_url, username="ghost")

    assert wrong_password.status_code == unknown_user.status_code == 401
    assert wrong_password.json()["detail"] == unknown_user.json()["detail"] == INVALID_CREDENTIALS


def test_an_inactive_account_cannot_log_in(client, token_url) -> None:
    UserFactory(username="staff-user", is_active=False)

    response = _login(client, token_url)

    assert response.status_code == 401


def test_login_is_throttled_at_five_per_minute(client, token_url) -> None:
    UserFactory(username="staff-user")

    statuses = [
        _login(client, token_url, password="wrong").status_code for _ in range(LOGIN_RATE_LIMIT + 1)
    ]

    assert statuses[:LOGIN_RATE_LIMIT] == [401] * LOGIN_RATE_LIMIT
    assert statuses[-1] == 429


def test_a_refresh_token_is_exchanged_for_a_new_access_token(client, token_url) -> None:
    UserFactory(username="staff-user")
    tokens = _login(client, token_url).json()

    response = client.post(
        reverse("accounts:token-refresh"), {"refresh": tokens["refresh"]}, format="json"
    )

    assert response.status_code == 200
    assert response.json()["access"]


def test_a_rotated_refresh_token_cannot_be_reused(client, token_url) -> None:
    UserFactory(username="staff-user")
    refresh = _login(client, token_url).json()["refresh"]
    url = reverse("accounts:token-refresh")

    first = client.post(url, {"refresh": refresh}, format="json")
    replay = client.post(url, {"refresh": refresh}, format="json")

    assert first.status_code == 200
    assert first.json()["refresh"] != refresh
    assert replay.status_code == 401


def test_a_garbage_refresh_token_is_rejected(client) -> None:
    response = client.post(
        reverse("accounts:token-refresh"), {"refresh": "not-a-token"}, format="json"
    )

    assert response.status_code == 401


def test_me_returns_the_authenticated_account(client) -> None:
    user = UserFactory(username="staff-user", role=Role.ADMIN)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")

    body = client.get(reverse("accounts:me")).json()

    assert body == {"id": user.pk, "username": "staff-user", "role": "ADMIN"}


def test_me_requires_a_token(client) -> None:
    assert client.get(reverse("accounts:me")).status_code == 401


def test_an_access_token_is_not_accepted_as_a_refresh_token(client, token_url) -> None:
    UserFactory(username="staff-user")
    access = _login(client, token_url).json()["access"]

    response = client.post(reverse("accounts:token-refresh"), {"refresh": access}, format="json")

    assert response.status_code == 401
