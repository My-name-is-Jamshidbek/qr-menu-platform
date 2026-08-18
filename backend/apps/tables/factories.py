"""Factories for tables and scan records."""

import factory
from factory.django import DjangoModelFactory

from apps.common.enums import Language
from apps.tables.models import Table, TableScan


class TableFactory(DjangoModelFactory):
    class Meta:
        model = Table

    number = factory.Sequence(lambda n: n + 1)
    label = factory.LazyAttribute(lambda table: f"Table {table.number}")
    is_active = True


class TableScanFactory(DjangoModelFactory):
    class Meta:
        model = TableScan

    table = factory.SubFactory(TableFactory)
    user_agent = "Mozilla/5.0 (test agent)"
    locale = Language.UZ
