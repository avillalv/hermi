// WF-009.2: smoke and rollback against local fake servers.
import test from "node:test";
import assert from "node:assert/strict";
import http from "node:http";
import { smoke, smokeOrRollback } from "./smoke.mjs";
import { pickPrevious, rollback } from "./rollback.mjs";

const listen = (handler) =>
  new Promise((resolve) => {
    const s = http.createServer(handler);
    s.listen(0, "127.0.0.1", () => resolve({ s, url: `http://127.0.0.1:${s.address().port}` }));
  });
const quiet = { log() {}, wait: async () => {}, retries: 3 };

async function fixtures({ ready = 200, web = 200 } = {}) {
  const hits = [];
  const app = await listen((req, res) => {
    hits.push(req.url);
    res.statusCode = req.url === "/health/ready" ? ready : 404;
    res.end();
  });
  const site = await listen((req, res) => {
    res.statusCode = web;
    res.end("<html>");
  });
  const calls = [];
  const render = await listen((req, res) => {
    calls.push(`${req.method} ${req.url}`);
    let body = "";
    req.on("data", (c) => (body += c));
    req.on("end", () => {
      if (req.method === "GET") {
        res.setHeader("content-type", "application/json");
        res.end(JSON.stringify([{ deploy: { id: "d3", status: "build_failed" } }, { deploy: { id: "d2", status: "deactivated" } }, { deploy: { id: "d1", status: "deactivated" } }]));
      } else {
        calls.push(body);
        res.end("{}");
      }
    });
  });
  const close = () => [app, site, render].forEach((x) => x.s.close());
  return { app, site, render, hits, calls, close };
}

test("smoke passes when health is 200 and web is 200", async () => {
  const f = await fixtures();
  assert.equal(await smoke({ api: f.app.url, web: f.site.url, ...quiet }), 0);
  assert.deepEqual(f.hits, ["/health/ready"]);
  f.close();
});

test("smoke fails after retries on a failing health check", async () => {
  const f = await fixtures({ ready: 503 });
  assert.equal(await smoke({ api: f.app.url, web: f.site.url, ...quiet }), 1);
  assert.equal(f.hits.length, 3);
  f.close();
});

test("smoke fails when the web URL is not 200", async () => {
  const f = await fixtures({ web: 500 });
  assert.equal(await smoke({ api: f.app.url, web: f.site.url, ...quiet }), 1);
  f.close();
});

test("smoke fails when nothing listens", async () => {
  assert.equal(await smoke({ api: "http://127.0.0.1:1", web: "http://127.0.0.1:1", ...quiet, retries: 1 }), 1);
});

test("failed smoke triggers a rollback to the previous good deploy", async () => {
  const f = await fixtures({ ready: 503 });
  const code = await smokeOrRollback({ api: f.app.url, web: f.site.url, ...quiet, rollbackIds: ["srv-1", "srv-2"], rollbackOpts: { apiKey: "k", base: f.render.url } });
  assert.equal(code, 1);
  assert.deepEqual(f.calls.filter((c) => c.startsWith("POST")), ["POST /services/srv-1/rollback", "POST /services/srv-2/rollback"]);
  assert.ok(f.calls.includes('{"deployId":"d2"}'));
  f.close();
});

test("passing smoke never rolls back", async () => {
  const f = await fixtures();
  assert.equal(await smokeOrRollback({ api: f.app.url, web: f.site.url, ...quiet, rollbackIds: ["srv-1"], rollbackOpts: { apiKey: "k", base: f.render.url } }), 0);
  assert.deepEqual(f.calls, []);
  f.close();
});

test("rollback reports failure when there is no previous good deploy", async () => {
  assert.equal(pickPrevious([{ deploy: { id: "a", status: "live" } }]), null);
  const fetch = async () => ({ ok: true, json: async () => [{ id: "a", status: "build_failed" }] });
  assert.equal(await rollback(["srv"], { fetch, apiKey: "k", log() {} }), 1);
});
