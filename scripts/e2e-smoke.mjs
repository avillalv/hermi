// npm run test:e2e:smoke: smoke checks against the running dev servers (npm run dev). Needs no browser.
// shortcut: plain fetch checks until Playwright arrives (WF-130 kit projects, then the smoke flows of
// 10 section 1.6). Replace this file's checks with the Playwright smoke project then.
import { test } from "node:test";
import assert from "node:assert/strict";

const api = process.env.API_URL ?? "http://127.0.0.1:8100";
const web = process.env.WEB_URL ?? "http://localhost:5173";
const get = (url) => fetch(url, { signal: AbortSignal.timeout(5000) });

test("API answers /health/live with 200", async () => {
  const r = await get(`${api}/health/live`);
  assert.equal(r.status, 200);
  assert.equal((await r.json()).status, "ok");
});

test("web app serves the shell", async () => {
  const r = await get(web);
  assert.equal(r.status, 200);
  assert.match(await r.text(), /<div id="root"/);
});
