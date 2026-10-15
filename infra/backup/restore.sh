#!/usr/bin/env bash
# P9-B05: restore a backup made by backup.sh.
#
#   infra/backup/restore.sh <backup_dir> [--target-db NAME] [--files-dest DIR] [--yes]
#
# Safe by default: restores into a NEW database (default forahis_restore) and
# never touches the live one. To replace the live database, pass
# --target-db <live name> and --yes; the existing database is renamed to
# <name>_pre_restore_<ts> rather than dropped, so a bad restore is reversible.
# Stop the backend first when restoring over the live database.
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

BACKUP="${1:-}"; shift || true
TARGET_DB="forahis_restore"
FILES_DEST=""
ASSUME_YES=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --target-db) TARGET_DB="$2"; shift 2 ;;
    --files-dest) FILES_DEST="$2"; shift 2 ;;
    --yes) ASSUME_YES=1; shift ;;
    *) die "unknown argument: $1" ;;
  esac
done
BACKUP="$(unixpath "$BACKUP")"; FILES_DEST="$(unixpath "$FILES_DEST")"
[[ -n "$BACKUP" && -d "$BACKUP" ]] || die "usage: restore.sh <backup_dir> [--target-db NAME] [--files-dest DIR] [--yes]"
[[ "$TARGET_DB" =~ ^[a-z_][a-z0-9_]*$ ]] || die "invalid database name '$TARGET_DB'"
resolve_pg_container

log "verifying checksums"
( cd "$BACKUP" && sha256sum -c SHA256SUMS >&2 ) || die "checksum mismatch - backup is corrupt or tampered with; refusing to restore"

EXISTS="$(psql_in -d postgres -c "SELECT 1 FROM pg_database WHERE datname='$TARGET_DB';")"
if [[ -n "$EXISTS" ]]; then
  if [[ "$TARGET_DB" == "$PG_DB" ]]; then
    [[ $ASSUME_YES -eq 1 ]] || die "'$TARGET_DB' is the live database; re-run with --yes (and stop the backend first)"
    PRE="${TARGET_DB}_pre_restore_$(date -u +%Y%m%dT%H%M%SZ)"
    log "renaming live database $TARGET_DB -> $PRE (kept for rollback)"
    psql_in -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='$TARGET_DB' AND pid <> pg_backend_pid();" >/dev/null
    psql_in -d postgres -c "ALTER DATABASE \"$TARGET_DB\" RENAME TO \"$PRE\";"
  else
    [[ $ASSUME_YES -eq 1 ]] || die "database '$TARGET_DB' already exists; re-run with --yes to replace it"
    psql_in -d postgres -c "DROP DATABASE \"$TARGET_DB\";"
  fi
fi

log "creating $TARGET_DB and restoring db.dump"
psql_in -d postgres -c "CREATE DATABASE \"$TARGET_DB\";"
docker exec -i "$PG_CONTAINER" pg_restore -U "$PG_USER" -d "$TARGET_DB" --no-owner --no-privileges \
  --exit-on-error < "$BACKUP/db.dump"

if [[ -n "$FILES_DEST" ]]; then
  [[ -f "$BACKUP/files.tar.gz" ]] || die "backup has no files.tar.gz"
  mkdir -p "$FILES_DEST"
  [[ -z "$(ls -A "$FILES_DEST")" || $ASSUME_YES -eq 1 ]] || die "'$FILES_DEST' is not empty; use --yes to extract over it"
  log "extracting uploaded files -> $FILES_DEST"
  tar xzf "$BACKUP/files.tar.gz" -C "$FILES_DEST"
fi

log "restored into database '$TARGET_DB' (run verify.sh for the recovery check)"
