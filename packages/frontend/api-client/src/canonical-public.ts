import { z } from "zod";

import {
  articleDetailSchema,
  articleSummarySchema,
  articlesPageSchema,
  assistantSettingsSchema,
  categorySchema,
  certificationSchema,
  educationSchema,
  editorialBlockSchema,
  experienceSchema,
  homePageSchema,
  homepageSectionSchema,
  mediaAssetSchema,
  metricSchema,
  openSourcePageSchema,
  openSourceProjectSchema,
  profilePageSchema,
  profileSchema,
  projectDetailSchema,
  projectSummarySchema,
  projectsPageSchema,
  sectorDetailSchema,
  sectorSchema,
  sectorsPageSchema,
  siteShellSchema,
  sitePresentationSchema,
  skillSchema,
  sponsorshipSchema,
  testimonialSchema,
  type HomepageSectionKind,
} from "./schemas";

const publicationStatusSchema = z.enum([
  "draft",
  "published",
  "hidden",
  "archived",
]);
const entityFields = {
  id: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
};
const publicationFields = {
  status: publicationStatusSchema,
  is_visible: z.boolean(),
  noindex: z.boolean(),
  published_at: z.string().nullable(),
  archived_at: z.string().nullable(),
};

export const rawPortraitSchema = z.object({
  ...entityFields,
  original_filename: z.string(),
  media_type: z.string(),
  size_bytes: z.number().int().nonnegative(),
  alt_text: z.string(),
  width: z.number().int().positive().nullable(),
  height: z.number().int().positive().nullable(),
  is_primary: z.boolean(),
  is_active: z.boolean(),
  sort_order: z.number().int(),
});

export const rawResumeSchema = z.object({
  ...entityFields,
  version_label: z.string(),
  original_filename: z.string(),
  media_type: z.string(),
  size_bytes: z.number().int().nonnegative(),
  effective_date: z.string().nullable(),
  is_current: z.boolean(),
  download_name: z.string(),
});

const rawSocialLinkSchema = z.object({
  ...entityFields,
  platform: z.string(),
  label: z.string(),
  url: z.string(),
  handle: z.string().nullable(),
  sort_order: z.number().int(),
  is_visible: z.boolean(),
});

export const rawProfileSchema = z.object({
  ...entityFields,
  ...publicationFields,
  full_name: z.string(),
  headline: z.string(),
  short_bio: z.string(),
  long_bio: z.string().nullable(),
  public_location: z.string().nullable(),
  availability_status: z.string().nullable(),
  availability_detail: z.string().nullable(),
  public_email: z.string().nullable(),
  primary_cta_label: z.string().nullable(),
  primary_cta_url: z.string().nullable(),
  secondary_cta_label: z.string().nullable(),
  secondary_cta_url: z.string().nullable(),
  portraits: z.array(rawPortraitSchema),
  social_links: z.array(rawSocialLinkSchema),
});

export const rawCategorySchema = z.object({
  ...entityFields,
  ...publicationFields,
  name: z.string(),
  slug: z.string(),
  description: z.string(),
  color: z.string().nullable(),
  icon_key: z.string().nullable(),
  sort_order: z.number().int(),
});

export const rawSectorSchema = rawCategorySchema.extend({
  project_count: z.number().int().nonnegative().default(0),
});

const rawSkillSummarySchema = z.object({
  id: z.string(),
  name: z.string(),
  slug: z.string(),
  icon_key: z.string().nullable(),
});

export const rawSkillSchema = z.object({
  id: z.string(),
  name: z.string(),
  slug: z.string(),
  description: z.string().nullable(),
  icon_key: z.string().nullable(),
  proficiency_label: z.string().nullable(),
  years_experience: z.number().int().nonnegative().nullable(),
  sort_order: z.number().int(),
  category: rawCategorySchema.nullable(),
  project_count: z.number().int().nonnegative(),
});

const rawPublicEvidenceSchema = z.object({
  label: z.string(),
  url: z.string().nullable(),
  captured_at: z.string(),
});

export const rawMetricSchema = z.object({
  ...entityFields,
  ...publicationFields,
  project_id: z.string().nullable(),
  experience_id: z.string().nullable(),
  subject_label: z.string().nullable(),
  label: z.string(),
  value: z.string(),
  unit: z.string().nullable(),
  context: z.string(),
  public_evidence: rawPublicEvidenceSchema.nullable(),
  sort_order: z.number().int(),
});

export const rawTestimonialSchema = z.object({
  ...entityFields,
  ...publicationFields,
  project_id: z.string().nullable(),
  experience_id: z.string().nullable(),
  subject_label: z.string().nullable(),
  quote: z.string(),
  attribution_name: z.string(),
  attribution_title: z.string().nullable(),
  attribution_organization: z.string().nullable(),
  public_evidence: rawPublicEvidenceSchema.nullable(),
  sort_order: z.number().int(),
});

