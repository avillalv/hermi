// Tests for the pure helpers behind run.mjs: task lines, PROGRESS tables, plans, the claude command
// line, gh classification and CLI arguments. Run: node --test "scripts/autopilot/**/*.test.mjs"
// (Node 22 does not accept a bare directory argument to --test.)

import assert from 'node:assert/strict';
import test from 'node:test';
import { APPEND_PROMPT_FILE, buildChildEnv, buildClaudeArgs, DISALLOWED_TOOLS, formatCommand, HOOK_FILES, MODE_MAX_TURNS, modelForMode, OPUS_MODEL, prependPath, SETTINGS_DONTASK_FILE, SETTINGS_FILE, SONNET_MODEL } from './lib/cmd.mjs';
import { assessBranchProtection, assessRepoSettings, CI_CHECK_NAME, classifyChecks, classifyMainRun, failedRunIds, hasLabel, hasNoChecks, parseTokenScopes, runIdFromLink } from './lib/ci.mjs';
import { validatePlan } from './lib/plan.mjs';
import { isDoneForPr, parseProgress, parseStatus, progressCounts, rowForUnit, selectNextUnit, sortUnits } from './lib/progress.mjs';
import * as taskLib from './lib/task.mjs';
import { approverFor, branchPrefixFor, buildFailedChecksBlock, buildSessionInput, buildTaskLine, ciFixVerdictId, CONTINUE_TEXT, expectedBranch, FINAL_VERDICT_ID, formatDay, formatStamp, hasStepCommit, isShipSafePath, logFileName, parsePromptTickets, promptFileForUnit, sessionName, shipVerdictId, slugFromPromptFile, tailLines, unitKind, verdictAllowed } from './lib/task.mjs';
import * as gitMod from './driver/git.mjs';
import { isTransientGhError } from './driver/git.mjs';
import { FILES, isOurClaude } from './driver/ctx.mjs';
import { parseNetstat } from './driver/sys.mjs';
import { parseArgs } from './run.mjs';

// ---------------------------------------------------------------------------------------------
// task.mjs
// ---------------------------------------------------------------------------------------------

test('buildTaskLine: optional STEP and PR, fixed order', () => {
  assert.equal(buildTaskLine({ mode: 'plan', unit: '07', attempt: 1 }), 'MODE=plan UNIT=07 ATTEMPT=1');
  assert.equal(buildTaskLine({ mode: 'ticket', unit: '07', step: 'WF-005.1', pr: 123, attempt: 2 }), 'MODE=ticket UNIT=07 STEP=WF-005.1 PR=123 ATTEMPT=2');
  assert.equal(buildTaskLine({ mode: 'ci-fix', unit: 'main', attempt: 3 }), 'MODE=ci-fix UNIT=main ATTEMPT=3');
  assert.equal(buildTaskLine({ mode: 'final', unit: 'FINAL', attempt: 1 }), 'MODE=final UNIT=FINAL ATTEMPT=1');
  assert.throws(() => buildTaskLine({ mode: 'deploy', unit: '01', attempt: 1 }), /unknown mode/);
});

test('buildSessionInput: task line, FAILED_CHECKS block, one-line RETRY_NOTE', () => {
  const line = buildTaskLine({ mode: 'ci-fix', unit: '07', pr: 9, attempt: 1 });
  const out = buildSessionInput({ taskLine: line, failedChecks: '- ci (fail)\nlog tail\n', retryNote: 'no commit\nfound   on origin' });
  assert.equal(out, `${line}\nFAILED_CHECKS:\n- ci (fail)\nlog tail\nRETRY_NOTE: no commit found on origin\n`);
  assert.equal(buildSessionInput({ taskLine: line }), `${line}\n`);
  assert.equal(CONTINUE_TEXT, 'Continue the task from where you stopped.');
});

test('unit kinds, slugs, prompt files and branch names', () => {
  assert.equal(unitKind('S2'), 'setup');
  assert.equal(unitKind('07'), 'build');
  assert.equal(unitKind('FINAL'), 'final');
  assert.equal(unitKind('main'), 'main');
  assert.equal(unitKind('7'), null);
  assert.equal(slugFromPromptFile('01-repo-foundation.md'), 'repo-foundation');
  assert.equal(slugFromPromptFile('S1-spec-runtime.md'), 'spec-runtime');
  assert.equal(slugFromPromptFile('README.md'), null);
  const files = ['00-orchestrator.md', '01-repo-foundation.md', 'S1-spec-runtime.md', 'S10-later.md', 'AUTOPILOT.md'];
  assert.equal(promptFileForUnit('01', files), '01-repo-foundation.md');
  assert.equal(promptFileForUnit('S1', files), 'S1-spec-runtime.md');
  assert.equal(promptFileForUnit('S2', files), null);
  assert.equal(expectedBranch('07', 'entitlements-and-collaboration'), 'phase1/p07-entitlements-and-collaboration');
  assert.equal(expectedBranch('S1', 'spec-runtime'), 'spec/s1-spec-runtime');
  assert.equal(expectedBranch('FINAL', 'x'), 'phase1/final');
  assert.equal(expectedBranch('main', 'x'), null);
  assert.equal(branchPrefixFor('S3'), 'spec/');
  assert.equal(branchPrefixFor('12'), 'phase1/');
});

