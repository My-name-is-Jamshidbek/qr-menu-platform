"""CSV audit trail and terminal summary for a migration run.

A migration that silently drops a dozen rows is worse than one that fails, so every
row the import refuses or distrusts is written out with the values it was judged on.
The file is meant to be opened in a spreadsheet and worked through by hand.
"""

import csv
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path

from apps.menu.legacy.quality import Issue, Status

COLUMNS = (
    "legacy_id",
    "status",
    "reason",
    "name_uz",
    "category",
    "subcategory",
    "price",
    "detail",
)


@dataclass(frozen=True, slots=True)
class ReportRow:
    legacy_id: str
    status: str
    reason: str
    name_uz: str
    category: str
    subcategory: str
    price: str
    detail: str


@dataclass
class ImportReport:
    """Counters plus the rejected/suspicious rows of one run."""

    rows: list[ReportRow] = field(default_factory=list)
    counts: Counter[str] = field(default_factory=Counter)

    def record(
        self,
        *,
        legacy_id: str,
        name_uz: str,
        category: str | None,
        subcategory: str | None,
        price: int | None,
        issues: list[Issue],
    ) -> None:
        """Write one report line per issue raised against a row."""
        for issue in issues:
            self.rows.append(
                ReportRow(
                    legacy_id=legacy_id,
                    status=str(issue.status),
                    reason=str(issue.reason),
                    name_uz=name_uz,
                    category=category or "",
                    subcategory=subcategory or "",
                    price="" if price is None else str(price),
                    detail=issue.detail,
                )
            )

    def tally(self, key: str, amount: int = 1) -> None:
        self.counts[key] += amount

    @property
    def reason_counts(self) -> Counter[str]:
        return Counter(f"{row.status}/{row.reason}" for row in self.rows)

    def write_csv(self, path: Path) -> Path:
        """Write the report, creating `backend/var/` on first use."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerows(asdict(row) for row in sorted(self.rows, key=_sort_key))
        return path

    def summary_table(self, order: list[str]) -> str:
        """Fixed-width outcome table for the command's stdout."""
        labels = [*order, *sorted(set(self.counts) - set(order))]
        width = max((len(label) for label in labels), default=0)
        rule = "-" * (width + 9)
        lines = [rule, f"{'outcome'.ljust(width)}  {'count':>5}", rule]
        lines += [f"{label.ljust(width)}  {self.counts[label]:>5}" for label in labels]
        lines.append(rule)
        return "\n".join(lines)

    def reason_table(self) -> str:
        """Breakdown of the CSV contents by status and reason."""
        reasons = self.reason_counts
        if not reasons:
            return "No rows were rejected or flagged."
        width = max(len(label) for label in reasons)
        return "\n".join(
            f"{label.ljust(width)}  {count:>5}" for label, count in sorted(reasons.items())
        )


def _sort_key(row: ReportRow) -> tuple[int, str, str]:
    # Quarantined rows first: they are the ones somebody has to re-enter by hand.
    return (0 if row.status == Status.QUARANTINED else 1, row.reason, row.name_uz)
