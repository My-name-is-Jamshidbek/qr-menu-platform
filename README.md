<div align="center">

# QR Menu Platform

**A trilingual QR menu for a café in Tashkent, and the staff panel behind it.**

Guests scan the code on their table and read the menu in Uzbek, Russian or English.
Staff change a price from a browser and the public page reflects it in about two seconds —
no rebuild, no deploy.

[![CI](https://github.com/My-name-is-Jamshidbek/qr-menu-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/My-name-is-Jamshidbek/qr-menu-platform/actions/workflows/ci.yml)
![Tests](https://img.shields.io/badge/tests-289%20passing-3F7D5A)
![Coverage](https://img.shields.io/badge/backend%20coverage-92%25-3F7D5A)
![Next.js](https://img.shields.io/badge/Next.js-16-000000?logo=nextdotjs)
![Django](https://img.shields.io/badge/Django-5.2-092E20?logo=django)
![License](https://img.shields.io/badge/license-MIT-D4AF37)

</div>

![Public menu, desktop](screenshots/menu-desktop.png)

<table>
<tr>
<td width="50%"><img src="screenshots/menu-mobile.png" alt="Menu on a phone"></td>
<td width="50%"><img src="screenshots/admin-03-product-list.png" alt="Admin product list"></td>
</tr>
<tr>
<td align="center"><em>What a guest sees after scanning</em></td>
<td align="center"><em>What staff use to change it</em></td>
</tr>
</table>

---

## Why this repository exists

This is a **rewrite**, and the interesting part is what it replaced.

The original was one folder holding two half-finished frontends at once — a Vite React app
under `src/` and a Next.js app under `app/` — plus a nested duplicate of the whole project.
The two halves read **different Firestore collections** (`menu_items` and `menu`), so a dish
added in one was invisible in the other. The admin password was compared in client-side
JavaScript and a session was recorded as `localStorage.adminToken = "authenticated"`.
Every photo lived inside its database document as a base64 string: **11.2 MB of JSON for
86 dishes**, downloaded in full by a guest sitting at a table on café Wi-Fi.

[Legacy → rebuild](#legacy--rebuild) has the point-by-point account.

## Where to look first

If you are reviewing this and have five minutes, these are the files that carry the ideas:

| # | File | Why it is worth opening |
|---|---|---|
| 1 | [`frontend/src/app/api/auth/login/route.ts`](frontend/src/app/api/auth/login/route.ts) | The backend-for-frontend. Credentials are exchanged with Django server-side and the JWT pair goes into httpOnly cookies — the browser never holds a token, so an XSS bug cannot lift a session |
| 2 | [`backend/apps/menu/api/aggregate.py`](backend/apps/menu/api/aggregate.py) | The whole menu in one cached, N+1-free query, with a test that asserts the query count rather than trusting it |
| 3 | [`backend/apps/menu/legacy/quality.py`](backend/apps/menu/legacy/quality.py) | The migration refuses to launder bad data: rows are quarantined or flagged, with a reason, into a CSV a human reviews |
| 4 | [`backend/apps/menu/models.py`](backend/apps/menu/models.py) | Translations as rows with a unique `(object, language)` constraint — which is how "what is missing in Russian?" became a query instead of a guess |
| 5 | [`frontend/src/styles/tokens.css`](frontend/src/styles/tokens.css) | The palette. Gold is an accent on a warm near-black ground, never a page background |
| 6 | [`tests/e2e/test_admin_products.py`](tests/e2e/test_admin_products.py) | Selenium asserts the primary button is genuinely hittable — `elementFromPoint` must resolve to the button itself, because in the original it did not |

`/uz/styleguide` renders every component in every state, which is the fastest way to see the
design system without clicking through the app.

## Stack

| Layer | Choice | Why |
|---|---|---|
| Frontend | Next.js 16 App Router, React 19, TypeScript strict | Server Components let the menu ship as static HTML and the admin guard live on the server, not in the client bundle |
| Styling | Tailwind CSS 4 over CSS custom properties | One palette in `tokens.css`; no hex literal appears in a component |
| i18n | `next-intl`, always-prefixed `/uz` `/ru` `/en` | Each language is a distinct canonical URL, separately indexable |
| API | Django 5.2 + DRF | The admin surface is CRUD over a relational schema — ORM, migrations and constraints are the entire value |
| Types | `drf-spectacular` → OpenAPI 3.1 → `openapi-typescript` | Response types are generated. A backend field rename breaks `tsc`, not production |
| Database | Postgres 16 | Translations are rows, not JSON blobs |
| Cache | Redis 7 | Menu aggregate per language, 300 s TTL, dropped on every write |
| Images | Pillow → WebP at 400/800/1600 → S3-compatible storage | MinIO in development, Cloudflare R2 in production |
| Auth | SimpleJWT held server-side in httpOnly cookies | See file #1 above |
| Tests | pytest + factory_boy · `node:test` · **Selenium** | 289 tests total; the browser suite is Selenium by project rule |

## Numbers

Measured on this machine, not estimated.

| | Legacy | This rebuild |
|---|---|---|
| Menu payload, first load | 11.2 MB of JSON | **415 KB** desktop · 460 KB mobile |
| Menu API response | — | 56 KB for 105 dishes |
| Text on gold contrast | 2.10:1 — fails WCAG AA | **8.50:1** ink on gold · 17.52:1 cream on ground |
| Prerendered pages | 0 | 58, across three locales |
| Automated tests | 0 | **289** — 229 backend (92% lines), 24 frontend, 36 Selenium |

## Quickstart

```bash
git clone https://github.com/My-name-is-Jamshidbek/qr-menu-platform.git
cd qr-menu-platform
cp .env.example .env

# Postgres, Redis, MinIO, plus a one-shot job that creates the public bucket
docker compose up -d postgres redis minio minio-init

# API and web
docker compose up --build api web
```

Then populate it:

```bash
docker compose exec api python manage.py migrate
docker compose exec api python manage.py seed_demo
docker compose exec api python manage.py createsuperuser
```

| Service | URL |
|---|---|
| Menu | <http://localhost:3100> |
| Style guide | <http://localhost:3100/uz/styleguide> |
| Admin panel | <http://localhost:3100/uz/admin> |
| API + Swagger | <http://localhost:8100/api/schema/swagger-ui/> |
| MinIO console | <http://localhost:9101> |

Ports are deliberately offset (3100 / 8100 / 5434 / 6382 / 9100) so the stack coexists with
other projects on the same host.

`seed_demo` builds the category tree, **42 dishes**, generated WebP photos in the bucket, and
deliberately uneven translation coverage — because that is what the real data looked like, and
it is the only way the fallback rule and the panel's missing-translation counter are ever
exercised. It is idempotent; `--flush` rebuilds from scratch.

<details>
<summary><strong>Running the app services on the host instead</strong> (faster edit loop)</summary>

Keep the three infrastructure containers up and source `.env.hostdev`, which is `.env` with
host-reachable addresses.

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

</details>

<details>
<summary><strong>Running the checks</strong></summary>

```bash
# backend — 229 tests, 92% coverage
cd backend && set -a && source ../.env.hostdev && set +a
.venv/bin/python -m pytest -q --cov
.venv/bin/ruff check .

# frontend
cd frontend && set -a && source ../.env.hostdev && set +a
npm run typecheck                              # next typegen && tsc --noEmit
npm run lint
node --test "src/features/menu/"*.test.mjs     # 24 tests
npm run build                                  # prerenders 58 pages; needs the API up

# browser journey — 36 Selenium tests, needs the whole stack running
cd tests && python -m pytest -q
```

`npm run build` calls `generateStaticParams`, which fetches the live menu, so the API must be
reachable at `API_INTERNAL_URL` before you build.

</details>

## Migrating the real legacy data

The importer reads the old Firestore collection over its REST API, decodes each base64 photo,
converts it to WebP, and writes to Postgres. It is idempotent and refuses to launder bad rows.

```bash
python manage.py import_firestore --dry-run   # writes a verdict per document, touches nothing
python manage.py import_firestore
```

A dry run over the real collection reports:

```
read             86
importable       74
needs_review     10      6 category mismatch · 5 suspicious text · 2 duplicate document
quarantined      12      every one of them priced below the 100 UZS floor
```

The twelve rejects are real: dishes recorded at 5, 28 and 35 so'm. They land in
`backend/var/import_report.csv` with a reason instead of quietly reaching the menu. Rows
flagged `needs_review` are imported but held back with `is_available=False`, so a human
decides — for example the bread filed under *beverages*.

## Legacy → rebuild

| What the original did | Why it hurt | What replaced it |
|---|---|---|
| A Vite React app and a Next.js app in the same folder, plus a nested duplicate copy of both | Two build systems fought over one folder; nobody could say which file was live | One Next.js app. The panel is a route group inside it and both sides consume the same generated API types |
| Two divergent Firestore collections (`menu_items`, `menu`) for the same dishes | A dish added in the panel was invisible on the menu | One Postgres schema with foreign keys and unique constraints. There is no second copy to diverge from |
| Admin password compared in client JavaScript; `localStorage.adminToken = "authenticated"` | Anyone who opened DevTools was an administrator | Credentials are exchanged server-side for a JWT pair stored in httpOnly cookies. See [ARCHITECTURE](docs/ARCHITECTURE.md#the-bff-auth-model) |
| Photos as `data:image/jpeg;base64,…` inside each document | 11.2 MB of JSON for 86 dishes, on café Wi-Fi | WebP at three widths in object storage. The API returns a `srcset` and intrinsic dimensions, so the browser fetches one right-sized file and the grid never reflows |
| Prices stored as whole numbers but never validated — 5, 28, 35 so'm all present | Nonsense prices on a live menu | `PositiveIntegerField` with a database `CheckConstraint` at 100. The importer quarantined twelve documents rather than forcing them through |
| `#D4AF37` as the page background with white text on top | 2.10:1 contrast — fails WCAG AA outright | Gold as an accent on a warm near-black ground: 8.50:1 ink on gold, 17.52:1 cream on ground |
| The "add product" button sat underneath another element | The primary action silently did nothing when clicked | Every interactive element is a real link or form, and a Selenium test asserts `elementFromPoint` resolves to the button itself |
| Three language fields that were filled by copying the Uzbek text | 72 of 86 Russian names were byte-identical to the Uzbek and only 6 contained a single Cyrillic character — a trilingual menu that was never translated | Translations are rows with a unique `(object, language)` constraint. A missing string falls back to Uzbek and is marked `is_fallback` in the API; the panel reports the exact gaps per dish |

## Layout

```
backend/
  config/settings/      base · local · production; every secret from env, no fallback
  apps/common/          TimeStampedModel, translation fallback, WebP pipeline,
                        error handler, accent-folding search, revalidation ping
  apps/menu/            Category · Product · translations · images
    api/                public menu and product endpoints, admin CRUD, Redis layer
    legacy/             Firestore reader, category mapper, data-quality rules,
                        base64 image recovery, CSV report
    management/         import_firestore, seed_demo
  apps/tables/          Table · TableScan, QR SVG and printable A4 sheet
  apps/accounts/        custom User with ADMIN/STAFF roles, JWT endpoints
frontend/
  src/app/[locale]/     (public)/menu — statically generated; admin/ — dynamic
  src/app/api/auth/     login · refresh · logout — the only places a JWT is handled
  src/app/api/revalidate/   ISR webhook the API posts to after every write
  src/app/t/[token]/    QR landing: records the scan, sets the table cookie, redirects
  src/features/         menu · admin · tables — data access, logic and components per feature
  src/components/ui/    Button, Card, Dialog, … driven entirely by tokens
  src/i18n/             routing, per-request config, generated message catalog
  messages/{uz,ru,en}/  UI strings by namespace — nothing user-facing lives in a component
tests/e2e/              Selenium journey, page objects, screenshot-on-failure
docs/                   contracts, architecture, ADRs
```

## Container images

Every push to `main` publishes both images to the GitHub Container Registry:

```bash
docker pull ghcr.io/my-name-is-jamshidbek/qr-menu-platform/api:latest
docker pull ghcr.io/my-name-is-jamshidbek/qr-menu-platform/web:latest
```

Tags: `latest`, the short SHA, and the semver tag when one is pushed.

## Documentation

| Document | Contents |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Request flow, the BFF auth model, caching and ISR invalidation, image pipeline, i18n |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Numbered ADRs for the choices worth arguing about |
| [docs/DATA_MODEL.md](docs/DATA_MODEL.md) | Every table, field, index and deletion rule |
| [docs/API_CONTRACT.md](docs/API_CONTRACT.md) | Endpoints, payloads, error shape, throttles |
| [docs/DESIGN_SYSTEM.md](docs/DESIGN_SYSTEM.md) | Tokens, typography, component rules, contrast budget |
| [deploy/deploy.md](deploy/deploy.md) | Provisioning, first deploy, secret rotation, restore, rollback |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Conventions, workflow, definition of done |

## Credits and licence

Built as a portfolio rewrite of a real café menu. The dish photographs belong to the café;
`seed_demo` generates a complete stand-in dataset so the project runs without them.

MIT — see [LICENSE](LICENSE).
