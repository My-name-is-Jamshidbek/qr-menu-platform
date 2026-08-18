# Contributing

Setup lives in the [README](README.md#quickstart). This file is the working agreement.

## The contracts come first

`docs/DATA_MODEL.md`, `docs/API_CONTRACT.md` and `docs/DESIGN_SYSTEM.md` describe what the
system *is*. Code that disagrees with them is a bug in the code, not in the document. If a
contract needs to change, change it in the same commit as the code and say why in the
message. Anything genuinely contested goes in `docs/DECISIONS.md` as a new numbered ADR;
existing ADRs are superseded, never rewritten.

## English only in code

Identifiers, comments, docstrings, filenames, commit messages, branch names, test names:
English. Every string a user can read lives in `frontend/messages/{uz,ru,en}/*.json` or in
a database translation table. A user-facing string hardcoded in a component is a review
blocker — it is the one mistake that makes adding a fourth language a refactor instead of a
data entry task.

## Conventions

**Backend**

- Ruff is the formatter and linter, 100 columns, rules `E F I UP B DJ`. `ruff check .` must
  be clean.
- Type-annotate function signatures. Django's own dynamic attributes are exempt.
- Business rules that are data invariants belong in the database as well as the model —
  the price floor is both a `MinValueValidator` and a `CheckConstraint` on purpose.
- No secret has a default. `config("KEY")` with no fallback makes a missing variable a
  startup error instead of a silent boot with a dev value.
- New user-visible endpoints go in the API contract, keep `snake_case` keys, and appear in
  `apps/common/tests/test_api_schema.py`'s expected-path list.

**Frontend**

- Server Components by default. `'use client'` needs a reason you can name: interactivity,
  browser API, or a hook that requires it.
- Data access goes through `src/lib/api.ts`. It imports `server-only`, so a client
  component importing it is a build error rather than a leak — keep it that way.
- Response types come from `src/types/api.d.ts`, which is generated. Never hand-write one;
  run `npm run gen:api` against a running API instead.
- No hex value in a component. Colours, spacing, radii and shadows are tokens from
  `src/styles/tokens.css`, consumed through Tailwind.
- Every interactive element has a visible focus state, a 44×44px minimum hit area, and does
  something. A control that looks clickable and is not is the exact defect this rewrite
  exists to fix.
- All motion is skipped under `prefers-reduced-motion`.
- Feature code lives under `src/features/<feature>/` with its data access, logic and
  components together; `src/components/ui/` is for genuinely shared primitives only.

**Both**

- Comments explain *why*. The code already says what.
- No dead code, no commented-out blocks, no `TODO` in a merged change. If it is worth
  doing later it is worth an issue; if it is not, delete it.

## Tests

Every change ships with the test that would have caught the bug.

| Layer | Where | Run |
|---|---|---|
| API, models, migration rules | `backend/apps/*/tests/` | `pytest -q` |
| Frontend pure logic (search, formatting, selectors) | `src/features/*/**.test.mjs` | `node --test "src/features/menu/*.test.mjs"` |
| Browser journeys | Selenium, captures into `screenshots/` | see [ADR-006](docs/DECISIONS.md#adr-006-selenium-for-end-to-end-coverage) |

Frontend logic tests are `.mjs`, not `.ts`, on purpose: `tsconfig.json` compiles every
`.ts` file in the project and does not enable `allowImportingTsExtensions`, so a TypeScript
test importing `./search.ts` would fail `next build`. Node strips the types off the imports,
so the code under test is still the real typed implementation.

Use `factory_boy` factories, not fixtures pasted between files. Assert on behaviour and on
the response body, not on the query count — unless the query count *is* the behaviour, as
in the menu aggregate.

## Definition of done

Run all of these before opening a pull request:

```bash
set -a; source .env.hostdev; set +a

cd backend
.venv/bin/python -m ruff check .
.venv/bin/python -m pytest -q

cd ../frontend
npm run lint
npm run typecheck
node --test "src/features/menu/*.test.mjs"
npm run build            # needs the API reachable at API_INTERNAL_URL
```

A change is done when all of the above pass, the contract docs match the code, no
user-facing string was added outside `messages/`, and — for anything visible — a screenshot
shows it working.

## Commits and branches

Branch from `main` as `<type>/<short-slug>`, e.g. `feat/table-qr-sheet`,
`fix/menu-cache-race`.

Commit messages are imperative and English, subject under 72 characters:

```
feat(menu): serve the whole menu in one cached request

The storefront needs categories, subcategories and products together to
prerender a filter page. Five queries assembled in Python, cached per
language in Redis and dropped by the write signals.
```

Types: `feat`, `fix`, `refactor`, `perf`, `test`, `docs`, `chore`. Scopes follow the app or
feature name (`menu`, `tables`, `accounts`, `admin`, `i18n`, `infra`).

One logical change per commit. A commit that both renames a field and adds a feature is two
commits.

## Reviewing

Reject on: a user-facing string outside `messages/`, a hardcoded colour, a hand-written API
response type, a secret with a default, a client component that did not need to be one, a
`TODO`, an interactive element with no focus state, and any test that asserts an
implementation detail rather than a behaviour.
