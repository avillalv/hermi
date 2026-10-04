import { expect, test } from "@playwright/test";

// Smoke flow 1 (10 section 1.6): dev persona sign-in lands on Trips. Needs `npm run dev` (API 8100 on AUTH_MODE=dev, web 5173).
test("Free persona signs in, lands on Trips, and sign-out clears the session", async ({ page }) => {
  await page.goto("/sign-in");
  await expect(page.getByRole("heading", { level: 1, name: "Sign in to Hermi" })).toBeVisible();
  await page.getByRole("button", { name: "Free user" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Trips" })).toBeVisible();
  expect(await page.evaluate(() => sessionStorage.getItem("hermi.auth"))).toContain("free");
  await page.getByRole("link", { name: "Account" }).first().click();
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page.getByRole("link", { name: "Sign in" })).toBeVisible();
  expect(await page.evaluate(() => sessionStorage.getItem("hermi.auth"))).toBeNull();
});

test("offline sign-in shows the offline message", async ({ page, context }) => {
  await page.goto("/sign-in");
  await context.setOffline(true);
  await expect(page.getByRole("status")).toHaveText("You are offline. Connect to sign in.");
  await expect(page.getByRole("button", { name: "Continue with Apple" })).toBeDisabled();
});

test("an unreachable provider shows an error", async ({ page }) => {
  await page.goto("/sign-in");
  await page.getByRole("button", { name: "Continue with Google" }).click();
  await expect(page.getByRole("alert")).toHaveText("Sign in is not available right now. Try again in a moment.");
});
