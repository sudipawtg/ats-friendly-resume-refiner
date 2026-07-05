import type { Page, Route } from "@playwright/test";
import {
  mockAnalyzeResult,
  mockCvProject,
  mockJobSearchResult,
  mockPreviewResult,
  mockTailorResult,
  sampleJobDescription,
} from "./fixtures";

function jsonResponse(route: Route, body: unknown, status = 200): Promise<void> {
  return route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  });
}

function resolveApiPath(url: string): string | null {
  const parsed = new URL(url);
  const apiIndex = parsed.pathname.indexOf("/api/");
  if (apiIndex === -1) {
    return null;
  }
  const apiPath = parsed.pathname.slice(apiIndex + 5);
  return apiPath.startsWith("/") ? apiPath.slice(1) : apiPath;
}

const MINIMAL_PDF = Buffer.from(
  "%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\nxref\n0 4\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n0\n%%EOF\n"
);

const MOCK_CV_TEMPLATES = [
  {
    id: "classic_blue",
    name: "Classic Blue",
    description: "Professional layout with blue accents.",
    preview_color: "#3D5A80",
    category: "Professional",
    section_order: ["Skills", "Experience", "Education", "Activities"],
    preview_url: "/api/cv-templates/classic_blue/preview.svg",
  },
  {
    id: "modern_teal",
    name: "Modern Teal",
    description: "Fresh teal highlights.",
    preview_color: "#14B8A6",
    category: "Modern",
    section_order: ["Skills", "Experience", "Education", "Activities"],
    preview_url: "/api/cv-templates/modern_teal/preview.svg",
  },
];

function svgResponse(route: Route): Promise<void> {
  return route.fulfill({
    status: 200,
    contentType: "image/svg+xml",
    body: '<svg xmlns="http://www.w3.org/2000/svg" width="300" height="200"><rect width="300" height="200" fill="#fff"/></svg>',
  });
}

function pdfResponse(route: Route): Promise<void> {
  return route.fulfill({
    status: 200,
    contentType: "application/pdf",
    body: MINIMAL_PDF,
  });
}

