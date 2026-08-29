# Architecture — V5

## 1. Architecture Style

Use a **production-ready monorepo sub-services architecture**.

All applications and sub-services live in one repository. Domain behavior is separated into explicit sub-service packages, while a **FastAPI composition host** exposes one backend HTTP surface by default. This preserves strong service boundaries without introducing unnecessary distributed-network complexity.

```text
Visitors / Crawlers
       |
 Reverse Proxy / HTTPS
     /             \
Next.js           FastAPI Composition Host
(TypeScript)             |
                         +-------------------------------+
                         |       Domain Sub-Services     |
                         | identity | portfolio | content|
                         | engagement | assistant | SEO  |
                         |       public catalog          |
                         +-------------------------------+
                                  |
                         Client / Adapter Layer
                    +-------------+-------------+
                    |             |             |
                PostgreSQL      Email       AI / Storage
```

Sub-services are **independently owned code/service boundaries**. They are composed into one API deployment initially, but their contracts must allow future extraction if genuinely needed.

---

## 2. Architecture Principles

1. Clean Code.
2. Behavior-driven and test-driven implementation.
3. Explicit boundaries.
4. Dependency inversion.
5. External systems accessed through clients/adapters.
6. Domain/business logic separated from infrastructure.
7. Modular sub-service ownership.
8. Reversible optional features.
9. Production readiness by default.
10. No unnecessary distributed complexity.

---

## 3. Monorepo Topology

```text
/
├── apps/
│   ├── web/                         # Next.js + TypeScript + Tailwind + shadcn/ui
│   └── api/                         # FastAPI composition root / HTTP API
├── services/
│   ├── identity/
│   ├── portfolio/
│   ├── content/
│   ├── engagement/
│   ├── assistant/
│   ├── discovery/
│   └── public_catalog/
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
├── db/
│   └── migrations/
├── infrastructure/
│   ├── docker/
│   └── scripts/
├── tests/
├── docs/
├── docker-compose.yml
├── Makefile
├── .env.example
└── README.md
```

**Ownership rules**
- `apps/api` is a composition root, not the owner of domain behavior.
- `services/*` own domain/application behavior.
- `packages/python/contracts` contains deliberately shared interfaces only.
- No sub-service may import another sub-service's private repository/model implementation.
- Cross-service collaboration uses explicit public service contracts.
- External systems are always reached through client/adapter contracts.
- `apps/web` is the only frontend application and uses TypeScript + Next.js.

---

## 4. Sub-Service Architecture

Each service is a Python package with a deliberate public boundary. Recommended service-internal shape:

```text
services/<service_name>/
├── __init__.py
├── contracts.py              # public application interfaces / DTOs if needed
├── schemas.py                # Pydantic boundary schemas
├── service.py                # application/business behavior
├── policies.py               # business policies/specifications where useful
├── repository.py             # persistence interface/implementation when useful
├── models.py                 # service-owned SQLAlchemy models when appropriate
├── dependencies.py
├── router.py                 # optional FastAPI router contributed to apps/api
└── tests/
```

A service does not need every file. Keep simple services simple.

Suggested ownership:

- `identity`: profile, portraits, résumé, social links.
- `portfolio`: professional categories, sectors, skills, experience, education, certifications, projects, metrics, testimonials.
- `content`: articles, media metadata, homepage sections, navigation.
- `engagement`: contact and sponsorship.
- `assistant`: public AI assistant retrieval/orchestration.
- `discovery`: SEO/AEO/GEO policies, structured data, sitemap/indexability.
- `public_catalog`: cross-domain aggregation of sanitized public contracts for assistant and
  discovery consumers; it never imports another service's private repository or model.

`apps/api` imports each service's **public router/composition hook only** and registers it with FastAPI.

---

## 5. Sub-Service Responsibilities

Each module owns:

- Domain/business behavior.
- Input/output schemas.
- Persistence coordination.
- Publication rules related to its data.
- Tests for its behavior.

Cross-module calls occur through service interfaces rather than reaching into each other's internal persistence logic.

