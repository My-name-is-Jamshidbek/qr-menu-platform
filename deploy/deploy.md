# Production runbook

Everything needed to put BOSS KAFE on a server and keep it there. Written to be
followed literally at 2 a.m. by someone who did not build it.

The stack is five containers on one host, defined in `docker-compose.prod.yml`:

| service | image | exposed | role |
|---|---|---|---|
| `caddy` | `caddy:2.10-alpine` | 80, 443 | TLS termination, routing, static files |
| `web` | built from `frontend/` | internal | Next.js standalone server |
| `api` | built from `backend/` | internal | Django + gunicorn |
| `postgres` | `postgres:16-alpine` | internal | data, volume `pgdata` |
| `redis` | `redis:7-alpine` | internal | cache, no persistence |
| `backup` | `postgres:16-alpine` | internal | nightly `pg_dump`, volume `backups` |

Nothing but Caddy listens on a public port. Product images live in Cloudflare R2,
not on the host.

Every command below runs from the repository root on the server.

---

## 1. Provision

Target: a 2 vCPU / 4 GB Debian 12 or Ubuntu 24.04 host with a public IPv4.
2 GB is enough to run it but not to build the images on the same box.

### 1.1 DNS

Point the record at the host **before** the first deploy — Caddy's ACME challenge
fails without it, and Let's Encrypt rate-limits repeated failures.

```
A    menu.example.uz    -> <server ip>
AAAA menu.example.uz    -> <server ipv6, if any>
```

Verify: `dig +short menu.example.uz` returns the server's address.

### 1.2 Host packages

```bash
sudo apt-get update && sudo apt-get install -y ca-certificates curl git ufw
# Docker Engine + Compose plugin, from Docker's own repository
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"   # log out and back in for this to take effect
```

Confirm: `docker compose version` prints v2.24 or newer (the `env_file` and
`healthcheck` syntax used here needs it).

### 1.3 Firewall

Only SSH and the web ports. The database is never reachable from outside.

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 443/udp   # HTTP/3
sudo ufw enable
sudo ufw status verbose
```

### 1.4 Object storage

Create a Cloudflare R2 bucket, an API token scoped to it, and a public custom
domain for reads (e.g. `media.example.uz`). Collect four values for `.env.prod`:
`S3_BUCKET`, `S3_ENDPOINT_URL`, `S3_PUBLIC_URL`, and the access key pair.

R2 is S3-compatible, so nothing in the Django settings changes between MinIO in
development and R2 here.

### 1.5 Checkout and configuration

```bash
sudo mkdir -p /srv/bosskafe && sudo chown "$USER" /srv/bosskafe
git clone <repository-url> /srv/bosskafe
cd /srv/bosskafe

cp deploy/env.prod.example .env.prod
chmod 600 .env.prod
$EDITOR .env.prod          # every CHANGE_ME must go
```

Generate the three secrets:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"   # DJANGO_SECRET_KEY
openssl rand -base64 36                                         # POSTGRES_PASSWORD
openssl rand -hex 32                                            # REVALIDATE_SECRET
```

`.env.prod` is not in the repository and must never be committed. Confirm before
the first commit on the server:

```bash
git check-ignore -v .env.prod   # must print a matching .gitignore rule
```

Sanity-check the composition without starting anything:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod config
```

---

## 2. First deploy

### 2.1 The one ordering constraint

`next build` prerenders the menu pages, which means the **web image calls the API
while it is being built**. On a first deploy the API is not running yet, so bring
it up first and point the build at it.

```bash
cd /srv/bosskafe
export COMPOSE="docker compose -f docker-compose.prod.yml --env-file .env.prod"

# 1. Data layer.
$COMPOSE up -d postgres redis

# 2. API. Its start command migrates and collects static files by itself.
$COMPOSE up -d --build api
$COMPOSE logs -f api        # wait for "Listening at: http://0.0.0.0:8000"
```

Wait for the healthcheck to go green — the web build depends on it:

```bash
$COMPOSE ps api             # STATUS must read "healthy"
```

### 2.2 Seed the menu

An empty menu makes the frontend build produce an empty site. Load the data
before building the web image — either the demo set or the legacy import:

```bash
$COMPOSE exec api python manage.py seed_demo          # demo menu
# or
$COMPOSE exec api python manage.py import_firestore   # legacy Firestore data
```

Dry-run the import first if the data source is not trusted:
`... import_firestore --dry-run` writes a CSV report and touches nothing.

### 2.3 Build and start the frontend and the edge

The API container is only reachable by name from inside the compose network, and
`docker build` does not join it. Publish the API on loopback for the duration of
the build:

```bash
# Temporarily expose the API to the builder.
docker run -d --name bosskafe-build-proxy --network bosskafe-prod_default \
  -p 127.0.0.1:8000:8000 alpine/socat \
  TCP-LISTEN:8000,fork,reuseaddr TCP:api:8000

