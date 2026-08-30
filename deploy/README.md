# Production operations

The production topology is one Caddy edge proxy, one Next.js process, one FastAPI process, and PostgreSQL. Only Caddy publishes host ports. PostgreSQL, the API, and Next.js stay on an internal Docker network. Database, media, Caddy state, and backups use named volumes. A one-shot `media-init` service establishes ownership for the non-root API user before startup.

All production base and service images are digest-pinned while retaining readable release tags.
The API build uses the exact production dependency set in `requirements.lock`. Update dependency
ranges, the lock, and image digests together; run the full test, typing, Bandit, dependency-audit,
and image-scan gates before promotion. Development-only dependencies never enter runtime images.
The final API and web stages also remove build-time package managers (`pip`, `npm`, Corepack, and
Yarn) and omit frontend source from the API image, reducing the deployed attack surface without
changing the application entry points.

## First deployment

1. Copy `.env.example` to `.env` outside source control and replace every `CHANGE_ME` value. Use independent high-entropy values for the PostgreSQL password, authentication secret, and privacy hash secret. Keep the PostgreSQL password URL-safe because Compose interpolates it into the async database URL.
2. Set `SITE_ADDRESS`, `HTTPS_REDIRECT_ORIGIN`, `PORTFOLIO_PUBLIC_BASE_URL`, allowed origins/hosts, cookie domain, and verified `sameAs` URLs to the real HTTPS host. The default browser-visible edge port is `18444`; Caddy detects plaintext HTTP sent to that TLS port and redirects it to the canonical HTTPS URL on the same port. `HTTPS_REDIRECT_ORIGIN` must include it unless an upstream maps the deployment to standard port 443. Do not list a social profile until ownership has been verified.
3. Validate and build:

   ```sh
   docker compose config --quiet
   docker compose build --pull
   docker compose up -d
   docker compose ps
   ```

The `migrate` job must finish successfully before the API starts. The API must pass `/health/ready` before Next.js starts, and Caddy waits for both application health checks. Migrations are forward-only during deployment; take a backup before changing a production schema.

Create the first owner interactively after the services are healthy:

```sh
docker compose exec api portfolio-admin create-admin --display-name "Site owner" --role owner
```

The management command reads `PORTFOLIO_ADMIN_EMAIL` and `PORTFOLIO_ADMIN_PASSWORD` from the
configured environment. Rotate an existing account without creating a second owner with:

```sh
docker compose exec api portfolio-admin update-admin --current-email owner@example.com --display-name "Site owner"
```

Do not put the admin password on the command line. The command prompts without echo.

## Health, logs, and shutdown

- Edge liveness: `https://HOST/healthz`
- API liveness: `https://HOST/health/live`
- API readiness: `https://HOST/health/ready`
- Logs: `docker compose logs --since=15m proxy web api`
- Graceful stop: `docker compose down --timeout 45`

FastAPI emits structured JSON logs with request IDs and no request bodies. Uvicorn receives `SIGTERM` and allows 30 seconds for graceful shutdown. Caddy supplies HSTS, CSP, security headers, compression, TLS, and JSON access logs.

## Backup and restore

Create a database and media backup with SHA-256 sidecars:

```sh
docker compose --profile operations run --rm backup
```

Copy named-volume backups to separately encrypted off-host storage. A backup is not accepted until its checksum has been verified and a restore drill has completed in a non-production environment.

Restore is intentionally gated and destructive. Stop API and web traffic first, then provide the exact dump paths:

```sh
docker compose stop proxy web api
docker compose --profile operations run --rm \
  -e CONFIRM_RESTORE=RESTORE restore \
  /backups/portfolio-YYYYMMDDTHHMMSSZ.dump \
  /backups/portfolio-media-YYYYMMDDTHHMMSSZ.tar.gz
docker compose up -d
```

The restore verifies both checksum sidecars, restores PostgreSQL in one transaction, and replaces media only when a media archive is explicitly supplied. It restores the runtime media ownership before the API is restarted.

## Release and rollback

Tag API and web images with an immutable `IMAGE_TAG`. Before promotion, run the CI workflow, back up production, and verify the candidate against a restored staging snapshot. Application rollback uses the previous image tag. If a schema change is not backward compatible, restore the pre-release database/media backup instead of issuing an unreviewed migration downgrade.