const rawProjectMediaSchema = z.object({
  ...entityFields,
  external_url: z.string().nullable(),
  original_filename: z.string().nullable(),
  media_type: z.string(),
  size_bytes: z.number().int().nonnegative().nullable(),
  alt_text: z.string(),
  is_decorative: z.boolean(),
  caption: z.string().nullable(),
  width: z.number().int().positive().nullable(),
  height: z.number().int().positive().nullable(),
  duration_seconds: z.number().int().nonnegative().nullable(),
  page_count: z.number().int().positive().nullable(),
  sort_order: z.number().int(),
  is_visible: z.boolean(),
});

const rawRepositoryMetadataSchema = z.object({
  provider: z.string(),
  repository_identity: z.string(),
  language: z.string().nullable(),
  stars: z.number().int().nonnegative().nullable(),
  forks: z.number().int().nonnegative().nullable(),
  fetched_at: z.string(),
  freshness: z.enum(["fresh", "stale"]),
});

export const rawProjectSummarySchema = z.object({
  ...entityFields,
  ...publicationFields,
  title: z.string(),
  slug: z.string(),
  summary: z.string(),
  role: z.string().nullable(),
  start_date: z.string().nullable(),
  end_date: z.string().nullable(),
  links: z.array(z.record(z.string(), z.unknown())),
  repository_url: z.string().nullable(),
  live_url: z.string().nullable(),
  is_open_source: z.boolean(),
  repository_metadata: rawRepositoryMetadataSchema.nullable(),
  nature: z.enum(["case_study", "product", "software"]),
  featured_rank: z.number().int().positive().nullable(),
  seo_title: z.string().nullable(),
  seo_description: z.string().nullable(),
  category: rawCategorySchema.nullable(),
  skills: z.array(rawSkillSummarySchema),
  sectors: z.array(rawSectorSchema),
  media: z.array(rawProjectMediaSchema),
  metrics: z.array(rawMetricSchema),
});

export const rawProjectSchema = rawProjectSummarySchema.extend({
  description: z.string().nullable(),
  problem: z.string().nullable(),
  solution: z.string().nullable(),
  architecture: z.string().nullable(),
  features: z.array(z.string()),
  decisions: z.array(z.string()),
  tradeoffs: z.array(z.string()),
  challenges: z.array(z.string()),
  outcomes: z.array(z.string()),
  testimonials: z.array(rawTestimonialSchema),
  related_projects: z.array(rawProjectSummarySchema),
});

export const rawExperienceSchema = z.object({
  ...entityFields,
  ...publicationFields,
  organization: z.string(),
  role: z.string(),
  location: z.string().nullable(),
  employment_type: z.string().nullable(),
  start_date: z.string(),
  end_date: z.string().nullable(),
  summary: z.string(),
  achievements: z.array(z.string()),
  sort_order: z.number().int(),
  skills: z.array(rawSkillSummarySchema),
  sectors: z.array(rawSectorSchema),
});

export const rawEducationSchema = z.object({
  ...entityFields,
  ...publicationFields,
  institution: z.string(),
  credential: z.string(),
  field_of_study: z.string().nullable(),
  location: z.string().nullable(),
  start_date: z.string().nullable(),
  end_date: z.string().nullable(),
  summary: z.string().nullable(),
  achievements: z.array(z.string()),
  sort_order: z.number().int(),
});

export const rawCertificationSchema = z.object({
  ...entityFields,
  ...publicationFields,
  name: z.string(),
  issuer: z.string(),
  credential_id: z.string().nullable(),
  credential_url: z.string().nullable(),
  issued_on: z.string().nullable(),
  expires_on: z.string().nullable(),
  description: z.string().nullable(),
  sort_order: z.number().int(),
});

const rawContentMediaSchema = z.object({
  ...entityFields,
  ...publicationFields,
  original_filename: z.string(),
  media_type: z.string(),
  size_bytes: z.number().int().nonnegative(),
  alt_text: z.string(),
  is_decorative: z.boolean(),
  caption: z.string().nullable(),
  width: z.number().int().positive().nullable(),
  height: z.number().int().positive().nullable(),
  duration_seconds: z.number().int().nonnegative().nullable(),
  page_count: z.number().int().positive().nullable(),
});

export const rawArticleSummarySchema = z.object({
  ...entityFields,
  ...publicationFields,
  title: z.string(),
  slug: z.string(),
  excerpt: z.string(),
  topics: z.array(z.string()),
  reading_minutes: z.number().int().positive().nullable(),
  seo_title: z.string().nullable(),
  seo_description: z.string().nullable(),
  hero_media: rawContentMediaSchema.nullable(),
});

export const rawArticleSchema = rawArticleSummarySchema.extend({
  body_markdown: z.string(),
  related_articles: z.array(rawArticleSummarySchema),
});

