// Tests for the stream parser, approval capture, rate limits, denials, auth errors and the canary
// evaluators. Fixtures mirror the event shapes observed on Claude Code 2.1.288 (init, assistant,
// forwarded subagent messages with SubagentHandback, rate_limit_event, result).

import assert from 'node:assert/strict';
import test from 'node:test';
import { CANARY_PROMPTS, evalAgentGuard, evalCommands, evalEnvRefused, evalSubagentModels } from './lib/canary.mjs';
import { assessRateLimit, autoModeUnavailable, denialSummary, formatDenials, isAuthError, limitPauseDecision } from './lib/limits.mjs';
import { extractVerdicts, OPUS_PREFIX, parseLine, StreamTracker, toolHint } from './lib/stream.mjs';
import { lastAssistantLines } from './status.mjs';

const L = (o) => JSON.stringify(o);
const OPUS = 'claude-opus-5-5';
const SONNET = 'claude-sonnet-5-5';

const init = (over = {}) => L({ type: 'system', subtype: 'init', session_id: 's1', model: SONNET, permissionMode: 'auto', apiKeySource: 'none', agents: ['opus-reviewer', 'opus-judge'], cwd: 'C:\\repo', ...over });
const mainText = (text, model = SONNET) => L({ type: 'assistant', message: { model, content: [{ type: 'text', text }] }, parent_tool_use_id: null, session_id: 's1' });
const mainTool = (id, name, input) => L({ type: 'assistant', message: { model: SONNET, content: [{ type: 'tool_use', id, name, input }] }, parent_tool_use_id: null, session_id: 's1' });
const subText = ({ model, agent, text }) => L({ type: 'assistant', message: { model, content: [{ type: 'text', text }] }, parent_tool_use_id: 'toolu_1', subagent_type: agent, session_id: 's1' });
const subHandback = ({ model, agent, text }) =>
  L({ type: 'assistant', message: { model, content: [{ type: 'tool_use', id: 'tu_h', name: 'SubagentHandback', input: { message: text } }] }, parent_tool_use_id: 'toolu_1', subagent_type: agent, session_id: 's1' });
const agentResult = ({ agent, model, text, extra = {} }) =>
  L({ type: 'user', message: { role: 'user', content: [{ type: 'tool_result', tool_use_id: 'toolu_1', content: [{ type: 'text', text: 'report delivered' }] }] }, parent_tool_use_id: null, tool_use_result: { status: 'completed', agentType: agent, resolvedModel: model, handbackReport: { text }, ...extra } });
const toolError = (id, text) => L({ type: 'user', message: { role: 'user', content: [{ type: 'tool_result', tool_use_id: id, is_error: true, content: text }] }, parent_tool_use_id: null });
const rate = (info) => L({ type: 'rate_limit_event', rate_limit_info: info, session_id: 's1' });
const result = (over = {}) => L({ type: 'result', subtype: 'success', is_error: false, result: 'done', permission_denials: [], total_cost_usd: 0.1234, num_turns: 4, session_id: 's1', ...over });

const feedAll = (lines) => {
  const t = new StreamTracker({ now: () => new Date('2026-10-03T12:00:00Z') });
  const all = { lines: [], signals: [] };
  for (const l of lines) {
    const r = t.feed(l);
    all.lines.push(...r.lines);
    all.signals.push(...r.signals);
  }
  return { t, ...all };
};

// ---------------------------------------------------------------------------------------------
// verdict lines
// ---------------------------------------------------------------------------------------------

test('extractVerdicts: exact lines only', () => {
  assert.deepEqual(extractVerdicts('review...\nVERDICT: APPROVE WF-023'), [{ verdict: 'APPROVE', stepId: 'WF-023' }]);
  assert.deepEqual(extractVerdicts('VERDICT: REQUEST_CHANGES WF-005.1\r\n1. fix x'), [{ verdict: 'REQUEST_CHANGES', stepId: 'WF-005.1' }]);
  assert.deepEqual(extractVerdicts('**VERDICT: APPROVE S1.2**'), [{ verdict: 'APPROVE', stepId: 'S1.2' }]);
  assert.deepEqual(extractVerdicts('VERDICT: APPROVE WF-023.'), [{ verdict: 'APPROVE', stepId: 'WF-023' }]);
  assert.deepEqual(extractVerdicts('End with VERDICT: APPROVE <step id> or VERDICT: REQUEST_CHANGES <step id>'), []);
  assert.deepEqual(extractVerdicts('I would say VERDICT: APPROVE WF-023 if the tests passed'), []);
  assert.deepEqual(extractVerdicts('verdict: approve WF-023'), []);
  assert.deepEqual(extractVerdicts(null), []);
});

