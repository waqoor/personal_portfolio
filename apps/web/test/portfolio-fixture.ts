import type {
  ArticleDetail,
  ArticlesPage,
  Category,
  ContactOptions,
  HomePage,
  HomepageSection,
  HomepageSectionKind,
  OpenSourcePage,
  ProfilePage,
  ProjectDetail,
  ProjectsPage,
  Sector,
  SectorDetail,
  SectorsPage,
  SiteSettings,
  SiteShell,
  Skill,
} from "@portfolio/api-client";

const apiOrigin = "http://127.0.0.1:4310";

export const categoryAi: Category = {
  id: "cat-ai",
  slug: "ai-intelligent-systems",
  name: "AI & Intelligent Systems",
  description:
    "Production AI systems grounded in useful workflows and explicit evidence.",
  statement:
    "Retrieval, orchestration, evaluation, and safe product integration.",
  order: 0,
  accent: "signal",
};
export const categorySoftware: Category = {
  id: "cat-software",
  slug: "software-product",
  name: "Software & Product Engineering",
  description:
    "Typed, operable products shaped around real user and business constraints.",
  statement: "From domain contract to interface and deployment.",
  order: 1,
  accent: "blue",
};
export const categoryData: Category = {
  id: "cat-data",
  slug: "data-infrastructure",
  name: "Data & Infrastructure",
  description:
    "Reliable data paths, service boundaries, and production infrastructure.",
  statement: "Systems designed to survive real operations.",
  order: 2,
  accent: "ink",
};

export const sectorHealth: Sector = {
  id: "sector-health",
  slug: "health-technology",
  name: "Health technology",
  description:
    "Careful systems where reliability, access, and evidence matter.",
  evidence_summary:
    "Published work connects workflows to measurable delivery outcomes.",
  order: 0,
  project_count: 2,
};
export const sectorLearning: Sector = {
  id: "sector-learning",
  slug: "learning-platforms",
  name: "Learning platforms",
  description:
    "Products that support knowledge, assessment, and collaboration.",
  evidence_summary:
    "Projects demonstrate product, data, and platform engineering in context.",
  order: 1,
  project_count: 1,
};

export const skillPython: Skill = {
  id: "skill-python",
  slug: "python",
  name: "Python",
  category: "Languages",
  description: "Typed backend services, data workflows, and AI orchestration.",
  proficiency_label: "Production practice",
  years: 8,
  project_count: 3,
  order: 0,
};
export const skillTypeScript: Skill = {
  id: "skill-ts",
  slug: "typescript",
  name: "TypeScript",
  category: "Languages",
  description: "Strict frontend contracts and product interfaces.",
  proficiency_label: "Production practice",
  years: 6,
  project_count: 3,
  order: 1,
};
export const skillFastApi: Skill = {
  id: "skill-fastapi",
  slug: "fastapi",
  name: "FastAPI",
  category: "Platforms",
  description: "Explicit API composition and service contracts.",
  proficiency_label: "Production practice",
  years: 5,
  project_count: 2,
  order: 2,
};
export const skillPostgres: Skill = {
  id: "skill-postgres",
  slug: "postgresql",
  name: "PostgreSQL",
  category: "Data",
  description: "Canonical relational data and robust publication queries.",
  proficiency_label: "Production practice",
  years: 8,
  project_count: 3,
  order: 3,
};

const media = (id: string, name: string, width = 1600, height = 1200) => ({
  id,
  kind: "image" as const,
  url: `${apiOrigin}/media/${name}.svg`,
  alt: `${name.replaceAll("-", " ")} test fixture`,
  is_decorative: false,
  width,
  height,
});

export const metricDelivery = {
  id: "metric-delivery",
  label: "Delivery cycle",
  value: "42",
  unit: "%",
  context: "Reduction measured against the approved project baseline.",
  verified: true,
  evidence_label: "Approved case-study evidence",
  evidence_url: "https://example.com/evidence/delivery",
} as const;
export const metricReliability = {
  id: "metric-reliability",
  label: "Workflow reliability",
  value: "99.9",
  unit: "%",
  context: "Observed availability across the published measurement window.",
  verified: true,
  evidence_label: "Published reliability review",
} as const;
export const testimonial = {
  id: "testimonial-1",
  quote:
    "The work connected deep technical judgment to a product people could actually operate.",
  attribution_name: "Test Collaborator",
  attribution_role: "Product lead",
  attribution_organization: "Fixture Studio",
  verified: true,
  source_label: "Approved reference",
  source_url: "https://example.com/reference",
} as const;

