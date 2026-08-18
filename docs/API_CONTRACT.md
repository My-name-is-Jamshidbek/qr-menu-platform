# API Contract

Base path `/api/v1/`. JSON only. Schema published by `drf-spectacular` at
`/api/schema/` (OpenAPI 3.1) and `/api/schema/swagger-ui/`.

Frontend types are **generated** from that schema into `frontend/src/types/api.d.ts`
via `openapi-typescript` (`npm run gen:api`). Never hand-write a response type.

## Conventions

- `snake_case` keys (Django side); the frontend consumes them as-is
- Language selection: `?lang=uz|ru|en`, default `uz`. Invalid value → 400
- Errors: RFC 7807-ish — `{"detail": str, "code": str, "field_errors": {field: [str]}}`
- Pagination: `?page=&page_size=` (default 20, max 100) → `{count, next, previous, results}`
- All timestamps ISO 8601 UTC

## Image object

Every image is serialized identically:

```json
{
  "alt": "Boss salad",
  "width": 1600,
  "height": 1200,
  "src": "https://.../products/2026/08/abc-800.webp",
  "srcset": {
    "400": "https://.../abc-400.webp",
    "800": "https://.../abc-800.webp",
    "1600": "https://.../abc-1600.webp"
  }
}
```

`null` when the product has no image — the frontend renders a monogram placeholder.

## Public endpoints (no auth, cached)

### `GET /api/v1/menu/?lang=uz`

The whole menu in **one request** — categories, subcategories and products nested.
The dataset is small (~86 products) and the page is statically generated, so one
round trip beats N. Cached in Redis for 300s, invalidated on any write.

```json
{
  "categories": [
    {
      "slug": "salads",
      "name": "Salatlar",
      "is_fallback": false,
      "children": [{ "slug": "cold-salads", "name": "Sovuq salatlar", "is_fallback": false }],
      "products": [
        {
          "slug": "boss-salad",
          "name": "Boss salat",
          "description": "",
          "is_fallback": false,
          "price": 30000,
          "category_slug": "salads",
          "image": { }
        }
      ]
    }
  ],
  "generated_at": "2026-08-18T10:00:00Z"
}
```

### `GET /api/v1/products/?lang=&category=&search=&page=`

Paginated flat list. `search` matches `ProductTranslation.name` and `description`
for the requested language, case-insensitive, unaccented.

### `GET /api/v1/products/{slug}/?lang=`

Single product, all images.

### `POST /api/v1/tables/{token}/scan/`

Records a `TableScan`. Returns `{"table_number": 7}` or 404 for an unknown/inactive token.
Rate-limited to 30/hour per token.

## Auth endpoints

### `POST /api/v1/auth/token/` → `{"access": str, "refresh": str}`
Body `{"username", "password"}`. Throttled at 5/min per IP. 401 on bad credentials —
the message never distinguishes "no such user" from "wrong password".

### `POST /api/v1/auth/token/refresh/` → `{"access": str}`
### `GET /api/v1/auth/me/` → `{"id", "username", "role"}`

Access token lifetime 15 min, refresh 7 days, rotation on, blacklist on.

## Admin endpoints (auth required)

`Authorization: Bearer <access>`. Called **only** from the Next.js server, never the browser.
Permission: `STAFF` for menu writes, `ADMIN` for tables and users.

| method | path | notes |
|---|---|---|
| GET/POST | `/api/v1/admin/products/` | list is paginated, includes **all** translations and a `missing_translations: ["ru","en"]` array |
| GET/PATCH/DELETE | `/api/v1/admin/products/{id}/` | |
| POST | `/api/v1/admin/products/{id}/images/` | multipart, field `image`; server converts to WebP at 3 widths |
| DELETE | `/api/v1/admin/products/{id}/images/{image_id}/` | |
| GET/POST | `/api/v1/admin/categories/` | |
| GET/PATCH/DELETE | `/api/v1/admin/categories/{id}/` | DELETE returns 409 if products reference it |
| GET/POST | `/api/v1/admin/tables/` | `ADMIN` only |
| GET/PATCH/DELETE | `/api/v1/admin/tables/{id}/` | |
| GET | `/api/v1/admin/tables/{id}/qr.svg` | QR as SVG (`segno`) |
| GET | `/api/v1/admin/tables/qr-sheet.pdf` | printable sheet, all active tables |
| GET | `/api/v1/admin/stats/` | product count, missing-translation count, scans last 7 days |

Write payload for a product — translations are nested and written atomically:

```json
{
  "category": 3,
  "price": 30000,
  "is_available": true,
  "translations": [
    {"language": "uz", "name": "Boss salat", "description": ""},
    {"language": "ru", "name": "Босс салат", "description": ""}
  ]
}
```

`uz` translation is **required**; `ru`/`en` are optional. Missing `uz` → 400.

## Cache invalidation

Any successful write to `Product`, `ProductTranslation`, `ProductImage` or `Category`
fires a `post_save`/`post_delete` signal that:

1. drops the Redis `menu:*` keys, and
2. `POST`s to `${FRONTEND_URL}/api/revalidate` with header `X-Revalidate-Secret`,
   body `{"tags": ["menu"]}`.

Next.js revalidates the tagged ISR pages. A staff edit is live in ~2 seconds without a rebuild.
The POST is fire-and-forget with a 2s timeout — a slow frontend must never block the API.

## Security

- CORS: `FRONTEND_URL` only. The browser never calls this API directly, so the list stays closed
- Throttling: anon 120/min, auth 600/min, login 5/min
- `SECURE_*` headers, HSTS, `X-Content-Type-Options`, strict CSP on the Next side
- No secret is ever read from code — everything via env, `.env.example` documents each key
