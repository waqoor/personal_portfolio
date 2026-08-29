# Technology Stack — V5

## 1. Purpose

This document is the authoritative technology and engineering-stack specification for the portfolio platform.

The target is a **modern, production-ready monorepo sub-services architecture** with a TypeScript/Next.js frontend, a FastAPI composition host, explicit Python domain sub-services, PostgreSQL persistence, strong automated testing, and Docker deployment.

Do not introduce alternative frameworks that duplicate the responsibilities below unless a documented requirement justifies the change.

---

## 2. Frontend Stack

### Mandatory Frontend Rule

The frontend is **TypeScript-first and Next.js-based**.

Required foundation:

```text
TypeScript
  ↓
Next.js App Router + React
  ↓
Tailwind CSS + shadcn/ui
  ↓
Motion / GSAP / React Three Fiber
  ↓
Typed FastAPI API Client
```

- Use TypeScript strict mode.
- Do not create a parallel JavaScript frontend.
- Do not introduce an alternate frontend framework.
- shadcn/ui is a primitive/component foundation, not the final visual identity.
- Public and admin experiences live in the same Next.js application unless a future operational requirement explicitly changes that decision.

### Next.js
Primary frontend framework.

Responsibilities:

- App Router.
- Server Components.
- Server-side rendering.
- Static generation where appropriate.
- Metadata generation.
- Routing.
- API consumption.
- Image/font optimization.
- Public/admin presentation.

### TypeScript
All frontend application code should use TypeScript with strict typing enabled.

### React
Underlying component model.

### Tailwind CSS
Primary utility styling system.

### shadcn/ui
Base accessible UI component primitives.

Use as a foundation, then customize heavily to fit the site's visual identity. Do not leave the site looking like default shadcn components.

### Motion / Framer Motion
Use for:

- Component transitions.
- State transitions.
- Hover/tap behavior.
- Dialogs.
- Navigation.
- Lightweight entrances.
- Micro-interactions.

### GSAP + ScrollTrigger
Use for:

- Pinned scroll narratives.
- Scrubbed timelines.
- Complex typography transitions.
- Media choreography.
- Long-form cinematic sections.

### Three.js / React Three Fiber
Use for selected:

- Hero WebGL scenes.
- Particle systems.
- Shader effects.
- Abstract geometry.
- Technology/sector visualizations where WebGL genuinely improves the experience.

### next-themes
Dark/light/system theme management.

### Optional Lenis
May be used for smooth scrolling if it does not interfere with:

- Native anchors.
- Accessibility.
- Reduced motion.
- Browser history.
- Mobile performance.

---

## 3. Backend Stack

### Python
Primary backend language.

Use a currently supported stable Python release.

### FastAPI
Primary backend web framework.

Responsibilities:

- Public API.
- Admin API.
- Authentication endpoints.
- Contact endpoints.
- AI assistant endpoints.
- Health/readiness.
- OpenAPI contract.

### Pydantic
Use for:

- API request/response validation.
- Settings/configuration.
- Seed validation.
- Internal boundary models where useful.
- Environment validation.

### SQLAlchemy 2.x
Primary ORM and SQL abstraction.

Use modern 2.x patterns.

### Alembic
Database schema migration authority.

Rules:

- Schema migrations only.
- No destructive editorial reseeding.
- Migrations must be deterministic.
- Migration history is committed.
- Production deployment runs migrations as a controlled step.

### PostgreSQL
Primary and canonical database.

Use for:

- Portfolio content.
- Admin users.
- Relationships.
- Contact messages.
- Publication state.
- SEO metadata.
- AI assistant source knowledge.
- Full-text retrieval initially where needed.

---

## 4. Database Access Pattern

Database interaction must be accessed through explicit infrastructure/database abstractions.

Recommended structure:

```text
business service
      ↓
repository / persistence interface
      ↓
SQLAlchemy implementation
      ↓
database session/client
      ↓
PostgreSQL
```

Do not import and execute raw database connection logic throughout business modules.

Suggested infrastructure components:

- `DatabaseClient` or database/session manager.
- Unit-of-work/session boundary where transaction coordination benefits from it.
- Repository interfaces for aggregate-heavy or reusable persistence logic.

