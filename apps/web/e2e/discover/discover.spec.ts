import { expect, test, type Page } from "@playwright/test";

// WF-133.3: Discover states with the API stubbed, so the test owns each state. Needs `npm run dev` for the web app only.
const card = { slug: "lisbon-5-days", title: "Lisbon in 5 days", destination_name: "Lisbon", days: 5, summary: "s", cover: null, tags: ["city"], suits: "Food lovers" };
const sample = {
  slug: "lisbon-5-days",
  title: "Lisbon in 5 days",
  summary: "Tiles and tram rides.",
  updated_at: "2026-09-12T10:00:00Z",
  presentation: {
    trip: { name: "Lisbon in 5 days", destinations: [{ name: "Lisbon" }] },
    days: [{ day: "2027-03-12", title: "Alfama", destination_name: "Lisbon", items: [{ id: "i1", start_time: "10:00:00", title: "Castelo walk", category: "activity", location_name: "Alfama", estimated_cost_minor: null, cost_currency: null, check_url: null, checked_at: null }] }],
    stays: [],
  },
};
const signIn = async (page: Page) => {
  await page.goto("/sign-in");
  await page.getByRole("button", { name: "Free user" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Trips" })).toBeVisible();
};
const stub = async (page: Page) => {
  await page.route((u) => u.pathname === "/v1/public/sample-trips", (r) => r.fulfill({ json: { items: [card], next_cursor: null, has_more: false } }));
  await page.route("**/v1/public/sample-trips/lisbon-5-days", (r) => r.fulfill({ json: sample }));
};

test("the gallery shows an error on a 500, and Try again recovers", async ({ page }) => {
  let fail = true;
  await page.route((u) => u.pathname === "/v1/public/sample-trips", (r) => (fail ? r.fulfill({ status: 500, json: {} }) : r.fulfill({ json: { items: [card], next_cursor: null, has_more: false } })));
  await page.goto("/discover");
  await expect(page.getByRole("alert").getByText("We could not load examples. Pull down to try again.", { exact: true })).toBeVisible({ timeout: 10_000 });
  fail = false;
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(page.getByRole("link", { name: /Lisbon in 5 days/ })).toBeVisible();
});

test("offline, a sample already opened stays readable and Use this plan is disabled", async ({ page, context }) => {
  await stub(page);
  await signIn(page);
  await page.goto("/discover/lisbon-5-days");
  await expect(page.getByRole("heading", { level: 1, name: "Lisbon in 5 days" })).toBeVisible();
  await context.setOffline(true);
  await expect(page.getByRole("status")).toContainText("offline");
  await expect(page.getByRole("button", { name: "Use this plan" })).toBeDisabled();
});

test("a 402 limit_reached shows the third trip paywall with the free path first", async ({ page }) => {
  await stub(page);
  await page.route("**/copy", (r) => r.fulfill({ status: 402, json: { code: "limit_reached" } }));
  await signIn(page);
  await page.goto("/discover/lisbon-5-days");
  await page.getByRole("button", { name: "Use this plan" }).click();
  const dialog = page.getByRole("dialog", { name: "Two trips are active" });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole("link", { name: "Archive a trip" })).toBeVisible();
});

test("a guest builds the local guest trip and makes no server write", async ({ page }) => {
  await stub(page);
  const writes: string[] = [];
  page.on("request", (r) => r.method() === "POST" && writes.push(r.url()));
  await page.goto("/discover/lisbon-5-days");
  await page.getByRole("button", { name: "Use this plan" }).click();
  await expect(page).toHaveURL(/\/guest-trip$/);
  await expect(page.getByText("Guest trip, saved on this phone")).toBeVisible();
  await expect(page.getByRole("heading", { level: 1, name: "Lisbon in 5 days" })).toBeVisible();
  expect(writes.filter((u) => u.includes("/v1/"))).toEqual([]);
});
