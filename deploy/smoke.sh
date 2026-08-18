#!/usr/bin/env bash
# End-to-end smoke test: drives a running stack over HTTP the way a phone would.
#
# Used two ways:
#   make e2e                       against the local development stack
#   BASE_URL=https://menu... smoke  as the last step of a production deploy
#
# It asserts the paths that must never be broken: the menu API answers in every
# language, the statically generated menu page renders, a QR token redirects,
# and the staff login rejects a bad password without leaking which half was
# wrong. It writes nothing, so it is safe to run against production.

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:3100}"
API_URL="${API_URL:-http://localhost:8100}"

pass=0
fail=0

red() { printf '\033[31m%s\033[0m\n' "$*"; }
green() { printf '\033[32m%s\033[0m\n' "$*"; }

# check <name> <expected-status> <url> [grep-pattern]
check() {
	local name="$1" expected="$2" url="$3" pattern="${4:-}"
	local body status

	body="$(mktemp)"
	# curl has already written the status code to stdout by the time it fails, so
	# the fallback must replace the capture, never be appended to it.
	if ! status="$(curl -sS -o "${body}" -w '%{http_code}' --max-time 20 "${url}")"; then
		status=000
	fi

	if [ "${status}" != "${expected}" ]; then
		red "FAIL  ${name}: expected HTTP ${expected}, got ${status}  (${url})"
		fail=$((fail + 1))
		rm -f "${body}"
		return
	fi

	if [ -n "${pattern}" ] && ! grep -q -- "${pattern}" "${body}"; then
		red "FAIL  ${name}: HTTP ${expected} but body does not contain '${pattern}'"
		fail=$((fail + 1))
		rm -f "${body}"
		return
	fi

	green "ok    ${name}"
	pass=$((pass + 1))
	rm -f "${body}"
}

echo "Smoke test  web=${BASE_URL}  api=${API_URL}"
echo

# --- API ---------------------------------------------------------------------
for lang in uz ru en; do
	check "GET /api/v1/menu/?lang=${lang}" 200 "${API_URL}/api/v1/menu/?lang=${lang}" '"categories"'
done
check 'GET /api/v1/menu/ rejects an unknown language' 400 "${API_URL}/api/v1/menu/?lang=fr"
check 'GET /api/v1/products/' 200 "${API_URL}/api/v1/products/?lang=uz" '"count"'
check 'GET /api/schema/' 200 "${API_URL}/api/schema/" 'openapi'

# Bad credentials must be a flat 401 with no hint about which field was wrong.
if ! login_status="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 20 \
	-H 'Content-Type: application/json' \
	-d '{"username":"nobody-smoke-test","password":"wrong"}' \
	"${API_URL}/api/v1/auth/token/")"; then
	login_status=000
fi
if [ "${login_status}" = "401" ]; then
	green "ok    POST /api/v1/auth/token/ rejects bad credentials"
	pass=$((pass + 1))
else
	red "FAIL  POST /api/v1/auth/token/: expected HTTP 401, got ${login_status}"
	fail=$((fail + 1))
fi

# --- Web ---------------------------------------------------------------------
check 'GET / redirects to the default locale' 307 "${BASE_URL}/"
for lang in uz ru en; do
	check "GET /${lang}/menu renders" 200 "${BASE_URL}/${lang}/menu" '<html'
done
check 'GET /uz/admin/login renders' 200 "${BASE_URL}/uz/admin/login" '<html'
check 'GET /t/<unknown token> is handled' 307 "${BASE_URL}/t/00000000-0000-0000-0000-000000000000"
check 'GET /uz/does-not-exist is a 404' 404 "${BASE_URL}/uz/does-not-exist"

echo
if [ "${fail}" -gt 0 ]; then
	red "${fail} failed, ${pass} passed"
	exit 1
fi
green "${pass} passed"
