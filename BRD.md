# Business Requirements Document (BRD) — V5

## 1. Executive Summary

The product is a premium personal-branding, technical portfolio, open-source showcase, and professional-discovery platform.

It must combine rich animation and visual storytelling with strong engineering quality, clean architecture, testability, and production readiness.

No useful existing capability should be removed merely to add another. Optional features should be modular and reversible.

---

## 2. Business Objectives

- Establish a strong personal brand.
- Present personal photo and résumé prominently.
- Demonstrate AI, software/product, data/infrastructure expertise.
- Show sectors/domains where capabilities were applied.
- Present selected flagship work and full project archive.
- Use real metrics and approved testimonials.
- Showcase broad skills/tools.
- Support open source, sponsorship, writing, AI assistant, and contact.
- Maximize SEO/AEO/GEO and AI discovery.
- Allow almost all content to be admin-managed.
- Preserve future optionality.
- Deliver production-grade engineering quality.

---

## 3. Engineering Business Requirements

### EBR-01 — Clean Code
Code must be readable, cohesive, typed, documented where needed, and free of unnecessary duplication.

### EBR-02 — Best Practices
Use framework and language best practices for FastAPI, Next.js, SQLAlchemy, PostgreSQL, Docker, and security.

### EBR-03 — Behavior Driven
Critical requirements must be represented as behavior-oriented tests/acceptance criteria.

### EBR-04 — Test Driven
Important business rules should have tests before or alongside implementation.

### EBR-05 — Design Patterns
Use proven patterns where they reduce coupling or improve extensibility.

### EBR-06 — Monorepo Sub-Services Architecture
The repository must use a monorepo sub-services architecture. `apps/api` is the FastAPI composition host; domain behavior is owned by explicit packages under `services/*`. Sub-services are composed into one backend deployment by default and must communicate through public contracts rather than private cross-imports.

### EBR-07 — External Clients
Database, email, AI, storage, and future external systems must be accessed through explicit clients/adapters or infrastructure interfaces.

### EBR-08 — Frontend Technology
The frontend must use **TypeScript, Next.js App Router, React, Tailwind CSS, and shadcn/ui** as its mandatory foundation, with Motion/GSAP/React Three Fiber for the agreed interaction layer. Backend communication must go through a typed API client.

### EBR-09 — Production Ready
Every implemented feature must include its production concerns: validation, error handling, security, configuration, tests, logging, migrations/persistence where applicable, and documentation.

---

## 4. Functional Scope

Retain all V3 functional capabilities:

- Home.
- Personal portrait.
- Resume.
- Categories.
- Sectors.
- Skills/tools.
- Experience.
- Education.
- Certifications.
- Projects.
- Metrics.
- Testimonials.
- Open source.
- Sponsorship.
- Contact.
- Articles.
- AI assistant.
- Admin.
- Media.
- Homepage composition.
- Feature visibility.
- Publishing/archive/noindex.
- SEO/AEO/GEO.
- Safe seeding.
- Docker deployment.
- Backup/restore.

---

## 5. Homepage Requirements

Configurable modules:

- Hero/personal identity.
- Resume CTA.
- Availability.
- What I Build.
- Categories.
- Selected work.
- Metrics.
- Testimonials.
- Sectors.
- Technology universe.
- Experience.
- Education/certifications.
- Open source.
- Sponsorship.
- Writing.
- AI CTA.
- Contact.
- Social links.
- Curated editorial sections.

Admin may enable, disable, reorder, and select supported display variants.

---

## 6. External Component Requirements

### Database
All database lifecycle and access must flow through explicit database/session infrastructure and repository/service boundaries.

### Email
Use an `EmailClient` abstraction.

### AI
Use an `AIProviderClient` abstraction.

### Storage
Use a `StorageClient` abstraction.

### Frontend Backend Communication
Use a typed frontend API client layer. Components should not scatter raw endpoint handling throughout the UI.

---

## 7. Design Pattern Requirements

Patterns may include:

- Dependency Injection.
- Adapter.
- Strategy.
- Factory.
- Repository.
- Unit of Work.
- Service Layer.
- Policy/Specification.
- Registry.

Only use a pattern when it solves a concrete coupling, configuration, lifecycle, or extensibility problem.

---

## 8. Testing Requirements

Required behavioral coverage includes:

- Publication/privacy.
- Seed preservation.
- Feature toggles.
- Resume current-file behavior.
- Featured project limits.
- Metric/testimonial approval.
- Contact persistence on email failure.
- AI public-data isolation.
- Admin authentication/authorization.
- Media validation.
- SEO/public indexing rules.
- Reduced-motion behavior.
- Critical public/admin journeys.

---

## 9. Production Requirements

- Production Docker images.
- PostgreSQL persistence.
- Controlled Alembic migrations.
- Non-destructive seeding.
- Validated environment configuration.
- Graceful startup/shutdown.
- Health/readiness.
- Structured logging.
- Rate limiting.
- Secure headers/CORS.
- Upload controls.
- External-client timeouts.
- Safe retry policies.
- Backup/restore.
- Dependency management.
- CI quality gates.
- Documentation.
- No dev-only shortcuts in production paths.

---

## 10. Non-Functional Requirements

### Performance
Protect Core Web Vitals, DB efficiency, page rendering, and WebGL cost.

### Accessibility
WCAG 2.2 AA principles.

### Security
Modern auth/security practices, least exposure, secure secrets, safe serializers, rate limiting.

### Reliability
Data persistence, safe errors, external-service failure tolerance, backups.

### Maintainability
Typed modular code, clear ownership, interfaces, test coverage, docs.

### Observability
Structured logs, health/readiness, useful diagnostic context without leaking secrets.

---

## 11. Acceptance Criteria

The product is accepted when:

- All public/content features remain intact.
- Tech-stack specification is implemented consistently.
- External components use client/adapter boundaries.
- The repository follows the documented monorepo sub-services topology.
- Backend behavior is owned by explicit sub-services and composed through `apps/api`.
- The frontend is TypeScript + Next.js + Tailwind + shadcn/ui with a typed API-client boundary.
- Critical behavior has automated tests.
- Design patterns are used intentionally.
- Code quality checks pass.
- Production Docker build/start works.
- Migrations and seed behavior are deterministic/safe.
- Public/private boundaries are enforced.
- External-provider failures degrade safely.
- Performance/accessibility/security checks pass.
- Backup/restore is tested.
- No repository-controlled production-readiness gap remains.
