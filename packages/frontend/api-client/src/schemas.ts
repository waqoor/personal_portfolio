import { z } from "zod";

export const publicationStatusSchema = z.enum([
  "draft",
  "published",
  "hidden",
  "archived",
]);

export const isoDateSchema = z.string().datetime({ offset: true }).or(z.string().date());

export const mediaAssetSchema = z.object({
  id: z.string(),
  kind: z.enum(["image", "video", "document"]),
  url: z.string().min(1),
  alt: z.string().default(""),
  is_decorative: z.boolean().default(false),
  filename: z.string().optional(),
  mime_type: z.string().optional(),
  width: z.number().int().positive().optional(),
  height: z.number().int().positive().optional(),
  duration_seconds: z.number().int().nonnegative().optional(),
  page_count: z.number().int().positive().optional(),
  blur_data_url: z.string().optional(),
  focal_x: z.number().min(0).max(1).optional(),
  focal_y: z.number().min(0).max(1).optional(),
  caption: z.string().optional(),
});

export const linkSchema = z.object({
  label: z.string().min(1),
  url: z.string().min(1),
  kind: z.enum(["website", "source", "demo", "social", "sponsor", "other"]),
  external: z.boolean().default(true),
});

export const publicLinkSchema = z.string().refine((value) => {
  if (value.startsWith("/") && !value.startsWith("//") && !value.includes("\\"))
    return true;
  try {
    const parsed = new URL(value);
    return (
      (parsed.protocol === "https:" && !parsed.username && !parsed.password) ||
      (parsed.protocol === "mailto:" && !parsed.search && !parsed.hash)
    );
  } catch {
    return false;
  }
}, "Link must be a local path, HTTPS URL, or mailto address without credentials");

export const profileCtaSchema = z.object({
  label: z.string().min(1).max(80),
  url: publicLinkSchema,
});

export const seoSchema = z.object({
  title: z.string().min(1),
  description: z.string().min(1),
  canonical_url: z.string().optional(),
  noindex: z.boolean().default(false),
  og_image: mediaAssetSchema.optional(),
  keywords: z.array(z.string()).default([]),
});

export const resumeAssetSchema = z.object({
  id: z.string(),
  label: z.string(),
  filename: z.string(),
  download_url: z.string().min(1),
  updated_at: isoDateSchema,
  version: z.string().optional(),
  file_size_bytes: z.number().int().nonnegative().optional(),
});

export const socialLinkSchema = z.object({
  id: z.string(),
  platform: z.string(),
  label: z.string(),
  url: z.string().min(1),
  handle: z.string().optional(),
});

export const availabilitySchema = z.object({
  status: z.enum(["available", "selective", "unavailable"]),
  label: z.string(),
  details: z.string().optional(),
});

export const profileSchema = z.object({
  id: z.string(),
  name: z.string().min(1),
  eyebrow: z.string().optional(),
  headline: z.string().min(1),
  short_bio: z.string().min(1),
  long_bio: z.string().optional(),
  public_location: z.string().optional(),
  public_email: z.string().email().optional(),
  primary_cta: profileCtaSchema.optional(),
  secondary_cta: profileCtaSchema.optional(),
  timezone: z.string().optional(),
  pronouns: z.string().optional(),
  portrait: mediaAssetSchema.optional(),
  portrait_secondary: mediaAssetSchema.optional(),
  resume: resumeAssetSchema.optional(),
  availability: availabilitySchema,
  socials: z.array(socialLinkSchema).default([]),
});

export const categorySchema = z.object({
  id: z.string(),
  slug: z.string(),
  name: z.string(),
  short_name: z.string().optional(),
  description: z.string(),
  statement: z.string().optional(),
  accent: z.string().optional(),
  icon: z.string().optional(),
  order: z.number().int(),
});

export const sectorSchema = z.object({
  id: z.string(),
  slug: z.string(),
  name: z.string(),
  description: z.string(),
  evidence_summary: z.string().optional(),
  accent: z.string().optional(),
  icon: z.string().optional(),
  order: z.number().int(),
  project_count: z.number().int().nonnegative().default(0),
});

