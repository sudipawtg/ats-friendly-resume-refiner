import { test, expect } from "@playwright/test";
import { mockDefaultApiRoutes } from "../helpers/api-mocks";
import { mockCvProject } from "../helpers/fixtures";

test.describe("CV platform flow (UI)", () => {
  test.beforeEach(async ({ page }) => {
    await mockDefaultApiRoutes(page);
  });

  test("CVs page shows template gallery with previews", async ({ page }) => {
    await page.goto("/cvs", { waitUntil: "commit" });
    await expect(page.getByTestId("template-gallery")).toBeVisible();
    await expect(page.getByTestId("template-preview-classic_blue")).toBeVisible();
    await expect(page.getByTestId("template-card-modern_teal")).toBeVisible();
  });

  test("Edit page supports section AI updates and preview", async ({ page }) => {
    await page.goto(`/edit?cvId=${mockCvProject.id}`, { waitUntil: "commit" });
    await expect(page.getByTestId("master-section-editor")).toBeVisible();
    await expect(page.getByTestId("playground-pdf-viewer")).toBeVisible();
    await expect(page.getByTestId("edit-download-docx-btn")).toBeVisible();
  });

  test("Outputs page offers PDF, DOCX, and ZIP downloads", async ({ page }) => {
    await page.goto("/outputs", { waitUntil: "commit" });
    await expect(page.getByTestId("outputs-page")).toBeVisible();
    await expect(page.getByTestId("pdf-job-output-1")).toBeVisible();
    await expect(page.getByTestId("docx-job-output-1")).toBeVisible();
    await expect(page.getByTestId("download-job-output-1")).toBeVisible();
  });

  test("CV project card links to edit and tailor flows", async ({ page }) => {
    await page.goto("/cvs", { waitUntil: "commit" });
    const projectCard = page.getByTestId(`cv-project-${mockCvProject.id}`);
    await expect(projectCard.getByRole("link", { name: "Edit" })).toHaveAttribute(
      "href",
      `/edit?cvId=${mockCvProject.id}`
    );
    await expect(projectCard.getByRole("link", { name: "Tailor" })).toHaveAttribute(
      "href",
      `/playground?cvId=${mockCvProject.id}`
    );
  });
});