export async function mockDefaultApiRoutes(page: Page): Promise<void> {
  await page.unroute("**/*");

  let cvProjects = [mockCvProject];

  await page.route("**/*", async (route) => {
    const path = resolveApiPath(route.request().url());
    if (!path) {
      await route.continue();
      return;
    }

    if (route.request().method() === "GET" && path === "cvs") {
      return jsonResponse(route, cvProjects);
    }

    if (route.request().method() === "GET" && path === "cv-templates") {
      return jsonResponse(route, MOCK_CV_TEMPLATES);
    }

    if (route.request().method() === "GET" && path.startsWith("cv-templates/") && path.endsWith("/preview.svg")) {
      return svgResponse(route);
    }

    if (route.request().method() === "GET" && path.endsWith("/master-pdf")) {
      return pdfResponse(route);
    }

    if (route.request().method() === "GET" && path.endsWith("/master-docx")) {
      return route.fulfill({
        status: 200,
        contentType: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        body: Buffer.from("mock-docx"),
      });
    }

    if (route.request().method() === "GET" && path.includes("/download/") && path.endsWith("/pdf")) {
      return pdfResponse(route);
    }

    if (route.request().method() === "GET" && path.includes("/download/") && path.endsWith("/docx")) {
      return route.fulfill({
        status: 200,
        contentType: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        body: Buffer.from("mock-docx"),
      });
    }

    if (route.request().method() === "POST" && path.endsWith("/sections/refine")) {
      return jsonResponse(route, {
        section_path: "sections/skills.tex",
        content: "\\item Updated skills content",
        reason: "Made bullets clearer",
      });
    }

    if (route.request().method() === "POST" && path.endsWith("/coach/review")) {
      return jsonResponse(route, {
        overall_score: 82,
        summary: "Solid CV with opportunities to strengthen experience impact.",
        strengths: ["Strong AI/ML background", "Clear production experience"],
        top_improvements: ["Sharpen experience bullets with metrics"],
        section_suggestions: [
          {
            section_path: "sections/experience.tex",
            score: 68,
            priority: "high",
            issues: ["Bullets could highlight measurable outcomes more clearly"],
            suggested_instruction:
              "Rewrite experience bullets using STAR format and metrics already in the CV.",
          },
          {
            section_path: "sections/skills.tex",
            score: 75,
            priority: "medium",
            issues: ["Skills could be grouped by category"],
            suggested_instruction: "Group skills into Languages, AI/ML, Cloud, and Tools.",
          },
        ],
      });
    }

    if (route.request().method() === "POST" && path.endsWith("/coach/chat")) {
      return jsonResponse(route, {
        reply:
          "I can shorten your experience section and add cloud keywords. Use Apply to CV when ready.",
        suggested_instruction: "Shorten experience bullets and emphasize AWS, Azure, and GCP.",
        target_section_path: "sections/experience.tex",
        messages: [
          { role: "user", content: "Make experience shorter" },
          {
            role: "assistant",
            content:
              "I can shorten your experience section and add cloud keywords. Use Apply to CV when ready.",
          },
        ],
      });
    }

    if (route.request().method() === "GET" && path === "settings/tailoring") {
      return jsonResponse(route, {
        global_instruction: "Position as Senior AI Engineer with cloud and LLM impact.",
        section_instructions: {},
        active_profile_id: null,
      });
    }

    if (route.request().method() === "PUT" && path === "settings/tailoring") {
      return jsonResponse(route, {
        global_instruction: "Position as Senior AI Engineer with cloud and LLM impact.",
        section_instructions: {},
        active_profile_id: null,
      });
    }

    if (route.request().method() === "PUT" && path.startsWith("cvs/") && path.includes("/sections/")) {
      const sectionPath = path.split("/sections/")[1] ?? "sections/skills.tex";
      return jsonResponse(route, {
        section_path: sectionPath,
        content: "\\item Manually saved LaTeX content",
      });
    }

    if (route.request().method() === "GET" && path.includes("/sections/") && path.endsWith("/history")) {
      const sectionPath = path.split("/sections/")[1]?.replace(/\/history$/, "") ?? "sections/skills.tex";
      return jsonResponse(route, [
        {
          version_id: "v1",
          source: "manual",
          created_at: "2026-01-01T00:00:00.000Z",
          preview: "\\item Previous version",
        },
      ]);
    }

    if (route.request().method() === "POST" && path.includes("/sections/") && path.endsWith("/restore")) {
      const sectionPath = path.split("/sections/")[1]?.replace(/\/restore$/, "") ?? "sections/skills.tex";
      return jsonResponse(route, {
        section_path: sectionPath,
        content: "\\item Restored previous version",
      });
    }

    if (route.request().method() === "GET" && path.startsWith("cvs/") && path.endsWith("/master-sections")) {
      return jsonResponse(route, {
        sections: mockCvProject.sections.map((sectionPath) => ({
          section_path: sectionPath,
          content: `\\item Sample content for ${sectionPath}`,
        })),
      });
    }

    if (route.request().method() === "GET" && path.startsWith("cvs/") && path.includes("/sections/")) {
      const sectionPath = path.split("/sections/")[1] ?? "sections/skills.tex";
      return jsonResponse(route, {
        section_path: sectionPath,
        content: `\\item Sample content for ${sectionPath}`,
      });
    }

    if (route.request().method() === "GET" && path === "batches") {
      return jsonResponse(route, [
        {
          id: "e2e-batch-001",
          name: "E2E Campaign",
          status: "completed",
          cv_project_id: mockCvProject.id,
          total_jobs: 1,
          completed: 1,
          processing: 0,
          needs_manual: 0,
          failed: 0,
          jobs: [
            {
              id: "job-output-1",
              url: "https://example.com/job",
              company: "Acme Corp",
              title: "AI Engineer",
              location: "London",
              status: "completed",
              fit_score: 82,
              key_skills: [],
              tailoring_status: "completed",
              warnings: [],
            },
          ],
          created_at: "2026-01-01T00:00:00.000Z",
        },
      ]);
    }

    if (route.request().method() === "GET" && path === "outputs") {
      return jsonResponse(route, [
        {
          job_id: "job-output-1",
          cv_project_id: mockCvProject.id,
          status: "completed",
          job_type: "tailor",
          fit_score: 82,
          ats_score: 75,
          url: "https://example.com/job",
          updated_at: "2026-01-01T00:00:00.000Z",
        },
      ]);
    }

    if (route.request().method() === "GET" && path === "instruction-profiles") {
      return jsonResponse(route, { ai_engineer: "Position as AI engineer" });
    }

    if (route.request().method() === "GET" && path === "jobs/search/sources") {
      return jsonResponse(route, {
        reed_uk: "Reed UK",
        remotive: "Remotive",
        arbeitnow: "Arbeitnow",
      });
    }

    if (route.request().method() === "GET" && path === "jobs/search/date-filters") {
      return jsonResponse(route, { "7": 7, "14": 14, "30": 30 });
    }

    if (route.request().method() === "POST" && path === "jobs/search") {
      return jsonResponse(route, mockJobSearchResult);
    }

    if (route.request().method() === "POST" && path === "crawl") {
      return jsonResponse(route, mockAnalyzeResult.job_description);
    }

    if (route.request().method() === "POST" && path === "tailor/analyze") {
      return jsonResponse(route, mockAnalyzeResult);
    }

    if (route.request().method() === "POST" && path === "tailor/preview") {
      return jsonResponse(route, mockPreviewResult);
    }

    if (route.request().method() === "POST" && path.startsWith("tailor/preview/") && path.endsWith("/refine-section")) {
      return jsonResponse(route, {
        job_id: mockPreviewResult.job_id,
        change: mockPreviewResult.changes[0],
        changes: mockPreviewResult.changes,
        status: "completed",
      });
    }

    if (route.request().method() === "POST" && path === "tailor") {
      return jsonResponse(route, { ...mockTailorResult, changes: mockPreviewResult.changes });
    }

    if (route.request().method() === "POST" && path === "prompt/refine") {
      return jsonResponse(route, {
        refined_instruction: "Refined: emphasize Python and LLM impact.",
        methodology_applied: "STAR",
        suggestions: ["Use quantified outcomes"],
      });
    }

    if (route.request().method() === "POST" && path === "cvs/upload") {
      cvProjects = [mockCvProject];
      return jsonResponse(route, mockCvProject);
    }

    if (route.request().method() === "POST" && path === "batches") {
      return jsonResponse(route, {
        id: "e2e-batch-001",
        name: "E2E Campaign",
        status: "processing",
        cv_project_id: mockCvProject.id,
        total_jobs: 1,
        completed: 0,
        processing: 1,
        needs_manual: 0,
        failed: 0,
        jobs: [
          {
            id: "batch-job-001",
            url: "https://example.com/job",
            company: "Acme Corp",
            title: "AI Engineer",
            location: "London",
            status: "processing",
            fit_score: null,
            key_skills: [],
            tailoring_status: "pending",
            warnings: [],
          },
        ],
        created_at: "2026-01-01T00:00:00.000Z",
      });
    }

    await route.continue();
  });
}

