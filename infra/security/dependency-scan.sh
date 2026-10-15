#!/usr/bin/env bash
# P9-B06: dependency vulnerability scan - run in CI and before every release.
#
#   infra/security/dependency-scan.sh
#
# Gates (exit 1 on failure):
#   backend   any known vulnerability in backend/requirements.lock (what ships)
#   frontend  any high/critical in production dependencies (what ships)
# Reported but not gating:
#   frontend  devDependency findings (test/lint tooling that is never deployed)
#
# Needs: python with `pip-audit` (pip install pip-audit), node/npm.
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
status=0

echo "== backend: pip-audit on requirements.lock =="
if python -m pip_audit -r backend/requirements.lock --no-deps --disable-pip --progress-spinner off; then
  echo "backend: OK"
else
  echo "backend: VULNERABLE (or scan failed)"; status=1
fi

echo
echo "== frontend: npm audit (production dependencies, high+) =="
if (cd frontend && npm audit --omit=dev --audit-level=high); then
  echo "frontend (prod): OK"
else
  echo "frontend (prod): VULNERABLE"; status=1
fi

echo
echo "== frontend: npm audit (devDependencies - informational) =="
(cd frontend && npm audit --audit-level=none 2>&1 | tail -8) || true

echo
echo "== lock freshness =="
if [[ backend/pyproject.toml -nt backend/requirements.lock ]]; then
  echo "backend/pyproject.toml is newer than requirements.lock - run infra/security/update-backend-lock.sh"
  status=1
else
  echo "requirements.lock is current with pyproject.toml"
fi
exit $status
