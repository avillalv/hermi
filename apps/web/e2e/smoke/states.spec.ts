import { expect, test } from "@playwright/test";

// WF-036.2: a trip route shows the shared offline and error states, and Try again recovers. Needs `npm run dev`. The trip is stubbed so the test owns the state.
const trip = { id: "t1", version: 1, name: "Lisbon", status: "planning", start_date: null, end_date: null, home_currency: "USD", my_role: "owner", destinations: [], travelers: [] };
const signIn = async (page: import("@playwright/test").Page) => {
  await page.goto("/sign-in");
  await page.getByRole("button", { name: "Free user" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Trips" })).toBeVisible();
};

test("a trip route shows the error state on a 500, and Try again recovers", async ({ page }) => {
  let fail = true;
  await page.route("**/v1/trips/t1", (r) => (fail ? r.fulfill({ status: 500, json: {} }) : r.fulfill({ json: trip })));
  await signIn(page);
  await page.goto("/trips/t1");
  await expect(page.getByRole("alert").getByText("We could not load this trip. Try again.", { exact: true })).toBeVisible({ timeout: 10_000 });
  fail = false;
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Lisbon" })).toBeVisible();
  await expect(page.getByRole("alert")).toHaveCount(0);
});

test("a trip route shows the offline state when the connection drops", async ({ page, context }) => {
  await page.route("**/v1/trips/t1", (r) => r.fulfill({ json: trip }));
  await signIn(page);
  await page.goto("/trips/t1");
  await expect(page.getByRole("heading", { level: 1, name: "Lisbon" })).toBeVisible();
  await context.setOffline(true);
  await expect(page.getByRole("status")).toContainText("offline");
});

test("a trip fetch that fails while offline shows the offline sentence", async ({ page, context }) => {
  await page.route("**/v1/trips/t1", (r) => r.fulfill({ status: 500, json: {} }));
  await signIn(page);
  await page.goto("/trips/t1");
  await expect(page.getByRole("alert").getByText("We could not load this trip. Try again.", { exact: true })).toBeVisible({ timeout: 10_000 });
  await context.setOffline(true);
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(page.getByRole("alert").getByText("You are offline. Your trip is saved on this phone. Changes will sync when you reconnect.", { exact: true })).toBeVisible({ timeout: 10_000 });
});
