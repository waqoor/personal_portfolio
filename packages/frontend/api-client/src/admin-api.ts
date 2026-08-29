import { z } from "zod";

import type { HttpClient } from "./client";
import { ApiError, queryString } from "./client";
import {
  adminListResponseSchema,
  adminLoginRequestSchema,
  adminRecordSchema,
  adminResourceSchema,
  adminSessionSchema,
  assistantSettingsSchema,
  dashboardSummarySchema,
  discoveryPageSchema,
  featureSettingSchema,
  homepageSectionKindSchema,
  homepageSectionSchema,
  mutationResponseSchema,
  siteSettingsSchema,
  type AdminLoginRequest,
  type AdminRecord,
  type AdminResource,
  type AssistantSettings,
  type HomepageSection,
  type SiteSettings,
} from "./schemas";
import { rawHomepageSchema } from "./canonical-public";

const rawAdminUserSchema = z
  .object({
    id: z.string(),
    email: z.string().email(),
    display_name: z.string(),
    role: z.enum(["owner", "editor"]),
    is_active: z.boolean().optional(),
  })
  .passthrough();

const rawLoginResponseSchema = z.object({
  admin: rawAdminUserSchema,
  expires_at: z.string(),
  csrf_token: z.string(),
});

const rawMessageSchema = z.object({ message: z.string() });
const rawRecordSchema = z
  .object({ id: z.string(), updated_at: z.string() })
  .passthrough();
const rawRecordListSchema = z.object({
  items: z.array(rawRecordSchema),
  total: z.number().int().nonnegative(),
  limit: z.number().int().positive(),
  offset: z.number().int().nonnegative(),
});
const rawRecordArraySchema = z.array(rawRecordSchema);

const rawPortraitAdminSchema = rawRecordSchema.extend({
  original_filename: z.string(),
  media_type: z.string(),
  size_bytes: z.number().int().nonnegative(),
  alt_text: z.string(),
  width: z.number().int().positive().nullable(),
  height: z.number().int().positive().nullable(),
  is_primary: z.boolean(),
  is_active: z.boolean(),
  sort_order: z.number().int().nonnegative(),
});
const rawResumeAdminSchema = rawRecordSchema.extend({
  status: z.enum(["draft", "published", "hidden", "archived"]),
  profile_id: z.string(),
  version_label: z.string(),
  original_filename: z.string(),
  media_type: z.string(),
  size_bytes: z.number().int().nonnegative(),
  effective_date: z.string().nullable(),
  is_current: z.boolean(),
  download_name: z.string(),
});
const rawProjectMediaAdminSchema = rawRecordSchema.extend({
  project_id: z.string(),
  external_url: z.string().nullable(),
  original_filename: z.string().nullable(),
  media_type: z.string(),
  size_bytes: z.number().int().nonnegative().nullable(),
  sha256: z.string().nullable(),
  alt_text: z.string(),
  is_decorative: z.boolean(),
  caption: z.string().nullable(),
  width: z.number().int().positive().nullable(),
  height: z.number().int().positive().nullable(),
  duration_seconds: z.number().int().nonnegative().nullable(),
  page_count: z.number().int().positive().nullable(),
  sort_order: z.number().int().nonnegative(),
  is_visible: z.boolean(),
});
const rawRepositoryMetadataAdminSchema = rawRecordSchema.extend({
  provider: z.string(),
  repository_identity: z.string().nullable(),
  language: z.string().nullable(),
  stars: z.number().int().nonnegative().nullable(),
  forks: z.number().int().nonnegative().nullable(),
  fetched_at: z.string().nullable(),
  stale_after: z.string().nullable(),
  status: z.enum(["fresh", "stale", "refreshing", "rate_limited", "unavailable"]),
  last_error_code: z.string().nullable(),
  last_error_at: z.string().nullable(),
  retry_after: z.string().nullable(),
});
const rawFeaturedProjectOrderSchema = z.object({
  limit: z.number().int().min(1).max(5),
  projects: z.array(rawRecordSchema).max(5),
});
const rawSocialLinkAdminSchema = rawRecordSchema.extend({
  profile_id: z.string(),
  platform: z.string(),
  label: z.string(),
  url: z.string(),
  handle: z.string().nullable(),
  sort_order: z.number().int().nonnegative(),
  is_visible: z.boolean(),
});
const rawProfileAssetsSchema = rawRecordSchema.extend({
  full_name: z.string(),
  status: z.enum(["draft", "published", "hidden", "archived"]),
  portraits: z.array(rawPortraitAdminSchema),
  social_links: z.array(rawSocialLinkAdminSchema),
});
const rawProfileAssetsPageSchema = z.object({
  items: z.array(rawProfileAssetsSchema),
  total: z.number().int().nonnegative(),
  limit: z.number().int().positive(),
  offset: z.number().int().nonnegative(),
});

