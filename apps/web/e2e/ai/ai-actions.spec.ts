import { expect, test, type Page } from "@playwright/test";

// WF-132.2 and WF-132.3: the AI action screens (explain, packing list, draft day, draft trip, research), credits history, the free repeat and the blurred day one at 0 credits.
// Needs `npm run dev` (API on fakes and web). The trip, the balance and the AI answers are stubbed so each test owns its state;
// the real fake-provider path, charges and the free repeat are covered by apps/api/tests/ai/test_ai_features.py.
// Run: npx playwright test --project ai
const trip = { id: "t1", version: 1, name: "Lisbon", status: "planning", start_date: "2027-05-01", end_date: "2027-05-05", home_currency: "USD", my_role: "owner", ai_enabled: true, destinations: [], travelers: [] };
const credits = (available: number) => ({ available, own: available, pool: 0, payer: "own", blocked: false, version: 1, total: available, monthly: available, trip_pass: 0, purchased: 0, next_monthly_grant_at: null });
const receipt = (over: Record<string, unknown> = {}) => ({ action: "explain", reserved: 1, charged: 1, from_cache: false, balance_after: 26, reservation_id: "r1", ...over });
const item = (n: number, day = "2027-05-01") => ({ title: `Stop ${n}`, day, start_time: "09:00", end_time: "10:00", category: "sights", status: "idea", location_name: "Alfama", notes: "", saved_place_id: null, verify: n === 2, source: "ai_draft" });

// Opens an AI screen and waits for the consent answer, so the first press is made when the gate knows what to do.
const openAi = async (page: Page, url: string) => {
  const answered = page.waitForResponse((r) => r.url().endsWith("/v1/me/consents") && r.request().method() === "GET");
  await page.goto(url);
  await answered;
};

