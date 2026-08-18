"""The custom user model.

Defined up front — `AUTH_USER_MODEL` cannot be swapped after the first migration
without significant pain — so the rest of the schema can be built on top of it.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models


class Role(models.TextChoices):
    ADMIN = "ADMIN", "Administrator"
    STAFF = "STAFF", "Staff"


class User(AbstractUser):
    """Staff account. `STAFF` edits the menu; `ADMIN` also manages tables and users."""

    role = models.CharField(max_length=8, choices=Role.choices, default=Role.STAFF)

    class Meta(AbstractUser.Meta):
        swappable = "AUTH_USER_MODEL"

    @property
    def is_admin_role(self) -> bool:
        return self.role == Role.ADMIN
