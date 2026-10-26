#!/usr/bin/env bash
# P9-B05: timestamped backup of the PostgreSQL database and uploaded files.
#
#   infra/backup/backup.sh
#
# Produces  $BACKUP_DIR/forahis_<UTC timestamp>/
#   db.dump        pg_dump custom format (compressed, restorable with pg_restore)
#   files.tar.gz   uploaded files (patient photos), if STORAGE_DIR/STORAGE_VOLUME is set
#   manifest.json  timestamp, alembic revision, per-table row counts, file count
#   SHA256SUMS     checksums, verified again before any restore
#
# The backup contains PHI: the directory is created 0700. Encrypt it and copy it
# off the host before relying on it (see docs/backup-restore.md).
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

resolve_pg_container
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DEST="$BACKUP_DIR/forahis_$STAMP"
mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR" 2>/dev/null || true
mkdir "$DEST"
chmod 700 "$DEST" 2>/dev/null || true
trap 'rc=$?; if [[ $rc -ne 0 ]]; then log "backup FAILED - removing partial $DEST"; rm -rf "$DEST"; record_failure backup "$rc"; fi' EXIT

log "database $PG_DB in $PG_CONTAINER -> $DEST"

# Counts first, dump second: rows written in between appear in the dump but not
# the manifest, so a restore can only hold >= the recorded counts (verify.sh
# relies on this ordering).
table_counts "$PG_DB" > "$DEST/.counts.tsv"
REVISION="$(alembic_revision "$PG_DB")"
PG_VERSION="$(psql_in -d "$PG_DB" -c 'SHOW server_version;')"

docker exec "$PG_CONTAINER" pg_dump -U "$PG_USER" -d "$PG_DB" --format=custom --compress=6 \
  --no-owner --no-privileges > "$DEST/db.dump"
[[ -s "$DEST/db.dump" ]] || die "pg_dump produced an empty file"

FILE_COUNT=0
if have_storage; then
  log "uploaded files -> files.tar.gz"
  tar_storage > "$DEST/files.tar.gz"
  tar tzf "$DEST/files.tar.gz" >/dev/null || die "files.tar.gz is not a valid archive"
  FILE_COUNT="$(tar tzf "$DEST/files.tar.gz" | grep -vc '/$' || true)"
else
  log "no STORAGE_DIR/STORAGE_VOLUME set - skipping uploaded files"
fi

python - "$(pypath "$DEST")" "$STAMP" "$REVISION" "$PG_VERSION" "$FILE_COUNT" <<'PY'
import json, sys
dest, stamp, revision, pg_version, file_count = sys.argv[1:6]
counts = {}
for line in open(f"{dest}/.counts.tsv", encoding="utf8"):
    table, _, n = line.rstrip("\n").partition("\t")
    counts[table] = int(n)
json.dump(
    {
        "created_utc": stamp,
        "database": "forahis",
        "postgres_version": pg_version,
        "alembic_revision": revision,
        "table_row_counts": counts,
        "uploaded_file_count": int(file_count),
    },
    open(f"{dest}/manifest.json", "w", encoding="utf8"),
    indent=2,
)
PY
rm -f "$DEST/.counts.tsv"

( cd "$DEST" && sha256sum db.dump manifest.json $(ls files.tar.gz 2>/dev/null) > SHA256SUMS )

if [[ "$RETENTION_DAYS" -gt 0 ]]; then
  # Only ever touches directories this script created.
  find "$BACKUP_DIR" -maxdepth 1 -type d -name 'forahis_[0-9]*T[0-9]*Z' -mtime +"$RETENTION_DAYS" \
    -print -exec rm -rf {} + | sed 's/^/pruned: /' >&2 || true
fi

trap - EXIT
record_success success
log "backup complete: $DEST ($(du -sh "$DEST" | cut -f1), revision $REVISION, $FILE_COUNT files)"
echo "$DEST"
