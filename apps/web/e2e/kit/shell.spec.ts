import { expect, type Page } from "@playwright/test";
import { test } from "./kit";

const TABS = ["Trips", "Discover", "Activity", "Account"];
const FAMILIES = ["Fredoka Variable", "Atkinson Hyperlegible Next Variable", "Atkinson Hyperlegible Mono Variable"];

async function open(page: Page, width: number, path = "/") {
  await page.setViewportSize({ width, height: 844 });
  // Start signed in as the dev Free persona (authStore keeps the session in sessionStorage); the list is stubbed so layout checks do not depend on data.
  await page.addInitScript(() => {
    if (!sessionStorage.getItem("hermi.auth")) sessionStorage.setItem("hermi.auth", JSON.stringify({ token: "dev-free", persona: "free" }));
  });
  await page.route("**/v1/trips", (r) => r.fulfill({ json: { items: [], next_cursor: null, has_more: false } }));
  await page.goto(path);
  await page.evaluate(() => document.fonts.ready);
}
const box = (page: Page, sel: string) => page.locator(sel).first().boundingBox();

// Layout per 05 5.3 and 10: tab bar under 768, 72 px rail 768 to 1199, 248 px sidebar from 1200.
const LAYOUTS: [number, "tabs" | "rail" | "sidebar"][] = [
  [390, "tabs"],
  [768, "rail"],
  [1023, "rail"],
  [1024, "rail"],
  [1199, "rail"],
  [1200, "sidebar"],
  [1440, "sidebar"],
];

for (const [width, mode] of LAYOUTS) {
  test(`shell layout at ${width}: ${mode}`, async ({ page }) => {
    await open(page, width);
    const tabbar = page.locator(".shell-tabs");
    const side = page.locator(".shell-side");
    if (mode === "tabs") {
      await expect(tabbar).toBeVisible();
      await expect(side).toBeHidden();
      const bar = (await box(page, ".h-tabbar__bar"))!;
      expect(bar.height).toBe(58);
      expect(bar.x).toBe(12);
      expect(bar.y + bar.height).toBe(844 - 22);
    } else {
      await expect(tabbar).toBeHidden();
      await expect(side).toBeVisible();
      expect((await box(page, ".shell-side"))!.width).toBe(mode === "rail" ? 72 : 248);
      // the rail label is visually hidden (1 px), shown on hover; the sidebar shows it
      expect(((await box(page, ".shell-link__label"))!.width > 8)).toBe(mode === "sidebar");
      if (mode === "sidebar") expect((await box(page, ".shell-sheet"))!.width).toBeLessThanOrEqual(1120);
    }
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await expect(page.getByRole("navigation", { name: mode === "tabs" ? "Tabs" : "Main" }).getByRole("link", { name: "Trips" })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });
}

test("viewport meta has viewport-fit=cover", async ({ page }) => {
  await open(page, 390);
  await expect(page.locator('meta[name="viewport"]')).toHaveAttribute("content", /viewport-fit=cover/);
});

test("content ends above the tab bar at 390 by 844", async ({ page }) => {
  await open(page, 390);
  const pad = await page.evaluate(() => parseFloat(getComputedStyle(document.querySelector(".shell-sheet")!).paddingBottom));
  expect(pad).toBeGreaterThanOrEqual(86);
  expect(await page.evaluate(() => getComputedStyle(document.documentElement).scrollPaddingBottom)).toBe("86px");
});

test("strip is sticky while the sheet scrolls under it", async ({ page }) => {
  await open(page, 390);
  await page.evaluate(() => {
    const strip = document.createElement("nav");
    strip.className = "h-strip shell-strip";
    strip.textContent = "strip";
    document.querySelector(".shell-main")!.prepend(strip);
    document.querySelector(".shell-sheet")!.append(Object.assign(document.createElement("div"), { style: "height:3000px" }));
  });
  await page.mouse.wheel(0, 1200);
  await page.waitForFunction(() => scrollY > 500);
  expect((await box(page, ".shell-strip"))!.y).toBe(0);
});

test("sidebar shows the dark lockup in dark mode", async ({ page }) => {
  await open(page, 1200);
  await page.evaluate(() => document.documentElement.classList.add("dark"));
  await expect(page.locator(".shell-lockup--dark")).toBeVisible();
  await expect(page.locator(".shell-lockup--light")).toBeHidden();
});

test("rail shows a tooltip on hover", async ({ page }) => {
  await open(page, 768);
  const link = page.locator(".shell-side").getByRole("link", { name: "Discover" });
  await link.hover();
  await expect(link.locator(".shell-link__label")).toBeVisible();
});

test("tab bar navigates between the four tabs", async ({ page }) => {
  await open(page, 390);
  await page.getByRole("navigation", { name: "Tabs" }).getByRole("link", { name: "Account" }).click();
  await expect(page).toHaveURL(/\/account$/);
  await expect(page.getByRole("heading", { level: 1, name: "Account" })).toBeVisible();
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1, name: "Trips" })).toBeVisible();
});

test("fonts come from bundled files: three families load, no googleapis or gstatic request", async ({ page, kit }) => {
  const urls: string[] = [];
  page.on("request", (r) => urls.push(r.url()));
  await open(page, 1200);
  const ok = await page.evaluate(async (families) => {
    await Promise.all(families.map((f) => document.fonts.load(`16px "${f}"`)));
    return families.map((f) => document.fonts.check(`16px "${f}"`));
  }, FAMILIES);
  expect(ok).toEqual([true, true, true]);
  const loaded = await page.evaluate(() => [...document.fonts].filter((f) => f.status === "loaded").map((f) => f.family.replace(/"/g, "")));
  for (const f of FAMILIES) expect(loaded).toContain(f);
  expect(urls.filter((u) => /googleapis|gstatic/.test(u))).toEqual([]);
  expect(kit.fontRequests).toEqual([]);
});

for (const width of [390, 768, 1200]) {
  test(`shell controls at ${width}: tab order, 3px solid focus ring, 44px targets`, async ({ page }) => {
    // A screen with no controls of its own, so Tab reaches only the shell: the read-only guest trip (Discover has filter chips now).
    await page.addInitScript(() => localStorage.setItem("hermi.guestTrip", JSON.stringify({ saved_at: "2026-10-01T00:00:00Z", sample: { slug: "s", title: "Sample", summary: "", updated_at: "2026-09-12T10:00:00Z", presentation: { trip: { name: "Sample", destinations: [] }, days: [], stays: [] } } })));
    await open(page, width, "/guest-trip");
    const names: string[] = [];
    const count = width === 390 ? 4 : 5; // the rail and sidebar add the logo link first
    for (let i = 0; i < count; i++) {
      await page.keyboard.press("Tab");
      const info = await page.evaluate(() => {
        const el = document.activeElement as HTMLElement;
        const cs = getComputedStyle(el);
        const r = el.getBoundingClientRect();
        return { name: (el.getAttribute("aria-label") ?? el.textContent ?? "").trim(), w: cs.outlineWidth, s: cs.outlineStyle, h: r.height, wd: r.width };
      });
      expect(info.w).toBe("3px");
      expect(info.s).toBe("solid");
      expect(info.h).toBeGreaterThanOrEqual(44);
      expect(info.wd).toBeGreaterThanOrEqual(44);
      names.push(info.name);
    }
    expect(names).toEqual(width === 390 ? TABS : ["Hermi, Trips", ...TABS]);
  });
}
