#!/usr/bin/env bash
# P9-B05: recovery test. Proves a backup is actually restorable, without
# touching the live database:
#   1. checksums match            3. alembic revision matches the manifest
#   2. restores into a scratch DB 4. every table's row count >= the manifest's
#   5. file archive extracts and its file count matches the manifest
#
#   infra/backup/verify.sh <backup_dir>      (exit 0 = recoverable, non-zero = not)
#
# Counts may be >= (never <) the manifest because writes can land between the
# manifest snapshot and the dump (see backup.sh). Set STRICT_COUNTS=1 for exact
# equality, which is right on a quiesced system.
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

BACKUP="${1:-}"
BACKUP="$(unixpath "$BACKUP")"
[[ -n "$BACKUP" && -d "$BACKUP" ]] || die "usage: verify.sh <backup_dir>"
resolve_pg_container
SCRATCH="forahis_verify_$(date -u +%Y%m%d%H%M%S)"
WORK="$(mktemp -d)"
cleanup() {
  rc=$?
  if [[ $rc -ne 0 ]]; then record_failure "backup verification" "$rc"; fi
  psql_in -d postgres -c "DROP DATABASE IF EXISTS \"$SCRATCH\";" >/dev/null 2>&1 || true
  rm -rf "$WORK"
}
trap cleanup EXIT

"$(dirname "${BASH_SOURCE[0]}")/restore.sh" "$BACKUP" --target-db "$SCRATCH" --yes >&2

table_counts "$SCRATCH" > "$WORK/restored.tsv"
REVISION="$(alembic_revision "$SCRATCH")"

python - "$(pypath "$BACKUP/manifest.json")" "$(pypath "$WORK/restored.tsv")" "$REVISION" "${STRICT_COUNTS:-0}" <<'PY'
import json, sys
manifest = json.load(open(sys.argv[1], encoding="utf8"))
restored = {}
for line in open(sys.argv[2], encoding="utf8"):
    table, _, n = line.rstrip("\n").partition("\t")
    restored[table] = int(n)
revision, strict = sys.argv[3], sys.argv[4] == "1"
problems = []
if revision != manifest["alembic_revision"]:
    problems.append(f"alembic revision {revision} != manifest {manifest['alembic_revision']}")
for table, expected in manifest["table_row_counts"].items():
    got = restored.get(table)
    if got is None:
        problems.append(f"table {table} missing after restore")
    elif (got != expected) if strict else (got < expected):
        problems.append(f"table {table}: restored {got} rows, manifest {expected}")
for table in restored.keys() - manifest["table_row_counts"].keys():
    problems.append(f"unexpected table {table} after restore")
if problems:
    print("RECOVERY CHECK FAILED:\n  " + "\n  ".join(problems), file=sys.stderr)
    sys.exit(1)
total = sum(restored.values())
print(f"database OK: {len(restored)} tables, {total} rows, revision {revision}", file=sys.stderr)
PY

if [[ -f "$BACKUP/files.tar.gz" ]]; then
  mkdir "$WORK/files"
  tar xzf "$BACKUP/files.tar.gz" -C "$WORK/files"
  GOT="$(find "$WORK/files" -type f | wc -l | tr -d ' ')"
  WANT="$(python -c "import json,sys;print(json.load(open(sys.argv[1]))['uploaded_file_count'])" "$(pypath "$BACKUP/manifest.json")")"
  [[ "$GOT" == "$WANT" ]] || die "RECOVERY CHECK FAILED: extracted $GOT files, manifest says $WANT"
  log "files OK: $GOT files extracted"
fi

record_success verified
log "RECOVERY CHECK PASSED for $BACKUP"
