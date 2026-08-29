import { AdminApi } from "./admin-api";
import { HttpClient } from "./client";

const now = "2026-08-27T10:00:00Z";

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

describe("AdminApi engagement integration", () => {
  it("lists private contacts and updates inbox status through the engagement contract", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockImplementation(async (input, init) => {
      const url = String(input);
      if (init?.method === "GET") {
        expect(url).toBe("https://portfolio.example/api/v1/admin/engagement/contact-submissions?limit=25&offset=0");
        return json({
          items: [{
            id: "contact-1",
            name: "Contact Test",
            email: "contact@example.com",
            category: "project",
            subject: "Canonical inquiry",
            message: "A sufficiently long private test message.",
            consent: true,
            status: "new",
            notification_status: "disabled",
            created_at: now,
            updated_at: now,
          }],
          total: 1,
          limit: 25,
          offset: 0,
        });
      }
      expect(url).toBe("https://portfolio.example/api/v1/admin/engagement/contact-submissions/contact-1/status");
      expect(init?.method).toBe("PATCH");
      expect(init?.body).toBe(JSON.stringify({ status: "read" }));
      return json({
        id: "contact-1",
        name: "Contact Test",
        email: "contact@example.com",
        category: "project",
        subject: "Canonical inquiry",
        message: "A sufficiently long private test message.",
        consent: true,
        status: "read",
        notification_status: "disabled",
        created_at: now,
        updated_at: now,
      });
    });
    const api = new AdminApi(new HttpClient({
      baseUrl: "https://portfolio.example/api/v1",
      fetch: fetchMock,
      csrfToken: "csrf-token",
    }));

    const inbox = await api.list("contact-submissions");
    expect(inbox.items[0]?.label).toContain("Canonical inquiry");
    const updated = await api.update("contact-submissions", "contact-1", { status: "read" });
    expect(updated.data.status).toBe("read");
    expect(new Headers(fetchMock.mock.calls[1]?.[1]?.headers).get("x-csrf-token")).toBe("csrf-token");
  });

  it("creates, publishes, and archives sponsorship through one canonical route family", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockImplementation(async (input, init) => {
      const url = String(input);
      expect(url).toMatch(/\/api\/v1\/admin\/engagement\/sponsorship/);
      if (init?.method === "POST") {
        expect(url).toBe("https://portfolio.example/api/v1/admin/engagement/sponsorship");
        return json({
          id: "sponsor-1",
          title: "Sponsor verification",
          is_published: false,
          is_archived: false,
          updated_at: now,
        }, 201);
      }
      if (init?.method === "PATCH") {
        expect(init.body).toBe(JSON.stringify({ is_published: true }));
        return json({
          id: "sponsor-1",
          title: "Sponsor verification",
          is_published: true,
          is_archived: false,
          updated_at: now,
        });
      }
      expect(init?.method).toBe("DELETE");
      return json({
        id: "sponsor-1",
        title: "Sponsor verification",
        is_published: false,
        is_archived: true,
        updated_at: now,
      });
    });
    const api = new AdminApi(new HttpClient({
      baseUrl: "https://portfolio.example/api/v1",
      fetch: fetchMock,
      csrfToken: "csrf-token",
    }));

    await api.create("sponsorship", {
      slug: "sponsor-verification",
      title: "Sponsor verification",
    });
    await api.publish("sponsorship", "sponsor-1", "published");
    await api.remove("sponsorship", "sponsor-1");

    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(fetchMock.mock.calls.map((call) => call[1]?.method)).toEqual(["POST", "PATCH", "DELETE"]);
  });
});

