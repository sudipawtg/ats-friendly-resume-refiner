import { test, expect } from "@playwright/test";
import { createSampleCvZip } from "../helpers/sample-cv-zip";
import { sampleJobDescription } from "../helpers/fixtures";
import { fillManualJobDescription } from "../helpers/playground";

const backendBaseUrl =
  process.env.PLAYWRIGHT_BACKEND_URL ?? "http://127.0.0.1:8001";

test.describe("Live API Integration", () => {
  test.beforeEach(async ({ page }) => {
    await page.unroute("**/*");
  });

  test("uploads CV via API and completes tailor flow in the UI", async ({ page, request }) => {
    const zipBuffer = await createSampleCvZip();
    const uploadResponse = await request.post(`${backendBaseUrl}/api/cvs/upload`, {
      multipart: {
        file: {
          name: "master_cv.zip",
          mimeType: "application/zip",
          buffer: zipBuffer,
        },
        name: "Playwright E2E CV",
      },
    });
    expect(uploadResponse.ok()).toBeTruthy();
    const uploadedProject = await uploadResponse.json();
    expect(uploadedProject.id).toBeTruthy();

    await page.goto("/cvs", { waitUntil: "commit" });
    await expect(page.getByTestId(`cv-project-${uploadedProject.id}`)).toBeVisible({
      timeout: 15_000,
    });

    await page.goto("/playground", { waitUntil: "commit" });
    await page.waitForResponse((response) => response.url().includes("/api/cvs"));

    await page.getByTestId("playground-cv-select").selectOption(uploadedProject.id);
    await fillManualJobDescription(page, sampleJobDescription);

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

    await expect(page.getByTestId("playground-fit-score")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("download-report-btn")).toBeVisible();
  });
});
