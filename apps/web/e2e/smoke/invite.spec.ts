import { expect, test, type Browser, type Page } from "@playwright/test";

const API = "http://localhost:8100";

async function signIn(page: Page, label: string) {
  await page.goto("/sign-in");
  await page.getByRole("button", { name: label }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Trips" })).toBeVisible();
  const auth = await page.evaluate(() => sessionStorage.getItem("hermi.auth"));
  return (JSON.parse(auth ?? "{}") as { token: string }).token;
}

async function second(browser: Browser, label: string) {
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const page = await ctx.newPage();
  await signIn(page, label);
  return { ctx, page };
}

// Smoke flows 3 and 4 (10 section 1.6, WF-026). The Free owner is the Free persona; the invitee is the Admin persona, which is on the Free tier.
// The trip is archived at the end so reruns on the same dev database stay under the Free active-trip limit.
test("a Free owner invites one person by link, the invitee accepts, and the second invite shows the paywall with a close control", async ({ page, browser }) => {
  const token = await signIn(page, "Free user");
  const auth = { Authorization: `Bearer ${token}` };
  const name = `Invite ${Date.now()}`;
  const made = await page.request.post(`${API}/v1/trips`, { headers: auth, data: { name } });
  expect(made.status()).toBe(201);
  const trip = (await made.json()) as { id: string; version: number };
  try {
    await page.goto(`/trips/${trip.id}/group?invite=1`);
    await expect(page.getByRole("region", { name: "Invite people" })).toBeVisible();
    await expect(page.getByText("0 of 1 on Free")).toBeVisible();
    // Flow 3: the first invite is a link. Read it from the API response so the test needs no clipboard.
    const sent = page.waitForResponse((r) => r.url().endsWith(`/v1/trips/${trip.id}/invites`) && r.request().method() === "POST");
    await page.getByRole("button", { name: "Share invite link" }).click();
    const invite = (await (await sent).json()) as { url: string };
    const path = new URL(invite.url).pathname;
    const guest = await second(browser, "Admin");
    try {
      await guest.page.goto(path);
      await guest.page.getByRole("button", { name: "Join trip" }).click();
      await expect(guest.page.getByText(name).first()).toBeVisible();
    } finally {
      await guest.ctx.close();
    }
    // Flow 4: the second invite is the `invite` paywall, with the free path and a visible close control.
    await page.goto(`/trips/${trip.id}/group?invite=1`);
    await expect(page.getByText("1 of 1 on Free")).toBeVisible();
    await page.getByRole("button", { name: "Share invite link" }).click();
    await expect(page.getByText("Plan together. They join free.")).toBeVisible();
    await expect(page.getByRole("button", { name: "Keep my one collaborator" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Share a read-only link" })).toBeVisible();
    await page.getByRole("button", { name: "Close" }).click();
    await expect(page.getByRole("region", { name: "Invite people" })).toBeHidden();
  } finally {
    await page.request.patch(`${API}/v1/trips/${trip.id}`, { headers: { ...auth, "If-Match": `"${trip.version}"` }, data: { status: "archived" } });
  }
});

test("the invite sheet says Connect to send an invite. when offline", async ({ page, context }) => {
  const token = await signIn(page, "Free user");
  const made = await page.request.post(`${API}/v1/trips`, { headers: { Authorization: `Bearer ${token}` }, data: { name: `Offline ${Date.now()}` } });
  const trip = (await made.json()) as { id: string; version: number };
  try {
    await page.goto(`/trips/${trip.id}/group?invite=1`);
    await expect(page.getByRole("region", { name: "Invite people" })).toBeVisible();
    await context.setOffline(true);
    await expect(page.getByText("Connect to send an invite.")).toBeVisible();
    await expect(page.getByRole("button", { name: "Share invite link" })).toBeDisabled();
  } finally {
    await context.setOffline(false);
    await page.request.patch(`${API}/v1/trips/${trip.id}`, { headers: { Authorization: `Bearer ${token}`, "If-Match": `"${trip.version}"` }, data: { status: "archived" } });
  }
});
