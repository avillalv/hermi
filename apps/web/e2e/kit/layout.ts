import { expect, type Page } from "@playwright/test";

/** Signed-in main routes of WF-036.3, each rendered with populated fixtures that have long names. */
export const MAIN_ROUTES = [
  "/", "/discover", "/activity", "/account", "/trips/new", "/trips/t1", "/trips/t1/edit", "/trips/t1/flights", "/trips/t1/flights/r1/fares/f1",
  "/trips/t1/stays", "/trips/t1/notes", "/trips/t1/plan", "/trips/t1/group",
];
/** Routes that load without a session. */
export const PUBLIC_ROUTES = ["/welcome", "/sign-in", "/onboarding"];

const LONG = "A very long trip name for the Algarve and Lisbon coast with the whole family and friends";
const ago = (h: number) => new Date(Date.now() - h * 3600_000).toISOString();
const person = (id: string, name: string, me = false) => ({ id, name, color: "#2AA5FF", home_airports: ["JFK"], linked_user_id: me ? "u1" : null, is_me: me });
const trip = {
  id: "t1", version: 1, name: LONG, status: "planning", start_date: "2027-03-12", end_date: "2027-03-14", home_currency: "USD", my_role: "owner",
  destinations: [{ id: "d1", position: 0, name: "Praia da Marinha, Lagoa", region: "Algarve", country: "Portugal", timezone: "Europe/Lisbon", lat: 37.09, lon: -8.41 }],
  travelers: [person("p1", "Alexandria Montgomery-Featherstonehaugh", true), person("p2", "Bartholomew Wolfeschlegelsteinhausenberger")],
};
const summary = { id: "t1", version: 1, name: LONG, status: "planning", start_date: "2027-03-12", end_date: "2027-03-14", destinations_label: "Praia da Marinha, Lagoa, Portugal", member_count: 2, my_role: "owner" };
const route = {
  id: "r1", trip_id: "t1", label: null, origin_codes: ["JFK"], destination_codes: ["LIS"], trip_type: "round_trip", depart_from: "2027-03-12", depart_to: "2027-03-12",
  return_from: "2027-03-19", return_to: "2027-03-19", min_nights: null, max_nights: null, adults: 2, children: 0, cabin: "economy", max_stops: null, mode: "cached",
  active: true, version: 1, chosen_fare_id: null, last_checked_at: ago(3),
};
const fare = (id: string, cents: number) => ({
  id, route_id: "r1", source: "travelpayouts", confidence: "cached", origin: "JFK", destination: "LIS", depart_date: "2027-03-12", return_date: "2027-03-19",
  price: { amount_minor: cents, currency: "USD" }, passengers: 2, airlines: ["TP"], stops_out: 0, stops_back: 0, duration_out_min: 420, duration_back_min: 440,
  depart_at_local: "2027-03-12T21:10", source_url: null, observed_at: ago(3), age_label: "cached 3 h ago", suspect: false, hidden: false,
});
const fares = [fare("f1", 41200), fare("f2", 45800)];
const day = (d: string, n: number) => ({ day: d, title: "", notes: "", destination_id: null, destination_name: null, timezone: null, in_trip: true, item_count: n, version: 0, first: null, last: null });
const item = (id: string, title: string, d: string | null, o: Record<string, unknown> = {}) => ({
  id, trip_id: "t1", title, day: d, start_time: null, end_time: null, category: "sights", status: "idea", location_name: null, address: null, lat: null, lon: null, url: null,
  notes: "", cost: null, sort_order: 1, version: 1, source: "manual", bookable: false, added_by: { id: "u1", display_name: "Alexandria" },
  created_at: "2027-01-01T00:00:00Z", updated_at: "2027-01-01T00:00:00Z", ...o,
});
const stay = {
  id: "s1", trip_id: "t1", title: "Casa do Penedo with a sea view terrace and a very long listing title", url: null, site: null, check_in: "2027-03-12", check_out: "2027-03-14",
  nights: 2, price_total: { amount_minor: 52000, currency: "USD" }, price_per_night: { amount_minor: 26000, currency: "USD" }, bedrooms: 3, rating: 4.7, notes: "", status: "candidate",
  added_via: "manual", version: 1, votes: [], vote_summary: { hearts: 0 },
};
const note = {
  id: "n1", trip_id: "t1", kind: "user", title: "", body: "Book the cave boat tour early because it sells out and the harbour office closes at four in the afternoon.", pinned: false,
  is_private: false, day: null, item_id: null, version: 1, author: { id: "u1", display_name: "Alexandria Montgomery-Featherstonehaugh" }, sources: [], checked_at: ago(1), stale: false, created_at: ago(2),
};
const entry = { verb: "created", entity_type: "item", entity_id: "i1", summary: "Alexandria added Walk along the Seven Hanging Valleys trail", at: ago(1), actor: { id: "u1", display_name: "Alexandria Montgomery-Featherstonehaugh" } };
const page = (items: unknown[]) => ({ items, next_cursor: null, has_more: false });

