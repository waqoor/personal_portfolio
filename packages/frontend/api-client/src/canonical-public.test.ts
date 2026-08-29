import {
  mapEditorialBlocks,
  mapOpenSourceProject,
  mapProjectDetail,
  mapSiteShell,
  rawHomepageSchema,
  rawProjectSchema,
  rawProjectSummarySchema,
} from "./canonical-public";
import type { HttpClient } from "./client";
import { PublicApi } from "./public-api";

const now = "2026-08-28T10:00:00Z";

function homepage() {
  return rawHomepageSchema.parse({
    profile: null,
    current_resume: null,
    navigation: [
      {
        id: "header-two",
        created_at: now,
        updated_at: now,
        status: "published",
        is_visible: true,
        noindex: false,
        published_at: now,
        archived_at: null,
        label: "Writing",
        href: "/writing",
        location: "header",
        sort_order: 20,
        open_in_new_tab: false,
      },
      {
        id: "footer-one",
        created_at: now,
        updated_at: now,
        status: "published",
        is_visible: true,
        noindex: false,
        published_at: now,
        archived_at: null,
        label: "Repository",
        href: "https://github.com/example",
        location: "footer",
        sort_order: 10,
        open_in_new_tab: true,
      },
      {
        id: "header-one",
        created_at: now,
        updated_at: now,
        status: "published",
        is_visible: true,
        noindex: false,
        published_at: now,
        archived_at: null,
        label: "Projects",
        href: "/projects",
        location: "header",
        sort_order: 10,
        open_in_new_tab: false,
      },
    ],
    features: { assistant: true, contact: true },
    feature_configurations: {
      assistant: {
        greeting: "Ask about published proof.",
        suggested_questions: ["Which implementation is verified?"],
        disclaimer: "Published evidence only.",
        max_question_length: 420,
      },
    },
    site_presentation: {
      site_name: "Portfolio",
      default_title: "Portfolio",
      default_description: "Reviewed public work and writing.",
      locale: "en",
      footer_eyebrow: "Contact",
      footer_heading: "Build something useful.",
      footer_statement: "Source-backed work.",
      about_title: "About",
      about_intro: "A reviewed professional profile.",
      projects_title: "Projects",
      projects_intro: "Selected case studies.",
      writing_title: "Writing",
      writing_intro: "Technical articles.",
      sectors_title: "Sectors",
      sectors_intro: "Areas of work.",
      open_source_title: "Open source",
      open_source_intro: "Reviewed public repositories.",
      sponsorship_title: "Sponsorship",
      sponsorship_description: "Support independent work.",
      sponsorship_principles: ["Transparent scope"],
    },
    sections: [
      {
        section: {
          id: "section-editorial",
          created_at: now,
          updated_at: now,
          status: "published",
          is_visible: true,
          noindex: false,
          published_at: now,
          archived_at: null,
          section_type: "editorial",
          title: "Editorial proof",
          position: 0,
          enabled: true,
          variant: "default",
          animation_variant: "reveal",
          data_limit: null,
          show_cta: true,
          theme: "default",
          feature_key: null,
          configuration: {
            blocks: [
              {
                id: "editorial-proof",
                eyebrow: "Verified",
                title: "Configuration survives",
                body: "The canonical public mapper renders configured editorial blocks.",
              },
            ],
          },
        },
        data: {
          blocks: [
            {
              id: "editorial-proof",
              eyebrow: "Verified",
              title: "Configuration survives",
              body: "The canonical public mapper renders configured editorial blocks.",
            },
          ],
        },
      },
    ],
  });
}

function projectSummary(id: string) {
  return rawProjectSummarySchema.parse({
    id,
    created_at: now,
    updated_at: now,
    status: "published",
    is_visible: true,
    noindex: false,
    published_at: now,
    archived_at: null,
    category_id: null,
    title: `Project ${id}`,
    slug: `project-${id}`,
    summary: `Summary ${id}`,
    role: null,
    start_date: null,
    end_date: null,
    links: [],
    repository_url: null,
    live_url: null,
    is_open_source: false,
    repository_metadata: null,
    nature: "case_study",
    featured_rank: null,
    seo_title: null,
    seo_description: null,
    category: null,
    skills: [],
    sectors: [],
    media: [],
    metrics: [],
  });
}

