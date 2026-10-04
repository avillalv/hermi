// WF-009.2: post-deploy smoke. Polls <api>/health/ready until 200, then checks the web URL returns 200.
// Usage: node infra/scripts/smoke.mjs --api <url> --web <url> [--rollback-on-fail]
//   (env fallbacks: SMOKE_API_URL, SMOKE_WEB_URL). --rollback-on-fail reads RENDER_API_KEY and
//   ROLLBACK_SERVICE_IDS and rolls those services back when the smoke fails. Exit 1 on failure.
import { pathToFileURL } from "node:url";
import { rollback } from "./rollback.mjs";

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function status(url, fetch, timeoutMs) {
  try {
    return (await fetch(url, { signal: AbortSignal.timeout(timeoutMs), redirect: "follow" })).status;
  } catch {
    return 0;
  }
}

/** Returns 0 when healthy, 1 otherwise. */
export async function smoke({ api, web, fetch = globalThis.fetch, retries = 30, intervalMs = 5000, timeoutMs = 10000, wait = sleep, log = console.log }) {
  const ready = `${api.replace(/\/$/, "")}/health/ready`;
  let ok = false;
  for (let i = 1; i <= retries && !ok; i++) {
    const s = await status(ready, fetch, timeoutMs);
    ok = s === 200;
    log(`${ok ? "ok     " : "WAIT   "} ${ready} -> ${s || "no response"} (try ${i}/${retries})`);
    if (!ok && i < retries) await wait(intervalMs);
  }
  if (!ok) return 1;
  const s = await status(web, fetch, timeoutMs);
  log(`${s === 200 ? "ok     " : "FAILED "} ${web} -> ${s || "no response"}`);
  return s === 200 ? 0 : 1;
}

/** Smoke, and on failure optionally roll back. Always returns the smoke result. */
export async function smokeOrRollback({ rollbackIds = [], rollbackOpts = {}, log = console.log, ...opts }) {
  const code = await smoke({ log, ...opts });
  if (code !== 0 && rollbackIds.length) {
    log("smoke failed, rolling back");
    await rollback(rollbackIds, { log, ...rollbackOpts });
  }
  return code;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const a = process.argv.slice(2);
  const arg = (n) => (a.includes(n) ? a[a.indexOf(n) + 1] : undefined);
  const api = arg("--api") || process.env.SMOKE_API_URL;
  const web = arg("--web") || process.env.SMOKE_WEB_URL;
  if (!api || !web) {
    console.error("usage: node smoke.mjs --api <url> --web <url> [--rollback-on-fail]");
    process.exitCode = 2;
  } else {
    const rollbackIds = a.includes("--rollback-on-fail") ? (process.env.ROLLBACK_SERVICE_IDS ?? "").split(",").filter(Boolean) : [];
    process.exitCode = await smokeOrRollback({ api, web, rollbackIds, rollbackOpts: { apiKey: process.env.RENDER_API_KEY } });
  }
}
