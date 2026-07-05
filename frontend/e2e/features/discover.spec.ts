import { test, expect } from "@playwright/test";
import { mockDefaultApiRoutes } from "../helpers/api-mocks";
import { mockJobSearchResult } from "../helpers/fixtures";

test.describe("Job Discovery", () => {
  test.beforeEach(async ({ page }) => {
    await mockDefaultApiRoutes(page);
    await page.goto("/discover", { waitUntil: "commit" });
    await page.waitForResponse((response) => response.url().includes("/api/jobs/search/sources"));
  });

  test("searches jobs and displays results", async ({ page }) => {
    await expect(page.getByTestId("discover-page")).toBeVisible();

    await page.getByTestId("discover-job-title").fill("AI Engineer");
    await page.getByTestId("discover-location").fill("London, UK");

    const searchRequest = page.waitForResponse(
      (response) =>
        response.url().includes("/api/jobs/search") && response.request().method() === "POST"
    );
    await page.getByTestId("discover-search-btn").click();
    await searchRequest;

    const firstResult = mockJobSearchResult.results[0];
    await expect(page.getByTestId(`job-result-${firstResult.id}`)).toBeVisible({ timeout: 10_000 });
    await expect(page.getByRole("heading", { name: firstResult.title })).toBeVisible();
    await expect(page.getByText(firstResult.company)).toBeVisible();
  });

  test("validates empty job title before search", async ({ page }) => {
    await page.getByTestId("discover-search-btn").click();
    await expect(page.getByText("Enter a job title.")).toBeVisible();
  });

  test("copy urls button appears after search", async ({ page }) => {
    await page.getByTestId("discover-job-title").fill("AI Engineer");

    const searchRequest = page.waitForResponse(
      (response) =>
        response.url().includes("/api/jobs/search") && response.request().method() === "POST"
    );
    await page.getByTestId("discover-search-btn").click();
    await searchRequest;

    await expect(page.getByTestId("copy-urls-btn")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByTestId("send-batch-btn")).toBeVisible();
  });
});
