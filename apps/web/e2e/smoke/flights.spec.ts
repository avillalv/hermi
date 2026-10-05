import { expect, test } from "@playwright/test";

// WF-030.3: Flights error with retry, and offline. Needs `npm run dev`. The trip and route calls are stubbed so the test owns the state.
const trip = { id: "t1", version: 1, name: "Lisbon", status: "planning", start_date: null, end_date: null, home_currency: "USD", my_role: "owner", destinations: [], travelers: [] };

test("Flights shows an error with Try again, then the empty state", async ({ page }) => {
  let fail = true;
  await page.route("**/v1/trips/t1", (r) => r.fulfill({ json: trip }));
  await page.route("**/v1/trips/t1/routes", (r) => (fail ? r.fulfill({ status: 500, json: {} }) : r.fulfill({ json: [] })));
  await page.route("**/v1/trips/t1/flights/summary", (r) => r.fulfill({ json: [] }));
  await page.goto("/sign-in");
  await page.getByRole("button", { name: "Free user" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Trips" })).toBeVisible();
  await page.goto("/trips/t1/flights");
  await expect(page.getByRole("alert")).toHaveText("We could not load fares. Try again.", { timeout: 10_000 });
  fail = false;
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(page.getByText("No routes yet")).toBeVisible();
});

test("Flights offline shows the saved fares banner", async ({ page, context }) => {
  await page.route("**/v1/trips/t1", (r) => r.fulfill({ json: trip }));
  await page.route("**/v1/trips/t1/routes", (r) => r.fulfill({ json: [] }));
  await page.route("**/v1/trips/t1/flights/summary", (r) => r.fulfill({ json: [] }));
  await page.goto("/sign-in");
  await page.getByRole("button", { name: "Free user" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Trips" })).toBeVisible();
  await page.goto("/trips/t1/flights");
  await expect(page.getByText("No routes yet")).toBeVisible();
  await context.setOffline(true);
  await expect(page.getByRole("status")).toHaveText("You are offline. Showing the last saved fares with their age.");
});