// ---------------------------------------------------------------------------------------------
// approvals from the forwarded subagent stream
// ---------------------------------------------------------------------------------------------

test('a forwarded Opus reviewer APPROVE is recorded with its model and agent', () => {
  const { t, signals } = feedAll([init(), subText({ model: OPUS, agent: 'opus-reviewer', text: 'All criteria met.\nVERDICT: APPROVE WF-023' })]);
  const a = t.approvals.get('WF-023');
  assert.equal(a.model, OPUS);
  assert.equal(a.agent, 'opus-reviewer');
  assert.equal(a.at, '2026-10-03T12:00:00.000Z');
  assert.ok(signals.some((s) => s.kind === 'verdict' && s.verdict === 'APPROVE' && s.stepId === 'WF-023'));
});

test('an Opus report delivered through SubagentHandback counts, with a dated model id too', () => {
  const { t } = feedAll([subHandback({ model: `${OPUS_PREFIX}-20260901`, agent: 'opus-reviewer', text: 'ok\nVERDICT: APPROVE WF-024' })]);
  assert.equal(t.approvals.has('WF-024'), true);
});

test('the harness result of an Opus agent counts as a third source', () => {
  const { t } = feedAll([agentResult({ agent: 'opus-judge', model: OPUS, text: 'accept\nVERDICT: APPROVE WF-030' })]);
  assert.equal(t.approvals.get('WF-030').source, 'result');
});

test('fix 5: only the last non-empty line of a message can be the verdict; an earlier APPROVE line followed by more text does not count', () => {
  const early = feedAll([
    subText({ model: OPUS, agent: 'opus-reviewer', text: 'VERDICT: APPROVE WF-023\nOn reflection the migration is unsafe, so I stop here.' }),
    subHandback({ model: OPUS, agent: 'opus-reviewer', text: 'VERDICT: APPROVE WF-024\r\nmore findings follow\r\n' }),
    agentResult({ agent: 'opus-judge', model: OPUS, text: 'VERDICT: APPROVE WF-025\n\nwhy: because' }),
  ]).t;
  assert.equal(early.approvals.size, 0, 'an APPROVE that is not the last line is ignored in all three sources');
  // trailing blank lines and CRLF after the last line are fine
  const last = feedAll([
    subText({ model: OPUS, agent: 'opus-reviewer', text: 'findings\nVERDICT: APPROVE WF-026\n\n  \n' }),
    subHandback({ model: OPUS, agent: 'opus-reviewer', text: 'findings\r\nVERDICT: APPROVE WF-027\r\n' }),
  ]).t;
  assert.deepEqual([...last.approvals.keys()], ['WF-026', 'WF-027']);
  // a late REQUEST_CHANGES still revokes
  const revoked = feedAll([
    subText({ model: OPUS, agent: 'opus-reviewer', text: 'VERDICT: APPROVE WF-028' }),
    subText({ model: OPUS, agent: 'opus-reviewer', text: '1. fix it\nVERDICT: REQUEST_CHANGES WF-028' }),
  ]).t;
  assert.equal(revoked.approvals.has('WF-028'), false);
});

test('a Sonnet APPROVE is ignored, whatever the agent says', () => {
  const { t } = feedAll([
    subText({ model: SONNET, agent: 'opus-reviewer', text: 'VERDICT: APPROVE WF-023' }),
    subHandback({ model: SONNET, agent: 'sonnet-coder', text: 'VERDICT: APPROVE WF-024' }),
    agentResult({ agent: 'sonnet-coder', model: SONNET, text: 'VERDICT: APPROVE WF-025' }),
  ]);
  assert.equal(t.approvals.size, 0);
});

test('an APPROVE written by the main session is ignored, even on Opus', () => {
  const { t } = feedAll([mainText('VERDICT: APPROVE WF-023', OPUS), mainText('VERDICT: APPROVE WF-024', SONNET)]);
  assert.equal(t.approvals.size, 0);
});