test('names and log files carry unit, mode, step and a stamp', () => {
  const d = new Date(2026, 9, 3, 7, 5, 9); // local time
  assert.equal(formatStamp(d), '20261003T070509');
  assert.equal(formatDay(d), '20261003');
  assert.equal(logFileName({ unit: '07', mode: 'ticket', step: 'WF-005.1', date: d }), '07-ticket-WF-005.1-20261003T070509.jsonl');
  assert.equal(logFileName({ unit: 'FINAL', mode: 'final', date: d }), 'FINAL-final-20261003T070509.jsonl');
  assert.equal(sessionName({ unit: '07', mode: 'ticket', step: 'WF-023' }), 'hermi-07-ticket-WF-023');
  assert.equal(sessionName({ unit: '07', mode: 'ship' }), 'hermi-07-ship');
});

const PROMPT_MD = `# Prompt 07

## Tickets, in this order

Intro line.

| Ticket | Title |
|---|---|
| WF-023 | Entitlements |
| WF-024 | Travelers |

## Notes

| WF-999 | not a ticket row (other section) |
`;

test('parsePromptTickets reads the Tickets table only', () => {
  assert.deepEqual(parsePromptTickets(PROMPT_MD), [
    { ticket: 'WF-023', title: 'Entitlements' },
    { ticket: 'WF-024', title: 'Travelers' },
  ]);
  assert.deepEqual(parsePromptTickets('# nothing here'), []);
  const s = parsePromptTickets('## Tickets, in this order\n\n| Ticket | Title |\n|---|---|\n| S1.1 | README |\n| S1.2 | 02 |\n');
  assert.deepEqual(s.map((r) => r.ticket), ['S1.1', 'S1.2']);
});

test('hasStepCommit: WF-005 must not match WF-005.1', () => {
  const subjects = ['WF-005.1 Providers', 'plan: 02', 'ship: 02'];
  assert.equal(hasStepCommit(subjects, 'WF-005.1'), true);
  assert.equal(hasStepCommit(subjects, 'WF-005'), false);
  assert.equal(hasStepCommit(subjects, 'WF-005.2'), false);
});

test('fix 9: uncoveredStepIds names step commits no approved id covers (an approved id, or approved sub-steps of a split step)', () => {
  const { uncoveredStepIds } = taskLib;
  assert.deepEqual(uncoveredStepIds(['WF-001 a', 'WF-002 b', 'plan: 01', 'ship: 01'], ['WF-001', 'WF-002']), []);
  assert.deepEqual(uncoveredStepIds(['WF-099 sneaky', 'WF-001 a'], ['WF-001']), ['WF-099']);
  assert.deepEqual(uncoveredStepIds(['WF-001 a', 'WF-001 again'], []), ['WF-001'], 'each id once');
  // a step that was split: the whole-step commit and the sub-step commits are covered by approved sub-steps
  assert.deepEqual(uncoveredStepIds(['WF-005 whole', 'WF-005.1 part', 'WF-005.2 part'], ['WF-005.1', 'WF-005.2']), []);
  assert.deepEqual(uncoveredStepIds(['WF-005.3 extra part'], ['WF-005.1', 'WF-005.2']), ['WF-005.3'], 'a sibling is not covered');
  assert.deepEqual(uncoveredStepIds(['WF-0051 other'], ['WF-005.1']), ['WF-0051'], 'a prefix of the text is not a prefix of the id');
  // setup steps
  assert.deepEqual(uncoveredStepIds(['S1.2 fix', 'S1.2.1 sub', 'S2.1 other'], ['S1.2', 'S1.2.1']), ['S2.1']);
  // anything else is not a step commit
  assert.deepEqual(uncoveredStepIds(['WF-001: colon', 'ci-fix: repair', 'Phase 1 / P01: x', 'wf-001 lower', 'WF-001'], []), []);
});

test('buildFailedChecksBlock lists checks, keeps the last 200 log lines, caps the size', () => {
  const text = Array.from({ length: 500 }, (_, i) => `line ${i}`).join('\n');
  const block = buildFailedChecksBlock({ checks: [{ name: 'ci', bucket: 'fail', link: 'https://x/runs/1' }], logs: [{ runId: '1', text }] });
  assert.match(block, /^- ci \(fail\) https:\/\/x\/runs\/1/);
  assert.match(block, /last 200 lines/);
  assert.ok(block.includes('line 499') && block.includes('line 300') && !block.includes('line 299'));
  const huge = buildFailedChecksBlock({ checks: [], logs: [{ runId: '2', text: 'y'.repeat(200000) }] });
  assert.ok(huge.length <= 60100 && huge.startsWith('[truncated]'));
  assert.equal(tailLines('a\nb\nc\n', 2), 'b\nc');
});

// ---------------------------------------------------------------------------------------------
// progress.mjs
// ---------------------------------------------------------------------------------------------

