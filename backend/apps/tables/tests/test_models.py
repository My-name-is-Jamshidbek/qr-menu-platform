"""Tables, their QR tokens and the scan log."""

import uuid

import pytest
from django.db import IntegrityError, transaction

from apps.tables.factories import TableFactory, TableScanFactory
from apps.tables.models import USER_AGENT_MAX_LENGTH, Table, TableScan

pytestmark = pytest.mark.django_db


def test_every_table_gets_a_unique_random_token() -> None:
    first = TableFactory()
    second = TableFactory()

    assert isinstance(first.token, uuid.UUID)
    assert first.token != second.token


def test_table_numbers_are_unique() -> None:
    TableFactory(number=7)

    with pytest.raises(IntegrityError), transaction.atomic():
        TableFactory(number=7)


def test_the_qr_path_carries_the_token_and_never_the_number() -> None:
    table = TableFactory(number=7)

    path = table.scan_path()

    assert path == f"/t/{table.token}"
    # The number never appears as the addressable segment, so tables cannot be enumerated.
    assert path.rsplit("/", 1)[-1] == str(table.token)


def test_a_table_without_a_label_is_named_by_its_number() -> None:
    table = TableFactory(number=3, label="")

    assert str(table) == "Table 3"


def test_scans_are_recorded_against_the_table() -> None:
    table = TableFactory()

    TableScanFactory(table=table)
    TableScanFactory(table=table)

    assert table.scans.count() == 2
    assert TableScan.objects.latest("scanned_at").table == table


def test_an_oversized_user_agent_is_truncated_rather_than_rejected() -> None:
    scan = TableScanFactory(user_agent="x" * 500)

    assert len(scan.user_agent) == USER_AGENT_MAX_LENGTH
    assert TableScan.objects.get(pk=scan.pk).user_agent == "x" * USER_AGENT_MAX_LENGTH


def test_deleting_a_table_removes_its_scans() -> None:
    scan = TableScanFactory()

    scan.table.delete()

    assert TableScan.objects.count() == 0
    assert Table.objects.count() == 0


def test_tables_are_listed_in_printed_number_order() -> None:
    second = TableFactory(number=12)
    first = TableFactory(number=2)

    assert list(Table.objects.all()) == [first, second]
