import { expect, test } from "@playwright/test";

test.describe("Playground", () => {
  test("renders playground workspace", async ({ page }) => {
    await page.goto("/playground", { waitUntil: "commit" });
    await expect(page.getByTestId("playground-page")).toBeVisible();
    await expect(page.getByTestId("playground-job-panel")).toBeVisible();
    await expect(page.getByTestId("playground-preview-panel")).toBeVisible();
    await expect(page.getByTestId("playground-steps")).toBeVisible();
    await expect(page.getByTestId("playground-analyze-btn")).toBeVisible();
    await expect(page.getByTestId("playground-preview-btn")).toBeVisible();
    await expect(page.getByTestId("playground-apply-btn")).toBeVisible();
  });

  test("prefills job url from query string", async ({ page }) => {
    await page.goto("/playground?url=https%3A%2F%2Fexample.com%2Fai-engineer", {
      waitUntil: "commit",
    });
    await expect(page.getByTestId("playground-job-url")).toHaveValue("https://example.com/ai-engineer");
  });

  test("nav includes playground link", async ({ page }) => {
    await page.goto("/playground", { waitUntil: "commit" });
    await expect(page.getByTestId("nav-playground")).toBeVisible();
  });
});