describe("AdminApi canonical CMS integration", () => {
  it("preserves canonical profile publication state for the résumé release gate", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith("/admin/identity/profiles?limit=1&offset=0")) {
        return json({
          items: [{
            id: "profile-1",
            updated_at: now,
            full_name: "Draft Owner",
            status: "draft",
            portraits: [],
            social_links: [],
          }],
          total: 1,
          limit: 1,
          offset: 0,
        });
      }
      expect(url).toBe(
        "https://portfolio.example/api/v1/admin/identity/profiles/profile-1/resume-versions",
      );
      return json([{
        id: "resume-1",
        updated_at: now,
        status: "draft",
        profile_id: "profile-1",
        version_label: "Reviewed draft",
        original_filename: "resume.pdf",
        media_type: "application/pdf",
        size_bytes: 1024,
        effective_date: "2026-08-27",
        is_current: false,
        download_name: "resume.pdf",
      }]);
    });
    const api = new AdminApi(new HttpClient({
      baseUrl: "https://portfolio.example/api/v1",
      fetch: fetchMock,
    }));

    const assets = await api.getIdentityAssets();

    expect(assets.profile.status).toBe("draft");
    expect(assets.resumes[0]?.status).toBe("draft");
  });

  it("persists the homepage composition in one atomic request without dropping configuration", async () => {
    const rawSection = {
      id: "section-editorial",
      updated_at: now,
      section_type: "editorial",
      title: "Field note",
      position: 0,
      enabled: true,
      variant: "default",
      animation_variant: "reveal",
      data_limit: null,
      show_cta: true,
      theme: "accent",
      feature_key: "assistant",
      configuration: {
        blocks: [{ id: "proof", title: "Proof", body: "Preserved configuration." }],
      },
      status: "published",
      is_visible: true,
    };
    const fetchMock = vi.fn<typeof fetch>().mockImplementation(async (input, init) => {
      expect(String(input)).toBe(
        "https://portfolio.example/api/v1/admin/content/sections/composition",
      );
      expect(init?.method).toBe("PUT");
      expect(JSON.parse(String(init?.body))).toEqual({
        sections: [
          expect.objectContaining({
            id: "section-editorial",
            section_type: "editorial",
            feature_key: "assistant",
            configuration: rawSection.configuration,
          }),
        ],
      });
      return json([rawSection]);
    });
    const api = new AdminApi(
      new HttpClient({
        baseUrl: "https://portfolio.example/api/v1",
        fetch: fetchMock,
        csrfToken: "csrf-token",
      }),
    );

    const saved = await api.saveHomepageSections([
      {
        id: rawSection.id,
        kind: "editorial",
        enabled: true,
        order: 0,
        variant: "default",
        animation_variant: "reveal",
        cta_visible: true,
        theme: "accent",
        feature_key: "assistant",
        custom_heading: "Field note",
        configuration: rawSection.configuration,
      },
    ]);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(saved[0]?.configuration).toEqual(rawSection.configuration);
    expect(saved[0]?.feature_key).toBe("assistant");
  });

  it("derives relationship IDs from canonical nested records for safe admin edits", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      json({
        items: [
          {
            id: "project-1",
            updated_at: now,
            title: "Relationship proof",
            status: "published",
            skills: [{ id: "skill-1", name: "Python" }],
            sectors: [{ id: "sector-1", name: "Platforms" }],
          },
        ],
        total: 1,
        limit: 25,
        offset: 0,
      }),
    );
    const api = new AdminApi(
      new HttpClient({
        baseUrl: "https://portfolio.example/api/v1",
        fetch: fetchMock,
      }),
    );

    const projects = await api.list("projects");

    expect(projects.items[0]?.data.skill_ids).toEqual(["skill-1"]);
    expect(projects.items[0]?.data.sector_ids).toEqual(["sector-1"]);
  });

  it("submits one structured evidence contract before requesting owner approval", async () => {
    const canonicalEvidence = {
      kind: "managed_media",
      visibility: "public",
      reference_url: null,
      managed_media_id: "media-proof-1",
      reference_text: null,
      public_label: "Reviewed benchmark artifact",
      provenance: "Owner-controlled immutable media archive",
      captured_at: "2026-08-20",
      reviewer_note: "Internal review complete.",
    };
    const fetchMock = vi.fn<typeof fetch>().mockImplementation(async (input, init) => {
      const url = String(input);
      if (init?.method === "POST") {
        expect(url).toBe("https://portfolio.example/api/v1/admin/portfolio/metrics");
        expect(JSON.parse(String(init.body))).toEqual({
          project_id: "project-1",
          label: "Latency reduction",
          value: "42%",
          context: "Measured against the reviewed baseline.",
          evidence: canonicalEvidence,
        });
        return json({
          id: "metric-1",
          updated_at: now,
          label: "Latency reduction",
          is_approved: false,
          evidence: canonicalEvidence,
        }, 201);
      }
      expect(init?.method).toBe("PUT");
      expect(url).toBe(
        "https://portfolio.example/api/v1/admin/portfolio/metrics/metric-1/approval",
      );
      expect(init?.body).toBe("{}");
      return json({
        id: "metric-1",
        updated_at: now,
        label: "Latency reduction",
        is_approved: true,
        evidence: canonicalEvidence,
      });
    });
    const api = new AdminApi(
      new HttpClient({
        baseUrl: "https://portfolio.example/api/v1",
        fetch: fetchMock,
        csrfToken: "csrf-token",
      }),
    );

    const saved = await api.create("metrics", {
      project_id: "project-1",
      label: "Latency reduction",
      value: "42%",
      context: "Measured against the reviewed baseline.",
      evidence_kind: "managed_media",
      evidence_visibility: "public",
      evidence_managed_media_id: "media-proof-1",
      evidence_public_label: "Reviewed benchmark artifact",
      evidence_provenance: "Owner-controlled immutable media archive",
      evidence_captured_at: "2026-08-20",
      evidence_reviewer_note: "Internal review complete.",
      is_approved: true,
    });

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(saved.data.evidence_kind).toBe("managed_media");
    expect(saved.data.evidence_managed_media_id).toBe("media-proof-1");
    expect(saved.data.is_approved).toBe(true);
  });
});
