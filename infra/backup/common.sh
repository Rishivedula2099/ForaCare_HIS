#!/usr/bin/env bash
# P9-B05: shared helpers for backup.sh / restore.sh / verify.sh.
#
# Everything talks to PostgreSQL through `docker exec` on the database
# container, so the host needs only Docker + bash (no local pg_dump, no
# version mismatch with the server).
#
# Configuration (environment):
#   PG_CONTAINER     database container name           (default: compose service "postgres")
#   PG_USER / PG_DB  credentials inside that container (default: forahis / forahis)
#   STORAGE_DIR      host directory holding uploaded files   } one of these;
#   STORAGE_VOLUME   docker volume holding uploaded files    } volume wins
#   BACKUP_DIR       where backups are written         (default: ./backups)
#   RETENTION_DAYS   prune backups older than this     (default: 14, 0 = keep all)

set -euo pipefail
# Git-bash on Windows rewrites arguments that look like POSIX paths; docker
# arguments here are container paths, so switch that off.
export MSYS_NO_PATHCONV=1

# Accept native Windows paths (C:\...) from callers; GNU tar would otherwise read
# "C:" as a remote host.
unixpath() { if [[ -n "$1" ]] && command -v cygpath >/dev/null 2>&1; then cygpath -u "$1"; else printf '%s' "$1"; fi; }

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PG_USER="${PG_USER:-forahis}"
PG_DB="${PG_DB:-forahis}"
BACKUP_DIR="${BACKUP_DIR:-$ROOT_DIR/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
BACKUP_DIR="$(unixpath "$BACKUP_DIR")"
STORAGE_VOLUME="${STORAGE_VOLUME:-}"
STORAGE_DIR="$(unixpath "${STORAGE_DIR:-}")"

log() { printf '[%s] %s\n' "$(date -u +%H:%M:%S)" "$*" >&2; }
die() { log "ERROR: $*"; exit 1; }

resolve_pg_container() {
  if [[ -z "${PG_CONTAINER:-}" ]]; then
    PG_CONTAINER="$(cd "$ROOT_DIR" && docker compose ps -q postgres 2>/dev/null | head -1 || true)"
  fi
  [[ -n "${PG_CONTAINER:-}" ]] || die "set PG_CONTAINER (could not find the compose 'postgres' service)"
  docker inspect -f '{{.State.Running}}' "$PG_CONTAINER" 2>/dev/null | grep -q true \
    || die "container '$PG_CONTAINER' is not running"
}

# psql inside the container; args after the db name are passed through.
psql_in() { docker exec -i "$PG_CONTAINER" psql -U "$PG_USER" -v ON_ERROR_STOP=1 -q -At "$@"; }

# Exact row count of every public table: "table<TAB>count" lines, sorted.
table_counts() {
  psql_in -d "$1" -F $'\t' -c "
    SELECT table_name,
           (xpath('/row/c/text()',
                  query_to_xml(format('SELECT count(*) AS c FROM %I.%I', table_schema, table_name),
                               false, true, '')))[1]::text
    FROM information_schema.tables
    WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
    ORDER BY table_name;"
}

alembic_revision() {
  psql_in -d "$1" -c "SELECT version_num FROM alembic_version LIMIT 1;" 2>/dev/null || echo "none"
}

have_storage() { [[ -n "$STORAGE_VOLUME" || -n "$STORAGE_DIR" ]]; }

# tar.gz of the uploaded-files tree on stdout.
tar_storage() {
  if [[ -n "$STORAGE_VOLUME" ]]; then
    docker run --rm -v "$STORAGE_VOLUME":/data:ro alpine tar czf - -C /data .
  else
    [[ -d "$STORAGE_DIR" ]] || die "STORAGE_DIR '$STORAGE_DIR' is not a directory"
    tar czf - -C "$STORAGE_DIR" .
  fi
}

# Native path for tools (Windows python) that cannot read MSYS paths like /tmp.
pypath() { if command -v cygpath >/dev/null 2>&1; then cygpath -m "$1"; else printf '%s' "$1"; fi; }

sha256_of() { sha256sum "$1" | cut -d' ' -f1; }