export async function mockEmptyCvLibrary(page: Page): Promise<void> {
  await page.unroute("**/*");

  let cvProjects: typeof mockCvProject[] = [];

  await page.route("**/*", async (route) => {
    const path = resolveApiPath(route.request().url());
    if (!path) {
      await route.continue();
      return;
    }

    if (route.request().method() === "GET" && path === "cvs") {
      return jsonResponse(route, cvProjects);
    }

    if (route.request().method() === "GET" && path === "cv-templates") {
      return jsonResponse(route, MOCK_CV_TEMPLATES);
    }

    if (route.request().method() === "GET" && path.startsWith("cv-templates/") && path.endsWith("/preview.svg")) {
      return svgResponse(route);
    }

    if (route.request().method() === "GET" && path.endsWith("/master-pdf")) {
      return pdfResponse(route);
    }

    if (route.request().method() === "GET" && path.includes("/download/") && path.endsWith("/pdf")) {
      return pdfResponse(route);
    }

    if (route.request().method() === "GET" && path.startsWith("cvs/") && path.endsWith("/master-sections")) {
      return jsonResponse(route, {
        sections: mockCvProject.sections.map((sectionPath) => ({
          section_path: sectionPath,
          content: `\\item Sample content for ${sectionPath}`,
        })),
      });
    }

    if (route.request().method() === "POST" && path.endsWith("/coach/review")) {
      return jsonResponse(route, {
        overall_score: 82,
        summary: "Solid CV with opportunities to strengthen experience impact.",
        strengths: ["Strong AI/ML background"],
        top_improvements: ["Sharpen experience bullets with metrics"],
        section_suggestions: [],
      });
    }

    if (route.request().method() === "POST" && path.endsWith("/coach/chat")) {
      return jsonResponse(route, {
        reply: "Try shortening bullets and adding cloud keywords.",
        suggested_instruction: "Shorten experience and add AWS/Azure/GCP.",
        target_section_path: "sections/experience.tex",
        messages: [
          { role: "user", content: "Make experience shorter" },
          { role: "assistant", content: "Try shortening bullets and adding cloud keywords." },
        ],
      });
    }

    if (route.request().method() === "GET" && path === "settings/tailoring") {
      return jsonResponse(route, {
        global_instruction: "Position as Senior AI Engineer.",
        section_instructions: {},
        active_profile_id: null,
      });
    }

    if (route.request().method() === "PUT" && path === "settings/tailoring") {
      return jsonResponse(route, {
        global_instruction: "Position as Senior AI Engineer.",
        section_instructions: {},
        active_profile_id: null,
      });
    }

    if (route.request().method() === "PUT" && path.startsWith("cvs/") && path.includes("/sections/")) {
      const sectionPath = path.split("/sections/")[1] ?? "sections/skills.tex";
      return jsonResponse(route, {
        section_path: sectionPath,
        content: "\\item Manually saved LaTeX content",
      });
    }

    if (route.request().method() === "GET" && path.includes("/sections/") && path.endsWith("/history")) {
      const sectionPath = path.split("/sections/")[1]?.replace(/\/history$/, "") ?? "sections/skills.tex";
      return jsonResponse(route, [
        {
          version_id: "v1",
          source: "manual",
          created_at: "2026-01-01T00:00:00.000Z",
          preview: "\\item Previous version",
        },
      ]);
    }

    if (route.request().method() === "POST" && path.includes("/sections/") && path.endsWith("/restore")) {
      const sectionPath = path.split("/sections/")[1]?.replace(/\/restore$/, "") ?? "sections/skills.tex";
      return jsonResponse(route, {
        section_path: sectionPath,
        content: "\\item Restored previous version",
      });
    }

    if (route.request().method() === "GET" && path.startsWith("cvs/") && path.includes("/sections/")) {
      const sectionPath = path.split("/sections/")[1] ?? "sections/skills.tex";
      return jsonResponse(route, {
        section_path: sectionPath,
        content: `\\item Sample content for ${sectionPath}`,
      });
    }

    if (route.request().method() === "GET" && path === "batches") {
      return jsonResponse(route, [
        {
          id: "e2e-batch-001",
          name: "E2E Campaign",
          status: "completed",
          cv_project_id: mockCvProject.id,
          total_jobs: 1,
          completed: 1,
          processing: 0,
          needs_manual: 0,
          failed: 0,
          jobs: [
            {
              id: "job-output-1",
              url: "https://example.com/job",
              company: "Acme Corp",
              title: "AI Engineer",
              location: "London",
              status: "completed",
              fit_score: 82,
              key_skills: [],
              tailoring_status: "completed",
              warnings: [],
            },
          ],
          created_at: "2026-01-01T00:00:00.000Z",
        },
      ]);
    }

    if (route.request().method() === "GET" && path === "outputs") {
      return jsonResponse(route, [
        {
          job_id: "job-output-1",
          cv_project_id: mockCvProject.id,
          status: "completed",
          job_type: "tailor",
          fit_score: 82,
          ats_score: 75,
          url: "https://example.com/job",
          updated_at: "2026-01-01T00:00:00.000Z",
        },
      ]);
    }

    if (route.request().method() === "GET" && path === "instruction-profiles") {
      return jsonResponse(route, { ai_engineer: "Position as AI engineer" });
    }

    if (route.request().method() === "GET" && path === "jobs/search/sources") {
      return jsonResponse(route, {
        reed_uk: "Reed UK",
        remotive: "Remotive",
        arbeitnow: "Arbeitnow",
      });
    }

    if (route.request().method() === "GET" && path === "jobs/search/date-filters") {
      return jsonResponse(route, { "7": 7, "14": 14, "30": 30 });
    }

    if (route.request().method() === "POST" && path === "jobs/search") {
      return jsonResponse(route, mockJobSearchResult);
    }

    if (route.request().method() === "POST" && path === "crawl") {
      return jsonResponse(route, mockAnalyzeResult.job_description);
    }

    if (route.request().method() === "POST" && path === "tailor/analyze") {
      return jsonResponse(route, mockAnalyzeResult);
    }

    if (route.request().method() === "POST" && path === "tailor/preview") {
      return jsonResponse(route, mockPreviewResult);
    }

    if (route.request().method() === "POST" && path.startsWith("tailor/preview/") && path.endsWith("/refine-section")) {
      return jsonResponse(route, {
        job_id: mockPreviewResult.job_id,
        change: mockPreviewResult.changes[0],
        changes: mockPreviewResult.changes,
        status: "completed",
      });
    }

    if (route.request().method() === "POST" && path === "tailor") {
      return jsonResponse(route, { ...mockTailorResult, changes: mockPreviewResult.changes });
    }

    if (route.request().method() === "POST" && path === "prompt/refine") {
      return jsonResponse(route, {
        refined_instruction: "Refined: emphasize Python and LLM impact.",
        methodology_applied: "STAR",
        suggestions: ["Use quantified outcomes"],
      });
    }

    if (route.request().method() === "POST" && path === "cvs/upload") {
      cvProjects = [mockCvProject];
      return jsonResponse(route, mockCvProject);
    }

    if (route.request().method() === "POST" && path === "batches") {
      return jsonResponse(route, {
        id: "e2e-batch-001",
        name: "E2E Campaign",
        status: "processing",
        cv_project_id: mockCvProject.id,
        total_jobs: 1,
        completed: 0,
        processing: 1,
        needs_manual: 0,
        failed: 0,
        jobs: [],
        created_at: "2026-01-01T00:00:00.000Z",
      });
    }

    await route.continue();
  });
}