const PROGRESS_MD = `# Phase 1 progress

## Setup prompts

| # | Prompt | Tickets | Status |
|---|---|---|---|
| S1 | [Spec fixes, runtime](S1-spec-runtime.md) | S1.1, S1.2 | Done (#3) |
| S2 | [Spec fixes, product](S2-spec-product-ui.md) | S2.1 | In review (#4) |
| S3 | [Spec fixes, roadmap](S3-spec-roadmap-prompts.md) | S3.1 | Not started |

## Prompts

| # | Prompt | Tickets | Status |
|---|---|---|---|
| 01 | [Repository foundation](01-repo-foundation.md) | WF-001, WF-002 | Not started |
| 02 | [Port reusable code](02-port-reusable-modules.md) | WF-005 | Not started |

## Measured numbers

| Measure | Value | When |
|---|---|---|
| Average agent run cost | not measured | |
`;

test('parseStatus covers every status value', () => {
  assert.deepEqual(parseStatus('Not started'), { kind: 'not-started', detail: '' });
  assert.deepEqual(parseStatus('In progress (phase1/p07-x)'), { kind: 'in-progress', detail: 'phase1/p07-x' });
  assert.deepEqual(parseStatus('In review (#12)'), { kind: 'in-review', detail: '#12' });
  assert.deepEqual(parseStatus('Done (#12)'), { kind: 'done', detail: '#12' });
  assert.deepEqual(parseStatus('Done'), { kind: 'done', detail: '' });
  assert.deepEqual(parseStatus('Stopped (denials: add an allow rule)'), { kind: 'stopped', detail: 'denials: add an allow rule' });
  assert.equal(parseStatus('**Done** (#5)').kind, 'done');
  assert.equal(parseStatus('whatever').kind, 'unknown');
});

test('parseProgress reads both tables and ignores other tables', () => {
  const rows = parseProgress(PROGRESS_MD);
  assert.deepEqual(rows.map((r) => r.id), ['S1', 'S2', 'S3', '01', '02']);
  assert.equal(rows[0].kind, 'setup');
  assert.equal(rows[3].kind, 'build');
  assert.equal(rows[0].title, 'Spec fixes, runtime');
  assert.equal(rows[0].file, 'S1-spec-runtime.md');
  assert.deepEqual(rows[3].tickets, ['WF-001', 'WF-002']);
  assert.deepEqual(progressCounts(rows), { done: 1, total: 5 });
  assert.equal(rowForUnit(rows, '02').statusText, 'Not started');
  assert.equal(rowForUnit(rows, '99'), null);
});