test('an Opus verdict from an agent outside the approver set is ignored', () => {
  const { t } = feedAll([subText({ model: OPUS, agent: 'general-purpose', text: 'VERDICT: APPROVE WF-023' })]);
  assert.equal(t.approvals.size, 0);
});

// Finding 6: modelsUsed, handback and the agent type must all check out.
test('a verdict from an unnamed agent is ignored; the agent type may also come from the Agent call that spawned it', () => {
  const noAgent = L({ type: 'assistant', message: { model: OPUS, content: [{ type: 'text', text: 'VERDICT: APPROVE WF-023' }] }, parent_tool_use_id: 'toolu_1' });
  assert.equal(feedAll([noAgent]).t.approvals.size, 0, 'no subagent_type and no known Agent call');
  const spawn = mainTool('toolu_1', 'Agent', { subagent_type: 'opus-reviewer', model: 'opus', prompt: 'review' });
  const named = feedAll([spawn, noAgent]).t;
  assert.equal(named.approvals.get('WF-023').agent, 'opus-reviewer');
  const wrong = mainTool('toolu_1', 'Agent', { subagent_type: 'sonnet-coder', model: 'sonnet', prompt: 'x' });
  assert.equal(feedAll([wrong, noAgent]).t.approvals.size, 0, 'the spawning agent is not an approver');
});

test('an agent result whose modelsUsed holds a non-Opus model is not a verdict, and revokes one taken from its forwarded text', () => {
  const forwarded = subText({ model: OPUS, agent: 'opus-reviewer', text: 'VERDICT: APPROVE WF-023' });
  const mixed = agentResult({ agent: 'opus-reviewer', model: OPUS, text: 'VERDICT: APPROVE WF-023', extra: { modelsUsed: [OPUS, SONNET] } });
  const { t } = feedAll([forwarded, mixed]);
  assert.equal(t.approvals.size, 0, 'the approval from the forwarded text was revoked');
  t.feed(subText({ model: OPUS, agent: 'opus-reviewer', text: 'VERDICT: APPROVE WF-023' }));
  assert.equal(t.approvals.size, 0, 'later text of the tainted call does not count either');
  assert.equal(feedAll([agentResult({ agent: 'opus-reviewer', model: OPUS, text: 'VERDICT: APPROVE WF-024', extra: { modelsUsed: [OPUS, `${OPUS_PREFIX}-20260901`] } })]).t.approvals.has('WF-024'), true, 'all-Opus modelsUsed is fine');
});

test('a hand-back that was flagged or withheld is not a verdict; only a clean send is', () => {
  for (const handback of ['flagged', 'withheld']) {
    const { t } = feedAll([subHandback({ model: OPUS, agent: 'opus-judge', text: 'VERDICT: APPROVE FINAL' }), agentResult({ agent: 'opus-judge', model: OPUS, text: 'VERDICT: APPROVE FINAL', extra: { handback } })]);
    assert.equal(t.approvals.size, 0, handback);
  }
  const ok = feedAll([agentResult({ agent: 'opus-judge', model: OPUS, text: 'VERDICT: APPROVE FINAL', extra: { handback: 'send' } })]).t;
  assert.equal(ok.approvals.get('FINAL').agent, 'opus-judge');
});

test('the last verdict wins: REQUEST_CHANGES revokes, a later APPROVE restores', () => {
  const { t } = feedAll([
    subText({ model: OPUS, agent: 'opus-reviewer', text: 'VERDICT: APPROVE WF-023' }),
    subText({ model: OPUS, agent: 'opus-reviewer', text: '1. fix\nVERDICT: REQUEST_CHANGES WF-023' }),
  ]);
  assert.equal(t.approvals.has('WF-023'), false);
  assert.deepEqual([...t.changesRequested], ['WF-023']);
  t.feed(subText({ model: OPUS, agent: 'opus-reviewer', text: 'VERDICT: APPROVE WF-023' }));
  assert.equal(t.approvals.has('WF-023'), true);
  assert.equal(t.changesRequested.size, 0);
});

test('thinking blocks and tool_use blocks of the main thread are not scanned for verdicts', () => {
  const thinking = L({ type: 'assistant', message: { model: OPUS, content: [{ type: 'thinking', thinking: 'VERDICT: APPROVE WF-023' }] }, parent_tool_use_id: 'toolu_1', subagent_type: 'opus-reviewer' });
  const { t } = feedAll([thinking, mainTool('t1', 'Bash', { command: 'echo VERDICT: APPROVE WF-023' })]);
  assert.equal(t.approvals.size, 0);
});

