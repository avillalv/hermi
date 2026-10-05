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
  await expect(page.getByRole("alert").getByText("We could not load fares. Try again.", { exact: true })).toBeVisible({ timeout: 10_000 });
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
  await page.route("**/v1/trips/t1/price-alerts", (r) => r.fulfill({ json: [] }));
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
  await expect(page.getByRole("switch", { name: "Alert me when it drops" })).toBeDisabled();
});

// Smoke flow 20 (10 section 1.6, WF-031.2): add a route, see cached fares, choose a fare, set an alert.
// The dev API has no Travelpayouts token, so the flight calls are stubbed with a small stateful fake; sign-in and the shell are real.
test("flow 20: add a route, see cached fares, choose a fare, set an alert", async ({ page }) => {
  const now = new Date().toISOString();
  const route = { id: "r1", trip_id: "t1", label: null, origin_codes: ["JFK"], destination_codes: ["LIS"], trip_type: "round_trip", depart_from: "2027-03-12", depart_to: "2027-03-12", return_from: "2027-03-19", return_to: "2027-03-19", adults: 1, children: 0, cabin: "economy", mode: "cached", version: 1, last_checked_at: now };
  const fare = { id: "f1", route_id: "r1", source: "travelpayouts", confidence: "cached", origin: "JFK", destination: "LIS", depart_date: "2027-03-12", return_date: "2027-03-19", price: { amount_minor: 41200, currency: "USD" }, passengers: 1, airlines: ["TP"], stops_out: 0, stops_back: 0, duration_out_min: 420, depart_at_local: "2027-03-12T21:10", source_url: null, observed_at: now, age_label: "cached just now" };
  let added = false;
  let chosen: typeof fare | null = null;
  const alerts: unknown[] = [];
  await page.route("**/v1/trips/t1", (r) => r.fulfill({ json: trip }));
  await page.route("**/v1/trips/t1/routes", (r) => {
    if (r.request().method() === "POST") {
      added = true;
      return r.fulfill({ status: 201, json: route });
    }
    return r.fulfill({ json: added ? [route] : [] });
  });
  await page.route("**/v1/trips/t1/flights/refresh", (r) => r.fulfill({ status: 200, json: {} }));
  await page.route("**/v1/trips/t1/flights/summary", (r) => r.fulfill({ json: added ? [{ route_id: "r1", cheapest: fare, last_checked_at: now, fare_count: 1, chosen, chosen_latest: null }] : [] }));
  await page.route("**/v1/trips/t1/flights/best**", (r) => r.fulfill({ json: [fare] }));
  await page.route("**/v1/trips/t1/routes/r1/price-history", (r) => r.fulfill({ json: { currency: "USD", google: [], points: [] } }));
  await page.route("**/v1/trips/t1/routes/r1/date-grid", (r) => r.fulfill({ json: [] }));
  await page.route("**/v1/trips/t1/routes/r1/fares**", (r) => r.fulfill({ json: { items: [fare], next_cursor: null, has_more: false } }));
  await page.route("**/v1/trips/t1/routes/r1/choice", (r) => {
    chosen = fare;
    return r.fulfill({ json: trip });
  });
  await page.route("**/v1/trips/t1/price-alerts", (r) => r.fulfill({ json: alerts }));
  await page.route("**/v1/routes/r1/price-alerts", (r) => {
    const body = r.request().postDataJSON() as { target_price: unknown; notify: unknown };
    alerts.push({ id: "a1", route_id: "r1", target_price: body.target_price, notify: body.notify, active: true, last_notified_at: null, last_notified_price: null });
    return r.fulfill({ status: 201, json: alerts[0] });
  });
  await page.goto("/sign-in");
  await page.getByRole("button", { name: "Free user" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Trips" })).toBeVisible();
  await page.goto("/trips/t1/flights");
  await page.getByRole("button", { name: "Add a route" }).click();
  await page.getByLabel("From", { exact: true }).fill("JFK");
  await page.getByLabel("To", { exact: true }).fill("LIS");
  await page.getByLabel("Leave on").fill("2027-03-12");
  await page.getByLabel("Return on").fill("2027-03-19");
  await page.getByRole("button", { name: "Add route", exact: true }).click();
  await expect(page.getByRole("button", { name: /LIS.*\$412/ })).toBeVisible();
  await page.getByRole("tab", { name: "Options" }).click();
  await page.getByRole("button", { name: "Choose", exact: true }).click();
  await expect(page.getByText("Chosen", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: /LIS.*\$412/ }).first().click();
  await expect(page).toHaveURL(/\/trips\/t1\/flights\/r1\/fares\/f1$/);
  await page.getByRole("switch", { name: "Alert me when it drops" }).click();
  await page.getByLabel("Alert me when the lowest fare is below").fill("400");
  await page.getByRole("button", { name: "Save alert" }).click();
  await expect(page.getByText("Alert on. We will tell you if the lowest fare drops below $400.")).toBeVisible();
  await expect(page.getByRole("switch", { name: "Alert me when it drops" })).toHaveAttribute("aria-checked", "true");
});

// WF-031.2: the alert list errors with Try again, then recovers.
test("Flights alert list shows an error with Try again, then recovers", async ({ page }) => {
  const now = new Date().toISOString();
  const route = { id: "r1", trip_id: "t1", label: null, origin_codes: ["JFK"], destination_codes: ["LIS"], trip_type: "round_trip", depart_from: "2027-03-12", depart_to: "2027-03-12", return_from: "2027-03-19", return_to: "2027-03-19", adults: 1, children: 0, cabin: "economy", mode: "cached", version: 1, last_checked_at: now };
  let fail = true;
  await page.route("**/v1/trips/t1", (r) => r.fulfill({ json: trip }));
  await page.route("**/v1/trips/t1/routes", (r) => r.fulfill({ json: [route] }));
  await page.route("**/v1/trips/t1/flights/summary", (r) => r.fulfill({ json: [{ route_id: "r1", cheapest: null, last_checked_at: now, fare_count: 0, chosen: null, chosen_latest: null }] }));
  await page.route("**/v1/trips/t1/routes/r1/price-history", (r) => r.fulfill({ json: { currency: "USD", google: [], points: [] } }));
  await page.route("**/v1/trips/t1/price-alerts", (r) => (fail ? r.fulfill({ status: 500, json: {} }) : r.fulfill({ json: [] })));
  await page.goto("/sign-in");
  await page.getByRole("button", { name: "Free user" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Trips" })).toBeVisible();
  await page.goto("/trips/t1/flights");
  await expect(page.getByRole("alert").filter({ hasText: "We could not load alerts. Try again." }).first()).toBeVisible({ timeout: 10_000 });
  fail = false;
  await page.getByRole("button", { name: "Try again" }).first().click();
  await expect(page.getByText("No price alerts yet. Turn on the alert on a route to get one.")).toBeVisible();
});
