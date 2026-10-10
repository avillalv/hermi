import { expect, test, type Page } from "@playwright/test";

// WF-053.2: the agent run screen shows the shared error state and the offline banner. Needs `npm run dev`. The run and its stream are stubbed so the test owns the state.
const trip = { id: "t1", version: 1, name: "Lisbon", status: "planning", start_date: null, end_date: null, home_currency: "USD", my_role: "owner", destinations: [], travelers: [] };
const run = {
  id: "r1", trip_id: "t1", kind: "deep_research", status: "running", started_by: null, params: { topic: "Lisbon in March" },
  queued_at: "2027-03-01T10:00:00Z", started_at: "2027-03-01T10:00:00Z", finished_at: null, summary: null, error_code: null,
  accepted_count: 0, rejected_count: 0, turns_used: 2, searches_used: 1, fetches_used: 0, from_cache: false, is_taster: false,
  credits: { action: "agent_run", reserved: 40, charged: null, from_cache: false, balance_after: null }, cancel_requested: false, events_url: "/v1/agent-runs/r1/events",
};
const started = { seq: 0, ts: "2027-03-01T10:00:00Z", type: "run.started", tool_name: null, summary: "Run started", payload: { kind: "deep_research" } };

const signIn = async (page: Page) => {
  await page.goto("/sign-in");
  await page.getByRole("button", { name: "Free user" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Trips" })).toBeVisible();
};

test("the run screen shows the error state on a 500, and Try again recovers", async ({ page }) => {
  let fail = true;
  await page.route("**/v1/trips/t1", (r) => r.fulfill({ json: trip }));
  await page.route("**/v1/agent-runs/r1", (r) => (fail ? r.fulfill({ status: 500, json: {} }) : r.fulfill({ json: run })));
  await page.route("**/v1/agent-runs/r1/stream", (r) => r.fulfill({ status: 200, contentType: "text/event-stream", body: `id: 0\nevent: run.started\ndata: ${JSON.stringify(started)}\n\n` }));
  await page.route("**/v1/agent-runs/r1/events**", (r) => r.fulfill({ json: [started] }));
  await signIn(page);
  await page.goto("/trips/t1/agents/r1");
  await expect(page.getByRole("alert").getByText("We could not load this run. Try again.", { exact: true })).toBeVisible({ timeout: 15_000 });
  fail = false;
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Research: Lisbon in March" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Stop" })).toBeVisible();
});

test("the run screen says the run keeps going when the connection drops", async ({ page, context }) => {
  await page.route("**/v1/trips/t1", (r) => r.fulfill({ json: trip }));
  await page.route("**/v1/agent-runs/r1", (r) => r.fulfill({ json: run }));
  await page.route("**/v1/agent-runs/r1/stream", (r) => r.fulfill({ status: 200, contentType: "text/event-stream", body: `id: 0\nevent: run.started\ndata: ${JSON.stringify(started)}\n\n` }));
  await page.route("**/v1/agent-runs/r1/events**", (r) => r.fulfill({ json: [started] }));
  await signIn(page);
  await page.goto("/trips/t1/agents/r1");
  await expect(page.getByRole("heading", { level: 1, name: "Research: Lisbon in March" })).toBeVisible();
  await context.setOffline(true);
  await expect(page.getByRole("status").filter({ hasText: "You are offline. The run keeps going." })).toBeVisible();
  await expect(page.getByRole("button", { name: "Stop" })).toBeDisabled();
});

const preview = { kind: "deep_research", credits: 0, price: 40, taster: true, taster_used: false, balance: 12, sufficient: true, from_cache: false };
const taster = { used: false, used_at: null, run_id: null, available: true, credits: 40 };
const stubStart = async (page: Page, failPreview: () => boolean) => {
  await page.route("**/v1/trips/t1", (r) => r.fulfill({ json: trip }));
  await page.route("**/v1/trips/t1/routes", (r) => r.fulfill({ json: [] }));
  await page.route("**/v1/me/agent-taster", (r) => r.fulfill({ json: taster }));
  await page.route("**/v1/trips/t1/agent-runs/preview**", (r) => (failPreview() ? r.fulfill({ status: 500, json: {} }) : r.fulfill({ json: preview })));
};

