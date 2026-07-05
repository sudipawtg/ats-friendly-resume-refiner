import { test, expect } from "@playwright/test";
import { mockDefaultApiRoutes } from "../helpers/api-mocks";
import { mockCvProject } from "../helpers/fixtures";

test.describe("CV Coach", () => {
  test.beforeEach(async ({ page }) => {
    await mockDefaultApiRoutes(page);
  });

  test("shows coach panel and analysis results on edit page", async ({ page }) => {
    await page.goto(`/edit?cvId=${mockCvProject.id}`, { waitUntil: "commit" });
    await expect(page.getByTestId("cv-coach-panel")).toBeVisible();
    await page.getByTestId("cv-coach-analyze-btn").click();
    await expect(page.getByTestId("cv-coach-results")).toBeVisible();
    await expect(page.getByTestId("cv-coach-section-sections/experience.tex")).toBeVisible();
    await expect(page.getByTestId("cv-coach-apply-sections/experience.tex")).toBeVisible();
  });
});
