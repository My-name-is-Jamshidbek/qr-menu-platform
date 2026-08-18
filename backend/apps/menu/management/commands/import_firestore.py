"""One-off migration of the legacy Firestore menu into the Postgres schema.

Usage:

    python manage.py import_firestore --dry-run          # read, judge, report only
    python manage.py import_firestore                    # write
    python manage.py import_firestore --limit 10         # first N documents
    python manage.py import_firestore --source dump.json # replay a saved response

The command is safe to run repeatedly: each product is anchored to its Firestore
document id (see `apps.menu.legacy.identity`), so a second run updates in place
rather than duplicating. Rows that cannot become a valid product are quarantined and
written to `backend/var/import_report.csv` instead of being forced through.
"""

from argparse import ArgumentParser
from pathlib import Path
from typing import Any

from decouple import config
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.common.enums import Language
from apps.menu.legacy.categories import CategoryPlan, CategoryWriter, UnknownCategory, plan_for
from apps.menu.legacy.firestore import (
    FirestoreCollection,
    FirestoreError,
    LegacyDocument,
    load_documents,
)
from apps.menu.legacy.identity import legacy_key, legacy_slug
from apps.menu.legacy.images import LegacyImageError, decode_image
from apps.menu.legacy.quality import (
    Issue,
    Reason,
    Status,
    TranslationDraft,
    build_translations,
    category_issues,
    comparison_key,
    normalize,
    price_issues,
)
from apps.menu.legacy.report import ImportReport
from apps.menu.models import Product, ProductImage, ProductTranslation

DEFAULT_REPORT_PATH = Path(settings.BASE_DIR) / "var" / "import_report.csv"

READ = "read"
IMPORTED = "imported"
UPDATED = "updated"
IMPORTABLE = "importable"
NEEDS_REVIEW = "needs_review"
QUARANTINED = "quarantined"
OUTCOME_ORDER = [READ, IMPORTED, UPDATED, IMPORTABLE, NEEDS_REVIEW, QUARANTINED]


class Row:
    """A legacy document after parsing, judging and slug assignment.

    Holding the verdict on the instance keeps the write phase free of validation:
    by the time a `Row` reaches the database it is known to be importable.
    """

    __slots__ = (
        "document",
        "issues",
        "name_uz",
        "category",
        "subcategory",
        "price",
        "plan",
        "translations",
        "image",
        "slug",
    )

    def __init__(self, document: LegacyDocument) -> None:
        self.document = document
        self.issues: list[Issue] = []
        self.name_uz: str = ""
        self.category: str | None = None
        self.subcategory: str | None = None
        self.price: int | None = None
        self.plan: CategoryPlan | None = None
        self.translations: list[TranslationDraft] = []
        self.image: bytes | None = None
        self.slug: str = ""

    @property
    def legacy_id(self) -> str:
        return self.document.id

    @property
    def quarantined(self) -> bool:
        return any(issue.status is Status.QUARANTINED for issue in self.issues)

    @property
    def needs_review(self) -> bool:
        return any(issue.status is Status.NEEDS_REVIEW for issue in self.issues)