export const skillSchema = z.object({
  id: z.string(),
  slug: z.string(),
  name: z.string(),
  category: z.string(),
  description: z.string().optional(),
  icon: z.string().optional(),
  proficiency_label: z.string().optional(),
  years: z.number().nonnegative().optional(),
  project_count: z.number().int().nonnegative().default(0),
  order: z.number().int(),
});

export const metricSchema = z.object({
  id: z.string(),
  label: z.string(),
  value: z.string(),
  unit: z.string().optional(),
  context: z.string(),
  verified: z.boolean(),
  evidence_label: z.string().optional(),
  evidence_url: z.string().optional(),
});

export const testimonialSchema = z.object({
  id: z.string(),
  quote: z.string(),
  attribution_name: z.string(),
  attribution_role: z.string().optional(),
  attribution_organization: z.string().optional(),
  portrait: mediaAssetSchema.optional(),
  verified: z.boolean(),
  source_label: z.string().optional(),
  source_url: z.string().optional(),
});

export const projectSummarySchema = z.object({
  id: z.string(),
  slug: z.string(),
  title: z.string(),
  kicker: z.string().optional(),
  summary: z.string(),
  year: z.string().optional(),
  role: z.string().optional(),
  nature: z.enum(["case_study", "product", "software"]),
  status_label: z.string().optional(),
  featured_rank: z.number().int().min(1).max(5).optional(),
  cover: mediaAssetSchema.optional(),
  categories: z.array(categorySchema).default([]),
  sectors: z.array(sectorSchema).default([]),
  skills: z.array(skillSchema).default([]),
  metrics: z.array(metricSchema).default([]),
  links: z.array(linkSchema).default([]),
});

export const projectSectionSchema = z.object({
  id: z.string(),
  kind: z.enum(["narrative", "features", "architecture", "decisions", "media", "quote"]),
  eyebrow: z.string().optional(),
  title: z.string(),
  body: z.string().optional(),
  items: z.array(z.string()).default([]),
  media: z.array(mediaAssetSchema).default([]),
});

export const projectDetailSchema = projectSummarySchema.extend({
  sections: z.array(projectSectionSchema).default([]),
  testimonials: z.array(testimonialSchema).default([]),
  gallery: z.array(mediaAssetSchema).default([]),
  related_projects: z.array(projectSummarySchema).default([]),
  seo: seoSchema,
});

export const experienceSchema = z.object({
  id: z.string(),
  organization: z.string(),
  role: z.string(),
  location: z.string().optional(),
  employment_type: z.string().optional(),
  start_date: z.string(),
  end_date: z.string().optional(),
  current: z.boolean().default(false),
  summary: z.string(),
  achievements: z.array(z.string()).default([]),
  skills: z.array(skillSchema).default([]),
  sectors: z.array(sectorSchema).default([]),
  logo: mediaAssetSchema.optional(),
});

export const educationSchema = z.object({
  id: z.string(),
  institution: z.string(),
  credential: z.string(),
  field: z.string().optional(),
  location: z.string().optional(),
  start_date: z.string().optional(),
  end_date: z.string().optional(),
  details: z.string().optional(),
  achievements: z.array(z.string()).default([]),
  logo: mediaAssetSchema.optional(),
});

export const certificationSchema = z.object({
  id: z.string(),
  name: z.string(),
  issuer: z.string(),
  issued_at: z.string().optional(),
  expires_at: z.string().optional(),
  credential_url: z.string().optional(),
  credential_id: z.string().optional(),
  description: z.string().optional(),
  badge: mediaAssetSchema.optional(),
});

export const openSourceProjectSchema = z.object({
  id: z.string(),
  slug: z.string(),
  name: z.string(),
  description: z.string(),
  repository_url: z.string(),
  website_url: z.string().optional(),
  sponsor_url: z.string().optional(),
  language: z.string().optional(),
  stars: z.number().int().nonnegative().optional(),
  forks: z.number().int().nonnegative().optional(),
  metadata_provider: z.string().optional(),
  repository_identity: z.string().optional(),
  metadata_fetched_at: isoDateSchema.optional(),
  metadata_freshness: z.enum(["fresh", "stale"]).optional(),
  status_label: z.string().optional(),
  skills: z.array(skillSchema).default([]),
});