const rawHomepageSectionSchema = z.object({
  ...entityFields,
  ...publicationFields,
  section_type: z.string(),
  title: z.string().nullable(),
  position: z.number().int(),
  enabled: z.boolean(),
  variant: z.string(),
  animation_variant: z.string().nullable(),
  data_limit: z.number().int().positive().nullable(),
  show_cta: z.boolean(),
  theme: z.string().nullable(),
  feature_key: z.string().nullable(),
  configuration: z.record(z.string(), z.unknown()),
});

export const rawHomepageSchema = z.object({
  profile: rawProfileSchema.nullable(),
  current_resume: rawResumeSchema.nullable(),
  navigation: z.array(
    z.object({
      ...entityFields,
      ...publicationFields,
      label: z.string(),
      href: z.string(),
      location: z.enum(["header", "footer"]),
      sort_order: z.number().int(),
      open_in_new_tab: z.boolean(),
    }),
  ),
  features: z.record(z.string(), z.boolean()),
  feature_configurations: z
    .record(z.string(), z.record(z.string(), z.unknown()))
    .default({}),
  site_presentation: sitePresentationSchema,
  sections: z.array(
    z.object({ section: rawHomepageSectionSchema, data: z.unknown() }),
  ),
});

export const rawSiteShellSchema = rawHomepageSchema.pick({
  profile: true,
  navigation: true,
  features: true,
  feature_configurations: true,
  site_presentation: true,
});

export const rawSponsorshipSchema = z.object({
  items: z.array(
    z.object({
      slug: z.string(),
      title: z.string(),
      description: z.string(),
      kind: z.string(),
      cta_label: z.string(),
      destination_url: z.string(),
      amount_minor: z.number().int().nonnegative().nullable(),
      currency: z.string().nullable(),
      recurrence: z.string().nullable(),
      rel: z.string(),
    }),
  ),
});

export const rawContactReceiptSchema = z.object({
  accepted: z.literal(true),
  reference_id: z.string(),
  accepted_at: z.string(),
  message: z.string(),
});

export const rawAssistantAnswerSchema = z.object({
  request_id: z.string(),
  answer: z.string(),
  sources: z.array(
    z.object({
      citation: z.string(),
      title: z.string(),
      content_type: z.string(),
      canonical_url: z.string(),
    }),
  ),
  grounded: z.boolean(),
  degraded: z.boolean(),
  input_was_redacted: z.boolean(),
});

type RawHomepage = z.infer<typeof rawHomepageSchema>;
type RawProfile = z.infer<typeof rawProfileSchema>;
type RawProject = z.infer<typeof rawProjectSummarySchema>;
type RawProjectDetail = z.infer<typeof rawProjectSchema>;
type RawSkill =
  z.infer<typeof rawSkillSchema> | z.infer<typeof rawSkillSummarySchema>;
type RawSponsorship = z.infer<typeof rawSponsorshipSchema>;

function mediaKind(mediaType: string): "image" | "video" | "document" {
  if (mediaType.startsWith("video/")) return "video";
  if (!mediaType.startsWith("image/")) return "document";
  return "image";
}

function mapPortrait(value: z.infer<typeof rawPortraitSchema>) {
  return mediaAssetSchema.parse({
    id: value.id,
    kind: "image",
    url: `/api/v1/public/portraits/${value.id}`,
    alt: value.alt_text,
    filename: value.original_filename,
    mime_type: value.media_type,
    width: value.width ?? undefined,
    height: value.height ?? undefined,
  });
}

export function mapResume(value: z.infer<typeof rawResumeSchema>) {
  return {
    id: value.id,
    label: value.version_label,
    filename: value.download_name,
    download_url: "/api/v1/public/resume",
    updated_at: value.updated_at,
    version: value.version_label,
    file_size_bytes: value.size_bytes,
  };
}

export function mapProfile(
  value: RawProfile,
  resume?: z.infer<typeof rawResumeSchema> | null,
) {
  const portraits = value.portraits
    .filter((item) => item.is_active)
    .sort((a, b) => a.sort_order - b.sort_order);
  const status =
    value.availability_status === "available" ||
    value.availability_status === "unavailable"
      ? value.availability_status
      : "selective";
  return profileSchema.parse({
    id: value.id,
    name: value.full_name,
    headline: value.headline,
    short_bio: value.short_bio,
    long_bio: value.long_bio ?? undefined,
    public_location: value.public_location ?? undefined,
    public_email: value.public_email ?? undefined,
    primary_cta:
      value.primary_cta_label && value.primary_cta_url
        ? { label: value.primary_cta_label, url: value.primary_cta_url }
        : undefined,
    secondary_cta:
      value.secondary_cta_label && value.secondary_cta_url
        ? { label: value.secondary_cta_label, url: value.secondary_cta_url }
        : undefined,
    portrait: portraits[0] ? mapPortrait(portraits[0]) : undefined,
    portrait_secondary: portraits[1] ? mapPortrait(portraits[1]) : undefined,
    resume: resume ? mapResume(resume) : undefined,
    availability: {
      status,
      label: value.availability_status ?? "Selective availability",
      details: value.availability_detail ?? undefined,
    },
    socials: value.social_links
      .filter((item) => item.is_visible)
      .sort((a, b) => a.sort_order - b.sort_order)
      .map((item) => ({
        id: item.id,
        platform: item.platform,
        label: item.label,
        url: item.url,
        handle: item.handle ?? undefined,
      })),
  });
}