// ---------------------------------------------------------------------------------------------
// console view, init, errors, rate limits, result
// ---------------------------------------------------------------------------------------------

test('console lines: text truncated, tool hints, subagent text prefixed with agent and model', () => {
  const long = 'x'.repeat(500);
  const { lines } = feedAll([
    init(),
    mainText(long),
    mainTool('t1', 'Bash', { command: 'git status --short' }),
    mainTool('t2', 'Edit', { file_path: 'C:\\repo\\apps\\web\\src\\App.tsx' }),
    mainTool('t3', 'Agent', { subagent_type: 'opus-reviewer', description: 'Review WF-023' }),
    subText({ model: OPUS, agent: 'opus-reviewer', text: 'Looks fine.\nVERDICT: APPROVE WF-023' }),
    result({ permission_denials: [{ tool_name: 'Bash', tool_use_id: 'x', tool_input: {} }] }),
  ]);
  assert.match(lines[0], /^init: model=claude-sonnet-5-5 permissionMode=auto/);
  assert.ok(lines[1].startsWith('say: ') && lines[1].length <= 'say: '.length + 303 && lines[1].endsWith('...'));
  assert.equal(lines[2], 'tool Bash: git status --short');
  assert.equal(lines[3], 'tool Edit: src/App.tsx');
  assert.equal(lines[4], 'tool Agent: opus-reviewer: Review WF-023');
  assert.match(lines[5], /^\[opus-reviewer opus-5-5\] say: Looks fine\. VERDICT: APPROVE WF-023/);
  assert.match(lines[6], /^result: success turns=4 cost=\$0\.12 denials=1/);
});

test('init is captured with the permission mode and API key source', () => {
  const { t, signals } = feedAll([init({ permissionMode: 'default', apiKeySource: 'ANTHROPIC_API_KEY' })]);
  assert.equal(t.init.permissionMode, 'default');
  assert.equal(t.init.apiKeySource, 'ANTHROPIC_API_KEY');
  assert.equal(t.sessionId, 's1');
  assert.equal(signals[0].kind, 'init');
});

test('tool errors are remembered with the tool call they answer', () => {
  const { t, lines } = feedAll([mainTool('t9', 'Bash', { command: 'cat .env' }), toolError('t9', 'PreToolUse:Bash hook error: bash-guard: commands may not mention .env')]);
  assert.equal(t.errorResults.length, 1);
  assert.deepEqual({ id: t.errorResults[0].id, tool: t.errorResults[0].tool, cmd: t.errorResults[0].input.command }, { id: 't9', tool: 'Bash', cmd: 'cat .env' });
  assert.ok(lines.some((l) => l.startsWith('tool error (Bash): PreToolUse:Bash hook error')));
});

test('rate_limit_event: allowed is quiet, rejected and overage are tracked per limit type', () => {
  const { t, lines, signals } = feedAll([
    rate({ status: 'allowed', resetsAt: 1791068400, rateLimitType: 'five_hour', overageStatus: 'rejected', overageDisabledReason: 'out_of_credits', isUsingOverage: false }),
  ]);
  assert.equal(lines.length, 0);
  assert.equal(t.rejected.size, 0);
  assert.equal(t.overageUsed, false);
  assert.equal(t.overageEnabled, false);
  assert.equal(signals[0].kind, 'rate_limit');

  t.feed(rate({ status: 'rejected', resetsAt: 1791100000, rateLimitType: 'seven_day_opus' }));
  assert.equal(t.rejected.get('seven_day_opus').opusWeekly, true);
  t.feed(rate({ status: 'allowed', resetsAt: 1791100000, rateLimitType: 'seven_day_opus' }));
  assert.equal(t.rejected.size, 0, 'cleared when that limit type is allowed again');

  const over = feedAll([rate({ status: 'allowed', rateLimitType: 'five_hour', isUsingOverage: true, overageStatus: 'allowed' })]);
  assert.equal(over.t.overageUsed, true);
  assert.equal(over.t.overageEnabled, true);
  assert.match(over.lines[0], /USING EXTRA USAGE/);
});

