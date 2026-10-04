// WF-009: guards for infra/render/render.yaml. Run by `npm test` (scripts/test.mjs).
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import yaml from "js-yaml";

const doc = yaml.load(readFileSync(new URL("./render.yaml", import.meta.url), "utf8"));
const services = doc.services ?? [];
const databases = doc.databases ?? [];
const byName = (n) => services.find((s) => s.name === n);
const SECRET_NAME = /(SECRET|TOKEN|PASSWORD|PRIVATE|DSN|DATABASE_URL|API_KEY|SERVICE_ROLE|ENCRYPTION_KEY|WEBHOOK_URL)/;
const groupsOf = (n) => byName(n).envVars.filter((e) => e.fromGroup).map((e) => e.fromGroup);
const valueOf = (n, k) => byName(n).envVars.find((e) => e.key === k)?.value;
const ENVS = {
  staging: { api: "hermi-api-staging", worker: "hermi-worker-staging", db: "hermi-db-staging", groups: { api: ["hermi-staging"], worker: ["hermi-staging"] } },
  production: { api: "hermi-api-prod", worker: "hermi-worker-prod", db: "hermi-db-prod", groups: { api: ["hermi-prod-shared", "hermi-prod-api"], worker: ["hermi-prod-shared", "hermi-prod-worker"] } },
};

for (const [env, n] of Object.entries(ENVS)) {
  test(`${env}: api and worker exist and pin AI_PROVIDER=anthropic_api`, () => {
    for (const name of [n.api, n.worker]) {
      const s = byName(name);
      assert.ok(s, `${name} missing`);
      const v = s.envVars.find((e) => e.key === "AI_PROVIDER");
      assert.equal(v?.value, "anthropic_api", `${name} AI_PROVIDER`);
      assert.equal(s.envVars.find((e) => e.key === "ENVIRONMENT")?.value, env);
    }
  });

  test(`${env}: Postgres 18 on a PITR-capable plan`, () => {
    const d = databases.find((x) => x.name === n.db);
    assert.ok(d, `${n.db} missing`);
    assert.equal(String(d.postgresMajorVersion), "18");
    assert.doesNotMatch(d.plan, /^(free|starter)/, "free and starter plans have no PITR");
  });

  test(`${env}: API has a pre-deploy migration`, () => {
    assert.match(byName(n.api).preDeployCommand, /^sh -c "hermi migrate && /);
  });

  test(`${env}: services take secrets from the right env groups`, () => {
    assert.deepEqual(groupsOf(n.api), n.groups.api);
    assert.deepEqual(groupsOf(n.worker), n.groups.worker);
  });

  test(`${env}: every service pins the live backends`, () => {
    const want = { ADMIN_AUTH_MODE: "cf_access", STORAGE_BACKEND: "r2", EMAIL_BACKEND: "resend", PROVIDERS_MODE: "live" };
    for (const name of [n.api, n.worker]) {
      for (const [k, v] of Object.entries(want)) assert.equal(valueOf(name, k), v, `${name}.${k}`);
    }
    assert.equal(valueOf(n.worker, "AUTH_MODE"), "supabase");
    assert.equal(valueOf(n.api, "AUTH_MODE"), "supabase");
    for (const name of [n.api, n.worker]) {
      assert.equal(byName(name).envVars.find((e) => e.key === "DATABASE_URL_ADMIN")?.sync, false, name);
    }
  });
}

test("no literal secret values", () => {
  for (const s of services) {
    for (const e of s.envVars ?? []) {
      if (e.fromGroup || e.fromDatabase) continue;
      if (SECRET_NAME.test(e.key)) {
        assert.equal(e.value, undefined, `${s.name}.${e.key} has a literal value`);
        assert.equal(e.sync, false, `${s.name}.${e.key} must be sync: false`);
      }
    }
  }
  assert.doesNotMatch(readFileSync(new URL("./render.yaml", import.meta.url), "utf8"), /postgres(ql)?(\+\w+)?:\/\/[^\s:]+:[^\s@]+@/);
});

test("staging and production are separate", () => {
  const names = [...services.map((s) => s.name), ...databases.map((d) => d.name)];
  assert.equal(new Set(names).size, names.length, "duplicate names");
  const prod = [...groupsOf(ENVS.production.api), ...groupsOf(ENVS.production.worker)];
  for (const g of [...groupsOf(ENVS.staging.api), ...groupsOf(ENVS.staging.worker)]) assert.ok(!prod.includes(g), `${g} shared`);
  assert.notEqual(byName(ENVS.staging.api).envVars.find((e) => e.key === "PUBLIC_API_URL").value, byName(ENVS.production.api).envVars.find((e) => e.key === "PUBLIC_API_URL").value);
  assert.equal(byName(ENVS.production.api).envVars.find((e) => e.key === "API_DOCS_ENABLED").value, "false");
});

test("deploys are never automatic (the workflows promote an image digest)", () => {
  for (const s of services) assert.equal(s.autoDeploy, false, s.name);
});
