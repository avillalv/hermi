import assert from "node:assert/strict";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import { checkCopy, findDashes } from "./check-copy.mjs";

const tmp = (text) => {
  const f = join(mkdtempSync(join(tmpdir(), "copy-")), "en.json");
  writeFileSync(f, text);
  return f;
};

test("missing file passes", () => {
  assert.equal(checkCopy(join(tmpdir(), "nope-en.json")).ok, true);
});

test("clean strings pass", () => {
  assert.equal(checkCopy(tmp('{"a":{"b":"Plan a trip, together."}}')).ok, true);
});

test("em and en dashes fail with the key path", () => {
  assert.deepEqual(findDashes({ a: { b: "x \u2014 y" }, c: ["1\u20132"] }), ["a.b", "c.0"]);
  const r = checkCopy(tmp('{"a":"x \u2014 y"}'));
  assert.equal(r.ok, false);
  assert.match(r.problems[0], /"a"/);
});

test("invalid JSON fails", () => {
  assert.equal(checkCopy(tmp("{nope")).ok, false);
});
