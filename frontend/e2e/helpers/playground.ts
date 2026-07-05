import type { Page } from "@playwright/test";

export async function fillManualJobDescription(page: Page, description: string): Promise<void> {
  await page.getByText("Or paste description").click();
  await page.getByTestId("playground-manual-jd").fill(description);
}

export async function openAdvancedOptions(page: Page): Promise<void> {
  await page.getByTestId("playground-advanced-toggle").click();
}