/** The populated read model, keyed by API path. */
function populated(u: string): unknown {
  if (u === "/v1/me") return { id: "u1" };
  if (u === "/v1/me/entitlements") return { tier: "free", limits: { airports_per_side: 1, collaborators: 3 }, trip_passes: [] };
  if (u === "/v1/trips") return page([summary]);
  if (u === "/v1/trips/t1") return trip;
  if (u === "/v1/trips/t1/days") return [day("2027-03-12", 2), day("2027-03-13", 1), day("2027-03-14", 0)];
  if (u === "/v1/trips/t1/items") return page([item("i1", "Walk along the Seven Hanging Valleys trail to Benagil", "2027-03-12"), item("i2", "Lunch at the harbour", "2027-03-12", { category: "food", sort_order: 2 }), item("i3", "Fado night", "2027-03-13", { category: "nightlife" }), item("i4", "Maybe a boat trip", null)]);
  if (u === "/v1/trips/t1/routes") return [route];
  if (u === "/v1/trips/t1/flights/summary") return [{ route_id: "r1", cheapest: fares[0], last_checked_at: ago(3), fare_count: 2, chosen: null, chosen_latest: null }];
  if (u === "/v1/trips/t1/flights/best") return fares;
  if (u === "/v1/trips/t1/routes/r1/fares") return page(fares);
  if (u === "/v1/trips/t1/routes/r1/price-history") return { currency: "USD", google: [], points: [{ day: "2027-01-01", source: "travelpayouts", price: { amount_minor: 45000, currency: "USD" } }, { day: "2027-01-02", source: "travelpayouts", price: { amount_minor: 41200, currency: "USD" } }] };
  if (u === "/v1/trips/t1/routes/r1/date-grid") return [];
  if (u === "/v1/routes/r1/price-alerts" || u === "/v1/trips/t1/price-alerts") return [];
  if (u === "/v1/trips/t1/lodging") return { items: [stay], has_more: false, sorted_by: "votes" };
  if (u === "/v1/trips/t1/notes") return { items: [note], has_more: false, next_cursor: null };
  if (u === "/v1/trips/t1/activity") return page([entry]);
  if (u === "/v1/trips/t1/saved-places") return page([]);
  return undefined;
}

type Mode = { signedIn?: boolean; errors?: boolean };

/** Once per test: the session and the API stubs. `errors` makes every read fail (the separate error-state pass). */
export async function prepare(page: Page, { signedIn = true, errors = false }: Mode = {}) {
  if (signedIn) await page.addInitScript(() => sessionStorage.setItem("hermi.auth", JSON.stringify({ token: "dev-free", persona: "free" })));
  await page.route("**/v1/**", (r) => {
    const body = errors ? undefined : populated(new URL(r.request().url()).pathname);
    return body === undefined ? r.fulfill({ status: errors ? 500 : 404, json: {} }) : r.fulfill({ json: body });
  });
}

/** Opens a route in a color scheme and waits until it is rendered: a heading, no skeleton, and no error state unless `errors`. */
export async function visit(page: Page, path: string, scheme: "light" | "dark" = "light", { errors = false } = {}) {
  await page.emulateMedia({ colorScheme: scheme });
  await page.goto(path);
  await page.evaluate(() => document.fonts.ready);
  if (errors) await expect(page.getByRole("alert").first(), path).toBeVisible({ timeout: 10_000 });
  else {
    await expect(page.getByRole("heading", { level: 1 }).or(page.getByRole("heading", { level: 2 })).first(), path).toBeVisible({ timeout: 10_000 });
    await expect(page.getByRole("alert"), `${path} shows an error state`).toHaveCount(0);
    await expect(page.locator('[aria-busy="true"]'), `${path} still loading`).toHaveCount(0, { timeout: 10_000 });
  }
}

export const noHScroll = (page: Page) => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth);
