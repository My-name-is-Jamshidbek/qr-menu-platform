# BOSS KAFE

A trilingual digital menu for a restaurant in Tashkent, and the staff panel behind it.
Guests scan the QR code on their table and get the menu in Uzbek, Russian or English;
staff edit prices, translations and photos from a browser and the public pages update in
about two seconds without a rebuild.

This is a rewrite. The original was a single-page React app that kept its data in
Firestore, its admin password in client-side JavaScript, and its photos as base64 blobs
inside the documents. Section [Legacy → rebuild](#legacy--rebuild) is a line-by-line
account of what was wrong and what replaced it.

![Public menu, desktop](screenshots/menu-desktop.png)

![Admin product list](screenshots/admin-03-product-list.png)

## Stack

| Layer | Choice | Why |
|---|---|---|
| Frontend | Next.js 16, App Router, React 19, TypeScript strict | Server Components mean the menu ships as static HTML and the admin panel needs no client-side auth guard at all |
| Styling | Tailwind CSS 4 with CSS custom properties | Tokens in `src/styles/tokens.css`, one source of truth for the palette; no hex literal appears in a component |
| i18n | `next-intl`, three locales, always-prefixed URLs | `/uz`, `/ru`, `/en` are distinct canonical URLs, so each language is separately indexable |
| API | Django 5.2 + DRF, Python 3.12+ | The admin surface is 80% CRUD over a relational schema — the ORM, migrations and admin are the whole point |
| Schema | `drf-spectacular` → OpenAPI 3.1 → `openapi-typescript` | Frontend response types are generated, never hand-written; a backend field rename breaks `tsc`, not production |
| Database | Postgres 16 | Translations are rows, not JSON — "which products have no Russian name?" is one query with an index behind it |
| Cache | Redis 7 | Menu aggregate per language, 300s TTL, dropped on every write |
| Images | Pillow → WebP at 400/800/1600 → S3-compatible storage (MinIO in dev, Cloudflare R2 in production) | Photos belong in object storage, not in database rows |
| Auth | SimpleJWT, tokens held server-side in httpOnly cookies | No token ever reaches the document, so an XSS bug cannot steal a session |
| Tests | pytest + factory_boy (229 tests, 92% line coverage), `node:test` for frontend logic, Selenium for the browser journey | |

## Quickstart

The whole stack runs in Docker. From a clean clone:

```bash
git clone <repo> boss-kafe && cd boss-kafe
cp .env.example .env

# Postgres, Redis, MinIO, and a one-shot job that creates the public bucket
docker compose up -d postgres redis minio minio-init

# API and web
docker compose up --build api web
```

Open <http://localhost:3100>. The API is on <http://localhost:8100>, its Swagger UI on
<http://localhost:8100/api/schema/swagger-ui/>, and the MinIO console on
<http://localhost:9101>.

Ports are deliberately offset (3100 / 8100 / 5434 / 6382 / 9100) so the stack coexists
with other projects on the same host.

### Populate the database

```bash
docker compose exec api python manage.py migrate
docker compose exec api python manage.py seed_demo
docker compose exec api python manage.py createsuperuser
```

`seed_demo` builds the real category tree, 42 dishes, generated WebP photos in the
bucket, and deliberately uneven translation coverage — half the dishes have no Russian
or English name, because that is what the production data looks like and it is the only
way the fallback rule and the panel's "missing translations" counter are ever exercised.
It is idempotent; `--flush` rebuilds from scratch.

To migrate the real legacy data instead, set `FIRESTORE_PROJECT_ID` and run
`python manage.py import_firestore --dry-run` first — it writes a verdict for every
document to `backend/var/import_report.csv` without touching the database.

### Running the app services on the host instead

Useful when you want a fast edit loop. Keep the three infrastructure containers up and
source `.env.hostdev`, which is `.env` with host-reachable addresses.

```bash
set -a; source .env.hostdev; set +a

cd backend
python -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver 127.0.0.1:8100

cd ../frontend
npm ci
npm run dev -- -p 3100
```

### Checks

```bash
# backend — 229 tests, 92% coverage
cd backend && set -a && source ../.env.hostdev && set +a
.venv/bin/python -m pytest -q
.venv/bin/python -m pytest -q --cov
.venv/bin/python -m ruff check .

# frontend
cd frontend && set -a && source ../.env.hostdev && set +a
npm run typecheck                        # next typegen && tsc --noEmit
npm run lint
node --test "src/features/menu/*.test.mjs"   # 24 tests
npm run build                            # prerenders 58 pages; needs the API running
```

`npm run build` calls `generateStaticParams`, which fetches the live menu, so the API
must be reachable at `API_INTERNAL_URL` before you build.

## Project layout

```
backend/
  config/settings/      base · local · production; every secret read from env, no fallback
  apps/common/          TimeStampedModel, translation fallback, WebP pipeline,
                        error handler, accent-folding search, revalidation ping
  apps/menu/            Category · Product · translations · images
    api/                public menu + product endpoints, admin CRUD, Redis layer
    legacy/             Firestore reader, category mapper, data-quality rules,
                        base64 image recovery, CSV report
    management/         import_firestore, seed_demo
  apps/tables/          Table · TableScan, QR SVG and printable A4 sheet
  apps/accounts/        custom User with ADMIN/STAFF roles, JWT endpoints
frontend/
  src/app/[locale]/     (public)/menu — statically generated; admin/ — dynamic
  src/app/api/auth/     login · refresh · logout — the only places a JWT is handled
  src/app/api/revalidate/  ISR webhook the API posts to
  src/app/t/[token]/    QR landing: records the scan, sets the table cookie, redirects
  src/features/         menu · admin · tables — data access, logic, components per feature
  src/components/ui/    Button, Card, Dialog, … driven entirely by tokens
  src/i18n/             routing, per-request config, generated message catalog
  messages/{uz,ru,en}/  UI strings by namespace — nothing user-facing lives in a component
docs/                   contracts (data model, API, design system) + architecture, ADRs
screenshots/            captures from the Selenium journey
```

`/uz/styleguide` renders every component in every state — the fastest way to see the
design system without clicking through the app.

## Legacy → rebuild

| What the original did | Why it hurt | What replaced it |
|---|---|---|
| Two separate React apps (`BOSS_menu`, `BOSS_admin`) in one folder, sharing nothing but a Firebase config | Every schema change had to be made twice and drifted immediately | One Next.js app; the panel is a route group inside it, and both sides read the same generated API types |
| Two divergent Firestore collections for the same dishes | The menu and the admin listed different prices for the same food | One Postgres schema. Products, categories and translations are rows with foreign keys and unique constraints; there is no second copy to diverge from |
| Admin password compared in client JavaScript, session marked with `localStorage.adminToken = "authenticated"` | Anyone who opened DevTools was an administrator | Credentials are posted to a Next.js route handler, exchanged with Django for a JWT pair, and stored in httpOnly cookies the browser cannot read. Every admin request is made server-side. See [ARCHITECTURE](docs/ARCHITECTURE.md#the-bff-auth-model) |
| Photos as `data:image/jpeg;base64,…` inside each document | ~15 MB of JSON for 86 dishes; the menu was unusable on a phone at a table | Uploads go to object storage as WebP at three widths; the API returns a `srcset` and intrinsic dimensions, so the browser fetches one appropriately-sized file and the grid never reflows |
| Prices as floats, some of them wrong (`5`, `28`) | Rounding artefacts, and nonsense prices nobody caught | `PositiveIntegerField` of whole UZS with a database `CheckConstraint` at 100. The migration quarantined 12 documents and flagged 13 more for review in `backend/var/import_report.csv` rather than forcing them through |
| `#D4AF37` as the page background, white text on top | ≈2.0:1 contrast — fails WCAG AA outright | Gold is an accent on a warm near-black ground; ink on gold, cream or gold-300 on dark, all ≥ 8:1 |
| The primary "add to order" button had no handler | The main call to action did nothing | Every interactive element is a real link, form or Server Action. The product card is deliberately *not* clickable, because there is no detail page for it to go to |
| Translations that existed only in Uzbek, silently blank elsewhere | 74 products had no Russian or English name and nobody knew | Translations are a table with a unique `(object, language)` constraint. A missing string falls back to Uzbek and is flagged `is_fallback` in the API; the panel shows the exact gaps per product |

## Documentation

| Document | Contents |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Request flow, the BFF auth model, caching and ISR invalidation, image pipeline, i18n |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Numbered ADRs for the choices worth arguing about |
| [docs/DATA_MODEL.md](docs/DATA_MODEL.md) | Every table, field, index and deletion rule |
| [docs/API_CONTRACT.md](docs/API_CONTRACT.md) | Endpoints, payloads, error shape, throttles |
| [docs/DESIGN_SYSTEM.md](docs/DESIGN_SYSTEM.md) | Tokens, typography, component rules, contrast budget |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Conventions, workflow, definition of done |