describe("canonical public configuration", () => {
  it("maps curated editorial section payloads", () => {
    expect(mapEditorialBlocks(homepage())).toEqual([
      expect.objectContaining({
        id: "editorial-proof",
        title: "Configuration survives",
      }),
    ]);
  });

  it("maps public-safe assistant experience settings into the site shell", () => {
    const shell = mapSiteShell(homepage());

    expect(shell.assistant_enabled).toBe(true);
    expect(shell.assistant_settings).toEqual({
      enabled: true,
      greeting: "Ask about published proof.",
      suggested_questions: ["Which implementation is verified?"],
      disclaimer: "Published evidence only.",
      max_question_length: 420,
    });
    expect(shell.contact_enabled).toBe(true);
    expect(shell.header_navigation.map((item) => item.label)).toEqual([
      "Projects",
      "Writing",
    ]);
    expect(shell.footer_navigation).toEqual([
      expect.objectContaining({
        label: "Repository",
        href: "https://github.com/example",
        external: true,
        location: "footer",
      }),
    ]);
  });

  it("loads canonical presentation settings for the standalone sponsorship page", async () => {
    const presentation = homepage().site_presentation;
    const get = vi.fn(async (path: string) => {
      if (path === "/public/site-presentation") return presentation;
      if (path === "/sponsorship") {
        return {
          items: [
            {
              slug: "public-support",
              title: "Provider-owned option title",
              description: "Provider-owned option description.",
              kind: "external",
              cta_label: "Sponsor public work",
              destination_url: "https://example.com/sponsor",
              amount_minor: null,
              currency: null,
              recurrence: null,
              rel: "sponsored nofollow noopener noreferrer",
            },
          ],
        };
      }
      throw new Error(`Unexpected public API path: ${path}`);
    });
    const api = new PublicApi({ get } as unknown as HttpClient);

    const sponsorship = await api.getSponsorship();

    expect(get).toHaveBeenCalledWith(
      "/public/site-presentation",
      expect.anything(),
      expect.anything(),
    );
    expect(sponsorship).toEqual(
      expect.objectContaining({
        title: "Sponsorship",
        description: "Support independent work.",
        principles: ["Transparent scope"],
      }),
    );
  });

  it("maps reviewed repository signals with freshness and never fabricates zeroes", () => {
    const source = rawProjectSummarySchema.parse({
      ...projectSummary("source-project"),
      title: "Source project",
      slug: "source-project",
      summary: "A repository-backed project.",
      repository_url: "https://github.com/example/source-project",
      is_open_source: true,
      nature: "software",
      repository_metadata: {
        provider: "github",
        repository_identity: "example/source-project",
        language: "Python",
        stars: 42,
        forks: 7,
        fetched_at: now,
        freshness: "stale",
      },
    });

    expect(mapOpenSourceProject(source)).toEqual(
      expect.objectContaining({
        language: "Python",
        stars: 42,
        forks: 7,
        metadata_provider: "github",
        repository_identity: "example/source-project",
        metadata_fetched_at: now,
        metadata_freshness: "stale",
      }),
    );

    const unavailable = mapOpenSourceProject({
      ...source,
      repository_metadata: null,
    });
    expect(unavailable.stars).toBeUndefined();
    expect(unavailable.forks).toBeUndefined();
    expect(unavailable.metadata_fetched_at).toBeUndefined();
  });

  it("maps every project story field once, preserves captions, and activates related items", () => {
    const detail = rawProjectSchema.parse({
      ...projectSummary("detail"),
      description: "UNIQUE_DESCRIPTION",
      problem: "UNIQUE_PROBLEM",
      solution: "UNIQUE_SOLUTION",
      architecture: "UNIQUE_ARCHITECTURE",
      features: ["UNIQUE_FEATURE"],
      decisions: ["UNIQUE_DECISION"],
      tradeoffs: ["UNIQUE_TRADEOFF"],
      challenges: ["UNIQUE_CHALLENGE"],
      outcomes: ["UNIQUE_OUTCOME"],
      testimonials: [],
      related_projects: [projectSummary("related-one"), projectSummary("related-two")],
      media: [
        {
          id: "captioned-media",
          created_at: now,
          updated_at: now,
          external_url: "https://cdn.example.com/diagram.png",
          original_filename: "diagram.png",
          media_type: "image/png",
          size_bytes: 1024,
          alt_text: "Architecture diagram",
          is_decorative: false,
          caption: "UNIQUE_CAPTION",
          width: 1200,
          height: 800,
          duration_seconds: null,
          page_count: null,
          sort_order: 0,
          is_visible: true,
        },
      ],
    });
    const mapped = mapProjectDetail(detail);
    const story = JSON.stringify(mapped.sections);

    for (const marker of [
      "UNIQUE_DESCRIPTION",
      "UNIQUE_PROBLEM",
      "UNIQUE_SOLUTION",
      "UNIQUE_ARCHITECTURE",
      "UNIQUE_FEATURE",
      "UNIQUE_DECISION",
      "UNIQUE_TRADEOFF",
      "UNIQUE_CHALLENGE",
      "UNIQUE_OUTCOME",
    ]) {
      expect(story.split(marker)).toHaveLength(2);
    }
    expect(mapped.cover?.caption).toBe("UNIQUE_CAPTION");
    expect(mapped.gallery).toEqual([]);
    expect(mapped.related_projects.map((project) => project.id)).toEqual([
      "related-one",
      "related-two",
    ]);
    expect(
      mapProjectDetail({ ...detail, related_projects: [] }).related_projects,
    ).toEqual([]);
  });
});
