import { test, expect } from "@playwright/test";
import { mockDefaultApiRoutes } from "../helpers/api-mocks";
import { mockCvProject } from "../helpers/fixtures";

test.describe("Edit CV", () => {
  test.beforeEach(async ({ page }) => {
    await mockDefaultApiRoutes(page);
    await page.goto(`/edit?cvId=${mockCvProject.id}`, { waitUntil: "commit" });
  });

  test("shows section editor and preview", async ({ page }) => {
    await expect(page.getByTestId("edit-page")).toBeVisible();
    await expect(page.getByTestId("master-section-editor")).toBeVisible();
    await expect(page.getByTestId("playground-pdf-viewer")).toBeVisible();
  });

  test("refines a section with AI", async ({ page }) => {
    const refineRequest = page.waitForResponse(
      (response) =>
        response.url().includes("/api/cvs/") &&
        response.url().includes("/sections/refine") &&
        response.request().method() === "POST"
    );

    await page.getByTestId("master-instruction-sections/skills.tex").fill("Make skills more concise");
    await page.getByTestId("master-regenerate-sections/skills.tex").click();
    await refineRequest;

    await expect(page.getByText("Updated")).toBeVisible();
  });
});
