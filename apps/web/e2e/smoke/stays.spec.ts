import { expect, test, type Browser, type Page } from "@playwright/test";

const API = "http://localhost:8100";

async function signIn(page: Page, label: string) {
  await page.goto("/sign-in");
  await page.getByRole("button", { name: label }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Trips" })).toBeVisible();
  const auth = await page.evaluate(() => sessionStorage.getItem("hermi.auth"));
  return (JSON.parse(auth ?? "{}") as { token: string }).token;
}

async function archive(page: Page, auth: Record<string, string>, tripId: string) {
  const now = (await (await page.request.get(`${API}/v1/trips/${tripId}`, { headers: auth })).json()) as { version: number };
  await page.request.patch(`${API}/v1/trips/${tripId}`, { headers: { ...auth, "If-Match": `"${now.version}"` }, data: { status: "archived" } });
}

// Smoke flow 5 (10 section 1.6, WF-034.3): heart a stay in both browser contexts; the tally updates within 30 seconds through polling.
// The Free owner invites the Admin persona (a Free account) by link. The trip is archived at the end so reruns stay under the Free trip limit.
test("flow 5: a heart in one context shows in the other within 30 seconds", async ({ page, browser }: { page: Page; browser: Browser }) => {
  test.setTimeout(120_000);
  const token = await signIn(page, "Free user");
  const auth = { Authorization: `Bearer ${token}` };
  const made = await page.request.post(`${API}/v1/trips`, { headers: auth, data: { name: `Hearts ${Date.now()}` } });
  expect(made.status()).toBe(201);
  const trip = (await made.json()) as { id: string };
  const guestCtx = await browser.newContext({ viewport: { width: 390, height: 844 } });
  try {
    const stay = await page.request.post(`${API}/v1/trips/${trip.id}/lodging`, { headers: auth, data: { title: "Casita with volcano view", url: "https://www.airbnb.com/rooms/123?adults=2", added_via: "paste", price_per_night: { amount_minor: 14200, currency: "USD" } } });
    expect(stay.status()).toBe(201);
    await page.goto(`/trips/${trip.id}/group?invite=1`);
    const sent = page.waitForResponse((r) => r.url().endsWith(`/v1/trips/${trip.id}/invites`) && r.request().method() === "POST");
    await page.getByRole("button", { name: "Share invite link" }).click();
    const invite = (await (await sent).json()) as { url: string };
    const guest = await guestCtx.newPage();
    await signIn(guest, "Admin");
    await guest.goto(new URL(invite.url).pathname);
    await guest.getByRole("button", { name: "Join trip" }).click();
    await expect(guest.getByText(/Hearts \d+/).first()).toBeVisible();

    await page.goto(`/trips/${trip.id}/stays`);
    await guest.goto(`/trips/${trip.id}/stays`);
    const heart = (p: Page) => p.getByRole("button", { name: /^You love this/ });
    const tally = (p: Page) => p.getByRole("button", { name: /like this$|No hearts yet$/ });

    await heart(page).click();
    await expect(heart(page)).toHaveAttribute("aria-pressed", "true");
    // The guest sees the owner's heart by polling (15 s), with no reload.
    await expect(tally(guest)).toHaveText(/^1 of \d like this$/, { timeout: 30_000 });
    await heart(guest).click();
    await expect(heart(guest)).toHaveAttribute("aria-pressed", "true");
    await expect(tally(guest)).toHaveText(/^2 of 2 like this$/);
    await expect(tally(page)).toHaveText(/^2 of 2 like this$/, { timeout: 30_000 });
    // A second heart from the same member changes nothing: it is a toggle, so tapping again removes it.
    await heart(guest).click();
    await expect(tally(guest)).toHaveText(/^1 of \d like this$/);
  } finally {
    await guestCtx.close();
    await archive(page, auth, trip.id);
  }
});

// Smoke flow 21 (10 section 1.6, WF-034.3): paste a stay link, heart it, compare two to four stays, mark one Booked.
// The Plus persona is used because Free compares two stays at once (the API refuses a third with 402).
test("flow 21: paste a link, heart it, compare four stays and mark one Booked", async ({ page }: { page: Page }) => {
  const token = await signIn(page, "Plus user");
  const auth = { Authorization: `Bearer ${token}` };
  const made = await page.request.post(`${API}/v1/trips`, { headers: auth, data: { name: `Stays ${Date.now()}`, start_date: "2027-11-27", end_date: "2027-12-01" } });
  expect(made.status()).toBe(201);
  const trip = (await made.json()) as { id: string };
  try {
    for (const [n, title] of ["Hotel near the hot springs", "Treehouse lodge", "Lake cabin"].entries()) {
      const r = await page.request.post(`${API}/v1/trips/${trip.id}/lodging`, { headers: auth, data: { title, added_via: "manual", price_per_night: { amount_minor: 12100 + n * 3000, currency: "USD" } } });
      expect(r.status()).toBe(201);
    }
    await page.goto(`/trips/${trip.id}/stays`);
    await expect(page.getByText("Sorted by hearts, most first")).toBeVisible();

    // Paste a link. It is saved exactly as typed, and the helper says no page is loaded.
    const typed = "https://www.airbnb.com/rooms/123?check_in=2027-11-27&check_out=2027-12-01&utm_source=abc";
    await page.getByRole("button", { name: "Add a stay" }).first().click();
    const dialog = page.getByRole("dialog", { name: "Add a stay" });
    await expect(dialog.getByText("We never change your links and never load these pages.")).toBeVisible();
    await dialog.getByLabel("Link").fill(typed);
    await dialog.getByLabel("Name").fill("Casita with volcano view");
    await dialog.getByLabel("Price per night").fill("142");
    await dialog.getByRole("button", { name: "Save stay" }).click();
    await expect(dialog).toBeHidden();
    const casita = page.getByRole("article", { name: /^Casita with volcano view/ });
    await expect(casita.getByText("$142")).toBeVisible();
    await expect(casita.getByRole("link", { name: "Open Casita with volcano view" })).toHaveAttribute("href", typed);

    // Heart it.
    await casita.getByRole("button", { name: /^You love this/ }).click();
    await expect(casita.getByRole("button", { name: /^You love this/ })).toHaveAttribute("aria-pressed", "true");
    await expect(casita.getByRole("button", { name: /1 of \d like this/ })).toBeVisible();

    // Compare four stays.
    for (const title of ["Casita with volcano view", "Hotel near the hot springs", "Treehouse lodge", "Lake cabin"]) await page.getByRole("checkbox", { name: `Compare ${title}` }).check();
    await page.getByRole("button", { name: "Compare (4)" }).click();
    const table = page.getByRole("table", { name: "Compare stays" });
    await expect(table.getByRole("columnheader")).toHaveCount(5);
    await expect(table.getByRole("row", { name: /Price per night/ }).getByText("Lowest")).toBeVisible();
    await page.getByRole("button", { name: "Back to the list" }).click();

    // Mark exactly one Booked.
    await page.getByRole("button", { name: "Mark Casita with volcano view as booked" }).click();
    await expect(casita.getByText("Booked")).toBeVisible();
    await expect(page.getByRole("button", { name: /^Mark .* as booked$/ })).toHaveCount(0);
    await page.screenshot({ path: "test-results/stays-phone.png" });
    await page.evaluate(() => document.documentElement.classList.add("dark"));
    await page.screenshot({ path: "test-results/stays-phone-dark.png" });
  } finally {
    await archive(page, auth, trip.id);
  }
});

// WF-034.3: the error and offline states, with the API stubbed so the test owns the state.
const stub = { id: "t1", version: 1, name: "Lisbon", status: "planning", start_date: "2027-05-01", end_date: "2027-05-02", home_currency: "USD", my_role: "owner", destinations: [], travelers: [] };

test("Stays: a failed load says so with a retry, and offline the list stays readable", async ({ page, context }) => {
  await page.route("**/v1/trips/t1", (r) => r.fulfill({ json: stub }));
  let fail = true;
  await page.route("**/v1/trips/t1/lodging?**", (r) =>
    fail
      ? r.fulfill({ status: 500, json: { code: "internal_error", detail: "x" } })
      : r.fulfill({ json: { items: [{ id: "s1", trip_id: "t1", title: "Casita", url: null, site: null, check_in: null, check_out: null, nights: null, price_total: null, price_per_night: { amount_minor: 14200, currency: "USD" }, bedrooms: null, rating: null, notes: "", status: "shortlisted", added_via: "manual", version: 1, votes: [], vote_summary: { hearts: 0 } }], next_cursor: null, has_more: false, sorted_by: "votes" } }),
  );
  await signIn(page, "Free user");
  await page.goto("/trips/t1/stays");
  await expect(page.getByRole("alert").getByText("We could not load your stays. Try again.", { exact: true })).toBeVisible();
  fail = false;
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(page.getByRole("article", { name: /^Casita/ })).toBeVisible();
  await context.setOffline(true);
  await expect(page.getByRole("status").filter({ hasText: "Offline. You can read your stays. Reconnect to add or change them." })).toBeVisible();
  await expect(page.getByRole("article", { name: /^Casita/ })).toBeVisible();
  await expect(page.getByRole("button", { name: "Add a stay" })).toBeDisabled();
});
