import { expect, test, type Page } from "@playwright/test";

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

// WF-018.2. The empty state needs an account with no trips, so the list is stubbed here (the real flow is the create test below).
test("Free persona lands on an empty Trips screen with a New trip button", async ({ page }) => {
  await page.route("**/v1/trips", (r) =>
    r.fulfill({ json: { items: [], next_cursor: null, has_more: false } }),
  );
  await page.goto("/sign-in");
  await page.getByRole("button", { name: "Free user" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Trips" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "No trips yet" })).toBeVisible();
  await page.getByRole("link", { name: "New trip" }).last().click();
  await expect(page.getByText("Step 1 of 3")).toBeVisible();
});

test("a trips load error shows the message and Try again", async ({ page }) => {
  await page.route("**/v1/trips", (r) => r.fulfill({ status: 500, json: {} }));
  await page.goto("/sign-in");
  await page.getByRole("button", { name: "Free user" }).click();
  await expect(page.getByRole("alert")).toHaveText("We could not load your trips. Try again.");
});

// WF-018.2 error and offline states. A real-provider session (no persona) whose GET /me is 401 is a new user.
async function asNewUser(page: Page) {
  await page.addInitScript(() => {
    if (!sessionStorage.getItem("hermi.auth")) sessionStorage.setItem("hermi.auth", JSON.stringify({ token: "tok" }));
  });
  await page.route("**/v1/me", (r) => r.fulfill({ status: 401, json: {} }));
}
async function asFreePersona(page: Page) {
  await page.addInitScript(() => {
    if (!sessionStorage.getItem("hermi.auth")) sessionStorage.setItem("hermi.auth", JSON.stringify({ token: "dev-free", persona: "free" }));
  });
  await page.route("**/v1/trips", (r) => r.fulfill({ json: { items: [], next_cursor: null, has_more: false } }));
}

test("Trips home offline shows the offline banner", async ({ page, context }) => {
  await asFreePersona(page);
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "No trips yet" })).toBeVisible();
  await context.setOffline(true);
  await expect(page.getByRole("status")).toHaveText("You are offline. Showing your saved trips.");
});

test("onboarding shows the setup error when bootstrap fails", async ({ page }) => {
  await asNewUser(page);
  await page.route("**/v1/me/bootstrap", (r) => r.fulfill({ status: 500, json: {} }));
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1, name: "Welcome to Hermi" })).toBeVisible();
  await page.getByLabel(/I am \d+ or older/).check();
  await page.getByRole("button", { name: "Skip for now" }).click();
  await expect(page.getByRole("alert")).toHaveText("We could not set up your account. Try again.");
});

test("onboarding offline disables saving", async ({ page, context }) => {
  await asNewUser(page);
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1, name: "Welcome to Hermi" })).toBeVisible();
  await context.setOffline(true);
  await expect(page.getByRole("status")).toHaveText("You are offline. Your answers stay here until you connect.");
  await expect(page.getByRole("button", { name: "Save and continue" })).toBeDisabled();
});

async function toLastStep(page: Page) {
  await page.goto("/trips/new");
  await page.getByLabel("Search a city or country").fill("Lisbon");
  await page.getByRole("button", { name: "Next" }).click();
  await page.getByLabel("I do not have dates yet").check();
  await page.getByRole("button", { name: "Next" }).click();
}

test("create trip shows the failure when the server errors", async ({ page }) => {
  await asFreePersona(page);
  await page.route("**/v1/geo/destinations*", (r) => r.fulfill({ json: [] }));
  await page.route("**/v1/trips", (r) =>
    r.request().method() === "POST" ? r.fulfill({ status: 500, json: {} }) : r.fulfill({ json: { items: [], next_cursor: null, has_more: false } }),
  );
  await toLastStep(page);
  await page.getByRole("button", { name: "Create trip" }).click();
  await expect(page.getByRole("alert")).toHaveText("We could not create your trip. Try again.");
});

test("create trip offline disables Create", async ({ page, context }) => {
  await asFreePersona(page);
  await page.route("**/v1/geo/destinations*", (r) => r.fulfill({ json: [] }));
  await toLastStep(page);
  await context.setOffline(true);
  await expect(page.getByRole("status")).toHaveText("You are offline. Connect to create your trip.");
  await expect(page.getByRole("button", { name: "Create trip" })).toBeDisabled();
});

// Real API on fakes. The Plus persona (25 active trips) and a unique name keep reruns on the same dev database passing.
test("new user creates a first trip in three steps", async ({ page }) => {
  const name = `Lisbon ${Date.now()}`;
  await page.goto("/sign-in");
  await page.getByRole("button", { name: "Plus user" }).click();
  await page.getByRole("link", { name: "New trip" }).last().click();
  await page.getByLabel("Search a city or country").fill(name);
  await page.getByRole("button", { name: "Next" }).click();
  await page.getByLabel("I do not have dates yet").check();
  await page.getByRole("button", { name: "Next" }).click();
  await page.getByRole("button", { name: "Create trip" }).click();
  await expect(page.getByText(name)).toBeVisible();
});
