import { test, expect } from "@playwright/test";
import { mockDefaultApiRoutes, mockEmptyCvLibrary } from "../helpers/api-mocks";
import { mockCvProject } from "../helpers/fixtures";
import { createSampleCvZip } from "../helpers/sample-cv-zip";

test.describe("CV Upload", () => {
  test.beforeEach(async ({ page }) => {
    await mockDefaultApiRoutes(page);
    await page.goto("/cvs", { waitUntil: "commit" });
  });

  test("shows uploaded project from API", async ({ page }) => {
    await expect(page.getByTestId("cvs-page")).toBeVisible();
    await expect(page.getByTestId(`cv-project-${mockCvProject.id}`)).toBeVisible();
    await expect(page.getByText(mockCvProject.name)).toBeVisible();
  });

  test("uploads a zip file and shows the project", async ({ page }) => {
    await mockEmptyCvLibrary(page);
    await page.goto("/cvs", { waitUntil: "commit" });
    await expect(page.getByTestId("empty-cvs")).toBeVisible();

    const zipBuffer = await createSampleCvZip();
    await page.getByTestId("cv-name-input").fill("Uploaded E2E CV");

    const uploadRequest = page.waitForResponse(
      (response) =>
        response.url().includes("/api/cvs/upload") && response.request().method() === "POST"
    );
    await page.getByTestId("cv-file-input").setInputFiles({
      name: "master_cv.zip",
      mimeType: "application/zip",
      buffer: zipBuffer,
    });
    await uploadRequest;

    await expect(page.getByTestId(`cv-project-${mockCvProject.id}`)).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText(mockCvProject.name)).toBeVisible();
  });
});