test('result event is captured', () => {
  const { t, signals } = feedAll([result({ is_error: true, subtype: 'error_max_turns', result: 'Reached max turns' })]);
  assert.equal(t.result.subtype, 'error_max_turns');
  assert.equal(signals[0].kind, 'result');
});

test('subagent models are collected per agent type for the canary', () => {
  const { t } = feedAll([subText({ model: OPUS, agent: 'opus-judge', text: 'OK' }), subHandback({ model: SONNET, agent: 'sonnet-researcher', text: 'OK' }), agentResult({ agent: 'opus-judge', model: OPUS, text: 'OK' })]);
  assert.deepEqual([...t.subagents.get('opus-judge')], [OPUS]);
  assert.deepEqual([...t.subagents.get('sonnet-researcher')], [SONNET]);
});

test('garbage lines and unknown events are ignored', () => {
  const { t, lines } = feedAll(['', 'not json', '{"type":"system","subtype":"post_turn_summary"}', '[1,2]', '{"type":"stream_event"}']);
  assert.equal(lines.length, 0);
  assert.equal(t.lines, 2);
  assert.equal(parseLine('{"a":1}').a, 1);
  assert.equal(parseLine('nope'), null);
});

test('toolHint shortens paths and commands', () => {
  assert.equal(toolHint('Read', { file_path: '/a/b/c/d.ts' }), 'c/d.ts');
  assert.equal(toolHint('Bash', { command: 'a\n  b' }), 'a b');
  assert.equal(toolHint('Grep', { pattern: 'foo' }), 'foo');
  assert.equal(toolHint('Custom', { x: 1, y: 'hello' }), 'hello');
});

// ---------------------------------------------------------------------------------------------
// limits.mjs
// ---------------------------------------------------------------------------------------------

test('assessRateLimit tolerates missing fields and detects overage use', () => {
  assert.equal(assessRateLimit(null), null);
  assert.equal(assessRateLimit({}).status, 'allowed');
  const a = assessRateLimit({ status: 'rejected', resetsAt: 100, rateLimitType: 'seven_day_opus' });
  assert.deepEqual({ rejected: a.rejected, opusWeekly: a.opusWeekly, resetsAtMs: a.resetsAtMs, usingOverage: a.usingOverage }, { rejected: true, opusWeekly: true, resetsAtMs: 100000, usingOverage: false });
  assert.equal(assessRateLimit({ status: 'allowed', isUsingOverage: true }).usingOverage, true);
  assert.equal(assessRateLimit({ status: 'allowed', overageInUse: true }).usingOverage, true);
  assert.equal(assessRateLimit({ status: 'allowed', rateLimitType: 'overage' }).usingOverage, true);
  const enabled = assessRateLimit({ status: 'allowed', overageStatus: 'allowed', isUsingOverage: false });
  assert.equal(enabled.usingOverage, false);
  assert.equal(enabled.overageEnabled, true);
  assert.equal(assessRateLimit({ status: 'allowed', rateLimitType: 'five_hour', unifiedWindows: { five_hour: { utilization: 0.42, resetsAt: 7 } } }).utilization, 0.42);
});

test('limitPauseDecision: reset plus 60 s, 30 minutes when unknown, Opus weekly flagged', () => {
  const now = 1_000_000_000_000;
  const rejected = assessRateLimit({ status: 'rejected', resetsAt: (now + 2 * 3600 * 1000) / 1000, rateLimitType: 'five_hour' });
  const err = { is_error: true, result: "You've hit your limit" };
  const d = limitPauseDecision({ rejections: [rejected], result: err, nowMs: now });
  assert.equal(d.resumeAtMs, now + 2 * 3600 * 1000 + 60000);
  assert.equal(d.known, true);
  assert.equal(d.type, 'five_hour');
  assert.equal(d.opusWeekly, false);

  const unknown = limitPauseDecision({ rejections: [], result: { is_error: true, result: "5-hour limit reached. Resets 7pm" }, nowMs: now });
  assert.equal(unknown.resumeAtMs, now + 30 * 60 * 1000);
  assert.equal(unknown.known, false);

  const stale = assessRateLimit({ status: 'rejected', resetsAt: (now - 3600 * 1000) / 1000, rateLimitType: 'five_hour' });
  assert.equal(limitPauseDecision({ rejections: [stale], result: err, nowMs: now }).resumeAtMs, now + 30 * 60 * 1000);

  const opus = assessRateLimit({ status: 'rejected', resetsAt: (now + 86400 * 1000) / 1000, rateLimitType: 'seven_day_opus' });
  const both = limitPauseDecision({ rejections: [rejected, opus], result: null, exitCode: 1, nowMs: now });
  assert.equal(both.opusWeekly, true);
  assert.equal(both.type, 'seven_day_opus');
  assert.equal(both.resumeAtMs, now + 86400 * 1000 + 60000);
});

