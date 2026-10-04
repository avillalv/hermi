// A fake `claude` for driver.test.mjs. Run as: node fake-claude.mjs <claude arguments>, with the task
// line on stdin. It does what the sessions in AUTOPILOT.md do (branches, commits, pushes, PROGRESS rows,
// plan files, labels) with real git in the scratch repository, and prints a stream-json stream shaped like
// Claude Code 2.1.288, including a forwarded Opus reviewer verdict. scenario.json picks the behavior:
//   {steps?, rules: [{match: {mode, unit, step, attempt, resumed}, do: <act>}], ci?, mainCi?}
// acts: ok, limit, auth-error, denials, overage, stop, wrong-permission, no-plan, bad-plan,
//       no-commit, no-approval, sonnet-approval, leave-unpushed, edit-autopilot, edit-agents,
//       edit-claude-settings, edit-mcp, extra-commit, plan-extra, plan-extra-bad, forget-ready,
//       forget-label, no-push, hang, hang-dirty, opus-limit, extra-approval, split-plan,
//       ship-code, ship-code-approved, ship-docs, unmark-done, mixed-models, flagged-handback

import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { expectedBranch, promptFileForUnit, slugFromPromptFile } from '../lib/task.mjs';
import { appendCall, createPr, ghState, readJson, scenario, writeJson } from './fake-state.mjs';

const OPUS = 'claude-opus-5-5';
const SONNET = 'claude-sonnet-5-5';
const argv = process.argv.slice(2);

if (argv[0] === '--version') {
  console.log('2.1.288 (Claude Code)');
  process.exit(0);
}
if (argv[0] === 'auth') {
  console.log(JSON.stringify({ loggedIn: true, authMethod: 'claude.ai', apiProvider: 'firstParty', subscriptionType: 'max' }));
  process.exit(0);
}

const arg = (n) => {
  const i = argv.indexOf(n);
  return i >= 0 ? argv[i + 1] : null;
};
const model = arg('--model');
const permission = arg('--permission-mode');
const settings = arg('--settings');
const resumeId = arg('--resume');
const stdin = fs.readFileSync(0, 'utf8');

const sessions = readJson('sessions.json', {});
let ctx;
if (resumeId && sessions[resumeId]) {
  ctx = { ...sessions[resumeId], resumed: true };
} else {
  const kv = Object.fromEntries(stdin.split('\n')[0].split(' ').map((p) => p.split('=')));
  ctx = { mode: kv.MODE, unit: kv.UNIT, step: kv.STEP, pr: kv.PR ? Number(kv.PR) : null, attempt: Number(kv.ATTEMPT), resumed: false };
}
const sid = resumeId ?? `fake-${Math.random().toString(36).slice(2, 10)}`;
sessions[sid] = { mode: ctx.mode, unit: ctx.unit, step: ctx.step, pr: ctx.pr, attempt: ctx.attempt };
writeJson('sessions.json', sessions);

const sc = scenario();
const planExisted = fs.existsSync(path.join('.autopilot', 'plans', `${ctx.unit}.json`));
const rule = (sc.rules ?? []).find((r) => Object.entries(r.match ?? {}).every(([k, v]) => ctx[k] === v)) ?? {};
const act = rule.do ?? 'ok';
appendCall({ ...ctx, sid, model, permission, settings, act, planExisted, args: argv, stdin: stdin.slice(0, 4000) });

