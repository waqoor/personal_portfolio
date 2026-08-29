export const SECTION_KINDS = [
  "hero",
  "resume",
  "availability",
  "what_i_build",
  "categories",
  "selected_work",
  "metrics",
  "testimonials",
  "sectors",
  "skills",
  "experience",
  "education",
  "certifications",
  "open_source",
  "sponsorship",
  "writing",
  "assistant",
  "contact",
  "social_links",
  "editorial",
] as const;

export type SectionKind = (typeof SECTION_KINDS)[number];

export type SectionDefinition = {
  label: string;
  description: string;
  variants: readonly string[];
  defaultVariant: string;
  supportsLimit: boolean;
  featureKey?: string;
};

const SECTION_COPY: Record<SectionKind, SectionDefinition> = {
  hero: {
    label: "Hero / personal identity",
    description: "Portrait-led introduction, positioning, availability, and primary calls to action.",
    variants: ["default", "portrait", "editorial"],
    defaultVariant: "portrait",
    supportsLimit: false,
  },
  resume: {
    label: "Résumé",
    description: "Stable current-résumé download with version and update context.",
    variants: ["default", "compact"],
    defaultVariant: "default",
    supportsLimit: false,
    featureKey: "resume",
  },
  availability: {
    label: "Availability",
    description: "Current collaboration status and response expectations.",
    variants: ["default", "badge"],
    defaultVariant: "badge",
    supportsLimit: false,
  },
  what_i_build: {
    label: "What I build",
    description: "Professional capability categories and positioning.",
    variants: ["default", "columns", "marquee"],
    defaultVariant: "columns",
    supportsLimit: true,
  },
  categories: {
    label: "Categories",
    description: "Published professional categories and their evidence context.",
    variants: ["default", "cards", "compact"],
    defaultVariant: "cards",
    supportsLimit: true,
  },
  selected_work: {
    label: "Selected work",
    description: "Up to five featured projects, with cinematic depth for the first three.",
    variants: ["default", "featured", "cinematic", "grid"],
    defaultVariant: "cinematic",
    supportsLimit: true,
    featureKey: "projects",
  },
  metrics: {
    label: "Verified impact",
    description: "Approved outcome metrics with evidence context.",
    variants: ["default", "cards", "compact"],
    defaultVariant: "cards",
    supportsLimit: true,
    featureKey: "metrics",
  },
  testimonials: {
    label: "Testimonials",
    description: "Approved quotes with clear attribution and source status.",
    variants: ["default", "cards", "compact"],
    defaultVariant: "cards",
    supportsLimit: true,
    featureKey: "testimonials",
  },
  sectors: {
    label: "Sectors / domains",
    description: "Domains where the portfolio demonstrates applied experience.",
    variants: ["default", "cards", "compact"],
    defaultVariant: "cards",
    supportsLimit: true,
    featureKey: "sectors",
  },
  skills: {
    label: "Technology universe",
    description: "Interactive skill relationships with a complete semantic fallback.",
    variants: ["default", "universe", "groups", "compact"],
    defaultVariant: "universe",
    supportsLimit: true,
    featureKey: "skills",
  },
  experience: {
    label: "Experience",
    description: "Professional timeline and evidence-backed achievements.",
    variants: ["default", "timeline", "compact"],
    defaultVariant: "timeline",
    supportsLimit: true,
    featureKey: "experience",
  },
  education: {
    label: "Education & certifications",
    description: "Education, credentials, and verified certification links.",
    variants: ["default", "cards", "compact"],
    defaultVariant: "cards",
    supportsLimit: true,
    featureKey: "credentials",
  },
  certifications: {
    label: "Certifications",
    description: "Published credentials and verification links.",
    variants: ["default", "cards", "compact"],
    defaultVariant: "cards",
    supportsLimit: true,
    featureKey: "credentials",
  },
  open_source: {
    label: "Open source",
    description: "Repositories, community work, and contribution pathways.",
    variants: ["default", "cards", "compact"],
    defaultVariant: "cards",
    supportsLimit: true,
    featureKey: "open_source",
  },
  sponsorship: {
    label: "Sponsorship",
    description: "Transparent sponsorship invitation and supported channels.",
    variants: ["default", "compact"],
    defaultVariant: "default",
    supportsLimit: false,
    featureKey: "sponsorship",
  },
  writing: {
    label: "Writing",
    description: "Published technical articles and editorial topics.",
    variants: ["default", "cards", "compact"],
    defaultVariant: "cards",
    supportsLimit: true,
    featureKey: "articles",
  },
  assistant: {
    label: "Ask my AI",
    description: "Portfolio-aware assistant entry point with factual-source messaging.",
    variants: ["default", "compact"],
    defaultVariant: "default",
    supportsLimit: false,
    featureKey: "assistant",
  },
  contact: {
    label: "Contact",
    description: "Contact workflow and collaboration prompt.",
    variants: ["default", "compact"],
    defaultVariant: "default",
    supportsLimit: false,
    featureKey: "contact",
  },
  social_links: {
    label: "Social links",
    description: "Approved public identity and community channels.",
    variants: ["default", "icons", "marquee"],
    defaultVariant: "marquee",
    supportsLimit: true,
  },
  editorial: {
    label: "Editorial block",
    description: "Curated narrative module with optional managed media and link.",
    variants: ["default", "split", "full_bleed"],
    defaultVariant: "split",
    supportsLimit: true,
  },
};

type RegistryEntry = {
  variants: string[];
  default_variant: string;
  default_limit: number | null;
  feature_key: string | null;
};

const AUTHORITATIVE_SECTION_REGISTRY = homepageRegistry as Record<
  SectionKind,
  RegistryEntry
>;

export const SECTION_DEFINITIONS = Object.fromEntries(
  SECTION_KINDS.map((kind) => {
    const registry = AUTHORITATIVE_SECTION_REGISTRY[kind];
    const definition: SectionDefinition = {
      ...SECTION_COPY[kind],
      variants: registry.variants,
      defaultVariant: registry.default_variant,
      supportsLimit: registry.default_limit !== null,
      ...(registry.feature_key ? { featureKey: registry.feature_key } : {}),
    };
    return [kind, definition];
  }),
) as Record<SectionKind, SectionDefinition>;

export const ADMIN_RESOURCE_GROUPS = [
  {
    label: "Identity",
    items: ["profile", "resumes", "media", "navigation"],
  },
  {
    label: "Portfolio",
    items: [
      "projects",
      "categories",
      "sectors",
      "skills",
      "experience",
      "education",
      "certifications",
      "metrics",
      "testimonials",
    ],
  },
  {
    label: "Publishing",
    items: ["articles", "open-source", "sponsorship", "contact-submissions"],
  },
  {
    label: "Experience settings",
    items: ["homepage-sections", "feature-settings", "site-settings", "assistant-settings"],
  },
] as const;

export const MOTION_VARIANTS = ["none", "reveal", "stagger"] as const;
export const SECTION_THEMES = ["default", "contrast", "muted", "accent"] as const;

export const PUBLIC_NAV_FALLBACK = [
  { label: "About", href: "/about" },
  { label: "Achievements", href: "/achievements" },
  { label: "Work", href: "/work" },
  { label: "Projects", href: "/projects" },
  { label: "Sponsor", href: "/sponsor" },
] as const;
import homepageRegistry from "../../../python/contracts/homepage_sections.json";