Do not force repositories for trivial one-off queries if they add no value, but maintain a clear infrastructure boundary.

---

## 5. External Component Clients

External communication must use dedicated client/adapter implementations.

Examples:

### Email
`EmailClient`

Possible implementations:

- SMTP client.
- Transactional email provider adapter.

### AI
`AIProviderClient`

Responsibilities:

- Provider communication.
- Authentication.
- Request timeout.
- Retry policy where safe.
- Error normalization.
- Model selection.
- Usage/cost metadata where available.

### Media / Object Storage
`StorageClient`

Possible implementations:

- Local persistent storage.
- S3-compatible storage.
- Cloudflare R2.
- MinIO.

### Future Cache
`CacheClient`

Only introduce if needed.

### Future Search
`SearchClient`

Only introduce if PostgreSQL retrieval becomes insufficient.

---

## 6. Client Design Rules

Every external client should:

- Have a small clear interface.
- Normalize provider-specific errors.
- Support configuration injection.
- Define timeouts.
- Apply bounded retries only when safe/idempotent.
- Avoid leaking credentials.
- Be mockable/fakeable for tests.
- Expose health/diagnostic behavior where useful.
- Avoid vendor-specific types leaking deep into domain services.

Use dependency injection to supply concrete implementations.

---

## 7. Monorepo Sub-Services Architecture

The repository contains one FastAPI composition application plus explicit domain sub-services.

```text
apps/api/                    # FastAPI composition root
services/
├── identity/                # profile, resume, socials
├── portfolio/               # projects, skills, sectors, experience, education, metrics, testimonials
├── content/                 # articles, media metadata, homepage, navigation
├── engagement/              # contact, sponsorship
├── assistant/               # AI assistant/retrieval
└── discovery/               # SEO/AEO/GEO, sitemap, structured-data policies
```

Each sub-service:
- Owns its domain/application behavior.
- Publishes only deliberate public contracts.
- May contribute a router to `apps/api`.
- Uses shared external-client contracts from `packages/python/clients`.
- Does not directly import another service's private models/repositories.
- Is independently unit/integration testable.
- Is composed into the same FastAPI deployment by default.

This is a **sub-services architecture**, not a requirement for network microservices.

Typical service package:

```text
service/
├── contracts.py
├── schemas.py
├── service.py
├── policies.py
├── repository.py       # when useful
├── models.py           # when service-owned
├── router.py           # when HTTP exposure exists
├── dependencies.py
└── tests/
```

Avoid rigid folder repetition when a service is simple.

---

## 8. Repository Topology

```text
/
├── apps/
│   ├── web/
│   └── api/
├── services/
├── packages/
│   ├── python/
│   │   ├── contracts/
│   │   ├── clients/
│   │   └── common/
│   └── frontend/
│       ├── ui/
│       ├── motion/
│       ├── api-client/
│       └── config/
├── db/migrations/
├── infrastructure/
├── tests/
└── docs/
```

`packages/frontend/api-client` is the only general-purpose frontend-to-FastAPI transport layer. UI code consumes typed functions rather than hard-coded raw endpoints.

## 8. Design Patterns

Use design patterns when they simplify real problems.

Recommended patterns:

### Dependency Injection
For database/session, AI clients, email clients, storage clients, settings.

### Adapter Pattern
For external providers/components.

### Repository Pattern
For reusable/complex persistence logic.

### Strategy Pattern
For selectable:

- AI provider/model.
- Storage backend.
- Rendering/display variants where appropriate.
- Search/retrieval strategy.
- Email delivery adapter.

### Factory Pattern
For building configured client implementations.

### Unit of Work
Use when multiple repository writes need a coordinated transaction.

### Service Layer
For business behavior spanning multiple models/repositories.

### Specification / Policy Pattern
Useful for publication/visibility rules, feature availability, or filtering when logic becomes complex.

Do not implement patterns merely to increase abstraction count.

---

## 9. Testing Stack

### Backend
Recommended:

- pytest.
- pytest-asyncio where async tests are needed.
- FastAPI test client / httpx.
- Factory fixtures.
- Test PostgreSQL integration for persistence-critical behavior.
- Coverage tooling.