const out = (o) => fs.writeSync(1, `${JSON.stringify(o)}\n`);
const git = (...args) => {
  const r = spawnSync('git', args, { encoding: 'utf8' });
  if (r.status !== 0) throw new Error(`git ${args.join(' ')}: ${r.stderr}`);
  return r.stdout.trim();
};
const gitOk = (...args) => spawnSync('git', args, { encoding: 'utf8' }).status === 0;
const planFile = (unit) => path.join('.autopilot', 'plans', `${unit}.json`);
const readPlan = () => JSON.parse(fs.readFileSync(planFile(ctx.unit), 'utf8'));
const commit = (msg) => {
  git('add', '-A');
  if (git('status', '--porcelain') !== '') git('commit', '-m', msg); // a rerun may have nothing new
};
const push = () => git('push', '-u', 'origin', 'HEAD');
const setRow = (unit, status) => {
  const f = 'app-buildout/prompts/PROGRESS.md';
  const text = fs.readFileSync(f, 'utf8').split('\n').map((l) => (l.startsWith(`| ${unit} |`) ? l.replace(/\|[^|]*\|\s*$/, `| ${status} |`) : l)).join('\n');
  fs.writeFileSync(f, text);
};
const defaultSteps = () =>
  sc.stepsByUnit?.[ctx.unit] ??
  sc.steps ?? [
    { id: 'WF-001', ticket: 'WF-001', title: 'First thing', ui: false, kit: null, migration: false, owner_pending: [] },
    { id: 'WF-002', ticket: 'WF-002', title: 'Second thing', ui: false, kit: null, migration: false, owner_pending: [] },
  ];

// A forwarded subagent verdict. taint: 'mixed' (the agent switched models mid-run) or 'flagged' (its hand-back
// was delivered under a warning): the harness result that follows says so, and the driver must not count it.
function emitVerdict({ stepId, agent = 'opus-reviewer', verdictModel = OPUS, verdict = 'APPROVE', taint = null }) {
  const message = `Reviewed.\nVERDICT: ${verdict} ${stepId}`;
  out({
    type: 'assistant',
    message: { model: verdictModel, content: [{ type: 'tool_use', id: 'tu_h', name: 'SubagentHandback', input: { message } }] },
    parent_tool_use_id: 'toolu_rev',
    subagent_type: agent,
    session_id: sid,
  });
  if (taint) {
    const extra = taint === 'mixed' ? { modelsUsed: [OPUS, SONNET] } : { handback: 'flagged' };
    out({
      type: 'user',
      message: { role: 'user', content: [{ type: 'tool_result', tool_use_id: 'toolu_rev', content: [{ type: 'text', text: 'report delivered' }] }] },
      parent_tool_use_id: null,
      tool_use_result: { status: 'completed', agentType: agent, resolvedModel: verdictModel, handbackReport: { text: message }, ...extra },
    });
  }
}

function end({ is_error = false, result = 'done', denials = 0, code = 0 } = {}) {
  out({
    type: 'result',
    subtype: is_error ? 'error_during_execution' : 'success',
    is_error,
    result,
    permission_denials: Array.from({ length: denials }, (_, i) => ({ tool_name: 'Bash', tool_use_id: `d${i}`, tool_input: { command: `cmd${i}` } })),
    total_cost_usd: 0.01,
    num_turns: 3,
    session_id: sid,
  });
  process.exit(code);
}

function doPlan() {
  const file = promptFileForUnit(ctx.unit, fs.readdirSync('app-buildout/prompts'));
  const branch = expectedBranch(ctx.unit, slugFromPromptFile(file));
  git('checkout', 'main');
  if (gitOk('rev-parse', '--verify', branch)) git('checkout', branch);
  else git('checkout', '-b', branch);
  setRow(ctx.unit, `In progress (${branch})`);
  const gs = ghState.load();
  const existing = Object.values(gs.prs).find((p) => p.headRefName === branch && p.state === 'OPEN');
  const pr = existing ? existing.number : createPr(gs, { headRefName: branch, title: `Phase 1 / P${ctx.unit}: demo`, isDraft: true });
  ghState.save(gs);
  if (act === 'plan-extra' || act === 'plan-extra-bad') fs.writeFileSync('src-by-plan.txt', 'a plan session must not write code\n');
  if (act !== 'no-plan') {
    fs.mkdirSync(path.dirname(planFile(ctx.unit)), { recursive: true });
    fs.writeFileSync(planFile(ctx.unit), act === 'bad-plan' || act === 'plan-extra-bad' ? '{ not json' : JSON.stringify({ unit: ctx.unit, branch, pr, gate: null, steps: defaultSteps() }, null, 2));
  }
  commit(`plan: ${ctx.unit}`);
  push();
}