export function mapCategory(value: z.infer<typeof rawCategorySchema>) {
  return categorySchema.parse({
    id: value.id,
    slug: value.slug,
    name: value.name,
    description: value.description,
    accent: value.color ?? undefined,
    icon: value.icon_key ?? undefined,
    order: value.sort_order,
  });
}

export function mapSector(
  value: z.infer<typeof rawSectorSchema>,
  projectCount = value.project_count,
) {
  return sectorSchema.parse({
    ...mapCategory(value),
    project_count: projectCount,
  });
}

export function mapSkill(
  value: RawSkill,
  projectCount = "project_count" in value ? value.project_count : 0,
) {
  const detailed = "sort_order" in value ? value : undefined;
  return skillSchema.parse({
    id: value.id,
    slug: value.slug,
    name: value.name,
    category: detailed?.category?.name ?? "Technology",
    description: detailed?.description ?? undefined,
    icon: value.icon_key ?? undefined,
    proficiency_label: detailed?.proficiency_label ?? undefined,
    years: detailed?.years_experience ?? undefined,
    project_count: projectCount,
    order: detailed?.sort_order ?? 0,
  });
}

function mapMetric(value: z.infer<typeof rawMetricSchema>) {
  return metricSchema.parse({
    id: value.id,
    label: value.label,
    value: value.value,
    unit: value.unit ?? undefined,
    context: value.context,
    // The public endpoint is itself the approval boundary. Approval audit fields
    // deliberately remain private, so every record admitted here is verified.
    verified: true,
    evidence_url: value.public_evidence?.url ?? undefined,
    evidence_label: value.public_evidence?.label ?? undefined,
  });
}

function mapTestimonial(value: z.infer<typeof rawTestimonialSchema>) {
  return testimonialSchema.parse({
    id: value.id,
    quote: value.quote,
    attribution_name: value.attribution_name,
    attribution_role: value.attribution_title ?? undefined,
    attribution_organization: value.attribution_organization ?? undefined,
    verified: true,
    source_url: value.public_evidence?.url ?? undefined,
    source_label: value.public_evidence?.label ?? undefined,
  });
}

function mapProjectMedia(value: z.infer<typeof rawProjectMediaSchema>) {
  if (!value.is_visible) return undefined;
  return mediaAssetSchema.parse({
    id: value.id,
    kind: mediaKind(value.media_type),
    url: value.external_url ?? `/api/v1/public/project-media/${value.id}`,
    alt: value.alt_text,
    is_decorative: value.is_decorative,
    filename: value.original_filename ?? undefined,
    mime_type: value.media_type,
    width: value.width ?? undefined,
    height: value.height ?? undefined,
    duration_seconds: value.duration_seconds ?? undefined,
    page_count: value.page_count ?? undefined,
    caption: value.caption ?? undefined,
  });
}

function projectLinks(value: RawProject) {
  const links: Array<{
    label: string;
    url: string;
    kind: "website" | "source" | "demo" | "social" | "sponsor" | "other";
    external: boolean;
  }> = [];
  for (const item of value.links) {
    const label = typeof item.label === "string" ? item.label : "Project link";
    const url = typeof item.url === "string" ? item.url : undefined;
    if (url) links.push({ label, url, kind: "other", external: true });
  }
  if (
    value.repository_url &&
    !links.some((item) => item.url === value.repository_url)
  ) {
    links.push({
      label: "Source",
      url: value.repository_url,
      kind: "source",
      external: true,
    });
  }
  if (value.live_url && !links.some((item) => item.url === value.live_url)) {
    links.push({
      label: "Live site",
      url: value.live_url,
      kind: "demo",
      external: true,
    });
  }
  return links;
}

export function mapProjectSummary(value: RawProject) {
  const media = value.media
    .map(mapProjectMedia)
    .filter((item) => item !== undefined);
  return projectSummarySchema.parse({
    id: value.id,
    slug: value.slug,
    title: value.title,
    summary: value.summary,
    year: (value.end_date ?? value.start_date)?.slice(0, 4),
    role: value.role ?? undefined,
    status_label: value.is_open_source ? "Open source" : undefined,
    nature: value.nature,
    featured_rank:
      value.featured_rank && value.featured_rank <= 5
        ? value.featured_rank
        : undefined,
    cover: media.find((item) => item.kind === "image"),
    categories: value.category ? [mapCategory(value.category)] : [],
    sectors: value.sectors.map((item) => mapSector(item)),
    skills: value.skills.map((item) => mapSkill(item)),
    metrics: value.metrics.map(mapMetric),
    links: projectLinks(value),
  });
}