const signIn = async (page: Page) => {
  await page.goto("/sign-in");
  await page.getByRole("button", { name: "Free user" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Trips" })).toBeVisible();
};

const stub = async (page: Page, available = 27) => {
  await page.route("**/v1/trips/t1", (r) => r.fulfill({ json: trip }));
  await page.route("**/v1/me/credits**", (r) => r.fulfill({ json: credits(available) }));
  await page.route("**/v1/me/consents", (r) => r.fulfill({ json: [{ kind: "ai_processing", version: "1", granted: true, accepted_at: "2027-01-01T00:00:00Z" }] }));
};

test("explain: ask, answer with the label, cost and thumbs; the same question again is a free repeat", async ({ page }) => {
  await stub(page);
  let asked = 0;
  await page.route("**/v1/trips/t1/ai/explain", (r) => {
    asked += 1;
    const free = asked > 1;
    return r.fulfill({
      json: {
        answer: "Alfama is hilly and best on foot.", confidence: "high", needs_source_check: false, sources: [], label: "AI suggestion", run_id: "run1",
        credits: receipt(free ? { reserved: 0, charged: 0, from_cache: true, reservation_id: null, balance_after: 26 } : {}),
      },
    });
  });
  await signIn(page);
  await page.goto("/trips/t1/ai/explain");
  await page.getByLabel("Your question").fill("Is Alfama hilly?");
  await expect(page.getByRole("button", { name: /^Ask, costs 1 credit/ })).toBeEnabled();
  await page.waitForTimeout(200);
  await page.getByRole("button", { name: /^Ask, costs 1 credit/ }).click();
  await expect(page.getByText("Alfama is hilly and best on foot.")).toBeVisible();
  await expect(page.getByText("AI suggestion, check details before booking")).toBeVisible();
  await expect(page.getByText("Used 1 credit. 26 left.")).toBeVisible();
  await expect(page.getByRole("group", { name: "Was this helpful?" })).toBeVisible();
  await page.getByRole("button", { name: "Ask another question" }).click();
  await page.getByLabel("Your question").fill("Is Alfama hilly?");
  await page.getByRole("button", { name: /^Ask, costs 1 credit/ }).click();
  await expect(page.getByText("Free repeat, no credits used.")).toBeVisible();
});

test("explain: the error state says nothing was charged and Try again recovers; offline disables Ask", async ({ page, context }) => {
  await stub(page);
  let fail = true;
  await page.route("**/v1/trips/t1/ai/explain", (r) =>
    fail
      ? r.fulfill({ status: 502, contentType: "application/problem+json", json: { code: "ai_failed" } })
      : r.fulfill({ json: { answer: "It is.", confidence: "high", needs_source_check: false, sources: [], label: "x", run_id: "run1", credits: receipt() } }),
  );
  await signIn(page);
  await page.goto("/trips/t1/ai/explain");
  await page.getByLabel("Your question").fill("Is it far?");
  await page.waitForTimeout(200);
  await page.getByRole("button", { name: /^Ask, costs 1 credit/ }).click();
  await expect(page.getByRole("alert").getByText("That did not work, and you were not charged. Try again.")).toBeVisible();
  fail = false;
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(page.getByText("It is.")).toBeVisible();
  await context.setOffline(true);
  await expect(page.getByRole("status").filter({ hasText: "AI needs a connection." })).toBeVisible();
  await expect(page.getByRole("button", { name: /^Ask, costs 1 credit/ })).toBeDisabled();
});

test("packing list: generate, tick lines", async ({ page }) => {
  await stub(page);
  await page.route("**/v1/trips/t1/ai/packing-list", (r) =>
    r.fulfill({ json: { items: [{ label: "Rain jacket", group: "clothing", qty: 1, reason: "Showers" }, { label: "Passport", group: "documents", qty: null, reason: null }], label: "x", run_id: "run2", credits: receipt() } }),
  );
  await signIn(page);
  await page.goto("/trips/t1/ai/packing");
  await expect(page.getByRole("button", { name: "Suggest a packing list, costs 1 credit" })).toBeEnabled();
  await page.waitForTimeout(200);
  await page.getByRole("button", { name: "Suggest a packing list, costs 1 credit" }).click();
  const clothing = page.getByRole("group", { name: "Clothing" });
  await expect(clothing.getByRole("checkbox", { name: /Rain jacket/ })).toBeVisible();
  await clothing.getByRole("checkbox", { name: /Rain jacket/ }).check();
  await expect(page.getByRole("group", { name: "Documents" })).toBeVisible();
});

test("draft day: preview, pick one item, add it to the plan", async ({ page }) => {
  await stub(page);
  await page.route("**/v1/trips/t1/ai/draft-day", (r) =>
    r.fulfill({ json: { day: "2027-05-01", title: "Old town", items: [item(1), item(2)], rationale: "Close together.", label: "x", run_id: "run3", credits: receipt({ action: "draft_day" }) } }),
  );
  let saved: { source: string; items: { title: string }[] } | null = null;
  await page.route("**/v1/trips/t1/items/bulk", (r) => {
    saved = r.request().postDataJSON();
    return r.fulfill({ status: 201, json: [] });
  });
  await signIn(page);
  await page.goto("/trips/t1/ai/day");
  await expect(page.getByRole("button", { name: /^Draft, costs 1 credit/ })).toBeEnabled();
  await page.waitForTimeout(200);
  await page.getByRole("button", { name: /^Draft, costs 1 credit/ }).click();
  await expect(page.getByText("Check hours before you go")).toBeVisible();
  await page.getByRole("checkbox", { name: /Stop 2/ }).check();
  await page.getByRole("button", { name: "Add picked (1)" }).click();
  await expect(page.getByText("Added 1 item to your plan.")).toBeVisible();
  expect(saved).toMatchObject({ source: "ai_draft", items: [{ title: "Stop 2" }] });
});

test("draft trip: preview by days and Accept all", async ({ page }) => {
  await stub(page);
  await page.route("**/v1/trips/t1/ai/draft-trip", (r) =>
    r.fulfill({
      status: 202,
      json: {
        id: "run4", kind: "draft_trip", status: "done", error_code: null, credits: receipt({ action: "draft_trip", reserved: 4, charged: 4, balance_after: 23 }),
        result: { days: [1, 2].map((d) => ({ day: `2027-05-0${d}`, title: `Day ${d}`, rationale: "", items: [item(d, `2027-05-0${d}`)] })), overview: "A slow week.", label: "x" },
      },
    }),
  );
  await page.route("**/v1/trips/t1/items/bulk", (r) => r.fulfill({ status: 201, json: [] }));
  await signIn(page);
  await page.goto("/trips/t1/ai/trip");
  await expect(page.getByRole("button", { name: /^Draft, costs 4 credits/ })).toBeEnabled();
  await page.waitForTimeout(200);
  await page.getByRole("button", { name: /^Draft, costs 4 credits/ }).click();
  await expect(page.getByText("A slow week.")).toBeVisible();
  await expect(page.getByText("Used 4 credits. 23 left.")).toBeVisible();
  await page.getByRole("button", { name: "Accept all" }).click();
  await expect(page.getByText("Added 2 items to your plan.")).toBeVisible();
});

test("draft trip at 0 credits: day one is blurred behind the out of credits offer, with the free path", async ({ page }) => {
  await stub(page, 0);
  await signIn(page);
  await page.goto("/trips/t1/ai/trip");
  const over = page.getByText("Add credits and Hermi drafts your days here.");
  await expect(over).toBeVisible();
  const filter = await page.locator(".ai-locked__preview").evaluate((el) => getComputedStyle(el).filter);
  expect(filter).toContain("blur");
  await expect(page.getByRole("heading", { name: "You are out of credits" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Write it myself" })).toBeVisible();
  await expect(page.getByText("You can add credits or upgrade in the iOS app.")).toBeVisible();
  await expect(page.getByRole("button", { name: /^Draft, costs 4 credits/ })).toBeEnabled();
});

const note = (n: number) => ({ title: `Marathon closes road ${n}`, topic: "events_and_closures", body: `The marathon closes the riverfront on 9 May ${n}.`, urls: [`https://events.example.org/lisbon-${n}`] });
const job = (over: Record<string, unknown> = {}) => ({
  id: "run5", kind: "research", status: "done", error_code: null, credits: receipt({ action: "research", reserved: 8, charged: 8, balance_after: 19 }),
  result: { topic: "events_and_closures", notes: [note(1), note(2)], sources: [], from_cache: false, stale: false, checked_days_ago: null, label: "AI suggestion" },
  ...over,
});

test("research: pick a topic, read sourced notes with the label, the cost and thumbs", async ({ page }) => {
  await stub(page);
  let body: unknown = null;
  await page.route("**/v1/trips/t1/ai/research", (r) => {
    body = r.request().postDataJSON();
    return r.fulfill({ status: 202, json: job() });
  });
  await signIn(page);
  await openAi(page, "/trips/t1/ai/research");
  await expect(page.getByText("Costs 8 credits. You have 27, so 19 left.")).toBeVisible();
  await page.getByLabel("Topic").selectOption("events_and_closures");
  await expect(page.getByRole("button", { name: /^Research, costs 8 credits/ })).toBeEnabled();
  await page.getByRole("button", { name: /^Research, costs 8 credits/ }).click();
  await expect(page.getByRole("heading", { name: "Marathon closes road 1" })).toBeVisible();
  expect(body).toEqual({ topic: "events_and_closures" });
  await expect(page.getByRole("link", { name: /events\.example\.org/ }).first()).toHaveAttribute("href", "https://events.example.org/lisbon-1");
  await expect(page.getByText("AI suggestion, check details before booking")).toBeVisible();
  await expect(page.getByText("Used 8 credits. 19 left.")).toBeVisible();
  await expect(page.getByRole("group", { name: "Was this helpful?" })).toBeVisible();
});

test("research: the error state says nothing was charged, and offline disables the button", async ({ page, context }) => {
  await stub(page);
  let fail = true;
  await page.route("**/v1/trips/t1/ai/research", (r) =>
    fail ? r.fulfill({ status: 502, contentType: "application/problem+json", json: { code: "ai_failed" } }) : r.fulfill({ status: 202, json: job() }),
  );
  await signIn(page);
  await openAi(page, "/trips/t1/ai/research");
  await expect(page.getByRole("button", { name: /^Research, costs 8 credits/ })).toBeEnabled();
  await page.getByRole("button", { name: /^Research, costs 8 credits/ }).click();
  await expect(page.getByRole("alert").getByText("That did not work, and you were not charged. Try again.")).toBeVisible();
  fail = false;
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(page.getByRole("heading", { name: "Marathon closes road 1" })).toBeVisible();
  await page.getByRole("button", { name: "Research another topic" }).click();
  await context.setOffline(true);
  await expect(page.getByRole("status").filter({ hasText: "AI needs a connection." })).toBeVisible();
  await expect(page.getByRole("button", { name: /^Research, costs 8 credits/ })).toBeDisabled();
});

test("research at 3 credits: the free path first, no price, no purchase", async ({ page }) => {
  await stub(page, 3);
  await signIn(page);
  await openAi(page, "/trips/t1/ai/research");
  await expect(page.getByRole("heading", { name: "You are out of credits" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Write a note myself" })).toBeVisible();
  await expect(page.getByText("You can add credits or upgrade in the iOS app.")).toBeVisible();
});

const entry = (kind: string, delta: number, over: Record<string, unknown> = {}) => ({
  reservation_id: null, at: "2027-05-02T10:00:00Z", kind, delta, charged: null, action: null, trip_id: null, run_id: null, note: null, ...over,
});

test("credits history: balance by pool, spends and refund marks, newest first", async ({ page }) => {
  await page.route("**/v1/me/credits", (r) => r.fulfill({ json: { ...credits(19), monthly: 12, purchased: 7, next_monthly_grant_at: "2027-06-01T00:00:00Z" } }));
  await page.route("**/v1/me/credits/ledger**", (r) =>
    r.fulfill({
      json: {
        items: [
          entry("refund", 8, { action: "research", reservation_id: "r1", at: "2027-05-03T09:00:00Z" }),
          entry("reserve", -8, { action: "research", reservation_id: "r1", at: "2027-05-03T08:59:00Z" }),
          entry("settle", 0, { action: "research", reservation_id: "r1", charged: 0 }),
          entry("grant", 12, { at: "2027-05-01T00:00:00Z" }),
        ],
        next_cursor: null,
        has_more: false,
      },
    }),
  );
  await signIn(page);
  await page.goto("/account/credits");
  await expect(page.getByRole("heading", { name: "19 credits left" })).toBeVisible();
  await expect(page.getByText(/7 bought/)).toBeVisible();
  const rows = page.getByRole("list", { name: "Credit history" }).getByRole("listitem");
  await expect(rows).toHaveCount(3);
  await expect(rows.nth(0)).toContainText("Refund, 8 credits returned");
  await expect(rows.nth(1)).toContainText("-8");
  await expect(rows.nth(2)).toContainText("Credits added");
});

test("credits history: the error state recovers with Try again, and offline says to connect", async ({ page, context }) => {
  await page.route("**/v1/me/credits", (r) => r.fulfill({ json: credits(19) }));
  let fail = true;
  await page.route("**/v1/me/credits/ledger**", (r) => (fail ? r.fulfill({ status: 500, json: {} }) : r.fulfill({ json: { items: [entry("grant", 12)], next_cursor: null, has_more: false } })));
  await signIn(page);
  await page.goto("/account/credits");
  await expect(page.getByRole("alert").getByText("We could not load your credit history. Your credits have not changed. Try again.")).toBeVisible({ timeout: 15_000 });
  fail = false;
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(page.getByText("Credits added")).toBeVisible();
  await context.setOffline(true);
  await expect(page.getByRole("status").filter({ hasText: "Connect to see your credits." })).toBeVisible();
});