function doTicket() {
  const plan = readPlan();
  git('checkout', plan.branch);
  const step = plan.steps.find((s) => s.id === ctx.step);
  if (act === 'split-plan') {
    // The session decides to split its step: it edits the plan file (not tracked by git) and ends.
    const steps = plan.steps.flatMap((s) => (s.id === step.id ? [1, 2].map((k) => ({ ...s, id: `${s.id}.${k}`, title: `${s.title} part ${k}` })) : [s]));
    fs.writeFileSync(planFile(ctx.unit), JSON.stringify({ ...plan, steps }, null, 2));
    return;
  }
  if (act !== 'no-commit') {
    fs.mkdirSync('src', { recursive: true });
    fs.writeFileSync(`src/${step.id}.txt`, `work for ${step.id}, attempt ${ctx.attempt}\n`);
    if (act === 'edit-autopilot') fs.appendFileSync('scripts/autopilot/lib/task.mjs', '\n// tampered by a session\n');
    if (act === 'edit-agents') fs.appendFileSync('.claude/agents/opus-judge.md', '\ntampered by a session\n');
    if (act === 'edit-claude-settings') fs.writeFileSync('.claude/settings.json', '{}\n');
    if (act === 'edit-mcp') fs.writeFileSync('.mcp.json', '{}\n');
    commit(`${step.id} ${step.title}`);
    if (act === 'extra-commit') {
      fs.writeFileSync('src/WF-099.txt', 'a commit for a step nobody reviewed\n');
      commit('WF-099 sneaky extra step');
    }
    if (act !== 'leave-unpushed') push();
  }
  if (act === 'sonnet-approval') emitVerdict({ stepId: step.id, verdictModel: SONNET });
  else if (act === 'mixed-models') emitVerdict({ stepId: step.id, taint: 'mixed' });
  else if (act === 'flagged-handback') emitVerdict({ stepId: step.id, taint: 'flagged' });
  else if (act !== 'no-approval') {
    emitVerdict({ stepId: step.id });
    // A verdict for another step is not this session's to give.
    if (act === 'extra-approval') emitVerdict({ stepId: plan.steps.find((s) => s.id !== step.id).id });
  }
}

function doShip() {
  const plan = readPlan();
  git('checkout', plan.branch);
  if (act === 'ship-code' || act === 'ship-code-approved') {
    fs.mkdirSync('src', { recursive: true });
    fs.writeFileSync('src/ship-extra.txt', 'a late code change made while shipping\n');
  }
  if (act === 'ship-docs') {
    fs.mkdirSync('docs', { recursive: true });
    fs.writeFileSync('docs/notes.md', '# notes written while shipping\n');
  }
  setRow(ctx.unit, `Done (#${plan.pr})`);
  commit(`ship: ${ctx.unit}`);
  push();
  const gs = ghState.load();
  const pr = gs.prs[plan.pr];
  if (act !== 'forget-ready') pr.isDraft = false;
  if (act !== 'forget-label' && act !== 'forget-ready') pr.labels.push('e2e');
  ghState.save(gs);
  if (act === 'ship-code-approved') emitVerdict({ stepId: `ship-${ctx.unit}` });
}

