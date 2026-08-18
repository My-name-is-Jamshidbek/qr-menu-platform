"""Physical tables and the QR scans that point at them."""

import uuid

from django.db import models

from apps.common.models import TimeStampedModel

USER_AGENT_MAX_LENGTH = 200


class Table(TimeStampedModel):
    """One table in the cafe, addressed in QR codes by an unguessable token.

    The QR encodes the token rather than the table number: numbers are sequential and
    would let anyone enumerate every table (and, later, order against them).
    """

    number = models.PositiveSmallIntegerField(unique=True)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    label = models.CharField(max_length=60, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["number"]

    def __str__(self) -> str:
        return self.label or f"Table {self.number}"

    def scan_path(self) -> str:
        """Path the QR code resolves to, relative to the public site root."""
        return f"/t/{self.token}"


class TableScan(models.Model):
    """Append-only record of one QR scan.

    Deliberately not a `TimeStampedModel`: rows are never updated, so an `updated_at`
    column would only ever repeat `scanned_at`. No IP address is stored — the analytics
    question is "how busy is this table", which needs no identifier of the guest.
    """

    table = models.ForeignKey(Table, on_delete=models.CASCADE, related_name="scans")
    scanned_at = models.DateTimeField(auto_now_add=True, db_index=True)
    user_agent = models.CharField(max_length=USER_AGENT_MAX_LENGTH, blank=True)
    locale = models.CharField(max_length=2, blank=True)

    class Meta:
        ordering = ["-scanned_at"]
        indexes = [models.Index(fields=["table", "-scanned_at"], name="scan_table_recent_idx")]

    def __str__(self) -> str:
        when = f"{self.scanned_at:%Y-%m-%d %H:%M}" if self.scanned_at else "pending"
        return f"scan of table {self.table_id} at {when}"

    def save(self, *args, **kwargs):
        # Browsers send arbitrarily long UA strings; truncate rather than reject, the
        # value is only ever read as a rough client breakdown.
        self.user_agent = self.user_agent[:USER_AGENT_MAX_LENGTH]
        return super().save(*args, **kwargs)
