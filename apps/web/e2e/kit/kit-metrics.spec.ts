import { expect, type Page } from "@playwright/test";
import { openApp, openKit, SCHEMES, test } from "./kit";

const SIDES = ["top", "right", "bottom", "left"];
const PROPS = [
  "display", "position", "box-sizing", "width", "height", "opacity", "gap", "flex-direction", "align-items", "justify-content",
  "font-family", "font-size", "font-weight", "line-height", "letter-spacing", "text-transform", "text-align", "color",
  "background-color", "background-image", "box-shadow", "outline-style", "outline-width", "outline-color",
  ...SIDES.flatMap((s) => [`padding-${s}`, `border-${s}-width`, `border-${s}-style`, `border-${s}-color`]),
  "margin-top", "margin-bottom",
  "border-top-left-radius", "border-top-right-radius", "border-bottom-right-radius", "border-bottom-left-radius",
];

// Left and right margins are not compared as resolved values: Chromium reports `auto` margins of an element that
// overflows a scroll container as 0px or a negative number from run to run. The box position and size (rect) cover them.

/** Computed styles of every h- element, grouped by the doc-block that holds it. */
async function metrics(page: Page) {
  return page.evaluate((props) => {
    const out: Record<string, string[]> = {};
    for (const block of document.querySelectorAll(".doc-block")) {
      out[block.id] = [...block.querySelectorAll(".doc-demo [class*='h-']")]
        .filter((el) => [...el.classList].some((c) => c.startsWith("h-")))
        .map((el) => {
          const cs = getComputedStyle(el);
          const r = el.getBoundingClientRect();
          const name = [...el.classList].filter((c) => c.startsWith("h-")).join(".");
          return `${name} ${props.map((p) => `${p}:${cs.getPropertyValue(p)}`).join(";")};rect:${[r.x, r.width].map(Math.round)}`;
        });
    }
    return out;
  }, PROPS);
}

for (const scheme of SCHEMES) {
  test(`h- components: computed styles match the kit (${scheme})`, async ({ page }) => {
    await openKit(page, "components.html", scheme);
    const kit = await metrics(page);
    await page.unroute("**/__kit/**");
    await openApp(page, "components.html", scheme);
    const app = await metrics(page);
    expect(Object.keys(app)).toEqual(Object.keys(kit));
    expect(Object.values(kit).reduce((n, l) => n + l.length, 0)).toBeGreaterThan(500);
    const diffs: string[] = [];
    for (const id of Object.keys(kit)) {
      expect(app[id].length, `elements in block ${id}`).toBe(kit[id].length);
      kit[id].forEach((k, i) => {
        const [a, b] = [k.split(" ").slice(1).join(" ").split(";"), app[id][i].split(" ").slice(1).join(" ").split(";")];
        a.forEach((v, j) => v !== b[j] && diffs.push(`${id} ${k.split(" ")[0]} ${v} -> ${b[j]}`));
      });
    }
    expect(diffs.slice(0, 20)).toEqual([]);
  });
}