test('limitPauseDecision: a healthy session or an unrelated error is not a limit hit', () => {
  assert.equal(limitPauseDecision({ rejections: [], result: { is_error: false, result: 'done' }, exitCode: 0 }), null);
  assert.equal(limitPauseDecision({ rejections: [], result: { is_error: true, result: 'Reached max turns' }, exitCode: 1 }), null);
  const long = `${'The rate limit middleware is documented here. '.repeat(30)}`;
  assert.equal(limitPauseDecision({ rejections: [], result: { is_error: true, result: long }, exitCode: 1 }), null, 'a long summary is not an error banner');
  assert.notEqual(limitPauseDecision({ rejections: [], result: { is_error: true, api_error_status: 429, result: '' }, exitCode: 1 }), null);
});

test('isAuthError: login and 401 errors, but not transient refresh races or healthy runs', () => {
  assert.equal(isAuthError({ result: { is_error: true, result: 'Not logged in. Please run /login' } }), true);
  assert.equal(isAuthError({ result: { is_error: true, result: 'Failed to authenticate. API Error: 401' } }), true);
  assert.equal(isAuthError({ result: { is_error: true, api_error_status: 401, result: '' } }), true);
  assert.equal(isAuthError({ result: null, stderr: 'Invalid API key', exitCode: 1 }), true);
  assert.equal(isAuthError({ result: { is_error: true, result: 'Failed to refresh OAuth token: another Claude Code process is refreshing it' } }), false);
  assert.equal(isAuthError({ result: { is_error: false, result: 'I fixed the 401 handler' } }), false);
  assert.equal(isAuthError({ result: { is_error: true, result: 'Reached max turns' } }), false);
});

test('autoModeUnavailable separates a permanent block from a classifier outage', () => {
  assert.equal(autoModeUnavailable('auto mode is unavailable for your plan'), 'permanent');
  assert.equal(autoModeUnavailable("auto mode isn't available in this session"), 'permanent');
  assert.equal(autoModeUnavailable('auto mode disabled by settings'), 'permanent');
  assert.equal(autoModeUnavailable('Auto mode is unavailable: the server returned no safety verdict for 3 responses in a row'), 'transient');
  assert.equal(autoModeUnavailable('all good'), null);
});

const denial = (n, command) => ({ tool_name: 'Bash', tool_use_id: `t${n}`, tool_input: { command } });

test('denialSummary: five real denials stop the run, guard blocks are listed but not counted', () => {
  const four = { permission_denials: [1, 2, 3, 4].map((n) => denial(n, `cmd${n}`)) };
  assert.equal(denialSummary(four).tooMany, false);
  const five = { permission_denials: [1, 2, 3, 4, 5].map((n) => denial(n, `cmd${n}`)) };
  const s = denialSummary(five);
  assert.deepEqual({ total: s.total, counted: s.counted, tooMany: s.tooMany }, { total: 5, counted: 5, tooMany: true });

  const errors = [1, 2, 3, 4, 5].map((n) => ({ id: `t${n}`, tool: 'Bash', input: { command: `cmd${n}` }, text: 'PreToolUse:Bash hook error: bash-guard: force-pushing is not allowed' }));
  const guarded = denialSummary(five, errors);
  assert.deepEqual({ total: guarded.total, counted: guarded.counted, tooMany: guarded.tooMany }, { total: 5, counted: 0, tooMany: false });
  assert.ok(guarded.items.every((i) => i.guard));
});

test('denialSummary: the classifier abort message stops the run and lists what it knows', () => {
  const errs = [{ id: 'a', tool: 'Bash', input: { command: 'npm i evil' }, text: 'Blocked by the auto mode classifier' }];
  const s = denialSummary({ result: 'Agent aborted: too many classifier denials in headless mode', permission_denials: [] }, errs);
  assert.equal(s.tooMany, true);
  assert.equal(s.aborted, true);
  assert.equal(s.items.length, 1);
  const text = formatDenials(s).join('\n');
  assert.match(text, /1\. Bash \{"command":"npm i evil"\}/);
  assert.match(text, /Blocked by the auto mode classifier/);
});

