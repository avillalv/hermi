import { expect, test, type Page } from "@playwright/test";

const API = "http://localhost:8100";

async function signIn(page: Page, label: string) {
  await page.goto("/sign-in");
  await page.getByRole("button", { name: label }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Trips" })).toBeVisible();
  const auth = await page.evaluate(() => sessionStorage.getItem("hermi.auth"));
  return (JSON.parse(auth ?? "{}") as { token: string }).token;
}

// Smoke flow 2 (10 section 1.6, WF-032.2): a trip with two destinations, an item added by hand, a reload, and it is still there.
// The trip is archived at the end so reruns on the same dev database stay under the Free active-trip limit.
test("create a trip with two destinations, add an itinerary item, reload, and it persists", async ({ page }) => {
  const token = await signIn(page, "Free user");
  const auth = { Authorization: `Bearer ${token}` };
  const made = await page.request.post(`${API}/v1/trips`, {
    headers: auth,
    data: {
      name: `Plan ${Date.now()}`,
      start_date: "2027-05-01",
      end_date: "2027-05-03",
      destinations: [
        { name: "Lisbon", country: "Portugal", country_code: "PT", lat: 38.72, lon: -9.14, timezone: "Europe/Lisbon" },
        { name: "Porto", country: "Portugal", country_code: "PT", lat: 41.15, lon: -8.61, timezone: "Europe/Lisbon" },
      ],
    },
  });
  expect(made.status()).toBe(201);
  const trip = (await made.json()) as { id: string; version: number; destinations: unknown[] };
  expect(trip.destinations).toHaveLength(2);
  try {
    await page.goto(`/trips/${trip.id}/plan`);
    await expect(page.getByText("Nothing planned yet")).toBeVisible();
    await page.getByRole("button", { name: "Add item" }).click();
    await page.getByLabel("Title").fill("Pasteis de Belem");
    await page.getByLabel("Category").selectOption("food");
    await page.getByRole("button", { name: "Add to plan" }).click();
    await expect(page.getByRole("heading", { level: 3, name: "Pasteis de Belem" })).toBeVisible();
    await page.reload();
    await expect(page.getByRole("heading", { level: 3, name: "Pasteis de Belem" })).toBeVisible();
    // The calendar file downloads.
    const saved = page.waitForEvent("download");
    await page.getByRole("button", { name: "Download calendar file" }).click();
    expect((await saved).suggestedFilename()).toMatch(/\.ics$/);
  } finally {
    // Read the current version first: nothing here edits the trip, but the cleanup must not depend on that.
    const now = (await (await page.request.get(`${API}/v1/trips/${trip.id}`, { headers: auth })).json()) as { version: number };
    const done = await page.request.patch(`${API}/v1/trips/${trip.id}`, { headers: { ...auth, "If-Match": `"${now.version}"` }, data: { status: "archived" } });
    expect(done.ok()).toBe(true);
  }
});

// WF-032.2: Plan error with retry, and offline. The trip, days and items calls are stubbed so the test owns the state.
const stub = { id: "t1", version: 1, name: "Lisbon", status: "planning", start_date: "2027-05-01", end_date: "2027-05-02", home_currency: "USD", my_role: "owner", destinations: [], travelers: [] };
const day = { day: "2027-05-01", title: "", notes: "", destination_id: null, destination_name: null, timezone: null, in_trip: true, item_count: 1, version: 0, first: null, last: null };
const item = { id: "i1", trip_id: "t1", title: "Castle", day: "2027-05-01", start_time: null, end_time: null, category: "sights", status: "idea", notes: "", sort_order: 1, version: 1, added_by: null };

test("Plan shows an error with Try again, then the day", async ({ page }) => {
  let fail = true;
  await page.route("**/v1/trips/t1", (r) => r.fulfill({ json: stub }));
  await page.route("**/v1/trips/t1/days", (r) => (fail ? r.fulfill({ status: 500, json: {} }) : r.fulfill({ json: [day] })));
  await page.route("**/v1/trips/t1/items**", (r) => r.fulfill({ json: { items: [item], next_cursor: null, has_more: false } }));
  await signIn(page, "Free user");
  await page.goto("/trips/t1/plan");
  await expect(page.getByRole("alert")).toHaveText("We could not load your plan. Try again.", { timeout: 10_000 });
  fail = false;
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(page.getByRole("heading", { level: 3, name: "Castle" })).toBeVisible();
});

test("Plan offline shows the read-only banner and disables rearranging", async ({ page, context }) => {
  await page.route("**/v1/trips/t1", (r) => r.fulfill({ json: stub }));
  await page.route("**/v1/trips/t1/days", (r) => r.fulfill({ json: [day] }));
  await page.route("**/v1/trips/t1/items**", (r) => r.fulfill({ json: { items: [item], next_cursor: null, has_more: false } }));
  await signIn(page, "Free user");
  await page.goto("/trips/t1/plan");
  await expect(page.getByRole("heading", { level: 3, name: "Castle" })).toBeVisible();
  await context.setOffline(true);
  await expect(page.getByRole("status")).toHaveText("Offline. You can read your plan. Reconnect to rearrange.");
  await expect(page.getByRole("button", { name: "Add item" })).toBeDisabled();
  await expect(page.getByRole("button", { name: "Move Castle" })).toBeDisabled();
});
