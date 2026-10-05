// WF-039: guards for backup-dump.sh and restore-drill.sh, plus the drill itself in --local mode.
// The local run needs PostgreSQL 18 client tools and a reachable local server (npm run db:init);
// without them it skips with a message. Guards need only bash and openssl.
import test from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { findPsql } from "../../scripts/lib/local.mjs";

const here = (f) => fileURLToPath(new URL(f, import.meta.url));
const haveBash = spawnSync("bash", ["-c", "command -v openssl"], { encoding: "utf8" }).status === 0;
const SECRET = "s3cret-key-value-123";
const run = (script, args, env = {}, timeout = 120000) =>
  spawnSync("bash", [here(script), ...args], { encoding: "utf8", timeout, env: { ...process.env, BACKUP_ENCRYPTION_KEY: "", ...env } });
const skip = haveBash ? false : "bash and openssl not available";

test("drill refuses a scratch name that does not start with hermi_", { skip }, () => {
  for (const name of ["postgres", "hermi", "prod", "hermi-test", "HERMI_x", "hermi_x;select 1"]) {
    const r = run("restore-drill.sh", ["--local", "--scratch-db", name]);
    assert.notEqual(r.status, 0, name);
    assert.match(r.stderr, /must start with hermi_/, name);
  }
});

test("drill refuses to run without a key (not in --local)", { skip }, () => {
  const r = run("restore-drill.sh", ["--file", "x.enc"]);
  assert.notEqual(r.status, 0);
  assert.match(r.stderr, /BACKUP_ENCRYPTION_KEY is not set/);
});

test("dump refuses to run without a key", { skip }, () => {
  const r = run("backup-dump.sh", ["--no-upload", "--out", "x.enc"]);
  assert.notEqual(r.status, 0);
  assert.match(r.stderr, /BACKUP_ENCRYPTION_KEY is not set/);
});

test("scripts never print the key, and never put credentials on a command line", { skip }, () => {
  const r = run("restore-drill.sh", ["--file", "does-not-exist.enc", "--scratch-db", "hermi_x"], { BACKUP_ENCRYPTION_KEY: SECRET, R2_SECRET_ACCESS_KEY: SECRET });
  assert.ok(!(r.stdout + r.stderr).includes(SECRET));
  for (const f of ["backup-dump.sh", "backup-lib.sh", "restore-drill.sh"]) {
    const text = readFileSync(here(f), "utf8");
    assert.doesNotMatch(text, /echo[^\n]*(KEY|SECRET|PASSWORD)/, `${f} echoes a secret`);
    assert.doesNotMatch(text, /-pass(?:word)? (?!env:)/, `${f} passes a passphrase on argv`);
    assert.doesNotMatch(text, /postgres(ql)?:\/\/[^\s:$]+:[^\s@$]+@/, `${f} has a literal connection string`);
  }
  const lib = readFileSync(here("backup-lib.sh"), "utf8");
  assert.match(lib, /-pass env:BACKUP_ENCRYPTION_KEY/);
  assert.match(lib, /curl -sS --fail -K -/, "R2 credentials must go to curl on stdin");
});

test("dumps keep owners and grants: no --no-owner or --no-privileges anywhere", { skip }, () => {
  for (const f of ["backup-dump.sh", "backup-lib.sh", "restore-drill.sh", "../../docs/runbooks/restore.md"]) {
    assert.doesNotMatch(readFileSync(here(f), "utf8"), /--no-owner|--no-privileges/, f);
  }
});

test("only hermi_ databases are created or dropped", { skip }, () => {
  const text = readFileSync(here("restore-drill.sh"), "utf8");
  const stmts = [...text.matchAll(/(?:CREATE|DROP) DATABASE[^"]*/g)];
  assert.ok(stmts.length >= 2);
  for (const m of stmts) assert.match(m[0], /\$scratch/, m[0]);
});

const pg = findPsql();
const reachable =
  !!pg && spawnSync(pg, ["-w", "-h", "localhost", "-U", "postgres", "-d", "hermi", "-Atc", "select 1"], { encoding: "utf8" }).stdout?.trim() === "1";

test("drill --local: dump, encrypt, restore, smoke test, PASS", { skip: skip || (!reachable && "PostgreSQL 18 tools or a local hermi database (npm run db:init) not available") }, () => {
  const r = run("restore-drill.sh", ["--local", "--scratch-db", `hermi_drilltest_${process.pid}`]);
  assert.equal(r.status, 0, r.stdout + r.stderr);
  assert.match(r.stdout, /deleted users stay deleted/);
  assert.match(r.stdout, /\nPASS\n/);
  assert.match(r.stdout, /definer functions owned by hermi_definer/);
  assert.match(r.stdout, /row level security still forced/);
  assert.match(r.stdout, /no privileged definer function executable by public/);
  assert.match(r.stdout, /hermi_app can read trips/);
  assert.doesNotMatch(r.stdout + r.stderr, /[0-9a-f]{64}/, "the generated key must never be printed");
});
