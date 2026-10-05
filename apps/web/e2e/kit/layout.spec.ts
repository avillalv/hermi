import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import { MAIN_ROUTES, PUBLIC_ROUTES, noHScroll, prepare, visit } from "./layout";

// WF-036.3: every route at the breakpoint edges has no horizontal scroll, and axe finds nothing in light and dark.
const WIDTHS = [390, 1023, 1024, 1199, 1200, 1440];
const ERROR_ROUTES = ["/", "/trips/t1", "/trips/t1/flights", "/trips/t1/stays", "/trips/t1/notes", "/trips/t1/plan", "/trips/t1/group", "/activity"];
const axe = async (page: Page) =>
  (await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze()).violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).join(" | ")}`);

for (const width of WIDTHS) {
  test(`no horizontal scroll on any route at ${width}`, async ({ page }) => {
    await page.setViewportSize({ width, height: 844 });
    await prepare(page);
    for (const path of MAIN_ROUTES) {
      await visit(page, path);
      expect(await noHScroll(page), `${path} at ${width}`).toBe(true);
    }
  });
  test(`no horizontal scroll on the error state at ${width}`, async ({ page }) => {
    await page.setViewportSize({ width, height: 844 });
    await prepare(page, { errors: true });
    for (const path of ERROR_ROUTES) {
      await visit(page, path, "light", { errors: true });
      expect(await noHScroll(page), `${path} error at ${width}`).toBe(true);
    }
  });
  test(`no horizontal scroll on public routes at ${width}`, async ({ page }) => {
    await page.setViewportSize({ width, height: 844 });
    await prepare(page, { signedIn: false });
    for (const path of PUBLIC_ROUTES) {
      await visit(page, path);
      expect(await noHScroll(page), `${path} at ${width}`).toBe(true);
    }
  });
}

for (const scheme of ["light", "dark"] as const) {
  test(`axe finds no violations on main routes in ${scheme}`, async ({ page }) => {
    await prepare(page);
    for (const path of MAIN_ROUTES) {
      await visit(page, path, scheme);
      expect(await axe(page), `${path} (${scheme})`).toEqual([]);
    }
  });
  test(`axe finds no violations on the error state in ${scheme}`, async ({ page }) => {
    await prepare(page, { errors: true });
    for (const path of ["/", "/trips/t1", "/trips/t1/flights"]) {
      await visit(page, path, scheme, { errors: true });
      expect(await axe(page), `${path} error (${scheme})`).toEqual([]);
    }
  });
  test(`axe finds no violations on public routes in ${scheme}`, async ({ page }) => {
    await prepare(page, { signedIn: false });
    for (const path of PUBLIC_ROUTES) {
      await visit(page, path, scheme);
      expect(await axe(page), `${path} (${scheme})`).toEqual([]);
    }
  });
}
