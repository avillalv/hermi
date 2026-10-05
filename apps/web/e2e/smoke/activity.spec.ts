import { expect, test } from "@playwright/test";

// WF-027.2: Activity tab error with retry, and offline. Needs `npm run dev`. The trips list is stubbed so the test owns the state.
const empty = { items: [], next_cursor: null, has_more: false };

test("Activity shows an error with Try again, then recovers", async ({ page }) => {
  let fail = true;
  await page.route("**/v1/trips", (r) => (fail ? r.fulfill({ status: 500, json: {} }) : r.fulfill({ json: empty })));
  await page.goto("/sign-in");
  await page.getByRole("button", { name: "Free user" }).click();
  await page.getByRole("link", { name: "Activity" }).first().click();
  await expect(page.getByRole("alert").getByText("We could not load activity.", { exact: true })).toBeVisible({ timeout: 10_000 });
  fail = false;
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(page.getByRole("heading", { name: "Nothing new" })).toBeVisible();
});

test("Activity offline shows the saved banner", async ({ page, context }) => {
  await page.route("**/v1/trips", (r) => r.fulfill({ json: empty }));
  await page.goto("/sign-in");
  await page.getByRole("button", { name: "Free user" }).click();
  await page.getByRole("link", { name: "Activity" }).first().click();
  await expect(page.getByRole("heading", { name: "Nothing new" })).toBeVisible();
  await context.setOffline(true);
  await expect(page.getByRole("status")).toHaveText("You are offline. Showing your saved activity.");
});