test('a full session fixture end to end: init, work, Opus APPROVE, Sonnet APPROVE ignored, limit, denials', () => {
  const { t } = feedAll([
    init(),
    mainText('Reading the plan.'),
    mainTool('b1', 'Bash', { command: 'npm run lint' }),
    subText({ model: SONNET, agent: 'sonnet-coder', text: 'Done.\nVERDICT: APPROVE WF-100' }),
    subHandback({ model: OPUS, agent: 'opus-reviewer', text: 'Solid.\nVERDICT: APPROVE WF-023' }),
    rate({ status: 'allowed_warning', rateLimitType: 'seven_day', resetsAt: 1791640800, utilization: 0.76 }),
    result({ permission_denials: [denial(1, 'a'), denial(2, 'b')] }),
  ]);
  assert.deepEqual([...t.approvals.keys()], ['WF-023']);
  assert.equal(t.result.permission_denials.length, 2);
  assert.equal(denialSummary(t.result, t.errorResults).tooMany, false);
  assert.equal(t.rejected.size, 0);
});

// ---------------------------------------------------------------------------------------------
// canary evaluators
// ---------------------------------------------------------------------------------------------

test('canary a: Opus judge, Sonnet researcher and auto mode', () => {
  const ok = feedAll([init(), subText({ model: OPUS, agent: 'opus-judge', text: 'OK' }), subText({ model: SONNET, agent: 'sonnet-researcher', text: 'OK' }), result()]).t;
  assert.equal(evalSubagentModels(ok).pass, true);
  const wrong = feedAll([init(), subText({ model: SONNET, agent: 'opus-judge', text: 'OK' }), subText({ model: SONNET, agent: 'sonnet-researcher', text: 'OK' }), result()]).t;
  assert.equal(evalSubagentModels(wrong).pass, false);
  const notAuto = feedAll([init({ permissionMode: 'default' }), subText({ model: OPUS, agent: 'opus-judge', text: 'OK' }), subText({ model: SONNET, agent: 'sonnet-researcher', text: 'OK' }), result()]).t;
  assert.equal(evalSubagentModels(notAuto).pass, false);
  assert.equal(evalSubagentModels(feedAll([init(), result()]).t).pass, false, 'agents that never ran fail');
});

test('fix 8: canary a compares the permission mode with the active profile (dontAsk passes only when dontAsk is expected)', () => {
  const agents = [subText({ model: OPUS, agent: 'opus-judge', text: 'OK' }), subText({ model: SONNET, agent: 'sonnet-researcher', text: 'OK' }), result()];
  const dontAsk = feedAll([init({ permissionMode: 'dontAsk' }), ...agents]).t;
  assert.equal(evalSubagentModels(dontAsk, 'dontAsk').pass, true);
  assert.equal(evalSubagentModels(dontAsk).pass, false, 'the default expects auto');
  assert.equal(evalSubagentModels(dontAsk, 'auto').pass, false);
  const auto = feedAll([init({ permissionMode: 'auto' }), ...agents]).t;
  assert.equal(evalSubagentModels(auto, 'auto').pass, true);
  assert.equal(evalSubagentModels(auto, 'dontAsk').pass, false, 'auto mode is not the dontAsk profile');
  assert.ok(evalSubagentModels(dontAsk, 'dontAsk').details.includes('init permissionMode: dontAsk'));
});

test('canary b: zero denials', () => {
  assert.equal(evalCommands(feedAll([init(), result()]).t).pass, true);
  assert.equal(evalCommands(feedAll([init(), result({ permission_denials: [denial(1, 'uv --version')] })]).t).pass, false);
  assert.equal(evalCommands(feedAll([init()]).t).pass, false);
});