export function mapProjectDetail(value: RawProjectDetail) {
  const summary = mapProjectSummary(value);
  const allMedia = value.media
    .map(mapProjectMedia)
    .filter((item) => item !== undefined);
  const gallery = allMedia.filter((item) => item.id !== summary.cover?.id);
  const sections: Array<Record<string, unknown>> = [];
  if (value.description)
    sections.push({
      id: `${value.id}-context`,
      kind: "narrative",
      eyebrow: "Context",
      title: "Project context",
      body: value.description,
    });
  if (value.problem)
    sections.push({
      id: `${value.id}-problem`,
      kind: "narrative",
      eyebrow: "Challenge",
      title: "The problem",
      body: value.problem,
    });
  if (value.solution)
    sections.push({
      id: `${value.id}-solution`,
      kind: "narrative",
      eyebrow: "Solution",
      title: "The system",
      body: value.solution,
    });
  if (value.architecture)
    sections.push({
      id: `${value.id}-architecture`,
      kind: "architecture",
      title: "Architecture",
      body: value.architecture,
    });
  if (value.features.length > 0)
    sections.push({
      id: `${value.id}-features`,
      kind: "features",
      title: "Key capabilities",
      items: value.features,
    });
  if (value.decisions.length > 0)
    sections.push({
      id: `${value.id}-decisions`,
      kind: "decisions",
      title: "Engineering decisions",
      items: value.decisions,
    });
  if (value.tradeoffs.length > 0)
    sections.push({
      id: `${value.id}-tradeoffs`,
      kind: "decisions",
      eyebrow: "Tradeoffs",
      title: "Deliberate tradeoffs",
      items: value.tradeoffs,
    });
  if (value.challenges.length > 0)
    sections.push({
      id: `${value.id}-challenges`,
      kind: "narrative",
      eyebrow: "Constraints",
      title: "Challenges encountered",
      items: value.challenges,
    });
  if (value.outcomes.length > 0)
    sections.push({
      id: `${value.id}-outcomes`,
      kind: "narrative",
      eyebrow: "Outcomes",
      title: "What changed",
      items: value.outcomes,
    });
  return projectDetailSchema.parse({
    ...summary,
    sections,
    testimonials: value.testimonials.map(mapTestimonial),
    gallery,
    related_projects: value.related_projects.map(mapProjectSummary),
    seo: {
      title: value.seo_title ?? value.title,
      description: value.seo_description ?? value.summary,
      canonical_url: `/projects/${value.slug}`,
      noindex: value.noindex,
      og_image: summary.cover ?? gallery.find((item) => item.kind === "image"),
      keywords: [
        ...value.skills.map((item) => item.name),
        ...value.sectors.map((item) => item.name),
      ],
    },
  });
}

export function mapExperience(value: z.infer<typeof rawExperienceSchema>) {
  return experienceSchema.parse({
    id: value.id,
    organization: value.organization,
    role: value.role,
    location: value.location ?? undefined,
    employment_type: value.employment_type ?? undefined,
    start_date: value.start_date,
    end_date: value.end_date ?? undefined,
    current: value.end_date === null,
    summary: value.summary,
    achievements: value.achievements,
    skills: value.skills.map((item) => mapSkill(item)),
    sectors: value.sectors.map((item) => mapSector(item)),
  });
}

export function mapEducation(value: z.infer<typeof rawEducationSchema>) {
  return educationSchema.parse({
    id: value.id,
    institution: value.institution,
    credential: value.credential,
    field: value.field_of_study ?? undefined,
    location: value.location ?? undefined,
    start_date: value.start_date ?? undefined,
    end_date: value.end_date ?? undefined,
    details: value.summary ?? undefined,
    achievements: value.achievements,
  });
}

export function mapCertification(
  value: z.infer<typeof rawCertificationSchema>,
) {
  return certificationSchema.parse({
    id: value.id,
    name: value.name,
    issuer: value.issuer,
    issued_at: value.issued_on ?? undefined,
    expires_at: value.expires_on ?? undefined,
    credential_url: value.credential_url ?? undefined,
    credential_id: value.credential_id ?? undefined,
    description: value.description ?? undefined,
  });
}

function mapContentMedia(value: z.infer<typeof rawContentMediaSchema>) {
  return mediaAssetSchema.parse({
    id: value.id,
    kind: mediaKind(value.media_type),
    url: `/api/v1/public/media/${value.id}`,
    alt: value.alt_text,
    is_decorative: value.is_decorative,
    filename: value.original_filename,
    mime_type: value.media_type,
    width: value.width ?? undefined,
    height: value.height ?? undefined,
    duration_seconds: value.duration_seconds ?? undefined,
    page_count: value.page_count ?? undefined,
    caption: value.caption ?? undefined,
  });
}