test('parseProgress tolerates a file with only the Prompts table', () => {
  const only = PROGRESS_MD.replace(/## Setup prompts[\s\S]*?(?=## Prompts)/, '');
  assert.deepEqual(parseProgress(only).map((r) => r.id), ['01', '02']);
  assert.deepEqual(parseProgress('# no tables'), []);
});

test('sortUnits puts S1..S3 first whatever the file order', () => {
  const shuffled = [...parseProgress(PROGRESS_MD)].reverse();
  assert.deepEqual(sortUnits(shuffled).map((r) => r.id), ['S1', 'S2', 'S3', '01', '02']);
});

test('selectNextUnit: first row that is not Done decides', () => {
  const rows = parseProgress(PROGRESS_MD);
  assert.deepEqual(selectNextUnit(rows, { finalGateExists: false }).unit, 'S2'); // In review is not Done
  const done = parseProgress(PROGRESS_MD.replace(/\| (In review \(#4\)|Not started) \|/g, '| Done (#9) |'));
  assert.equal(selectNextUnit(done, { finalGateExists: false }).unit, 'FINAL');
  assert.deepEqual(selectNextUnit(done, { finalGateExists: true }), { action: 'complete' });
});

test('selectNextUnit: Stopped halts, empty tables are an error', () => {
  const stopped = parseProgress(PROGRESS_MD.replace('| Not started |\n| 02', '| Stopped (merge-impossible: branch protection needs a review) |\n| 02').replace(/\| (In review \(#4\)) \|/, '| Done (#4) |').replace(/(S3.*)\| Not started \|/, '$1| Done (#5) |'));
  const sel = selectNextUnit(stopped, { finalGateExists: false });
  assert.equal(sel.action, 'stopped');
  assert.equal(sel.unit, '01');
  assert.match(sel.reason, /merge-impossible/);
  assert.equal(selectNextUnit([], { finalGateExists: false }).action, 'error');
});

test('isDoneForPr matches the PR number exactly', () => {
  assert.equal(isDoneForPr(parseStatus('Done (#12)'), 12), true);
  assert.equal(isDoneForPr(parseStatus('Done (#12)'), 123), false);
  assert.equal(isDoneForPr(parseStatus('In review (#12)'), 12), false);
  assert.equal(isDoneForPr(parseStatus('Done'), 12), false);
});

// ---------------------------------------------------------------------------------------------
// plan.mjs
// ---------------------------------------------------------------------------------------------

const goodPlan = () => ({
  unit: '07',
  branch: 'phase1/p07-entitlements-and-collaboration',
  pr: 123,
  gate: 'month-1',
  steps: [
    { id: 'WF-023', ticket: 'WF-023', title: 'Entitlements', ui: false, kit: null, migration: true, owner_pending: [] },
    { id: 'WF-024', ticket: 'WF-024', title: 'Travelers', ui: true, kit: 'none, follow DL section 11', migration: false, owner_pending: ['device check'] },
  ],
});
const ctx07 = { unit: '07', slug: 'entitlements-and-collaboration', promptTickets: [{ ticket: 'WF-023' }, { ticket: 'WF-024' }] };

test('validatePlan accepts a good plan and tolerates sub-steps', () => {
  assert.deepEqual(validatePlan(goodPlan(), ctx07), { ok: true, errors: [], warnings: [] });
  const p = goodPlan();
  p.steps.push({ id: 'WF-024.1', ticket: 'WF-024', title: 'Part 2' });
  assert.equal(validatePlan(p, ctx07).ok, true);
});

test('validatePlan rejects the usual mistakes', () => {
  const bad = (mutate) => {
    const p = goodPlan();
    mutate(p);
    return validatePlan(p, ctx07);
  };
  assert.match(bad((p) => (p.unit = '08')).errors[0], /unit is "08"/);
  assert.match(bad((p) => (p.branch = 'main')).errors.join(), /must start with "phase1\/"/);
  assert.match(bad((p) => (p.pr = '12')).errors.join(), /pr must be a positive integer/);
  assert.match(bad((p) => (p.gate = 'month-9')).errors.join(), /gate must be/);
  assert.match(bad((p) => (p.steps = [])).errors.join(), /steps is empty/);
  assert.match(bad((p) => p.steps.push({ ...p.steps[0] })).errors.join(), /duplicate step id WF-023/);
  assert.match(bad((p) => (p.steps[0].id = 'WF 023')).errors.join(), /id "WF 023" must match/);
  assert.match(bad((p) => p.steps.pop()).errors.join(), /does not cover ticket\(s\): WF-024/);
  assert.equal(validatePlan(null, ctx07).ok, false);
  assert.equal(validatePlan([], ctx07).ok, false);
});

test('validatePlan: slug mismatch only warns; FINAL may have no steps', () => {
  const p = goodPlan();
  p.branch = 'phase1/p07-other-name';
  const r = validatePlan(p, ctx07);
  assert.equal(r.ok, true);
  assert.match(r.warnings[0], /differs from the expected/);
  const fin = { unit: 'FINAL', branch: 'phase1/final', pr: 9, gate: null, steps: [] };
  assert.equal(validatePlan(fin, { unit: 'FINAL' }).ok, true);
  assert.equal(validatePlan({ ...fin, branch: 'phase1/other' }, { unit: 'FINAL' }).ok, false);
});

// Finding 7: the S prompts' tickets (S1.1, S1.2, ...) must be covered by a step too.
test('validatePlan: a setup plan must cover every Sn.k ticket of its prompt', () => {
  const s1 = { unit: 'S1', branch: 'spec/s1-spec-runtime', pr: 5, gate: null, steps: [{ id: 'S1.1', ticket: 'S1.1', title: 'README' }] };
  const tickets = [{ ticket: 'S1.1' }, { ticket: 'S1.2' }];
  const r = validatePlan(s1, { unit: 'S1', slug: 'spec-runtime', promptTickets: tickets });
  assert.equal(r.ok, false);
  assert.match(r.errors.join(), /does not cover ticket\(s\): S1\.2/);
  const full = { ...s1, steps: [...s1.steps, { id: 'S1.2', ticket: 'S1.2', title: 'Architecture' }] };
  assert.equal(validatePlan(full, { unit: 'S1', slug: 'spec-runtime', promptTickets: tickets }).ok, true);
  const split = { ...s1, steps: [{ id: 'S1.1', ticket: 'S1.1', title: 'a' }, { id: 'S1.2.1', ticket: 'S1.2', title: 'b' }, { id: 'S1.2.2', ticket: 'S1.2', title: 'c' }] };
  assert.equal(validatePlan(split, { unit: 'S1', slug: 'spec-runtime', promptTickets: tickets }).ok, true, 'sub-steps cover their ticket');
  assert.equal(validatePlan(s1, { unit: 'S1', slug: 'spec-runtime', promptTickets: [] }).ok, true, 'no table, no coverage check');
  assert.equal(validatePlan(s1, { unit: 'S1', slug: 'spec-runtime', promptTickets: [{ ticket: 'S1.1' }, { ticket: 'not a ticket' }] }).ok, true, 'rows that are not Sn.k are ignored');
});

// ---------------------------------------------------------------------------------------------
// cmd.mjs
// ---------------------------------------------------------------------------------------------

test('models and turn caps per mode', () => {
  assert.equal(modelForMode('plan'), OPUS_MODEL);
  assert.equal(modelForMode('final'), OPUS_MODEL);
  for (const m of ['ticket', 'ship', 'ci-fix']) assert.equal(modelForMode(m), SONNET_MODEL);
  assert.deepEqual(MODE_MAX_TURNS, { plan: 150, ticket: 300, ship: 200, 'ci-fix': 200, final: 300 });
  assert.throws(() => modelForMode('canary'));
});

test('buildClaudeArgs: the documented session command, prompt not on the command line', () => {
  const args = buildClaudeArgs({ model: OPUS_MODEL, name: 'hermi-07-plan' });
  assert.deepEqual(args, [
    '-p', '--model', 'claude-opus-5-5',
    '--append-system-prompt-file', 'app-buildout/prompts/AUTOPILOT.md',
    '--settings', 'scripts/autopilot/settings.json',
    '--permission-mode', 'auto', '--permission-prompts', 'none',
    '--output-format', 'stream-json', '--verbose', '--forward-subagent-text',
    '--strict-mcp-config',
    '--disallowedTools', ...DISALLOWED_TOOLS,
    '--name', 'hermi-07-plan',
  ]);
  // findings 13 and 21: no MCP server (the owner's Gmail and Drive connectors stay out), and no Monitor tool
  assert.ok(buildClaudeArgs({ model: SONNET_MODEL, name: 'n' }).includes('--strict-mcp-config'));
  assert.ok(!buildClaudeArgs({ model: SONNET_MODEL, name: 'n' }).includes('--mcp-config'));
  assert.deepEqual(DISALLOWED_TOOLS, ['AskUserQuestion', 'EnterPlanMode', 'EnterWorktree', 'CronCreate', 'RemoteTrigger', 'ScheduleWakeup', 'Workflow', 'Monitor']);
});

test('buildClaudeArgs: the opt-in dontAsk profile, resume, hook events, no append file', () => {
  const a = buildClaudeArgs({ model: SONNET_MODEL, permission: 'dontAsk', name: 'n', resumeId: 'abc-123', hookEvents: true, appendPromptFile: null });
  assert.equal(a[a.indexOf('--settings') + 1], 'scripts/autopilot/settings-dontask.json');
  assert.equal(a[a.indexOf('--permission-mode') + 1], 'dontAsk');
  assert.ok(a.includes('--include-hook-events'));
  assert.ok(!a.includes('--append-system-prompt-file'));
  assert.deepEqual(a.slice(-2), ['--resume', 'abc-123']);
});

test('buildChildEnv: no API key, no parent-session markers, per-mode turns', () => {
  const base = {
    ANTHROPIC_API_KEY: 'sk-secret',
    ANTHROPIC_AUTH_TOKEN: 't',
    CLAUDECODE: '1',
    CLAUDE_CODE_SESSION_ID: 'parent',
    CLAUDE_CODE_ENTRYPOINT: 'claude-desktop',
    CLAUDE_CODE_OAUTH_TOKEN: 'keep-me',
    CLAUDE_CODE_GIT_BASH_PATH: 'C:\\bash.exe',
    CLAUDE_AGENT_SDK_VERSION: '0.3',
    CLAUDE_PROJECT_DIR: '/parent',
    PATH: '/usr/bin',
    HOME: '/home/x',
  };
  const env = buildChildEnv(base, { mode: 'ticket' });
  assert.equal(env.ANTHROPIC_API_KEY, undefined);
  assert.equal(env.ANTHROPIC_AUTH_TOKEN, undefined);
  assert.equal(env.CLAUDECODE, undefined);
  assert.equal(env.CLAUDE_CODE_SESSION_ID, undefined);
  assert.equal(env.CLAUDE_CODE_ENTRYPOINT, undefined);
  assert.equal(env.CLAUDE_AGENT_SDK_VERSION, undefined);
  assert.equal(env.CLAUDE_PROJECT_DIR, undefined);
  assert.equal(env.CLAUDE_CODE_OAUTH_TOKEN, 'keep-me');
  assert.equal(env.CLAUDE_CODE_GIT_BASH_PATH, 'C:\\bash.exe');
  assert.equal(env.HOME, '/home/x');
  assert.equal(env.CLAUDE_CODE_DISABLE_AUTO_MEMORY, '1');
  assert.equal(env.CLAUDE_CODE_MAX_TURNS, '300');
  assert.equal(env.MSYS_NO_PATHCONV, '1');
  assert.equal(buildChildEnv(base, { mode: 'plan' }).CLAUDE_CODE_MAX_TURNS, '150');
  assert.equal(base.ANTHROPIC_API_KEY, 'sk-secret', 'the input is not mutated');
});

test('prependPath finds the existing PATH key whatever its case', () => {
  const env = prependPath({ Path: 'C:\\a' }, ['C:\\gh']);
  assert.equal(Object.keys(env).length, 1);
  assert.ok(env.Path.startsWith('C:\\gh'));
  assert.equal(prependPath({}, []).PATH, undefined);
});

test('formatCommand quotes only what needs quoting', () => {
  assert.equal(formatCommand('C:\\bin\\claude.exe', ['-p', '--name', 'a b', 'x"y']), 'C:\\bin\\claude.exe -p --name "a b" "x\\"y"');
});

// ---------------------------------------------------------------------------------------------
// ci.mjs
// ---------------------------------------------------------------------------------------------

test('classifyChecks (finding 1): only a check named ci decides, and only bucket pass is a pass', () => {
  assert.equal(CI_CHECK_NAME, 'ci');
  assert.equal(classifyChecks([]).state, 'none');
  assert.equal(classifyChecks(undefined).state, 'none');
  assert.equal(classifyChecks([{ name: 'ci', bucket: 'pass' }]).state, 'pass');
  // other checks are ignored, whatever their result
  assert.equal(classifyChecks([{ name: 'lint', bucket: 'pass' }, { name: 'e2e', bucket: 'pass' }]).state, 'none', 'green checks that are not ci never pass');
  assert.equal(classifyChecks([{ name: 'ci', bucket: 'pass' }, { name: 'e2e', bucket: 'fail' }]).state, 'pass');
  assert.equal(classifyChecks([{ name: 'ci / ci', bucket: 'pass' }]).state, 'none', 'the name must be exactly ci');
  // skipped, unknown or missing ci is not a pass
  assert.equal(classifyChecks([{ name: 'ci', bucket: 'skipping' }]).state, 'none');
  assert.equal(classifyChecks([{ name: 'ci', bucket: 'pass' }, { name: 'ci', bucket: 'skipping' }]).state, 'none');
  assert.equal(classifyChecks([{ name: 'ci', bucket: 'weird' }]).state, 'none');
  // pending beats fail beats pass
  const f = classifyChecks([{ name: 'ci', bucket: 'fail' }, { name: 'lint', bucket: 'pass' }]);
  assert.equal(f.state, 'fail');
  assert.deepEqual(f.failed.map((c) => c.name), ['ci']);
  assert.equal(classifyChecks([{ name: 'ci', bucket: 'fail' }, { name: 'ci', bucket: 'pending' }]).state, 'pending');
  assert.equal(classifyChecks([{ name: 'ci', bucket: 'cancel' }]).state, 'fail');
  assert.equal(classifyChecks([{ name: 'build', bucket: 'pass' }], 'build').state, 'pass', 'the name is a parameter');
});

test('run ids come from check links', () => {
  assert.equal(runIdFromLink('https://github.com/avillalv/hermi/actions/runs/123456/job/789'), '123456');
  assert.equal(runIdFromLink('https://example.com'), null);
  const failed = [{ link: 'https://github.com/o/r/actions/runs/1/job/2' }, { link: 'https://github.com/o/r/actions/runs/1/job/3' }, { link: 'https://github.com/o/r/actions/runs/5/job/6' }, { link: null }];
  assert.deepEqual(failedRunIds(failed), ['1', '5']);
});

test('hasNoChecks recognises both "nothing reported" messages of gh (and there is no fallback keyed on them any more)', () => {
  assert.equal(hasNoChecks("no required checks reported on the 'phase1/x' branch"), true);
  assert.equal(hasNoChecks("no checks reported on the 'phase1/x' branch"), true);
  assert.equal(hasNoChecks('All checks were successful'), false);
});

test('classifyMainRun', () => {
  assert.equal(classifyMainRun([]).state, 'none');
  assert.equal(classifyMainRun([{ status: 'in_progress', conclusion: '' }]).state, 'running');
  assert.equal(classifyMainRun([{ status: 'completed', conclusion: 'success' }]).state, 'green');
  for (const c of ['failure', 'timed_out', 'startup_failure']) assert.equal(classifyMainRun([{ status: 'completed', conclusion: c }]).state, 'red');
  assert.equal(classifyMainRun([{ status: 'completed', conclusion: 'cancelled' }]).state, 'other');
});

test('gh auth scopes, branch protection and repo settings', () => {
  const text = "github.com\n  - Token scopes: 'gist', 'read:org', 'repo', 'workflow'\n";
  assert.deepEqual(parseTokenScopes(text), ['gist', 'read:org', 'repo', 'workflow']);
  assert.equal(parseTokenScopes('no scopes line'), null);
  assert.equal(assessBranchProtection({ message: 'Branch not protected' }).protected, false);
  // finding 2: protected, ci required AND enforced for administrators
  const ok = assessBranchProtection({ required_status_checks: { contexts: ['ci'] }, enforce_admins: { enabled: true }, required_pull_request_reviews: { required_approving_review_count: 0 } });
  assert.deepEqual({ p: ok.protected, pr: ok.requiresPr, ci: ok.requiresCi, admins: ok.enforceAdmins, problems: ok.problems.length }, { p: true, pr: true, ci: true, admins: true, problems: 0 });
  // fix 1: a pull request must be required (a null rule lets a commit whose ci passed be pushed to main directly)
  assert.equal(assessBranchProtection({ required_status_checks: { contexts: ['ci'] }, enforce_admins: { enabled: true }, required_pull_request_reviews: null }).requiresPr, false, 'no-pr');
  assert.equal(assessBranchProtection({ required_status_checks: { contexts: ['ci'] } }).requiresPr, false, 'rule missing');
  assert.equal(assessBranchProtection({ message: 'Branch not protected' }).requiresPr, false);
  assert.equal(assessBranchProtection({ required_status_checks: { contexts: ['ci'] } }).enforceAdmins, false, 'enforce_admins missing');
  assert.equal(assessBranchProtection({ required_status_checks: { contexts: ['ci'] }, enforce_admins: { enabled: false } }).enforceAdmins, false);
  assert.equal(assessBranchProtection({ enforce_admins: { enabled: true } }).requiresCi, false, 'no required status checks');
  assert.equal(assessBranchProtection({ required_status_checks: { contexts: ['lint'] }, enforce_admins: { enabled: true } }).requiresCi, false, 'ci is not among them');
  assert.equal(assessBranchProtection({ message: 'Branch not protected' }).enforceAdmins, false);
  assert.equal(assessBranchProtection({ required_status_checks: { checks: [{ context: 'ci' }] } }).requiresCi, true);
  const reviews = assessBranchProtection({ required_status_checks: { contexts: ['ci'] }, required_pull_request_reviews: { required_approving_review_count: 1 } });
  assert.match(reviews.problems[0], /requires 1 approving review/);
  assert.equal(assessRepoSettings({ allow_squash_merge: false }).problems.length, 1);
  assert.deepEqual(assessRepoSettings({ allow_squash_merge: true, private: false }), { problems: [] });
  assert.equal(hasLabel([{ name: 'e2e' }, { name: 'x' }], 'e2e'), true);
  assert.equal(hasLabel([{ name: 'x' }], 'e2e'), false);
  assert.equal(hasLabel(undefined, 'e2e'), false);
});

test('isTransientGhError separates network hiccups from real answers', () => {
  for (const t of ['dial tcp: lookup api.github.com: no such host', 'HTTP 502: Bad Gateway', 'error connecting to api.github.com', 'read: connection reset by peer', 'API rate limit exceeded', 'context deadline exceeded: timeout']) {
    assert.equal(isTransientGhError(t), true, t);
  }
  for (const t of ['Could not resolve to a PullRequest with the number of 999.', 'no pull requests found', 'HTTP 404: Not Found', 'accepts at most 1 arg(s), received 2']) {
    assert.equal(isTransientGhError(t), false, t);
  }
});

// ---------------------------------------------------------------------------------------------
// CLI arguments
// ---------------------------------------------------------------------------------------------

test('parseArgs', () => {
  assert.deepEqual(parseArgs([]), { dryRun: false, once: false, unit: null, canary: false, help: false, permissionProfile: 'auto' });
  assert.deepEqual(parseArgs(['--dry-run', '--once', '--unit', 'S2']), { dryRun: true, once: true, unit: 'S2', canary: false, help: false, permissionProfile: 'auto' });
  // finding 12: dontAsk only by an explicit flag, and only that value
  assert.equal(parseArgs(['--permission-profile', 'dontask']).permissionProfile, 'dontask');
  assert.throws(() => parseArgs(['--permission-profile']), /only accepts "dontask"/);
  assert.throws(() => parseArgs(['--permission-profile', 'auto']), /only accepts "dontask"/);
  assert.throws(() => parseArgs(['--permission-profile', 'bypassPermissions']), /only accepts "dontask"/);
  assert.equal(parseArgs(['--unit', 'FINAL']).unit, 'FINAL');
  assert.equal(parseArgs(['--canary']).canary, true);
  assert.equal(parseArgs(['-h']).help, true);
  assert.throws(() => parseArgs(['--unit']), /--unit needs/);
  assert.throws(() => parseArgs(['--unit', '7']), /--unit needs/);
  assert.throws(() => parseArgs(['--nope']), /unknown option/);
});

// ---------------------------------------------------------------------------------------------
// verdict ids, ship diff, ports, lock, one set of constants, dead code
// ---------------------------------------------------------------------------------------------

test('verdict ids (finding 4): FINAL, ci-fix-<pr>-<n> and ship-<unit>, each from its own agent', () => {
  assert.equal(FINAL_VERDICT_ID, 'FINAL');
  assert.equal(ciFixVerdictId(12, 2), 'ci-fix-12-2');
  assert.equal(shipVerdictId('07'), 'ship-07');
  assert.deepEqual(approverFor('FINAL'), ['opus-judge']);
  assert.deepEqual(approverFor('ci-fix-12-2'), ['opus-judge']);
  assert.deepEqual(approverFor('ship-07'), ['opus-reviewer']);
  assert.deepEqual(approverFor('WF-023'), ['opus-reviewer', 'opus-judge']);
  assert.deepEqual(approverFor('ci-fix-x-2'), ['opus-reviewer', 'opus-judge'], 'only the exact shape is a ci-fix id');
});

test('verdictAllowed (finding 5): a session may earn only the verdict of its own mode and step', () => {
  const ticket = verdictAllowed({ mode: 'ticket', unit: '07', step: 'WF-023', pr: 5, attempt: 1 });
  assert.deepEqual(['WF-023', 'WF-024', 'ship-07', 'FINAL', 'ci-fix-5-1'].map(ticket), [true, false, false, false, false]);
  const ship = verdictAllowed({ mode: 'ship', unit: '07', pr: 5, attempt: 1 });
  assert.deepEqual(['ship-07', 'ship-08', 'WF-023', 'FINAL'].map(ship), [true, false, false, false]);
  const fix = verdictAllowed({ mode: 'ci-fix', unit: '07', pr: 5, attempt: 2 });
  assert.deepEqual(['ci-fix-5-2', 'ci-fix-5-1', 'ci-fix-6-2', 'WF-023'].map(fix), [true, false, false, false]);
  const main = verdictAllowed({ mode: 'ci-fix', unit: 'main', attempt: 2 }); // the session opens its own PR
  assert.deepEqual(['ci-fix-9-2', 'ci-fix-9-1', 'ci-fix-x-2', 'FINAL'].map(main), [true, false, false, false]);
  const fin = verdictAllowed({ mode: 'final', unit: 'FINAL', attempt: 1 });
  assert.deepEqual(['FINAL', 'ship-FINAL', 'WF-023'].map(fin), [true, false, false]);
  const plan = verdictAllowed({ mode: 'plan', unit: '07', attempt: 1 });
  assert.deepEqual(['WF-023', 'FINAL', 'ship-07'].map(plan), [false, false, false], 'a plan session approves nothing');
});

test('isShipSafePath (finding 4): documents, status logs, knowledge, findings, skills, API types and the seed only', () => {
  for (const f of ['docs/gates/month-1.md', 'docs/owner-guide.md', 'knowledge/autopilot.md', 'findings/2026-10-03.md', '.claude/skills/run-hermi-locally/SKILL.md', 'apps/web/src/lib/api/schema.d.ts', 'apps/api/hermi/seed/airports.py', 'infra/scripts/seed-staging.py', 'app-buildout/prompts/PROGRESS.md', 'app-buildout/prompts/HUMAN_TASKS.md', 'app-buildout/prompts/DECISIONS.md']) {
    assert.equal(isShipSafePath(f), true, f);
  }
  for (const f of ['apps/api/hermi/routes.py', 'apps/web/src/app.tsx', 'src/ship-extra.txt', '.claude/agents/opus-reviewer.md', '.claude/rules/design-token-sync.md', 'CLAUDE.md', 'app-buildout/prompts/AUTOPILOT.md', 'scripts/autopilot/run.mjs', '.github/workflows/ci.yml', 'package.json', 'scripts/x.mjs']) {
    assert.equal(isShipSafePath(f), false, f);
  }
  assert.equal(isShipSafePath('docs' + String.fromCharCode(92) + 'owner-guide.md'), true, 'a Windows path is read the same way');
});

test('parseNetstat (finding 11): IPv4 and IPv6 listeners, nothing else', () => {
  const text = [
    '  Proto  Local Address          Foreign Address        State           PID',
    '  TCP    0.0.0.0:8100           0.0.0.0:0              LISTENING       4120',
    '  TCP    127.0.0.1:5173         0.0.0.0:0              LISTENING       5300',
    '  TCP    [::]:8100              [::]:0                 LISTENING       4120',
    '  TCP    [::1]:5173             [::]:0                 LISTENING       5304',
    '  TCP    [::1]:51730            [::]:0                 LISTENING       777',
    '  TCP    127.0.0.1:8100         127.0.0.1:60000        ESTABLISHED     9001',
    '  TCP    [::1]:8100             [::1]:60001            TIME_WAIT       0',
    '  UDP    0.0.0.0:5173           *:*                                    8888',
    '',
  ].join('\r\n');
  assert.deepEqual(parseNetstat(text, 8100), [4120]);
  assert.deepEqual(parseNetstat(text, 5173).sort(), [5300, 5304], 'a server bound only to [::1] is found');
  assert.deepEqual(parseNetstat('  TCP    [::1]:5173   [::]:0   LISTENING   5304', 5173), [5304]);
  assert.deepEqual(parseNetstat(text, 9999), []);
  assert.deepEqual(parseNetstat('', 8100), []);
});

test('isOurClaude (finding 18): a takeover kills only a claude.exe that carries --name hermi-', () => {
  assert.equal(isOurClaude('claude.exe', 'C:/Users/matic/.local/bin/claude.exe -p --model claude-sonnet-5-5 --name hermi-07-ticket-WF-023'), true);
  assert.equal(isOurClaude('claude.exe', 'claude.exe -p --name hermi-canary-a'), true);
  assert.equal(isOurClaude('claude.exe', 'claude.exe --name my-own-session'), false, 'the owner\'s own claude session');
  assert.equal(isOurClaude('claude.exe', ''), false);
  assert.equal(isOurClaude('claude.exe', undefined), false);
  assert.equal(isOurClaude('node.exe', 'node server.js --name hermi-x'), false, 'the pid now belongs to another program');
  assert.equal(isOurClaude(null, 'claude --name hermi-x'), false);
});

test('one set of constants and no dead code (finding 24)', () => {
  assert.equal(FILES.appendPrompt, APPEND_PROMPT_FILE);
  assert.equal(FILES.settings, SETTINGS_FILE);
  assert.equal(FILES.settingsDontask, SETTINGS_DONTASK_FILE);
  assert.deepEqual(FILES.hooks, HOOK_FILES);
  assert.deepEqual(HOOK_FILES.map((f) => f.split('/').pop()), ['agent-guard.mjs', 'bash-guard.mjs', 'file-guard.mjs']);
  for (const name of ['SETUP_UNITS', 'mainFixBranchPrefix']) assert.equal(name in taskLib, false, `task.mjs no longer exports ${name}`);
  assert.equal('gitOut' in gitMod, false);
  assert.equal(Object.keys(assessRepoSettings({ private: true, delete_branch_on_merge: true })).join(), 'problems');
  assert.equal(typeof MODE_MAX_TURNS.plan, 'number', 'MODE_MAX_TURNS stays: buildChildEnv uses it');
});
