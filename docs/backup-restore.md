# Backup and restore (P9-B05)

What is backed up, how to take a backup, how to restore, and how to prove a
backup works. Scripts live in `infra/backup/`; they need only Docker and bash.

## What holds state

| Data | Where | Backed up by |
|---|---|---|
| All clinical, billing, lab, audit data | PostgreSQL (`forahis_postgres_data` volume) | `pg_dump` -> `db.dump` |
| Patient photos | `FILE_STORAGE_ROOT` (`/app/storage`, volume `forahis_file_storage`) | `files.tar.gz` |
| Secrets (`JWT_*`, `QR_SIGNING_SECRET_KEY`, `ABDM_CLIENT_SECRET`) | environment / secret store | **Not in the backup** - keep them in your secret manager |

`QR_SIGNING_SECRET_KEY` matters for recovery: if it is lost, already-printed
document and lab-report QR codes stop verifying.

> Before P9-B05 the full compose stack had no volume for uploaded files, so
> photos were lost whenever the backend container was recreated. `docker-compose.yml`
> now mounts `forahis_file_storage`. Photos uploaded before that change exist
> only in the old container - copy them out first (`docker cp <backend>:/app/storage ./storage`).

## Take a backup

```bash
# full compose stack
STORAGE_VOLUME=foracare_his_forahis_file_storage infra/backup/backup.sh

# local dev database (backend/docker-compose.yml), files on the host
PG_CONTAINER=backend-postgres-1 STORAGE_DIR=backend/storage infra/backup/backup.sh
```

Output: `backups/forahis_<UTC timestamp>/` containing `db.dump` (pg_dump custom
format), `files.tar.gz`, `manifest.json` (timestamp, Alembic revision, row count
of every table, file count) and `SHA256SUMS`. The directory is mode 0700.

Settings: `BACKUP_DIR` (default `./backups`), `RETENTION_DAYS` (default 14, `0`
keeps everything; only `forahis_<timestamp>` directories are ever pruned),
`PG_CONTAINER`, `PG_USER`, `PG_DB`.

A failed backup deletes its partial directory and exits non-zero, so a
scheduler can alert on the exit code.

### Schedule it

Daily is the minimum for a hospital system (that is the worst-case data loss,
the RPO). Example cron, 02:00 UTC, with a recovery check after:

```cron
0 2 * * * cd /opt/foracare && STORAGE_VOLUME=foracare_his_forahis_file_storage infra/backup/backup.sh >> /var/log/foracare-backup.log 2>&1 \
  && infra/backup/verify.sh "$(ls -d backups/forahis_* | tail -1)" >> /var/log/foracare-backup.log 2>&1
```

### Protect the copies (not done by the scripts)

A backup holds every patient's data. Before it leaves the machine:

1. **Encrypt** it, e.g. `tar c forahis_<ts> | age -r <recipient> > forahis_<ts>.tar.age`.
2. **Copy it off-host** to a separate failure domain (another region/account,
   object storage with versioning/object lock). A backup on the same disk as
   the database is not a backup.
3. Keep the **encryption key separately** from the backups.
4. Apply the same access controls and retention rules as the live database.

## Restore

Restoring is **non-destructive by default**: it creates a new database and
verifies checksums first, refusing a corrupt or tampered backup.

```bash
# 1. Inspect / dry-run into a separate database (live system untouched)
infra/backup/restore.sh backups/forahis_20261015T020000Z                  # -> database forahis_restore
infra/backup/restore.sh backups/forahis_20261015T020000Z --files-dest ./storage_restored

# 2. Disaster recovery: replace the live database
docker compose stop backend nginx frontend
infra/backup/restore.sh backups/forahis_20261015T020000Z --target-db forahis --yes \
    --files-dest /path/to/storage
docker compose start backend nginx frontend
```

Replacing the live database **renames** the old one to
`forahis_pre_restore_<timestamp>` instead of dropping it, so a bad restore is
reversible (`ALTER DATABASE ... RENAME`). Drop the old copy once the restored
system is confirmed good.

After a restore, bring the app up: it runs `alembic upgrade head`, so a backup
from an older schema is migrated forward automatically.

## Verify a backup (recovery test)

```bash
infra/backup/verify.sh backups/forahis_20261015T020000Z
```

Exit 0 means the backup is genuinely recoverable. It checks:

1. checksums match;
2. `pg_restore` succeeds into a scratch database (always dropped afterwards, even on failure);
3. the Alembic revision equals the manifest's;
4. every table has at least the manifest's row count (`STRICT_COUNTS=1` demands exact equality - use on a quiesced system), and no table is missing or unexpected;
5. the file archive extracts and its file count matches.

**Run it after every backup, and do a full drill (step 2 of Restore, into a
staging environment, then log in and open a patient with a photo) at least
quarterly.** An untested backup is an assumption.

## Targets to agree with the hospital

| | Suggested starting point | Driven by |
|---|---|---|
| RPO (max data loss) | 24 h with daily backups; add WAL archiving / PITR for minutes | backup frequency |
| RTO (time to recover) | < 1 h for the current data size | measured by the quarterly drill |
| Retention | 14 daily local + 12 monthly off-site | policy / regulation |

For an RPO below a day, continuous WAL archiving (`archive_command`/pgBackRest/
WAL-G) is the next step; `pg_dump` snapshots cannot do point-in-time recovery.

## Tests

`backend/tests/test_backup_restore.py` exercises the real scripts against the
dev Postgres container (restores only into scratch databases): timestamped
output, recovery check, named-database restore, file restore, corruption and
tampering refusal, a manifest that over-claims rows, live-database protection,
hostile database names, no partial directory after a failed backup, and
retention touching only backup directories. It skips itself when
bash/Docker/the container are unavailable.
