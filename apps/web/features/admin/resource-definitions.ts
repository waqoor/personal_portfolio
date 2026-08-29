import type { AdminListQuery, AdminResource } from "@portfolio/api-client";

export type AdminFieldType =
  | "text"
  | "slug"
  | "url"
  | "email"
  | "textarea"
  | "number"
  | "date"
  | "datetime"
  | "switch"
  | "select"
  | "relation-one"
  | "relation-many"
  | "json";

export type AdminRelationDefinition = {
  resource: AdminResource;
  selectedDataKey?: string;
  filters?: Readonly<Pick<AdminListQuery, "approved" | "status">>;
  ordered?: boolean;
};

export type AdminFieldDefinition = {
  key: string;
  label: string;
  type: AdminFieldType;
  description?: string;
  required?: boolean;
  readOnly?: boolean;
  placeholder?: string;
  options?: ReadonlyArray<{ label: string; value: string }>;
  min?: number;
  max?: number;
  defaultChecked?: boolean;
  relation?: AdminRelationDefinition;
};

export type AdminResourceDefinition = {
  label: string;
  singular: string;
  description: string;
  supportsPublication: boolean;
  createEnabled: boolean;
  editEnabled?: boolean;
  deleteEnabled: boolean;
  ownerOnly?: boolean;
  fields: readonly AdminFieldDefinition[];
};

const visibilityFields: readonly AdminFieldDefinition[] = [
  { key: "is_visible", label: "Visible when published", type: "switch", defaultChecked: true },
  { key: "noindex", label: "Exclude from search indexing", type: "switch" },
];

const sortField: AdminFieldDefinition = { key: "sort_order", label: "Display order", type: "number", min: 0 };
const evidenceFields: readonly AdminFieldDefinition[] = [
  {
    key: "evidence_kind",
    label: "Evidence source type",
    type: "select",
    options: [
      { label: "Reviewed public URL", value: "public_url" },
      { label: "Managed project media", value: "managed_media" },
      { label: "Private document reference", value: "document_reference" },
    ],
    description: "Choose one source type. Saving an empty evidence section removes the draft evidence.",
  },
  {
    key: "evidence_visibility",
    label: "Evidence visibility",
    type: "select",
    options: [
      { label: "Private review only", value: "private_review" },
      { label: "Public label and source", value: "public" },
    ],
  },
  { key: "evidence_reference_url", label: "Public evidence URL", type: "url", placeholder: "https://â€¦" },
  {
    key: "evidence_managed_media_id",
    label: "Managed evidence asset",
    type: "relation-one",
    relation: { resource: "project-media", selectedDataKey: "evidence_managed_media" },
    description: "Select a validated, active project-media asset. Archived assets are unavailable and revoke approval.",
  },
  { key: "evidence_reference_text", label: "Document reference", type: "textarea", placeholder: "Document title, revision, and page or section" },
  { key: "evidence_public_label", label: "Reviewed public label", type: "text", description: "Required only when evidence visibility is public." },
  { key: "evidence_provenance", label: "Provenance", type: "textarea", placeholder: "Where this evidence came from and who controls it" },
  { key: "evidence_captured_at", label: "Evidence captured on", type: "date" },
  { key: "evidence_reviewer_note", label: "Private reviewer note", type: "textarea" },
  { key: "is_approved", label: "Owner approval for the reviewed revision", type: "switch", description: "Approval is bound to the exact claim and evidence revision and is revoked by material edits." },
];
const availabilityOptions = [
  { label: "Available", value: "available" },
  { label: "Selective", value: "selective" },
  { label: "Unavailable", value: "unavailable" },
] as const;

