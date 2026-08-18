"""Staff account roles."""

import pytest
from django.db import IntegrityError, transaction

from apps.accounts.factories import DEFAULT_TEST_PASSWORD, UserFactory
from apps.accounts.models import Role, User

pytestmark = pytest.mark.django_db


def test_a_new_account_is_staff_by_default() -> None:
    user = User.objects.create_user(username="new-hire", password=DEFAULT_TEST_PASSWORD)

    assert user.role == Role.STAFF
    assert user.is_admin_role is False


def test_the_admin_trait_produces_an_administrator() -> None:
    user = UserFactory(admin=True)

    assert user.role == Role.ADMIN
    assert user.is_admin_role is True


def test_the_factory_sets_a_usable_password() -> None:
    user = UserFactory()

    assert user.check_password(DEFAULT_TEST_PASSWORD)


def test_usernames_are_unique() -> None:
    UserFactory(username="duplicate")

    with pytest.raises(IntegrityError), transaction.atomic():
        UserFactory(username="duplicate")