$COMPOSE build web            # BUILD_API_INTERNAL_URL points at 127.0.0.1:8000
docker rm -f bosskafe-build-proxy

$COMPOSE up -d
```

> If the frontend is changed so that `generateStaticParams` tolerates an
> unreachable API (returning `[]` and rendering the menu on demand), this whole
> step collapses to `$COMPOSE up -d --build`. That is the preferred end state.

### 2.4 Verify

```bash
$COMPOSE ps                                   # every service healthy
curl -I https://menu.example.uz               # 200, and a valid certificate
BASE_URL=https://menu.example.uz \
  API_URL=https://menu.example.uz bash deploy/smoke.sh
```

Caddy issues the certificate on the first request; the first one may take a few
seconds. `$COMPOSE logs caddy` shows the ACME exchange if it does not.

---

## 3. Routine deploys

Images are tagged with the git SHA so that a rollback is a tag change, not a
rebuild.

```bash
cd /srv/bosskafe
git fetch --all
git checkout <sha>

export IMAGE_TAG="$(git rev-parse --short HEAD)"
sed -i "s/^IMAGE_TAG=.*/IMAGE_TAG=${IMAGE_TAG}/" .env.prod

$COMPOSE build                 # see 2.3 about the API the web build needs
$COMPOSE up -d
BASE_URL=https://menu.example.uz API_URL=https://menu.example.uz bash deploy/smoke.sh
```

There is a few seconds of downtime while `web` and `api` are replaced. For a menu
that is read from a phone at a table, that is acceptable; a blue/green setup is
not worth the moving parts here.

---

## 4. Migrations

The `api` container runs `manage.py migrate --noinput` on every start, so an
ordinary deploy needs no manual step. Migrations are idempotent — a restart
re-runs the command, not the migrations.

Run one by hand (a data migration, or a fix after a failed deploy):

```bash
$COMPOSE exec api python manage.py migrate
$COMPOSE exec api python manage.py showmigrations   # what is applied
```

**A migration that drops or rewrites a column is not reversible by rolling back
the image.** Before deploying one:

1. take a manual backup (§6.1),
2. deploy,
3. if it goes wrong, restore the backup rather than reverting the migration.

Django cannot roll a destructive migration back safely, and pretending otherwise
is how data gets lost.

---

## 5. Creating the first admin user

The API image has no user in it. Create one interactively after the first deploy:

```bash
$COMPOSE exec api python manage.py createsuperuser
```

`createsuperuser` sets `is_staff` and `is_superuser`, but the API's permission
layer keys off `User.role`, which defaults to `STAFF`. Promote the account:

```bash
$COMPOSE exec api python manage.py shell -c "
from apps.accounts.models import User
u = User.objects.get(username='<username>')
u.role = 'ADMIN'
u.save(update_fields=['role'])
print(u.username, u.role)
"
```

`ADMIN` may manage tables and users; `STAFF` may only edit the menu.

Confirm the account works end to end — the staff UI is at
`https://menu.example.uz/uz/admin/login`, the Django admin at
`https://menu.example.uz/admin/`.

Create further staff accounts from the Django admin; do not share one login.

---

## 6. Backups

The `backup` service dumps the database into the `backups` volume on start and
then every `BACKUP_INTERVAL_SECONDS` (default: daily), keeping
`BACKUP_RETENTION_DAYS` (default: 14) of history. Dumps are `pg_dump -Fc`
(custom format, compressed).

```bash
$COMPOSE exec backup ls -lh /backups        # what exists
$COMPOSE logs backup                        # what happened
```

The service healthcheck turns unhealthy when the newest dump is older than one
and a half intervals — that is the signal that backups have stopped, and it is
worth wiring to whatever alerting the host has.

> These dumps live on the same host as the database, which protects against a
> bad migration but not against losing the host. Copy them off-site:
> `rclone sync` to the R2 account already in use is the cheapest option.

### 6.1 Take one now

```bash
$COMPOSE exec backup /usr/local/bin/backup.sh once
```

### 6.2 Copy a dump to your machine

```bash
$COMPOSE cp backup:/backups/bosskafe-20260818T030000Z.dump ./
```

---

## 7. Restoring a backup

Restoring **replaces the live database**. Read the whole section first.

