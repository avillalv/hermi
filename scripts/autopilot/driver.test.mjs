// End-to-end simulation of the driver. The REAL driver (copied into a scratch repository) runs against
// real git, a bare "origin", a fake `gh` and a fake `claude` (test-support/). The fakes do what the
// sessions in AUTOPILOT.md do and print Claude Code 2.1.288 style streams, so plan, ticket, ship, CI,
// merge, retries, limits, stops and the exit codes are exercised without spending quota or touching
// GitHub. Each scenario takes a few seconds.

import assert from 'node:assert/strict';
import { spawn, spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { after, describe, it } from 'node:test';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const FAKE_CLAUDE = path.join(HERE, 'test-support', 'fake-claude.mjs');
const FAKE_GH = path.join(HERE, 'test-support', 'fake-gh.mjs');
const made = [];
after(() => {
  for (const d of made) fs.rmSync(d, { recursive: true, force: true, maxRetries: 5 });
});

const git = (cwd, ...args) => {
  const r = spawnSync('git', args, { cwd, encoding: 'utf8' });
  if (r.status !== 0) throw new Error(`git ${args.join(' ')} failed in ${cwd}: ${r.stderr}`);
  return r.stdout.trim();
};
const write = (root, rel, text) => {
  fs.mkdirSync(path.dirname(path.join(root, rel)), { recursive: true });
  fs.writeFileSync(path.join(root, rel), text);
};

const PROGRESS = `# Phase 1 progress

## Prompts

| # | Prompt | Tickets | Status |
|---|---|---|---|
| 01 | [Demo unit](01-demo-unit.md) | WF-001, WF-002 | Not started |
`;
const PROMPT = `# Prompt 01: Demo unit

## Tickets, in this order

| Ticket | Title |
|---|---|
| WF-001 | First thing |
| WF-002 | Second thing |
`;

/** A scratch world: bare origin, a work clone holding the driver, fake gh state. */
function world(scenario = {}, { progress = PROGRESS, files = {} } = {}) {
  const T = fs.mkdtempSync(path.join(os.tmpdir(), 'autopilot-sim-'));
  made.push(T);
  const origin = path.join(T, 'origin.git');
  const work = path.join(T, 'work');
  const state = path.join(T, 'state');
  fs.mkdirSync(state);
  git(T, 'init', '--quiet', '--bare', '--initial-branch=main', origin);
  git(T, 'clone', '--quiet', origin, work);
  for (const [k, v] of [['user.name', 'Sim'], ['user.email', 'sim@example.com'], ['core.autocrlf', 'false'], ['commit.gpgsign', 'false']]) git(work, 'config', k, v);
  write(work, '.gitignore', '.autopilot/\n.claude/handoff/\nnode_modules/\n');
  write(work, 'app-buildout/prompts/AUTOPILOT.md', '# fake\n');
  write(work, 'app-buildout/prompts/PROGRESS.md', progress);
  write(work, 'app-buildout/prompts/01-demo-unit.md', PROMPT);
  for (const a of ['opus-reviewer', 'opus-judge', 'sonnet-coder', 'sonnet-researcher']) write(work, `.claude/agents/${a}.md`, `---\nname: ${a}\n---\n`);
  for (const [rel, text] of Object.entries(files)) write(work, rel, text);
  fs.cpSync(HERE, path.join(work, 'scripts', 'autopilot'), { recursive: true, filter: (s) => !s.includes('node_modules') });
  git(work, 'add', '-A');
  git(work, 'commit', '--quiet', '-m', 'init');
  git(work, 'push', '--quiet', '-u', 'origin', 'main');
  fs.writeFileSync(path.join(state, 'scenario.json'), JSON.stringify(scenario));
  const vars = {
    AUTOPILOT_CLAUDE: process.execPath,
    AUTOPILOT_CLAUDE_PREARGS: JSON.stringify([FAKE_CLAUDE]),
    AUTOPILOT_GH: process.execPath,
    AUTOPILOT_GH_PREARGS: JSON.stringify([FAKE_GH]),
    AUTOPILOT_PORTS: '[]',
    AUTOPILOT_LIMIT_GRACE_MS: '150',
    AUTOPILOT_CI_POLL_MS: '100',
    AUTOPILOT_CI_MISSING_RETRIES: '3',
    FAKE_STATE_DIR: state,
  };
  const w = { T, origin, work, state, vars };
  w.run = (args = ['--once']) =>
    new Promise((resolve) => {
      const child = spawn(process.execPath, ['scripts/autopilot/run.mjs', ...args], { cwd: work, env: { ...process.env, ...vars }, windowsHide: true });
      let out = '';
      child.stdout.on('data', (d) => (out += d));
      child.stderr.on('data', (d) => (out += d));
      const timer = setTimeout(() => child.kill(), 240000);
      child.on('close', (code) => {
        clearTimeout(timer);
        resolve({ code, out });
      });
    });
  w.calls = () => {
    try {
      return fs.readFileSync(path.join(state, 'calls.jsonl'), 'utf8').split('\n').filter(Boolean).map((l) => JSON.parse(l));
    } catch {
      return [];
    }
  };
  w.gh = () => JSON.parse(fs.readFileSync(path.join(state, 'gh.json'), 'utf8'));
  w.driverState = () => JSON.parse(fs.readFileSync(path.join(work, '.autopilot', 'state.json'), 'utf8'));
  w.mainLog = () => git(origin, 'log', 'main', '--format=%s').split('\n');
  w.mainFile = (f) => git(origin, 'show', `main:${f}`);
  w.setScenario = (s) => fs.writeFileSync(path.join(state, 'scenario.json'), JSON.stringify(s));
  w.setGh = (fn) => {
    const g = w.gh();
    fn(g);
    fs.writeFileSync(path.join(state, 'gh.json'), JSON.stringify(g));
  };
  return w;
}

const modes = (calls) => calls.map((c) => `${c.mode}${c.step ? `:${c.step}` : ''}`);

describe('driver simulation', { concurrency: 8, skip: process.env.AUTOPILOT_SKIP_SIM === '1' ? 'AUTOPILOT_SKIP_SIM=1' : false }, () => {
// ---------------------------------------------------------------------------------------------

it('happy path: plan, two tickets, ship, CI, squash merge, state and PROGRESS', async () => {
  const w = world();
  const r = await w.run();
  assert.equal(r.code, 0, r.out);
  assert.match(r.out, /MERGED: 01 \(PR #1\) is on main/);
  const calls = w.calls();
  assert.deepEqual(modes(calls), ['plan', 'ticket:WF-001', 'ticket:WF-002', 'ship']);
  assert.deepEqual(calls.map((c) => c.model), ['claude-opus-5-5', 'claude-sonnet-5-5', 'claude-sonnet-5-5', 'claude-sonnet-5-5']);
  assert.ok(calls.every((c) => c.permission === 'auto' && c.settings === 'scripts/autopilot/settings.json'));
  assert.match(calls[0].stdin, /^MODE=plan UNIT=01 ATTEMPT=1\n/);
  assert.match(calls[1].stdin, /^MODE=ticket UNIT=01 STEP=WF-001 PR=1 ATTEMPT=1\n/);
  assert.match(w.mainLog()[0], /^Phase 1 \/ P01: demo \(#1\)$/);
  assert.match(w.mainFile('app-buildout/prompts/PROGRESS.md'), /\| 01 \| \[Demo unit\]\(01-demo-unit\.md\) \| WF-001, WF-002 \| Done \(#1\) \|/);
  const st = w.driverState();
  assert.equal(st.phase, 'merged');
  assert.equal(st.unit, '01');
  assert.deepEqual(Object.keys(st.approvals).sort(), ['WF-001', 'WF-002']);
  assert.equal(st.approvals['WF-001'].model, 'claude-opus-5-5');
  assert.equal(st.sessions.length, 4);
  assert.equal(w.gh().prs[1].state, 'MERGED');
  assert.equal(git(w.origin, 'branch', '--list', 'phase1/*'), '', 'the PR branch was deleted on origin');
  assert.equal(git(w.work, 'rev-parse', '--abbrev-ref', 'HEAD'), 'main');
  assert.equal(git(w.work, 'status', '--porcelain'), '');
  assert.equal(git(w.work, 'stash', 'list'), '');
  assert.equal(fs.readdirSync(path.join(w.work, '.autopilot', 'logs')).length, 4);
  assert.match(r.out, /autopilot: exit 0 \(done\) \| merged this run: 01/);
});

it('status.mjs reads the run without loading big files', async () => {
  const w = world();
  assert.equal((await w.run()).code, 0);
  const s = spawnSync(process.execPath, ['scripts/autopilot/status.mjs'], { cwd: w.work, env: { ...process.env, ...w.vars }, encoding: 'utf8' });
  assert.equal(s.status, 0);
  assert.match(s.stdout, /unit:\s+01\s+phase: merged/);
  assert.match(s.stdout, /progress: 1 of 1 prompts Done on main; all rows Done/);
  assert.match(s.stdout, /newest log: 01-ship-/);
  assert.match(s.stdout, /\| fake ship 01 attempt 1/);
});

it('a missing Opus approval makes the ticket session run again, with a RETRY_NOTE that names the verdict line', async () => {
  const w = world({ rules: [{ match: { mode: 'ticket', step: 'WF-002', attempt: 1 }, do: 'no-approval' }] });
  const r = await w.run();
  assert.equal(r.code, 0, r.out);
  const wf2 = w.calls().filter((c) => c.step === 'WF-002');
  assert.deepEqual(wf2.map((c) => c.attempt), [1, 2]);
  assert.match(wf2[1].stdin, /RETRY_NOTE: .*VERDICT: APPROVE WF-002/);
  assert.equal(Object.keys(w.driverState().attempts).length, 0);
});

it('a Sonnet APPROVE is not an approval', async () => {
  const w = world({ rules: [{ match: { mode: 'ticket', step: 'WF-001', attempt: 1 }, do: 'sonnet-approval' }] });
  const r = await w.run();
  assert.equal(r.code, 0, r.out);
  assert.equal(w.calls().filter((c) => c.step === 'WF-001').length, 2);
  assert.equal(w.driverState().approvals['WF-001'].model, 'claude-opus-5-5');
});

it('commits a session left unpushed are pushed by the driver, so the step is not redone', async () => {
  const w = world({ rules: [{ match: { mode: 'ticket', step: 'WF-001', attempt: 1 }, do: 'leave-unpushed' }] });
  const r = await w.run();
  assert.equal(r.code, 0, r.out);
  assert.equal(w.calls().filter((c) => c.step === 'WF-001').length, 1);
});

it('a step with no commit is retried', async () => {
  const w = world({ rules: [{ match: { mode: 'ticket', step: 'WF-001', attempt: 1 }, do: 'no-commit' }] });
  const r = await w.run();
  assert.equal(r.code, 0, r.out);
  const wf1 = w.calls().filter((c) => c.step === 'WF-001');
  assert.equal(wf1.length, 2);
  assert.match(wf1[1].stdin, /RETRY_NOTE: .*no commit whose subject starts with "WF-001 "/);
});

it('three failed attempts stop the unit: stop.json, label on the PR, exit 2, and the next start refuses', async () => {
  const w = world({ rules: [1, 2, 3].map((attempt) => ({ match: { mode: 'ticket', step: 'WF-001', attempt }, do: 'no-approval' })) });
  const r = await w.run();
  assert.equal(r.code, 2, r.out);
  assert.match(r.out, /STOPPED on unit 01: step WF-001 did not complete in 3 attempts/);
  assert.equal(w.calls().filter((c) => c.step === 'WF-001').length, 3);
  const stop = JSON.parse(fs.readFileSync(path.join(w.work, '.autopilot', 'stop.json'), 'utf8'));
  assert.equal(stop.unit, '01');
  assert.match(stop.ownerAction, /remove-label autopilot:stopped/);
  assert.deepEqual(w.gh().prs[1].labels, ['autopilot:stopped']);
  assert.equal(w.driverState().phase, 'stopped');
  const before = w.calls().length;
  const again = await w.run();
  assert.equal(again.code, 2);
  assert.match(again.out, /stopped on unit 01/);
  assert.equal(w.calls().length, before, 'no session started');
});

it('plan retries when the plan file is missing or invalid', async () => {
  const w = world({ rules: [{ match: { mode: 'plan', attempt: 1 }, do: 'no-plan' }, { match: { mode: 'plan', attempt: 2 }, do: 'bad-plan' }] });
  const r = await w.run();
  assert.equal(r.code, 0, r.out);
  const plans = w.calls().filter((c) => c.mode === 'plan');
  assert.equal(plans.length, 3);
  assert.match(plans[1].stdin, /RETRY_NOTE: .*was not written/);
  assert.match(plans[2].stdin, /RETRY_NOTE: .*not valid JSON/);
});

it('CI fails once: a ci-fix session gets the FAILED_CHECKS block, then the driver merges the new head', async () => {
  const w = world({ ci: { default: ['fail', 'pass'] } });
  const r = await w.run();
  assert.equal(r.code, 0, r.out);
  const fix = w.calls().filter((c) => c.mode === 'ci-fix');
  assert.equal(fix.length, 1);
  assert.match(fix[0].stdin, /^MODE=ci-fix UNIT=01 PR=1 ATTEMPT=1\nFAILED_CHECKS:\n- ci \(fail\)/);
  assert.match(fix[0].stdin, /AssertionError: ceiling not enforced/);
  assert.equal(fix[0].model, 'claude-sonnet-5-5');
  assert.equal(w.driverState().ciFixAttempts, 1);
  assert.equal(w.gh().prs[1].state, 'MERGED');
  assert.ok(w.mainLog().some((s) => /P01: demo/.test(s)));
});

it('CI still red after three ci-fix sessions: label, stop.json, exit 2', async () => {
  const w = world({ ci: { default: ['fail'] } });
  const r = await w.run();
  assert.equal(r.code, 2, r.out);
  assert.match(r.out, /CI is still red on PR #1 after 3 ci-fix sessions/);
  assert.deepEqual(w.calls().filter((c) => c.mode === 'ci-fix').map((c) => c.attempt), [1, 2, 3]);
  assert.ok(w.gh().prs[1].labels.includes('autopilot:stopped'));
  assert.equal(w.gh().prs[1].state, 'OPEN');
});

// Finding 1: only a check named ci that passed lets the driver merge. Nothing else (a green lint job, a skipped ci,
// an empty list) counts, and there is no fallback to "watch all checks".
it('a green check that is not named ci never merges: the driver waits, then stops (exit 2) with the PR still open', async () => {
  const w = world({ checks: 'other-only' });
  const r = await w.run();
  assert.equal(r.code, 2, r.out);
  assert.match(r.out, /No check named "ci" has passed or failed on PR #1/);
  assert.equal(w.gh().prs[1].state, 'OPEN');
  assert.ok(!w.gh().calls.some((c) => c.startsWith('pr merge')), 'gh pr merge was never called');
  assert.equal(w.calls().filter((c) => c.mode === 'ci-fix').length, 0, 'a missing check is not a red CI');
});

it('no checks reported yet, or a skipped ci, are not a pass either', async () => {
  const none = world({ checks: 'none' });
  const r1 = await none.run();
  assert.equal(r1.code, 2, r1.out);
  assert.match(r1.out, /No check named "ci"/);
  assert.equal(none.gh().prs[1].state, 'OPEN');
  const skipped = world({ ci: { default: ['skipping'] } });
  const r2 = await skipped.run();
  assert.equal(r2.code, 2, r2.out);
  assert.match(r2.out, /missing or skipped/);
  assert.equal(skipped.gh().prs[1].state, 'OPEN');
});

it('ci still pending is polled, not merged; a lint job that passes beside it changes nothing', async () => {
  const w = world({ pendingPolls: 3, checks: 'with-other' });
  const r = await w.run();
  assert.equal(r.code, 0, r.out);
  assert.equal(w.gh().prs[1].state, 'MERGED');
  assert.ok(w.gh().calls.filter((c) => c.startsWith('pr checks')).length >= 4, 'it polled until ci finished');
});

it('usage limit: sleeps until the reset, resumes the SAME session, and does not use up an attempt', async () => {
  const w = world({ rules: [{ match: { mode: 'ship', attempt: 1, resumed: false }, do: 'limit' }] });
  const r = await w.run();
  assert.equal(r.code, 0, r.out);
  assert.match(r.out, /PAUSED \(five_hour limit\)/);
  assert.match(r.out, /pause over; resuming/);
  const ship = w.calls().filter((c) => c.mode === 'ship');
  assert.equal(ship.length, 2);
  assert.equal(ship[1].resumed, true);
  assert.equal(ship[1].sid, ship[0].sid);
  assert.equal(ship[1].attempt, 1);
  assert.equal(ship[1].stdin.trim(), 'Continue the task from where you stopped.');
  assert.equal(w.driverState().pause, null);
});

it('a session that writes stop.json halts the run with its reason and owner action', async () => {
  const w = world({ rules: [{ match: { mode: 'ship' }, do: 'stop' }] });
  const r = await w.run();
  assert.equal(r.code, 2, r.out);
  assert.match(r.out, /spec-conflict/);
  assert.match(r.out, /Decide which document wins and rerun/);
  assert.equal(w.driverState().phase, 'stopped');
});

it('five permission denials in one session: exit 3 with every denial listed', async () => {
  const w = world({ rules: [{ match: { mode: 'plan' }, do: 'denials' }] });
  const r = await w.run();
  assert.equal(r.code, 3, r.out);
  for (let i = 0; i < 5; i++) assert.match(r.out, new RegExp(`${i + 1}\\. Bash \\{"command":"cmd${i}"\\}`));
  assert.match(r.out, /autoMode\.allow/);
  assert.equal(w.calls().length, 1, 'no retry');
});

it('paid extra usage: the session is killed and the driver exits 4', async () => {
  const w = world({ rules: [{ match: { mode: 'plan' }, do: 'overage' }] });
  const r = await w.run();
  assert.equal(r.code, 4, r.out);
  assert.match(r.out, /extra usage is on: turn it off in claude\.ai settings/);
  assert.match(r.out, /killing the session: overage/);
  assert.equal(w.calls().length, 1);
});

it('an authentication error exits 5 and is never retried', async () => {
  const w = world({ rules: [{ match: { mode: 'plan' }, do: 'auth-error' }] });
  const r = await w.run();
  assert.equal(r.code, 5, r.out);
  assert.match(r.out, /claude auth login/);
  assert.equal(w.calls().length, 1);
});

// Finding 12: the driver never loosens the rules by itself.
it('auto mode not available: the driver stops with exit 1 and an owner action, and does NOT switch to dontAsk', async () => {
  const w = world({ rules: [{ match: { mode: 'plan' }, do: 'wrong-permission' }] });
  const r = await w.run();
  assert.equal(r.code, 1, r.out);
  assert.match(r.out, /Auto mode is not available/);
  assert.match(r.out, /Owner action: .*--permission-profile dontask/);
  const calls = w.calls();
  assert.equal(calls.length, 1, 'no second session under another profile');
  assert.equal(calls[0].permission, 'auto');
  assert.equal(w.driverState().permissionFallback, undefined);
});

it('--permission-profile dontask is the opt-in: every session runs in dontAsk with the narrowed settings file', async () => {
  const w = world({ rules: [{ match: { mode: 'plan' }, do: 'wrong-permission' }] }); // the act only bites in auto mode
  const r = await w.run(['--once', '--permission-profile', 'dontask']);
  assert.equal(r.code, 0, r.out);
  assert.match(r.out, /running with the dontAsk profile/);
  const calls = w.calls();
  assert.ok(calls.length >= 4 && calls.every((c) => c.permission === 'dontAsk' && c.settings === 'scripts/autopilot/settings-dontask.json'));
});

it('a session that changes scripts/autopilot is caught after the session', async () => {
  const w = world({ rules: [{ match: { mode: 'ticket', step: 'WF-001' }, do: 'edit-autopilot' }] });
  const r = await w.run();
  assert.equal(r.code, 2, r.out);
  assert.match(r.out, /a session changed owner-controlled files \(scripts\/autopilot\/, \.claude\/agents\/, \.claude\/settings\.json, \.mcp\.json\): scripts\/autopilot\/lib\/task\.mjs/);
  assert.ok(w.gh().prs[1].labels.includes('autopilot:stopped'));
});

it('fix 4: a session that changes .claude/agents, .claude/settings.json or .mcp.json is caught after the session', async () => {
  for (const [act, file] of [['edit-agents', '.claude/agents/opus-judge.md'], ['edit-claude-settings', '.claude/settings.json'], ['edit-mcp', '.mcp.json']]) {
    const w = world({ rules: [{ match: { mode: 'ticket', step: 'WF-001' }, do: act }] });
    const r = await w.run();
    assert.equal(r.code, 2, `${act}: ${r.out}`);
    assert.ok(r.out.includes(`a session changed owner-controlled files (scripts/autopilot/, .claude/agents/, .claude/settings.json, .mcp.json): ${file}`), `${act}: ${r.out}`);
    assert.ok(w.gh().prs[1].labels.includes('autopilot:stopped'), act);
    assert.equal(w.gh().prs[1].state, 'OPEN', act);
  }
});

it('a draft PR after ship means ship runs again; a missing e2e label is added by the driver', async () => {
  const draft = world({ rules: [{ match: { mode: 'ship', attempt: 1 }, do: 'forget-ready' }] });
  const r1 = await draft.run();
  assert.equal(r1.code, 0, r1.out);
  const ship = draft.calls().filter((c) => c.mode === 'ship');
  assert.equal(ship.length, 2);
  assert.match(ship[1].stdin, /RETRY_NOTE: .*still a draft/);

  const label = world({ rules: [{ match: { mode: 'ship' }, do: 'forget-label' }] });
  const r2 = await label.run();
  assert.equal(r2.code, 0, r2.out);
  assert.equal(label.calls().filter((c) => c.mode === 'ship').length, 1, 'no second session for a label');
  assert.match(r2.out, /added the e2e label to PR #1/);
});

it('a red main is repaired first: ci-fix UNIT=main opens a fix PR, which the driver merges, then the unit runs', async () => {
  const w = world({ mainCi: 'failure' });
  const r = await w.run();
  assert.equal(r.code, 0, r.out);
  const calls = w.calls();
  assert.equal(calls[0].mode, 'ci-fix');
  assert.equal(calls[0].unit, 'main');
  assert.match(calls[0].stdin, /^MODE=ci-fix UNIT=main ATTEMPT=1\nFAILED_CHECKS:\n- ci \(fail\)/);
  assert.equal(calls[1].mode, 'plan');
  assert.ok(w.mainLog().some((s) => /ci-fix: repair main/.test(s)));
  assert.equal(w.gh().prs[1].headRefName, 'fix/main-ci-20260101');
  assert.equal(w.gh().prs[1].state, 'MERGED');
  assert.equal(w.driverState().unit, '01');
});

it('FINAL: one final session opens phase1/final and the PR, the driver merges it', async () => {
  const w = world();
  const r = await w.run(['--unit', 'FINAL']);
  assert.equal(r.code, 0, r.out);
  assert.deepEqual(modes(w.calls()), ['final']);
  assert.equal(w.calls()[0].model, 'claude-opus-5-5');
  assert.match(w.calls()[0].stdin, /^MODE=final UNIT=FINAL ATTEMPT=1\n/);
  assert.match(w.mainFile('docs/gates/phase-1-complete.md'), /Phase 1 complete/);
  assert.equal(w.gh().prs[1].state, 'MERGED');
  const plan = JSON.parse(fs.readFileSync(path.join(w.work, '.autopilot', 'plans', 'FINAL.json'), 'utf8'));
  assert.deepEqual({ unit: plan.unit, branch: plan.branch, pr: plan.pr, steps: plan.steps.length }, { unit: 'FINAL', branch: 'phase1/final', pr: 1, steps: 0 });
});

it('all prompts Done and the gate on main: Phase 1 complete, exit 0, no session', async () => {
  const w = world({}, { progress: PROGRESS.replace('Not started', 'Done (#7)') });
  write(w.work, 'docs/gates/phase-1-complete.md', '# done\n');
  git(w.work, 'add', '-A');
  git(w.work, 'commit', '--quiet', '-m', 'gate');
  git(w.work, 'push', '--quiet', 'origin', 'main');
  const r = await w.run([]);
  assert.equal(r.code, 0, r.out);
  assert.match(r.out, /Phase 1 complete/);
  assert.equal(w.calls().length, 0);
});

it('a Stopped row on main halts with exit 2 before any session', async () => {
  const w = world({}, { progress: PROGRESS.replace('Not started', 'Stopped (spec-conflict: decide which document wins)') });
  const r = await w.run();
  assert.equal(r.code, 2, r.out);
  assert.match(r.out, /PROGRESS\.md says 01 is Stopped \(spec-conflict: decide which document wins\)/);
  assert.equal(w.calls().length, 0);
});

it('preflight refuses a live second driver and an active PR-train handoff', async () => {
  const w = world();
  fs.mkdirSync(path.join(w.work, '.autopilot'), { recursive: true });
  fs.writeFileSync(path.join(w.work, '.autopilot', 'lock'), JSON.stringify({ pid: process.pid, startedAt: 'now', childPid: null }));
  const locked = await w.run();
  assert.equal(locked.code, 1, locked.out);
  assert.match(locked.out, /another driver is running/);
  fs.rmSync(path.join(w.work, '.autopilot', 'lock'));
  write(w.work, '.claude/handoff/train.md', '---\nstatus: active\n---\n# train\n');
  const handoff = await w.run();
  assert.equal(handoff.code, 2, handoff.out);
  assert.match(handoff.out, /active PR-train handoff: train\.md/);
  assert.equal(w.calls().length, 0);
});

it('a stale lock (dead pid) is taken over', async () => {
  const w = world();
  fs.mkdirSync(path.join(w.work, '.autopilot'), { recursive: true });
  fs.writeFileSync(path.join(w.work, '.autopilot', 'lock'), JSON.stringify({ pid: 2147483000, startedAt: 'long ago', childPid: null }));
  const r = await w.run();
  assert.equal(r.code, 0, r.out);
});

it('a dirty tree is stashed (never discarded) and the driver says so', async () => {
  const w = world();
  write(w.work, 'scratch-notes.txt', 'unsaved owner work\n');
  const r = await w.run();
  assert.equal(r.code, 0, r.out);
  assert.match(r.out, /working tree was dirty: stashed it as "autopilot-/);
  assert.match(git(w.work, 'stash', 'list'), /autopilot-/);
  assert.match(git(w.work, 'stash', 'show', '--include-untracked', '--stat', 'stash@{0}'), /scratch-notes\.txt/);
});

it('dry run: reports every check and the exact command, changes nothing, starts no session', async () => {
  const w = world();
  const r = await w.run(['--dry-run']);
  assert.equal(r.code, 0, r.out);
  assert.match(r.out, /dry run: nothing is changed/);
  assert.match(r.out, /Next session: plan on claude-opus-5-5/);
  assert.match(r.out, /stdin:\s+MODE=plan UNIT=01 ATTEMPT=1/);
  assert.match(r.out, /--permission-mode auto --permission-prompts none --output-format stream-json --verbose --forward-subagent-text --strict-mcp-config --disallowedTools AskUserQuestion EnterPlanMode EnterWorktree CronCreate RemoteTrigger ScheduleWakeup Workflow Monitor --name hermi-01-plan/);
  assert.match(r.out, /All checks pass: a real run would start\./);
  assert.equal(w.calls().length, 0);
  assert.equal(fs.existsSync(path.join(w.work, '.autopilot')), false);
  assert.equal(git(w.work, 'status', '--porcelain'), '');
});

it('dry run reports each failure with its fix', async () => {
  const w = world();
  write(w.work, '.claude/handoff/train.md', '---\nstatus: active\n---\n');
  const r = await w.run(['--dry-run']);
  assert.equal(r.code, 2, r.out);
  assert.match(r.out, /\[FAIL\] active PR-train handoff: train\.md\n\s+Fix: Finish the train/);
  assert.match(r.out, /1 check\(s\) would stop a real run/);
});

it('resume after a stop: the owner clears it and the same unit continues from its plan, with no second plan session', async () => {
  const w = world({ rules: [{ match: { mode: 'ticket', step: 'WF-001', attempt: 1 }, do: 'stop' }] });
  const first = await w.run();
  assert.equal(first.code, 2, first.out);
  fs.rmSync(path.join(w.work, '.autopilot', 'stop.json'));
  w.setScenario({});
  const second = await w.run();
  assert.equal(second.code, 0, second.out);
  assert.match(second.out, /plan for 01 exists \(2 step\(s\), branch phase1\/p01-demo-unit, PR #1\)/);
  assert.deepEqual(modes(w.calls()), ['plan', 'ticket:WF-001', 'ticket:WF-001', 'ticket:WF-002', 'ship']);
  assert.equal(w.gh().prs[1].state, 'MERGED');
});

it('a hung session is killed by the idle watchdog and resumed, and that counts as an attempt', async () => {
  const w = world({ rules: [{ match: { mode: 'ticket', step: 'WF-001', attempt: 1, resumed: false }, do: 'hang' }] });
  w.vars.AUTOPILOT_IDLE_MS = '4000';
  const r = await w.run();
  assert.equal(r.code, 0, r.out);
  assert.match(r.out, /killing the session: watchdog-idle/);
  const wf1 = w.calls().filter((c) => c.step === 'WF-001');
  assert.equal(wf1.length, 2);
  assert.equal(wf1[1].resumed, true);
  assert.equal(wf1[1].sid, wf1[0].sid);
  assert.equal(wf1[1].stdin.trim(), 'Continue the task from where you stopped.');
  assert.equal(w.driverState().sessions.find((x) => x.result === 'killed:watchdog-idle').mode, 'ticket');
});

it('a killed session that left .git/index.lock behind does not break the next git command', async () => {
  const w = world({ rules: [{ match: { mode: 'ticket', step: 'WF-001', attempt: 1, resumed: false }, do: 'lock-and-hang' }] });
  w.vars.AUTOPILOT_IDLE_MS = '4000';
  const r = await w.run();
  assert.equal(r.code, 0, r.out);
  assert.match(r.out, /removed git lock file\(s\) left by the killed session: index\.lock/);
  assert.equal(fs.existsSync(path.join(w.work, '.git', 'index.lock')), false);
  assert.equal(w.gh().prs[1].state, 'MERGED');
});

it('a weekly Opus limit kills the session, pauses the whole run, then resumes: judgement never falls back to Sonnet', async () => {
  const w = world({ rules: [{ match: { mode: 'ticket', step: 'WF-001', attempt: 1, resumed: false }, do: 'opus-limit' }] });
  const r = await w.run();
  assert.equal(r.code, 0, r.out);
  assert.match(r.out, /killing the session: opus-weekly/);
  assert.match(r.out, /PAUSED \(weekly Opus limit/);
  const wf1 = w.calls().filter((c) => c.step === 'WF-001');
  assert.equal(wf1.length, 2);
  assert.equal(wf1[1].resumed, true);
});

it('canary: four short sessions with the real flags, each judged PASS or FAIL', async () => {
  const ok = world();
  const r1 = await ok.run(['--canary']);
  assert.equal(r1.code, 0, r1.out);
  assert.match(r1.out, /PASS  canary a: opus-judge runs on Opus, sonnet-researcher on Sonnet, auto mode is on/);
  assert.match(r1.out, /PASS  canary b: everyday commands run with zero permission denials/);
  assert.match(r1.out, /PASS  canary c: cat \.env\.canary \(a decoy name\) is blocked by the bash-guard hook/);
  assert.match(r1.out, /PASS  canary d: a general-purpose agent on Opus is blocked by the agent-guard hook/);
  assert.match(r1.out, /All canaries PASS/);
  const calls = ok.calls();
  assert.equal(calls.length, 4);
  assert.ok(calls.every((c) => c.model === 'claude-sonnet-5-5' && c.permission === 'auto'));
  assert.match(calls[0].stdin, /^Use the opus-judge agent to reply OK, then the sonnet-researcher agent to reply OK\. Call each agent with run_in_background false\. Then stop\./);
  assert.match(calls[1].stdin, /git status --short; node --version; npm --version; uv --version; node scripts\/spec-lint\.mjs/);
  assert.match(calls[2].stdin, /exactly once with the command: cat \.env\.canary\n/);
  assert.match(calls[3].stdin, /subagent_type "general-purpose", model "opus"/);

  const bad = world({ canaryBad: true });
  const r2 = await bad.run(['--canary']);
  assert.equal(r2.code, 1, r2.out);
  assert.match(r2.out, /FAIL  canary a/);
  assert.match(r2.out, /opus-judge ran on: claude-sonnet-5-5/);
  assert.match(r2.out, /FAIL  canary b/);
  assert.match(r2.out, /FAIL  canary c/);
  assert.match(r2.out, /the command was NOT refused: it ran/);
  assert.match(r2.out, /FAIL  canary d/);
  assert.match(r2.out, /the agent was NOT refused/);
  assert.match(r2.out, /4 canary check\(s\) FAILED/);

  // Finding 21: a refusal by a permission denial alone does not prove the hook works.
  const noHook = world({ canaryNoHook: true });
  const r3 = await noHook.run(['--canary']);
  assert.equal(r3.code, 1, r3.out);
  assert.match(r3.out, /FAIL  canary c/);
  assert.match(r3.out, /no bash-guard hook block was seen/);
});

it('a whole run: S1, then 01, then FINAL, then Phase 1 complete with exit 0', async () => {
  const progress = `# Phase 1 progress

## Setup prompts

| # | Prompt | Tickets | Status |
|---|---|---|---|
| S1 | [Demo spec fixes](S1-spec-demo.md) | S1.1 | Not started |

## Prompts

| # | Prompt | Tickets | Status |
|---|---|---|---|
| 01 | [Demo unit](01-demo-unit.md) | WF-001, WF-002 | Not started |
`;
  const s1 = '# S1\n\n## Tickets, in this order\n\n| Ticket | Title |\n|---|---|\n| S1.1 | Edit the README |\n';
  const w = world({ stepsByUnit: { S1: [{ id: 'S1.1', ticket: 'S1.1', title: 'Edit the README' }] } }, { progress, files: { 'app-buildout/prompts/S1-spec-demo.md': s1 } });
  const r = await w.run([]);
  assert.equal(r.code, 0, r.out);
  assert.match(r.out, /Phase 1 complete/);
  assert.match(r.out, /merged this run: S1, 01, FINAL/);
  assert.deepEqual(modes(w.calls()), ['plan', 'ticket:S1.1', 'ship', 'plan', 'ticket:WF-001', 'ticket:WF-002', 'ship', 'final']);
  assert.deepEqual([1, 2, 3].map((n) => w.gh().prs[n].headRefName), ['spec/s1-spec-demo', 'phase1/p01-demo-unit', 'phase1/final']);
  const prog = w.mainFile('app-buildout/prompts/PROGRESS.md');
  assert.match(prog, /\| S1 \|.*\| Done \(#1\) \|/);
  assert.match(prog, /\| 01 \|.*\| Done \(#2\) \|/);
  assert.match(w.mainFile('docs/gates/phase-1-complete.md'), /Phase 1 complete/);
  assert.equal(w.mainLog().filter((x) => /\(#\d\)$/.test(x)).length, 3, 'three squash merges');
});

// ---------------------------------------------------------------------------------------------
// Review findings: one or more tests per gap (see .claude/handoff/driver-review.md)
// ---------------------------------------------------------------------------------------------

/** Run the driver in a mini script inside the scratch repository (its ROOT), for the git helpers that have no CLI. */
const inWorld = (w, code) => spawnSync(process.execPath, ['--input-type=module', '-e', code], { cwd: w.work, encoding: 'utf8', env: { ...process.env, ...w.vars } });

it('finding 2: main must be protected, require ci and apply to administrators; a real run exits 2 with the exact owner action, the dry run prints everything and still reports FAIL', async () => {
  const cases = [
    ['none', /\[FAIL\] main has no branch protection/],
    ['no-ci', /\[FAIL\] main protection does not require the "ci" status check/],
    ['no-admins', /\[FAIL\] main protection is not enforced for administrators/],
    ['no-pr', /\[FAIL\] main protection does not require a pull request, so a commit whose ci passed can be pushed to main directly/],
  ];
  await Promise.all(
    cases.map(async ([protection, re]) => {
      const w = world({ protection });
      const dry = await w.run(['--dry-run']);
      assert.equal(dry.code, 2, `${protection}: ${dry.out}`);
      assert.match(dry.out, re, protection);
      assert.match(dry.out, /Do not allow bypassing the above settings/, 'the fix is the exact action');
      assert.match(dry.out, /gh api -X PUT repos\/\{owner\}\/\{repo\}\/branches\/main\/protection/);
      assert.match(dry.out, /Require a pull request before merging/, 'the fix says to require a pull request');
      assert.match(dry.out, /"required_pull_request_reviews":\{"required_approving_review_count":0\}/, 'the command requires a pull request with 0 approvals');
      assert.match(dry.out, /Next session: plan on claude-opus-5-5/, 'the dry run still prints the rest');
      assert.match(dry.out, /1 check\(s\) would stop a real run\./);
      assert.equal(w.calls().length, 0);
      assert.equal(fs.existsSync(path.join(w.work, '.autopilot')), false, 'the dry run changed nothing');
      const real = await w.run(['--once']);
      assert.equal(real.code, 2, `${protection}: ${real.out}`);
      assert.match(real.out, /Fix: GitHub, Settings, Branches, Add classic branch protection rule/);
      assert.equal(w.calls().length, 0, 'no session starts without protection');
    }),
  );
});

it('fix 4: a .claude/settings.local.json in the checkout stops the run before any session (exit 2) with the owner action; without it the check is ok', async () => {
  const clean = world();
  const ok = await clean.run(['--dry-run']);
  assert.equal(ok.code, 0, ok.out);
  assert.match(ok.out, /\[ ok \] no \.claude\/settings\.local\.json/);

  const w = world();
  write(w.work, '.claude/settings.local.json', '{"hooks":{}}\n');
  const dry = await w.run(['--dry-run']);
  assert.equal(dry.code, 2, dry.out);
  assert.match(dry.out, /\[FAIL\] \.claude\/settings\.local\.json exists in the checkout/);
  assert.match(dry.out, /Fix: delete \.claude\/settings\.local\.json \(it can disable the hooks\)/);
  const real = await w.run(['--once']);
  assert.equal(real.code, 2, real.out);
  assert.match(real.out, /Fix: delete \.claude\/settings\.local\.json \(it can disable the hooks\)/);
  assert.equal(w.calls().length, 0, 'no session starts with a local settings file');
});

it('fix 9: a plan session that commits anything but PROGRESS.md stops the unit (exit 2) before any ticket session', async () => {
  const w = world({ rules: [{ match: { mode: 'plan' }, do: 'plan-extra' }] });
  const r = await w.run();
  assert.equal(r.code, 2, r.out);
  assert.ok(r.out.includes('the plan session changed files other than app-buildout/prompts/PROGRESS.md on phase1/p01-demo-unit: src-by-plan.txt'), r.out);
  assert.deepEqual(modes(w.calls()), ['plan']);
  assert.ok(w.gh().prs[1].labels.includes('autopilot:stopped'));
});

it('fix 9: a plan session that resumes a branch already holding code is judged by what it added, not by the whole branch', async () => {
  const w = world({ rules: [{ match: { mode: 'plan', attempt: 1 }, do: 'plan-extra-bad' }] });
  const r = await w.run();
  assert.equal(r.code, 0, r.out);
  assert.deepEqual(modes(w.calls()).slice(0, 2), ['plan', 'plan']);
  assert.equal(w.gh().prs[1].state, 'MERGED');
});

it('fix 9: right before the merge, a commit for a step id that no valid Opus APPROVE covers stops the unit', async () => {
  const w = world({ rules: [{ match: { mode: 'ticket', step: 'WF-002' }, do: 'extra-commit' }] });
  const r = await w.run();
  assert.equal(r.code, 2, r.out);
  assert.match(r.out, /phase1\/p01-demo-unit holds commit\(s\) for WF-099 that no valid Opus APPROVE covers/);
  assert.equal(w.gh().prs[1].state, 'OPEN');
  assert.ok(w.gh().prs[1].labels.includes('autopilot:stopped'));
  assert.ok(!w.gh().calls.some((c) => c.startsWith('pr merge')), 'gh pr merge was never called');
});

it('finding 3: right before gh pr merge the driver looks again: stop.json, the stopped label, a draft PR and the Done row each stop it', async () => {
  const cases = [
    ['stop.json appears while CI runs', { duringCi: { stop: true } }, /The session stopped on unit 01: spec-conflict/],
    ['the stopped label appears while CI runs', { duringCi: { label: 'autopilot:stopped' } }, /PR #1 is labelled autopilot:stopped/],
    ['the PR is a draft again', { duringCi: { draft: true } }, /PR #1 is a draft again/],
    ['a ci-fix session changed the Done row', { ci: { default: ['fail', 'pass'] }, rules: [{ match: { mode: 'ci-fix' }, do: 'unmark-done' }] }, /no longer says "Done \(#1\)"/],
  ];
  await Promise.all(
    cases.map(async ([name, scenario, re]) => {
      const w = world(scenario);
      const r = await w.run();
      assert.equal(r.code, 2, `${name}: ${r.out}`);
      assert.match(r.out, re, name);
      assert.equal(w.gh().prs[1].state, 'OPEN', name);
      assert.ok(!w.gh().calls.some((c) => c.startsWith('pr merge')), `${name}: gh pr merge was never called`);
    }),
  );
});

it('finding 4: FINAL needs VERDICT: APPROVE FINAL from opus-judge, and the final session is rerun until it has one', async () => {
  const w = world({ rules: [{ match: { mode: 'final', attempt: 1 }, do: 'no-approval' }] });
  const r = await w.run(['--unit', 'FINAL']);
  assert.equal(r.code, 0, r.out);
  const finals = w.calls().filter((c) => c.mode === 'final');
  assert.deepEqual(finals.map((c) => c.attempt), [1, 2]);
  assert.match(finals[1].stdin, /RETRY_NOTE: .*no "VERDICT: APPROVE FINAL" from the opus-judge agent/);
  assert.equal(w.driverState().approvals.FINAL.agent, 'opus-judge');

  const never = world({ rules: [1, 2, 3].map((attempt) => ({ match: { mode: 'final', attempt }, do: 'no-approval' })) });
  const r2 = await never.run(['--unit', 'FINAL']);
  assert.equal(r2.code, 2, r2.out);
  assert.match(r2.out, /the final session did not complete in 3 attempts: .*VERDICT: APPROVE FINAL/);
  assert.equal(never.gh().prs[1].state, 'OPEN');
});

it('finding 4: a ci-fix needs opus-judge\'s ci-fix-<pr>-<n> verdict before the merge, and a PR that got one merges', async () => {
  const w = world({ ci: { default: ['fail', 'pass'] }, rules: [{ match: { mode: 'ci-fix' }, do: 'no-approval' }] });
  const r = await w.run();
  assert.equal(r.code, 2, r.out);
  assert.match(r.out, /CI is green but there is no valid Opus APPROVE for: ci-fix-1-1/);
  assert.equal(w.gh().prs[1].state, 'OPEN');
  assert.deepEqual(Object.keys(w.driverState().required), ['ci-fix-1-1']);

  const ok = world({ ci: { default: ['fail', 'pass'] } });
  assert.equal((await ok.run()).code, 0);
  assert.equal(ok.driverState().approvals['ci-fix-1-1'].agent, 'opus-judge');
  assert.equal(ok.gh().prs[1].state, 'MERGED');
});

it('finding 4: the fix PR for a red main needs ci-fix-<pr>-<n> too', async () => {
  const w = world({ mainCi: 'failure', rules: [{ match: { mode: 'ci-fix', unit: 'main' }, do: 'no-approval' }] });
  const r = await w.run();
  assert.equal(r.code, 2, r.out);
  assert.match(r.out, /CI is green but there is no valid Opus APPROVE for: ci-fix-1-1/);
  assert.equal(w.gh().prs[1].state, 'OPEN');
  assert.equal(w.calls().filter((c) => c.mode === 'plan').length, 0, 'the unit did not start');
});

it('finding 4: a ship diff outside docs, status logs, knowledge, skills, API types and seed needs VERDICT: APPROVE ship-<unit> from opus-reviewer', async () => {
  const docs = world({ rules: [{ match: { mode: 'ship' }, do: 'ship-docs' }] });
  assert.equal((await docs.run()).code, 0);
  assert.equal(docs.driverState().approvals['ship-01'], undefined, 'a documents-only ship diff needs no second review');
  assert.deepEqual(docs.driverState().required, {});

  const approved = world({ rules: [{ match: { mode: 'ship' }, do: 'ship-code-approved' }] });
  const r = await approved.run();
  assert.equal(r.code, 0, r.out);
  assert.equal(approved.driverState().approvals['ship-01'].agent, 'opus-reviewer');
  assert.deepEqual(approved.driverState().required['ship-01'].files, ['src/ship-extra.txt']);
  assert.equal(approved.mainFile('src/ship-extra.txt').trim(), 'a late code change made while shipping');

  const unreviewed = world({ rules: [1, 2, 3].map((attempt) => ({ match: { mode: 'ship', attempt }, do: 'ship-code' })) });
  const r2 = await unreviewed.run();
  assert.equal(r2.code, 2, r2.out);
  assert.match(r2.out, /need "VERDICT: APPROVE ship-01" from the opus-reviewer agent/);
  assert.match(r2.out, /src\/ship-extra\.txt/);
  assert.equal(unreviewed.gh().prs[1].state, 'OPEN');
});

it('finding 5: a ticket session earns only its own step\'s verdict (a verdict it prints for another step is ignored), and approvals carry their branch and PR', async () => {
  const w = world({
    rules: [{ match: { mode: 'ticket', step: 'WF-001', attempt: 1 }, do: 'extra-approval' }, ...[1, 2, 3].map((attempt) => ({ match: { mode: 'ticket', step: 'WF-002', attempt }, do: 'no-approval' }))],
  });
  const r = await w.run();
  assert.equal(r.code, 2, r.out);
  assert.match(r.out, /step WF-002 did not complete in 3 attempts/);
  const approvals = w.driverState().approvals;
  assert.deepEqual(Object.keys(approvals), ['WF-001'], 'the WF-002 verdict printed by the WF-001 session did not count');
  assert.equal(approvals['WF-001'].branch, 'phase1/p01-demo-unit');
  assert.equal(approvals['WF-001'].pr, 1);
});

it('finding 5: writing a new plan clears every approval, so the steps are reviewed again', async () => {
  const w = world({ rules: [1, 2, 3].map((attempt) => ({ match: { mode: 'ticket', step: 'WF-002', attempt }, do: 'no-approval' })) });
  assert.equal((await w.run()).code, 2);
  assert.deepEqual(Object.keys(w.driverState().approvals), ['WF-001']);
  // the owner clears the stop and the plan file, so a plan session runs again on the same branch and PR
  fs.rmSync(path.join(w.work, '.autopilot', 'stop.json'));
  fs.rmSync(path.join(w.work, '.autopilot', 'plans', '01.json'));
  w.setGh((g) => (g.prs[1].labels = []));
  w.setScenario({});
  const r = await w.run();
  assert.equal(r.code, 0, r.out);
  assert.deepEqual(modes(w.calls()), ['plan', 'ticket:WF-001', 'ticket:WF-002', 'ticket:WF-002', 'ticket:WF-002', 'plan', 'ticket:WF-001', 'ticket:WF-002', 'ship']);
});

it('finding 6: an approval whose Agent result shows a mid-run model switch, or a hand-back that was not clean, is not an approval', async () => {
  for (const act of ['mixed-models', 'flagged-handback']) {
    const w = world({ rules: [{ match: { mode: 'ticket', step: 'WF-001', attempt: 1 }, do: act }] });
    const r = await w.run();
    assert.equal(r.code, 0, `${act}: ${r.out}`);
    const wf1 = w.calls().filter((c) => c.step === 'WF-001');
    assert.deepEqual(wf1.map((c) => c.attempt), [1, 2], act);
    assert.match(wf1[1].stdin, /RETRY_NOTE: .*VERDICT: APPROVE WF-001/, act);
  }
});

it('finding 8: a ci-fix session that changes scripts/autopilot is caught before the merge', async () => {
  const w = world({ ci: { default: ['fail', 'pass'] }, rules: [{ match: { mode: 'ci-fix' }, do: 'edit-autopilot' }] });
  const r = await w.run();
  assert.equal(r.code, 2, r.out);
  assert.match(r.out, /a session changed owner-controlled files \(scripts\/autopilot\/, \.claude\/agents\/, \.claude\/settings\.json, \.mcp\.json\): scripts\/autopilot\/lib\/task\.mjs/);
  assert.equal(w.gh().prs[1].state, 'OPEN');
  assert.ok(w.gh().prs[1].labels.includes('autopilot:stopped'));
  assert.ok(!w.gh().calls.some((c) => c.startsWith('pr merge')));
});

it('finding 9: after the owner clears a stop, the unit gets fresh attempts (steps and ci-fix), not a second stop at once', async () => {
  const steps = world({ rules: [1, 2, 3].map((attempt) => ({ match: { mode: 'ticket', step: 'WF-001', attempt }, do: 'no-approval' })) });
  assert.equal((await steps.run()).code, 2);
  assert.equal(steps.driverState().attempts['ticket:WF-001'], 3);
  fs.rmSync(path.join(steps.work, '.autopilot', 'stop.json'));
  steps.setGh((g) => (g.prs[1].labels = []));
  steps.setScenario({});
  const r = await steps.run();
  assert.equal(r.code, 0, r.out);
  assert.deepEqual(steps.calls().filter((c) => c.step === 'WF-001').map((c) => c.attempt), [1, 2, 3, 1], 'attempt numbering starts again');

  const ci = world({ ci: { default: ['fail'] } });
  assert.equal((await ci.run()).code, 2);
  assert.equal(ci.driverState().ciFixAttempts, 3);
  fs.rmSync(path.join(ci.work, '.autopilot', 'stop.json'));
  ci.setGh((g) => (g.prs[1].labels = []));
  ci.setScenario({ ci: { default: ['fail', 'fail', 'fail', 'fail', 'pass'] } });
  const r2 = await ci.run();
  assert.equal(r2.code, 0, r2.out);
  assert.deepEqual(ci.calls().filter((c) => c.mode === 'ci-fix').map((c) => c.attempt), [1, 2, 3, 1]);
  assert.equal(ci.calls().filter((c) => c.mode === 'ship').length, 1, 'the ci-fix commits pushed after the ship are not part of the ship diff, so the restart does not run ship again');
  assert.equal(ci.gh().prs[1].state, 'MERGED');
});

it('finding 10: a session the watchdog killed is resumed in its own tree: its uncommitted work is not stashed', async () => {
  const w = world({ rules: [{ match: { mode: 'ticket', step: 'WF-001', attempt: 1, resumed: false }, do: 'hang-dirty' }] });
  w.vars.AUTOPILOT_IDLE_MS = '4000';
  const r = await w.run();
  assert.equal(r.code, 0, r.out);
  assert.match(r.out, /killing the session: watchdog-idle/);
  assert.doesNotMatch(r.out, /working tree was dirty: stashed/);
  assert.equal(git(w.work, 'stash', 'list'), '', 'nothing was stashed');
  assert.equal(w.mainFile('src/hang-work.txt').trim(), 'uncommitted work of the hung session', 'the resumed session committed it');
  const wf1 = w.calls().filter((c) => c.step === 'WF-001');
  assert.equal(wf1.length, 2);
  assert.equal(wf1[1].resumed, true);
});

it('finding 13: every session runs with --strict-mcp-config and without the Monitor tool', async () => {
  const w = world();
  assert.equal((await w.run()).code, 0);
  for (const c of w.calls()) {
    assert.ok(c.args.includes('--strict-mcp-config'), c.mode);
    assert.ok(!c.args.includes('--mcp-config'), c.mode);
    assert.ok(c.args.slice(c.args.indexOf('--disallowedTools')).includes('Monitor'), c.mode);
  }
});

it('finding 17: a stop.json that cannot be parsed still counts as a stop', async () => {
  const w = world();
  fs.mkdirSync(path.join(w.work, '.autopilot'), { recursive: true });
  fs.writeFileSync(path.join(w.work, '.autopilot', 'stop.json'), '{ "unit": "01", "reason": "spec-conf');
  const r = await w.run();
  assert.equal(r.code, 2, r.out);
  assert.match(r.out, /stop\.json exists but is not valid JSON/);
  assert.equal(w.calls().length, 0);
});

it('finding 18: taking over a stale lock kills the recorded claude only when its command line carries --name hermi-', async () => {
  const progress = PROGRESS.replace('Not started', 'Done (#7)');
  const claudeName = process.platform === 'win32' ? 'claude.exe' : 'claude';
  const spawnClaudeLike = (w, name, extra) => {
    const exe = path.join(w.T, name);
    fs.copyFileSync(process.execPath, exe);
    fs.chmodSync(exe, 0o755);
    return spawn(exe, ['-e', 'setTimeout(() => {}, 120000)', '--', ...extra], { stdio: 'ignore', windowsHide: true });
  };
  const alive = (pid) => {
    try {
      process.kill(pid, 0);
      return true;
    } catch {
      return false;
    }
  };
  const results = {};
  for (const [label, extra] of [['ours', ['--name', 'hermi-01-ticket-WF-001']], ['foreign', ['--name', 'someone-elses-session']]]) {
    const w = world({}, { progress });
    write(w.work, 'docs/gates/phase-1-complete.md', '# done\n');
    git(w.work, 'add', '-A');
    git(w.work, 'commit', '--quiet', '-m', 'gate');
    git(w.work, 'push', '--quiet', 'origin', 'main');
    const child = spawnClaudeLike(w, claudeName, extra);
    await new Promise((res) => setTimeout(res, 800));
    fs.mkdirSync(path.join(w.work, '.autopilot'), { recursive: true });
    fs.writeFileSync(path.join(w.work, '.autopilot', 'lock'), JSON.stringify({ pid: 2147483000, startedAt: 'long ago', childPid: child.pid }));
    const r = await w.run([]);
    assert.equal(r.code, 0, `${label}: ${r.out}`);
    await new Promise((res) => setTimeout(res, 500));
    results[label] = alive(child.pid);
    if (alive(child.pid)) child.kill();
  }
  assert.deepEqual(results, { ours: false, foreign: true });
});

it('finding 22: a plan session finds the old plan file in place (it repairs it), instead of a deleted one', async () => {
  const w = world({ rules: [{ match: { mode: 'plan', attempt: 1 }, do: 'bad-plan' }] });
  const r = await w.run();
  assert.equal(r.code, 0, r.out);
  const plans = w.calls().filter((c) => c.mode === 'plan');
  assert.equal(plans.length, 2);
  assert.equal(plans[0].planExisted, false);
  assert.equal(plans[1].planExisted, true, 'the invalid file from attempt 1 was not deleted');
  assert.match(plans[1].stdin, /RETRY_NOTE: .*plan file is invalid/);
});

it('finding 22: --unit still stops on a Stopped row', async () => {
  const w = world({}, { progress: PROGRESS.replace('Not started', 'Stopped (spec-conflict: decide which document wins)') });
  const r = await w.run(['--unit', '01']);
  assert.equal(r.code, 2, r.out);
  assert.match(r.out, /PROGRESS\.md says 01 is Stopped \(spec-conflict: decide which document wins\)/);
  assert.equal(w.calls().length, 0);
  const dry = await w.run(['--dry-run', '--unit', '01']);
  assert.match(dry.out, /PROGRESS\.md says 01 is Stopped/);
});

it('finding 22: a ticket session may split its step; the driver reloads the plan and runs the sub-steps', async () => {
  const w = world({ rules: [{ match: { mode: 'ticket', step: 'WF-001', attempt: 1 }, do: 'split-plan' }] });
  const r = await w.run();
  assert.equal(r.code, 0, r.out);
  assert.match(r.out, /step WF-001 was replaced in the plan/);
  assert.deepEqual(modes(w.calls()), ['plan', 'ticket:WF-001', 'ticket:WF-001.1', 'ticket:WF-001.2', 'ticket:WF-002', 'ship']);
  assert.deepEqual(Object.keys(w.driverState().approvals).sort(), ['WF-001.1', 'WF-001.2', 'WF-002']);
});

it('finding 7: a setup plan that leaves an S ticket uncovered is refused like a build plan', async () => {
  const progress = `# Phase 1 progress

## Setup prompts

| # | Prompt | Tickets | Status |
|---|---|---|---|
| S1 | [Demo spec fixes](S1-spec-demo.md) | S1.1, S1.2 | Not started |
`;
  const s1 = '# S1\n\n## Tickets, in this order\n\n| Ticket | Title |\n|---|---|\n| S1.1 | Edit the README |\n| S1.2 | Edit the architecture |\n';
  const w = world({ stepsByUnit: { S1: [{ id: 'S1.1', ticket: 'S1.1', title: 'Edit the README' }] } }, { progress, files: { 'app-buildout/prompts/S1-spec-demo.md': s1 } });
  const r = await w.run(['--once']);
  assert.equal(r.code, 2, r.out);
  assert.match(r.out, /the plan session failed 3 times: plan does not cover ticket\(s\): S1\.2/);
});

it('finding 22: git helpers refuse to lose work: ls-remote errors throw, checkout -B and branch -D keep local commits that origin does not have', async () => {
  const w = world();
  // a local branch that is ahead of its origin
  git(w.work, 'checkout', '-b', 'phase1/p09-x');
  write(w.work, 'a.txt', 'a\n');
  git(w.work, 'add', '-A');
  git(w.work, 'commit', '--quiet', '-m', 'WF-900 first');
  git(w.work, 'push', '--quiet', '-u', 'origin', 'phase1/p09-x');
  const pushedTip = git(w.work, 'rev-parse', 'HEAD');
  write(w.work, 'b.txt', 'b\n');
  git(w.work, 'add', '-A');
  git(w.work, 'commit', '--quiet', '-m', 'WF-900 unpushed');
  git(w.work, 'checkout', 'main');
  const mod = "import { checkoutBranch, deleteLocalBranch, branchOnOrigin } from './scripts/autopilot/driver/git.mjs';";
  const checkout = inWorld(w, `${mod} try { checkoutBranch('phase1/p09-x'); console.log('RESET'); } catch (e) { console.log('REFUSED', e.code, e.message.split('\\n')[0]); }`);
  assert.match(checkout.stdout, /REFUSED 2 local branch phase1\/p09-x has 1 commit\(s\) that are not on origin\/phase1\/p09-x/);
  assert.equal(git(w.work, 'log', '-1', '--format=%s', 'phase1/p09-x'), 'WF-900 unpushed', 'the local commit is still there');
  const keep = inWorld(w, `${mod} console.log('DELETED', deleteLocalBranch('phase1/p09-x', '${pushedTip}'));`);
  assert.match(keep.stdout, /DELETED false/, 'the merged commit does not contain the local one');
  assert.match(git(w.work, 'branch', '--list', 'phase1/p09-x'), /phase1\/p09-x/);
  const tip = git(w.work, 'rev-parse', 'phase1/p09-x');
  const del = inWorld(w, `${mod} console.log('DELETED', deleteLocalBranch('phase1/p09-x', '${tip}'));`);
  assert.match(del.stdout, /DELETED true/);
  assert.equal(git(w.work, 'branch', '--list', 'phase1/p09-x'), '');
  // an ls-remote that fails is an error, not "the branch is not there"
  git(w.work, 'remote', 'set-url', 'origin', path.join(w.T, 'nowhere.git'));
  const remote = inWorld(w, `${mod} try { console.log('ANSWER', branchOnOrigin('phase1/p09-x')); } catch (e) { console.log('THROWS', e.code, e.message.split('\\n')[0]); }`);
  assert.match(remote.stdout, /THROWS 1 git ls-remote origin phase1\/p09-x failed/);
});
});
