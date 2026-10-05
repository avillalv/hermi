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

// WF-030.4: a fare chip opens Fare detail; its error has a retry and offline disables booking.
test("Fare detail opens from a chip, errors with Try again, and disables booking offline", async ({ page, context }) => {
  const now = new Date().toISOString();
  const route = { id: "r1", trip_id: "t1", label: null, origin_codes: ["JFK"], destination_codes: ["LIS"], trip_type: "round_trip", depart_from: "2027-03-12", depart_to: "2027-03-12", return_from: "2027-03-19", return_to: "2027-03-19", adults: 1, children: 0, mode: "cached", version: 1, last_checked_at: now };
  const fare = { id: "f1", route_id: "r1", source: "travelpayouts", confidence: "cached", origin: "JFK", destination: "LIS", depart_date: "2027-03-12", return_date: "2027-03-19", price: { amount_minor: 41200, currency: "USD" }, passengers: 1, airlines: ["TP"], stops_out: 0, stops_back: 0, duration_out_min: 420, depart_at_local: "2027-03-12T21:10", source_url: null, observed_at: now, age_label: "cached just now" };
  let fail = true;
  await page.route("**/v1/trips/t1", (r) => r.fulfill({ json: trip }));
  await page.route("**/v1/trips/t1/routes", (r) => r.fulfill({ json: [route] }));
  await page.route("**/v1/trips/t1/flights/summary", (r) => r.fulfill({ json: [{ route_id: "r1", cheapest: fare, last_checked_at: now, fare_count: 1, chosen: null, chosen_latest: null }] }));
  await page.route("**/v1/trips/t1/routes/r1/price-history", (r) => r.fulfill({ json: { currency: "USD", google: [], points: [] } }));
  await page.route("**/v1/trips/t1/routes/r1/date-grid", (r) => r.fulfill({ json: [] }));
  await page.route("**/v1/trips/t1/routes/r1/fares**", (r) => (fail ? r.fulfill({ status: 500, json: {} }) : r.fulfill({ json: { items: [fare], next_cursor: null, has_more: false } })));
  await page.goto("/sign-in");
  await page.getByRole("button", { name: "Free user" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Trips" })).toBeVisible();
  await page.goto("/trips/t1/flights");
  await page.getByRole("button", { name: /LIS.*\$412/ }).click();
  await expect(page).toHaveURL(/\/trips\/t1\/flights\/r1\/fares\/f1$/);
  await expect(page.getByText("We could not load this fare. Try again.")).toBeVisible({ timeout: 10_000 });
  fail = false;
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(page.getByRole("heading", { level: 1, name: /^JFK to LIS/ })).toBeVisible();
  await context.setOffline(true);
  await expect(page.getByText("Connect to the internet to book.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Mark as booked" })).toBeDisabled();
});
