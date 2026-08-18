"""The published OpenAPI schema is a build artefact for the frontend types.

If it stops generating cleanly, `npm run gen:api` silently produces worse types, so the
warning count is asserted here rather than left to a manual command.
"""

import pytest
from django.urls import reverse
from drf_spectacular.drainage import GENERATOR_STATS
from drf_spectacular.generators import SchemaGenerator
from rest_framework.test import APIClient

EXPECTED_PATHS = [
    "/api/v1/menu/",
    "/api/v1/products/",
    "/api/v1/products/{slug}/",
    "/api/v1/tables/{token}/scan/",
    "/api/v1/auth/token/",
    "/api/v1/auth/token/refresh/",
    "/api/v1/auth/me/",
    "/api/v1/admin/products/",
    "/api/v1/admin/products/{id}/",
    "/api/v1/admin/products/{product_id}/images/",
    "/api/v1/admin/products/{product_id}/images/{image_id}/",
    "/api/v1/admin/categories/",
    "/api/v1/admin/categories/{id}/",
    "/api/v1/admin/tables/",
    "/api/v1/admin/tables/{id}/",
    "/api/v1/admin/tables/{id}/qr.svg",
    "/api/v1/admin/tables/qr-sheet.pdf",
    "/api/v1/admin/stats/",
]


@pytest.fixture
def schema() -> dict:
    GENERATOR_STATS.reset()
    generated = SchemaGenerator().get_schema(request=None, public=True)
    assert not GENERATOR_STATS._warn_cache, dict(GENERATOR_STATS._warn_cache)
    assert not GENERATOR_STATS._error_cache, dict(GENERATOR_STATS._error_cache)
    return generated


def test_the_schema_generates_without_warnings_or_errors(schema) -> None:
    assert schema["openapi"].startswith("3.1")


@pytest.mark.parametrize("path", EXPECTED_PATHS)
def test_every_contract_path_is_published(schema, path: str) -> None:
    assert path in schema["paths"]


def test_the_menu_response_is_fully_typed(schema) -> None:
    response = schema["paths"]["/api/v1/menu/"]["get"]["responses"]["200"]
    reference = response["content"]["application/json"]["schema"]["$ref"]

    assert reference.rsplit("/", 1)[-1] == "Menu"
    menu = schema["components"]["schemas"]["Menu"]
    assert set(menu["properties"]) == {"categories", "generated_at"}


def test_the_image_upload_is_documented_as_multipart(schema) -> None:
    operation = schema["paths"]["/api/v1/admin/products/{product_id}/images/"]["post"]

    assert "multipart/form-data" in operation["requestBody"]["content"]


@pytest.mark.django_db
def test_the_schema_endpoint_serves_it() -> None:
    response = APIClient().get(reverse("schema"))

    assert response.status_code == 200
    assert response["Content-Type"].startswith("application/vnd.oai.openapi")
