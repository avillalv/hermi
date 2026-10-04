// WF-009.2: structure guards for the deploy workflows, plus deploy.mjs with an injected fetch.
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import yaml from "js-yaml";
import { deploy } from "./deploy.mjs";

const root = (p) => fileURLToPath(new URL(`../../${p}`, import.meta.url));
const load = (f) => {
  const text = readFileSync(root(`.github/workflows/${f}`), "utf8");
  return { text, doc: yaml.load(text) };
};
const staging = load("deploy-staging.yml");
const prod = load("deploy-prod.yml");

test("staging triggers on push to main and by hand", () => {
  assert.deepEqual(staging.doc.on.push.branches, ["main"]);
  assert.ok("workflow_dispatch" in staging.doc.on);
});

test("prod is manual only, in the production environment, and takes a digest", () => {
  assert.deepEqual(Object.keys(prod.doc.on), ["workflow_dispatch"]);
  assert.ok(prod.doc.on.workflow_dispatch.inputs.image_digest.required);
  assert.equal(prod.doc.jobs.deploy.environment, "production");
  assert.ok(!prod.text.includes("build-push-action"), "prod must not rebuild the image");
});

test("both gate on DEPLOY_ENABLED and skip with a message", () => {
  for (const { text } of [staging, prod]) {
    assert.match(text, /vars\.DEPLOY_ENABLED/);
    assert.match(text, /skipping deploy: missing/);
  }
  assert.equal(staging.doc.jobs.deploy.if, "needs.gate.outputs.enabled == 'true'");
});

test("jobs have timeouts and prod smoke rolls back", () => {
  for (const { doc } of [staging, prod]) for (const j of Object.values(doc.jobs)) assert.ok(j["timeout-minutes"] <= 15);
  assert.ok(staging.doc.jobs.deploy["timeout-minutes"] <= 10);
  assert.match(prod.text, /smoke\.mjs .*--rollback-on-fail/);
});

test("secrets are only referenced, never literal", () => {
  for (const { text } of [staging, prod]) {
    assert.doesNotMatch(text, /(ghp_|sk-ant|rnd_[A-Za-z0-9]{8})/);
    for (const m of text.matchAll(/^\s+(\w*(?:TOKEN|API_KEY|SERVICE_IDS?|ACCOUNT_ID))\s*:\s*(.+)$/gm)) {
      assert.match(m[2], /\$\{\{ secrets\./, m[1]);
    }
  }
});

test("actions are pinned to a major version", () => {
  for (const { text } of [staging, prod]) {
    for (const m of text.matchAll(/uses:\s*(\S+)/g)) assert.match(m[1], /@v\d+$/, m[1]);
  }
});

test("image matches render.yaml", () => {
  const render = readFileSync(root("infra/render/render.yaml"), "utf8");
  for (const { text } of [staging, prod]) assert.ok(render.includes(text.match(/IMAGE: (\S+)/)[1]));
});

test("secrets are never set at job level", () => {
  const hit = /(TOKEN|API_KEY|SERVICE_IDS?|ACCOUNT_ID)$/;
  for (const { doc } of [staging, prod]) {
    for (const j of Object.values(doc.jobs)) {
      for (const k of Object.keys(j.env ?? {})) assert.doesNotMatch(k, hit, `job env ${k}`);
    }
  }
});

test("cloudflare credentials only on the Pages step, render key only on deploy and rollback steps", () => {
  for (const { doc } of [staging, prod]) {
    for (const s of doc.jobs.deploy.steps.filter((x) => x.id !== "gate")) {
      const keys = Object.keys(s.env ?? {});
      const pages = /wrangler/.test(s.run ?? "");
      assert.equal(keys.includes("CLOUDFLARE_API_TOKEN"), pages, s.name);
      if (keys.includes("RENDER_API_KEY")) assert.match(s.run, /(deploy|smoke|rollback)\.mjs/, s.name);
    }
  }
});

test("wrangler is pinned to an exact version", () => {
  for (const { text } of [staging, prod]) assert.match(text, /wrangler@\d+\.\d+\.\d+ /);
});

test("staging installs and builds before the GHCR login", () => {
  const steps = staging.doc.jobs.deploy.steps;
  const at = (re) => steps.findIndex((s) => re.test(`${s.uses ?? ""} ${s.run ?? ""}`));
  assert.ok(at(/npm ci/) < at(/docker\/login-action/));
  assert.ok(at(/build --workspace apps\/web/) < at(/docker\/login-action/));
});

test("prod runs from main only, checks the staging digest, and rolls back what went live", () => {
  assert.equal(prod.doc.jobs.deploy.if, "github.ref == 'refs/heads/main'");
  assert.equal(prod.doc.jobs.deploy.permissions.packages, "read");
  assert.match(prod.text, /imagetools inspect "\$\{IMAGE\}:staging-\$\{GIT_SHA\}"/);
  const last = prod.doc.jobs.deploy.steps.at(-1);
  assert.match(last.if, /^failure\(\)/);
  assert.match(last.run, /rollback\.mjs/);
});

test("deploy waits for live and fails on a failed deploy", async () => {
  const statuses = { a: ["building", "live"], b: ["build_failed"] };
  const fetch = async (url, init = {}) => {
    const svc = url.match(/services\/(\w+)/)[1];
    if (init.method === "POST") return { ok: true, json: async () => ({ id: `d-${svc}` }) };
    return { ok: true, json: async () => ({ status: statuses[svc].shift() }) };
  };
  const o = { fetch, apiKey: "k", wait: async () => {}, log() {} };
  assert.equal(await deploy(["a"], "img@sha256:x", o), 0);
  assert.equal(await deploy(["b"], "img@sha256:x", o), 1);
});

test("deploy runs services in order, stops at the first failure and reports what went live", async () => {
  const order = [];
  const statuses = { api: ["live"], worker: ["live"], bad: ["update_failed"] };
  const fetch = async (url, init = {}) => {
    const svc = url.match(/services\/(\w+)/)[1];
    if (init.method === "POST") { order.push(svc); return { ok: true, json: async () => ({ id: `d-${svc}` }) }; }
    return { ok: true, json: async () => ({ status: statuses[svc].shift() }) };
  };
  const base = { fetch, apiKey: "k", wait: async () => {}, log() {} };
  const live = [];
  assert.equal(await deploy(["api", "worker"], "img@sha256:x", { ...base, live }), 0);
  assert.deepEqual(order, ["api", "worker"]);
  assert.deepEqual(live, ["api", "worker"]);

  order.length = 0;
  statuses.api = ["update_failed"];
  const live2 = [];
  assert.equal(await deploy(["api", "worker"], "img@sha256:x", { ...base, live: live2 }), 1);
  assert.deepEqual(order, ["api"], "worker is not started after the API fails");
  assert.deepEqual(live2, []);

  statuses.api = ["live"];
  const live3 = [];
  assert.equal(await deploy(["api", "bad"], "img@sha256:x", { ...base, live: live3 }), 1);
  assert.deepEqual(live3, ["api"]);
});
