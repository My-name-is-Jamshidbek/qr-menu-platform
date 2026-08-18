"""The public scan endpoint, table administration and the QR artwork."""

import uuid

import pytest
from django.core.cache import cache
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.factories import UserFactory
from apps.tables.api.qr import qr_sheet_pdf, scan_url, site_url, table_qr_svg
from apps.tables.factories import TableFactory
from apps.tables.models import Table, TableScan

pytestmark = pytest.mark.django_db

SCAN_RATE_LIMIT = 30


@pytest.fixture(autouse=True)
def clean_cache():
    """Scan throttle counters live in Redis; reset them between tests."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def client() -> APIClient:
    return APIClient()


def _client_for(user) -> APIClient:
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    return client


@pytest.fixture
def admin_client() -> APIClient:
    return _client_for(UserFactory(admin=True))


@pytest.fixture
def staff_client() -> APIClient:
    return _client_for(UserFactory())


def _scan_url(table: Table) -> str:
    return reverse("tables:scan", args=[table.token])


# --------------------------------------------------------------------------- scanning


def test_a_scan_records_a_row_and_returns_the_table_number(client) -> None:
    table = TableFactory(number=7)

    response = client.post(_scan_url(table), {}, format="json", HTTP_USER_AGENT="Pixel")

    assert response.status_code == 200
    assert response.json() == {"table_number": 7}
    scan = TableScan.objects.get()
    assert scan.table_id == table.pk
    assert scan.user_agent == "Pixel"


def test_a_scan_may_report_its_language(client) -> None:
    table = TableFactory()

    client.post(_scan_url(table), {"language": "ru"}, format="json")

    assert TableScan.objects.get().locale == "ru"


def test_an_unsupported_language_is_rejected(client) -> None:
    table = TableFactory()

    response = client.post(_scan_url(table), {"language": "de"}, format="json")

    assert response.status_code == 400
    assert not TableScan.objects.exists()


def test_an_unknown_token_is_a_404(client) -> None:
    response = client.post(reverse("tables:scan", args=[uuid.uuid4()]), {}, format="json")

    assert response.status_code == 404


def test_an_inactive_table_is_a_404(client) -> None:
    table = TableFactory(is_active=False)

    response = client.post(_scan_url(table), {}, format="json")

    assert response.status_code == 404
    assert not TableScan.objects.exists()


def test_scanning_is_rate_limited_per_token(client) -> None:
    table = TableFactory()
    url = _scan_url(table)

    statuses = [client.post(url, {}, format="json").status_code for _ in range(SCAN_RATE_LIMIT + 1)]

    assert statuses[:SCAN_RATE_LIMIT] == [200] * SCAN_RATE_LIMIT
    assert statuses[-1] == 429


def test_the_rate_limit_of_one_table_does_not_affect_another(client) -> None:
    busy = TableFactory()
    quiet = TableFactory()
    for _ in range(SCAN_RATE_LIMIT + 1):
        client.post(_scan_url(busy), {}, format="json")

    response = client.post(_scan_url(quiet), {}, format="json")

    assert response.status_code == 200


# --------------------------------------------------------------------------- admin


def test_staff_may_not_reach_the_table_admin(staff_client) -> None:
    assert staff_client.get(reverse("tables:admin-table-list")).status_code == 403


def test_an_administrator_can_create_a_table(admin_client) -> None:
    response = admin_client.post(
        reverse("tables:admin-table-list"), {"number": 7, "label": "Terrace 3"}, format="json"
    )

    assert response.status_code == 201
    body = response.json()
    assert body["number"] == 7
    assert body["scan_url"].endswith(f"/t/{body['token']}")


def test_the_token_cannot_be_set_by_a_client(admin_client) -> None:
    table = TableFactory()
    original = table.token

    admin_client.patch(
        reverse("tables:admin-table-detail", args=[table.pk]),
        {"token": str(uuid.uuid4())},
        format="json",
    )

    table.refresh_from_db()
    assert table.token == original


def test_an_administrator_can_deactivate_and_delete_a_table(admin_client) -> None:
    table = TableFactory()
    detail = reverse("tables:admin-table-detail", args=[table.pk])

    admin_client.patch(detail, {"is_active": False}, format="json")
    table.refresh_from_db()
    assert table.is_active is False

    assert admin_client.delete(detail).status_code == 204
    assert not Table.objects.filter(pk=table.pk).exists()


# --------------------------------------------------------------------------- QR


def test_the_qr_svg_encodes_the_scan_url(admin_client) -> None:
    table = TableFactory()

    response = admin_client.get(reverse("tables:admin-table-qr", args=[table.pk]))

    assert response.status_code == 200
    assert response["Content-Type"] == "image/svg+xml"
    assert response.content.startswith(b"<?xml")
    assert b"<svg" in response.content


def test_the_encoded_payload_is_the_public_site_url(settings) -> None:
    settings.FRONTEND_URL = "http://menu.test"
    table = TableFactory()

    assert scan_url(table) == f"{site_url()}/t/{table.token}"
    assert scan_url(table).endswith(f"/t/{table.token}")


def test_the_qr_svg_is_administrator_only(staff_client) -> None:
    table = TableFactory()

    assert staff_client.get(reverse("tables:admin-table-qr", args=[table.pk])).status_code == 403


def test_an_unknown_table_has_no_qr(admin_client) -> None:
    assert admin_client.get(reverse("tables:admin-table-qr", args=[9999])).status_code == 404


def test_the_sheet_is_a_pdf_covering_the_active_tables(admin_client) -> None:
    for number in range(1, 16):
        TableFactory(number=number)
    TableFactory(number=99, is_active=False)

    response = admin_client.get(reverse("tables:admin-table-qr-sheet"))

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
    # Twelve codes per A4 page, so fifteen active tables need two pages.
    assert response.content.count(b"/Type /Page\n") == 2


def test_an_empty_sheet_is_still_a_valid_pdf() -> None:
    assert qr_sheet_pdf([]).startswith(b"%PDF")


def test_two_tables_get_different_codes() -> None:
    first, second = TableFactory(), TableFactory()

    assert table_qr_svg(first) != table_qr_svg(second)