export const sponsorshipSchema = z.object({
  enabled: z.boolean(),
  title: z.string(),
  description: z.string(),
  links: z.array(linkSchema).default([]),
  principles: z.array(z.string()).default([]),
});

const textBlockSchema = z.object({
  id: z.string(),
  kind: z.literal("text"),
  body: z.string(),
});

const headingBlockSchema = z.object({
  id: z.string(),
  kind: z.literal("heading"),
  level: z.union([z.literal(2), z.literal(3)]),
  text: z.string(),
});

const quoteBlockSchema = z.object({
  id: z.string(),
  kind: z.literal("quote"),
  quote: z.string(),
  attribution: z.string().optional(),
});

const codeBlockSchema = z.object({
  id: z.string(),
  kind: z.literal("code"),
  code: z.string(),
  language: z.string().optional(),
  caption: z.string().optional(),
});

const imageBlockSchema = z.object({
  id: z.string(),
  kind: z.literal("image"),
  media: mediaAssetSchema,
  caption: z.string().optional(),
});

const listBlockSchema = z.object({
  id: z.string(),
  kind: z.literal("list"),
  style: z.enum(["ordered", "unordered"]),
  items: z.array(z.string()),
});

const markdownBlockSchema = z.object({
  id: z.string(),
  kind: z.literal("markdown"),
  source: z.string(),
});

export const articleBlockSchema = z.discriminatedUnion("kind", [
  textBlockSchema,
  headingBlockSchema,
  quoteBlockSchema,
  codeBlockSchema,
  imageBlockSchema,
  listBlockSchema,
  markdownBlockSchema,
]);

export const articleSummarySchema = z.object({
  id: z.string(),
  slug: z.string(),
  title: z.string(),
  excerpt: z.string(),
  published_at: isoDateSchema,
  updated_at: isoDateSchema.optional(),
  reading_minutes: z.number().int().positive(),
  topics: z.array(z.string()).default([]),
  cover: mediaAssetSchema.optional(),
});

export const articleDetailSchema = articleSummarySchema.extend({
  blocks: z.array(articleBlockSchema),
  related_articles: z.array(articleSummarySchema).default([]),
  seo: seoSchema,
});

export const editorialBlockSchema = z.object({
  id: z.string(),
  eyebrow: z.string().optional(),
  title: z.string(),
  body: z.string(),
  link: linkSchema.optional(),
  media: mediaAssetSchema.optional(),
});

export const homepageSectionKindSchema = z.enum([
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
]);

export const homepageSectionSchema = z.object({
  id: z.string(),
  kind: homepageSectionKindSchema,
  enabled: z.boolean(),
  order: z.number().int(),
  variant: z.string(),
  animation_variant: z.enum(["none", "reveal", "stagger"]).default("reveal"),
  data_limit: z.number().int().positive().optional(),
  cta_visible: z.boolean().default(true),
  theme: z.enum(["default", "contrast", "muted", "accent"]).default("default"),
  feature_key: z.string().regex(/^[a-z][a-z0-9_.-]{1,119}$/).optional(),
  custom_heading: z.string().optional(),
  configuration: z.record(z.string(), z.unknown()).default({}),
});

export const featureFlagsSchema = z.record(z.string(), z.boolean());

export const sitePresentationSchema = z.object({
  site_name: z.string().trim().min(1).max(160),
  default_title: z.string().trim().min(1).max(200),
  default_description: z.string().trim().min(1).max(320),
  locale: z.string().trim().min(2).max(35),
  footer_eyebrow: z.string().trim().min(1).max(120),
  footer_heading: z.string().trim().min(1).max(240),
  footer_statement: z.string().trim().min(1).max(240),
  about_title: z.string().trim().min(1).max(240),
  about_intro: z.string().trim().min(1).max(500),
  achievements_title: z.string().trim().min(1).max(200).default("Achievements"),
  achievements_intro: z.string().trim().min(1).max(500).default("Certifications, recognition, professional milestones, and published research."),
  work_title: z.string().trim().min(1).max(200).default("Work"),
  work_intro: z.string().trim().min(1).max(500).default("Full-time, contract, part-time, freelance, and project-based experience."),
  projects_title: z.string().trim().min(1).max(200),
  projects_intro: z.string().trim().min(1).max(500),
  writing_title: z.string().trim().min(1).max(200),
  writing_intro: z.string().trim().min(1).max(500),
  sectors_title: z.string().trim().min(1).max(200),
  sectors_intro: z.string().trim().min(1).max(500),
  open_source_title: z.string().trim().min(1).max(200),
  open_source_intro: z.string().trim().min(1).max(500),
  sponsorship_title: z.string().trim().min(1).max(200),
  sponsorship_description: z.string().trim().min(1).max(500),
  sponsorship_principles: z.array(z.string().trim().min(1).max(240)).min(1).max(8),
});

