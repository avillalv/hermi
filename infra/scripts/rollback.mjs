// WF-009.2: roll Render services back to their previous successful deploy.
// Usage: RENDER_API_KEY=... node infra/scripts/rollback.mjs <serviceId>[,<serviceId>...]
// Exit 0 when every service was rolled back, 1 otherwise. Pure functions take an injected fetch.
import { pathToFileURL } from "node:url";

const LIVE = new Set(["live", "deactivated"]);

/** Newest-first deploy list in; the id of the previous successful deploy out (index 0 is the current one). */
export function pickPrevious(deploys) {
  return deploys.map((d) => d.deploy ?? d).slice(1).find((d) => LIVE.has(d.status))?.id ?? null;
}

export async function rollbackService(serviceId, { fetch = globalThis.fetch, apiKey, base = "https://api.render.com/v1", log = console.log } = {}) {
  const headers = { Authorization: `Bearer ${apiKey}`, Accept: "application/json", "Content-Type": "application/json" };
  const list = await fetch(`${base}/services/${serviceId}/deploys?limit=20`, { headers });
  if (!list.ok) throw new Error(`list deploys failed: ${list.status}`);
  const deployId = pickPrevious(await list.json());
  if (!deployId) throw new Error(`no previous successful deploy for ${serviceId}`);
  const res = await fetch(`${base}/services/${serviceId}/rollback`, { method: "POST", headers, body: JSON.stringify({ deployId }) });
  if (!res.ok) throw new Error(`rollback failed: ${res.status}`);
  log(`rolled back ${serviceId} to deploy ${deployId}`);
  return deployId;
}

export async function rollback(serviceIds, opts = {}) {
  const log = opts.log ?? console.log;
  let code = 0;
  for (const id of serviceIds) {
    try {
      await rollbackService(id, opts);
    } catch (e) {
      log(`ROLLBACK FAILED for ${id}: ${e.message}`);
      code = 1;
    }
  }
  return code;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const ids = (process.argv[2] ?? "").split(",").filter(Boolean);
  if (!ids.length || !process.env.RENDER_API_KEY) {
    console.error("usage: RENDER_API_KEY=... node rollback.mjs <serviceId>[,<serviceId>...]");
    process.exitCode = 2;
  } else {
    process.exitCode = await rollback(ids, { apiKey: process.env.RENDER_API_KEY });
  }
}
