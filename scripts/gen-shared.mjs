// Writes apps/api/hermi/analytics_catalogue.json from the blocks in packages/shared/src/events.ts (the one source).
import fs from "node:fs";

const src = fs.readFileSync("packages/shared/src/events.ts", "utf8");
const block = (name) => {
  const m = src.match(new RegExp(String.raw`// BEGIN ${name}\r?\n[^=]*= (\{[\s\S]*?\}) as const;\r?\n// END ${name}`));
  if (!m) throw new Error(`events.ts: block ${name} not found`);
  return JSON.parse(m[1].replace(/,(\s*\})/g, "$1"));
};
const out = { events: block("EVENT_CATALOGUE"), common: block("COMMON_PROPERTIES") };
fs.writeFileSync("apps/api/hermi/analytics_catalogue.json", JSON.stringify(out, null, 1) + "\n");
console.log(`gen:shared: ${Object.keys(out.events).length} events`);
