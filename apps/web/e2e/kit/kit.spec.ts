import { expect } from "@playwright/test";
import { openApp, openKit, SCHEMES, test } from "./kit";

const FAMILIES = ["Fredoka Variable", "Atkinson Hyperlegible Next Variable", "Atkinson Hyperlegible Mono Variable"];

for (const scheme of SCHEMES) {
  test(`app fixture makes no googleapis or gstatic request (${scheme})`, async ({ page, kit }) => {
    await openApp(page, "components.html", scheme);
    expect(kit.fontRequests).toEqual([]);
  });

  test(`bundled fonts load in the app fixture (${scheme})`, async ({ page }) => {
    await openApp(page, "components.html", scheme);
    for (const family of FAMILIES) {
      const r = await page.evaluate(async (f) => {
        await document.fonts.load(`16px "${f}"`);
        return { check: document.fonts.check(`16px "${f}"`), status: [...document.fonts].filter((x) => x.family.replace(/"/g, "") === f).map((x) => x.status) };
      }, family);
      expect(r.check, family).toBe(true);
      expect(r.status, family).toContain("loaded");
    }
  });

  test(`kit page fonts come from the bundled files (${scheme})`, async ({ page, kit }) => {
    await openKit(page, "components.html", scheme);
    expect(kit.fontRequests.length).toBeGreaterThan(0);
    expect(await page.evaluate(() => document.fonts.check("16px Fredoka"))).toBe(true);
  });

  test(`clock is frozen (${scheme})`, async ({ page }) => {
    await openApp(page, "components.html", scheme);
    expect(await page.evaluate(() => new Date().toISOString())).toBe("2026-01-15T12:00:00.000Z");
  });
}
