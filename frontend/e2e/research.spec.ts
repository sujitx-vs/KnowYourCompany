import { test, expect } from "@playwright/test";

test("research, refresh recovery, cited preparation and PDF download", async ({ page }, testInfo) => {
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Know the company. Find your place." })).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath("welcome.png"), fullPage: true });
  await page.getByLabel("Which company is on your mind?").fill("Northstar Systems");
  await page.getByRole("button", { name: "Build my brief" }).click();
  await expect(page.getByRole("heading", { name: "Northstar Systems", exact: true }).first()).toBeVisible();
  await page.reload();
  await expect(page.getByRole("heading", { name: "Where do you want to go?" })).toBeVisible({ timeout: 25000 });
  await page.screenshot({ path: testInfo.outputPath("company-brief.png"), fullPage: true });
  await page.getByRole("button", { name: /Software Engineering.*engineering evidence/ }).click();
  await expect(page.getByRole("button", { name: "Download PDF" })).toBeVisible({ timeout: 25000 });
  await expect(page.getByText("Suggested preparation", { exact: true })).toBeVisible();
  await page.getByRole("link", { name: "Read source D1" }).first().click();
  await expect(page.locator("#source-D1")).toBeInViewport();
  await page.screenshot({ path: testInfo.outputPath("complete-dossier.png"), fullPage: true });
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download PDF" }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toContain("dossier.pdf");
  await page.getByLabel("How useful was this brief?").selectOption("5");
  await page.getByRole("button", { name: "Send feedback" }).click();
  await expect(page.getByText("Thanks. Your feedback is saved with this brief.")).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  expect(errors).toEqual([]);
});

test("keyboard search and cancellation", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Which company is on your mind?").fill("Northstar Systems");
  await page.getByLabel("Which company is on your mind?").press("Enter");
  await page.getByRole("button", { name: "Cancel research" }).click();
  await expect(page.getByRole("heading", { name: "Pick it up when you’re ready." })).toBeVisible();
  await page.reload();
  await expect(page.getByRole("heading", { name: "Pick it up when you’re ready." })).toBeVisible();
});

test("status polling recovers when the event stream is unavailable", async ({ page }) => {
  await page.route("**/runs/*/events", route => route.abort());
  await page.goto("/");
  await page.getByLabel("Which company is on your mind?").fill("Northstar Systems");
  await page.getByRole("button", { name: "Build my brief" }).click();
  await expect(page.getByRole("heading", { name: "Where do you want to go?" })).toBeVisible({ timeout: 25000 });
  await expect(page.getByRole("heading", { name: "The company brief", exact: true })).toBeVisible();
});

test("operator credentials are not persisted", async ({ page }) => {
  await page.route("**/admin/metrics", route => route.fulfill({ json: {
    runs: 4, completed: 2, failed: 1, activated: 3, cancelled: 1, cache_hits: 1,
    feedback_count: 2, returning_sessions: 1, period_days: 30, median_compute_seconds: 20,
    p95_compute_seconds: 40, estimated_provider_cost_usd: null,
    estimated_cost_per_completed_brief_usd: null, cost_note: "Prices are not configured.",
  } }));
  await page.goto("/operator");
  const key = "local-test-operator-credential-123456789";
  await page.getByLabel("Operator access key").fill(key);
  await page.getByRole("button", { name: "Load metrics" }).click();
  await expect(page.getByText("Completed dossiers", { exact: true })).toBeVisible();
  expect(await page.evaluate(() => JSON.stringify(localStorage))).not.toContain(key);
  await page.getByRole("button", { name: "Clear access" }).click();
  await expect(page.getByLabel("Operator access key")).toHaveValue("");
});
