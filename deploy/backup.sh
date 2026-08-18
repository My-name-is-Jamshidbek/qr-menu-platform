#!/bin/sh
# Periodic Postgres backup for the production stack.
#
# Runs as the `backup` service in docker-compose.prod.yml: one dump immediately
# on start, then one every BACKUP_INTERVAL_SECONDS, pruning anything older than
# BACKUP_RETENTION_DAYS.
#
# Custom format (-Fc) rather than plain SQL: it is compressed, and pg_restore can
# read a single table out of it without replaying the whole file.
#
# Connection parameters come from the standard PG* environment variables, so no
# credential is ever written into a command line where `ps` could read it.
#
# Restoring is documented in deploy/deploy.md.

set -eu

BACKUP_DIR="${BACKUP_DIR:-/backups}"
BACKUP_INTERVAL_SECONDS="${BACKUP_INTERVAL_SECONDS:-86400}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"

log() {
	echo "[backup] $(date -u '+%Y-%m-%dT%H:%M:%SZ') $*"
}

dump_once() {
	timestamp="$(date -u '+%Y%m%dT%H%M%SZ')"
	target="${BACKUP_DIR}/${PGDATABASE}-${timestamp}.dump"
	partial="${target}.partial"

	log "dumping ${PGDATABASE} -> ${target}"

	# Write to a .partial name first: a dump interrupted by a container restart
	# must never be mistaken for a restorable one by the retention sweep or by a
	# hurried operator.
	if pg_dump --format=custom --compress=9 --no-owner --no-privileges --file="${partial}"; then
		mv "${partial}" "${target}"
		log "wrote $(du -h "${target}" | cut -f1) to ${target}"
	else
		log "ERROR: pg_dump failed, leaving ${partial} for inspection"
		return 1
	fi
}

prune() {
	log "pruning dumps older than ${BACKUP_RETENTION_DAYS} days"
	find "${BACKUP_DIR}" -maxdepth 1 -name '*.dump' -mtime "+${BACKUP_RETENTION_DAYS}" -print -delete
	# Interrupted dumps are never restorable; do not keep them around for long.
	find "${BACKUP_DIR}" -maxdepth 1 -name '*.dump.partial' -mtime +1 -print -delete
}

mkdir -p "${BACKUP_DIR}"

log "starting: interval=${BACKUP_INTERVAL_SECONDS}s retention=${BACKUP_RETENTION_DAYS}d dir=${BACKUP_DIR}"

# A single run for ad-hoc use: `docker compose ... run --rm backup once`.
if [ "${1:-}" = "once" ]; then
	dump_once
	prune
	exit 0
fi

while true; do
	# A failed dump must not kill the loop — the next attempt may well succeed,
	# and the service healthcheck is what surfaces a sustained failure.
	dump_once || log "dump failed, will retry at the next interval"
	prune || log "prune failed"
	log "sleeping ${BACKUP_INTERVAL_SECONDS}s"
	sleep "${BACKUP_INTERVAL_SECONDS}"
done
