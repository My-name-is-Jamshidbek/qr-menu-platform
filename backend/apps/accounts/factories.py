"""Factories for staff accounts."""

import factory
from factory.django import DjangoModelFactory

from apps.accounts.models import Role, User

DEFAULT_TEST_PASSWORD = "test-password-123"


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"staff{n}")
    email = factory.LazyAttribute(lambda user: f"{user.username}@example.com")
    role = Role.STAFF
    is_staff = True
    # `Password` hashes at build time, so the account is usable without a second save.
    password = factory.django.Password(DEFAULT_TEST_PASSWORD)

    class Params:
        admin = factory.Trait(role=Role.ADMIN, is_superuser=True)
