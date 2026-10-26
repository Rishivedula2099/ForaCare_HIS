# Dependency security (P9-B06)

Scan results, what was patched, what remains, and how to keep it that way.
Scanned 2026-10-15 with `pip-audit` (PyPI/OSV advisories) and `npm audit`.

## How to run it

```bash
infra/security/dependency-scan.sh          # gates: exit 1 on any finding that ships
infra/security/update-backend-lock.sh      # re-resolve backend pins (inside python:3.11-slim)
```

Run the scan in CI on every PR and on a weekly schedule (new advisories appear
without any code change). It fails on:

- any known vulnerability in `backend/requirements.lock` (everything that ships),
- any high/critical in the frontend **production** dependencies,
- a `pyproject.toml` newer than its lock.

Frontend devDependency findings are printed but do not gate: that tooling
(test runner, linter) is never deployed.

## Backend

**Before:** `pyproject.toml` used open `>=` ranges and the Dockerfile built from
them, so every image build pulled whatever was newest that day - not
reproducible, and not scannable before it shipped.

**Now:** `backend/requirements.lock` pins every package (40, transitive
included) with hashes; the Dockerfile installs it with `--require-hashes`.
`pip-audit` on the lock: **no known vulnerabilities**. The full backend suite
(332 passed, 38 skipped) was run in a clean virtualenv on exactly these versions,
including major steps such as SQLAlchemy 2.1, bcrypt 5, FastAPI 0.143, Starlette 1.8.

**The developer environment was vulnerable.** The environment the tests normally
ran in held old copies of the same packages:

| Package (installed) | Advisories | Fixed in | Why it matters here |
|---|---|---|---|
| PyJWT 2.12.1 | 15 | 2.15 | signs/verifies every session token |
| Pillow 12.1.1 | 18 | 12.3 | decodes uploaded patient photos |
| Starlette 1.0.0 | 5 | 1.3.1+ | the HTTP layer |
| python-multipart 0.0.20 | 6 | 0.0.31+ | parses photo uploads |
| Jinja2 3.1.4 | 3 | 3.1.6 | renders documents |
| anyio, mako, idna, pydantic-settings | 1-2 each | see lock | |

The lock moves all of these to patched versions (PyJWT 2.15.1, Pillow 12.3.0,
Starlette 1.8.0, python-multipart 0.0.32, Jinja2 3.1.6). Developers should
install from the lock (`pip install -r backend/requirements.lock`, plus
`pytest pytest-asyncio httpx`) rather than a long-lived global environment. The
same machine also holds unrelated packages (torch, nltk, transformers, ...) with
hundreds of advisories; they are not project dependencies and were excluded.

Two platform notes: `uvloop` is Linux-only, so on Windows install the lock without
it; `colorama` (a Windows-only `qrcode` dependency) is absent from the Linux lock.

## Frontend

**Before:** 15 advisories - 3 critical, 9 high, 3 moderate.

| Finding | Severity | Ships? | Action |
|---|---|---|---|
| **next 16.3.4** - 7 advisories: RCE in `next/og`, cache poisoning of SSG/ISR pages (cross-user content), SSRF in image optimisation, information disclosure in metadata routes and Draft Mode | critical | **yes** | **Upgraded to 16.4.1** (same major) |
| vitest <=4.1.10, tinypool <=2.1.1 (RCE via prototype pollution), vite <=6.4.2, esbuild, vite-node, @vitest/mocker | critical/high/moderate | no (test tooling) | Upgraded to vitest 5.0.4, vite 7.3.7, @vitejs/plugin-react 5.2, @types/node 22 |
| brace-expansion, sharp, source-map-js | high | partly (transitive) | Cleared by the lock refresh |
| braces, micromatch, fast-glob, @next/eslint-plugin-next, eslint-config-next | high | no (linter) | **Accepted - see below** |

**Now:** production dependencies **0 vulnerabilities**. The type-check, the
production `next build`, and all 54 frontend tests pass on the new versions.

**Accepted risk (5 high, dev-only).** The remaining findings are one chain under
`eslint-config-next` (`braces` stack exhaustion on pathological glob patterns).
No patched `braces` exists upstream, and npm's suggested "fix" downgrades
`eslint-config-next` to 14.2.35, which would break Next 16 linting. The code
runs only on developer machines/CI against this repository's own files, never in
the deployed image. Re-check when `braces` publishes a fix.

## Patch priority

1. **Done - Next.js 16.4.1.** Critical, internet-facing, self-hosted (cache
   poisoning and SSRF apply to exactly this deployment).
2. **Done - backend lock with patched PyJWT, Pillow, Starlette, python-multipart.**
   Authentication, upload parsing and the HTTP layer.
3. **Rebuild and redeploy images** so production actually runs the above
   (see "Not verified").
4. **Done - test tooling** (vitest/tinypool/vite): developer-machine risk, patched
   for hygiene and so CI is not a foothold.
5. **Accepted - ESLint chain**: dev-only, no upstream fix.
6. **Ongoing:** weekly scheduled scan; review the lock diff on every refresh;
   keep the base images (`python:3.11-slim`, `postgres:16-alpine`, `nginx:1.27-alpine`,
   `alpine` in the backup scripts) patched - these are **not covered** by
   `pip-audit`/`npm audit`; scan them with an image scanner such as Trivy.

## Not verified

- The Docker image was **not rebuilt** with the hash-locked install in this
  session, so `pip install --require-hashes` on Linux is untested end to end
  (the lock was resolved on Linux, but run `docker compose build backend`
  before deploying).
- OS packages in the images, Chromium/Playwright browser builds, and the
  database server are outside the language-level scanners.
- `pip-audit` and `npm audit` only know published advisories; they say nothing
  about unpublished flaws or malicious packages. The hash-pinned lock and
  committed `package-lock.json` limit, but do not eliminate, supply-chain risk.
