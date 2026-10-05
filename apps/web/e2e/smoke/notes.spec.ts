import { expect, test, type Page } from "@playwright/test";

async function signIn(page: Page, label: string) {
  await page.goto("/sign-in");
  await page.getByRole("button", { name: label }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Trips" })).toBeVisible();
}

// WF-035.2: the error and offline states, with the API stubbed so the test owns the state.
const stub = { id: "t1", version: 1, name: "Lisbon", status: "planning", start_date: "2027-05-01", end_date: "2027-05-02", home_currency: "USD", my_role: "owner", destinations: [], travelers: [] };
const now = new Date().toISOString();

test("Notes: a failed load says so with a retry, and offline the list stays readable", async ({ page, context }) => {
  await page.route("**/v1/trips/t1", (r) => r.fulfill({ json: stub }));
  let fail = true;
  await page.route("**/v1/trips/t1/notes?**", (r) =>
    fail
      ? r.fulfill({ status: 500, json: { code: "internal_error", detail: "x" } })
      : r.fulfill({ json: { items: [{ id: "n1", trip_id: "t1", kind: "user", title: "", body: "Ask about the shuttle", pinned: false, is_private: false, day: null, item_id: null, version: 1, author: { id: "u1", display_name: "Ana" }, run_id: null, sources: [], checked_at: now, stale: false, created_at: now, updated_at: now }], next_cursor: null, has_more: false } }),
  );
  await signIn(page, "Free user");
  await page.goto("/trips/t1/notes");
  await expect(page.getByRole("alert")).toHaveText("We could not load notes. Pull down to try again.");
  fail = false;
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(page.getByText("Ask about the shuttle")).toBeVisible();
  await context.setOffline(true);
  await expect(page.getByRole("status").filter({ hasText: "You are offline." })).toBeVisible();
  await expect(page.getByText("Ask about the shuttle")).toBeVisible();
  await expect(page.getByRole("button", { name: "Add a note" })).toBeDisabled();
});