export const homePageSchema = z.object({
  profile: profileSchema,
  presentation: sitePresentationSchema,
  sections: z.array(homepageSectionSchema),
  categories: z.array(categorySchema).default([]),
  featured_projects: z.array(projectSummarySchema).max(5).default([]),
  metrics: z.array(metricSchema).default([]),
  testimonials: z.array(testimonialSchema).default([]),
  sectors: z.array(sectorSchema).default([]),
  skills: z.array(skillSchema).default([]),
  experience: z.array(experienceSchema).default([]),
  education: z.array(educationSchema).default([]),
  certifications: z.array(certificationSchema).default([]),
  open_source: z.array(openSourceProjectSchema).default([]),
  sponsorship: sponsorshipSchema.optional(),
  articles: z.array(articleSummarySchema).default([]),
  editorial_blocks: z.array(editorialBlockSchema).default([]),
  feature_flags: featureFlagsSchema.default({}),
  seo: seoSchema,
});

export const navigationItemSchema = z.object({
  id: z.string(),
  label: z.string(),
  href: z.string(),
  external: z.boolean().default(false),
  order: z.number().int(),
  location: z.enum(["header", "footer"]),
});

export const assistantSettingsSchema = z.object({
  enabled: z.boolean(),
  greeting: z.string().trim().min(1).max(500),
  suggested_questions: z.array(z.string().trim().min(2).max(240)).min(1).max(8),
  disclaimer: z.string().trim().min(1).max(500),
  max_question_length: z.number().int().min(50).max(2000),
});

export const siteShellSchema = z.object({
  brand_name: z.string(),
  brand_mark: z.string().optional(),
  header_navigation: z.array(navigationItemSchema),
  footer_navigation: z.array(navigationItemSchema),
  socials: z.array(socialLinkSchema).default([]),
  assistant_enabled: z.boolean(),
  assistant_settings: assistantSettingsSchema,
  contact_enabled: z.boolean(),
  public_email: z.string().email().optional(),
  presentation: sitePresentationSchema,
});

export const pageInfoSchema = z.object({
  page: z.number().int().positive(),
  page_size: z.number().int().positive(),
  total: z.number().int().nonnegative(),
  total_pages: z.number().int().nonnegative(),
});

export const projectsPageSchema = z.object({
  items: z.array(projectSummarySchema),
  page_info: pageInfoSchema,
  categories: z.array(categorySchema).default([]),
  sectors: z.array(sectorSchema).default([]),
  presentation: sitePresentationSchema,
  seo: seoSchema,
});

export const articlesPageSchema = z.object({
  items: z.array(articleSummarySchema),
  page_info: pageInfoSchema,
  topics: z.array(z.string()).default([]),
  presentation: sitePresentationSchema,
  seo: seoSchema,
});

export const profilePageSchema = z.object({
  profile: profileSchema,
  presentation: sitePresentationSchema,
  experience: z.array(experienceSchema),
  education: z.array(educationSchema),
  certifications: z.array(certificationSchema),
  seo: seoSchema,
});

export const sectorsPageSchema = z.object({
  items: z.array(sectorSchema),
  presentation: sitePresentationSchema,
  seo: seoSchema,
});

export const sectorDetailSchema = sectorSchema.extend({
  projects: z.array(projectSummarySchema).default([]),
  skills: z.array(skillSchema).default([]),
  metrics: z.array(metricSchema).default([]),
  seo: seoSchema,
});