test('canary c: cat .env.canary (a decoy) must be blocked by the bash-guard hook, not merely denied, and never run', () => {
  const guardMsg = 'PreToolUse:Bash hook error: bash-guard: commands may not mention .env.canary';
  const hook = L({ type: 'system', subtype: 'hook_response', hook_event: 'PreToolUse', hook_name: 'PreToolUse:Bash', exit_code: 2, outcome: 'error', stderr: 'bash-guard: commands may not mention .env.canary' });
  const refused = feedAll([init(), mainTool('c1', 'Bash', { command: 'cat .env.canary' }), hook, toolError('c1', guardMsg), result({ permission_denials: [denial(1, 'cat .env.canary')] })]).t;
  assert.equal(evalEnvRefused(refused).pass, true);
  // refused by a permission denial only: no hook response, so the hook is unproven
  const denied = feedAll([init(), mainTool('c1', 'Bash', { command: 'cat .env.canary' }), toolError('c1', 'Permission denied'), result({ permission_denials: [denial(1, 'cat .env.canary')] })]).t;
  const d = evalEnvRefused(denied);
  assert.equal(d.pass, false);
  assert.ok(d.details.some((x) => /no bash-guard hook block/.test(x)));
  // a PreToolUse block by another hook does not count
  const other = L({ type: 'system', subtype: 'hook_response', hook_event: 'PreToolUse', hook_name: 'PreToolUse:Bash', exit_code: 2, outcome: 'error', stderr: 'some-other-hook: no' });
  assert.equal(evalEnvRefused(feedAll([init(), mainTool('c1', 'Bash', { command: 'cat .env.canary' }), other, toolError('c1', guardMsg), result()]).t).pass, false);
  const ran = feedAll([init(), mainTool('c1', 'Bash', { command: 'cat .env.canary' }), hook, result()]).t;
  const r = evalEnvRefused(ran);
  assert.equal(r.pass, false);
  assert.ok(r.details.some((x) => /NOT refused/.test(x)));
  const example = feedAll([init(), mainTool('c2', 'Bash', { command: 'cat .env.example' }), result()]).t;
  assert.equal(evalEnvRefused(example).pass, false, 'no .env call at all is not a pass');
  assert.equal(CANARY_PROMPTS.c, 'Run: cat .env.canary');
});

test('canary d: a general-purpose agent on Opus must be blocked by the agent-guard hook', () => {
  const block = L({ type: 'system', subtype: 'hook_response', hook_event: 'PreToolUse', hook_name: 'PreToolUse:Agent', exit_code: 2, outcome: 'error', stderr: 'agent-guard: general-purpose needs model "sonnet" explicitly' });
  const ok = feedAll([init(), mainTool('d1', 'Agent', { subagent_type: 'general-purpose', model: 'opus', prompt: 'reply OK' }), block, result()]).t;
  assert.equal(evalAgentGuard(ok).pass, true);
  const retried = feedAll([init(), block, subText({ model: SONNET, agent: 'general-purpose', text: 'OK' }), result()]).t;
  assert.equal(evalAgentGuard(retried).pass, true, 'a retry on Sonnet is allowed');
  const ran = feedAll([init(), subText({ model: OPUS, agent: 'general-purpose', text: 'OK' }), result()]).t;
  const r = evalAgentGuard(ran);
  assert.equal(r.pass, false);
  assert.ok(r.details.some((x) => /NOT refused/.test(x)));
  assert.equal(evalAgentGuard(feedAll([init(), result()]).t).pass, false, 'no hook block seen');
  const bash = L({ type: 'system', subtype: 'hook_response', hook_event: 'PreToolUse', hook_name: 'PreToolUse:Bash', exit_code: 2, outcome: 'error', stderr: 'bash-guard: x' });
  assert.equal(evalAgentGuard(feedAll([init(), bash, result()]).t).pass, false, 'only agent-guard counts');
  assert.match(CANARY_PROMPTS.d, /subagent_type "general-purpose", model "opus"/);
});

// ---------------------------------------------------------------------------------------------
// status.mjs helper
// ---------------------------------------------------------------------------------------------

test('lastAssistantLines: main-thread text only, last N lines, a cut first line is dropped', () => {
  const lines = [
    'xxxx cut line from the middle of an event',
    mainText('first\nsecond'),
    subText({ model: OPUS, agent: 'opus-reviewer', text: 'subagent text must not show' }),
    mainText('third'),
    mainTool('z', 'Bash', { command: 'ls' }),
    mainText('fourth\n\n  fifth  '),
  ].join('\n');
  assert.deepEqual(lastAssistantLines(lines, true, 3), ['third', 'fourth', 'fifth']);
  assert.deepEqual(lastAssistantLines(lines, true, 15), ['first', 'second', 'third', 'fourth', 'fifth']);
  assert.deepEqual(lastAssistantLines('', false), []);
});