export const RESOURCE_DEFINITIONS: Partial<Record<AdminResource, AdminResourceDefinition>> = {
  profile: {
    label: "Profile",
    singular: "profile",
    description: "Canonical public identity, positioning, availability, and calls to action.",
    supportsPublication: true,
    createEnabled: true,
    deleteEnabled: false,
    ownerOnly: true,
    fields: [
      { key: "full_name", label: "Public name", type: "text", required: true },
      { key: "headline", label: "Headline", type: "text", required: true },
      { key: "short_bio", label: "Short biography", type: "textarea", required: true },
      { key: "long_bio", label: "Long biography", type: "textarea" },
      { key: "public_location", label: "Public location", type: "text" },
      { key: "availability_status", label: "Availability", type: "select", options: availabilityOptions },
      { key: "availability_detail", label: "Availability detail", type: "textarea" },
      { key: "public_email", label: "Public email", type: "email" },
      { key: "primary_cta_label", label: "Primary CTA label", type: "text" },
      {
        key: "primary_cta_url",
        label: "Primary CTA URL",
        type: "text",
        placeholder: "/projects or https://example.com",
        description: "A site-relative path, HTTPS URL, or mailto address. The API validates the destination before saving.",
      },
      { key: "secondary_cta_label", label: "Secondary CTA label", type: "text" },
      {
        key: "secondary_cta_url",
        label: "Secondary CTA URL",
        type: "text",
        placeholder: "/sponsor or https://example.com",
        description: "A site-relative path, HTTPS URL, or mailto address. The API validates the destination before saving.",
      },
      { key: "is_primary", label: "Primary public profile", type: "switch", defaultChecked: true },
      ...visibilityFields,
    ],
  },
  resumes: {
    label: "Résumé versions",
    singular: "résumé version",
    description: "Validated immutable PDF versions. Publish one version as current while the public /resume URL stays stable.",
    supportsPublication: true,
    createEnabled: false,
    editEnabled: false,
    deleteEnabled: true,
    ownerOnly: true,
    fields: [
      { key: "version_label", label: "Version", type: "text", readOnly: true },
      { key: "original_filename", label: "Original file", type: "text", readOnly: true },
      { key: "download_name", label: "Download name", type: "text", readOnly: true },
      { key: "effective_date", label: "Effective date", type: "date", readOnly: true },
      { key: "size_bytes", label: "Bytes", type: "number", readOnly: true },
      { key: "is_current", label: "Current résumé", type: "switch", readOnly: true },
    ],
  },
  categories: {
    label: "Professional categories",
    singular: "category",
    description: "Capability groups used by projects, skills, and homepage composition.",
    supportsPublication: true,
    createEnabled: true,
    deleteEnabled: true,
    fields: [
      { key: "name", label: "Name", type: "text", required: true },
      { key: "slug", label: "Slug", type: "slug", required: true },
      { key: "description", label: "Description", type: "textarea", required: true },
      { key: "color", label: "Color token", type: "text" },
      { key: "icon_key", label: "Icon key", type: "text" },
      sortField,
      ...visibilityFields,
    ],
  },
  sectors: {
    label: "Sectors",
    singular: "sector",
    description: "Applied domains linked to published project evidence.",
    supportsPublication: true,
    createEnabled: true,
    deleteEnabled: true,
    fields: [
      { key: "name", label: "Name", type: "text", required: true },
      { key: "slug", label: "Slug", type: "slug", required: true },
      { key: "description", label: "Description", type: "textarea", required: true },
      { key: "color", label: "Color token", type: "text" },
      { key: "icon_key", label: "Icon key", type: "text" },
      sortField,
      ...visibilityFields,
    ],
  },
  skills: {
    label: "Skills & technologies",
    singular: "skill",
    description: "Technology-universe nodes with category relationships and honest practice context.",
    supportsPublication: true,
    createEnabled: true,
    deleteEnabled: true,
    fields: [
      { key: "name", label: "Name", type: "text", required: true },
      { key: "slug", label: "Slug", type: "slug", required: true },
      { key: "category_id", label: "Category", type: "relation-one", relation: { resource: "categories", selectedDataKey: "category" } },
      { key: "description", label: "Description", type: "textarea" },
      { key: "icon_key", label: "Icon key", type: "text" },
      { key: "proficiency_label", label: "Practice label", type: "text" },
      { key: "years_experience", label: "Years of experience", type: "number", min: 0 },
      sortField,
      ...visibilityFields,
    ],
  },
  experience: {
    label: "Experience",
    singular: "experience entry",
    description: "Professional roles with dates, achievements, and explicit portfolio relationships.",
    supportsPublication: true,
    createEnabled: true,
    deleteEnabled: true,
    fields: [
      { key: "organization", label: "Organization", type: "text", required: true },
      { key: "role", label: "Role", type: "text", required: true },
      { key: "location", label: "Location", type: "text" },
      { key: "employment_type", label: "Employment type", type: "text" },
      { key: "start_date", label: "Start date", type: "date", required: true },
      { key: "end_date", label: "End date", type: "date" },
      { key: "summary", label: "Summary", type: "textarea", required: true },
      { key: "achievements", label: "Achievements", type: "json", description: "JSON array of factual statements." },
      { key: "skill_ids", label: "Skills", type: "relation-many", relation: { resource: "skills", selectedDataKey: "skills" } },
      { key: "sector_ids", label: "Sectors", type: "relation-many", relation: { resource: "sectors", selectedDataKey: "sectors" } },
      { key: "project_ids", label: "Projects", type: "relation-many", relation: { resource: "projects", selectedDataKey: "projects" } },
      sortField,
      ...visibilityFields,
    ],
  },
  education: {
    label: "Education",
    singular: "education entry",
    description: "Formal education and appropriate supporting public details.",
    supportsPublication: true,
    createEnabled: true,
    deleteEnabled: true,
    fields: [
      { key: "institution", label: "Institution", type: "text", required: true },
      { key: "credential", label: "Credential", type: "text", required: true },
      { key: "field_of_study", label: "Field of study", type: "text" },
      { key: "location", label: "Location", type: "text" },
      { key: "start_date", label: "Start date", type: "date" },
      { key: "end_date", label: "End date", type: "date" },
      { key: "summary", label: "Summary", type: "textarea" },
      { key: "achievements", label: "Achievements", type: "json" },
      sortField,
      ...visibilityFields,
    ],
  },
  certifications: {
    label: "Credentials & recognition",
    singular: "credential or recognition",
    description: "Certifications, awards, recognition, issuers, dates, and public verification destinations.",
    supportsPublication: true,
    createEnabled: true,
    deleteEnabled: true,
    fields: [
      { key: "name", label: "Name", type: "text", required: true },
      { key: "issuer", label: "Issuer", type: "text", required: true },
      { key: "credential_id", label: "Credential ID", type: "text" },
      { key: "credential_url", label: "Credential URL", type: "url" },
      { key: "issued_on", label: "Issued on", type: "date" },
      { key: "expires_on", label: "Expires on", type: "date" },
      { key: "description", label: "Description", type: "textarea", description: "Start awards and recognition descriptions with “Recognition:” so the Achievements page groups them correctly." },
      sortField,
      ...visibilityFields,
    ],
  },
  projects: {
    label: "Projects",
    singular: "project",
    description: "Complete case studies, featured rank, relationships, evidence, and discovery metadata.",
    supportsPublication: true,
    createEnabled: true,
    deleteEnabled: true,
    fields: [
      { key: "title", label: "Title", type: "text", required: true },
      { key: "slug", label: "Slug", type: "slug", required: true },
      { key: "category_id", label: "Primary category", type: "relation-one", relation: { resource: "categories", selectedDataKey: "category" } },
      { key: "summary", label: "Summary", type: "textarea", required: true },
      { key: "description", label: "Description", type: "textarea" },
      { key: "role", label: "Role", type: "text" },
      { key: "start_date", label: "Start date", type: "date" },
      { key: "end_date", label: "End date", type: "date" },
      { key: "problem", label: "Problem", type: "textarea" },
      { key: "solution", label: "Solution", type: "textarea" },
      { key: "architecture", label: "Architecture", type: "textarea" },
      { key: "features", label: "Features", type: "json" },
      { key: "decisions", label: "Decisions", type: "json" },
      { key: "tradeoffs", label: "Tradeoffs", type: "json" },
      { key: "challenges", label: "Challenges", type: "json" },
      { key: "outcomes", label: "Outcomes", type: "json" },
      { key: "links", label: "Additional links", type: "json" },
      { key: "repository_url", label: "Repository URL", type: "url" },
      { key: "live_url", label: "Live URL", type: "url" },
      { key: "is_open_source", label: "Open source", type: "switch" },
      {
        key: "repository_metadata_refresh_enabled",
        label: "Refresh repository signals",
        type: "switch",
        description: "Owner opt-in for source-of-record language, star, and fork snapshots.",
      },
      {
        key: "nature",
        label: "Project nature",
        type: "select",
        options: [
          { label: "Case study / creative work", value: "case_study" },
          { label: "Product", value: "product" },
          { label: "Software source", value: "software" },
        ],
        description: "Controls reviewed schema.org classification. Open-source projects default to software.",
      },
      { key: "featured_rank", label: "Featured rank", type: "number", min: 1, max: 5, description: "Ranks 1–3 get the richest homepage treatment; at most five are public." },
      { key: "skill_ids", label: "Skills", type: "relation-many", relation: { resource: "skills", selectedDataKey: "skills" } },
      { key: "sector_ids", label: "Sectors", type: "relation-many", relation: { resource: "sectors", selectedDataKey: "sectors" } },
      { key: "seo_title", label: "SEO title", type: "text" },
      { key: "seo_description", label: "SEO description", type: "textarea" },
      ...visibilityFields,
    ],
  },
  metrics: {
    label: "Impact metrics",
    singular: "metric",
    description: "Metrics remain private until separately approved and supported by evidence context.",
    supportsPublication: true,
    createEnabled: true,
    deleteEnabled: true,
    fields: [
      { key: "project_id", label: "Project", type: "relation-one", relation: { resource: "projects", selectedDataKey: "project" } },
      { key: "experience_id", label: "Experience", type: "relation-one", relation: { resource: "experience", selectedDataKey: "experience" } },
      { key: "subject_label", label: "Subject label", type: "text" },
      { key: "label", label: "Metric label", type: "text", required: true },
      { key: "value", label: "Value", type: "text", required: true },
      { key: "unit", label: "Unit", type: "text" },
      { key: "context", label: "Context", type: "textarea", required: true },
      ...evidenceFields,
      sortField,
      ...visibilityFields,
    ],
  },
  testimonials: {
    label: "Testimonials",
    singular: "testimonial",
    description: "Quotes remain non-public until attribution, source review, and approval are complete.",
    supportsPublication: true,
    createEnabled: true,
    deleteEnabled: true,
    fields: [
      { key: "project_id", label: "Project", type: "relation-one", relation: { resource: "projects", selectedDataKey: "project" } },
      { key: "experience_id", label: "Experience", type: "relation-one", relation: { resource: "experience", selectedDataKey: "experience" } },
      { key: "subject_label", label: "Subject label", type: "text" },
      { key: "quote", label: "Quote", type: "textarea", required: true },
      { key: "attribution_name", label: "Attribution name", type: "text", required: true },
      { key: "attribution_title", label: "Attribution title", type: "text" },
      { key: "attribution_organization", label: "Organization", type: "text" },
      ...evidenceFields,
      sortField,
      ...visibilityFields,
    ],
  },
  articles: {
    label: "Writing",
    singular: "article",
    description: "Published Markdown articles, topics, managed hero media, and discovery metadata. Use the “Publication” topic for papers shown on Achievements.",
    supportsPublication: true,
    createEnabled: true,
    deleteEnabled: true,
    fields: [
      { key: "title", label: "Title", type: "text", required: true },
      { key: "slug", label: "Slug", type: "slug", required: true },
      { key: "excerpt", label: "Excerpt", type: "textarea", required: true },
      { key: "body_markdown", label: "Article body (Markdown)", type: "textarea", required: true },
      { key: "topics", label: "Topics", type: "json" },
      { key: "reading_minutes", label: "Reading minutes", type: "number", min: 1 },
      { key: "hero_media_id", label: "Hero media", type: "relation-one", relation: { resource: "media", selectedDataKey: "hero_media" } },
      { key: "seo_title", label: "SEO title", type: "text" },
      { key: "seo_description", label: "SEO description", type: "textarea" },
      ...visibilityFields,
    ],
  },
  "open-source": {
    label: "Open source",
    singular: "open-source project",
    description: "The open-source view of canonical projects, with repository and contribution context.",
    supportsPublication: true,
    createEnabled: true,
    deleteEnabled: true,
    fields: [
      { key: "title", label: "Project name", type: "text", required: true },
      { key: "slug", label: "Slug", type: "slug", required: true },
      { key: "summary", label: "Summary", type: "textarea", required: true },
      { key: "description", label: "Description", type: "textarea" },
      { key: "repository_url", label: "Repository URL", type: "url", required: true },
      { key: "live_url", label: "Live URL", type: "url" },
      { key: "featured_rank", label: "Featured rank", type: "number", min: 1, max: 5 },
      { key: "skill_ids", label: "Skills", type: "relation-many", relation: { resource: "skills", selectedDataKey: "skills" } },
      { key: "sector_ids", label: "Sectors", type: "relation-many", relation: { resource: "sectors", selectedDataKey: "sectors" } },
      { key: "seo_title", label: "SEO title", type: "text" },
      { key: "seo_description", label: "SEO description", type: "textarea" },
      ...visibilityFields,
    ],
  },
  sponsorship: {
    label: "Sponsorship",
    singular: "sponsorship option",
    description: "Manage the canonical sponsorship options exposed by the public sponsorship service.",
    supportsPublication: true,
    createEnabled: true,
    editEnabled: true,
    deleteEnabled: true,
    ownerOnly: true,
    fields: [
      { key: "title", label: "Title", type: "text", required: true },
      { key: "slug", label: "Slug", type: "text", required: true },
      { key: "description", label: "Description", type: "textarea", required: true },
      { key: "kind", label: "Kind", type: "text", required: true },
      { key: "cta_label", label: "CTA label", type: "text", required: true },
      { key: "destination_url", label: "HTTPS destination", type: "url", required: true },
      { key: "amount_minor", label: "Amount (minor units)", type: "number", min: 0 },
      { key: "currency", label: "Currency", type: "text" },
      { key: "recurrence", label: "Recurrence", type: "select", options: [{ label: "One time", value: "one_time" }, { label: "Monthly", value: "monthly" }, { label: "Yearly", value: "yearly" }] },
      { key: "sort_order", label: "Display order", type: "number", min: 0 },
      { key: "is_published", label: "Published", type: "switch" },
      { key: "nofollow", label: "Mark link sponsored/nofollow", type: "switch", defaultChecked: true },
    ],
  },
  media: {
    label: "Media library",
    singular: "media asset",
    description: "Validated images, video, documents, and accessible media metadata.",
    supportsPublication: true,
    createEnabled: true,
    deleteEnabled: true,
    fields: [
      { key: "original_filename", label: "Filename", type: "text", readOnly: true },
      { key: "media_type", label: "Media type", type: "text", readOnly: true },
      { key: "size_bytes", label: "Bytes", type: "number", readOnly: true },
      { key: "alt_text", label: "Alternative text", type: "textarea", required: true },
      { key: "caption", label: "Caption", type: "textarea" },
      { key: "width", label: "Width", type: "number", min: 1 },
      { key: "height", label: "Height", type: "number", min: 1 },
      { key: "duration_seconds", label: "Duration (seconds)", type: "number", min: 0 },
      ...visibilityFields,
    ],
  },
  navigation: {
    label: "Navigation",
    singular: "navigation item",
    description: "Ordered header/footer navigation with explicit link behavior.",
    supportsPublication: true,
    createEnabled: true,
    deleteEnabled: true,
    ownerOnly: true,
    fields: [
      { key: "label", label: "Label", type: "text", required: true },
      { key: "href", label: "Destination", type: "text", required: true },
      { key: "location", label: "Location", type: "select", options: [{ label: "Header", value: "header" }, { label: "Footer", value: "footer" }] },
      { key: "sort_order", label: "Display order", type: "number", min: 0 },
      { key: "open_in_new_tab", label: "Open in new tab", type: "switch" },
      ...visibilityFields,
    ],
  },
  "contact-submissions": {
    label: "Contact submissions",
    singular: "contact submission",
    description: "Review persisted inquiries in the authenticated CMS. Contact data never enters public responses or discovery.",
    supportsPublication: false,
    createEnabled: false,
    editEnabled: true,
    deleteEnabled: false,
    fields: [
      { key: "name", label: "Name", type: "text", readOnly: true },
      { key: "email", label: "Email", type: "email", readOnly: true },
      { key: "organization", label: "Organization", type: "text", readOnly: true },
      { key: "category", label: "Category", type: "text", readOnly: true },
      { key: "subject", label: "Subject", type: "text", readOnly: true },
      { key: "message", label: "Message", type: "textarea", readOnly: true },
      { key: "notification_status", label: "Notification", type: "text", readOnly: true },
      { key: "status", label: "Inbox status", type: "select", options: [{ label: "New", value: "new" }, { label: "Read", value: "read" }, { label: "Closed", value: "closed" }, { label: "Spam", value: "spam" }] },
    ],
  },
};

export const ADMIN_RESOURCE_LABELS: Record<AdminResource, string> = {
  profile: "Profile",
  resumes: "Identity assets",
  categories: "Professional categories",
  sectors: "Sectors",
  skills: "Skills & technologies",
  experience: "Experience",
  education: "Education",
  certifications: "Credentials & recognition",
  projects: "Projects",
  "project-media": "Project media",
  metrics: "Impact metrics",
  testimonials: "Testimonials",
  articles: "Writing",
  "open-source": "Open source",
  sponsorship: "Sponsorship",
  media: "Media library",
  navigation: "Navigation",
  "homepage-sections": "Homepage composition",
  "feature-settings": "Feature settings",
  "site-settings": "Site settings",
  "assistant-settings": "Assistant settings",
  "contact-submissions": "Contact submissions",
};