function doCiFix() {
  const gs = ghState.load();
  if (ctx.unit === 'main') {
    git('checkout', 'main');
    git('checkout', '-b', 'fix/main-ci-20260101');
    fs.writeFileSync('fix-main.txt', 'repair\n');
    commit('ci-fix: repair main');
    push();
    const n = createPr(gs, { headRefName: 'fix/main-ci-20260101', title: 'ci-fix: repair main', isDraft: false });
    ghState.save(gs);
    if (act !== 'no-approval') emitVerdict({ stepId: `ci-fix-${n}-${ctx.attempt}`, agent: 'opus-judge' });
    return;
  }
  const branch = gs.prs[ctx.pr].headRefName;
  git('checkout', branch);
  if (act === 'no-push') return;
  fs.writeFileSync(`fix-${ctx.attempt}.txt`, `repair by ${sid}\n`); // a new session always makes a new commit
  if (act === 'edit-autopilot') fs.appendFileSync('scripts/autopilot/lib/task.mjs', '\n// tampered by a ci-fix session\n');
  if (act === 'unmark-done') setRow(ctx.unit, 'In progress (changed by a ci-fix session)');
  commit('ci-fix: repair');
  push();
  if (act !== 'no-approval') emitVerdict({ stepId: `ci-fix-${ctx.pr}-${ctx.attempt}`, agent: 'opus-judge' });
}

function doFinal() {
  const branch = 'phase1/final';
  git('checkout', 'main');
  if (gitOk('rev-parse', '--verify', branch)) git('checkout', branch);
  else git('checkout', '-b', branch);
  fs.mkdirSync('docs/gates', { recursive: true });
  fs.writeFileSync('docs/gates/phase-1-complete.md', '# Phase 1 complete\n');
  commit('final: phase 1 complete');
  push();
  const gs = ghState.load();
  const existing = Object.values(gs.prs).find((p) => p.headRefName === branch && p.state === 'OPEN');
  const pr = existing ? existing.number : createPr(gs, { headRefName: branch, title: 'Phase 1 / final', isDraft: false });
  if (!gs.prs[pr].labels.includes('e2e')) gs.prs[pr].labels.push('e2e');
  gs.prs[pr].isDraft = false;
  ghState.save(gs);
  if (act !== 'no-approval') emitVerdict({ stepId: 'FINAL', agent: 'opus-judge' }); // the completeness verdict
}

// The four canary prompts of `run.mjs --canary` are free text, not a task line.
if (!resumeId && !/^MODE=/.test(stdin)) {
  const subMsg = (agent, subModel) => out({ type: 'assistant', message: { model: subModel, content: [{ type: 'tool_use', id: `tu_${agent}`, name: 'SubagentHandback', input: { message: 'OK' } }] }, parent_tool_use_id: `toolu_${agent}`, subagent_type: agent, session_id: sid });
  out({ type: 'system', subtype: 'init', session_id: sid, model, permissionMode: permission, apiKeySource: 'none', agents: ['opus-judge', 'sonnet-researcher'], cwd: process.cwd() });
  if (/opus-judge/.test(stdin)) {
    subMsg('opus-judge', sc.canaryBad ? SONNET : OPUS);
    subMsg('sonnet-researcher', SONNET);
    end();
  } else if (/cat \.env\.canary/.test(stdin)) {
    out({ type: 'assistant', message: { model, content: [{ type: 'tool_use', id: 'c1', name: 'Bash', input: { command: 'cat .env.canary' } }] }, parent_tool_use_id: null, session_id: sid });
    // canaryNoHook: refused by a permission denial only, which is not what canary c proves.
    const hooked = !sc.canaryBad && !sc.canaryNoHook;
    out({ type: 'system', subtype: 'hook_response', hook_event: 'PreToolUse', hook_name: 'PreToolUse:Bash', exit_code: hooked ? 2 : 0, outcome: hooked ? 'error' : 'success', stderr: hooked ? 'bash-guard: commands may not mention .env.canary' : '' });
    if (!sc.canaryBad) out({ type: 'user', message: { role: 'user', content: [{ type: 'tool_result', tool_use_id: 'c1', is_error: true, content: hooked ? 'PreToolUse:Bash hook error: bash-guard: commands may not mention .env.canary' : 'Permission denied' }] }, parent_tool_use_id: null });
    end({ denials: sc.canaryBad ? 0 : 1 });
  } else if (/general-purpose/.test(stdin)) {
    out({ type: 'assistant', message: { model, content: [{ type: 'tool_use', id: 'd1', name: 'Agent', input: { subagent_type: 'general-purpose', model: 'opus', prompt: 'reply OK' } }] }, parent_tool_use_id: null, session_id: sid });
    out({ type: 'system', subtype: 'hook_response', hook_event: 'PreToolUse', hook_name: 'PreToolUse:Agent', exit_code: sc.canaryBad ? 0 : 2, outcome: sc.canaryBad ? 'success' : 'error', stderr: sc.canaryBad ? '' : 'agent-guard: general-purpose needs model "sonnet" explicitly' });
    if (sc.canaryBad) subMsg('general-purpose', OPUS);
    end();
  }
  end({ denials: sc.canaryBad ? 1 : 0 });
}

