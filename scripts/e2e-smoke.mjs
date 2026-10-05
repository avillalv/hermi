// Fetch checks against the running dev servers (npm run dev). npm run test:e2e:smoke runs these, then the Playwright smoke project.
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