export type AdminIdentityAssets = {
  profile: {
    id: string;
    full_name: string;
    status: "draft" | "published" | "hidden" | "archived";
  };
  portraits: Array<z.infer<typeof rawPortraitAdminSchema>>;
  resumes: Array<z.infer<typeof rawResumeAdminSchema>>;
  social_links: Array<z.infer<typeof rawSocialLinkAdminSchema>>;
};

export type AdminProjectMedia = z.infer<typeof rawProjectMediaAdminSchema>;
export type AdminRepositoryMetadata = z.infer<typeof rawRepositoryMetadataAdminSchema>;
export type AdminFeaturedProjectOrder = {
  limit: number;
  projects: AdminRecord[];
};

export type AdminSocialLinkInput = {
  platform: string;
  label: string;
  url: string;
  handle?: string | null;
  sort_order: number;
  is_visible: boolean;
};

const rawHomepageSectionSchema = rawRecordSchema.extend({
  section_type: z.string(),
  title: z.string().nullable(),
  position: z.number().int().nonnegative(),
  enabled: z.boolean(),
  variant: z.string(),
  animation_variant: z.string().nullable(),
  data_limit: z.number().int().positive().nullable(),
  show_cta: z.boolean(),
  theme: z.string().nullable(),
  feature_key: z.string().nullable().optional(),
  configuration: z.record(z.string(), z.unknown()),
  status: z.enum(["draft", "published", "hidden", "archived"]),
  is_visible: z.boolean(),
});
const rawHomepageSectionPageSchema = z.object({
  items: z.array(rawHomepageSectionSchema),
  total: z.number().int().nonnegative(),
  limit: z.number().int().positive(),
  offset: z.number().int().nonnegative(),
});

const rawFeatureSettingSchema = rawRecordSchema.extend({
  key: z.string(),
  description: z.string().nullable(),
  enabled: z.boolean(),
  configuration: z.record(z.string(), z.unknown()),
  archived_at: z.string().nullable(),
});
const rawFeatureSettingPageSchema = z.object({
  items: z.array(rawFeatureSettingSchema),
  total: z.number().int().nonnegative(),
  limit: z.number().int().positive(),
  offset: z.number().int().nonnegative(),
});

type RawRecord = z.infer<typeof rawRecordSchema>;

type LiveResourceRoute = {
  scope: "identity" | "portfolio" | "content" | "engagement";
  segment: string;
};

const LIVE_RESOURCE_ROUTES: Partial<Record<AdminResource, LiveResourceRoute>> =
  {
    profile: { scope: "identity", segment: "profiles" },
    categories: { scope: "portfolio", segment: "categories" },
    sectors: { scope: "portfolio", segment: "sectors" },
    skills: { scope: "portfolio", segment: "skills" },
    experience: { scope: "portfolio", segment: "experiences" },
    education: { scope: "portfolio", segment: "education" },
    certifications: { scope: "portfolio", segment: "certifications" },
    projects: { scope: "portfolio", segment: "projects" },
    "project-media": { scope: "portfolio", segment: "project-media" },
    metrics: { scope: "portfolio", segment: "metrics" },
    testimonials: { scope: "portfolio", segment: "testimonials" },
    articles: { scope: "content", segment: "articles" },
    "open-source": { scope: "portfolio", segment: "projects" },
    media: { scope: "content", segment: "media" },
    navigation: { scope: "content", segment: "navigation" },
    sponsorship: { scope: "engagement", segment: "sponsorship" },
    "contact-submissions": {
      scope: "engagement",
      segment: "contact-submissions",
    },
  };

const statusSchema = z.enum(["draft", "published", "hidden", "archived"]);

