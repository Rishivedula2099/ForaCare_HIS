"""P9-F03: the frontend's route policy and `hasPermission(...)` checks may
only reference permission codes the backend actually defines, and every role
must be able to reach at least its landing pages. A typo here silently locks
a role out (or, worse, is never satisfiable)."""
import re
from pathlib import Path

from app.modules.rbac.constants import ALL_PERMISSION_CODES, ROLE_PERMISSION_SEED

FRONTEND_SRC = Path(__file__).resolve().parents[2] / "frontend" / "src"
CODE = re.compile(r'"([a-z_]+(?:\.[a-z_]+)+)"')


def _route_policy_codes() -> set[str]:
    text = (FRONTEND_SRC / "lib" / "route-access.ts").read_text(encoding="utf8")
    return set(CODE.findall(" ".join(re.findall(r"anyOf:\s*\[([^\]]*)\]", text))))


def _has_permission_codes() -> set[str]:
    codes: set[str] = set()
    for path in FRONTEND_SRC.rglob("*.ts*"):
        if "__tests__" in path.parts:
            continue
        codes.update(re.findall(r'hasPermission\(\s*"([a-z_.]+)"', path.read_text(encoding="utf8")))
    return codes


def test_route_policy_uses_only_real_permission_codes():
    codes = _route_policy_codes()
    assert codes, "no permission codes parsed from route-access.ts"
    assert codes <= set(ALL_PERMISSION_CODES), codes - set(ALL_PERMISSION_CODES)


def test_ui_has_permission_checks_use_only_real_codes():
    codes = _has_permission_codes()
    assert codes
    assert codes <= set(ALL_PERMISSION_CODES), codes - set(ALL_PERMISSION_CODES)


def test_every_route_policy_is_reachable_by_some_role():
    text = (FRONTEND_SRC / "lib" / "route-access.ts").read_text(encoding="utf8")
    granted = {code for perms in ROLE_PERMISSION_SEED.values() for code in perms}
    for block in re.findall(r"anyOf:\s*\[([^\]]*)\]", text):
        needed = CODE.findall(block)
        assert any(code in granted for code in needed), f"no role holds any of {needed}"