export function mapArticleSummary(value: z.infer<typeof rawArticleSummarySchema>) {
  return articleSummarySchema.parse({
    id: value.id,
    slug: value.slug,
    title: value.title,
    excerpt: value.excerpt,
    published_at: value.published_at ?? value.created_at,
    updated_at: value.updated_at,
    reading_minutes: value.reading_minutes ?? 1,
    topics: value.topics,
    cover: value.hero_media ? mapContentMedia(value.hero_media) : undefined,
  });
}

export function mapArticleDetail(value: z.infer<typeof rawArticleSchema>) {
  return articleDetailSchema.parse({
    ...mapArticleSummary(value),
    blocks: [
      { id: `${value.id}-body`, kind: "markdown", source: value.body_markdown },
    ],
    related_articles: value.related_articles.map(mapArticleSummary),
    seo: {
      title: value.seo_title ?? value.title,
      description: value.seo_description ?? value.excerpt,
      canonical_url: `/writing/${value.slug}`,
      noindex: value.noindex,
      og_image: value.hero_media
        ? mapContentMedia(value.hero_media)
        : undefined,
      keywords: value.topics,
    },
  });
}

const sectionKinds: Partial<Record<string, HomepageSectionKind>> = {
  hero: "hero",
  resume: "resume",
  availability: "availability",
  what_i_build: "what_i_build",
  categories: "categories",
  selected_work: "selected_work",
  metrics: "metrics",
  testimonials: "testimonials",
  sectors: "sectors",
  skills: "skills",
  experience: "experience",
  education: "education",
  certifications: "certifications",
  open_source: "open_source",
  sponsorship: "sponsorship",
  writing: "writing",
  assistant: "assistant",
  contact: "contact",
  social_links: "social_links",
  editorial: "editorial",
};

function mapSections(homepage: RawHomepage) {
  const seen = new Set<HomepageSectionKind>();
  return homepage.sections
    .sort((a, b) => a.section.position - b.section.position)
    .flatMap(({ section }) => {
      const kind = sectionKinds[section.section_type];
      if (!kind || seen.has(kind)) return [];
      seen.add(kind);
      const theme =
        section.theme === "contrast" ||
        section.theme === "muted" ||
        section.theme === "accent"
          ? section.theme
          : "default";
      return [
        homepageSectionSchema.parse({
          id: section.id,
          kind,
          enabled: section.enabled,
          order: section.position,
          variant: section.variant,
          animation_variant: section.animation_variant ?? "reveal",
          data_limit: section.data_limit ?? undefined,
          cta_visible: section.show_cta,
          theme,
          feature_key: section.feature_key ?? undefined,
          custom_heading: section.title ?? undefined,
          configuration: section.configuration,
        }),
      ];
    });
}

function asRecord(value: unknown): Record<string, unknown> | undefined {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : undefined;
}

export function mapEditorialBlocks(homepage: RawHomepage) {
  const blocks = homepage.sections.flatMap(({ section, data }) => {
    if (section.section_type !== "editorial") return [];
    const record = asRecord(data);
    const candidates = Array.isArray(data)
      ? data
      : Array.isArray(record?.blocks)
        ? record.blocks
        : Array.isArray(record?.editorial_blocks)
          ? record.editorial_blocks
          : record
            ? [record]
            : [];
    return candidates.flatMap((candidate, index) => {
      const candidateRecord = asRecord(candidate);
      if (!candidateRecord) return [];
      const parsed = editorialBlockSchema.safeParse({
        ...candidateRecord,
        id:
          typeof candidateRecord.id === "string" && candidateRecord.id
            ? candidateRecord.id
            : `${section.id}-${index + 1}`,
      });
      return parsed.success ? [parsed.data] : [];
    });
  });
  return [...new Map(blocks.map((block) => [block.id, block])).values()];
}

function sectionItems<T>(
  homepage: RawHomepage,
  names: readonly string[],
  schema: z.ZodType<T>,
): T[] {
  const values: T[] = [];
  for (const payload of homepage.sections) {
    if (
      !names.includes(payload.section.section_type) ||
      !Array.isArray(payload.data)
    )
      continue;
    for (const item of payload.data) {
      const parsed = schema.safeParse(item);
      if (parsed.success) values.push(parsed.data);
    }
  }
  return [
    ...new Map(
      values.map((item) => [String((item as { id?: unknown }).id), item]),
    ).values(),
  ];
}

export function mapSponsorship(
  value: RawSponsorship,
  presentation?: z.infer<typeof sitePresentationSchema>,
) {
  return sponsorshipSchema.parse({
    enabled: value.items.length > 0,
    title:
      presentation?.sponsorship_title ?? "Support sustainable open-source work",
    description:
      presentation?.sponsorship_description ?? value.items[0]?.description ??
      "Transparent sponsorship helps maintain public technical work.",
    links: value.items.map((item) => ({
      label: item.cta_label,
      url: item.destination_url,
      kind: "sponsor",
      external: true,
    })),
    principles: presentation?.sponsorship_principles ?? [
      "Public work remains technically independent.",
      "Sponsored links are explicitly identified.",
      "No private access or endorsement is implied.",
    ],
  });
}

