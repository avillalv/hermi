import { mkdirSync, readdirSync, writeFileSync } from "node:fs";
import { expect, type Page } from "@playwright/test";
import pixelmatch from "pixelmatch";
import { PNG } from "pngjs";
import { DESIGN, OUT, openApp, openKit, SCHEMES, test, type Scheme } from "./kit";

const COMPONENT_MAX_RATIO = 0.002; // hard gate: share of differing pixels per component block
const SCREENS = readdirSync(`${DESIGN}/screens`).filter((f) => /^\d\d-.*\.html$/.test(f));

function diff(a: Buffer, b: Buffer, name: string) {
  const [x, y] = [PNG.sync.read(a), PNG.sync.read(b)];
  if (x.width !== y.width || x.height !== y.height) return 1;
  const d = new PNG({ width: x.width, height: x.height });
  const n = pixelmatch(x.data, y.data, d.data, x.width, x.height, { threshold: 0.1 });
  mkdirSync(OUT, { recursive: true });
  for (const [suffix, buf] of [["kit", a], ["app", b], ["diff", PNG.sync.write(d)]] as const) writeFileSync(`${OUT}/${name}-${suffix}.png`, buf);
  return n / (x.width * x.height);
}

/** Screenshot kit, then app, and compare inside this run (no committed baselines). */
async function compare(page: Page, rel: string, scheme: Scheme, name: string, shoot: (p: Page) => Promise<Buffer>) {
  await openKit(page, rel, scheme);
  const kit = await shoot(page);
  await page.unroute("**/__kit/**");
  await openApp(page, rel, scheme);
  return diff(kit, await shoot(page), `${name}-${scheme}`);
}

for (const scheme of SCHEMES) {
  test(`components: each block matches the kit (${scheme})`, async ({ page }) => {
    await openKit(page, "components.html", scheme);
    const ids = await page.$$eval(".doc-block", (els) => els.map((e) => e.id));
    const failures: string[] = [];
    for (const id of ids) {
      const ratio = await compare(page, "components.html", scheme, `components-${id}`, (p) =>
        p.locator(`#${id}`).screenshot({ animations: "disabled" }),
      );
      if (ratio > COMPONENT_MAX_RATIO) failures.push(`${id} ${ratio.toFixed(5)}`);
    }
    expect(failures, "blocks above the diff ratio").toEqual([]);
  });

  for (const file of SCREENS) {
    test(`screen ${file} (${scheme}), evidence only`, async ({ page }) => {
      const ratio = await compare(page, `screens/${file}`, scheme, file.replace(".html", ""), (p) =>
        p.screenshot({ animations: "disabled" }),
      );
      console.log(`parity ${file} ${scheme} diff ratio ${ratio.toFixed(5)} (${OUT})`);
    });
  }
}
