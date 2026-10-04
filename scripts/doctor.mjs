// npm run doctor: report what is set and what is optional. Names and states only, never a value.
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { PLACEHOLDER, commandVersion, findPsql, loadEnv, parseEnv, pgpassPath, portInUse, root } from "./lib/local.mjs";

let required = 0;
const line = (state, name, note = "") => console.log(`  ${state.padEnd(8)} ${name}${note ? `  ${note}` : ""}`);
const need = (ok, name, note) => {
  if (!ok) required++;
  line(ok ? "ok" : "MISSING", name, ok ? "" : note);
};
const warn = (ok, name, note) => line(ok ? "ok" : "warn", name, ok ? "" : note);

console.log("Tools");
const [major, minor] = process.versions.node.split(".").map(Number);
need(major > 22 || (major === 22 && minor >= 12), `node ${process.versions.node}`, "needs 22.12 or newer");
const uv = commandVersion("uv");
need(Boolean(uv), uv ?? "uv", "install uv (winget install --id astral-sh.uv -e)");
const psql = findPsql();
warn(Boolean(psql), "PostgreSQL 18 psql", "install PostgreSQL 18 or set PG_BIN to its bin directory (db:init needs it)");
warn(existsSync(pgpassPath()), "pgpass for the postgres user", "db:init connects as postgres through pgpass.conf (HUMAN_TASKS.md)");
warn(Boolean(commandVersion("claude")), "claude CLI", "optional: only for AI_PROVIDER=claude_cli on your machine");

console.log("\nEnvironment (.env overlaid by the process environment)");
const envFile = existsSync(join(root, ".env"));
need(envFile, ".env file", "run npm run setup");
const example = parseEnv(readFileSync(join(root, ".env.example"), "utf8"));
const env = loadEnv();
const state = (k) => {
  const v = env[k];
  if (v === undefined || v === "") return "empty";
  return v.includes(PLACEHOLDER) ? "placeholder" : "set";
};
const core = Object.keys(example).filter((k) => example[k] !== "");
const optional = Object.keys(example).filter((k) => example[k] === "");
const generated = ["FIELD_ENCRYPTION_KEY", "ADMIN_SESSION_SECRET", "UNSUBSCRIBE_SECRET"];
if (envFile) {
  const badCore = core.filter((k) => state(k) !== "set");
  need(badCore.length === 0, `${core.length - badCore.length} of ${core.length} core variables`, `not set or still placeholder: ${badCore.join(", ")} (npm run setup fills the placeholders)`);
  const missingGen = generated.filter((k) => state(k) !== "set");
  warn(missingGen.length === 0, "generated local secrets", `empty: ${missingGen.join(", ")} (npm run setup)`);
}
const setOpt = optional.filter((k) => !generated.includes(k) && state(k) === "set");
const emptyOpt = optional.filter((k) => !generated.includes(k) && state(k) !== "set");
line("optional", `set (${setOpt.length})`, setOpt.join(", "));
line("optional", `not set (${emptyOpt.length})`, "a missing key makes its provider raise NotConfigured; the app still runs on fakes");

console.log("\nPorts");
for (const [port, what] of [[8100, "API"], [5173, "web"]]) {
  line((await portInUse(port)) ? "in use" : "free", `${port} (${what})`);
}

console.log(required ? `\n${required} required item(s) missing.` : "\nAll required items present.");
process.exit(required ? 1 : 0);
