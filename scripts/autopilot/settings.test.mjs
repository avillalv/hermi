// Tests that keep the two settings files, the hooks they name and the files in scripts/autopilot/
// honest: same deny list and hooks in both profiles, every rule the plan requires, no dashes, valid syntax.

import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..', '..');
const readJson = (f) => JSON.parse(fs.readFileSync(path.join(HERE, f), 'utf8'));
const auto = readJson('settings.json');
const dontask = readJson('settings-dontask.json');

function listFiles(dir) {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((e) => (e.isDirectory() ? listFiles(path.join(dir, e.name)) : [path.join(dir, e.name)]));
}
const files = listFiles(HERE);

test('env pins the two models and turns auto memory off, in both profiles', () => {
  for (const s of [auto, dontask]) {
    assert.equal(s.env.ANTHROPIC_DEFAULT_OPUS_MODEL, 'claude-opus-5-5');
    assert.equal(s.env.ANTHROPIC_DEFAULT_SONNET_MODEL, 'claude-sonnet-5-5');
    assert.equal(s.env.CLAUDE_CODE_DISABLE_AUTO_MEMORY, '1');
  }
});

const REQUIRED_DENY = [
  'Bash(gh pr merge*)',
  'Bash(git push --force*)',
  'Bash(git push -f*)',
  'Bash(git push origin main*)',
  'Bash(git push origin HEAD:main*)',
  'Read(./.env)',
  'Edit(./.env)',
  'Write(./.env)',
  'Edit(./scripts/autopilot/**)',
  'Write(./scripts/autopilot/**)',
  // fix 4: the Claude settings, the agent definitions and the MCP configuration are owner-controlled too
  'Edit(./.claude/settings*.json)',
  'Write(./.claude/settings*.json)',
  'Edit(./.claude/agents/**)',
  'Write(./.claude/agents/**)',
  'Edit(./.mcp.json)',
  'Write(./.mcp.json)',
];

test('both profiles carry the same deny list, including every rule the plan requires', () => {
  assert.deepEqual(dontask.permissions.deny, auto.permissions.deny);
  for (const rule of REQUIRED_DENY) assert.ok(auto.permissions.deny.includes(rule), rule);
  assert.ok(auto.permissions.deny.some((r) => r.startsWith('WebFetch(domain:airbnb.com')));
});

test('both profiles carry the same three PreToolUse hooks, and the files they run exist', () => {
  assert.deepEqual(dontask.hooks, auto.hooks);
  const pre = auto.hooks.PreToolUse;
  assert.deepEqual(pre.map((h) => h.matcher), ['Agent|Task', 'Bash|PowerShell', 'Read|Grep|Glob']);
  const cmds = pre.map((h) => h.hooks[0].command);
  assert.match(cmds[0], /agent-guard\.mjs/);
  assert.match(cmds[1], /bash-guard\.mjs/);
  assert.match(cmds[2], /file-guard\.mjs/);
  for (const c of cmds) {
    const rel = /\$CLAUDE_PROJECT_DIR\/(\S+?)"/.exec(c)?.[1];
    assert.ok(rel, c);
    assert.ok(fs.existsSync(path.join(ROOT, rel)), `${rel} exists`);
  }
  for (const h of pre) assert.equal(h.hooks[0].type, 'command');
});

test('autoMode: environment, allow rules and hard boundaries are in place, defaults inherited', () => {
  const am = auto.autoMode;
  for (const k of ['environment', 'allow', 'hard_deny']) {
    assert.ok(Array.isArray(am[k]) && am[k][0] === '$defaults', `${k} starts with $defaults`);
  }
  const env = am.environment.join('\n');
  for (const needle of ['C:/Users/matic/code/hermi', 'avillalv/hermi', 'PostgreSQL 18', 'localhost:5432', 'hermi_*', 'npm', 'PyPI', 'unattended autonomous build']) {
    assert.ok(env.includes(needle), `environment mentions ${needle}`);
  }
  const labels = (list) => list.slice(1).map((r) => r.split(':')[0]);
  assert.deepEqual(labels(am.allow), ['Hermi Stack Packages', 'Local npx Binaries', 'Disposable Hermi Databases', 'Hermi Branch Pushes', 'Hermi Pull Requests', 'Local Dev Servers', 'Project Scripts', 'Hermi AI Smoke', 'Sibling Repo Port', 'Build Cleanup']);
  assert.deepEqual(labels(am.hard_deny), ['Autopilot Self-Edit', 'Rental Site Fetching', 'Pull Request Merge', 'Push to Main', 'Push Outside Autopilot Branches', 'Repository Protection Change']);
  const allow = am.allow.join('\n');
  for (const needle of ['react', 'vite', '@tanstack', '@radix-ui', 'shadcn', 'maplibre-gl', '@fullcalendar', 'recharts', '@capacitor', '@playwright/test', 'vitest', 'eslint', 'prettier', 'stylelint', 'fastapi', 'sqlalchemy', 'alembic', 'pydantic', 'procrastinate', 'psycopg', 'httpx', 'pytest', 'playwright install chromium', 'hermi_', 'phase1/*', 'spec/*', 'fix/*']) {
    assert.ok(allow.includes(needle), `allow rules mention ${needle}`);
  }
  assert.ok(am.allow.every((r) => r.length < 3000), 'rules stay readable');
});