---

## 6. External Client Layer

All external infrastructure communication must be isolated.

### Database
The database layer owns:

- Engine creation.
- Session lifecycle.
- Transaction handling.
- Connection health.

Business services receive repositories/session abstractions through dependency injection.

### Email
Contact/email delivery goes through `EmailClient`.

Contact acceptance and email delivery are separate transactions. `engagement` atomically persists
the submission and its outbox operation, then a lifespan-owned worker acquires bounded leases and
delivers with provider idempotency, bounded retry, and stale-lease recovery. Delivery failure cannot
roll back or duplicate an accepted contact.

### AI
Assistant/provider communication goes through `AIProviderClient`.

### Storage
Media/files go through `StorageClient`.

Concrete client adapters are selected using configuration/factory logic.

External-provider exceptions should be normalized into application-level exceptions.

---

## 7. Dependency Direction

Preferred dependency flow:

```text
API router
   ↓
application/service layer
   ↓
domain policies / contracts
   ↓
repository/client interfaces
   ↓
infrastructure adapters
```

Infrastructure must not become the owner of business rules.

---

## 8. Design Patterns

Apply intentionally:

- Dependency Injection.
- Adapter.
- Strategy.
- Factory.
- Repository where beneficial.
- Unit of Work where transaction coordination is needed.
- Service Layer.
- Policy/Specification for publication/visibility.
- Registry pattern for homepage sections/display variants.

Avoid needless abstractions.

---

## 9. Frontend Architecture

Use Next.js App Router.

Main layers:

- Server-rendered content pages.
- Client-side interaction islands.
- UI design system.
- Motion primitives.
- Three.js scenes.
- Admin interface.
- API client layer.

Frontend should use an explicit API/client wrapper rather than scattering raw fetch calls throughout components.

Example:

```text
component / server page
       ↓
portfolioApi client
       ↓
FastAPI
```

This client handles:

- Base URL.
- Typed requests.
- Error normalization.
- Timeouts where applicable.
- Auth handling for admin.
- Contract consistency.

---

## 10. Frontend Architecture — Mandatory Stack

`apps/web` uses:

- TypeScript strict mode.
- Next.js App Router.
- React.
- Tailwind CSS.
- shadcn/ui as accessible primitives, customized to the brand.
- Motion / Framer Motion.
- GSAP + ScrollTrigger.
- Three.js / React Three Fiber.
- next-themes.
- Optional Lenis only when accessibility/native behavior remain correct.

Recommended route/component organization:

```text
apps/web/
├── app/
│   ├── (public)/
│   └── (admin)/
├── components/
├── features/
├── lib/
└── styles/
```

Shared frontend packages live under `packages/frontend`.

All backend calls go through `packages/frontend/api-client` (or an equivalent typed API client). Presentation components must not scatter raw endpoint URLs and ad-hoc `fetch()` behavior.

---

## 10. Homepage Section Registry

Use a known registry of supported section types.

Each section supports configuration such as:

- enabled
- order
- variant
- animation variant
- data limit
- CTA visibility
- theme option

Unknown/untrusted component names are never dynamically executed.

---

## 11. Optionality Model

Feature lifecycle:

1. Hide.
2. Disable.
3. Archive.
4. Deprecate.
5. Remove deliberately.

Data survives hide/disable/archive.

---

## 12. Core Data Model

Core entities:

- AdminUser.
- Profile.
- ProfileMedia.
- ResumeAsset/ResumeVersion.
- ProfessionalCategory.
- Sector.
- SocialLink.
- Experience.
- Education.
- Certification.
- Skill.
- Project.
- ProjectMedia.
- ImpactMetric.
- Testimonial.
- Article.
- SponsorshipLink/Tier.
- HomepageSection.
- NavigationItem.
- ContactCategory/Submission.
- MediaAsset.
- FeatureSetting.
- SiteSetting.
- AssistantSetting.

Relationships connect projects, skills, sectors, experience, articles, metrics, and testimonials.

---

## 13. Publication / Approval Authority

