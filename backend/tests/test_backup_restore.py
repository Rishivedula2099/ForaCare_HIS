"""P9-B05: backup / restore / recovery-test scripts (infra/backup).

Drives the real scripts against the real PostgreSQL container, restoring only
into scratch databases - the live database is read, never modified. Skipped
when bash/docker or the database container is unavailable.
"""
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / "infra" / "backup"
CONTAINER = os.environ.get("PG_CONTAINER", "backend-postgres-1")


def _bash() -> str | None:
    found = shutil.which("bash")
    if found and "system32" in found.lower():  # WSL launcher, not a usable shell
        return None
    return found


def _container_running() -> bool:
    if not shutil.which("docker"):
        return False
    r = subprocess.run(
        ["docker", "inspect", "-f", "{{.State.Running}}", CONTAINER], capture_output=True, text=True
    )
    return r.returncode == 0 and "true" in r.stdout


pytestmark = pytest.mark.skipif(
    not (_bash() and _container_running()), reason="needs bash + a running postgres container"
)


def run(script: str, *args: str, env_extra: dict | None = None, check=False):
    env = {**os.environ, "PG_CONTAINER": CONTAINER, **(env_extra or {})}
    return subprocess.run(
        [_bash(), str(SCRIPTS / script), *args],
        capture_output=True, text=True, env=env, cwd=REPO, check=check,
    )


def psql(sql: str, db: str = "postgres") -> str:
    r = subprocess.run(
        ["docker", "exec", CONTAINER, "psql", "-U", "forahis", "-d", db, "-At", "-c", sql],
        capture_output=True, text=True,
    )
    return r.stdout.strip()


def databases() -> set[str]:
    return set(psql("SELECT datname FROM pg_database").split())


@pytest.fixture
def storage(tmp_path):
    root = tmp_path / "storage" / "tenant" / "patients"
    root.mkdir(parents=True)
    (root / "a.jpg").write_bytes(b"photo-a")
    (root / "b.png").write_bytes(b"photo-b")
    return tmp_path / "storage"


@pytest.fixture
def backup(tmp_path, storage):
    out = tmp_path / "backups"
    r = run("backup.sh", env_extra={"BACKUP_DIR": str(out), "STORAGE_DIR": str(storage)})
    assert r.returncode == 0, r.stderr
    dirs = list(out.glob("forahis_*"))
    assert len(dirs) == 1
    return dirs[0]


def test_backup_is_timestamped_and_complete(backup):
    assert (backup.name.startswith("forahis_") and backup.name.endswith("Z"))
    for name in ("db.dump", "files.tar.gz", "manifest.json", "SHA256SUMS"):
        assert (backup / name).stat().st_size > 0
    manifest = json.loads((backup / "manifest.json").read_text())
    assert manifest["uploaded_file_count"] == 2
    assert manifest["alembic_revision"] != "none"
    assert manifest["table_row_counts"]["users"] > 0
    assert "db.dump" in (backup / "SHA256SUMS").read_text()


def test_recovery_check_passes_and_leaves_nothing_behind(backup):
    before = databases()
    r = run("verify.sh", str(backup))
    assert r.returncode == 0, r.stderr
    assert "RECOVERY CHECK PASSED" in r.stderr
    assert databases() == before, "scratch database was not cleaned up"


def test_restore_into_a_named_database_matches_the_source(backup):
    name = "forahis_restore_pytest"
    psql(f'DROP DATABASE IF EXISTS "{name}"')
    try:
        r = run("restore.sh", str(backup), "--target-db", name)
        assert r.returncode == 0, r.stderr
        manifest = json.loads((backup / "manifest.json").read_text())
        assert int(psql("SELECT count(*) FROM users", name)) >= manifest["table_row_counts"]["users"]
        assert psql("SELECT version_num FROM alembic_version", name) == manifest["alembic_revision"]
    finally:
        psql(f'DROP DATABASE IF EXISTS "{name}"')


def test_files_restore_to_a_destination(backup, tmp_path):
    dest = tmp_path / "restored_files"
    name = "forahis_restore_pytest_files"
    try:
        r = run("restore.sh", str(backup), "--target-db", name, "--files-dest", str(dest))
        assert r.returncode == 0, r.stderr
        assert (dest / "tenant" / "patients" / "a.jpg").read_bytes() == b"photo-a"
    finally:
        psql(f'DROP DATABASE IF EXISTS "{name}"')


def test_corrupted_backup_is_refused_before_anything_is_created(backup):
    dump = backup / "db.dump"
    data = bytearray(dump.read_bytes())
    data[len(data) // 2] ^= 0xFF
    dump.write_bytes(bytes(data))

    before = databases()
    r = run("restore.sh", str(backup), "--target-db", "forahis_should_not_exist")
    assert r.returncode != 0
    assert "checksum mismatch" in r.stderr
    assert databases() == before


def test_tampered_files_archive_is_refused(backup):
    (backup / "files.tar.gz").write_bytes(b"not the original archive")
    r = run("verify.sh", str(backup))
    assert r.returncode != 0 and "checksum mismatch" in r.stderr


def test_recovery_check_catches_a_manifest_that_claims_more_rows(backup):
    manifest = json.loads((backup / "manifest.json").read_text())
    manifest["table_row_counts"]["users"] += 1_000
    (backup / "manifest.json").write_text(json.dumps(manifest))
    # keep checksums valid so it is the content check that must fail
    import hashlib

    lines = []
    for name in ("db.dump", "manifest.json", "files.tar.gz"):
        digest = hashlib.sha256((backup / name).read_bytes()).hexdigest()
        lines.append(f"{digest}  {name}")
    # bytes, so the file has LF endings as sha256sum expects (not Windows CRLF)
    (backup / "SHA256SUMS").write_bytes(("\n".join(lines) + "\n").encode())

    before = databases()
    r = run("verify.sh", str(backup))
    assert r.returncode != 0
    assert "RECOVERY CHECK FAILED" in r.stderr and "users" in r.stderr
    assert databases() == before, "scratch database leaked after a failed check"


def test_restore_refuses_to_replace_the_live_database_without_confirmation(backup):
    r = run("restore.sh", str(backup), "--target-db", "forahis")
    assert r.returncode != 0
    assert "--yes" in r.stderr
    assert int(psql("SELECT count(*) FROM users", "forahis")) > 0  # untouched


def test_restore_rejects_a_hostile_database_name(backup):
    r = run("restore.sh", str(backup), "--target-db", 'x"; DROP DATABASE forahis; --')
    assert r.returncode != 0 and "invalid database name" in r.stderr
    assert "forahis" in databases()


def test_failed_backup_leaves_no_partial_directory(tmp_path):
    out = tmp_path / "backups"
    r = run("backup.sh", env_extra={"BACKUP_DIR": str(out), "PG_DB": "no_such_db"})
    assert r.returncode != 0
    assert not list(out.glob("forahis_*"))


def test_retention_prunes_only_old_backup_directories(tmp_path, storage):
    out = tmp_path / "backups"
    out.mkdir()
    old = out / "forahis_20200101T000000Z"
    old.mkdir()
    (old / "db.dump").write_bytes(b"x")
    stranger = out / "important_notes"
    stranger.mkdir()
    ancient = 946684800  # 2000-01-01
    os.utime(old, (ancient, ancient))
    os.utime(stranger, (ancient, ancient))

    r = run("backup.sh", env_extra={"BACKUP_DIR": str(out), "STORAGE_DIR": str(storage), "RETENTION_DAYS": "7"})
    assert r.returncode == 0, r.stderr
    assert not old.exists()
    assert stranger.exists(), "retention must never touch directories it did not create"