```bash
# 1. Stop everything that writes. Postgres itself stays up.
$COMPOSE stop caddy web api backup

# 2. Take a dump of the current state first — restoring the wrong file is a
#    recoverable mistake only if this exists.
$COMPOSE exec -T postgres pg_dump -U "$POSTGRES_USER" -Fc "$POSTGRES_DB" \
  > "pre-restore-$(date -u +%Y%m%dT%H%M%SZ).dump"

# 3. Restore. --clean --if-exists drops each object before recreating it, so the
#    result is the dump's contents and nothing else.
$COMPOSE exec -T backup pg_restore \
  --clean --if-exists --no-owner --no-privileges \
  --dbname "$POSTGRES_DB" /backups/<file>.dump

# 4. Bring the stack back and check.
$COMPOSE up -d
$COMPOSE exec api python manage.py migrate --noinput   # dump may predate a migration
BASE_URL=https://menu.example.uz API_URL=https://menu.example.uz bash deploy/smoke.sh
```

Notes:

- `pg_restore` prints errors for objects that did not exist before the restore.
  Those are expected with `--clean --if-exists`; a non-zero exit is not fatal on
  its own. Read the output before deciding.
- The dump contains the database only. Product images are in R2 and are not
  affected — but a restore to an older state can leave rows pointing at images
  deleted since. Re-uploading is the fix.
- Flush the cache so no stale menu survives the restore:
  `$COMPOSE exec redis redis-cli FLUSHALL`

---

## 8. Rotating secrets

Rotate on a schedule, and immediately if a value has been exposed.

### `DJANGO_SECRET_KEY`

Signs sessions and password-reset tokens; JWTs are signed with it too. Rotating
it logs every staff user out. No data is lost.

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
$EDITOR .env.prod
$COMPOSE up -d --force-recreate api
```

### `POSTGRES_PASSWORD`

`POSTGRES_PASSWORD` only initialises the cluster; changing it in the environment
does **not** change the existing role's password. Change both:

```bash
NEW="$(openssl rand -base64 36)"
$COMPOSE exec postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "ALTER ROLE \"$POSTGRES_USER\" WITH PASSWORD '${NEW}';"
sed -i "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=${NEW}|" .env.prod
$COMPOSE up -d --force-recreate api backup
```

### `REVALIDATE_SECRET`

Shared between Django (the sender) and Next.js (the receiver), so both must be
recreated together or cache invalidation silently stops working.

```bash
$EDITOR .env.prod
$COMPOSE up -d --force-recreate api web
# Prove it: edit a product price in the staff UI, reload the public menu.
```

### `S3_ACCESS_KEY` / `S3_SECRET_KEY`

Create the new R2 token first, put it in `.env.prod`, recreate `api`, upload one
image to confirm, then revoke the old token in the Cloudflare dashboard. Never
revoke before verifying.

```bash
$COMPOSE up -d --force-recreate api
```

After any rotation, `git log -p -- .env.prod` must return nothing. If a secret
was ever committed, rotating it is mandatory — removing the commit is not enough.

---

## 9. Rolling back

Because every deploy is tagged with a git SHA, rolling back is a tag change.

```bash
cd /srv/bosskafe
sed -i "s/^IMAGE_TAG=.*/IMAGE_TAG=<previous short sha>/" .env.prod
$COMPOSE up -d
BASE_URL=https://menu.example.uz API_URL=https://menu.example.uz bash deploy/smoke.sh
```

If the old images are no longer on the host, rebuild them from the tag:

```bash
git checkout <previous sha>
$COMPOSE build && $COMPOSE up -d
```

**Rolling back the code does not roll back the database.** Check what the deploy
migrated before assuming the old code will run:

```bash
$COMPOSE exec api python manage.py showmigrations
```

- Additive migration (new nullable column, new table, new index): the old code
  ignores it. Roll back freely.
- Destructive migration (dropped or renamed column, changed constraint): the old
  code will fail. Restore the pre-deploy backup (§7) instead.

---

## 10. Day-to-day operations

```bash
$COMPOSE ps                          # health of every service
$COMPOSE logs -f --tail=100 api      # follow one service
$COMPOSE exec api python manage.py shell
$COMPOSE exec postgres psql -U "$POSTGRES_USER" "$POSTGRES_DB"
$COMPOSE exec redis redis-cli FLUSHALL          # drop the menu cache
$COMPOSE exec caddy caddy reload --config /etc/caddy/Caddyfile   # after a Caddyfile edit
docker system prune -af --filter "until=168h"   # reclaim disk from old images
```

### When the site is down

1. `$COMPOSE ps` — which service is unhealthy?
2. `caddy` down → certificate or DNS. `$COMPOSE logs caddy`, check the A record.
3. `api` unhealthy → `$COMPOSE logs api`. Usually Postgres unreachable or a
   failed migration on start.
4. `web` unhealthy → `$COMPOSE logs web`. Usually the API was unreachable during
   a render.
5. `postgres` unhealthy → check disk: `df -h`. A full disk stops Postgres first
   and looks like everything else failing.
