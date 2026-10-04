import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
// shortcut: js-yaml is a transitive dependency (eslint). Declare it if eslint drops it.
import yaml from "js-yaml";

const doc = yaml.load(readFileSync(".github/workflows/security.yml", "utf8"));
const text = JSON.stringify(doc);

test("security workflow is not named ci and triggers on PR, push, schedule", () => {
  assert.notEqual(doc.name, "ci");
  for (const t of ["pull_request", "push", "schedule", "workflow_dispatch"]) assert.ok(t in doc.on, t);
});

test("security workflow runs the five tools", () => {
  for (const tool of ["pip-audit", "npm audit", "gitleaks", "codeql-action", "trivy-action"]) {
    assert.ok(text.includes(tool), tool);
  }
});

test("only gitleaks may fail the run", () => {
  for (const [name, job] of Object.entries(doc.jobs)) {
    if (name !== "gitleaks") assert.ok(job["continue-on-error"] === true, `${name} must be non-blocking`);
  }
});

test("gitleaks job is blocking and runs a strict command", () => {
  const job = doc.jobs.gitleaks;
  assert.notEqual(job["continue-on-error"], true);
  for (const step of job.steps) assert.notEqual(step["continue-on-error"], true);
  const run = job.steps.map((s) => s.run ?? "").join("\n");
  for (const part of ["gitleaks detect", "--config .gitleaks.toml", "--redact"]) assert.ok(run.includes(part), part);
  assert.ok(!run.includes("|| true"));
  assert.ok(!run.includes("--exit-code 0"));
  assert.ok(run.includes("sha256sum -c"));
});

test("schedule cron runs on a fixed weekday", () => {
  for (const { cron } of doc.on.schedule) assert.notEqual(cron.split(" ")[4], "*");
});
