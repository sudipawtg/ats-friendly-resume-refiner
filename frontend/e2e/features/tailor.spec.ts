import { test, expect } from "@playwright/test";
import { mockDefaultApiRoutes } from "../helpers/api-mocks";
import { mockCvProject, mockTailorResult, sampleJobDescription } from "../helpers/fixtures";
import { fillManualJobDescription, openAdvancedOptions } from "../helpers/playground";

test.describe("Playground apply flow", () => {
  test.beforeEach(async ({ page }) => {
    await mockDefaultApiRoutes(page);
    await page.goto("/playground", { waitUntil: "commit" });
    await page.waitForResponse((response) => response.url().includes("/api/cvs"));
  });

  test("completes apply flow with manual job description", async ({ page }) => {
    await expect(page.getByTestId("playground-page")).toBeVisible();

    await page.getByTestId("playground-cv-select").selectOption(mockCvProject.id);
    await fillManualJobDescription(page, sampleJobDescription);
    await openAdvancedOptions(page);
    await page.getByTestId("playground-global-instruction").fill("Emphasize Python and LLM experience");

    const applyRequest = page.waitForResponse(
      (response) =>
        response.url().includes("/api/tailor") &&
        response.request().method() === "POST" &&
        !response.url().includes("/preview") &&
        !response.url().includes("/analyze")
    );
    await page.getByTestId("playground-apply-btn").click();
    await applyRequest;

    await expect(page.getByText(`${mockTailorResult.fit_analysis.overall_fit}%`)).toBeVisible();
    await expect(page.getByText("Strong matches")).toBeVisible();
    await expect(
      page.getByTestId("playground-job-panel").getByText("Python", { exact: true })
    ).toBeVisible();
    await expect(page.getByTestId("download-report-btn")).toBeVisible();
  });

  test("preview shows tailored PDF and section editor", async ({ page }) => {
    await page.getByTestId("playground-cv-select").selectOption(mockCvProject.id);
    await fillManualJobDescription(page, sampleJobDescription);

    const previewRequest = page.waitForResponse(
      (response) => response.url().includes("/api/tailor/preview") && response.request().method() === "POST"
    );
    await page.getByTestId("playground-preview-btn").click();
    await previewRequest;

    await expect(page.getByTestId("playground-pdf-viewer")).toBeVisible();
    await expect(page.getByTestId("section-editor-panel")).toBeVisible();
  });

  test("original preview shows master PDF", async ({ page }) => {
    await page.getByTestId("playground-cv-select").selectOption(mockCvProject.id);
    await page.getByTestId("preview-master-btn").click();
    await expect(page.getByTestId("playground-pdf-viewer")).toBeVisible();
  });

  test("apply stays disabled without CV and job input", async ({ page }) => {
    await expect(page.getByTestId("playground-apply-btn")).toBeDisabled();

    await page.getByTestId("playground-cv-select").selectOption(mockCvProject.id);
    await expect(page.getByTestId("playground-apply-btn")).toBeDisabled();

    await fillManualJobDescription(page, sampleJobDescription);
    await expect(page.getByTestId("playground-apply-btn")).toBeEnabled();
  });
});
