import { test, expect } from "@playwright/test";

for (const phase of ["company", "domain", "export"]) {
  test(`${phase} retry controls reflect remaining budget`, async ({ page }) => {
    await page.addInitScript(() => localStorage.setItem("kyc.run.v2", "fixture"));
    let remaining = 0;
    await page.route("**/runs", route => route.fulfill({ json: [{
      id: "fixture", company_name: "Fixture", phase,
      status: phase === "export" ? "export_failed" : "failed",
      stage: "company_brief", message: "The saved step could not finish.",
      created_at: Date.now() / 1000, updated_at: Date.now() / 1000,
      completed_nodes: [], sources: [], events: [], identity: null,
      export_status: phase === "export" ? "failed" : "not_started",
      retry_allowed: remaining > 0, retries_remaining: remaining, retry_scope: "phase",
      failure_category: "provider_rate_limit",
    }] }));
    await page.route("**/usage", route => route.fulfill({ json: { daily_limit: 10, used_today: 0 } }));
    await page.goto("/");
    await expect(page.getByText("No manual retries remain", { exact: false })).toBeVisible();
    await expect(page.getByText("Waiting does not reset", { exact: false })).toBeVisible();
    await expect(page.getByRole("button", { name: /Retry saved step|Retry PDF export/ })).toHaveCount(0);
    remaining = 2;
    await page.reload();
    await expect(page.getByText("2 manual retries remain", { exact: false })).toBeVisible();
    await expect(page.getByRole("button", { name: /Retry saved step|Retry PDF export/ })).toBeVisible();
    await expect(page.getByText("separate from your manual retry allowance", { exact: false })).toBeVisible();
  });
}