out({ type: 'system', subtype: 'init', session_id: sid, model, permissionMode: act === 'wrong-permission' && permission === 'auto' ? 'default' : permission, apiKeySource: 'none', agents: ['opus-reviewer', 'opus-judge', 'sonnet-coder', 'sonnet-researcher'], cwd: process.cwd() });
out({ type: 'assistant', message: { model, content: [{ type: 'text', text: `fake ${ctx.mode} ${ctx.unit}${ctx.step ? ` ${ctx.step}` : ''} attempt ${ctx.attempt}${ctx.resumed ? ' (resumed)' : ''}` }] }, parent_tool_use_id: null, session_id: sid });

// A real session is killed at its init event, before its first tool call; do no work meanwhile.
if (act === 'wrong-permission' && permission === 'auto') await new Promise((r) => setTimeout(r, 60000));

if (act === 'limit') {
  out({ type: 'rate_limit_event', rate_limit_info: { status: 'rejected', resetsAt: Math.ceil(Date.now() / 1000) + 1, rateLimitType: 'five_hour', overageStatus: 'rejected', isUsingOverage: false }, session_id: sid });
  end({ is_error: true, result: "You've hit your limit · resets soon", code: 1 });
}
if (act === 'hang') await new Promise((r) => setTimeout(r, 120000)); // the watchdog kills us
if (act === 'hang-dirty') {
  // Work in progress that is not committed when the watchdog kills us: the driver must not stash it.
  git('checkout', readPlan().branch);
  fs.mkdirSync('src', { recursive: true });
  fs.writeFileSync('src/hang-work.txt', 'uncommitted work of the hung session\n');
  await new Promise((r) => setTimeout(r, 120000));
}
if (act === 'lock-and-hang') {
  fs.writeFileSync(path.join(git('rev-parse', '--git-dir'), 'index.lock'), ''); // a git command interrupted by the kill
  await new Promise((r) => setTimeout(r, 120000));
}
if (act === 'opus-limit') {
  out({ type: 'rate_limit_event', rate_limit_info: { status: 'rejected', resetsAt: Math.ceil(Date.now() / 1000) + 1, rateLimitType: 'seven_day_opus' }, session_id: sid });
  await new Promise((r) => setTimeout(r, 120000)); // the driver kills us and pauses the run
}
if (act === 'auth-error') end({ is_error: true, result: 'Not logged in · Please run /login', code: 1 });
if (act === 'denials') end({ denials: 5 });
if (act === 'overage') {
  out({ type: 'rate_limit_event', rate_limit_info: { status: 'allowed', rateLimitType: 'five_hour', overageStatus: 'allowed', isUsingOverage: true }, session_id: sid });
  await new Promise((r) => setTimeout(r, 30000)); // the driver kills us
  end();
}
if (act === 'stop') {
  fs.mkdirSync('.autopilot', { recursive: true });
  fs.writeFileSync('.autopilot/stop.json', JSON.stringify({ unit: ctx.unit, reason: 'spec-conflict', ownerAction: 'Decide which document wins and rerun.' }));
  end({ result: 'stopped' });
}

if (ctx.mode === 'plan') doPlan();
else if (ctx.mode === 'ticket') doTicket();
else if (ctx.mode === 'ship') doShip();
else if (ctx.mode === 'ci-fix') doCiFix();
else if (ctx.mode === 'final') doFinal();
end();
