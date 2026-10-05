import { expect, test, type Page } from "@playwright/test";

const API = "http://localhost:8100";

async function signIn(page: Page, label: string) {
  await page.goto("/sign-in");
  await page.getByRole("button", { name: label }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Trips" })).toBeVisible();
  const auth = await page.evaluate(() => sessionStorage.getItem("hermi.auth"));
  return (JSON.parse(auth ?? "{}") as { token: string }).token;
}

// Smoke flow 22 (10 section 1.6, WF-033.2): drag items onto days, then use Add activity with place search and the map.
// The API runs on the recorded Geoapify fixtures (PROVIDERS_MODE=fake), so "belem" finds Belem Tower with no network.
// The trip is archived at the end so reruns on the same dev database stay under the Free active-trip limit.
test("drag items onto days, then add a place from search and see it on the map", async ({ page }) => {
  const token = await signIn(page, "Free user");
  const auth = { Authorization: `Bearer ${token}` };
  const made = await page.request.post(`${API}/v1/trips`, {
    headers: auth,
    data: {
      name: `Places ${Date.now()}`,
      start_date: "2027-05-01",
      end_date: "2027-05-03",
      destinations: [{ name: "Lisbon", country: "Portugal", country_code: "PT", lat: 38.72, lon: -9.14, timezone: "Europe/Lisbon" }],
    },
  });
  expect(made.status()).toBe(201);
  const trip = (await made.json()) as { id: string };
  try {
    for (const title of ["Fado night", "Tram 28"]) {
      const r = await page.request.post(`${API}/v1/trips/${trip.id}/items`, { headers: auth, data: { title, category: "sights" } });
      expect(r.status()).toBe(201);
    }
    await page.goto(`/trips/${trip.id}/plan`);
    // Drag both ideas onto day 2, then check day 2 holds them.
    await page.getByRole("tab", { name: /^Ideas/ }).click();
    for (const title of ["Fado night", "Tram 28"]) {
      await page.locator("li.h-timeline__row", { hasText: title }).dragTo(page.getByRole("tab", { name: /^Day 2/ }));
      await expect(page.locator("li.h-timeline__row", { hasText: title })).toHaveCount(0);
    }
    await page.getByRole("tab", { name: /^Day 2/ }).click();
    await expect(page.getByRole("heading", { level: 3, name: "Fado night" })).toBeVisible();
    await expect(page.getByRole("heading", { level: 3, name: "Tram 28" })).toBeVisible();

    // Add activity: search, open the result, add it to day 2.
    await page.getByRole("button", { name: "Add item" }).click();
    await page.getByRole("searchbox", { name: "Search places" }).fill("belem");
    await page.getByRole("button", { name: "Search", exact: true }).click();
    await page.getByRole("option", { name: /Belem Tower/ }).click();
    await expect(page.getByText("Text from Wikipedia, CC BY-SA 4.0")).toBeVisible();
    await page.getByRole("button", { name: "Add Belem Tower to Day 2" }).click();
    await expect(page.getByRole("heading", { level: 3, name: "Belem Tower" })).toBeVisible();

    // The map: the list always shows the place; the canvas shows when the browser has WebGL.
    await page.getByRole("tab", { name: "Map" }).click();
    await expect(page.getByRole("button", { name: /^Belem Tower/ })).toBeVisible();
    await expect(page.getByRole("link", { name: "Open in Apple Maps" })).toHaveAttribute("href", /maps\.apple\.com\/\?ll=38\.6916%2C-9\.216&q=Belem\+Tower/);
    await expect(page.getByRole("link", { name: "Open in Google Maps" })).toBeVisible();
    await expect(page.getByText("Map data © OpenStreetMap contributors")).toBeVisible();
    await page.screenshot({ path: "test-results/places-map-phone.png" });
  } finally {
    const now = (await (await page.request.get(`${API}/v1/trips/${trip.id}`, { headers: auth })).json()) as { version: number };
    const done = await page.request.patch(`${API}/v1/trips/${trip.id}`, { headers: { ...auth, "If-Match": `"${now.version}"` }, data: { status: "archived" } });
    expect(done.ok()).toBe(true);
  }
});

// WF-033.2: the map's offline state and the search error, with the API stubbed so the test owns the state.
const stub = { id: "t1", version: 1, name: "Lisbon", status: "planning", start_date: "2027-05-01", end_date: "2027-05-02", home_currency: "USD", my_role: "owner", destinations: [{ id: "d1", position: 0, name: "Lisbon", region: null, country: "Portugal", timezone: null, lat: 38.72, lon: -9.14 }], travelers: [] };
const day = { day: "2027-05-01", title: "", notes: "", destination_id: null, destination_name: null, timezone: null, in_trip: true, item_count: 1, version: 0, first: null, last: null };
const item = { id: "i1", trip_id: "t1", title: "Castle", day: "2027-05-01", start_time: null, end_time: null, category: "sights", status: "idea", notes: "", sort_order: 1, version: 1, added_by: null, lat: 38.71, lon: -9.13, address: null };
async function plan(page: Page) {
  await page.route("**/v1/trips/t1", (r) => r.fulfill({ json: stub }));
  await page.route("**/v1/trips/t1/days", (r) => r.fulfill({ json: [day] }));
  await page.route("**/v1/trips/t1/items**", (r) => r.fulfill({ json: { items: [item], next_cursor: null, has_more: false } }));
  await page.route("**/v1/trips/t1/saved-places**", (r) => r.fulfill({ json: { items: [], next_cursor: null, has_more: false } }));
  await signIn(page, "Free user");
  await page.goto("/trips/t1/plan");
}

test("Add activity: a failed search says so and offers Add by hand", async ({ page }) => {
  await plan(page);
  await page.route("**/v1/places/search**", (r) => r.fulfill({ status: 503, json: { code: "provider_unavailable", detail: "x" } }));
  await page.getByRole("button", { name: "Add item" }).click();
  await page.getByRole("searchbox", { name: "Search places" }).fill("belem");
  await page.getByRole("button", { name: "Search", exact: true }).click();
  await expect(page.getByRole("alert")).toHaveText("Place search is not working right now. Add it by hand and we will match it later.");
  await page.getByRole("button", { name: "Add by hand" }).click();
  await expect(page.getByLabel("Title")).toBeVisible();
});

test("Map: offline the map is not started and the list stays", async ({ page, context }) => {
  await plan(page);
  await page.getByRole("tab", { name: "Map" }).click();
  await expect(page.getByRole("button", { name: /^Castle/ })).toBeVisible();
  await context.setOffline(true);
  await expect(page.getByRole("status").filter({ hasText: "Maps need a connection. Your list is below." })).toBeVisible();
  await expect(page.getByRole("button", { name: /^Castle/ })).toBeVisible();
});
