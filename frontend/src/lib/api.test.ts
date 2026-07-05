import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import {
  applyCVTemplate,
  createCVFromTemplate,
  crawlJob,
  createBatch,
  downloadHtmlReport,
  fetchBatch,
  fetchBatches,
  fetchCVProjects,
  fetchCVTemplates,
  fetchDateFilters,
  fetchInstructionProfiles,
  fetchJobSearchSources,
  getDocxUrl,
  getDownloadUrl,
  getMasterDocxUrl,
  getReportDownloadUrl,
  getTemplatePreviewUrl,
  refineMasterSection,
  refinePrompt,
  searchJobs,
  tailorCV,
  uploadCV,
} from "./api";

const API_BASE = "/api";

function mockFetch(response: Partial<Response> & { json?: () => unknown }) {
  return vi.fn().mockResolvedValue({
    ok: true,
    status: 200,
    headers: new Headers({ "content-type": "application/json" }),
    json: async () => response.json?.() ?? {},
    text: async () => "",
    blob: async () => new Blob(["html"]),
    ...response,
  });
}

describe("api client", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", mockFetch({ json: () => [] }));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("fetchCVProjects calls GET /cvs", async () => {
    const fetchMock = mockFetch({ json: () => [{ id: "1", name: "CV" }] });
    vi.stubGlobal("fetch", fetchMock);

    const projects = await fetchCVProjects();
    expect(projects).toHaveLength(1);
    expect(fetchMock).toHaveBeenCalledWith(
      `${API_BASE}/cvs`,
      expect.objectContaining({ headers: expect.any(Object) })
    );
  });

  it("uploadCV sends multipart form data without JSON content-type", async () => {
    const fetchMock = mockFetch({ json: () => ({ id: "p1", name: "Test" }) });
    vi.stubGlobal("fetch", fetchMock);

    const file = new File(["zip"], "cv.zip", { type: "application/zip" });
    await uploadCV(file, "My CV", "modern_teal");

    const [, options] = fetchMock.mock.calls[0];
    expect(options?.body).toBeInstanceOf(FormData);
    expect(options?.headers).not.toHaveProperty("Content-Type");
    expect(options?.method).toBe("POST");
    expect(fetchMock.mock.calls[0][0]).toBe(`${API_BASE}/cvs/upload`);
  });

  it("fetchCVTemplates calls GET /cv-templates", async () => {
    const fetchMock = mockFetch({
      json: () => [
        {
          id: "classic_blue",
          name: "Classic Blue",
          description: "Test",
          preview_color: "#3D5A80",
          category: "Professional",
          section_order: ["Skills"],
          preview_url: "/api/cv-templates/classic_blue/preview.svg",
        },
      ],
    });
    vi.stubGlobal("fetch", fetchMock);

    const templates = await fetchCVTemplates();
    expect(templates).toHaveLength(1);
    expect(fetchMock.mock.calls[0][0]).toBe(`${API_BASE}/cv-templates`);
  });

  it("createCVFromTemplate posts name and template_id", async () => {
    const fetchMock = mockFetch({ json: () => ({ id: "p1", source_type: "template" }) });
    vi.stubGlobal("fetch", fetchMock);

    await createCVFromTemplate("Starter", "classic_blue");

    const body = JSON.parse(fetchMock.mock.calls[0][1]?.body as string);
    expect(body).toEqual({ name: "Starter", template_id: "classic_blue" });
  });

  it("refineMasterSection posts section refine payload", async () => {
    const fetchMock = mockFetch({
      json: () => ({
        section_path: "sections/skills.tex",
        content: "\\item Python",
        reason: "Updated",
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await refineMasterSection({
      projectId: "proj-1",
      sectionPath: "sections/skills.tex",
      instruction: "Make concise",
    });

    expect(fetchMock.mock.calls[0][0]).toBe(`${API_BASE}/cvs/proj-1/sections/refine`);
    const body = JSON.parse(fetchMock.mock.calls[0][1]?.body as string);
    expect(body.section_path).toBe("sections/skills.tex");
    expect(body.instruction).toBe("Make concise");
  });

  it("export URL helpers build expected paths", () => {
    expect(getDocxUrl("proj-1", "job-1")).toBe(`${API_BASE}/cvs/proj-1/download/job-1/docx`);
    expect(getMasterDocxUrl("proj-1")).toBe(`${API_BASE}/cvs/proj-1/master-docx`);
    expect(getTemplatePreviewUrl("classic_blue")).toBe(
      `${API_BASE}/cv-templates/classic_blue/preview.svg`
    );
  });

  it("applyCVTemplate posts template id", async () => {
    const fetchMock = mockFetch({ json: () => ({ id: "p1", template_id: "modern_teal" }) });
    vi.stubGlobal("fetch", fetchMock);

    await applyCVTemplate("proj-1", "modern_teal");

    const body = JSON.parse(fetchMock.mock.calls[0][1]?.body as string);
    expect(body.template_id).toBe("modern_teal");
  });

  it("crawlJob posts url and manual description", async () => {
    const fetchMock = mockFetch({ json: () => ({ title: "Engineer", extraction_confidence: 0.9 }) });
    vi.stubGlobal("fetch", fetchMock);

    await crawlJob("https://example.com/job", "Manual JD");

    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe(`${API_BASE}/crawl`);
    expect(JSON.parse(options?.body as string)).toEqual({
      url: "https://example.com/job",
      manual_description: "Manual JD",
    });
  });

  it("tailorCV posts payload as JSON", async () => {
    const fetchMock = mockFetch({ json: () => ({ job_id: "j1", status: "completed" }) });
    vi.stubGlobal("fetch", fetchMock);

    await tailorCV({ cv_project_id: "p1", job_description: "JD" });

    const [, options] = fetchMock.mock.calls[0];
    expect(options?.method).toBe("POST");
    expect(JSON.parse(options?.body as string).cv_project_id).toBe("p1");
  });

  it("refinePrompt sends instruction fields", async () => {
    const fetchMock = mockFetch({
      json: () => ({ refined_instruction: "Refined", methodology_applied: "STAR", suggestions: [] }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await refinePrompt("Be concise", "context", "sections/skills.tex");

    const body = JSON.parse(fetchMock.mock.calls[0][1]?.body as string);
    expect(body.raw_instruction).toBe("Be concise");
    expect(body.context).toBe("context");
    expect(body.target_section).toBe("sections/skills.tex");
  });

  it("createBatch and fetchBatches use correct paths", async () => {
    const fetchMock = mockFetch({ json: () => ({ id: "b1", total_jobs: 1 }) });
    vi.stubGlobal("fetch", fetchMock);

    await createBatch({ cv_project_id: "p1", name: "Batch", jobs: [] });
    expect(fetchMock.mock.calls[0][0]).toBe(`${API_BASE}/batches`);

    fetchMock.mockResolvedValueOnce({
      ok: true,
      status: 200,
      headers: new Headers({ "content-type": "application/json" }),
      json: async () => [],
    });
    await fetchBatches();
    expect(fetchMock.mock.calls[1][0]).toBe(`${API_BASE}/batches`);
  });

  it("fetchBatch uses batch id in path", async () => {
    const fetchMock = mockFetch({ json: () => ({ id: "b1" }) });
    vi.stubGlobal("fetch", fetchMock);

    await fetchBatch("batch-123");
    expect(fetchMock.mock.calls[0][0]).toBe(`${API_BASE}/batches/batch-123`);
  });

  it("fetchInstructionProfiles calls correct endpoint", async () => {
    const fetchMock = mockFetch({ json: () => ({ ai_engineer: "Profile text" }) });
    vi.stubGlobal("fetch", fetchMock);

    const profiles = await fetchInstructionProfiles();
    expect(profiles.ai_engineer).toBe("Profile text");
  });

  it("getDownloadUrl builds project and job paths", () => {
    expect(getDownloadUrl("proj-1", "job-1")).toBe(
      `${API_BASE}/cvs/proj-1/download/job-1`
    );
  });

  it("getReportDownloadUrl builds query string", () => {
    const url = getReportDownloadUrl("job-1", undefined);
    expect(url).toContain("/reports/html?");
    expect(url).toContain("job_id=job-1");
  });

  it("searchJobs posts search payload", async () => {
    const fetchMock = mockFetch({
      json: () => ({ query: "AI Engineer", total_results: 0, results: [], sources_searched: [], warnings: [] }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await searchJobs({ job_title: "AI Engineer", location: "London" });

    const body = JSON.parse(fetchMock.mock.calls[0][1]?.body as string);
    expect(body.job_title).toBe("AI Engineer");
  });

  it("fetchJobSearchSources and fetchDateFilters", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers: new Headers({ "content-type": "application/json" }),
        json: async () => ({ reed_uk: "Reed" }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers: new Headers({ "content-type": "application/json" }),
        json: async () => ({ "7": 7 }),
      });
    vi.stubGlobal("fetch", fetchMock);

    const sources = await fetchJobSearchSources();
    expect(sources.reed_uk).toBe("Reed");

    const filters = await fetchDateFilters();
    expect(filters["7"]).toBe(7);
  });

  it("downloadHtmlReport returns blob on success", async () => {
    const blob = new Blob(["<html></html>"], { type: "text/html" });
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        blob: async () => blob,
      })
    );

    const result = await downloadHtmlReport({ job_id: "j1" });
    expect(result).toBeInstanceOf(Blob);
  });

  it("throws on non-ok response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        text: async () => "Server error",
        headers: new Headers(),
      })
    );

    await expect(fetchCVProjects()).rejects.toThrow("Server error");
  });

  it("downloadHtmlReport throws on failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, status: 500 })
    );

    await expect(downloadHtmlReport({ job_id: "j1" })).rejects.toThrow(
      "Report generation failed"
    );
  });
});