const projectOne = {
  id: "project-1",
  slug: "evidence-aware-ai-workspace",
  title: "Evidence-aware AI workspace",
  kicker: "Answers that stay attached to authorized source material.",
  summary:
    "A production AI workspace combining typed retrieval, explicit approval gates, and operable human review.",
  year: "2026",
  role: "Product & systems engineering",
  nature: "software" as const,
  status_label: "Production",
  featured_rank: 1,
  cover: media("media-project-1", "project-ai"),
  categories: [categoryAi, categorySoftware],
  sectors: [sectorHealth],
  skills: [skillPython, skillTypeScript, skillFastApi, skillPostgres],
  metrics: [metricDelivery, metricReliability],
  links: [
    {
      label: "Source",
      url: "https://example.com/source",
      kind: "source" as const,
      external: true,
    },
  ],
};
const projectTwo = {
  id: "project-2",
  slug: "operable-product-platform",
  title: "Operable product platform",
  kicker: "A platform rebuilt around domain ownership and production feedback.",
  summary:
    "A modular product platform with clear service boundaries, measurable workflows, and a resilient administration surface.",
  year: "2025",
  role: "Lead engineer",
  nature: "product" as const,
  status_label: "Live",
  featured_rank: 2,
  cover: media("media-project-2", "project-platform"),
  categories: [categorySoftware, categoryData],
  sectors: [sectorLearning],
  skills: [skillTypeScript, skillPostgres],
  metrics: [metricDelivery],
  links: [],
};
const projectThree = {
  id: "project-3",
  slug: "data-signal-system",
  title: "Data signal system",
  kicker: "From scattered operational data to decisions with provenance.",
  summary:
    "A typed data and reporting layer focused on provenance, clarity, and stable operations.",
  year: "2024",
  role: "Data & infrastructure engineer",
  nature: "case_study" as const,
  status_label: "Delivered",
  featured_rank: 3,
  cover: media("media-project-3", "project-data"),
  categories: [categoryData],
  sectors: [sectorHealth],
  skills: [skillPython, skillPostgres],
  metrics: [metricReliability],
  links: [],
};
const projectFour = {
  ...projectThree,
  id: "project-4",
  slug: "open-delivery-toolkit",
  title: "Open delivery toolkit",
  summary: "Reusable open-source delivery primitives for small product teams.",
  featured_rank: 4,
  cover: media("media-project-4", "project-open"),
};
const projectFive = {
  ...projectTwo,
  id: "project-5",
  slug: "learning-operations-suite",
  title: "Learning operations suite",
  summary:
    "An accessible workflow suite for learning operations and assessment.",
  featured_rank: 5,
  cover: media("media-project-5", "project-learning"),
};

export const projectSummaries = [
  projectOne,
  projectTwo,
  projectThree,
  projectFour,
  projectFive,
];

export const projectDetail: ProjectDetail = {
  ...projectOne,
  sections: [
    {
      id: "story-1",
      kind: "narrative",
      eyebrow: "System boundary",
      title: "Ground the answer before generating it.",
      body: "The retrieval layer resolves published evidence first. The model receives bounded context with identifiers the interface can return as citations.",
      items: [],
      media: [],
    },
    {
      id: "story-2",
      kind: "architecture",
      eyebrow: "Architecture",
      title: "One path from contract to evidence.",
      body: "Presentation code consumes a runtime-validated client while the API composes isolated service behavior.",
      items: [
        "Typed public and admin contracts",
        "Provider failures normalized at the adapter",
        "Private data excluded structurally",
      ],
      media: [],
    },
  ],
  testimonials: [testimonial],
  gallery: [media("media-gallery-1", "case-study-detail")],
  related_projects: [projectTwo, projectThree],
  seo: {
    title: "Evidence-aware AI workspace",
    description: "Case study for an evidence-aware production AI workspace.",
    noindex: false,
    keywords: ["AI", "retrieval", "FastAPI"],
  },
};

