import { test, expect } from "@playwright/test";
import { mockDefaultApiRoutes } from "../helpers/api-mocks";
import { mockCvProject } from "../helpers/fixtures";

test.describe("Dashboard", () => {
  test.beforeEach(async ({ page }) => {
    await mockDefaultApiRoutes(page);
    await page.goto("/", { waitUntil: "commit" });
  });

  test("renders dashboard stats and navigation", async ({ page }) => {
    await expect(page.getByTestId("dashboard-page")).toBeVisible();
    await expect(page.getByTestId("stat-cvs")).toContainText("1");
    await expect(page.getByTestId("stat-batches")).toContainText("0");
    await expect(page.getByRole("heading", { name: "Welcome back" })).toBeVisible();
  });

  test("navigates to key feature pages from sidebar", async ({ page }) => {
    await page.getByTestId("nav-cvs").click();
    await expect(page).toHaveURL(/\/cvs/);
    await expect(page.getByTestId("cvs-page")).toBeVisible();

    await page.getByTestId("nav-playground").click();
    await expect(page).toHaveURL(/\/playground/);
    await expect(page.getByTestId("playground-page")).toBeVisible();

    await page.getByTestId("nav-discover").click();
    await expect(page).toHaveURL(/\/discover/);
    await expect(page.getByTestId("discover-page")).toBeVisible();
  });
});
