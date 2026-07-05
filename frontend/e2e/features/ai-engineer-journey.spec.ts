import { test, expect } from "@playwright/test";
import { createSampleCvZip } from "../helpers/sample-cv-zip";
import { fillManualJobDescription, openAdvancedOptions } from "../helpers/playground";

const backendBaseUrl =
  process.env.PLAYWRIGHT_BACKEND_URL ?? "http://127.0.0.1:8001";

const aiEngineerJobDescription = `
AI Engineer — TechNova Ltd, London, UK (Hybrid)

We are hiring an AI Engineer to design and deploy production LLM applications.
You will build RAG pipelines, integrate OpenAI and Azure APIs, and ship FastAPI microservices on AWS.

Responsibilities:
- Develop and fine-tune LLM-based features for enterprise clients
- Build retrieval-augmented generation pipelines with LangChain
- Collaborate with product and data teams on model evaluation
- Deploy services with Docker and Kubernetes

Required: Python, PyTorch or TensorFlow, LLMs, RAG, AWS, 3+ years ML engineering experience.
Preferred: MLOps, vector databases, stakeholder communication, insurance or fintech domain.
`.trim();

test.describe("AI Engineer job — full user journey", () => {
  test.setTimeout(180_000);

  test.beforeEach(async ({ page }) => {
    await page.unroute("**/*");
  });

  test("job description → preview sections → tailor with instructions → download", async ({
    page,
    request,
  }) => {
    const zipBuffer = await createSampleCvZip();
    const uploadResponse = await request.post(`${backendBaseUrl}/api/cvs/upload`, {
      multipart: {
        file: {
          name: "master_cv.zip",
          mimeType: "application/zip",
          buffer: zipBuffer,
        },
        name: "AI Engineer E2E CV",
      },
    });
    expect(uploadResponse.ok()).toBeTruthy();
    const project = await uploadResponse.json();

    const skillsSection = await request.get(
      `${backendBaseUrl}/api/cvs/${project.id}/sections/sections/skills.tex`
    );
    expect(skillsSection.ok()).toBeTruthy();
    const skillsContent = (await skillsSection.json()).content as string;
    expect(skillsContent.length).toBeGreaterThan(0);

    await page.goto("/playground", { waitUntil: "commit" });
    await page.waitForResponse((response) => response.url().includes("/api/cvs"));

    await page.getByTestId("playground-cv-select").selectOption(project.id);
    await fillManualJobDescription(page, aiEngineerJobDescription);
    await openAdvancedOptions(page);
    await page.getByTestId("playground-global-instruction").fill(
      "Position me as a strong AI Engineer. Highlight Python, LLM, and RAG experience. Use STAR for experience bullets."
    );
    await page.getByTestId("playground-profile-select").selectOption("ai_engineer");

    const tailorResponsePromise = page.waitForResponse(
      (response) =>
        response.url().includes("/api/tailor") &&
        response.request().method() === "POST" &&
        !response.url().includes("/preview") &&
        !response.url().includes("/analyze")
    );
    await page.getByTestId("playground-apply-btn").click();

    const tailorResponse = await tailorResponsePromise;
    expect(tailorResponse.ok()).toBeTruthy();

    const tailorResult = await tailorResponse.json();
    expect(tailorResult.job_id).toBeTruthy();
    expect(tailorResult.status).toMatch(/completed|needs_manual/);
    expect(tailorResult.fit_analysis.overall_fit).toBeGreaterThanOrEqual(0);
    expect(tailorResult.ats_analysis.overall_score).toBeGreaterThanOrEqual(0);

    await expect(page.getByTestId("playground-fit-score")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("download-report-btn")).toBeVisible();

    const downloadResponse = await request.get(
      `${backendBaseUrl}/api/cvs/${project.id}/download/${tailorResult.job_id}`
    );
    expect(downloadResponse.ok()).toBeTruthy();
    expect(downloadResponse.headers()["content-type"]).toContain("zip");

    const reportResponse = await request.post(`${backendBaseUrl}/api/reports/html`, {
      data: { job_id: tailorResult.job_id },
    });
    expect(reportResponse.ok()).toBeTruthy();
    const reportHtml = await reportResponse.text();
    expect(reportHtml).toContain("ResumeForge");
  });
});
