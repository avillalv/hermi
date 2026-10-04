// node scripts/check-copy.mjs [file]: copy lint over locales/en.json (created in WF-018).
// Passes when the file does not exist yet. Fails on invalid JSON and on em or en dashes in any string.
import { existsSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const DASH = /[\u2013\u2014]/;

export function findDashes(value, path = "") {
  if (typeof value === "string") return DASH.test(value) ? [path] : [];
  if (value && typeof value === "object") {
    return Object.entries(value).flatMap(([k, v]) => findDashes(v, path ? `${path}.${k}` : k));
  }
  return [];
}

export function checkCopy(file) {
  if (!existsSync(file)) return { ok: true, problems: [], skipped: true };
  let data;
  try {
    data = JSON.parse(readFileSync(file, "utf8"));
  } catch (e) {
    return { ok: false, problems: [`${file}: invalid JSON (${e.message})`] };
  }
  const bad = findDashes(data);
  return { ok: bad.length === 0, problems: bad.map((p) => `${file}: em or en dash in "${p}"`) };
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const file = process.argv[2] ?? "locales/en.json";
  const r = checkCopy(file);
  if (r.skipped) console.log(`check-copy: ${file} not found, skipped`);
  for (const p of r.problems) console.error(p);
  process.exit(r.ok ? 0 : 1);
}