export const openSourcePageSchema = z.object({
  items: z.array(openSourceProjectSchema),
  sponsorship: sponsorshipSchema.optional(),
  presentation: sitePresentationSchema,
  seo: seoSchema,
});

export const contactOptionsSchema = z.object({
  categories: z.array(z.object({ id: z.string(), label: z.string() })),
  response_time_label: z.string().optional(),
  accepting_messages: z.boolean(),
});

export const contactRequestSchema = z.object({
  name: z.string().trim().min(2).max(120),
  email: z.string().trim().email().max(254),
  category_id: z.enum(["general", "project", "collaboration", "speaking", "sponsorship", "other"]),
  organization: z.string().trim().max(160).optional(),
  subject: z.string().trim().min(3).max(180),
  message: z.string().trim().min(20).max(5000),
  website: z.string().max(0).optional(),
  consent: z.literal(true),
});

export const contactResponseSchema = z.object({
  id: z.string(),
  status: z.enum(["received", "queued"]),
  message: z.string(),
});

export const assistantRequestSchema = z.object({
  question: z.string().trim().min(3).max(2000),
});

export const assistantCitationSchema = z.object({
  citation: z.string(),
  title: z.string(),
  url: z.string(),
  excerpt: z.string().optional(),
});

export const assistantResponseSchema = z.object({
  answer: z.string(),
  citations: z.array(assistantCitationSchema).default([]),
  confidence: z.enum(["high", "medium", "low", "unknown"]),
});

export const sitemapEntrySchema = z.object({
  url: z.string(),
  last_modified: isoDateSchema.optional(),
  change_frequency: z.enum(["always", "hourly", "daily", "weekly", "monthly", "yearly", "never"]).optional(),
  priority: z.number().min(0).max(1).optional(),
});

export const sitemapSchema = z.array(sitemapEntrySchema);

export const discoveryPageSchema = z.object({
  metadata: z.object({
    title: z.string(),
    description: z.string(),
    canonical_url: z.string(),
    robots: z.string(),
    open_graph: z.object({
      type: z.string(),
      site_name: z.string(),
      locale: z.string(),
      title: z.string(),
      description: z.string(),
      url: z.string(),
      images: z.array(z.string()),
    }),
    twitter: z.object({
      card: z.string(),
      title: z.string(),
      description: z.string(),
      images: z.array(z.string()),
    }),
  }),
  breadcrumbs: z.array(z.object({ label: z.string(), url: z.string() })),
  related_urls: z.array(z.string()),
  json_ld: z.record(z.string(), z.unknown()),
});

export const machineTextSchema = z.object({ content: z.string() });

export const adminSessionSchema = z.object({
  authenticated: z.boolean(),
  user: z.object({
    id: z.string(),
    email: z.string().email(),
    display_name: z.string(),
    role: z.enum(["owner", "editor"]),
  }).optional(),
  csrf_token: z.string().optional(),
});

export const adminLoginRequestSchema = z.object({
  email: z.string().email(),
  password: z.string().min(12).max(256),
});

export const dashboardSummarySchema = z.object({
  counts: z.record(z.string(), z.number().int().nonnegative()),
  drafts: z.number().int().nonnegative(),
  pending_approvals: z.number().int().nonnegative(),
  unread_contacts: z.number().int().nonnegative(),
  recent_activity: z.array(z.object({
    id: z.string(),
    action: z.string(),
    resource: z.string(),
    label: z.string(),
    at: isoDateSchema,
  })).default([]),
});

export const adminResourceSchema = z.enum([
  "profile",
  "resumes",
  "categories",
  "sectors",
  "skills",
  "experience",
  "education",
  "certifications",
  "projects",
  "project-media",
  "metrics",
  "testimonials",
  "articles",
  "open-source",
  "sponsorship",
  "media",
  "navigation",
  "homepage-sections",
  "feature-settings",
  "site-settings",
  "assistant-settings",
  "contact-submissions",
]);

export const adminRecordSchema = z.object({
  id: z.string(),
  label: z.string(),
  slug: z.string().optional(),
  status: publicationStatusSchema.optional(),
  order: z.number().int().optional(),
  updated_at: isoDateSchema,
  data: z.record(z.string(), z.unknown()),
});