const articleSummary = {
  id: "article-1",
  slug: "designing-ai-that-can-say-unknown",
  title: "Designing AI that can say ‘unknown’",
  excerpt:
    "A practical field note on evidence boundaries, confidence, and review-aware product behavior.",
  published_at: "2026-08-01T09:00:00+00:00",
  updated_at: "2026-08-05T09:00:00+00:00",
  reading_minutes: 7,
  topics: ["AI systems", "Product engineering"],
  cover: media("media-article-1", "article-ai"),
};
export const articleDetail: ArticleDetail = {
  ...articleSummary,
  blocks: [
    {
      id: "block-1",
      kind: "text",
      body: "Useful AI behavior starts with a boundary: what the system is allowed to know, and what it must refuse to infer.",
    },
    {
      id: "block-2",
      kind: "heading",
      level: 2,
      text: "Confidence is a product behavior",
    },
    {
      id: "block-3",
      kind: "text",
      body: "A confidence label should reflect evidence quality and freshness, not the fluency of generated prose.",
    },
    {
      id: "block-4",
      kind: "quote",
      quote: "Clarity about uncertainty is part of correctness.",
      attribution: "Field note",
    },
    {
      id: "block-5",
      kind: "list",
      style: "unordered",
      items: [
        "Resolve deterministic facts first",
        "Keep sources visible",
        "Escalate ambiguity to review",
      ],
    },
  ],
  related_articles: [],
  seo: {
    title: articleSummary.title,
    description: articleSummary.excerpt,
    noindex: false,
    keywords: articleSummary.topics,
  },
};

const section = (
  kind: HomepageSectionKind,
  order: number,
  variant: string,
  extra: Partial<HomepageSection> = {},
): HomepageSection => ({
  id: `section-${kind}`,
  kind,
  enabled: true,
  order,
  variant,
  animation_variant: kind === "selected_work" ? "stagger" : "reveal",
  cta_visible: true,
  theme: kind === "assistant" ? "contrast" : "default",
  configuration: {},
  ...extra,
});

export const fixturePresentation: SiteSettings = {
  site_name: "Yazeed Hasan",
  default_title: "Yazeed Hasan portfolio",
  default_description: "Selected work, writing, and collaboration context.",
  locale: "en",
  footer_eyebrow: "End of transmission",
  footer_heading: "Build what matters.",
  footer_statement: "Designed for people. Legible to machines.",
  about_title: "A builder working across systems and product.",
  about_intro: "Published experience, education, and verified credentials.",
  achievements_title: "Achievements",
  achievements_intro: "Published credentials, recognition, and research.",
  work_title: "Work",
  work_intro: "Published professional experience.",
  projects_title: "Projects",
  projects_intro: "Case studies with decisions, constraints, and evidence.",
  writing_title: "Writing",
  writing_intro: "Technical field notes and practical explanations.",
  sectors_title: "Sectors",
  sectors_intro: "Applied domains supported by published project evidence.",
  open_source_title: "Open source",
  open_source_intro: "Public repositories and contribution work.",
  sponsorship_title: "Support sustainable open-source work",
  sponsorship_description: "Transparent sponsorship helps maintain public technical work.",
  sponsorship_principles: ["Public work remains technically independent."],
};