test('autoMode rules do not place restrictions inside allow rules (the critique: allow rules are exceptions)', () => {
  const allow = auto.autoMode.allow.slice(1).join('\n');
  assert.ok(!/never allowed|is not allowed|must not/i.test(allow.replace(/does not cover|is not covered|not covered|not part of|not this rule|must not download/gi, '')), 'restrictions belong in hard_deny');
});

// Finding 12: the opt-in dontAsk profile is narrow: npm run and npm ci, node scripts/*, uv run, Read(./**), no global WebFetch.
const SPEC_DONTASK_ALLOW = [
  'Bash(git *)', 'Bash(gh pr create*)', 'Bash(gh pr view*)', 'Bash(gh pr list*)', 'Bash(gh pr checks*)', 'Bash(gh pr ready*)', 'Bash(gh pr edit*)',
  'Bash(gh run *)', 'Bash(gh label *)', 'Bash(npm run *)', 'Bash(npm ci)', 'Bash(npx playwright *)', 'Bash(npx cap *)', 'Bash(npx tsc *)',
  'Bash(npx vitest *)', 'Bash(npx eslint *)', 'Bash(npx prettier *)', 'Bash(npx stylelint *)', 'Bash(uv run *)', 'Bash(node scripts/*)', 'Bash(timeout *)',
  'Bash(ls *)', 'Bash(cat *)', 'Bash(grep *)', 'Bash(find *)', 'Bash(mkdir *)', 'Bash(cp *)', 'Bash(mv *)', 'Bash(rm *)',
  'Edit', 'Write', 'Read(./**)', 'Glob', 'Grep', 'WebSearch', 'Agent', 'Skill',
];
// fix 3c: no session step needs gh api, so the profile does not allow it (a session could change refs or protection through it)
const BROAD_RULES_GONE = ['Bash(npm *)', 'Bash(uv *)', 'Bash(node *)', 'Read', 'WebFetch', 'Bash(gh api *)'];

test('the dontAsk profile has the narrowed allow list and the PostgreSQL 18 binaries', () => {
  for (const r of SPEC_DONTASK_ALLOW) assert.ok(dontask.permissions.allow.includes(r), r);
  for (const r of BROAD_RULES_GONE) assert.ok(!dontask.permissions.allow.includes(r), `${r} is no longer allowed`);
  assert.ok(!dontask.permissions.allow.some((r) => /^WebFetch/.test(r)), 'no WebFetch rule in the allow list');
  assert.ok(dontask.permissions.allow.some((r) => r.includes('C:/Program Files/PostgreSQL/18/bin/psql.exe')));
  assert.equal(dontask.autoMode, undefined, 'dontAsk does not use the classifier');
  assert.equal(auto.permissions.allow, undefined, 'auto mode relies on the classifier, not a broad allow list');
});

test('the Repository Protection Change rule names protection, rulesets and refs of avillalv/hermi', () => {
  const rule = auto.autoMode.hard_deny.find((r) => r.startsWith('Repository Protection Change:'));
  assert.ok(rule, 'rule present');
  for (const needle of ['branch protection', 'rulesets', 'any ref', 'avillalv/hermi', 'gh api', 'GraphQL']) assert.ok(rule.includes(needle), needle);
});

test('both profiles keep the owner\'s claude.ai connectors (Gmail, Drive) out of the session (finding 13)', () => {
  // disableClaudeAiConnectors is a settings key of Claude Code 2.1.288 (it is in the binary's settings schema);
  // --strict-mcp-config on the command line is the other half (see run.test.mjs).
  assert.equal(auto.disableClaudeAiConnectors, true);
  assert.equal(dontask.disableClaudeAiConnectors, true);
});

test('no em or en dash (U+2014, U+2013) anywhere in scripts/autopilot', () => {
  const bad = files.filter((f) => /[\u2013\u2014]/.test(fs.readFileSync(f, 'utf8'))).map((f) => path.relative(ROOT, f));
  assert.deepEqual(bad, []);
});

test('scripts/autopilot holds only .mjs and .json files, with no dependencies', () => {
  const odd = files.filter((f) => !/\.(mjs|json)$/.test(f)).map((f) => path.relative(ROOT, f));
  assert.deepEqual(odd, []);
  assert.ok(!files.some((f) => f.endsWith('package.json')));
});

test('every .mjs file passes a syntax check', () => {
  const bad = [];
  for (const f of files.filter((x) => x.endsWith('.mjs'))) {
    const r = spawnSync(process.execPath, ['--check', f], { encoding: 'utf8' });
    if (r.status !== 0) bad.push(`${path.relative(ROOT, f)}: ${r.stderr.split('\n')[0]}`);
  }
  assert.deepEqual(bad, []);
});

test('driver modules import only the standard library and each other', () => {
  const bad = [];
  for (const f of files.filter((x) => x.endsWith('.mjs'))) {
    for (const m of fs.readFileSync(f, 'utf8').matchAll(/^\s*(?:import|export)[^'"\n]*from\s+['"]([^'"]+)['"]/gm)) {
      const spec = m[1];
      if (!(spec.startsWith('node:') || spec.startsWith('./') || spec.startsWith('../'))) bad.push(`${path.relative(ROOT, f)} imports ${spec}`);
    }
  }
  assert.deepEqual(bad, []);
});
