#!/usr/bin/env bash
# P9-B06: regenerate backend/requirements.lock (hash-pinned) from pyproject.toml.
# Resolved inside python:3.11-slim - the image the backend ships in - so the
# platform-specific pins (uvloop, httptools, ...) match production.
#
#   infra/security/update-backend-lock.sh            # re-resolve to newest allowed versions
#
# Review the diff, run the test suite, then infra/security/dependency-scan.sh.
set -euo pipefail
export MSYS_NO_PATHCONV=1
cd "$(dirname "${BASH_SOURCE[0]}")/../../backend"
SRC="$(pwd)"
command -v cygpath >/dev/null 2>&1 && SRC="$(cygpath -m "$SRC")"
docker run --rm -v "$SRC:/src" -w /src python:3.11-slim sh -c \
  "pip install -q pip-tools && pip-compile -q --upgrade --generate-hashes --strip-extras --allow-unsafe -o requirements.lock pyproject.toml"
echo "backend/requirements.lock updated"
