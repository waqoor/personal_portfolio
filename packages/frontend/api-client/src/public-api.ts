import { z } from "zod";

import type { ApiRequestOptions, HttpClient } from "./client";
import { ApiError, queryString } from "./client";
import {
  mapArticleDetail,
  mapArticlesPage,
  mapHomePage,
  mapOpenSourcePage,
  mapProfilePage,
  mapProjectDetail,
  mapProjectsPage,
  mapResume,
  mapSectorDetail,
  mapSectorsPage,
  mapSkill,
  mapSiteShell,
  mapSponsorship,
  rawArticleSchema,
  rawArticleSummarySchema,
  rawAssistantAnswerSchema,
  rawCategorySchema,
  rawCertificationSchema,
  rawContactReceiptSchema,
  rawEducationSchema,
  rawExperienceSchema,
  rawHomepageSchema,
  rawProfileSchema,
  rawProjectSchema,
  rawProjectSummarySchema,
  rawResumeSchema,
  rawSectorSchema,
  rawSkillSchema,
  rawSiteShellSchema,
  rawSponsorshipSchema,
} from "./canonical-public";
import {
  assistantRequestSchema,
  assistantResponseSchema,
  contactOptionsSchema,
  contactRequestSchema,
  contactResponseSchema,
  discoveryPageSchema,
  machineTextSchema,
  resumeAssetSchema,
  sitePresentationSchema,
  sitemapSchema,
  type AssistantRequest,
  type ContactRequest,
} from "./schemas";

const rawProjectsPageSchema = z.object({
  items: rawProjectSummarySchema.array(),
  total: z.number().int().nonnegative(),
  limit: z.number().int().positive(),
  offset: z.number().int().nonnegative(),
});
const rawCategoriesSchema = rawCategorySchema.array();
const rawSectorsSchema = rawSectorSchema.array();
const rawArticlesPageSchema = z.object({
  items: rawArticleSummarySchema.array(),
  total: z.number().int().nonnegative(),
  limit: z.number().int().positive(),
  offset: z.number().int().nonnegative(),
  topics: z.array(z.string()),
});
const rawSectorDetailSchema = z.object({
  sector: rawSectorSchema,
  projects: rawProjectSummarySchema.array(),
  total: z.number().int().nonnegative(),
});
const liveContent: ApiRequestOptions = {
  next: { revalidate: 60, tags: ["portfolio-public"] },
};

export type PublicListQuery = {
  page?: number | undefined;
  pageSize?: number | undefined;
  category?: string | undefined;
  sector?: string | undefined;
  topic?: string | undefined;
  search?: string | undefined;
};

export class PublicApi {
  constructor(private readonly http: HttpClient) {}

  async getSiteShell() {
    const shell = await this.http.get("/public/site-shell", rawSiteShellSchema, liveContent);
    return mapSiteShell(shell);
  }

  async getHomePage() {
    const [homepage, sponsorship] = await Promise.all([
      this.http.get("/public/homepage", rawHomepageSchema, liveContent),
      this.http.get("/sponsorship", rawSponsorshipSchema, liveContent),
    ]);
    return mapHomePage(homepage, sponsorship);
  }

  async getProfilePage() {
    const [profile, presentation, resume, experience, education, certifications] =
      await Promise.all([
        this.http.get("/public/profile", rawProfileSchema, liveContent),
        this.http.get("/public/site-presentation", sitePresentationSchema, liveContent),
        this.getOptionalResume(),
        this.http.get(
          "/public/experiences?limit=100",
          rawExperienceSchema.array(),
          liveContent,
        ),
        this.http.get(
          "/public/education?limit=100",
          rawEducationSchema.array(),
          liveContent,
        ),
        this.http.get(
          "/public/certifications?limit=100",
          rawCertificationSchema.array(),
          liveContent,
        ),
      ]);
    return mapProfilePage(
      profile,
      resume,
      experience,
      education,
      certifications,
      presentation,
    );
  }

  async getSkills() {
    const skills = await this.http.get(
      "/public/skills?limit=100",
      rawSkillSchema.array(),
      liveContent,
    );
    return skills.map((skill) => mapSkill(skill));
  }

