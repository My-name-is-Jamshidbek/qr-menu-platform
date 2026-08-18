# BOSS KAFE — web

Next.js 16 (App Router, Turbopack) frontend for the BOSS KAFE menu and admin panel.

## Prerequisites

Environment variables come from the repository root. To run against the host-mapped
dev infrastructure:

```bash
set -a; source ../.env.hostdev; set +a
```

| variable | used by | notes |
|---|---|---|
| `API_INTERNAL_URL` | `src/lib/api.ts` | Django API base path. **Server-only** — never prefix it with `NEXT_PUBLIC_`. |
| `NEXT_PUBLIC_SITE_URL` | metadata | Public origin, used for canonical and `hreflang` links. |
| `REVALIDATE_SECRET` | revalidation webhook | Shared secret the API sends as `X-Revalidate-Secret`. |

## Scripts

| script | what it does |
|---|---|
| `npm run dev` | Dev server on port 3000. Regenerates the message catalog first. |
| `npm run build` | Production build (`output: 'standalone'`). Regenerates the message catalog first. |
| `npm run start` | Serves the production build. |
| `npm run lint` | ESLint (`eslint-config-next`, core-web-vitals + TypeScript). |
| `npm run typecheck` | `next typegen` followed by `tsc --noEmit`. |
| `npm run gen:messages` | Rebuilds `src/i18n/catalog.generated.ts` from `messages/`. |
| `npm run gen:api` | Regenerates `src/types/api.d.ts` from the live OpenAPI schema. |

`gen:api` reads `API_SCHEMA_URL` and falls back to `http://localhost:8100/api/schema/`:

```bash
npm run gen:api
API_SCHEMA_URL=http://api:8000/api/schema/ npm run gen:api
```

Response types are always generated — never hand-written.

## Layout

```
messages/<locale>/<namespace>.json   translations (see messages/README.md)
scripts/                             build-time codegen
src/app/[locale]/                    the only route tree; every URL is locale-prefixed
src/i18n/                            routing, request config, catalog, navigation helpers
src/lib/api.ts                       server-only API client (errors + cache tags)
src/lib/fonts.ts                     self-hosted Playfair Display / Inter
src/proxy.ts                         locale negotiation (Next.js 16 name for middleware)
```

## Internationalisation

Locales are `uz` (default), `ru`, `en`, always prefixed: `/uz/menu`, `/ru/menu`, `/en/menu`.
`/` redirects to the best match from the `NEXT_LOCALE` cookie, then `Accept-Language`,
then `uz`. Missing `ru`/`en` keys fall back to `uz` per key.

Import `Link`, `redirect`, `useRouter` and `usePathname` from `@/i18n/navigation`, not
from `next/link` or `next/navigation`, so links keep their locale prefix.

## Data fetching

```ts
import {apiFetch, fetchMenuData, ApiError, CACHE_TAGS} from '@/lib/api';

const menu = await fetchMenuData<MenuResponse>('menu/', {query: {lang: locale}});
```

`fetchMenuData` tags the response with `menu`, which the API purges through
`POST /api/revalidate` on every write. `apiFetch` throws `ApiError` (carrying `status`,
`code` and `fieldErrors`) for both HTTP errors and transport failures.

## Docker

Multi-stage `Dockerfile`:

- `--target runner` — production image, standalone output, runs as the non-root `nextjs` user.
- default (last) stage `dev` — what `docker-compose.yml` builds; runs `npm run dev` as `node`.
