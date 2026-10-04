import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { expect, test as base, type Page } from "@playwright/test";

const here = dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);
export const DESIGN = resolve(here, "../../../../app-buildout/phase-1-launch/design");
export const OUT = resolve(here, "../../../../test-results/kit");
export const FIXED_TIME = new Date("2026-01-15T12:00:00Z");
export const SCHEMES = ["light", "dark"] as const;
export type Scheme = (typeof SCHEMES)[number];

type Font = { pkg: string; file: string; weights: string; family: string };
const FONTS: Record<string, Font> = {
  "fredoka.woff2": { pkg: "fredoka", file: "fredoka-latin-wght-normal.woff2", weights: "300 700", family: "Fredoka" },
  "next.woff2": {
    pkg: "atkinson-hyperlegible-next",
    file: "atkinson-hyperlegible-next-latin-wght-normal.woff2",
    weights: "200 800",
    family: "Atkinson Hyperlegible Next",
  },
  "mono.woff2": {
    pkg: "atkinson-hyperlegible-mono",
    file: "atkinson-hyperlegible-mono-latin-wght-normal.woff2",
    weights: "200 800",
    family: "Atkinson Hyperlegible Mono",
  },
};
const fontPath = (f: Font) => join(dirname(require.resolve(`@fontsource-variable/${f.pkg}/package.json`)), "files", f.file);
const GOOGLE_CSS = Object.entries(FONTS)
  .map(
    ([name, f]) =>
      `@font-face{font-family:"${f.family}";font-weight:${f.weights};font-display:swap;src:url(https://fonts.gstatic.com/${name}) format("woff2");}`,
  )
  .join("\n");

export type Kit = { fontRequests: string[]; unserved: string[] };

/** Kit pages link Google Fonts. Fulfil those requests from the bundled @fontsource files and record each one. */
export const test = base.extend<{ kit: Kit }>({
  kit: [
    async ({ page }, use) => {
      const kit: Kit = { fontRequests: [], unserved: [] };
      await page.route(/(googleapis|gstatic)\.com/, (route) => {
        const url = new URL(route.request().url());
        kit.fontRequests.push(url.href);
        if (url.hostname.endsWith("googleapis.com")) return route.fulfill({ contentType: "text/css", body: GOOGLE_CSS });
        const font = FONTS[url.pathname.slice(1)];
        if (font) return route.fulfill({ contentType: "font/woff2", body: readFileSync(fontPath(font)) });
        kit.unserved.push(url.href);
        return route.abort();
      });
      await page.clock.setFixedTime(FIXED_TIME);
      await use(kit);
      expect(kit.unserved, "googleapis or gstatic requests the route did not serve").toEqual([]);
    },
    { auto: true },
  ],
});

/** Kit page from disk. `rel` is relative to design/ (components.html or screens/NN-name.html). */
export async function openKit(page: Page, rel: string, scheme: Scheme) {
  await page.emulateMedia({ colorScheme: scheme, reducedMotion: "reduce" });
  await page.goto(`${pathToFileURL(join(DESIGN, rel)).href}${scheme === "dark" ? "#dark" : ""}`);
  await ready(page);
}

/**
 * The same kit markup rendered through the app's CSS pipeline: the kit page with its css links swapped for
 * e2e/kit/fixture.css. shortcut: markup comes from the kit file until WF-130.3 renders React components.
 */
export async function openApp(page: Page, rel: string, scheme: Scheme) {
  await page.emulateMedia({ colorScheme: scheme, reducedMotion: "reduce" });
  await page.route(`**/__kit/${rel}`, (r) => {
    const html = readFileSync(join(DESIGN, rel), "utf8")
      .replace(/<link rel="stylesheet" href="(\.\.\/)?(tokens|hermi)\.css">/g, "")
      .replace(/<link rel="stylesheet" href="https:\/\/fonts\.googleapis[^>]*>/, "")
      .replace("<head>", '<head><link rel="stylesheet" href="/e2e/kit/fixture.css">');
    return r.fulfill({ contentType: "text/html", body: html });
  });
  await page.goto(`/__kit/${rel}${scheme === "dark" ? "#dark" : ""}`);
  await ready(page);
}

async function ready(page: Page) {
  await page.waitForLoadState("load");
  // fonts, then two frames so layout (auto margins in scroll containers) has settled
  await page.evaluate(() => document.fonts.ready.then(() => new Promise<void>((r) => requestAnimationFrame(() => requestAnimationFrame(() => r())))));
}