export const adminListResponseSchema = z.object({
  items: z.array(adminRecordSchema),
  page_info: pageInfoSchema,
});

export const featureSettingSchema = z.object({
  key: z.string(),
  label: z.string(),
  description: z.string().optional(),
  enabled: z.boolean(),
  public: z.boolean().default(true),
});

export const siteSettingsSchema = sitePresentationSchema;

export const mutationResponseSchema = z.object({
  id: z.string(),
  message: z.string(),
  updated_at: isoDateSchema.optional(),
});

export type MediaAsset = z.infer<typeof mediaAssetSchema>;
export type Link = z.infer<typeof linkSchema>;
export type Seo = z.infer<typeof seoSchema>;
export type ResumeAsset = z.infer<typeof resumeAssetSchema>;
export type SocialLink = z.infer<typeof socialLinkSchema>;
export type Profile = z.infer<typeof profileSchema>;
export type Category = z.infer<typeof categorySchema>;
export type Sector = z.infer<typeof sectorSchema>;
export type Skill = z.infer<typeof skillSchema>;
export type Metric = z.infer<typeof metricSchema>;
export type Testimonial = z.infer<typeof testimonialSchema>;
export type ProjectSummary = z.infer<typeof projectSummarySchema>;
export type ProjectDetail = z.infer<typeof projectDetailSchema>;
export type ProjectSection = z.infer<typeof projectSectionSchema>;
export type Experience = z.infer<typeof experienceSchema>;
export type Education = z.infer<typeof educationSchema>;
export type Certification = z.infer<typeof certificationSchema>;
export type OpenSourceProject = z.infer<typeof openSourceProjectSchema>;
export type Sponsorship = z.infer<typeof sponsorshipSchema>;
export type ArticleSummary = z.infer<typeof articleSummarySchema>;
export type ArticleDetail = z.infer<typeof articleDetailSchema>;
export type ArticleBlock = z.infer<typeof articleBlockSchema>;
export type EditorialBlock = z.infer<typeof editorialBlockSchema>;
export type HomepageSectionKind = z.infer<typeof homepageSectionKindSchema>;
export type HomepageSection = z.infer<typeof homepageSectionSchema>;
export type HomePage = z.infer<typeof homePageSchema>;
export type SiteShell = z.infer<typeof siteShellSchema>;
export type NavigationItem = z.infer<typeof navigationItemSchema>;
export type ProjectsPage = z.infer<typeof projectsPageSchema>;
export type ArticlesPage = z.infer<typeof articlesPageSchema>;
export type ProfilePage = z.infer<typeof profilePageSchema>;
export type SectorsPage = z.infer<typeof sectorsPageSchema>;
export type SectorDetail = z.infer<typeof sectorDetailSchema>;
export type OpenSourcePage = z.infer<typeof openSourcePageSchema>;
export type ContactOptions = z.infer<typeof contactOptionsSchema>;
export type ContactRequest = z.infer<typeof contactRequestSchema>;
export type ContactResponse = z.infer<typeof contactResponseSchema>;
export type AssistantRequest = z.infer<typeof assistantRequestSchema>;
export type AssistantResponse = z.infer<typeof assistantResponseSchema>;
export type SitemapEntry = z.infer<typeof sitemapEntrySchema>;
export type DiscoveryPage = z.infer<typeof discoveryPageSchema>;
export type AdminSession = z.infer<typeof adminSessionSchema>;
export type AdminLoginRequest = z.infer<typeof adminLoginRequestSchema>;
export type DashboardSummary = z.infer<typeof dashboardSummarySchema>;
export type AdminResource = z.infer<typeof adminResourceSchema>;
export type AdminRecord = z.infer<typeof adminRecordSchema>;
export type AdminListResponse = z.infer<typeof adminListResponseSchema>;
export type FeatureSetting = z.infer<typeof featureSettingSchema>;
export type SiteSettings = z.infer<typeof siteSettingsSchema>;
export type AssistantSettings = z.infer<typeof assistantSettingsSchema>;
