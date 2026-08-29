# Implementation Plan — V5

## 1. Execution Rules

Use all six authority documents:

1. `goal.md`
2. `BRD.md`
3. `architecture.md`
4. `design_document.md`
5. `tech_stack.md`
6. `implementation_plan.md`

Rules:

- Preserve all useful prior requirements.
- Add capabilities without destructive replacement.
- Keep optional features configurable.
- Use clean code and best practices.
- Use behavior/test-driven implementation.
- Use design patterns only where useful.
- Use the documented **monorepo sub-services architecture**.
- `apps/api` is the FastAPI composition host; domain behavior belongs under `services/*`.
- Do not introduce network microservices unless explicitly justified later.
- Use **TypeScript + Next.js + Tailwind CSS + shadcn/ui** as the frontend foundation.
- Access external components through clients/adapters.
- Every phase must be production-ready within its scope.
- Do not defer repository-controlled quality/security/reliability gaps to “later”.
- No mocks/placeholders in production code paths.

---

## Phase 0 — Monorepo, Sub-Service Skeleton, and Tooling

Create the authoritative topology first:

- `apps/web` — TypeScript + Next.js App Router + React + Tailwind CSS + shadcn/ui.
- `apps/api` — FastAPI composition root.
- `services/*` — identity, portfolio, content, engagement, assistant, discovery.
- `packages/python/contracts`, `packages/python/clients`, `packages/python/common`.
- `packages/frontend/ui`, `packages/frontend/motion`, `packages/frontend/api-client`, `packages/frontend/config`.
- `db/migrations`.
- PostgreSQL.
- Docker/Compose.
- Python/TypeScript strict tooling.
- Ruff.
- Python type checker.
- ESLint.
- Frontend test stack.
- Backend pytest stack.
- Playwright.
- `.env.example`.
- Makefile/root commands.
- CI-ready scripts.

**Exit:** clean clone installs, lints, typechecks, tests, builds, and starts.

---

## Phase 1 — Core Infrastructure Clients

Before business modules, implement infrastructure boundaries:

- Database/session client.
- Email client interface + configured implementation.
- AI provider client interface + implementation.
- Storage client interface + local implementation.
- Typed frontend API client.

Add:

- Config validation.
- Error normalization.
- Timeouts.
- Safe retry rules.
- Test fakes/stubs.

**Exit:** business code can depend on interfaces rather than vendor details.

---

## Phase 2 — Database / Migrations

Implement SQLAlchemy 2 models and Alembic migrations for all canonical entities and relationships.

Add indexes and constraints appropriate to:

- Slugs.
- Publication queries.
- Featured ordering.
- Relationship lookup.
- Contact status.
- Search/retrieval.

**Exit:** empty DB migration succeeds and migration tests pass.

---

## Phase 3 — Domain Sub-Service Foundations

Implement the initial service ownership map:

- `identity` — profile, résumé, social identity.
- `portfolio` — categories, sectors, skills, experience, education, certifications, projects, metrics, testimonials.
- `content` — articles, media metadata, homepage composition, navigation.
- `engagement` — contact and sponsorship.
- `assistant` — assistant retrieval/orchestration.
- `discovery` — SEO/AEO/GEO and structured-discovery behavior.

Keep authentication/platform settings in the composition/core layer unless their behavior becomes large enough to justify their own service.

Each sub-service receives:
- Public application contract.
- Service/business layer.
- Persistence contracts/implementation as needed.
- Client dependencies through injection.
- Behavior tests.
- Router/composition hook only when it exposes HTTP behavior.

Enforce with architecture/import tests where practical:
- No private cross-service repository/model imports.
- `apps/api` composes services but does not own their business rules.
- External provider SDKs do not leak into domain services.

**Exit:** domain ownership is explicit and all sub-services run together through the single FastAPI composition host.

---

## Phase 4 — Authentication / Security Baseline

Implement:

- Admin auth.
- Secure password hashing.
- Session/cookie strategy.
- CSRF where applicable.
- Login rate limiting.
- Admin authorization.
- CORS/security headers.
- Safe error responses.

**Exit:** auth/security tests pass.

---

## Phase 5 — Admin CMS

Implement complete admin CRUD/publishing for all content and settings.

Include:

- Feature toggles.
- Homepage registry/order/variants.
- Resume versions/current asset.
- Project featured rank.
- Metrics approval.
- Testimonials approval.
- Media.
- SEO.
- AI settings.

**Exit:** all canonical public content is configurable through admin.

---

## Phase 6 — Safe Seed System

Implement behavior-first tests for:

- First seed.
- Repeated seed.
- Seed after admin modification.
- Seed after visibility/order changes.
- Missing source fields.
- Unknown source facts.

Then implement deterministic Pydantic-validated seed pipeline.

**Exit:** no destructive reseeding behavior exists.

---

## Phase 7 — Public API

Implement typed public API and publication authority.

Tests first for:

- Draft exclusion.
- Archive behavior.
- Noindex behavior.
- Featured limit.
- Approved metrics/testimonials.
- Feature toggles.
- Current resume route.

**Exit:** public contracts are stable and tested.

---

## Phase 8 — TypeScript Frontend API Client

Implement `packages/frontend/api-client` as the typed transport boundary between the Next.js application and FastAPI.

No scattered raw fetches in presentation components.

Add tests for:

