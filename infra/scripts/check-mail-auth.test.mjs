import test from "node:test";
import assert from "node:assert/strict";
import { run } from "./check-mail-auth.mjs";

const records = {
  "hermi.world": ["v=spf1 include:amazonses.com ~all"],
  "resend._domainkey.hermi.world": ["p=MIGfMA0GCSqGSIb3DQEBAQUAA4GN"],
  "_dmarc.hermi.world": ["v=DMARC1; p=none; rua=mailto:dmarc@hermi.world"],
};
const mx = { "hermi.world": [{ exchange: "mx.example.com", priority: 10 }] };

function fake(skip, over = {}, mxThrows = false) {
  return {
    async resolveTxt(name) {
      if (name === skip || !records[name]) throw Object.assign(new Error("nodata"), { code: "ENODATA" });
      return (over[name] || records[name]).map((r) => [r]);
    },
    async resolveMx(name) {
      if (mxThrows) throw new Error("SERVFAIL");
      if (name === skip || !mx[name]) throw Object.assign(new Error("nodata"), { code: "ENODATA" });
      return mx[name];
    },
  };
}
const sink = () => {
  const lines = [];
  return { lines, log: (s) => lines.push(s) };
};

test("all records present exits 0", async () => {
  const o = sink();
  assert.equal(await run(["hermi.world"], fake(), o.log), 0);
});

for (const missing of ["hermi.world", "resend._domainkey.hermi.world", "_dmarc.hermi.world"]) {
  test(`missing ${missing} exits non-zero`, async () => {
    const o = sink();
    assert.notEqual(await run(["hermi.world"], fake(missing), o.log), 0);
  });
}

test("no argument prints usage and exits 2", async () => {
  const o = sink();
  assert.equal(await run([], fake(), o.log), 2);
  assert.match(o.lines.join("\n"), /Usage/);
});

test("empty DKIM key exits non-zero", async () => {
  const o = sink();
  const f = fake(null, { "resend._domainkey.hermi.world": ["v=DKIM1; p="] });
  assert.notEqual(await run(["hermi.world"], f, o.log), 0);
});

test("resolveMx throwing exits non-zero", async () => {
  const o = sink();
  assert.notEqual(await run(["hermi.world"], fake(null, {}, true), o.log), 0);
});

test("two SPF records exit non-zero", async () => {
  const o = sink();
  const f = fake(null, { "hermi.world": ["v=spf1 include:a.com ~all", "v=spf1 include:b.com ~all"] });
  assert.notEqual(await run(["hermi.world"], f, o.log), 0);
});
