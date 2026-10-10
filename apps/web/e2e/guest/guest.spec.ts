import { expect, test, type Page } from "@playwright/test";

// WF-062.2: guest mode end to end. Needs `npm run dev` (API on fakes and web). Run: npx playwright test --project guest
const API = "http://localhost:8100";

// Claimed trips are archived afterwards so reruns on the same dev database stay under the Free active-trip limit.
const claimedIds: string[] = [];
test.afterEach(async ({ page }) => {
  const auth = { Authorization: `Bearer ${await token(page)}` };
  for (const id of claimedIds.splice(0)) {
    const now = await page.request.get(`${API}/v1/trips/${id}`, { headers: auth });
    const { version } = (await now.json()) as { version: number };
    await page.request.patch(`${API}/v1/trips/${id}`, { headers: { ...auth, "If-Match": `"${version}"` }, data: { status: "archived" } });
  }
});

const token = async (page: Page) => (JSON.parse((await page.evaluate(() => sessionStorage.getItem("hermi.auth"))) ?? "{}") as { token?: string }).token ?? "";

test("a guest plans on the device with no server request, saves through the sheet, and the claim happens once", async ({ page }) => {
  const name = `Lisbon guest ${Date.now()}`;
  const v1: string[] = [];
  page.on("request", (r) => r.url().includes("/v1/") && v1.push(`${r.method()} ${new URL(r.url()).pathname}`));

  // 1. A signed-out visitor creates a trip locally.
  await page.goto("/welcome");
  await page.getByRole("link", { name: "Plan a trip" }).click();
  await expect(page).toHaveURL(/\/guest-trip$/);
  await page.getByLabel("Where are you going?").fill(name);
  await page.getByRole("button", { name: "Create trip" }).click();
  await expect(page.getByRole("heading", { level: 1, name })).toBeVisible();
  await page.getByLabel("What are you doing?").fill("Castelo walk");
  await page.getByRole("button", { name: "Add to plan" }).click();
  await expect(page.getByText("Castelo walk")).toBeVisible();
  await expect(page.getByText("Guest trip, saved on this phone")).toBeVisible();
  const doc = JSON.parse((await page.evaluate(() => localStorage.getItem("hermi.guest.v2"))) ?? "null") as { claim_id: string; trip: { items: unknown[] } };
  expect(doc.trip.items).toHaveLength(1);
  // Nothing about the guest reached the server: no tenant call and no claim before sign-in.
  expect(v1).toEqual([]);

  // 2. An invite attempt opens the Save sheet; email goes to sign in.
  await page.getByRole("button", { name: "Invite people" }).click();
  const sheet = page.getByRole("dialog", { name: "Save your trip" });
  await expect(sheet).toBeVisible();
  await expect(sheet.getByRole("button")).toHaveText(["Continue with Apple", "Continue with Google", "Continue with email", "Not now"]);
  expect(v1.filter((r) => r.includes("/me/claim"))).toEqual([]);
  await sheet.getByRole("button", { name: "Continue with email" }).click();
  await expect(page).toHaveURL(/\/sign-in$/);

  // 3. Dev persona sign-in, then the claim.
  const claimed = page.waitForResponse((r) => r.url().endsWith("/v1/me/claim") && r.request().method() === "POST");
  await page.getByRole("button", { name: "Free user" }).click();
  const first = await claimed;
  let result = first;
  if (first.status() === 409) {
    // The persona already owns trips: the Merge choice shows its count.
    const merge = page.getByRole("dialog", { name: "Add this trip to your account?" });
    await expect(merge).toContainText("You already have");
    const second = page.waitForResponse((r) => r.url().endsWith("/v1/me/claim") && r.request().method() === "POST");
    await merge.getByRole("button", { name: "Add this trip" }).click();
    result = await second;
  }
  expect(result.status()).toBe(200);
  const body = (await result.json()) as { trip_id: string | null; archived: boolean };
  if (body.trip_id) claimedIds.push(body.trip_id);
  await expect(page.getByRole("dialog", { name: "Your trip is saved" })).toBeVisible();
  expect(await page.evaluate(() => localStorage.getItem("hermi.guest.v2"))).toBeNull();
  await page.getByRole("button", { name: "View trip" }).click();
  if (body.trip_id) await expect(page.getByRole("heading", { level: 1, name })).toBeVisible();
  await expect(page.getByText("Guest trip, saved on this phone")).toHaveCount(0);

  // 4. The same claim id again returns the first result and adds nothing.
  const bearer = { Authorization: `Bearer ${await token(page)}` };
  const again = await page.request.post(`${API}/v1/me/claim`, { headers: bearer, data: { trip: { name }, claim_id: doc.claim_id, merge: true } });
  expect(again.status()).toBe(200);
  expect(again.headers()["idempotent-replay"]).toBe("true");
  expect(((await again.json()) as { trip_id: string | null }).trip_id).toBe(body.trip_id);
  const list = await page.request.get(`${API}/v1/trips`, { headers: bearer });
  const trips = ((await list.json()) as { items: { name: string }[] }).items;
  expect(trips.filter((t) => t.name === name)).toHaveLength(1);
});

test("offline the Save sheet disables sign-in and says the trip stays on the phone", async ({ page, context }) => {
  await page.goto("/guest-trip");
  await page.getByLabel("Where are you going?").fill("Porto");
  await page.getByRole("button", { name: "Create trip" }).click();
  await context.setOffline(true);
  await page.getByRole("button", { name: "Export" }).click();
  const sheet = page.getByRole("dialog", { name: "Save your trip" });
  await expect(sheet.getByRole("status")).toContainText("Connect to the internet to create your account. Your trip stays on this phone.");
  await expect(sheet.getByRole("button", { name: "Continue with email" })).toBeDisabled();
  await sheet.getByRole("button", { name: "Not now" }).click();
  await expect(sheet).toHaveCount(0);
  // The trip is still there, and the banner remains.
  await expect(page.getByText("Guest trip, saved on this phone")).toBeVisible();
});

test("a failed claim keeps the trip on the phone and Retry moves it", async ({ page }) => {
  const name = `Porto guest ${Date.now()}`;
  await page.goto("/guest-trip");
  await page.getByLabel("Where are you going?").fill(name);
  await page.getByRole("button", { name: "Create trip" }).click();
  let fail = true;
  await page.route("**/v1/me/claim", (r) => (fail ? r.fulfill({ status: 500, json: { code: "internal_error" } }) : r.continue()));
  await page.goto("/sign-in");
  await page.getByRole("button", { name: "Free user" }).click();
  await expect(page.getByRole("alert")).toContainText("We could not move your trip into your account. It is still on this phone. Try again.");
  expect(await page.evaluate(() => localStorage.getItem("hermi.guest.v2"))).not.toBeNull();
  fail = false;
  await page.getByRole("button", { name: "Retry" }).click();
  const merge = page.getByRole("dialog", { name: "Add this trip to your account?" });
  const saved = page.getByRole("dialog", { name: "Your trip is saved" });
  await expect(merge.or(saved)).toBeVisible();
  if (await merge.isVisible()) await merge.getByRole("button", { name: "Add this trip" }).click();
  await expect(saved).toBeVisible();
  expect(await page.evaluate(() => localStorage.getItem("hermi.guest.v2"))).toBeNull();
  const mine = await page.request.get(`${API}/v1/trips`, { headers: { Authorization: `Bearer ${await token(page)}` } });
  for (const t of ((await mine.json()) as { items: { id: string; name: string }[] }).items) if (t.name === name) claimedIds.push(t.id);
});