export function mapHomePage(
  homepage: RawHomepage,
  sponsorship: RawSponsorship,
) {
  if (!homepage.profile)
    throw new Error("The canonical API has no published profile.");
  const categories = sectionItems(
    homepage,
    ["what_i_build", "categories"],
    rawCategorySchema,
  ).map(mapCategory);
  const projectRecords = sectionItems(
    homepage,
    ["selected_work"],
    rawProjectSummarySchema,
  );
  const projects = projectRecords.map(mapProjectSummary).slice(0, 5);
  const metrics = sectionItems(homepage, ["metrics"], rawMetricSchema).map(mapMetric);
  const testimonials = sectionItems(
    homepage,
    ["testimonials"],
    rawTestimonialSchema,
  ).map(mapTestimonial);
  const sectors = sectionItems(homepage, ["sectors"], rawSectorSchema).map(
    (sector) => mapSector(sector),
  );
  const skills = sectionItems(homepage, ["skills"], rawSkillSchema).map(
    (item) => mapSkill(item),
  );
  const experience = sectionItems(
    homepage,
    ["experience"],
    rawExperienceSchema,
  ).map(mapExperience);
  const education = sectionItems(
    homepage,
    ["education"],
    rawEducationSchema,
  ).map(mapEducation);
  const certifications = sectionItems(
    homepage,
    ["certifications"],
    rawCertificationSchema,
  ).map(mapCertification);
  const openSource = sectionItems(homepage, ["open_source"], rawProjectSummarySchema)
    .filter((item) => item.is_open_source && item.repository_url)
    .map(mapOpenSourceProject);
  const articles = sectionItems(homepage, ["writing"], rawArticleSummarySchema).map(
    mapArticleSummary,
  );
  return homePageSchema.parse({
    profile: mapProfile(homepage.profile, homepage.current_resume),
    presentation: homepage.site_presentation,
    sections: mapSections(homepage),
    categories,
    featured_projects: projects,
    metrics,
    testimonials,
    sectors,
    skills,
    experience,
    education,
    certifications,
    open_source: openSource,
    sponsorship: mapSponsorship(sponsorship, homepage.site_presentation),
    articles,
    editorial_blocks: mapEditorialBlocks(homepage),
    feature_flags: homepage.features,
    seo: {
      title: `${homepage.profile.full_name} — ${homepage.profile.headline}`,
      description: homepage.profile.short_bio,
      canonical_url: "/",
      noindex: homepage.profile.noindex,
      keywords: [
        ...skills.slice(0, 12).map((item) => item.name),
        ...sectors.slice(0, 8).map((item) => item.name),
      ],
    },
  });
}

export function mapSiteShell(homepage: z.infer<typeof rawSiteShellSchema>) {
  const enabled = homepage.features.assistant ?? false;
  const defaults = {
    enabled,
    greeting: "Ask about published projects, experience, skills, and writing.",
    suggested_questions: [
      "Which projects best demonstrate production AI work?",
      "What technologies appear across the selected projects?",
      "What experience is most relevant to platform engineering?",
    ],
    disclaimer:
      "Answers use published portfolio evidence and may ask you to narrow the question.",
    max_question_length: 600,
  };
  const configured = assistantSettingsSchema.safeParse({
    ...defaults,
    ...homepage.feature_configurations.assistant,
    enabled,
  });
  const assistantSettings = configured.success ? configured.data : defaults;
  return siteShellSchema.parse({
    brand_name: homepage.site_presentation.site_name,
    header_navigation: homepage.navigation
      .filter((item) => item.location === "header")
      .sort((a, b) => a.sort_order - b.sort_order)
      .map((item) => ({
        id: item.id,
        label: item.label,
        href: item.href,
        external: item.open_in_new_tab || /^https?:\/\//i.test(item.href),
        order: item.sort_order,
        location: item.location,
      })),
    footer_navigation: homepage.navigation
      .filter((item) => item.location === "footer")
      .sort((a, b) => a.sort_order - b.sort_order)
      .map((item) => ({
        id: item.id,
        label: item.label,
        href: item.href,
        external: item.open_in_new_tab || /^https?:\/\//i.test(item.href),
        order: item.sort_order,
        location: item.location,
      })),
    socials: homepage.profile
      ? mapProfile(homepage.profile, null).socials
      : [],
    assistant_enabled: enabled,
    assistant_settings: assistantSettings,
    contact_enabled: homepage.features.contact ?? false,
    public_email: homepage.profile?.public_email ?? undefined,
    presentation: homepage.site_presentation,
  });
}

