from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

BACKEND_DIR = Path(__file__).resolve().parent.parent


def _script_directory() -> ScriptDirectory:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    return ScriptDirectory.from_config(config)


def test_migration_history_has_a_single_head():
    script = _script_directory()

    heads = script.get_heads()
    assert len(heads) == 1


def test_baseline_revision_is_the_root():
    script = _script_directory()

    revisions = list(script.walk_revisions())
    root = revisions[-1]
    assert root.down_revision is None
    assert "baseline" in root.doc.lower()