### Frontend
Recommended:

- Vitest.
- React Testing Library.
- Playwright for E2E.
- axe-based accessibility checks.

### Quality
- Ruff for Python linting/formatting where selected.
- mypy or pyright for Python static typing.
- ESLint for TypeScript/Next.js.
- Prettier if required by repository style.
- TypeScript strict mode.

Use one formatter per language and avoid overlapping tools.

---

## 10. Behavior-Driven / Test-Driven Engineering

Critical behaviors should be expressed in tests before or alongside implementation.

Examples:

- “Given an admin-edited seeded project, when seeding runs again, the edit remains.”
- “Given a draft project, when the public project API is called, the project is absent.”
- “Given six featured projects, when homepage work is resolved with the default limit, only five are returned.”
- “Given email delivery failure, when a valid contact form is submitted, the inquiry remains stored.”
- “Given the assistant is disabled, when the public site loads, no assistant entry point is exposed.”
- “Given reduced-motion preference, when the homepage renders, essential content remains available without cinematic animation.”

Tests should focus on behavior and contracts rather than private method implementation.

---

## 11. Deployment Stack

### Docker
All deployable components must have production-ready Dockerfiles.

Requirements:

- Multi-stage builds where useful.
- Non-root runtime user where practical.
- Small production image.
- Explicit dependencies.
- Health checks.
- No development tooling in production image unless needed.
- Graceful shutdown.

### Docker Compose
Baseline production/local orchestration:

- `web`
- `api`
- `db`

Optional services may be added only when justified.

### Reverse Proxy / HTTPS
Deployment should support a standard reverse proxy such as Nginx, Caddy, Traefik, or platform-managed ingress.

Do not hard-code a specific proxy into application logic.

---

## 12. Production Configuration

Use environment-based configuration with validated Pydantic settings.

Required categories:

- Application environment.
- API/public URLs.
- Database.
- Auth.
- Email.
- AI provider.
- Storage.
- CORS.
- Security.
- Logging.
- Rate limiting.
- SEO/public-domain configuration.

Fail fast on invalid required production configuration.

---

## 13. Observability

Baseline:

- Structured logs.
- Request IDs/correlation IDs where useful.
- Error logging.
- Health endpoint.
- Readiness endpoint.
- Startup/migration logging.
- External-client failure logging without secrets.

Optional future integrations:

- Sentry.
- OpenTelemetry.
- Metrics backend.

Architect hooks cleanly, but do not require an observability platform for basic operation.

---

## 14. Security Stack / Practices

- Secure password hashing.
- HttpOnly/Secure/SameSite cookies where applicable.
- CSRF protection when required by auth strategy.
- Restrictive CORS.
- Content Security Policy.
- Security headers.
- Rate limiting.
- Input validation.
- Safe SQLAlchemy parameterization.
- Upload validation.
- Secret management through environment/platform secrets.
- No secrets in Git or frontend.
- Dependency updates/scanning.
- Public/private response-model separation.

---

## 15. Data / Migration / Backup

### Migrations
Alembic is authoritative for schema.

### Seed Data
Dedicated seed subsystem; never use migrations for changing editorial content.

### Backup
Use PostgreSQL-native backup tooling such as `pg_dump`.

### Media
Backup independently from DB if stored as files/object storage.

### Restore
Document and test full restore.

---

## 16. CI Quality Gates

A production-ready CI pipeline should run:

1. Python lint/format check.
2. Python type check.
3. Backend tests.
4. Frontend lint.
5. Frontend type check.
6. Frontend tests.
7. Production frontend build.
8. Production backend import/start smoke test.
9. Migration validation.
10. E2E tests for critical flows.
11. Security/dependency checks where practical.

Do not merge knowingly failing required quality gates.

---

## 17. Explicit Non-Requirements

Do not add by default:

- Kubernetes.
- Microservices.
- Redis.
- Celery.
- Kafka.
- Elasticsearch.
- Dedicated vector DB.
- Service mesh.
- GraphQL.
- Separate BFF.
- Multiple databases.

Add only when a real functional or scale requirement justifies them.
