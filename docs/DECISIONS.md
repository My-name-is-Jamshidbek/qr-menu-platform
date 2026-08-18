# Architecture decision records

One record per choice that was genuinely contested and would be expensive to reverse.
Each states what was decided, what it costs, and what would make it wrong.

| # | Decision | Status |
|---|---|---|
| [001](#adr-001-two-services-next-for-delivery-django-for-data) | Two services: Next.js for delivery, Django for data | Accepted |
| [002](#adr-002-translation-tables-not-a-jsonb-column) | Translation tables, not a JSONB column | Accepted |
| [003](#adr-003-prices-as-integer-uzs) | Prices as integer UZS | Accepted |
| [004](#adr-004-jwt-in-httponly-cookies-behind-a-bff) | JWT in httpOnly cookies behind a BFF | Accepted |
| [005](#adr-005-object-storage-for-images-not-base64-in-the-row) | Object storage for images, not base64 in the row | Accepted |
| [006](#adr-006-selenium-for-end-to-end-coverage) | Selenium for end-to-end coverage | Accepted |
| [007](#adr-007-generated-api-types-instead-of-hand-written-ones) | Generated API types instead of hand-written ones | Accepted |

---

## ADR-001: Two services, Next for delivery, Django for data

**Context.** The legacy system was two React SPAs — `BOSS_menu` and `BOSS_admin` — sitting
in one folder, sharing a Firebase config and nothing else. Every schema change had to be
made twice, and immediately drifted. The obvious corrections were either "one Next.js app
with route handlers and an ORM" or "one Django app rendering templates".

**Decision.** Next.js owns delivery — routing, rendering, caching, i18n, sessions. Django
owns data — schema, migrations, validation, permissions, the image pipeline, the legacy
import. They meet at one versioned HTTP contract, `/api/v1/`, published as OpenAPI.

**Why not one Next.js app.** The admin panel is roughly 80% CRUD over a relational schema
with per-role permissions and a nasty one-off data migration. Django's ORM, migrations,
DRF serializers and management commands cover all of that out of the box; reproducing them
on top of an ORM like Prisma is weeks of work to arrive somewhere worse. `import_firestore`
alone — reader, category mapper, data-quality rules, base64 image recovery, CSV report,
re-runnable — is exactly the shape of a Django management command.

**Why not one Django app.** The public menu has to be fast on a phone with a weak
connection at a restaurant table. React Server Components, per-route static generation and
tag-based ISR give that essentially for free. Django templates plus a sprinkle of
JavaScript would mean rebuilding the interactivity by hand and losing the typed boundary.

**Cost.** Two runtimes, two dependency sets, two test stacks; a network hop on every
render; the risk that the contract drifts. The last one is mitigated by ADR-007 — types are
generated from the live schema, so drift is a compile error.

**What would make this wrong.** If the panel shrank to a couple of forms, one Next.js app
would win on operational simplicity.

---

## ADR-002: Translation tables, not a JSONB column

**Context.** Three languages, with Uzbek as the fallback. The compact option is
`name = {"uz": "...", "ru": "..."}` in a JSONB column — one row per product, no joins.

**Decision.** `ProductTranslation` and `CategoryTranslation` side tables, each with a
`UniqueConstraint(object, language)` and an index on `(language, name)`.

**Rationale.** The legacy data had 74 products with no Russian or English name and nobody
noticed for two years. That is the failure this schema exists to prevent. With side tables,
"which products lack a Russian name?" is one indexed query, `missing_translations` is a
serializer property, and the panel prints the gap on every row. With JSONB it is a
sequential scan and a key existence check, which is precisely the kind of query nobody
writes.

Search is the other half. `ProductTranslation.name` is a real indexed column, so
case- and accent-insensitive matching works with ordinary SQL functions rather than JSON
path expressions.

The constraint matters too: a unique `(product, language)` makes a duplicate Russian name
impossible at the database level. JSONB will happily store whatever the application put
there.

**Cost.** More rows, a `prefetch_related` on every read path, and nested writes in the
admin serializer. `TranslatableMixin` and `resolve_translation()` absorb the read cost in
one place, and the prefetch means the lookup runs in Python at no extra query.

**What would make this wrong.** A dozen locales with sparse coverage and no need to query
across them would tilt back toward JSONB.

---

## ADR-003: Prices as integer UZS

**Context.** The legacy data stored prices as floats and contained real values of `5`,
`28` and `35` — data-entry accidents that had been live for years.

**Decision.** `PositiveIntegerField` counting whole som, with `MinValueValidator(100)` in
the application *and* a `CheckConstraint(price >= 100)` in the database.

**Rationale.** The Uzbek som has no practical minor unit — nothing is priced in tiyin, and
menu prices are five- and six-figure round numbers. An integer therefore represents the
domain exactly, and removes float rounding and the whole class of bugs that comes with it.
`Decimal` would be defensible but adds serialization ceremony (`COERCE_DECIMAL_TO_STRING`,
quantisation on every arithmetic operation) for a precision nobody needs.

The floor is a data rule, so it lives in the database, not only in a form. The Firestore
import quarantined 12 documents on that constraint and flagged 13 more for review, writing
a verdict for each to `backend/var/import_report.csv` rather than forcing them through: a
migration that silently accepts nonsense is worse than one that stops and says why.

**Cost.** A second currency, or any currency with cents, needs a migration. Formatting is
locale-aware in the frontend (`30 000 so'm` with a no-break space in uz/ru, `30,000` in en)
and the integer is never formatted server-side.

**What would make this wrong.** Multi-currency pricing, or an integration whose API speaks
decimals.

---

## ADR-004: JWT in httpOnly cookies behind a BFF

**Context.** The original compared an admin password inside client JavaScript and recorded
success as `localStorage.adminToken = "authenticated"`. Anyone who opened DevTools was an
administrator. The obvious replacements were (a) JWT in `localStorage` with the browser
calling the API directly, (b) Django session cookies with the browser calling the API
directly, or (c) tokens held server-side by Next.js.

**Decision.** (c). Credentials go to a Next.js route handler, which exchanges them with
Django for an access/refresh pair and writes both to `httpOnly; secure; sameSite=lax`
cookies. Every admin API call is made from the Next.js server with the token attached. The
browser receives HTML.

**Rationale.** A token in `localStorage` is readable by any script on the page: one XSS,
one bad dependency, and the session leaks. httpOnly removes that entire attack class rather
than mitigating it. And because the token never leaves the server, the API host itself
never appears in client code — `API_INTERNAL_URL` has no `NEXT_PUBLIC_` prefix, CORS is
locked to a single origin, and the API can live on a network the internet cannot route to.

Session cookies from Django would have worked, but they would force the browser to call the
API directly (reopening CORS, cross-site cookie rules, and a public API host) and would
give up the stateless refresh-rotation flow that makes a stolen token expire in 15 minutes.

The design that falls out of it:

- Access cookie `maxAge` equals the token lifetime, so *expired* and *signed out* are
  distinguishable without decoding a JWT at the edge.
- The proxy only redirects; the real gate is a Server Component asking `/auth/me/`. No
  admin markup is ever produced for an unauthenticated request, so there is no client guard
  racing to hide the interface.
- Refresh rotation with blacklisting, so a leaked refresh token is single-use.

**Cost.** Every admin interaction is a server round trip; there is no optimistic
client-side cache of admin data. For a panel used by three people editing a menu, that is
the right trade. Token exchange is confined to Node route handlers because the edge runtime
cannot read request-time environment variables — the mechanics are in
[ARCHITECTURE](ARCHITECTURE.md#the-bff-auth-model).

---

## ADR-005: Object storage for images, not base64 in the row

**Context.** Each legacy document embedded its photo as `data:image/jpeg;base64,…`. The
collection was ~15 MB of JSON for 86 dishes, and the menu was unusable on a phone.

**Decision.** Uploads go to S3-compatible object storage (MinIO in development, Cloudflare
R2 in production, identical env keys). Django converts each to WebP at 400/800/1600 px on
save and keeps the original as the regeneration source. The database stores keys and
intrinsic dimensions; the API returns `{src, srcset, alt, width, height}`.

**Rationale.** Base64 inflates bytes by ~33%, defeats HTTP caching (the image is inside a
JSON response that changes whenever anything else does), forces the whole payload down the
wire before the first dish renders, and makes the row unusable for any query. Object
storage inverts all four: images are cacheable forever behind immutable keys, are fetched
in parallel and lazily, and the JSON stays small.

Three widths, not on-the-fly resizing: the set of sizes the design needs is known
(`sizes` in the product grid), conversion happens once at upload, and CDN cost is a flat
`immutable` header. `next/image`'s optimiser is deliberately bypassed with a custom
loader — re-encoding an already-optimised WebP is a second lossy pass and a proxy hop for
no benefit.

**Cost.** A second piece of infrastructure and a bucket policy. `post_delete` cleanup has
to be right or the bucket accumulates orphans; it removes the original and all three
derivatives, including on cascade from a deleted product.

---

## ADR-006: Selenium for end-to-end coverage

**Context.** The unit and integration layers are strong — 229 pytest tests at 92% line
coverage on the API, plus `node:test` suites for the frontend's pure logic. None of them
prove that a human can actually sign in, upload a photo, and see the menu change. The
legacy app's headline bug was a primary button with no handler; every unit test in the
world would have passed.

**Decision.** End-to-end coverage is a Selenium journey driving a real Chrome through the
real stack: sign in, list products, create, edit, upload an image, search, delete, sign
out, and survive a silent token refresh. Each step captures a screenshot into
`screenshots/`, which is also where the images in this repository's documentation come
from.

**Why Selenium rather than Playwright or Cypress.** The backend already owns the test
infrastructure — pytest, fixtures, factories, a configured database — and Selenium is a
Python client, so the browser journey lives in the same runner, seeds its data with the
same factories, and asserts against the same models. Playwright would mean a second test
runner, a second CI job and a second set of fixtures in a different language for a suite
that is intentionally small.

**Cost.** Selenium is slower and flakier than the modern alternatives; it has no
auto-waiting, so every interaction needs an explicit `WebDriverWait` on a condition rather
than a sleep. The suite is therefore kept to journeys that cross the whole stack and are
worth that price. Anything expressible as a unit test is a unit test.

**What would make this wrong.** A large E2E suite, or a need for network interception and
trace viewing, would justify the second runner.

---

## ADR-007: Generated API types instead of hand-written ones

**Context.** Two languages describing one contract. Hand-written TypeScript interfaces
mirroring DRF serializers drift the moment somebody renames a field, and the drift shows up
in production rather than in CI.

**Decision.** `drf-spectacular` publishes OpenAPI 3.1 at `/api/schema/`;
`npm run gen:api` turns it into `src/types/api.d.ts` via `openapi-typescript`. Frontend
code imports `components['schemas'][...]`. No response type is written by hand.

**Rationale.** It makes the contract mechanically enforced instead of socially enforced. A
renamed backend field breaks `tsc`, and `npm run typecheck` is part of the definition of
done. The schema is also the API's own documentation (Swagger UI in development), so there
is one artefact rather than a spec and a doc that disagree.

**Cost.** The generator needs a running API, so `gen:api` is a manual step rather than a
build hook, and a stale `api.d.ts` is possible between a backend change and a regeneration.
A test asserts the schema still generates cleanly
(`apps/common/tests/test_api_schema.py`), and the file is committed so a clean clone can
type-check without the stack up.
