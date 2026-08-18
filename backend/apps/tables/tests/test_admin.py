"""The tables admin surfaces scan activity and keeps the scan log read-only."""

import pytest
from django.contrib import admin
from django.urls import reverse

from apps.accounts.factories import DEFAULT_TEST_PASSWORD, UserFactory
from apps.tables.factories import TableFactory, TableScanFactory
from apps.tables.models import Table, TableScan

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_client_logged_in(client):
    UserFactory(username="table-admin", admin=True, is_staff=True)
    client.login(username="table-admin", password=DEFAULT_TEST_PASSWORD)
    return client


def test_the_table_list_counts_scans(admin_client_logged_in) -> None:
    table = TableFactory()
    TableScanFactory(table=table)
    TableScanFactory(table=table)

    response = admin_client_logged_in.get(reverse("admin:tables_table_changelist"))
    row = response.context["cl"].result_list.get(pk=table.pk)

    assert response.status_code == 200
    assert admin.site._registry[Table].scan_count(row) == 2


def test_scans_cannot_be_created_or_edited_by_hand(rf) -> None:
    scan_admin = admin.site._registry[TableScan]
    request = rf.get("/")

    assert scan_admin.has_add_permission(request) is False
    assert scan_admin.has_change_permission(request) is False
