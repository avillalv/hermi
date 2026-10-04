// WF-009.2: deploy an image to Render services and wait until each deploy is live.
// Usage: RENDER_API_KEY=... node infra/scripts/deploy.mjs <image-ref> <serviceId>[,<serviceId>...]
// Migrations are not run here: render.yaml preDeployCommand runs `hermi migrate` before traffic moves.
import { appendFileSync } from "node:fs";
import { pathToFileURL } from "node:url";

const FAILED = new Set(["build_failed", "update_failed", "pre_deploy_failed", "canceled", "deactivated"]);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

export async function deployService(serviceId, imageUrl, { fetch = globalThis.fetch, apiKey, base = "https://api.render.com/v1", wait = sleep, polls = 60, intervalMs = 10000, log = console.log } = {}) {
  const headers = { Authorization: `Bearer ${apiKey}`, Accept: "application/json", "Content-Type": "application/json" };
  const start = await fetch(`${base}/services/${serviceId}/deploys`, { method: "POST", headers, body: JSON.stringify({ imageUrl }) });
  if (!start.ok) throw new Error(`trigger failed: ${start.status}`);
  const id = (await start.json()).id;
  for (let i = 0; i < polls; i++) {
    const res = await fetch(`${base}/services/${serviceId}/deploys/${id}`, { headers });
    const status = res.ok ? (await res.json()).status : "unknown";
    if (status === "live") return log(`${serviceId} deploy ${id} is live`);
    if (FAILED.has(status)) throw new Error(`deploy ${id} ended as ${status}`);
    await wait(intervalMs);
  }
  throw new Error(`deploy ${id} not live after ${polls} polls`);
}

/** Deploy one service at a time, in the order given (API first, then worker); stop at the first failure.
 * Services that went live are appended to opts.live (an array) so a caller can roll them back. */
export async function deploy(serviceIds, imageUrl, opts = {}) {
  const log = opts.log ?? console.log;
  for (const id of serviceIds) {
    try {
      await deployService(id, imageUrl, opts);
      opts.live?.push(id);
    } catch (e) {
      log(`DEPLOY FAILED for ${id}: ${e.message}`);
      return 1;
    }
  }
  return 0;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const [image, ids] = process.argv.slice(2);
  const list = (ids ?? "").split(",").filter(Boolean);
  if (!image || !list.length || !process.env.RENDER_API_KEY) {
    console.error("usage: RENDER_API_KEY=... node deploy.mjs <image-ref> <serviceId>[,<serviceId>...]");
    process.exitCode = 2;
  } else {
    const live = [];
    process.exitCode = await deploy(list, image, { apiKey: process.env.RENDER_API_KEY, live });
    // The prod workflow reads this to roll back services that already went live.
    if (process.env.GITHUB_OUTPUT) appendFileSync(process.env.GITHUB_OUTPUT, `live=${live.join(",")}
`);
  }
}
