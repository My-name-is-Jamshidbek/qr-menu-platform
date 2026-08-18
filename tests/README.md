# End-to-end tests

Selenium WebDriver driving a real headless Chromium against a running stack.

**Selenium only.** Playwright is not used anywhere in this project and must not be
introduced here.

## What is covered

| File | Covers |
|---|---|
| `e2e/test_menu.py` | the menu loads, every published dish renders with a name and price, sections are grouped, unavailable dishes stay hidden |
| `e2e/test_category_filter.py` | filtering changes the URL *and* the result set, filtered URLs survive a reload and the back button, subsections narrow further, an unknown section 404s |
| `e2e/test_search.py` | search narrows the grid, is case-insensitive, matches descriptions, shows an empty state, and clears |
| `e2e/test_language.py` | the language switch changes navigation chrome and dish copy together, keeps the current filter, and falls back to Uzbek for a missing translation |
| `e2e/test_admin_auth.py` | bad credentials are rejected without a session cookie, the two failure modes are indistinguishable, good credentials open the panel with httpOnly cookies, the panel is guarded |
| `e2e/test_admin_products.py` | the add-product button is genuinely clickable, and the full create → edit → delete cycle including its effect on the public menu |
| `e2e/test_table_qr.py` | a QR token URL redirects to the menu and claims the table in a cookie; an unknown token does not |
| `e2e/test_mobile.py` | a 390x844 phone smoke test: single-column grid, working search, no sideways scroll, reachable language switch |

## Running

The stack must already be up — the suite starts no services.

```bash
set -a; source .env.hostdev; set +a
pip install -r tests/requirements.txt
cd tests && pytest
```

Useful invocations:

```bash
pytest -k mobile                  # one area
pytest e2e/test_admin_products.py # one file
pytest -x -vv                     # stop at the first failure, verbose
E2E_HEADLESS=0 pytest -k qr       # watch it happen in a real window
```

## Requirements

* Chromium and a matching chromedriver on the host. The suite never downloads a
  browser; it uses `/usr/bin/chromium` and `/usr/bin/chromedriver` by default.
* Postgres, Redis and MinIO as configured in `.env.hostdev`.
* An `ADMIN` account. If the configured credentials cannot sign in, the suite
  provisions `e2e-admin` once through `manage.py`, because the API deliberately
  exposes no endpoint for creating users. Set `E2E_PROVISION_ADMIN=0` to forbid
  that and supply an existing account instead.

## Configuration

Every value is an environment variable with a default matching `.env.hostdev`.

| Variable | Default | Purpose |
|---|---|---|
| `E2E_WEB_URL` | `http://localhost:3100` | front-end origin |
| `E2E_API_URL` | `http://localhost:8100/api/v1` | API base |
| `E2E_ADMIN_USERNAME` | `e2e-admin` | staff account the suite signs in as |
| `E2E_ADMIN_PASSWORD` | `e2e-password-123` | its password |
| `REDIS_URL` | `redis://localhost:6382/0` | where the login throttle counter lives |
| `E2E_HEADLESS` | `1` | set `0` to watch the browser |
| `E2E_WAIT_TIMEOUT` | `30` | seconds an explicit wait polls |
| `E2E_SCREENSHOT_DIR` | `screenshots/failures` | where failure artefacts land |
| `E2E_CHROME_BINARY` | `/usr/bin/chromium` | browser binary |
| `E2E_CHROMEDRIVER` | `/usr/bin/chromedriver` | driver binary |

## How the suite is built

**Page Object pattern.** Every selector lives in `e2e/pages/`, so markup changes
are one edit and the tests read as descriptions of behaviour. `BasePage` carries
the waiting, clicking and measuring helpers.

**No `time.sleep`, anywhere.** Waiting is always an explicit `WebDriverWait` on
the condition the test cares about — a card appearing, the result summary
changing, the URL becoming what it should be. `BasePage.await_hydration` waits
for React to claim a node before typing into it, so a controlled input never
receives keystrokes it will discard.

**Fixtures own their data.** Every category, product and table a test needs is
created through the REST API in a fixture and deleted again in teardown. Nothing
depends on seeded rows, on another test having run first, or on the order tests
execute in. `make_product` and `make_table` are factories; `fixture_category`
is session-scoped and sorted last in the menu so it never displaces real
sections.

**One sign-in per run.** The API throttles logins to 5/min per IP.
`test_admin_auth.py` exercises the sign-in form for real and clears the throttle
counter before each attempt; every other panel test injects the session cookies
obtained once by the `panel_cookies` fixture, so the suite is not testing the
same login twenty times.

**A fresh browser per test.** `next dev` compiles a route the first time it is
requested and swaps its chunk graph underneath any tab still holding the old
one, which surfaces as a `ChunkLoadError` and a dead renderer. A session-scoped
warm-up requests every route first, and each test gets a clean profile.

**Failure artefacts.** Any failing browser test writes
`screenshots/failures/<timestamp>-<test-id>.png` and a matching `.html` of the
page source, and prints the path.

## Notes on the environment

Two Chromium settings are load-bearing rather than decorative, and removing them
brings back "tab crashed" failures that look like product bugs:

* the background-networking flags in `e2e/browser.py` — with component updates,
  sync and GCM registration enabled, Chromium blocks on requests that never
  resolve in a sandbox without outbound internet;
* `E2E_TEMP_DIR` (default `tests/e2e/.tmp`) — Chromium profiles default to
  `/tmp`, which on this host is a 437MB partition that a full run fills, and a
  full `/tmp` kills the renderer mid-test.

The mobile viewport is set over CDP with `mobile: false`, not with
`--window-size`: headless Chromium will not shrink its window to 390px, and
`mobile: true` decouples the visual from the layout viewport, which would make
an overflow assertion measure the emulator instead of the page.