  private async getOptionalResume() {
    try {
      return await this.http.get("/public/resume/meta", rawResumeSchema, liveContent);
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 404) return null;
      throw caught;
    }
  }

  async getResume() {
    const resume = await this.http.get("/public/resume/meta", rawResumeSchema, {
      cache: "no-store",
    });
    return resumeAssetSchema.parse(mapResume(resume));
  }

  async getProjects(query: PublicListQuery = {}) {
    const page = Math.max(1, query.page ?? 1);
    const pageSize = Math.min(100, Math.max(1, query.pageSize ?? 12));
    const category =
      query.category && query.category !== "all" ? query.category : undefined;
    const sector =
      query.sector && query.sector !== "all" ? query.sector : undefined;
    const [projects, categories, sectors, presentation] = await Promise.all([
      this.http.get(
        `/public/projects${queryString({
          limit: pageSize,
          offset: (page - 1) * pageSize,
          category,
          sector,
          search: query.search?.trim(),
        })}`,
        rawProjectsPageSchema,
        liveContent,
      ),
      this.http.get(
        "/public/categories?limit=100",
        rawCategoriesSchema,
        liveContent,
      ),
      this.http.get("/public/sectors?limit=100", rawSectorsSchema, liveContent),
      this.http.get("/public/site-presentation", sitePresentationSchema, liveContent),
    ]);
    return mapProjectsPage(
      projects.items,
      categories,
      sectors,
      page,
      pageSize,
      projects.total,
      presentation,
    );
  }

  async getProject(slug: string) {
    const project = await this.http.get(
      `/public/projects/${encodeURIComponent(slug)}`,
      rawProjectSchema,
      liveContent,
    );
    return mapProjectDetail(project);
  }

  async getSectors() {
    const [sectors, presentation] = await Promise.all([
      this.http.get("/public/sectors?limit=100", rawSectorsSchema, liveContent),
      this.http.get("/public/site-presentation", sitePresentationSchema, liveContent),
    ]);
    return mapSectorsPage(sectors, presentation);
  }

  async getSector(slug: string) {
    const detail = await this.http.get(
      `/public/sectors/${encodeURIComponent(slug)}`,
      rawSectorDetailSchema,
      liveContent,
    );
    return mapSectorDetail(detail.sector, detail.projects);
  }

  async getArticles(query: PublicListQuery = {}) {
    const page = Math.max(1, query.page ?? 1);
    const pageSize = Math.min(100, Math.max(1, query.pageSize ?? 10));
    const [articles, presentation] = await Promise.all([
      this.http.get(
        `/public/articles${queryString({
          limit: pageSize,
          offset: (page - 1) * pageSize,
          topic: query.topic && query.topic !== "all" ? query.topic : undefined,
          search: query.search?.trim(),
        })}`,
        rawArticlesPageSchema,
        liveContent,
      ),
      this.http.get("/public/site-presentation", sitePresentationSchema, liveContent),
    ]);
    return mapArticlesPage(
      articles.items,
      page,
      pageSize,
      articles.total,
      articles.topics,
      presentation,
    );
  }

  async getArticle(slug: string) {
    const article = await this.http.get(
      `/public/articles/${encodeURIComponent(slug)}`,
      rawArticleSchema,
      liveContent,
    );
    return mapArticleDetail(article);
  }

  async getOpenSource() {
    const [projects, sponsorship, presentation] = await Promise.all([
      this.http.get(
        "/public/projects?limit=100&offset=0&open_source=true",
        rawProjectsPageSchema,
        liveContent,
      ),
      this.http.get("/sponsorship", rawSponsorshipSchema, liveContent),
      this.http.get("/public/site-presentation", sitePresentationSchema, liveContent),
    ]);
    return mapOpenSourcePage(projects.items, sponsorship, presentation);
  }

  async getSponsorship() {
    const [sponsorship, presentation] = await Promise.all([
      this.http.get("/sponsorship", rawSponsorshipSchema, liveContent),
      this.http.get("/public/site-presentation", sitePresentationSchema, liveContent),
    ]);
    return mapSponsorship(sponsorship, presentation);
  }

  getContactOptions() {
    return this.http.get("/contact/options", contactOptionsSchema, liveContent);
  }

  async submitContact(
    input: ContactRequest,
    options: { idempotencyKey: string },
  ) {
    const validated = contactRequestSchema.parse(input);
    const receipt = await this.http.post(
      "/contact",
      {
        name: validated.name,
        email: validated.email,
        category: validated.category_id,
        organization: validated.organization,
        subject: validated.subject,
        message: validated.message,
        website: validated.website,
        consent: validated.consent,
      },
      rawContactReceiptSchema,
      {
        headers: {
          "Idempotency-Key": options.idempotencyKey,
        },
      },
    );
    return contactResponseSchema.parse({
      id: receipt.reference_id,
      status: "received",
      message: receipt.message,
    });
  }

  async askAssistant(input: AssistantRequest) {
    const validated = assistantRequestSchema.parse(input);
    const answer = await this.http.post(
      "/assistant/query",
      { question: validated.question },
      rawAssistantAnswerSchema,
    );
    return assistantResponseSchema.parse({
      answer: answer.answer,
      citations: answer.sources.map((source) => ({
        citation: source.citation,
        title: source.title,
        url: source.canonical_url,
      })),
      confidence: answer.grounded
        ? answer.degraded
          ? "medium"
          : "high"
        : "low",
    });
  }

  getSitemap() {
    return this.http.get("/discovery/sitemap", sitemapSchema, liveContent);
  }

  getDiscoveryPage(path: string) {
    const suffix = queryString({ path });
    return this.http.get(
      `/discovery/page${suffix}`,
      discoveryPageSchema,
      liveContent,
    );
  }

  getRobotsText() {
    return this.http.get("/discovery/robots", machineTextSchema, liveContent);
  }

  getLlmsText() {
    return this.http.get("/discovery/llms", machineTextSchema, liveContent);
  }
}
