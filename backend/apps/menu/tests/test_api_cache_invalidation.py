"""Menu writes must drop the Redis aggregate and ping the frontend — without blocking."""

import pytest
import requests
from django.core.cache import cache
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.factories import UserFactory
from apps.common.api.revalidate import MENU_TAG, post_revalidate, revalidate_async
from apps.common.enums import Language
from apps.menu.api.cache import invalidate_menu_cache, menu_cache_key
from apps.menu.factories import CategoryFactory, ProductFactory, ProductTranslationFactory
from apps.menu.signals import flush_menu

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def clean_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def staff_client() -> APIClient:
    client = APIClient()
    token = RefreshToken.for_user(UserFactory()).access_token
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


@pytest.fixture(autouse=True)
def silent_revalidation(monkeypatch) -> list[list[str]]:
    """Capture revalidation pings instead of letting the suite talk to the network."""
    calls: list[list[str]] = []
    monkeypatch.setattr("apps.menu.signals.revalidate_async", lambda tags: calls.append(list(tags)))
    return calls


def _warm_the_cache(client: APIClient) -> None:
    client.get(reverse("menu:menu"))
    assert cache.get(menu_cache_key(Language.UZ.value)) is not None


def test_invalidate_menu_cache_only_removes_menu_keys() -> None:
    cache.set(menu_cache_key("uz"), {"categories": []}, 60)
    cache.set(menu_cache_key("ru"), {"categories": []}, 60)
    cache.set("unrelated", "keep", 60)

    removed = invalidate_menu_cache()

    assert removed == 2
    assert cache.get(menu_cache_key("uz")) is None
    assert cache.get("unrelated") == "keep"


def test_a_product_write_drops_the_cache_and_pings_the_frontend(
    staff_client, silent_revalidation, django_capture_on_commit_callbacks
) -> None:
    category = CategoryFactory(slug="salads")
    _warm_the_cache(APIClient())

    with django_capture_on_commit_callbacks(execute=True):
        response = staff_client.post(
            reverse("menu:admin-product-list"),
            {
                "category": category.pk,
                "price": 30_000,
                "translations": [{"language": "uz", "name": "Boss salat"}],
            },
            format="json",
        )

    assert response.status_code == 201
    assert cache.get(menu_cache_key(Language.UZ.value)) is None
    assert silent_revalidation == [[MENU_TAG]]


def test_a_translation_write_invalidates_too(
    silent_revalidation, django_capture_on_commit_callbacks
) -> None:
    product = ProductFactory(slug="boss-salad")
    _warm_the_cache(APIClient())

    with django_capture_on_commit_callbacks(execute=True):
        ProductTranslationFactory(product=product, language=Language.RU, name="Босс салат")

    assert cache.get(menu_cache_key(Language.UZ.value)) is None
    assert silent_revalidation == [[MENU_TAG]]


def test_a_delete_invalidates_too(silent_revalidation, django_capture_on_commit_callbacks) -> None:
    product = ProductFactory(slug="boss-salad")
    _warm_the_cache(APIClient())

    with django_capture_on_commit_callbacks(execute=True):
        product.delete()

    assert cache.get(menu_cache_key(Language.UZ.value)) is None
    assert silent_revalidation


def test_the_menu_is_rebuilt_after_an_invalidation(silent_revalidation) -> None:
    category = CategoryFactory(slug="salads")
    client = APIClient()
    _warm_the_cache(client)

    ProductFactory(slug="new-dish", category=category)
    flush_menu()

    body = client.get(reverse("menu:menu")).json()

    assert [row["slug"] for row in body["categories"][0]["products"]] == ["new-dish"]


# --------------------------------------------------------------------------- transport


def test_the_revalidation_post_carries_the_shared_secret(monkeypatch, settings) -> None:
    settings.FRONTEND_URL = "http://frontend.test"
    settings.REVALIDATE_SECRET = "s3cret"
    seen: dict = {}

    def fake_post(url, **kwargs):
        seen.update({"url": url, **kwargs})
        return type("Response", (), {"status_code": 200})()

    monkeypatch.setattr(requests, "post", fake_post)

    assert post_revalidate([MENU_TAG]) is True
    assert seen["url"] == "http://frontend.test/api/revalidate"
    assert seen["headers"]["X-Revalidate-Secret"] == "s3cret"
    assert seen["json"] == {"tags": [MENU_TAG]}
    assert seen["timeout"] == settings.REVALIDATE_TIMEOUT_SECONDS


def test_a_dead_frontend_is_logged_and_swallowed(monkeypatch, caplog) -> None:
    def explode(*args, **kwargs):
        raise requests.ConnectionError("frontend is down")

    monkeypatch.setattr(requests, "post", explode)

    assert post_revalidate([MENU_TAG]) is False
    assert "failed" in caplog.text


def test_an_error_status_from_the_frontend_is_not_fatal(monkeypatch) -> None:
    monkeypatch.setattr(
        requests, "post", lambda url, **kwargs: type("Response", (), {"status_code": 500})()
    )

    assert post_revalidate([MENU_TAG]) is False


def test_the_ping_runs_off_the_request_thread(monkeypatch) -> None:
    monkeypatch.setattr(
        requests, "post", lambda url, **kwargs: type("Response", (), {"status_code": 200})()
    )

    thread = revalidate_async([MENU_TAG])

    assert thread.daemon is True
    thread.join(timeout=5)
    assert not thread.is_alive()
