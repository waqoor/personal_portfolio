# Goal — Personal Branding & Portfolio Platform (V5)

## 1. Mission

Build a production-ready personal branding and technical portfolio platform that presents the owner as an **AI, software/product, data, infrastructure, and open-source builder**.

The platform must combine:

- Strong personal branding and photography.
- Rich visualizations, animation, and motion.
- Clear professional structure.
- Deep project case studies.
- Broad technical skills and tools.
- Sectors/domains where experience has been applied.
- Experience, education, certifications, achievements, metrics, and testimonials.
- Open-source work and sponsorship.
- Downloadable résumé.
- Contact workflows.
- Portfolio-aware AI assistant.
- Technical writing.
- Strong SEO, AEO, GEO, and AI/agent discoverability.
- Secure CMS-like administration.
- Safe initial résumé/LinkedIn seeding.
- Production-grade engineering, testing, deployment, and operational readiness.

The frontend may be visually ambitious. The underlying architecture must remain clean, modular, testable, maintainable, and operationally simple.

---

## 2. Engineering Goal

The repository must be built as production software, not as a visual prototype.

Required engineering principles:

- Clean Code.
- SOLID principles where useful.
- Behavior-driven development.
- Test-driven development for important business behavior.
- Strong typing.
- Explicit interfaces and contracts.
- Dependency inversion around external components.
- Design patterns used intentionally, not decoratively.
- **Monorepo sub-services architecture:** all applications, domain sub-services, shared packages, infrastructure, tests, and documentation live in one repository with explicit service boundaries.
- A FastAPI composition host exposes the backend API while domain behavior is owned by isolated sub-service packages.
- **TypeScript-first frontend:** Next.js App Router + TypeScript + Tailwind CSS + shadcn/ui are the mandatory frontend foundation.
- Production-ready configuration, logging, security, migrations, backups, health checks, error handling, and deployment.
- No direct coupling of domain/business logic to external infrastructure when an interface/client boundary is appropriate.

---

## 3. Monorepo Sub-Services Architecture

Use a **single monorepo containing the frontend application, FastAPI composition host, domain sub-services, shared packages, infrastructure, tests, and documentation**.

The backend is organized as independently owned **domain sub-services**. These are code/service boundaries, not mandatory network microservices. The default production deployment composes them into the FastAPI API process so the platform stays operationally simple.

Each sub-service:
- Owns its business behavior.
- Owns its application/service layer and persistence contracts.
- Exposes a small public Python contract to the composition host and other allowed consumers.
- Must not reach into another sub-service's private models/repositories.
- Communicates with external components only through shared client/adapter contracts.
- Is independently testable.
- Can later be extracted into an independently deployed service if real scale or operational requirements justify it, without redesigning the domain boundary.

Examples:

- Auth Service.
- Profile Service.
- Résumé Service.
- Portfolio/Projects Service.
- Skills Service.
- Sectors Service.
- Experience Service.
- Media Service.
- Contact Service.
- Sponsorship Service.
- Article Service.
- SEO/Discovery Service.
- Assistant Service.
- Settings/Configuration Service.

Each sub-service owns its business rules and exposes clear service methods/contracts.

This is **not** a microservices architecture. Do not create separate network services unless a future requirement explicitly justifies it.

---

## 4. External Component Client Rule

All communication with infrastructure or external systems must go through explicit client/adapter code.

Examples:

- `DatabaseClient` / database session provider.
- `EmailClient`.
- `AIProviderClient`.
- `StorageClient`.
- `CacheClient` if caching is introduced.
- `SearchClient` if a future external search engine is introduced.
- `AnalyticsClient` if server-side analytics integration is introduced.

Business services must not scatter vendor/library-specific calls throughout the codebase.

The application should depend on interfaces/contracts, with concrete adapters selected through configuration/dependency injection.

---

## 5. Public Professional Positioning

Default public emphasis:

1. **AI & Intelligent Systems**
2. **Software & Product Engineering**
3. **Data & Infrastructure**

Categories remain configurable and can be renamed, reordered, added, hidden, archived, or removed later.

---

## 6. Portfolio Focus

Default presentation:

- Up to five featured projects.
- Strongest three receive richer storytelling.
- Complete project archive remains available.
- Evidence and outcomes are prioritized over vague descriptions.
- Real verified metrics are used where available.
- Approved testimonials are supported.
- No fabricated metrics, testimonials, users, adoption, impact, or achievements.

These are presentation defaults, not hard schema constraints.

---

## 7. Visual Direction

Supported capabilities include:

- Personal portrait in hero.
- Animated hero scene.
- Theme-aware visual environment.
- Moving typography.
- Marquee/ticker motion.
- Scroll-linked transitions.
- Sticky/pinned storytelling.
- Mask/clip reveals.
- Parallax.
- Cursor-responsive effects.
- Magnetic CTAs.
- Card tilt/depth.
- Animated verified metrics.
- Interactive sector visualization.
- Interactive skills/tool universe.
- Timeline animation.
- Project transitions.
- Page transitions.
- Three.js / React Three Fiber.
- Particles, shaders, geometry, or abstract data visuals.
- Dark/light/system themes.
- Reduced-motion and mobile fallbacks.

Motion must support the narrative and never become the only carrier of important content.

---

## 8. Homepage Modules

Supported configurable modules:

1. Hero / personal identity.
2. Résumé CTA.
3. Availability/status.
4. What I Build.
5. Professional categories.
6. Selected/Signature Work.
7. Impact metrics.
8. Testimonials.
9. Sectors/domains.
10. Technology universe.
11. Experience snapshot.
12. Education/certifications snapshot.
13. Open-source spotlight.
14. Sponsorship CTA.
15. Writing/articles preview.
16. AI assistant CTA.
17. Contact CTA.
18. Social links.
19. Optional curated editorial blocks.

Each section should be configurable, reorderable, hideable, and replaceable by a supported display variant.

---

## 9. Technology Baseline

See `tech_stack.md` for the authoritative stack.

Core baseline:

### Frontend — Mandatory Foundation
- **TypeScript** in strict mode for application code.
- **Next.js** using the App Router.
- **React**.
- **Tailwind CSS**.
- **shadcn/ui**, heavily customized to the portfolio design system.
- Motion / Framer Motion.
- GSAP + ScrollTrigger.
- Three.js / React Three Fiber.
- next-themes.
- Typed frontend API client generated/shared from FastAPI/OpenAPI contracts where practical.

Do not introduce a second frontend framework or plain-JavaScript application path.

### Backend
- Python.
- FastAPI.
- Pydantic.
- SQLAlchemy 2.x.
- Alembic.
- PostgreSQL.

### Deployment / Operations
- Docker.
- Docker Compose.
- Persistent database and media storage.
- Reverse proxy / HTTPS.
- Production environment configuration.
- Structured logs.
- Health/readiness checks.
- Backup/restore.

---

## 10. Content Authority

PostgreSQL owns canonical structured content.

The same data powers:

- Public site.
- Admin.
- Internal relationships.
- SEO metadata.
- JSON-LD.
- Sitemaps.
- AI assistant retrieval.

---

## 11. Testing Goal

The platform is behavior- and test-driven.

Important behavior should be specified before or alongside implementation through tests.

Required test levels:

- Unit tests.
- Service/business behavior tests.
- Repository/client adapter tests.
- API integration tests.
- Migration tests.
- Seed-safety tests.
- Frontend component tests.
- Accessibility tests.
- E2E tests.
- Security-sensitive behavior tests.
- Production build tests.

Tests should validate observable behavior rather than internal implementation details whenever practical.

---

## 12. Production Readiness Goal

Production readiness includes:

- Secure configuration.
- Environment validation.
- Database migrations.
- Non-destructive startup.
- Persistence.
- Backup/restore.
- Graceful shutdown.
- Health/readiness.
- Structured logging.
- Safe error handling.
- Request correlation where useful.
- Rate limiting.
- Security headers.
- Upload protection.
- Dependency/version management.
- CI-quality checks.
- Production Docker images.
- Deployment documentation.
- No placeholder production paths.
- No mock integrations in production code paths.

---

## 13. Safe Growth and Removal

Optional features should support:

- Hide.
- Disable.
- Archive.
- Deprecate.
- Remove through deliberate migration.

Removing a public feature must not automatically destroy its data.

---

## 14. Definition of Success

The repository is complete when:

1. It runs from a clean checkout.
2. PostgreSQL migrations are deterministic.
3. Résumé/LinkedIn seed data is safe and idempotent.
4. Personal photo and résumé are first-class managed assets.
5. Sectors, skills, experience, projects, open source, metrics, and testimonials are fully modeled.
6. Homepage/public modules are configurable.
7. Premium motion works with reduced-motion/mobile fallbacks.
8. Admin manages canonical content.
9. External components are accessed through explicit client/adapter boundaries.
10. Backend uses clear sub-services/modules.
11. Design patterns are applied appropriately.
12. Critical behavior is covered by tests.
13. Public/private publication boundaries are enforced.
14. Contact and AI workflows are production-ready.
15. SEO/AEO/GEO is fully implemented.
16. Data survives rebuilds and restarts.
17. Backup/restore works.
18. Production Docker deployment is documented and tested.
19. Security, accessibility, performance, linting, typing, tests, and builds pass.
20. No feature is considered complete while repository-controlled production gaps remain.


---

## 15. Authoritative Monorepo Topology

The target repository shape is:

```text
/
├── apps/
│   ├── web/                         # Next.js + TypeScript public site + admin UI
│   └── api/                         # FastAPI composition root / HTTP entrypoint
├── services/
│   ├── identity/                    # profile, resume, socials
│   ├── portfolio/                   # projects, skills, sectors, experience, education, metrics, testimonials
│   ├── content/                     # articles, media metadata, homepage composition, navigation
│   ├── engagement/                  # contact and sponsorship behavior
│   ├── assistant/                   # AI assistant and retrieval orchestration
│   └── discovery/                   # SEO/AEO/GEO, sitemap, structured-data policies
├── packages/
│   ├── python/
│   │   ├── contracts/               # shared interfaces/value contracts
│   │   ├── clients/                 # database/email/AI/storage client contracts + reusable adapters
│   │   └── common/                  # small cross-cutting utilities only
│   └── frontend/
│       ├── ui/                      # shared UI/design system
│       ├── motion/                  # reusable motion primitives
│       ├── api-client/              # typed FastAPI client
│       └── config/
├── db/
│   └── migrations/                  # Alembic migration authority
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

The exact number of sub-services may evolve, but the architecture rule remains: **one monorepo, explicit service ownership, shared contracts rather than private cross-service imports, and a single FastAPI composition host by default.**
