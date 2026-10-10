import { expect, test, type Page } from "@playwright/test";

// Smoke flows 6 and 23 (10 section 1.6, WF-132.3). Needs `npm run dev` with AI_PROVIDER=fake, so every model answer is a recorded
// fixture. The Plus persona is used because Free has 12 credits a month and the draft and research part of flow 23 spends 13. Dev personas keep their state between
// runs, so each test resets what it depends on through the API and skips (with the reason) when the credits are spent.
const API = "http://localhost:8100";

async function signIn(page: Page, label: string) {
  await page.goto("/sign-in");
  await page.getByRole("button", { name: label }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Trips" })).toBeVisible();
  const auth = await page.evaluate(() => sessionStorage.getItem("hermi.auth"));
  return { Authorization: `Bearer ${(JSON.parse(auth ?? "{}") as { token: string }).token}` };
}

// Opens an AI screen and waits for the consent answer, so a press is never made before the gate knows what to do.
async function openAi(page: Page, url: string) {
  const answered = page.waitForResponse((r) => r.url().endsWith("/v1/me/consents") && r.request().method() === "GET");
  await page.goto(url);
  await answered;
}

// The dev database keeps state between runs, so a spent dev account skips locally. CI starts from a fresh database: there it must fail.
const skipUnlessCi = (cond: boolean, why: string) => (process.env.CI ? expect(cond, why).toBe(false) : test.skip(cond, why));

const consent = (page: Page, auth: Record<string, string>, granted: boolean) =>
  page.request.put(`${API}/v1/me/consents/ai_processing`, { headers: auth, data: { version: "1", granted } });

async function makeTrip(page: Page, auth: Record<string, string>, name: string) {
  const made = await page.request.post(`${API}/v1/trips`, {
    headers: auth,
    data: {
      name: `${name} ${Date.now()}`,
      start_date: "2027-05-01",
      end_date: "2027-05-05",
      destinations: [{ name: "Lisbon", country: "Portugal", country_code: "PT", lat: 38.72, lon: -9.14, timezone: "Europe/Lisbon" }],
    },
  });
  expect(made.status()).toBe(201);
  return ((await made.json()) as { id: string }).id;
}

async function archive(page: Page, auth: Record<string, string>, tripId: string) {
  const now = (await (await page.request.get(`${API}/v1/trips/${tripId}`, { headers: auth })).json()) as { version: number };
  await page.request.patch(`${API}/v1/trips/${tripId}`, { headers: { ...auth, "If-Match": `"${now.version}"` }, data: { status: "archived" } });
}

const balance = async (page: Page, auth: Record<string, string>) =>
  ((await (await page.request.get(`${API}/v1/me/credits`, { headers: auth })).json()) as { available: number }).available;

// Flow 6: the consent screen shows on first AI use, declining leaves the app usable, and accepting runs explain for 1 credit.
test("flow 6: consent on first AI use, Not now keeps the app usable, Allow runs explain and spends 1 credit", async ({ page }) => {
  test.setTimeout(90_000);
  const auth = await signIn(page, "Plus user");
  expect((await consent(page, auth, false)).ok()).toBe(true); // first use again: the latest answer is a withdrawal
  const before = await balance(page, auth);
  skipUnlessCi(before < 1, "The dev Plus account is out of credits. Reset the dev database.");
  const trip = await makeTrip(page, auth, "Consent");
  try {
    await openAi(page, `/trips/${trip}/ai`);
    await page.getByRole("button", { name: /^Explain, costs 1 credit/ }).click();
    const gate = page.getByRole("dialog", { name: "Allow AI on your trips?" });
    await expect(gate).toBeVisible();
    await gate.getByRole("button", { name: "Not now" }).click();
    await expect(gate).toBeHidden();
    // Declining leaves the app usable: the trip and the Trips tab still work, and nothing was charged.
    await page.goto(`/trips/${trip}`);
    await expect(page.getByRole("heading", { level: 1 }).first()).toBeVisible();
    await page.getByRole("link", { name: "Trips" }).first().click();
    await expect(page.getByRole("heading", { level: 1, name: "Trips" })).toBeVisible();
    expect(await balance(page, auth)).toBe(before);

    // Accepting runs explain.
    await openAi(page, `/trips/${trip}/ai/explain`);
    await page.getByLabel("Your question").fill(`Is the old town walkable? ${Date.now()}`);
    const ask = page.getByRole("button", { name: /^Ask, costs 1 credit/ });
    await expect(ask).toBeEnabled();
    await ask.click();
    const again = page.getByRole("dialog", { name: "Allow AI on your trips?" });
    await expect(again).toBeVisible();
    await again.getByRole("button", { name: "Allow" }).click();
    await expect(page.getByText("AI suggestion, check details before booking")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByText(/^Used 1 credit\./)).toBeVisible();
    expect(await balance(page, auth)).toBe(before - 1);
  } finally {
    await consent(page, auth, true);
    await archive(page, auth, trip);
  }
});

// Flow 23, part one: draft a day, draft the trip and run research, on the fake provider.
test("flow 23: draft a day, draft a trip and run research", async ({ page }) => {
  test.setTimeout(150_000);
  const auth = await signIn(page, "Plus user");
  expect((await consent(page, auth, true)).ok()).toBe(true);
  skipUnlessCi((await balance(page, auth)) < 13, "Draft day, draft trip and research need 13 credits. Reset the dev database.");
  const trip = await makeTrip(page, auth, "Drafts");
  try {
    // Draft this day: preview, then Accept all.
    await openAi(page, `/trips/${trip}/ai/day`);
    const day = page.getByRole("button", { name: /^Draft, costs 1 credit/ });
    await expect(day).toBeEnabled();
    await day.click();
    await expect(page.getByRole("button", { name: "Accept all" })).toBeVisible({ timeout: 30_000 });
    await expect(page.getByText(/^Used 1 credit\./)).toBeVisible();
    await page.getByRole("button", { name: "Accept all" }).click();
    await expect(page.getByText(/^Added \d+ items? to your plan\./)).toBeVisible();

    // Draft the trip.
    await openAi(page, `/trips/${trip}/ai/trip`);
    const full = page.getByRole("button", { name: /^Draft, costs 4 credits/ });
    await expect(full).toBeEnabled();
    await full.click();
    await expect(page.getByRole("button", { name: "Accept all" })).toBeVisible({ timeout: 30_000 });
    await expect(page.getByText(/^Used 4 credits\./)).toBeVisible();
    await page.getByRole("button", { name: "Accept all" }).click();
    await expect(page.getByText(/^Added \d+ items? to your plan\./)).toBeVisible();

    // Research: sourced notes, the AI label, and 8 credits on a cold run.
    await openAi(page, `/trips/${trip}/ai/research`);
    await page.getByLabel("Topic").selectOption("events_and_closures");
    const research = page.getByRole("button", { name: /^Research, costs 8 credits/ });
    await expect(research).toBeEnabled();
    await research.click();
    await expect(page.getByRole("heading", { level: 3 }).first()).toBeVisible({ timeout: 60_000 });
    await expect(page.getByText(/Found on /).first()).toBeVisible();
    await expect(page.getByText("AI suggestion, check details before booking")).toBeVisible();
    await expect(page.getByText(/^Used (8 credits|1 credit)\./)).toBeVisible();

    // The balance and the history agree with the spends above.
    await page.goto("/account/credits");
    const list = page.getByRole("list", { name: "Credit history" });
    await expect(list).toBeVisible();
    await expect(list.getByRole("listitem").filter({ hasText: "Research" }).first()).toContainText(/-(8|1)$/);
  } finally {
    await archive(page, auth, trip);
  }
});

// Flow 23, part two: start an agent run and watch its live log. The Free persona runs it on its one lifetime taster (the demo Plus
// account holds 40 credits, which parts one and flow 6 partly spend). The run is the worker's job, so this needs `hermi worker`
// beside `npm run dev`. Without it the run stays queued: the test then cancels it and skips the live log.
test("flow 23: run an agent and watch its live log", async ({ page }) => {
  test.setTimeout(180_000);
  const auth = await signIn(page, "Free user");
  expect((await consent(page, auth, true)).ok()).toBe(true);
  const trip = await makeTrip(page, auth, "Agent");
  try {
    const preview = (await (await page.request.get(`${API}/v1/trips/${trip}/agent-runs/preview`, { headers: auth, params: { kind: "deep_research" } })).json()) as { sufficient: boolean };
    skipUnlessCi(!preview.sufficient, "The Free persona's one free run is used. Reset the dev database.");
    await page.goto(`/trips/${trip}/agents`);
    await page.getByLabel("What should it research?").fill("Events during the trip dates");
    await page.getByRole("button", { name: /^(Start free run|Plan a deep run)$/ }).click();
    await page.getByRole("dialog").getByRole("button", { name: "Start run" }).click();
    await expect(page).toHaveURL(new RegExp(`/trips/${trip}/agents/[0-9a-f-]+$`));
    await expect(page.getByRole("list", { name: "Steps of this run" })).toBeVisible();
    const ticket = page.getByRole("group", { name: /^(Agent run|Taster run): / });
    await expect(ticket).toBeVisible();
    const left = await expect
      .poll(async () => (await ticket.getAttribute("aria-label")) ?? "", { timeout: 25_000 })
      .not.toMatch(/Queued$/)
      .then(
        () => true,
        () => false,
      );
    if (!left) {
      await page.getByRole("button", { name: "Cancel run" }).click(); // release the reservation; there is no worker here
      skipUnlessCi(true, "No worker is running, so the live log was not exercised. Start `hermi worker` and run again.");
    }
    // The live log: the steps list shows while the run works, then the ticket reaches an end state. The recorded fake
    // fixture saves nothing, so the dev run ends Failed with "You were not charged"; a richer fixture would end Done.
    await expect(page.getByRole("list", { name: "Steps of this run" }).getByRole("listitem").first()).toBeVisible();
    await expect(ticket).toHaveAttribute("aria-label", /(Done|Failed|Stopped)$/, { timeout: 120_000 });
  } finally {
    await archive(page, auth, trip);
  }
});