function titleCase(value: string): string {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function routeFor(resource: AdminResource): LiveResourceRoute {
  const route = LIVE_RESOURCE_ROUTES[resource];
  if (!route) {
    throw new ApiError({
      message: `The ${resource} workspace is not exposed by the current FastAPI admin contract.`,
      status: 501,
      code: "admin_capability_unavailable",
    });
  }
  return route;
}

function routePath(route: LiveResourceRoute): string {
  return `/admin/${route.scope}/${route.segment}`;
}

function rawValue(record: RawRecord, key: string): unknown {
  return (record as Record<string, unknown>)[key];
}

function recordLabel(resource: AdminResource, record: RawRecord): string {
  const pick = (...keys: string[]) => {
    for (const key of keys) {
      const value = rawValue(record, key);
      if (typeof value === "string" && value.trim()) return value;
    }
    return undefined;
  };
  if (resource === "experience") {
    const role = pick("role");
    const organization = pick("organization");
    if (role && organization) return `${role} · ${organization}`;
  }
  if (resource === "education") {
    const credential = pick("credential");
    const institution = pick("institution");
    if (credential && institution) return `${credential} · ${institution}`;
  }
  if (resource === "testimonials") {
    const attribution = pick("attribution_name");
    if (attribution) return `Testimonial · ${attribution}`;
  }
  if (resource === "contact-submissions") {
    const subject = pick("subject");
    const email = pick("email");
    if (subject && email) return `${subject} · ${email}`;
    if (email) return `Contact · ${email}`;
  }
  return (
    pick(
      "full_name",
      "title",
      "name",
      "label",
      "version_label",
      "original_filename",
      "alt_text",
      "caption",
      "slug",
    ) ?? `${titleCase(resource)} record`
  );
}

function toAdminRecord(
  resource: AdminResource,
  record: RawRecord,
): AdminRecord {
  let status = statusSchema.safeParse(rawValue(record, "status"));
  if (resource === "sponsorship") {
    const sponsorshipStatus =
      rawValue(record, "is_archived") === true
        ? "archived"
        : rawValue(record, "is_published") === true
          ? "published"
          : "draft";
    status = statusSchema.safeParse(sponsorshipStatus);
  }
  const slug = rawValue(record, "slug");
  const order = rawValue(record, "sort_order") ?? rawValue(record, "position");
  const data = { ...(record as Record<string, unknown>) };
  if (resource === "metrics" || resource === "testimonials") {
    const evidence = rawValue(record, "evidence");
    if (typeof evidence === "object" && evidence !== null) {
      const source = evidence as Record<string, unknown>;
      for (const key of [
        "kind",
        "visibility",
        "reference_url",
        "managed_media_id",
        "reference_text",
        "public_label",
        "provenance",
        "captured_at",
        "reviewer_note",
      ]) {
        data[`evidence_${key}`] = source[key] ?? null;
      }
      data.evidence_managed_media = source.managed_media ?? null;
    }
  }
  for (const [relation, target] of [
    ["skills", "skill_ids"],
    ["sectors", "sector_ids"],
    ["projects", "project_ids"],
  ] as const) {
    const values = rawValue(record, relation);
    if (Array.isArray(values)) {
      data[target] = values.flatMap((value) => {
        if (typeof value !== "object" || value === null || !("id" in value))
          return [];
        const id = (value as { id?: unknown }).id;
        return typeof id === "string" ? [id] : [];
      });
    }
  }
  return adminRecordSchema.parse({
    id: record.id,
    label: recordLabel(resource, record),
    slug: typeof slug === "string" ? slug : undefined,
    status: status.success ? status.data : undefined,
    order: typeof order === "number" ? order : undefined,
    updated_at: record.updated_at,
    data,
  });
}

function pageFromRecords(
  records: AdminRecord[],
  page: number,
  pageSize: number,
  total = records.length,
) {
  return adminListResponseSchema.parse({
    items: records,
    page_info: {
      page,
      page_size: pageSize,
      total,
      total_pages: total === 0 ? 0 : Math.ceil(total / pageSize),
    },
  });
}

function mutationResult(record: RawRecord, message: string) {
  return mutationResponseSchema.parse({
    id: record.id,
    message,
    updated_at: record.updated_at,
  });
}

const EVIDENCE_FIELDS = [
  "kind",
  "visibility",
  "reference_url",
  "managed_media_id",
  "reference_text",
  "public_label",
  "provenance",
  "captured_at",
  "reviewer_note",
] as const;

function evidencePayload(payload: Record<string, unknown>): void {
  const values = Object.fromEntries(
    EVIDENCE_FIELDS.map((key) => [key, payload[`evidence_${key}`] ?? null]),
  ) as Record<(typeof EVIDENCE_FIELDS)[number], unknown>;
  const touched = EVIDENCE_FIELDS.some((key) => `evidence_${key}` in payload);
  for (const key of EVIDENCE_FIELDS) delete payload[`evidence_${key}`];
  if (!touched) return;

  const populated = Object.values(values).some(
    (value) => value !== null && value !== undefined && value !== "",
  );
  if (!populated) {
    payload.evidence = null;
    return;
  }
  const kind = z
    .enum(["public_url", "managed_media", "document_reference"])
    .parse(values.kind);
  const visibility = z
    .enum(["private_review", "public"])
    .default("private_review")
    .parse(values.visibility ?? undefined);
  const provenance = z.string().trim().min(3).max(500).parse(values.provenance);
  const capturedAt = z.string().date().parse(values.captured_at);
  const locator = {
    reference_url: kind === "public_url" ? values.reference_url : null,
    managed_media_id: kind === "managed_media" ? values.managed_media_id : null,
    reference_text: kind === "document_reference" ? values.reference_text : null,
  };
  payload.evidence = {
    kind,
    visibility,
    ...locator,
    public_label: values.public_label || null,
    provenance,
    captured_at: capturedAt,
    reviewer_note: values.reviewer_note || null,
  };
}

function mutationPayload(
  resource: AdminResource,
  data: Record<string, unknown>,
): Record<string, unknown> {
  const payload = { ...data };
  for (const key of [
    "id",
    "created_at",
    "updated_at",
    "published_at",
    "archived_at",
    "status",
    "approved_at",
    "approved_by_admin_id",
    "is_approved",
    "current",
    "is_current",
  ])
    delete payload[key];
  if (resource === "metrics" || resource === "testimonials") evidencePayload(payload);
  if (resource === "open-source") payload.is_open_source = true;
  return payload;
}

function frontendSection(
  value: z.infer<typeof rawHomepageSectionSchema>,
): HomepageSection {
  const kind = homepageSectionKindSchema.parse(value.section_type);
  const theme =
    value.theme === "contrast" ||
    value.theme === "muted" ||
    value.theme === "accent"
      ? value.theme
      : "default";
  return homepageSectionSchema.parse({
    id: value.id,
    kind,
    enabled: value.enabled && value.status !== "archived" && value.is_visible,
    order: value.position,
    variant: value.variant,
    animation_variant: value.animation_variant ?? "reveal",
    data_limit: value.data_limit ?? undefined,
    cta_visible: value.show_cta,
    theme,
    feature_key: value.feature_key ?? undefined,
    custom_heading: value.title ?? undefined,
    configuration: value.configuration,
  });
}

function backendSection(value: HomepageSection, position: number) {
  return {
    ...(value.id.startsWith("new:") ? {} : { id: value.id }),
    section_type: value.kind,
    title: value.custom_heading ?? null,
    position,
    enabled: value.enabled,
    variant: value.variant,
    animation_variant: value.animation_variant,
    data_limit: value.data_limit ?? null,
    show_cta: value.cta_visible,
    theme: value.theme,
    feature_key: value.feature_key ?? null,
    configuration: value.configuration,
    is_visible: true,
    noindex: false,
  };
}

export type AdminListQuery = {
  page?: number;
  pageSize?: number;
  search?: string;
  status?: string;
  approved?: boolean;
};

export class AdminApi {
  constructor(private readonly http: HttpClient) {}

  async login(input: AdminLoginRequest) {
    const response = await this.http.post(
      "/auth/login",
      adminLoginRequestSchema.parse(input),
      rawLoginResponseSchema,
    );
    return adminSessionSchema.parse({
      authenticated: true,
      user: response.admin,
      csrf_token: response.csrf_token,
    });
  }

  async logout() {
    await this.http.post("/auth/logout", {}, rawMessageSchema);
    return { success: true as const };
  }

  async getSession() {
    const user = await this.http.get("/auth/me", rawAdminUserSchema, {
      cache: "no-store",
    });
    return adminSessionSchema.parse({ authenticated: true, user });
  }

  async getDashboard() {
    const resources = [
      "projects",
      "articles",
      "media",
      "metrics",
      "testimonials",
      "sponsorship",
      "contact-submissions",
    ] as const;
    const draftResources = resources.filter(
      (resource) => resource !== "contact-submissions",
    );
    const [pages, draftPages, approvalPages, unreadPage] = await Promise.all([
      Promise.all(
        resources.map((resource) =>
          this.list(resource, { page: 1, pageSize: 8 }),
        ),
      ),
      Promise.all(
        draftResources.map((resource) =>
          this.list(resource, { page: 1, pageSize: 1, status: "draft" }),
        ),
      ),
      Promise.all(
        (["metrics", "testimonials"] as const).map((resource) =>
          this.list(resource, { page: 1, pageSize: 1, approved: false }),
        ),
      ),
      this.list("contact-submissions", {
        page: 1,
        pageSize: 1,
        status: "new",
      }),
    ]);
    const counts = Object.fromEntries(
      resources.map((resource, index) => [
        resource,
        pages[index]?.page_info.total ?? 0,
      ]),
    );
    const records = pages.flatMap((page) => page.items);
    return dashboardSummarySchema.parse({
      counts,
      drafts: draftPages.reduce(
        (total, page) => total + page.page_info.total,
        0,
      ),
      pending_approvals: approvalPages.reduce(
        (total, page) => total + page.page_info.total,
        0,
      ),
      unread_contacts: unreadPage.page_info.total,
      recent_activity: [...records]
        .sort((left, right) => right.updated_at.localeCompare(left.updated_at))
        .slice(0, 8)
        .map((record) => ({
          id: record.id,
          action: record.status ?? "updated",
          resource: record.slug ?? "content",
          label: record.label,
          at: record.updated_at,
        })),
    });
  }

  async list(resource: AdminResource, query: AdminListQuery = {}) {
    const safeResource = adminResourceSchema.parse(resource);
    const page = Math.max(1, query.page ?? 1);
    const pageSize = Math.min(100, Math.max(1, query.pageSize ?? 25));

    if (safeResource === "resumes") {
      const profiles = await this.http.get(
        "/admin/identity/profiles?limit=1&offset=0",
        rawRecordListSchema,
        { cache: "no-store" },
      );
      const profile = profiles.items[0];
      if (!profile) return pageFromRecords([], page, pageSize, 0);
      const versions = await this.http.get(
        `/admin/identity/profiles/${encodeURIComponent(profile.id)}/resume-versions`,
        rawRecordArraySchema,
        { cache: "no-store" },
      );
      const records = versions.map((item) => toAdminRecord(safeResource, item));
      return pageFromRecords(
        records.slice((page - 1) * pageSize, page * pageSize),
        page,
        pageSize,
        records.length,
      );
    }

    const route = routeFor(safeResource);
    const suffix = queryString({
      limit: pageSize,
      offset: (page - 1) * pageSize,
      search: query.search?.trim(),
      status: query.status && query.status !== "all" ? query.status : undefined,
      open_source: safeResource === "open-source" ? true : undefined,
      approved: query.approved,
    });
    const response = await this.http.get(
      `${routePath(route)}${suffix}`,
      rawRecordListSchema,
      { cache: "no-store" },
    );
    const records = response.items.map((item) =>
      toAdminRecord(safeResource, item),
    );
    return pageFromRecords(records, page, pageSize, response.total);
  }

  async get(resource: AdminResource, id: string) {
    const safeResource = adminResourceSchema.parse(resource);
    const route = routeFor(safeResource);
    if (
      safeResource === "profile" ||
      safeResource === "projects" ||
      safeResource === "open-source"
    ) {
      const record = await this.http.get(
        `${routePath(route)}/${encodeURIComponent(id)}`,
        rawRecordSchema,
        { cache: "no-store" },
      );
      return toAdminRecord(safeResource, record);
    }
    const page = await this.list(safeResource, { page: 1, pageSize: 100 });
    const record = page.items.find((item) => item.id === id);
    if (!record)
      throw new ApiError({
        message: "The managed record was not found.",
        status: 404,
        code: "not_found",
      });
    return record;
  }

  async getFeaturedProjectOrder(): Promise<AdminFeaturedProjectOrder> {
    const result = await this.http.get(
      "/admin/portfolio/projects/featured-order",
      rawFeaturedProjectOrderSchema,
      { cache: "no-store" },
    );
    return {
      limit: result.limit,
      projects: result.projects.map((project) => toAdminRecord("projects", project)),
    };
  }

  async replaceFeaturedProjectOrder(projectIds: string[]): Promise<AdminRecord[]> {
    const result = await this.http.put(
      "/admin/portfolio/projects/featured-order",
      { project_ids: projectIds },
      z.array(rawRecordSchema),
    );
    return result.map((project) => toAdminRecord("projects", project));
  }

  async create(resource: AdminResource, data: Record<string, unknown>) {
    const safeResource = adminResourceSchema.parse(resource);
    const route = routeFor(safeResource);
    const requestedApproval = data.is_approved === true;
    const record = await this.http.post(
      routePath(route),
      mutationPayload(safeResource, data),
      rawRecordSchema,
    );
    if (
      requestedApproval &&
      (safeResource === "metrics" || safeResource === "testimonials")
    ) {
      const approved = await this.http.put(
        `${routePath(route)}/${encodeURIComponent(record.id)}/approval`,
        {},
        rawRecordSchema,
      );
      return toAdminRecord(safeResource, approved);
    }
    return toAdminRecord(safeResource, record);
  }

  async update(
    resource: AdminResource,
    id: string,
    data: Record<string, unknown>,
  ) {
    const safeResource = adminResourceSchema.parse(resource);
    const route = routeFor(safeResource);
    if (safeResource === "contact-submissions") {
      const status = z
        .enum(["new", "read", "closed", "spam"])
        .parse(data.status);
      const record = await this.http.patch(
        `${routePath(route)}/${encodeURIComponent(id)}/status`,
        { status },
        rawRecordSchema,
      );
      return toAdminRecord(safeResource, record);
    }
    const requestedApproval =
      typeof data.is_approved === "boolean" ? data.is_approved : undefined;
    let record = await this.http.patch(
      `${routePath(route)}/${encodeURIComponent(id)}`,
      mutationPayload(safeResource, data),
      rawRecordSchema,
    );
    if (
      requestedApproval !== undefined &&
      (safeResource === "metrics" || safeResource === "testimonials")
    ) {
      const approvalPath = `${routePath(route)}/${encodeURIComponent(id)}/approval`;
      record = requestedApproval
        ? await this.http.put(approvalPath, {}, rawRecordSchema)
        : await this.http.delete(approvalPath, rawRecordSchema);
    }
    return toAdminRecord(safeResource, record);
  }

  async remove(resource: AdminResource, id: string) {
    const safeResource = adminResourceSchema.parse(resource);
    if (safeResource === "resumes") {
      const record = await this.http.delete(
        `/admin/identity/resume-versions/${encodeURIComponent(id)}`,
        rawRecordSchema,
      );
      return mutationResult(record, "Résumé version archived.");
    }
    const route = routeFor(safeResource);
    if (safeResource === "sponsorship") {
      const record = await this.http.delete(
        `${routePath(route)}/${encodeURIComponent(id)}`,
        rawRecordSchema,
      );
      return mutationResult(record, "Sponsorship option archived.");
    }
    const record = await this.http.put(
      `${routePath(route)}/${encodeURIComponent(id)}/status`,
      { status: "archived" },
      rawRecordSchema,
    );
    return mutationResult(record, "Record archived.");
  }

  async publish(
    resource: AdminResource,
    id: string,
    status: "draft" | "published" | "hidden" | "archived",
  ) {
    const safeResource = adminResourceSchema.parse(resource);
    if (safeResource === "resumes") {
      const record =
        status === "published"
          ? await this.http.put(
              `/admin/identity/resume-versions/${encodeURIComponent(id)}/publish-current`,
              {},
              rawRecordSchema,
            )
          : await this.http.delete(
              `/admin/identity/resume-versions/${encodeURIComponent(id)}`,
              rawRecordSchema,
            );
      return mutationResult(
        record,
        status === "published"
          ? "Résumé published as current."
          : "Résumé archived.",
      );
    }
    const route = routeFor(safeResource);
    if (safeResource === "sponsorship") {
      const record =
        status === "archived"
          ? await this.http.delete(
              `${routePath(route)}/${encodeURIComponent(id)}`,
              rawRecordSchema,
            )
          : await this.http.patch(
              `${routePath(route)}/${encodeURIComponent(id)}`,
              { is_published: status === "published" },
              rawRecordSchema,
            );
      return mutationResult(record, `Sponsorship state changed to ${status}.`);
    }
    const record = await this.http.put(
      `${routePath(route)}/${encodeURIComponent(id)}/status`,
      { status },
      rawRecordSchema,
    );
    return mutationResult(record, `Publication state changed to ${status}.`);
  }

  async getHomepageSections() {
    const response = await this.http.get(
      "/admin/content/sections?limit=100&offset=0",
      rawHomepageSectionPageSchema,
      { cache: "no-store" },
    );
    return homepageSectionSchema.array().parse(
      response.items
        .filter((item) => item.status !== "archived")
        .map(frontendSection)
        .sort((left, right) => left.order - right.order),
    );
  }

  async saveHomepageSections(sections: HomepageSection[]) {
    const validated = homepageSectionSchema.array().parse(sections);
    const response = await this.http.put(
      "/admin/content/sections/composition",
      { sections: validated.map(backendSection) },
      rawHomepageSectionSchema.array(),
    );
    return homepageSectionSchema.array().parse(response.map(frontendSection));
  }

  async getFeatureSettings() {
    const response = await this.http.get(
      "/admin/content/features?limit=100&offset=0",
      rawFeatureSettingPageSchema,
      { cache: "no-store" },
    );
    return featureSettingSchema.array().parse(
      response.items
        .filter((item) => item.archived_at === null)
        .map((item) => ({
          key: item.key,
          label: titleCase(item.key),
          description: item.description ?? undefined,
          enabled: item.enabled,
          public: true,
        })),
    );
  }

  async updateFeatureSetting(key: string, enabled: boolean) {
    const response = await this.http.get(
      "/admin/content/features?limit=100&offset=0",
      rawFeatureSettingPageSchema,
      { cache: "no-store" },
    );
    const existing = response.items.find(
      (item) => item.key === key && item.archived_at === null,
    );
    const updated = await this.http.put(
      "/admin/content/features",
      {
        key,
        enabled,
        description: existing?.description ?? null,
        configuration: existing?.configuration ?? {},
      },
      rawFeatureSettingSchema,
    );
    return featureSettingSchema.parse({
      key: updated.key,
      label: titleCase(updated.key),
      description: updated.description ?? undefined,
      enabled: updated.enabled,
      public: true,
    });
  }

  async getSiteSettings() {
    return this.http.get(
      "/public/site-presentation",
      siteSettingsSchema,
      { cache: "no-store" },
    );
  }

  async updateSiteSettings(input: SiteSettings) {
    const validated = siteSettingsSchema.parse(input);
    await this.http.put(
      "/admin/content/features",
      {
        key: "site_settings",
        enabled: true,
        description: "Public discovery identity and presentation defaults.",
        configuration: validated,
      },
      rawFeatureSettingSchema,
    );
    return validated;
  }

  async getAssistantSettings() {
    const response = await this.http.get(
      "/admin/content/features?limit=100&offset=0",
      rawFeatureSettingPageSchema,
      { cache: "no-store" },
    );
    const settings = response.items.find(
      (item) => item.key === "assistant" && item.archived_at === null,
    );
    const configured = assistantSettingsSchema.safeParse({
      ...settings?.configuration,
      enabled: settings?.enabled,
    });
    if (configured.success) return configured.data;

    const homepage = await this.http.get(
      "/public/homepage",
      rawHomepageSchema,
      { cache: "no-store" },
    );
    return assistantSettingsSchema.parse({
      enabled: homepage.features.assistant ?? false,
      greeting:
        "Ask about published projects, experience, skills, and writing.",
      suggested_questions: [
        "Which projects best demonstrate production AI work?",
        "What technologies appear across the selected projects?",
        "What experience is most relevant to platform engineering?",
      ],
      disclaimer:
        "Answers use published portfolio evidence and may ask you to narrow the question.",
      max_question_length: 600,
    });
  }

  async updateAssistantSettings(input: AssistantSettings) {
    const validated = assistantSettingsSchema.parse(input);
    const { enabled, ...configuration } = validated;
    await this.http.put(
      "/admin/content/features",
      {
        key: "assistant",
        enabled,
        description: "Public portfolio assistant experience settings.",
        configuration,
      },
      rawFeatureSettingSchema,
    );
    return validated;
  }

  async getIdentityAssets(): Promise<AdminIdentityAssets> {
    const profiles = await this.http.get(
      "/admin/identity/profiles?limit=1&offset=0",
      rawProfileAssetsPageSchema,
      { cache: "no-store" },
    );
    const profile = profiles.items[0];
    if (!profile) {
      throw new ApiError({
        message: "Create a canonical profile before uploading identity assets.",
        status: 409,
        code: "profile_required",
      });
    }
    const resumes = await this.http.get(
      `/admin/identity/profiles/${encodeURIComponent(profile.id)}/resume-versions`,
      z.array(rawResumeAdminSchema),
      { cache: "no-store" },
    );
    return {
      profile: {
        id: profile.id,
        full_name: profile.full_name,
        status: profile.status,
      },
      portraits: profile.portraits.sort(
        (left, right) => left.sort_order - right.sort_order,
      ),
      resumes: resumes.sort((left, right) =>
        right.updated_at.localeCompare(left.updated_at),
      ),
      social_links: profile.social_links.sort(
        (left, right) => left.sort_order - right.sort_order,
      ),
    };
  }

  uploadPortrait(
    file: File,
    input: {
      profileId: string;
      altText: string;
      makePrimary: boolean;
      sortOrder?: number;
    },
  ) {
    const form = new FormData();
    form.set("file", file);
    form.set("profile_id", input.profileId);
    form.set("alt_text", input.altText);
    form.set("make_primary", String(input.makePrimary));
    form.set("sort_order", String(input.sortOrder ?? 0));
    return this.http.upload(
      "/admin/identity/portraits",
      form,
      rawPortraitAdminSchema,
    );
  }

  uploadProjectMedia(
    file: File,
    input: {
      projectId: string;
      altText: string;
      isDecorative: boolean;
      caption?: string;
      sortOrder?: number;
    },
  ) {
    const form = new FormData();
    form.set("file", file);
    form.set("project_id", input.projectId);
    form.set("alt_text", input.altText);
    form.set("is_decorative", String(input.isDecorative));
    if (input.caption) form.set("caption", input.caption);
    form.set("sort_order", String(input.sortOrder ?? 0));
    form.set("is_visible", "true");
    return this.http.upload(
      "/admin/portfolio/project-media/upload",
      form,
      rawProjectMediaAdminSchema,
    );
  }

  archiveProjectMedia(mediaId: string) {
    return this.http.delete(
      `/admin/portfolio/project-media/${encodeURIComponent(mediaId)}`,
      rawProjectMediaAdminSchema,
    );
  }

  refreshRepositoryMetadata(projectId: string, force = false) {
    return this.http.post(
      `/admin/portfolio/projects/${encodeURIComponent(projectId)}/repository-metadata/refresh${force ? "?force=true" : ""}`,
      {},
      rawRepositoryMetadataAdminSchema,
    );
  }

  setPrimaryPortrait(id: string) {
    return this.http.put(
      `/admin/identity/portraits/${encodeURIComponent(id)}/primary`,
      {},
      rawPortraitAdminSchema,
    );
  }

  archivePortrait(id: string) {
    return this.http.delete(
      `/admin/identity/portraits/${encodeURIComponent(id)}`,
      rawPortraitAdminSchema,
    );
  }

  uploadResume(
    file: File,
    input: {
      profileId: string;
      versionLabel: string;
      effectiveDate?: string;
      downloadName: string;
    },
  ) {
    const form = new FormData();
    form.set("file", file);
    form.set("profile_id", input.profileId);
    form.set("version_label", input.versionLabel);
    form.set("download_name", input.downloadName);
    if (input.effectiveDate) form.set("effective_date", input.effectiveDate);
    return this.http.upload(
      "/admin/identity/resume-versions",
      form,
      rawResumeAdminSchema,
    );
  }

  publishCurrentResume(id: string) {
    return this.http.put(
      `/admin/identity/resume-versions/${encodeURIComponent(id)}/publish-current`,
      {},
      rawResumeAdminSchema,
    );
  }

  archiveResume(id: string) {
    return this.http.delete(
      `/admin/identity/resume-versions/${encodeURIComponent(id)}`,
      rawResumeAdminSchema,
    );
  }

  createSocialLink(profileId: string, input: AdminSocialLinkInput) {
    return this.http.post(
      "/admin/identity/social-links",
      { ...input, profile_id: profileId },
      rawSocialLinkAdminSchema,
    );
  }

  updateSocialLink(id: string, input: AdminSocialLinkInput) {
    return this.http.patch(
      `/admin/identity/social-links/${encodeURIComponent(id)}`,
      input,
      rawSocialLinkAdminSchema,
    );
  }

  async deleteSocialLink(id: string) {
    await this.http.delete(
      `/admin/identity/social-links/${encodeURIComponent(id)}`,
      rawMessageSchema,
    );
    return { success: true as const };
  }

  async uploadMedia(
    file: File,
    metadata: { alt: string; caption?: string; isDecorative: boolean },
  ) {
    const form = new FormData();
    form.set("file", file);
    form.set("alt_text", metadata.alt);
    form.set("is_decorative", String(metadata.isDecorative));
    if (metadata.caption) form.set("caption", metadata.caption);
    const record = await this.http.upload(
      "/admin/content/media",
      form,
      rawRecordSchema,
    );
    return toAdminRecord("media", record);
  }
}