export const fixtureHome: HomePage = {
  profile: {
    id: "profile-1",
    name: "Yazeed Hasan",
    eyebrow: "AI · Product · Data · Infrastructure",
    headline:
      "I build intelligent products and the systems that make them reliable.",
    short_bio:
      "An engineering portfolio focused on evidence-aware AI, operable software products, dependable data, infrastructure, and open-source work.",
    long_bio:
      "I work from the useful problem outward—connecting product intent, domain rules, technical architecture, and the operational reality after launch.",
    public_location: "Riyadh, Saudi Arabia",
    timezone: "Asia/Riyadh",
    portrait: media("media-portrait", "portrait", 1200, 1500),
    portrait_secondary: media(
      "media-portrait-2",
      "portrait-secondary",
      1200,
      1500,
    ),
    resume: {
      id: "resume-1",
      label: "Current technical résumé",
      filename: "yazeed-hasan-resume.pdf",
      download_url: `${apiOrigin}/media/resume.pdf`,
      updated_at: "2026-08-20T10:00:00+00:00",
      version: "5.0",
      file_size_bytes: 184320,
    },
    availability: {
      status: "selective",
      label: "Selective collaborations",
      details:
        "Open to high-leverage AI, product, and platform work with clear ownership.",
    },
    socials: [
      {
        id: "social-github",
        platform: "GitHub",
        label: "GitHub",
        url: "https://github.com/example",
        handle: "example",
      },
      {
        id: "social-linkedin",
        platform: "LinkedIn",
        label: "LinkedIn",
        url: "https://www.linkedin.com/in/example",
        handle: "example",
      },
    ],
  },
  presentation: fixturePresentation,
  sections: [
    section("hero", 0, "portrait"),
    section("resume", 1, "default"),
    section("what_i_build", 2, "columns"),
    section("selected_work", 3, "cinematic", { data_limit: 5 }),
    section("metrics", 4, "cards"),
    section("testimonials", 5, "cards"),
    section("sectors", 6, "cards"),
    section("skills", 7, "universe"),
    section("experience", 8, "timeline"),
    section("education", 9, "cards"),
    section("certifications", 10, "cards"),
    section("open_source", 11, "cards"),
    section("sponsorship", 12, "default"),
    section("writing", 13, "cards"),
    section("assistant", 14, "default"),
    section("contact", 15, "default"),
    section("social_links", 16, "marquee"),
    section("editorial", 17, "split"),
  ],
  categories: [categoryAi, categorySoftware, categoryData],
  featured_projects: projectSummaries,
  metrics: [metricDelivery, metricReliability],
  testimonials: [testimonial],
  sectors: [sectorHealth, sectorLearning],
  skills: [skillPython, skillTypeScript, skillFastApi, skillPostgres],
  experience: [
    {
      id: "experience-1",
      organization: "Fixture Product Studio",
      role: "Lead AI & Product Engineer",
      location: "Riyadh",
      start_date: "2023-01",
      current: true,
      summary:
        "Owned product and systems engineering across AI-assisted workflows and platform operations.",
      achievements: [
        "Shipped evidence-aware AI workflows.",
        "Established typed contracts across frontend and API.",
      ],
      skills: [skillPython, skillTypeScript],
      sectors: [sectorHealth],
    },
  ],
  education: [
    {
      id: "education-1",
      institution: "Fixture University",
      credential: "Bachelor of Engineering",
      field: "Software Engineering",
      start_date: "2012",
      end_date: "2016",
      details: "Test-only education record.",
      achievements: [],
    },
  ],
  certifications: [
    {
      id: "cert-1",
      name: "Production Systems Architecture",
      issuer: "Fixture Institute",
      issued_at: "2025",
      credential_url: "https://example.com/credential",
    },
  ],
  open_source: [
    {
      id: "oss-1",
      slug: "typed-workflow-kit",
      name: "Typed Workflow Kit",
      description: "Reusable boundaries for typed workflow applications.",
      repository_url: "https://github.com/example/typed-workflow-kit",
      sponsor_url: "https://github.com/sponsors/example",
      language: "TypeScript",
      stars: 240,
      forks: 28,
      status_label: "Maintained",
      skills: [skillTypeScript],
    },
  ],
  sponsorship: {
    enabled: true,
    title: "Support durable open work.",
    description:
      "Sponsorship funds maintenance, documentation, and useful public tooling.",
    links: [
      {
        label: "Sponsor",
        url: "https://github.com/sponsors/example",
        kind: "sponsor",
        external: true,
      },
    ],
    principles: [
      "Public maintenance",
      "Clear scope",
      "No paywalled core fixes",
    ],
  },
  articles: [articleSummary],
  editorial_blocks: [
    {
      id: "editorial-1",
      eyebrow: "Working principle",
      title: "Make the system explain its decisions.",
      body: "Operability improves when evidence, tradeoffs, and boundaries are visible to the people responsible for the outcome.",
      link: {
        label: "Read the field notes",
        url: "/writing",
        kind: "other",
        external: false,
      },
      media: media("media-editorial", "editorial-system"),
    },
  ],
  feature_flags: {
    projects: true,
    metrics: true,
    testimonials: true,
    sectors: true,
    skills: true,
    experience: true,
    credentials: true,
    open_source: true,
    sponsorship: true,
    articles: true,
    assistant: true,
    contact: true,
    resume: true,
  },
  seo: {
    title: "Yazeed Hasan · AI, Product, Data & Infrastructure",
    description:
      "Selected engineering work, evidence-aware AI systems, product platforms, writing, and open source.",
    noindex: false,
    keywords: ["AI engineering", "product engineering", "data infrastructure"],
  },
};

