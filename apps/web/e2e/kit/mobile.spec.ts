import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";
import { MAIN_ROUTES, noHScroll, prepare, visit } from "./layout";

const fieldSizes = (page: Page) =>
  page.evaluate(() => [...document.querySelectorAll("input:not([type=checkbox]):not([type=radio]):not([type=hidden]), textarea, select")].map((e) => parseFloat(getComputedStyle(e).fontSize)));

// WF-036.3: the iPhone 15 profile (touch, 393 wide, scale 3) shows the tab bar and every main route fits.
test("iPhone 15 profile is a touch device with the floating tab bar", async ({ page }) => {
  await prepare(page);
  await visit(page, "/");
  expect(await page.evaluate(() => matchMedia("(pointer: coarse)").matches)).toBe(true);
  await expect(page.locator(".shell-tabs")).toBeVisible();
  await expect(page.locator(".shell-side")).toBeHidden();
  await page.getByRole("navigation", { name: "Tabs" }).getByRole("link", { name: "Account" }).tap();
  await expect(page).toHaveURL(/\/account$/);
});

test("every main route fits the iPhone 15 width", async ({ page }) => {
  await prepare(page);
  for (const path of MAIN_ROUTES) {
    await visit(page, path);
    expect(await noHScroll(page), path).toBe(true);
  }
});

test("text inputs are 16 px so iOS does not zoom", async ({ page }) => {
  await prepare(page);
  for (const path of ["/trips/new", "/trips/t1/edit", "/trips/t1/notes"]) {
    await visit(page, path);
    if (path.endsWith("/notes")) await page.getByRole("button", { name: "Add a note" }).first().click();
    expect(await fieldSizes(page), path).not.toEqual([]);
    for (const s of await fieldSizes(page)) expect(s, path).toBeGreaterThanOrEqual(16);
  }
});

test("the sign-in email field is 16 px", async ({ page }) => {
  await prepare(page, { signedIn: false });
  await visit(page, "/sign-in");
  await page.getByRole("button", { name: "Continue with email" }).click();
  const sizes = await fieldSizes(page);
  expect(sizes.length).toBeGreaterThan(0);
  for (const s of sizes) expect(s).toBeGreaterThanOrEqual(16);
});
