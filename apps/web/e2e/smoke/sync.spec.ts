import { expect, test, type Browser, type Page } from "@playwright/test";

const API = "http://localhost:8100";

async function signIn(page: Page, label: string) {
  await page.goto("/sign-in");
  await page.getByRole("button", { name: label }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Trips" })).toBeVisible();
  const auth = await page.evaluate(() => sessionStorage.getItem("hermi.auth"));
  return (JSON.parse(auth ?? "{}") as { token: string }).token;
}

async function second(browser: Browser) {
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const page = await ctx.newPage();
  await signIn(page, "Free user");
  return { ctx, page };
}

const archive = (page: Page, token: string, trip: { id: string }) =>
  page.request.get(`${API}/v1/trips/${trip.id}`, { headers: { Authorization: `Bearer ${token}` } }).then(async (r) => {
    const v = ((await r.json()) as { version: number }).version;
    await page.request.patch(`${API}/v1/trips/${trip.id}`, { headers: { Authorization: `Bearer ${token}`, "If-Match": `"${v}"` }, data: { status: "archived" } });
  });

// Smoke flow 18 (10 section 1.6, WF-125): the header shows "Synced N s ago" and reads the offline state within 5 seconds of cutting the network.
test("the trip header shows Synced N s ago, then Offline, 1 edit waiting within 5 seconds of cutting the network", async ({ page, context }) => {
  const token = await signIn(page, "Free user");
  const made = await page.request.post(`${API}/v1/trips`, { headers: { Authorization: `Bearer ${token}` }, data: { name: `Sync ${Date.now()}` } });
  const trip = (await made.json()) as { id: string };
  try {
    await page.goto(`/trips/${trip.id}`);
    await expect(page.getByRole("button", { name: /^Synced \d+ s ago$/ })).toBeVisible();
    // Another section carries the chip too.
    await page.goto(`/trips/${trip.id}/plan`);
    await expect(page.getByRole("button", { name: /^Synced \d+ s ago$/ })).toBeVisible();
    await page.evaluate(() => (window as unknown as { __hermiSetQueued: (id: string, n: number) => void }).__hermiSetQueued(location.pathname.split("/")[2], 1));
    await context.setOffline(true);
    await expect(page.getByRole("button", { name: "Offline, 1 edit waiting" })).toBeVisible({ timeout: 5000 });
    await context.setOffline(false);
    await expect(page.getByRole("button", { name: /^Synced \d+ s ago$/ })).toBeVisible();
  } finally {
    await archive(page, token, trip);
  }
});

test("a failed poll leaves the timer running, three failures say so, and Try now recovers", async ({ page }) => {
  const token = await signIn(page, "Free user");
  const made = await page.request.post(`${API}/v1/trips`, { headers: { Authorization: `Bearer ${token}` }, data: { name: `Sync ${Date.now()}` } });
  const trip = (await made.json()) as { id: string };
  try {
    await page.clock.install();
    await page.goto(`/trips/${trip.id}`);
    await expect(page.getByRole("button", { name: /^Synced \d+ s ago$/ })).toBeVisible();
    await page.route(`**/v1/trips/${trip.id}`, (r) => r.fulfill({ status: 503, json: { code: "internal_error", detail: "x" } }));
    await page.clock.fastForward(20_000);
    const age = async () => Number((await page.getByRole("button", { name: /^Synced \d+ s ago$/ }).textContent())?.match(/\d+/)?.[0]);
    await expect.poll(age).toBeGreaterThanOrEqual(20);
    await page.clock.fastForward(20_000);
    await page.clock.fastForward(20_000);
    await expect(page.getByRole("button", { name: "Could not sync, retrying" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Try now" })).toBeVisible();
    await page.unroute(`**/v1/trips/${trip.id}`);
    await page.getByRole("button", { name: "Try now" }).click();
    await expect(page.getByRole("button", { name: "Synced 0 s ago" })).toBeVisible();
  } finally {
    await archive(page, token, trip);
  }
});

// Two contexts edit the same trip. The second save is stale, so the sheet opens (05 4.21).
for (const choice of ["Keep mine", "Use theirs"] as const) {
  test(`a conflict opens the sheet and ${choice} resolves it`, async ({ page, browser }) => {
    const token = await signIn(page, "Free user");
    const made = await page.request.post(`${API}/v1/trips`, { headers: { Authorization: `Bearer ${token}` }, data: { name: `Conflict ${Date.now()}` } });
    const trip = (await made.json()) as { id: string };
    const other = await second(browser);
    try {
      await page.goto(`/trips/${trip.id}/edit`);
      await other.page.goto(`/trips/${trip.id}/edit`);
      await expect(page.getByLabel("Trip name")).toBeVisible();
      await expect(other.page.getByLabel("Trip name")).toBeVisible();
      await page.getByLabel("Trip name").fill("Theirs");
      await page.getByRole("button", { name: "Save", exact: true }).click();
      await expect(page.getByRole("heading", { level: 1, name: "Theirs" })).toBeVisible();
      await other.page.getByLabel("Trip name").fill("Mine");
      await other.page.getByRole("button", { name: "Save", exact: true }).click();
      await expect(other.page.getByRole("dialog", { name: "This trip changed elsewhere" })).toBeVisible();
      await other.page.getByRole("button", { name: choice }).click();
      if (choice === "Keep mine") await expect(other.page.getByRole("heading", { level: 1, name: "Mine" })).toBeVisible();
      else await expect(other.page.getByLabel("Trip name")).toHaveValue("Theirs");
      await expect(other.page.getByRole("dialog")).toBeHidden();
    } finally {
      await other.ctx.close();
      await archive(page, token, trip);
    }
  });
}
