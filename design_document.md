# Technical Design Document — V5

## 1. Objective

Translate the platform requirements into an implementation-ready technical design emphasizing:

- Premium UI/UX.
- Clean code.
- Monorepo sub-services architecture.
- FastAPI composition root with domain-owned sub-services.
- TypeScript + Next.js + Tailwind CSS + shadcn/ui frontend.
- External client/adapter boundaries.
- Design-pattern discipline.
- Behavior/test-driven development.
- Production readiness.
- Feature reversibility.

---

## 2. Monorepo Sub-Service Contract

Backend domain behavior lives under `services/*`; `apps/api` is the FastAPI composition host.

A sufficiently complex sub-service may contain:

```text
services/<service_name>/
├── router.py
├── schemas.py
├── service.py
├── repository.py
├── policies.py
├── dependencies.py
└── tests/
```

Simple modules may use fewer files.

### Router
HTTP concerns only:

- Validation integration.
- Authentication/authorization.
- Status codes.
- Calling service layer.
- Mapping service results to responses.

### Service
Owns business behavior.

### Repository
Owns reusable persistence operations when a repository abstraction improves clarity/testability.

### Policies
Owns rules such as publication, visibility, approval, or feature availability.

### Cross-Service Rule
A sub-service may consume another sub-service only through an explicitly exported application contract. It must never reach into another service's private SQLAlchemy models, repositories, internal helpers, or router implementation.

### Composition Root
`apps/api` wires settings, clients, database dependencies, sub-service dependencies, and routers into the FastAPI application. Composition and dependency construction belong here rather than inside domain behavior.

---

## 3. External Client Design

### Database Client / Session Manager

Responsibilities:

- Engine lifecycle.
- Connection pooling.
- Session creation.
- Transaction lifecycle.
- Health check.
- Graceful cleanup.

Do not expose raw connection setup across modules.

### Email Client

Interface example:

```text
send_contact_notification(...)
send_system_email(...)
```

Concrete adapter may use SMTP or another provider.

### AI Provider Client

Interface example:

```text
generate(...)
health_check(...)
```

Provider-specific payloads should not leak into assistant business logic.

### Storage Client

Interface example:

```text
save(...)
delete(...)
open/read(...)
public_url(...)
```

Concrete local and S3-compatible adapters can implement the same contract.

---

## 4. Dependency Injection

FastAPI dependencies/factories should provide:

- Settings.
- DB session/UoW.
- Repositories.
- Email client.
- AI client.
- Storage client.
- Auth/session dependencies.

Tests replace these cleanly.

---

## 5. Frontend Client Layer

Create typed API modules such as:

```text
lib/api/
├── client.ts
├── public.ts
├── admin.ts
├── projects.ts
├── profile.ts
├── assistant.ts
└── contact.ts
```

Do not scatter raw `fetch()` calls inside presentation components.

Client layer owns:

- URL construction.
- Typed responses.
- Error normalization.
- Authentication headers/cookies where required.
- Request cancellation/timeouts when relevant.

---

## 6. Frontend Technical Design

### Mandatory Stack
- TypeScript strict mode.
- Next.js App Router.
- React.
- Tailwind CSS.
- shadcn/ui customized to the brand.
- Motion / Framer Motion.
- GSAP + ScrollTrigger.
- React Three Fiber / Three.js.
- next-themes.
- Typed API client.

### Frontend Boundaries

```text
apps/web/
├── app/
│   ├── (public)/
│   └── (admin)/
├── features/
├── components/
└── lib/

packages/frontend/
├── ui/
├── motion/
├── api-client/
└── config/
```

- Server Components/server rendering are preferred for content-heavy public surfaces.
- Client Components are limited to actual interactive behavior.
- Raw endpoint URLs and ad-hoc fetch behavior are not scattered through components.
- `api-client` owns request typing, normalized errors, authentication transport, and common transport behavior.
- shadcn/ui primitives must be visually customized; the public portfolio must not resemble a default component-library demo.

---

## 6. Public UX

Retain all previously specified public modules:

- Personal-photo hero.
- Resume download.
- Categories.
- Selected work.
- Metrics.
- Testimonials.
- Sectors.
- Skills/technology universe.
- Experience.
- Education/certifications.
- Open source.
- Sponsorship.
- Writing.
- AI assistant.
- Contact.

Every optional module remains independently configurable.

---

## 7. Motion Design

Use centralized motion tokens and primitives.

Recommended primitives:

- Reveal.
- TextReveal.
- Stagger.
- Parallax.
- Marquee.
- MagneticButton.
- TiltCard.
- Counter.
- PinnedStory.
- MediaReveal.
- PageTransition.
- CursorFollower.
- ReducedMotionBoundary.

GSAP owns complex timeline behavior.

Motion owns component state/microinteraction.

R3F owns genuine 3D/WebGL.

---

## 8. Data Model

### Profile
Name, headline, bios, availability, public location, CTAs, portraits.

### Resume
Stable current asset plus optional versions.

### ProfessionalCategory
Name, slug, description, visual metadata, order, visibility.

