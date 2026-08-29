# Yazeed Hasan portfolio platform

Production-oriented personal portfolio and publishing platform built as one monorepo. The public
site and admin workspace are a Next.js/TypeScript application; `apps/api` is the single FastAPI
composition root; domain behavior remains owned by the packages in `services/`.

## Architecture at a glance

- `apps/web` — public experience and authenticated admin UI using Next.js, Tailwind CSS,
  shadcn/Radix primitives, and the shared motion package.
- `apps/api` — HTTP composition, dependency injection, authentication, health, and middleware.
- `services/*` — identity, portfolio, content, engagement, assistant, discovery, and the
  cross-domain public-catalog application service.
- `packages/python/clients` — database, storage, SMTP, and AI client/adapter boundaries.
- `packages/frontend/api-client` — the typed, validated frontend-to-FastAPI transport layer.
- `db/migrations` — the only Alembic migration graph.
- `deploy` — production container, edge, backup, and restore infrastructure.

The detailed product and implementation authorities are [goal.md](goal.md), [BRD.md](BRD.md),
[architecture.md](architecture.md), [design_document.md](design_document.md),
[tech_stack.md](tech_stack.md), and [implementation_plan.md](implementation_plan.md).

## Prerequisites

- Python 3.12–3.14
- Node.js 22 or newer and npm 10 or newer
- PostgreSQL 17 for normal development and integration tests
- Docker with Compose v2 for production-parity validation

## Local setup

Install the locked workspace dependencies:

```sh
python -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[dev]"
npm ci
```

On PowerShell, activate with `.\.venv\Scripts\Activate.ps1` and then use `python` in place of
`.venv/bin/python`.

Set a PostgreSQL connection and independent development secrets in `.env`, then migrate:

```dotenv
PORTFOLIO_ENVIRONMENT=development
PORTFOLIO_DATABASE_URL=postgresql+asyncpg://portfolio:local-password@localhost:5432/portfolio
PORTFOLIO_AUTH_SECRET=replace-with-an-independent-32-character-development-secret
PORTFOLIO_PRIVACY_HASH_SECRET=replace-with-another-independent-32-character-secret
```

```sh
alembic upgrade head
uvicorn apps.api.main:app --reload --port 8000
npm run dev
```

The web app runs on `http://localhost:3000`; FastAPI runs on `http://localhost:8000`. The browser
uses only the typed API client. API documentation is enabled in development at `/docs` and disabled
in production by default.

## Canonical content and administration

Create the first owner without placing a password on the command line:

```sh
portfolio-admin create-admin --display-name "Site owner" --role owner
```

The command reads the email from `PORTFOLIO_ADMIN_EMAIL`. It reads the password from
`PORTFOLIO_ADMIN_PASSWORD` when set, otherwise it prompts securely. Existing credentials can be
rotated without creating a duplicate account; all active sessions are revoked during rotation:

```sh
portfolio-admin update-admin --current-email owner@example.com --display-name "Site owner"
```

A first owner can bootstrap an empty installation in `/admin/profiles`: create the canonical
profile, upload a portrait and résumé, review the drafts, publish the profile, and then make the
reviewed résumé current. The public site, discovery documents, and stable `/resume` route remain
unavailable until those publication dependencies are satisfied. Editors can author drafts, while
owner-only controls enforce public identity, feature, approval, sponsorship, and repository-refresh
transitions at the API boundary.

Seed data is explicit, validated, additive, and idempotent. It never truncates or replaces existing
records:

```sh
portfolio-seed init --file portfolio.manifest.json
portfolio-seed validate --file portfolio.manifest.json
portfolio-seed dry-run --file portfolio.manifest.json
portfolio-seed apply --file portfolio.manifest.json --approve
```

Bounded draft-only import adapters are also available through `portfolio-seed import-json-resume`
and `portfolio-seed import-linkedin`. Imports never publish automatically and must pass the same
validation, dry-run, explicit-approval, and canonical persistence workflow as hand-authored
manifests.

`tests/fixtures/e2e/manifest.json` contains fictional browser-test data and must not be treated as
production identity content. Résumé and managed media files referenced by a manifest are validated
before persistence.

### Yazeed Hasan starter content

`yazeed.portfolio.manifest.json` is the reviewed, resume-backed starter for this portfolio. It
publishes the supplied `portfolio_image.png` as the primary portrait and
`YazeedHasanResume.pdf` as the current public resume. Validate and preview it before the explicitly
approved additive apply:

```sh
portfolio-seed validate --file yazeed.portfolio.manifest.json
portfolio-seed dry-run --file yazeed.portfolio.manifest.json
portfolio-seed apply --file yazeed.portfolio.manifest.json --approve
```

The admin dashboard maps the five public chapters to their canonical content areas. About is
managed through profiles, portraits, resumes, social links, skills, and education; Achievements
through credentials and writing; Work through experience; Projects through projects; and Sponsor
through sponsorship and contact submissions. The Sponsor page remains available for
purpose-specific inquiries while direct gateway options are intentionally unconfigured. Add only
reviewed payment destinations in `/admin/sponsorship` when those details are supplied.

Publication is compositional: public children require every populated parent to be public, evidence
approvals are tied to an immutable content/evidence hash, and only evidence deliberately marked
public is projected outside the admin API. Feature settings retain four distinct states
(`unconfigured`, `enabled`, `disabled`, and `archived`); disabled and archived features always fail
closed across APIs, site chrome, homepage composition, discovery, and the assistant.

Contact submissions are committed with a payload-bound idempotency key and a durable notification
outbox. The API lifespan worker leases due rows, retries with bounded backoff, recovers stale leases,
and reuses the provider idempotency key. Poll cadence and batch size are controlled by
`PORTFOLIO_CONTACT_NOTIFICATION_POLL_SECONDS` and
`PORTFOLIO_CONTACT_NOTIFICATION_BATCH_SIZE`. Owner-only manual processing is available for
operations; it is not required for normal delivery.

## Verification

The main local gates are:

```sh
ruff format --check apps services packages tests
ruff check apps services packages tests
mypy apps services packages
pytest -m "not integration" --cov=apps --cov=services --cov=packages --cov-report=term-missing
npm run verify
npm run test:coverage
bandit -c pyproject.toml -r apps services packages/python
pip-audit --requirement requirements.lock
npm audit --omit=dev --audit-level=high
```

With `CORE_TEST_DATABASE_URL` pointing to a disposable migrated PostgreSQL database, run
`pytest -m integration -q`. The production Compose job additionally validates migrations,
health/readiness, seed idempotency, backup/restore, browser E2E, accessibility, security headers,
and performance budgets.

## Production operations

Copy `.env.example` to a secret-managed `.env`, replace every `CHANGE_ME` value, and validate the
rendered topology before starting it:

```sh
docker compose config --quiet
docker compose build --pull
docker compose up -d
docker compose ps
```

Only Caddy publishes host ports. PostgreSQL, FastAPI, and Next.js remain on the internal network;
migrations and media ownership initialization must succeed before application readiness. Complete
deployment, TLS, logging, backup/restore, and rollback procedures are in
[deploy/README.md](deploy/README.md).

Public Next.js reads use bounded revalidation and publication-tag invalidation. The internal
`/admin/revalidate-public` handler validates the browser/proxy origin, and the production web
container provides a bounded writable cache mount while retaining a read-only root filesystem.

Do not enable SMTP or the AI assistant until real provider configuration is present and its
readiness checks pass. Never fabricate credentials, social profiles, résumé claims, testimonials,
metrics, or production content.