class Command(BaseCommand):
    help = "Import the legacy Firestore menu, quarantining rows that fail validation."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Read and validate everything, write nothing (the report is still produced).",
        )
        parser.add_argument("--limit", type=int, help="Process at most N documents.")
        parser.add_argument(
            "--source",
            type=Path,
            help="Read a saved Firestore JSON response instead of calling the API.",
        )
        parser.add_argument("--page-size", type=int, default=50, help="Documents per API page.")
        parser.add_argument(
            "--report",
            type=Path,
            default=DEFAULT_REPORT_PATH,
            help=f"Where to write the CSV report (default: {DEFAULT_REPORT_PATH}).",
        )
        parser.add_argument(
            "--project",
            default=config("FIRESTORE_PROJECT_ID", default="orginal-boss-kafe"),
            help="Firestore project id.",
        )
        parser.add_argument(
            "--collection",
            default=config("FIRESTORE_COLLECTION", default="menu_items"),
            help="Firestore collection name.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        dry_run: bool = options["dry_run"]
        report = ImportReport()

        rows = self._read(options, report)
        if dry_run:
            report.tally(IMPORTABLE, len(rows))
            self.stdout.write(self.style.WARNING("Dry run: nothing was written."))
        else:
            self._write(rows, report)

        path = report.write_csv(options["report"])
        self._print_summary(report, path)

    # ------------------------------------------------------------------ read phase

    def _read(self, options: dict[str, Any], report: ImportReport) -> list[Row]:
        """Fetch, decode and judge every document. No database access happens here."""
        rows: list[Row] = []
        seen: dict[tuple[str, str], str] = {}

        for document in self._documents(options):
            row = self._judge(document)

            # The export holds the same dish twice under different ids ("Original
            # Asarti", "Sirniy palichka"). Both are imported — one may be the newer
            # price — but the later one is flagged so a human picks a winner.
            identity = (comparison_key(row.name_uz), row.category or "")
            previous = seen.setdefault(identity, row.legacy_id)
            if previous != row.legacy_id:
                row.issues.append(
                    Issue(
                        Status.NEEDS_REVIEW,
                        Reason.DUPLICATE_DOCUMENT,
                        f"same name and category as document {previous}",
                    )
                )

            report.tally(READ)
            report.record(
                legacy_id=row.legacy_id,
                name_uz=row.name_uz,
                category=row.category,
                subcategory=row.subcategory,
                price=row.price,
                issues=row.issues,
            )
            if row.quarantined:
                report.tally(QUARANTINED)
                continue
            if row.needs_review:
                report.tally(NEEDS_REVIEW)
            rows.append(row)

        return rows

    def _documents(self, options: dict[str, Any]):
        source: Path | None = options["source"]
        limit: int | None = options["limit"]

        try:
            if source is not None:
                documents = iter(load_documents(source))
            else:
                collection = FirestoreCollection(
                    options["project"], options["collection"], page_size=options["page_size"]
                )
                self.stdout.write(f"Reading {collection.url}")
                documents = iter(collection)

            for index, document in enumerate(documents):
                if limit is not None and index >= limit:
                    return
                yield document
        except FirestoreError as exc:
            raise CommandError(str(exc)) from exc

    def _judge(self, document: LegacyDocument) -> Row:
        """Apply every data-quality rule to one document."""
        row = Row(document)
        names = document.text_map("name")
        descriptions = document.text_map("info")

        row.name_uz = normalize(names.get(Language.UZ))
        row.category = document.string("category")
        row.subcategory = document.string("subcategory")
        row.price = document.integer("price")
        row.slug = legacy_slug(document.id, row.name_uz)

        if not row.name_uz:
            row.issues.append(Issue(Status.QUARANTINED, Reason.MISSING_UZ_NAME, "name.uz is empty"))
        else:
            row.translations, translation_issues = build_translations(names, descriptions)
            row.issues.extend(translation_issues)

        row.issues.extend(price_issues(row.price))

        try:
            row.plan = plan_for(row.category, row.subcategory)
        except UnknownCategory:
            row.issues.append(
                Issue(
                    Status.QUARANTINED,
                    Reason.UNKNOWN_CATEGORY,
                    f"no mapping for category {row.category!r}",
                )
            )
        else:
            if row.plan.unknown_subcategory:
                row.issues.append(
                    Issue(
                        Status.NEEDS_REVIEW,
                        Reason.UNKNOWN_SUBCATEGORY,
                        f"{row.plan.unknown_subcategory!r} filed on the parent section",
                    )
                )
            row.issues.extend(category_issues(row.name_uz, row.category or "", row.subcategory))

        try:
            row.image, _ = decode_image(document.string("image"))
        except LegacyImageError as exc:
            row.issues.append(Issue(Status.QUARANTINED, Reason.INVALID_IMAGE, str(exc)))

        return row

    # ----------------------------------------------------------------- write phase

    def _write(self, rows: list[Row], report: ImportReport) -> None:
        categories = CategoryWriter()
        order: dict[int, int] = {}

        for row in rows:
            # `_judge` quarantines any row with an unmapped category or unusable
            # image, so everything reaching here has both.
            category = categories.ensure(row.plan)
            order[category.pk] = order.get(category.pk, 0) + 1

            created = self._save(row, category.pk, order[category.pk])
            report.tally(IMPORTED if created else UPDATED)
            self.stdout.write(f"  {'+' if created else '~'} {row.slug}")

    @transaction.atomic
    def _save(self, row: Row, category_id: int, order: int) -> bool:
        """Create or refresh one product. Returns True when it was newly created."""
        key = legacy_key(row.legacy_id)
        product = Product.objects.filter(slug__endswith=f"-{key}").first()
        created = product is None
        # An existing product keeps its slug even if the dish was renamed upstream:
        # the old URL is already printed on QR-linked pages and in search results.

        if product is None:
            product = Product(slug=row.slug, is_available=not row.needs_review)
        elif row.needs_review:
            # Re-flagging is safe; clearing the flag is not, because staff may have
            # hidden the product for an unrelated reason such as it being sold out.
            product.is_available = False

        product.category_id = category_id
        product.price = row.price
        product.order = order
        product.save()

        self._sync_translations(product, row.translations)
        if created:
            self._attach_image(product, row)
        return created

    @staticmethod
    def _sync_translations(product: Product, drafts: list[TranslationDraft]) -> None:
        """Make the stored translations match the drafts exactly.

        Languages that lost their content upstream have their row deleted, so the
        "which products lack Russian?" query keeps telling the truth.
        """
        existing = {t.language: t for t in product.translations.all()}
        for draft in drafts:
            translation = existing.pop(draft.language, None)
            if translation is None:
                ProductTranslation.objects.create(
                    product=product,
                    language=draft.language,
                    name=draft.name,
                    description=draft.description,
                )
            elif (translation.name, translation.description) != (draft.name, draft.description):
                translation.name = draft.name
                translation.description = draft.description
                translation.save(update_fields=["name", "description", "updated_at"])

        for orphan in existing.values():
            orphan.delete()

    @staticmethod
    def _attach_image(product: Product, row: Row) -> None:
        """Store the recovered photo; `ProductImage.save()` builds the WebP variants."""
        ProductImage(
            product=product,
            image=ContentFile(row.image, name=f"{legacy_key(row.legacy_id)}.jpg"),
            is_primary=True,
            order=0,
        ).save()

    # --------------------------------------------------------------------- output

    def _print_summary(self, report: ImportReport, path: Path) -> None:
        self.stdout.write("")
        self.stdout.write(report.summary_table(OUTCOME_ORDER))
        self.stdout.write("")
        self.stdout.write(report.reason_table())
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"Report written to {path}"))
