// npm run db:init: run infra/db/bootstrap.sql as the postgres superuser. Idempotent.
// The superuser password comes from pgpass.conf (never prompted, never stored here). The four role
// passwords come from the effective environment (.env overlaid by the process env) and go to psql
// on stdin, so they never appear in a process list or in output.
import { spawnSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { PLACEHOLDER, ROLE_URL_KEYS, dbUrlParts, findPsql, isHermiDb, isSafePsqlValue, loadEnv, pgpassPath, root } from "./lib/local.mjs";

function fail(msg) {
  console.error(`db:init: ${msg}`);
  process.exit(1);
}

const env = loadEnv();
const psql = findPsql(env);
if (!psql) fail("PostgreSQL 18 client tools not found. Install PostgreSQL 18 or set PG_BIN to its bin directory.");

const roles = Object.fromEntries(Object.entries(ROLE_URL_KEYS).map(([r, k]) => [r, dbUrlParts(env[k])]));
for (const [r, p] of Object.entries(roles)) {
  if (!p.password || p.password === PLACEHOLDER) fail(`${ROLE_URL_KEYS[r]} has no generated password. Run npm run setup first.`);
}
const mainDb = roles.api.database;
const testDb = dbUrlParts(env.TEST_DATABASE_URL).database || `${mainDb}_test`;
for (const db of [mainDb, testDb]) {
  if (!isHermiDb(db)) fail(`database name "${db}" is not allowed. Only hermi and hermi_* databases are created here.`);
}

const pgpass = pgpassPath(env);
if (!env.PGPASSWORD && !existsSync(pgpass)) {
  fail(`no ${pgpass}. Add a line "localhost:5432:*:postgres:<password>" so db:init can connect as postgres (HUMAN_TASKS.md).`);
}

// psql \set values are single-quoted: a backslash or a line break would change their meaning.
const q = (v) => {
  if (!isSafePsqlValue(v)) fail("a role password contains a backslash or line break. Remove it from .env or re-run npm run setup.");
  return `'${String(v).replaceAll("'", "''")}'`;
};
const prelude = [
  ["main_db", mainDb],
  ["test_db", testDb],
  ["migrate_pw", roles.migrate.password],
  ["api_pw", roles.api.password],
  ["worker_pw", roles.worker.password],
  ["admin_pw", roles.admin.password],
]
  .map(([k, v]) => `\\set ${k} ${q(v)}`)
  .join("\n");
const script = readFileSync(join(root, "infra", "db", "bootstrap.sql"), "utf8");

const host = roles.api.host;
const port = roles.api.port;
const r = spawnSync(
  psql,
  ["-X", "-w", "-q", "-v", "ON_ERROR_STOP=1", "-h", host, "-p", port, "-U", "postgres", "-d", "postgres", "-f", "-"],
  { input: `${prelude}\n${script}`, encoding: "utf8", env },
);
if (r.error) fail(`could not run psql: ${r.error.message}`);
if (r.status !== 0) {
  // psql errors name objects, not passwords, but strip any line that echoes a set command to be safe.
  const err = (r.stderr || "").split(/\r?\n/).filter((l) => !/_pw\b|PASSWORD/i.test(l)).join("\n");
  fail(`bootstrap.sql failed (is PostgreSQL running, and is the postgres password in pgpass correct?)\n${err.trim()}`);
}
console.log(`db:init: roles and databases ready (${mainDb}, ${testDb}).`);