Backend policies govern:

- Draft.
- Published.
- Hidden.
- Archived.
- Noindex.
- Metric approval.
- Testimonial approval.

Public API, sitemap, JSON-LD, assistant, and rendering all reuse the same authority.

Public projections are dedicated, sanitized contracts. Publication is compositional across every
populated ancestor, current identity assets are bound to the exact selected public profile, and
approval audit/private evidence never crosses the public boundary. Structured evidence approval is
bound to the reviewed content and evidence revision and is revoked by material change.

Feature resolution has explicit `unconfigured`, `enabled`, `disabled`, and `archived` states. Runtime
capability is applied first, persisted state second, and a bootstrap default only when no setting has
ever existed. Action-bearing surfaces fail closed when the authority cannot be loaded.

---

## 14. Seeding Architecture

Dedicated seed subsystem:

- Pydantic validation.
- Stable seed keys.
- Safe create-missing behavior.
- Field/provenance awareness where useful.
- No destructive startup reseeding.
- No resetting manual order/visibility/feature settings.
- Testable independently.

---

## 15. Behavior-Driven Architecture

Important business invariants are encoded in tests.

Examples:

- Draft content never leaks.
- Seed reruns preserve admin edits.
- Disabling a feature hides it but preserves content.
- Resume route always resolves current published file.
- Contact remains stored when email delivery fails.
- Assistant cannot retrieve private content.

Architecture decisions should make these behaviors easy to test without needing the full external environment.

---

## 16. Testing Architecture

Use dependency injection and client interfaces so tests can replace:

- Database repositories.
- Email client.
- AI provider.
- Storage.
- Clock/time where needed.

Maintain separate test layers:

- Unit.
- Service.
- Integration.
- API.
- Frontend component.
- E2E.

Use real PostgreSQL integration tests for persistence-critical logic rather than relying only on mocks.

---

## 17. Motion Architecture

CSS → basic transitions.

Motion → UI/micro-interactions.

GSAP → complex scroll choreography.

R3F → WebGL/3D.

Central motion tokens and reusable primitives prevent duplicated animation logic.

---

## 18. SEO / Rendering Architecture

```text
PostgreSQL
  ↓
FastAPI canonical public data
  ↓
Next.js SSR / bounded tagged revalidation
  ├── semantic HTML
  ├── metadata
  ├── canonical
  ├── JSON-LD
  ├── breadcrumbs
  └── interactive enhancement
```

Canvas/WebGL remains supplementary.

Publication mutations invalidate explicit Next.js cache tags through a same-origin,
proxy-aware server route. Production keeps the application root read-only and mounts only the
bounded `.next/cache` path writable. Discovery dependency failures use a bounded last-known-good
document or conservative `noindex, nofollow`; they never manufacture an indexable identity.

---

## 19. Production Architecture

Production must include:

- Validated environment settings.
- Production Docker images.
- Non-root runtime where practical.
- Graceful shutdown.
- Health/readiness.
- Database connection pooling.
- Controlled migrations.
- Persistent storage.
- Structured logs.
- Rate limiting.
- Security headers.
- Backup/restore.
- Failure-safe email/AI handling.
- No development-only settings in production.

---

## 20. Deployment

Docker Compose baseline:

- web.
- api.
- db.

Reverse proxy terminates HTTPS.

No microservice split is required.

---

## 21. Observability

Baseline:

- Structured logs.
- Request IDs.
- Health/readiness.
- External-client error normalization/logging.
- Startup/shutdown logs.
- Safe exception reporting.

Optional integrations can be added later without changing business services.

---

## 22. Architecture Decisions

1. Monorepo sub-services architecture with a FastAPI composition host.
2. External components behind client/adapter boundaries.
3. Dependency injection for infrastructure.
4. Design patterns only where they reduce coupling.
5. PostgreSQL canonical authority.
6. Typed frontend API client.
7. Behavior-driven tests protect business invariants.
8. Production readiness is part of definition of done.
9. Visual sophistication does not justify backend complexity.
10. Optional features remain reversible.