- Error mapping.
- Auth behavior.
- Typed payload handling.
- Public/admin requests.

---

## Phase 9 — Base UI / Accessibility

Implement:

- Design tokens.
- Dark/light/system.
- Typography.
- Layout.
- Navigation.
- Forms.
- Focus behavior.
- Reduced motion.
- Responsive foundations.

**Exit:** static accessible site foundation passes checks.

---

## Phase 10 — Public Pages

Implement all public pages and all prior content capabilities before cinematic effects.

Server-render important data.

**Exit:** site is complete and useful without advanced motion.

---

## Phase 11 — Personal Hero / Resume

Implement personal portrait management/presentation, availability, CTA, stable résumé download, responsive/reduced-motion behavior.

Add behavior/E2E tests for resume replacement and stable route.

---

## Phase 12 — Portfolio Focus

Implement category presentation, selected work, full archive, metrics, testimonials, case-study summaries.

Default featured project limit: five, configurable.

---

## Phase 13 — Sectors / Skills

Implement sector relationships/UI and technology universe with semantic fallbacks.

---

## Phase 14 — Motion System

Implement reusable animation primitives and clear library ownership.

Test reduced-motion behavior and avoid content dependence on animation.

---

## Phase 15 — Cinematic Homepage

Implement hero motion, typography, marquees, scroll scenes, selected-work storytelling, metrics, sectors, technology universe, experience/open-source motion, closing CTA.

---

## Phase 16 — Project Case Studies

Implement deep case studies with sticky storytelling, architecture visuals, metrics, testimonials, tradeoffs, outcomes, media, related work.

---

## Phase 17 — Contact Service

Behavior-first tests:

- Valid message persists.
- Invalid message rejected.
- Rate limit works.
- Email failure does not lose stored inquiry.

Then implement contact service through `EmailClient`.

---

## Phase 18 — AI Assistant Service

Behavior-first tests:

- Only published content retrieved.
- Disabled assistant unavailable.
- Missing facts produce uncertainty.
- Provider failure handled safely.
- Private/admin/contact data never included.

Implement through `AIProviderClient`.

---

## Phase 19 — Media / Storage

Implement through `StorageClient`.

Test:

- Type/size validation.
- Safe replace/delete.
- Portrait.
- Resume.
- Project media.
- Persistence.

---

## Phase 20 — Open Source / Sponsorship / Writing

Implement all optional modules with feature toggles and admin control.

---

## Phase 21 — SEO / AEO / GEO

Implement metadata, canonical, OG, JSON-LD, sitemap, robots, index/noindex, sameAs, breadcrumbs, internal links, factual machine-readable text, social preview.

Add automated validation.

---

## Phase 22 — Database / Query Quality Pass

Review:

- N+1.
- Indexes.
- Query plans where needed.
- Pagination.
- Transaction boundaries.
- Connection pooling.
- Repository/service ownership.

---

## Phase 23 — Security Hardening

Review auth, CSRF, CORS, CSP, headers, rate limits, uploads, external clients, secrets, logs, serializers, admin access, assistant/contact privacy, dependencies.

---

## Phase 24 — Performance Pass

Measure:

- Core Web Vitals.
- JS bundles.
- R3F/GSAP cost.
- Images/video/fonts.
- API latency.
- DB queries.

Optimize based on measurements.

---

## Phase 25 — Accessibility Pass

Keyboard, focus, screen readers, forms/errors, contrast, reduced motion, mobile, non-WebGL fallback.

---

## Phase 26 — Production Docker / Operations

Build production Docker images and Compose deployment.

Implement/test:

- Non-root runtime where practical.
- Health/readiness.
- Graceful shutdown.
- Persistent volumes.
- Controlled migrations.
- Environment validation.
- Restart behavior.
- Structured logs.
- Reverse proxy/HTTPS docs.

---

## Phase 27 — Backup / Restore

Implement PostgreSQL and media backup/restore scripts.

Perform documented restore test.

---

## Phase 28 — CI Quality Gates

Required gates:

- Python lint/format.
- Python typing.
- Backend tests.
- Frontend lint.
- Frontend typing.
- Frontend tests.
- Production builds.
- Migration validation.
- E2E critical flows.
- Security/dependency checks where practical.

---

## Phase 29 — Final Production Verification

Manual and automated verification of:

1. Public site.
2. Personal photo.
3. Résumé.
4. Categories.
5. Sectors.
6. Skills.
7. Projects.
8. Metrics/testimonials.
9. Experience.
10. Open source.
11. Sponsorship.
12. Writing.
13. Contact.
14. AI assistant.
15. Admin.
16. Feature toggles.
17. Seed safety.
18. Publication privacy.
19. SEO/AEO/GEO.
20. Motion/reduced motion.
21. Performance.
22. Accessibility.
23. Security.
24. Docker.
25. Persistence.
26. Backup/restore.
27. External-client failure behavior.
28. Monorepo sub-service import/ownership boundaries.
29. All public/admin frontend application code uses TypeScript.
30. Next.js/Tailwind/shadcn design-system implementation is consistent.
31. Presentation components do not bypass the typed frontend API client for normal backend communication.

---

## Completion Standard

A feature is complete only when:

- Behavior is implemented.
- Tests pass.
- Errors are handled.
- External dependencies use proper clients/adapters.
- Security concerns are addressed.
- Production configuration exists.
- Documentation is current.
- No placeholder/mock production path remains.