export const fixtureShell: SiteShell = {
  brand_name: "Yazeed Hasan",
  brand_mark: "YH",
  brand_logo: fixtureHome.profile.portrait,
  header_navigation: [
    {
      id: "nav-work",
      label: "Work",
      href: "/work",
      external: false,
      order: 0,
      location: "header",
    },
    {
      id: "nav-projects",
      label: "Projects",
      href: "/projects",
      external: false,
      order: 1,
      location: "header",
    },
    {
      id: "nav-achievements",
      label: "Achievements",
      href: "/achievements",
      external: false,
      order: 2,
      location: "header",
    },
    {
      id: "nav-sponsor",
      label: "Sponsor",
      href: "/sponsor",
      external: false,
      order: 3,
      location: "header",
    },
  ],
  footer_navigation: [],
  socials: fixtureHome.profile.socials,
  assistant_enabled: true,
  assistant_settings: {
    enabled: true,
    greeting: "Ask about published fixture content.",
    suggested_questions: ["Which projects demonstrate production engineering?"],
    disclaimer: "Answers use published fixture evidence only.",
    max_question_length: 600,
  },
  contact_enabled: true,
  public_email: "hello@example.com",
  presentation: fixturePresentation,
};
export const fixtureProjectsPage: ProjectsPage = {
  items: projectSummaries,
  page_info: { page: 1, page_size: 12, total: 5, total_pages: 1 },
  categories: fixtureHome.categories,
  sectors: fixtureHome.sectors,
  presentation: fixturePresentation,
  seo: {
    title: "Project archive",
    description: "All published case studies.",
    noindex: false,
    keywords: [],
  },
};
export const fixtureArticlesPage: ArticlesPage = {
  items: [articleSummary],
  page_info: { page: 1, page_size: 10, total: 1, total_pages: 1 },
  topics: ["AI systems", "Product engineering"],
  presentation: fixturePresentation,
  seo: {
    title: "Writing",
    description: "Technical field notes.",
    noindex: false,
    keywords: [],
  },
};
export const fixtureProfilePage: ProfilePage = {
  profile: fixtureHome.profile,
  presentation: fixturePresentation,
  experience: fixtureHome.experience,
  education: fixtureHome.education,
  certifications: fixtureHome.certifications,
  seo: {
    title: "About Yazeed Hasan",
    description: fixtureHome.profile.short_bio,
    noindex: false,
    keywords: [],
  },
};
export const fixtureSectorsPage: SectorsPage = {
  items: fixtureHome.sectors,
  presentation: fixturePresentation,
  seo: {
    title: "Sectors",
    description: "Applied domains connected to published work.",
    noindex: false,
    keywords: [],
  },
};
export const fixtureSectorDetail: SectorDetail = {
  ...sectorHealth,
  projects: [projectOne, projectThree],
  skills: [skillPython, skillPostgres],
  metrics: [metricReliability],
  seo: {
    title: sectorHealth.name,
    description: sectorHealth.description,
    noindex: false,
    keywords: [],
  },
};
export const fixtureOpenSourcePage: OpenSourcePage = {
  items: fixtureHome.open_source,
  sponsorship: fixtureHome.sponsorship,
  presentation: fixturePresentation,
  seo: {
    title: "Open source",
    description: "Published repositories and sponsorship.",
    noindex: false,
    keywords: [],
  },
};
export const fixtureContactOptions: ContactOptions = {
  categories: [
    { id: "project", label: "Project collaboration" },
    { id: "role", label: "Role / team" },
    { id: "open-source", label: "Open source" },
    { id: "sponsorship", label: "Sponsorship" },
  ],
  response_time_label: "Usually reviewed within three business days.",
  accepting_messages: true,
};
