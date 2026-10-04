// node scripts/wait-ready.mjs [timeoutSeconds]: wait until the API and the web app answer. Exits 1 on timeout.
// The API check uses /health/ready when it exists and falls back to /health/live (ready arrives in WF-008).
const api = process.env.API_URL ?? "http://127.0.0.1:8100";
const web = process.env.WEB_URL ?? "http://localhost:5173";
const deadline = Date.now() + Number(process.argv[2] ?? 60) * 1000;

async function ok(url) {
  try {
    return (await fetch(url, { signal: AbortSignal.timeout(2000) })).ok;
  } catch {
    return false;
  }
}
async function apiReady() {
  const r = await fetch(`${api}/health/ready`, { signal: AbortSignal.timeout(2000) }).catch(() => null);
  if (r?.status === 404) return ok(`${api}/health/live`);
  return Boolean(r?.ok);
}

let a = false;
let w = false;
while (Date.now() < deadline && !(a && w)) {
  a = a || (await apiReady());
  w = w || (await ok(web));
  if (!(a && w)) await new Promise((r) => setTimeout(r, 500));
}
console.log(`api ${a ? "ready" : "NOT ready"} (${api}), web ${w ? "ready" : "NOT ready"} (${web})`);
process.exit(a && w ? 0 : 1);
