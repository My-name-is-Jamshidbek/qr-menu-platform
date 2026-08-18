"""Guards on the infrastructure wiring the whole API depends on."""

from django.conf import settings
from django.core.cache import cache
from django.core.files.storage import default_storage

from apps.common.pagination import StandardPagination


def test_pagination_limits_match_the_api_contract() -> None:
    assert StandardPagination.page_size == 20
    assert StandardPagination.max_page_size == 100
    assert StandardPagination.page_size_query_param == "page_size"


def test_throttle_rates_match_the_api_contract() -> None:
    rates = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]
    assert rates["anon"] == "120/min"
    assert rates["user"] == "600/min"
    assert rates["login"] == "5/min"


def test_project_uses_the_custom_user_model_and_tashkent_time() -> None:
    assert settings.AUTH_USER_MODEL == "accounts.User"
    assert settings.TIME_ZONE == "Asia/Tashkent"
    assert settings.USE_TZ is True


def test_cors_is_locked_to_the_frontend_origin() -> None:
    assert settings.CORS_ALLOWED_ORIGINS == [settings.FRONTEND_URL]


def test_redis_cache_round_trips() -> None:
    cache.set("wiring-probe", "ok", 10)
    assert cache.get("wiring-probe") == "ok"
    cache.delete("wiring-probe")


def test_default_storage_points_at_the_configured_bucket() -> None:
    url = default_storage.url("products/probe.webp")
    assert url.startswith(settings.S3_PUBLIC_URL)
    assert settings.S3_BUCKET in url
    # The bucket is public, so URLs must not carry a signature.
    assert "?" not in url
