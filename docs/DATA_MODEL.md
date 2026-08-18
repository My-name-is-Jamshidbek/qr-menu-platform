# Data Model

Postgres 16 via Django 5 ORM. Three Django apps: `menu`, `tables`, `accounts`.

All models inherit `TimeStampedModel` (`created_at`, `updated_at`, both `auto_now*`).

## Language

```python
class Language(models.TextChoices):
    UZ = "uz", "O'zbekcha"
    RU = "ru", "Русский"
    EN = "en", "English"
```

`uz` is the fallback: if a translation is missing for the requested language, the API
serves the `uz` value and sets `"is_fallback": true` on that field's parent object.

## menu

### Category

Self-referencing tree, one level deep (parent = section, child = subsection).
The original data had a flat `category` + `subcategory` pair; this replaces it.

| field | type | notes |
|---|---|---|
| `id` | BigAuto | |
| `parent` | FK self, null, `related_name="children"` | null → top-level |
| `slug` | Slug, unique | URL segment, e.g. `desserts` |
| `order` | PositiveSmallInt, default 0 | manual sort |
| `is_active` | Bool, default True | hidden from public API when False |

`Meta.ordering = ["order", "id"]`.
`clean()` forbids depth > 2 (a child may not itself have children).

### CategoryTranslation

| field | type | notes |
|---|---|---|
| `category` | FK Category, `related_name="translations"` | |
| `language` | CharField(2), choices=Language | |
| `name` | CharField(120) | |

`UniqueConstraint(fields=["category", "language"])`.

### Product

| field | type | notes |
|---|---|---|
| `category` | FK Category, PROTECT, `related_name="products"` | |
| `slug` | Slug, unique | |
| `price` | PositiveIntegerField | **UZS so'm, integer.** UZS has no practical minor unit; integers avoid float error entirely. `MinValueValidator(100)` — the legacy data contains "5 so'm" rows that must not survive migration |
| `is_available` | Bool, default True | sold out → hidden from public list |
| `order` | PositiveSmallInt, default 0 | |

`Meta.ordering = ["order", "id"]`.

### ProductTranslation

| field | type | notes |
|---|---|---|
| `product` | FK Product, `related_name="translations"` | |
| `language` | CharField(2), choices=Language | |
| `name` | CharField(160) | |
| `description` | TextField, blank | |

`UniqueConstraint(fields=["product", "language"])`.

A dedicated table rather than a JSONField, so that "which products lack a Russian name?" is one
ORM query. The legacy data has ~74 products with no `ru`/`en` name and nobody noticed — the admin
UI surfaces this count.

### ProductImage

| field | type | notes |
|---|---|---|
| `product` | FK Product, `related_name="images"` | |
| `image` | ImageField, upload_to `products/%Y/%m/` | stored on S3/MinIO via django-storages |
| `alt` | CharField(200), blank | falls back to the product's translated name |
| `order` | PositiveSmallInt, default 0 | |
| `is_primary` | Bool, default False | |
| `width`, `height` | PositiveInt | filled on save; lets the frontend reserve space (no CLS) |

`UniqueConstraint(fields=["product"], condition=Q(is_primary=True), name="one_primary_image")`.

On save, the original upload is converted to **WebP** at three widths (400 / 800 / 1600) with
Pillow. The DB stores the base key; the API returns a `srcset`-ready dict. Uploads are capped at
8 MB and validated as real images (content sniffing, not just extension).

## tables

### Table

| field | type | notes |
|---|---|---|
| `number` | PositiveSmallInt, unique | as printed on the table |
| `token` | UUIDField, unique, default uuid4, db_index | goes in the QR code — not guessable, so table numbers cannot be enumerated |
| `label` | CharField(60), blank | e.g. "Terrace 3" |
| `is_active` | Bool, default True | |

QR encodes `https://<host>/t/<token>`. That route sets a `table` cookie and redirects to the menu,
which is what a future ordering feature will read.

### TableScan

Append-only analytics row: `table` FK, `scanned_at`, `user_agent` (truncated 200), `locale`.
No IP address is stored.

## accounts

`User` = `AbstractUser` subclass (created up front — swapping later is painful), plus:

| field | type | notes |
|---|---|---|
| `role` | CharField, choices `ADMIN` / `STAFF`, default `STAFF` | `STAFF` may edit products; `ADMIN` may also manage tables and users |

Authentication is JWT (`djangorestframework-simplejwt`). Tokens never reach the browser —
Next.js holds them in httpOnly cookies and calls the API server-side.

## Indexes

- `Product`: `(category, order)`, `(is_available,)`
- `ProductTranslation`: `(language, name)` — powers search
- `Category`: `(parent, order)`
- `Table`: `token` (unique already implies it)

## Deletion

`Category` → `PROTECT` (a category with products cannot be deleted).
`Product` → images cascade; the storage objects are removed by a post-delete signal.
Products are hard-deleted; `is_available=False` is the soft-hide path staff actually use.
