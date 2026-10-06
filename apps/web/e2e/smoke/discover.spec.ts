import { expect, test } from "@playwright/test";

const API = "http://localhost:8100";

// Smoke flow 19 (10 section 1.6, WF-133.3): open a sample trip from Discover, tap "Use this plan", and see it as a new trip in Trips.
// Needs the demo seed (`hermi seed --demo`). The copy is archived at the end so reruns stay under the Free active-trip limit.
test("open a sample from Discover, use this plan, and see it as a new trip in Trips", async ({ page }) => {
  await page.goto("/sign-in");
  await page.getByRole("button", { name: "Free user" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Trips" })).toBeVisible();
  const token = (JSON.parse((await page.evaluate(() => sessionStorage.getItem("hermi.auth"))) ?? "{}") as { token: string }).token;

  await page.getByRole("link", { name: "Discover" }).first().click();
  await expect(page.getByRole("heading", { level: 1, name: "Discover" })).toBeVisible();
  const first = page.locator("a.h-ticket__card").first();
  await expect(first).toBeVisible({ timeout: 10_000 });
  const name = (await first.getByRole("heading").innerText()).trim();
  await first.click();
  await expect(page.getByRole("heading", { level: 1, name })).toBeVisible();
  await expect(page.getByText("Sample trip. Prices and facts are dated and may have changed.")).toBeVisible();

  const copied = page.waitForResponse((r) => r.url().includes("/copy") && r.request().method() === "POST");
  await page.getByRole("button", { name: "Use this plan" }).click();
  const res = await copied;
  expect(res.status()).toBe(201);
  const trip = (await res.json()) as { id: string; version: number };
  try {
    await expect(page).toHaveURL(new RegExp(`/trips/${trip.id}$`));
    await page.getByRole("link", { name: "Trips" }).first().click();
    await expect(page.getByRole("link", { name: new RegExp(name) }).first()).toBeVisible();
  } finally {
    await page.request.patch(`${API}/v1/trips/${trip.id}`, { headers: { Authorization: `Bearer ${token}` }, data: { status: "archived", version: trip.version } });
  }
});