### Sector
Name, slug, description, visual metadata, relationships, order, visibility.

### Skill
Category, name, slug, description, icon, related work, order, visibility.

### Experience
Organization, role, dates, achievements, sectors, skills, projects, metrics, testimonials.

### Project
Descriptions, category, sectors, skills, dates, role, problem, solution, architecture, features, decisions, tradeoffs, challenges, outcomes, media, links, featured rank, publication, SEO.

### Metric
Label, value, unit, context, evidence, approval.

### Testimonial
Quote, attribution, source, related entity, approval.

### Article
Title, content, topics, relations, publication, SEO.

---

## 9. Business Invariants

The following should exist as explicit behavior tests:

- Public data excludes drafts.
- Hidden/archived content follows policy.
- Unapproved metrics/testimonials are not public.
- Featured project count honors configuration.
- Seeding preserves admin modifications.
- Current résumé route remains stable after replacement.
- Contact persistence occurs before notification.
- Assistant retrieves only public approved content.
- Disabled features disappear from public presentation without data deletion.

---

## 10. Behavior-Driven / Test-Driven Workflow

For each feature:

1. Define expected observable behavior.
2. Add or update test.
3. Implement minimal correct behavior.
4. Refactor toward clean design.
5. Run unit/integration/E2E checks as applicable.
6. Update docs/contracts.

Avoid testing private implementation details.

---

## 11. Error Model

Use normalized application exceptions:

- Validation error.
- Not found.
- Conflict.
- Unauthorized.
- Forbidden.
- Rate limited.
- External provider unavailable.
- Storage failure.
- Email failure.
- AI provider failure.

API error envelopes should be consistent and avoid leaking sensitive internals.

---

## 12. Transaction Design

Use transaction boundaries intentionally.

Examples:

- Contact message persistence is committed independently of notification.
- Project update plus relationship changes should be atomic.
- Media replacement should avoid leaving invalid references.
- Resume-current-version updates should be atomic.

Use Unit of Work only where it improves clarity.

---

## 13. Production Configuration

Pydantic settings validate:

- Environment.
- Public URLs.
- DB URL/pool.
- Auth secret/settings.
- Email config.
- AI provider/model.
- Storage backend.
- CORS.
- Security.
- Logging.
- Feature defaults.

Production should fail fast on missing required configuration.

---

## 14. Security

- Secure password hashing.
- Secure cookie/session strategy.
- CSRF where applicable.
- Restrictive CORS.
- CSP/security headers.
- Rate limits.
- File-upload validation.
- Explicit response schemas.
- No secrets in frontend.
- Safe logs.
- Admin deny-by-default.
- Assistant/contact isolation.

---

## 15. Performance

- SSR core content.
- Lazy-load R3F.
- Dynamic import heavy motion.
- Pause offscreen effects.
- Optimize images/video/fonts.
- Adaptive quality.
- Control client hydration.
- Use DB indexes based on actual query patterns.
- Avoid N+1 queries.
- Paginate growing admin/public collections.
- Protect Core Web Vitals.

---

## 16. Accessibility

Target WCAG 2.2 AA principles.

Include:

- Keyboard navigation.
- Visible focus.
- Semantic structure.
- Form labels/errors.
- Contrast.
- Skip link.
- Reduced motion.
- Static alternatives.
- Screen-reader-friendly interactions.
- Accessible dialog/menu behavior.

---

## 17. Testing

### Backend
- Unit tests.
- Service behavior tests.
- Repository tests.
- Client adapter tests.
- API integration tests.
- Auth tests.
- Publication tests.
- Seed safety.
- Migration checks.
- Contact behavior.
- Assistant privacy.

### Frontend
- Component tests.
- API client tests.
- Theme.
- Section registry.
- Reduced motion.
- Accessibility.
- Admin workflows.

### E2E
- Home.
- Resume download.
- Project browse/detail.
- Sectors/skills.
- Contact.
- Admin edit/publish.
- Feature disable/re-enable.
- Seed preservation.
- AI assistant.
- Draft privacy.

---

## 18. CI/CD Readiness

CI should block merge on required failures:

- lint.
- formatting.
- typing.
- backend tests.
- frontend tests.
- production build.
- migration validation.
- E2E critical flows.
- dependency/security checks where practical.

Deployment automation may remain simple but must be reproducible.

---

## 19. Production Docker Design

### API Image
- Multi-stage if useful.
- Install only runtime dependencies.
- Non-root user where practical.
- Explicit app command.
- Graceful shutdown.
- Health check.

### Web Image
- Production Next.js build.
- Minimal runtime.
- Environment separation.

### DB
Use official PostgreSQL image with persistent volume.

---

## 20. Completion Quality

Code is considered production-ready only when:

- No critical TODOs/placeholders.
- No mock production adapters.
- Error cases are handled.
- Client timeouts exist.
- Tests cover key behavior.
- Logging exists.
- Security rules are applied.
- Migrations and startup are deterministic.
- Data is persistent.
- Deployment is documented.