test("the start screen shows the error state on a 500, and Try again recovers", async ({ page }) => {
  let fail = true;
  await stubStart(page, () => fail);
  await signIn(page);
  await page.goto("/trips/t1/agents");
  await expect(page.getByRole("alert").getByText("We could not load the price for this run. Try again.", { exact: true })).toBeVisible({ timeout: 15_000 });
  fail = false;
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(page.getByRole("alert")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Start free run" })).toBeEnabled();
});

test("the start screen is disabled offline and says AI needs a connection", async ({ page, context }) => {
  await stubStart(page, () => false);
  await signIn(page);
  await page.goto("/trips/t1/agents");
  await expect(page.getByRole("button", { name: "Start free run" })).toBeEnabled();
  await context.setOffline(true);
  await expect(page.getByRole("status").filter({ hasText: "AI needs a connection." })).toBeVisible();
  await expect(page.getByRole("button", { name: "Start free run" })).toBeDisabled();
});

// WF-054: the consent sheet shows its error and offline states, and the thumbs are disabled offline.
test("the consent sheet shows an error when saving fails", async ({ page }) => {
  await stubStart(page, () => false);
  let asked = false;
  await page.route("**/v1/me/consents", (r) => ((asked = true), r.fulfill({ json: [] })));
  await page.route("**/v1/me/consents/ai_processing", (r) => r.fulfill({ status: 500, json: {} }));
  await signIn(page);
  await page.goto("/trips/t1/agents");
  const start = page.getByRole("button", { name: "Start free run" });
  await expect(start).toBeEnabled();
  await expect.poll(() => asked).toBe(true);
  await page.waitForTimeout(200); // the answer is cached before the tap, so the gate opens on first use
  await start.click();
  const sheet = page.getByRole("dialog", { name: "Allow AI on your trips?" });
  await sheet.getByRole("button", { name: "Allow" }).click();
  await expect(sheet.getByText("We could not save your choice. Try again.")).toBeVisible();
});

test("the consent sheet is offline aware", async ({ page, context }) => {
  await stubStart(page, () => false);
  let asked = false;
  await page.route("**/v1/me/consents", (r) => ((asked = true), r.fulfill({ json: [] })));
  await signIn(page);
  await page.goto("/trips/t1/agents");
  const start = page.getByRole("button", { name: "Start free run" });
  await expect(start).toBeEnabled();
  await expect.poll(() => asked).toBe(true);
  await page.waitForTimeout(200); // the answer is cached before the tap, so the gate opens on first use
  await start.click();
  const sheet = page.getByRole("dialog", { name: "Allow AI on your trips?" });
  await context.setOffline(true);
  await expect(sheet.getByText("AI needs a connection.")).toBeVisible();
  await expect(sheet.getByRole("button", { name: "Allow" })).toBeDisabled();
});

test("thumbs are disabled offline on a finished run", async ({ page, context }) => {
  const done = { ...run, status: "succeeded", finished_at: "2027-03-01T10:05:00Z", accepted_count: 1, credits: { ...run.credits, charged: 31 } };
  const note = { seq: 4, ts: "2027-03-01T10:00:04Z", type: "note.saved", tool_name: null, summary: "Saved note", payload: { title: "Tram 28 is crowded", source_urls: ["https://lisbon-guide.org/t"] } };
  const fin = { seq: 9, ts: "2027-03-01T10:05:00Z", type: "run.finished", tool_name: null, summary: "", payload: { status: "succeeded", accepted: 1, credits: { reserved: 40, charged: 31, balance_after: null } } };
  await page.route("**/v1/trips/t1", (r) => r.fulfill({ json: trip }));
  await page.route("**/v1/agent-runs/r1", (r) => r.fulfill({ json: done }));
  await page.route("**/v1/agent-runs/r1/stream", (r) => r.fulfill({ status: 200, contentType: "text/event-stream", body: [started, note, fin].map((e) => `id: ${e.seq}
event: x
data: ${JSON.stringify(e)}

`).join("") }));
  await page.route("**/v1/agent-runs/r1/events**", (r) => r.fulfill({ json: [started, note, fin] }));
  await signIn(page);
  await page.goto("/trips/t1/agents/r1");
  await expect(page.getByRole("button", { name: "Helpful", exact: true })).toBeEnabled();
  await context.setOffline(true);
  await expect(page.getByText("Feedback needs a connection.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Helpful", exact: true })).toBeDisabled();
  await expect(page.getByRole("button", { name: "Not helpful" })).toBeDisabled();
});
