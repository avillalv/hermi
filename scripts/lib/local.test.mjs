import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import net from "node:net";
import { test } from "node:test";
import { dbUrlParts, fillSecrets, isHermiDb, isSafePsqlValue, parseEnv, portInUse, pgBinCandidates, pgpassPath, root } from "./local.mjs";

const example = readFileSync(join(root, ".env.example"), "utf8");
let n = 0;
const gen = () => `g${++n}x`;

test("fillSecrets replaces placeholders and blanks, one password per role, shared with test urls", () => {
  const { text, changed } = fillSecrets(example, gen);
  const env = parseEnv(text);
  assert.ok(!text.includes("change-me"));
  const pw = (k) => dbUrlParts(env[k]).password;
  const roles = ["DATABASE_URL", "DATABASE_URL_SYSTEM", "DATABASE_URL_ADMIN", "MIGRATION_DATABASE_URL"];
  assert.equal(new Set(roles.map(pw)).size, 4);
  assert.equal(pw("TEST_DATABASE_URL"), pw("DATABASE_URL"));
  assert.equal(pw("TEST_MIGRATION_DATABASE_URL"), pw("MIGRATION_DATABASE_URL"));
  assert.ok(env.FIELD_ENCRYPTION_KEY && env.ADMIN_SESSION_SECRET && env.UNSUBSCRIBE_SECRET);
  assert.ok(changed.includes("DATABASE_URL") && changed.includes("FIELD_ENCRYPTION_KEY"));
});

test("fillSecrets never overwrites and is idempotent", () => {
  const first = fillSecrets(example, gen).text;
  const again = fillSecrets(first, gen);
  assert.equal(again.text, first);
  assert.deepEqual(again.changed, []);
  const custom = example.replace("FIELD_ENCRYPTION_KEY=", "FIELD_ENCRYPTION_KEY=mine");
  assert.equal(parseEnv(fillSecrets(custom, gen).text).FIELD_ENCRYPTION_KEY, "mine");
});

test("only hermi databases are allowed", () => {
  for (const ok of ["hermi", "hermi_test", "hermi_scratch1"]) assert.ok(isHermiDb(ok));
  for (const bad of ["postgres", "hermi-x", "other_hermi", "", undefined, "hermi;drop"]) assert.ok(!isHermiDb(bad));
});

test("dbUrlParts reads sqlalchemy urls", () => {
  const p = dbUrlParts("postgresql+psycopg://u:p%40w@localhost:5433/hermi_x");
  assert.deepEqual(p, { user: "u", password: "p@w", host: "localhost", port: "5433", database: "hermi_x" });
});

test("pg bin and pgpass paths by platform", () => {
  assert.ok(pgBinCandidates({}, "win32").some((p) => p.includes("PostgreSQL") && p.includes("18")));
  assert.ok(pgBinCandidates({}, "linux").includes("/usr/lib/postgresql/18/bin"));
  assert.equal(pgBinCandidates({ PG_BIN: "/x" }, "linux")[0], "/x");
  assert.ok(pgpassPath({ APPDATA: "A" }, "win32").endsWith("pgpass.conf"));
  assert.ok(pgpassPath({ HOME: "/h" }, "linux").endsWith(".pgpass"));
});

test("portInUse sees a listener on ::1 and on 127.0.0.1", async (t) => {
  for (const host of ["::1", "127.0.0.1"]) {
    const srv = net.createServer();
    const ok = await new Promise((res) => (srv.once("error", () => res(false)), srv.listen(0, host, () => res(true))));
    if (!ok) {
      t.diagnostic(`${host} unavailable, skipped`);
      continue;
    }
    assert.equal(await portInUse(srv.address().port), true);
    await new Promise((r) => srv.close(r));
  }
});

test("psql values with backslash or line breaks are rejected", () => {
  assert.ok(isSafePsqlValue("abc_-Z9"));
  for (const bad of ["a\\b", "a\nb", "a\rb"]) assert.ok(!isSafePsqlValue(bad));
});