export function mapProfilePage(
  profile: RawProfile,
  resume: z.infer<typeof rawResumeSchema> | null,
  experience: z.infer<typeof rawExperienceSchema>[],
  education: z.infer<typeof rawEducationSchema>[],
  certifications: z.infer<typeof rawCertificationSchema>[],
  presentation: z.infer<typeof sitePresentationSchema>,
) {
  return profilePageSchema.parse({
    profile: mapProfile(profile, resume),
    presentation,
    experience: experience.map(mapExperience),
    education: education.map(mapEducation),
    certifications: certifications.map(mapCertification),
    seo: {
      title: `About ${profile.full_name}`,
      description: profile.short_bio,
      canonical_url: "/about",
      noindex: profile.noindex,
    },
  });
}

function pageInfo(total: number, page: number, pageSize: number) {
  return {
    page,
    page_size: pageSize,
    total,
    total_pages: total === 0 ? 0 : Math.ceil(total / pageSize),
  };
}

export function mapProjectsPage(
  projects: RawProject[],
  categories: z.infer<typeof rawCategorySchema>[],
  sectors: z.infer<typeof rawSectorSchema>[],
  page: number,
  pageSize: number,
  total: number,
  presentation: z.infer<typeof sitePresentationSchema>,
) {
  return projectsPageSchema.parse({
    items: projects.map(mapProjectSummary),
    page_info: pageInfo(total, page, pageSize),
    categories: categories.map(mapCategory),
    sectors: sectors.map((sector) => mapSector(sector)),
    presentation,
    seo: {
      title: presentation.projects_title,
      description: presentation.projects_intro,
      canonical_url: "/projects",
      noindex: false,
    },
  });
}

export function mapSectorsPage(
  sectors: z.infer<typeof rawSectorSchema>[],
  presentation: z.infer<typeof sitePresentationSchema>,
) {
  return sectorsPageSchema.parse({
    items: sectors.map((sector) => mapSector(sector)),
    presentation,
    seo: {
      title: presentation.sectors_title,
      description: presentation.sectors_intro,
      canonical_url: "/sectors",
      noindex: false,
    },
  });
}

export function mapSectorDetail(
  sector: z.infer<typeof rawSectorSchema>,
  projects: RawProject[],
) {
  const matching = projects.filter((project) =>
    project.sectors.some((item) => item.id === sector.id),
  );
  const skills = [
    ...new Map(
      matching
        .flatMap((project) => project.skills)
        .map((item) => [item.id, item]),
    ).values(),
  ];
  const metrics = matching.flatMap((project) => project.metrics);
  return sectorDetailSchema.parse({
    ...mapSector(sector, matching.length),
    projects: matching.map(mapProjectSummary),
    skills: skills.map((item) => mapSkill(item)),
    metrics: metrics.map(mapMetric),
    seo: {
      title: sector.name,
      description: sector.description,
      canonical_url: `/sectors/${sector.slug}`,
      noindex: sector.noindex,
    },
  });
}

export function mapOpenSourceProject(value: RawProject) {
  if (!value.repository_url)
    throw new Error("An open-source project must publish a repository URL.");
  return openSourceProjectSchema.parse({
    id: value.id,
    slug: value.slug,
    name: value.title,
    description: value.summary,
    repository_url: value.repository_url,
    website_url: value.live_url ?? undefined,
    status_label: "Open source",
    language: value.repository_metadata?.language ?? undefined,
    stars: value.repository_metadata?.stars ?? undefined,
    forks: value.repository_metadata?.forks ?? undefined,
    metadata_provider: value.repository_metadata?.provider ?? undefined,
    repository_identity: value.repository_metadata?.repository_identity ?? undefined,
    metadata_fetched_at: value.repository_metadata?.fetched_at ?? undefined,
    metadata_freshness: value.repository_metadata?.freshness ?? undefined,
    skills: value.skills.map((item) => mapSkill(item)),
  });
}

export function mapOpenSourcePage(
  projects: RawProject[],
  sponsorship: RawSponsorship,
  presentation: z.infer<typeof sitePresentationSchema>,
) {
  return openSourcePageSchema.parse({
    items: projects
      .filter((item) => item.is_open_source && item.repository_url)
      .map(mapOpenSourceProject),
    sponsorship: mapSponsorship(sponsorship, presentation),
    presentation,
    seo: {
      title: presentation.open_source_title,
      description: presentation.open_source_intro,
      canonical_url: "/open-source",
      noindex: false,
    },
  });
}

export function mapArticlesPage(
  articles: z.infer<typeof rawArticleSummarySchema>[],
  page: number,
  pageSize: number,
  total: number,
  topics: string[],
  presentation: z.infer<typeof sitePresentationSchema>,
) {
  return articlesPageSchema.parse({
    items: articles.map(mapArticleSummary),
    page_info: pageInfo(total, page, pageSize),
    topics,
    presentation,
    seo: {
      title: presentation.writing_title,
      description: presentation.writing_intro,
      canonical_url: "/writing",
      noindex: false,
    },
  });
}
