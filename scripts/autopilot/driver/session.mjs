// One `claude -p` session: spawn, stream, watchdog, and what to do about limits, auth and denials.
//
// spawnClaude   runs one process and returns what it saw.
// runPhaseSession wraps it with the guards: overage (exit 4), auth (exit 5), denials (exit 3),
//               the auto-mode fallback, and usage-limit sleeps that resume the same session.

import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import readline from 'node:readline';
import { buildChildEnv, buildClaudeArgs, formatCommand, modelForMode } from '../lib/cmd.mjs';
import { autoModeUnavailable, denialSummary, formatDenials, isAuthError, limitPauseDecision } from '../lib/limits.mjs';
import { StreamTracker } from '../lib/stream.mjs';
import { buildSessionInput, buildTaskLine, CONTINUE_TEXT, logFileName, sessionName, verdictAllowed } from '../lib/task.mjs';
import { DriverExit, PATHS, ROOT, say, updateLock, warn } from './ctx.mjs';
import { clearStaleGitLocks } from './git.mjs';
import { killTree, sleep } from './sys.mjs';

export const IDLE_MS = 45 * 60 * 1000; // no stream event for this long: the session is stuck
export const TOTAL_MS = 5 * 60 * 60 * 1000; // hard ceiling for one session
const MAX_LIMIT_CYCLES = 60; // consecutive usage-limit sleeps before giving up

// Tests shorten these through the environment; real runs use the defaults (reset + 60 s, or 30 min).
const limitTimings = () => ({
  ...(process.env.AUTOPILOT_LIMIT_GRACE_MS ? { graceMs: Number(process.env.AUTOPILOT_LIMIT_GRACE_MS) } : {}),
  ...(process.env.AUTOPILOT_LIMIT_WAIT_MS ? { defaultWaitMs: Number(process.env.AUTOPILOT_LIMIT_WAIT_MS) } : {}),
});

const idleMs = () => Number(process.env.AUTOPILOT_IDLE_MS) || IDLE_MS;
const totalMs = () => Number(process.env.AUTOPILOT_TOTAL_MS) || TOTAL_MS;

/** auto mode, unless the owner chose the dontAsk profile with --permission-profile dontask. Never switched by the driver. */
export const permissionFor = (ctx) => (ctx.args?.permissionProfile === 'dontask' ? 'dontAsk' : 'auto');

const billsApi = (src) => Boolean(src) && src !== 'none' && /key|helper|anthropic|env/i.test(String(src));

/** Run one claude process. Returns what the stream showed; policy lives in runPhaseSession. */
export async function spawnClaude(ctx, spec) {
  const permission = permissionFor(ctx);
  const model = spec.model ?? modelForMode(spec.mode);
  const name = spec.name ?? sessionName(spec);
  const args = buildClaudeArgs({ model, permission, name, resumeId: spec.resumeId, appendPromptFile: ctx.appendPrompt, hookEvents: spec.hookEvents });
  const env = buildChildEnv(process.env, { mode: spec.mode, extraPathDirs: ctx.extraPathDirs });
  if (spec.maxTurns) env.CLAUDE_CODE_MAX_TURNS = String(spec.maxTurns);

  fs.mkdirSync(PATHS.logs, { recursive: true });
  const logFile = path.join(PATHS.logs, logFileName({ unit: spec.unit, mode: spec.mode, step: spec.step, date: new Date() }));
  const log = fs.createWriteStream(logFile, { flags: 'a' });
  const writeLog = (obj) => log.write(`${JSON.stringify({ type: 'driver', at: new Date().toISOString(), ...obj })}\n`);
  const tag = `${spec.unit} ${spec.mode}${spec.step ? ` ${spec.step}` : ''}${spec.attempt ? ` #${spec.attempt}` : ''}`;

  const rec = { mode: spec.mode, step: spec.step ?? null, sessionId: null, startedAt: new Date().toISOString(), endedAt: null, result: null, denials: 0, attempt: spec.attempt ?? null, model, permission, log: path.relative(ROOT, logFile) };
  if (!spec.noState) {
    ctx.state.data.sessions.push(rec);
    ctx.state.save();
  }

  say(`=== ${tag} | ${model} | ${permission}${spec.resumeId ? ` | resume ${spec.resumeId.slice(0, 8)}` : ''} | log ${path.relative(ROOT, logFile)}`);
  writeLog({ subtype: 'spawn', command: formatCommand(ctx.claudeExe, [...ctx.claudePre, ...args]), cwd: ROOT, model, permission, resumeId: spec.resumeId ?? null });

  const tracker = new StreamTracker();
  const child = spawn(ctx.claudeExe, [...ctx.claudePre, ...args], { cwd: ROOT, env, shell: false, windowsHide: true, stdio: ['pipe', 'pipe', 'pipe'], detached: process.platform !== 'win32' });
  ctx.child = child;
  updateLock({ childPid: child.pid ?? null });

  let stderrTail = '';
  let killedBy = null;
  let lastEvent = Date.now();
  const startedAtMs = Date.now();
  const kill = (reason) => {
    if (killedBy) return;
    killedBy = reason;
    warn(`[${tag}] killing the session: ${reason}`);
    writeLog({ subtype: 'kill', reason });
    killTree(child.pid);
  };

  child.stderr.setEncoding('utf8');
  child.stderr.on('data', (d) => {
    stderrTail = (stderrTail + d).slice(-8192);
    writeLog({ subtype: 'stderr', text: d });
  });
  child.stdin.on('error', () => {});

  const handle = (s) => {
    if (s.kind === 'init') {
      rec.sessionId = s.init.sessionId;
      if (s.init.permissionMode !== permission) kill('permission-mode');
      else if (billsApi(s.init.apiKeySource)) kill('api-key');
    } else if (s.kind === 'rate_limit') {
      const a = s.assessment;
      if (a.usingOverage) kill('overage');
      else if (a.rejected && a.opusWeekly) kill('opus-weekly');
      if (a.overageEnabled && !ctx.overageWarned) {
        ctx.overageWarned = true;
        warn('extra usage looks ENABLED on this account: turn it off in claude.ai settings so the build can never spend money');
      }
    }
  };

  const rl = readline.createInterface({ input: child.stdout, crlfDelay: Infinity });
  rl.on('line', (line) => {
    lastEvent = Date.now();
    log.write(`${line}\n`);
    const { lines, signals } = tracker.feed(line);
    for (const l of lines) say(`[${tag}] ${l}`);
    for (const s of signals) handle(s);
  });
  const rlClosed = new Promise((res) => rl.on('close', res));

  const watchdog = setInterval(() => {
    const now = Date.now();
    if (now - lastEvent > idleMs()) kill('watchdog-idle');
    else if (now - startedAtMs > totalMs()) kill('watchdog-total');
  }, Math.min(30000, Math.max(250, Math.floor(idleMs() / 4))));

  const closed = new Promise((res) => {
    child.on('error', (e) => {
      stderrTail += `\n${e.message}`;
      writeLog({ subtype: 'spawn-error', message: e.message });
      res({ code: -1 });
    });
    child.on('close', (code, signal) => res({ code, signal }));
  });

  child.stdin.end(spec.stdinText);
  const exit = await closed;
  await new Promise((res) => {
    const t = setTimeout(res, 5000); // never wait long for the last stdout line
    rlClosed.then(() => {
      clearTimeout(t);
      res();
    });
  });
  clearInterval(watchdog);
  ctx.child = null;
  updateLock({ childPid: null });
  if (killedBy) {
    const removed = clearStaleGitLocks();
    if (removed.length) warn(`removed git lock file(s) left by the killed session: ${removed.join(', ')}`);
  }

  const result = tracker.result;
  rec.endedAt = new Date().toISOString();
  rec.result = killedBy ? `killed:${killedBy}` : result ? (result.is_error ? `error:${result.subtype}` : 'success') : `exit:${exit.code}`;
  rec.cost = result?.total_cost_usd ?? null;
  ctx.cost += Number(result?.total_cost_usd ?? 0);
  writeLog({ subtype: 'end', exitCode: exit.code, killedBy, result: rec.result });
  await new Promise((res) => log.end(res));
  if (!spec.noState) ctx.state.save();

  return { tracker, result, sessionId: tracker.sessionId ?? rec.sessionId, killedBy, exitCode: exit.code, stderrTail, logFile, rec, permission };
}

/**
 * Keep the verdicts this session may earn (task.mjs verdictAllowed: a ticket session only its own step,
 * a ship session only ship-<unit>, a ci-fix only ci-fix-<pr>-<n>, final only FINAL) with the branch and
 * PR they were given for. Everything else a session printed is ignored.
 */
function mergeApprovals(ctx, tracker, spec) {
  const st = ctx.state.data;
  const allowed = verdictAllowed(spec);
  for (const [id, a] of tracker.approvals) if (allowed(id)) st.approvals[id] = { ...a, branch: spec.branch ?? null, pr: spec.pr ?? null };
  for (const id of tracker.changesRequested) if (allowed(id)) delete st.approvals[id];
  ctx.state.save();
}

export function recordStop(ctx, reason, ownerAction) {
  ctx.state.data.phase = 'stopped';
  ctx.state.data.stopped = { reason, ownerAction };
  ctx.state.save();
}

/**
 * Run a session with the unattended-run guards. spec: {mode, unit, step?, pr?, branch?, attempt,
 * failedChecks?, retryNote?, resumeId?}. Returns the last spawnClaude outcome plus
 * {resumable, transient}. Throws DriverExit for exits 1 (auto mode unavailable), 3, 4 and 5.
 */
export async function runPhaseSession(ctx, spec) {
  const fresh = () => buildSessionInput({ taskLine: buildTaskLine(spec), failedChecks: spec.failedChecks, retryNote: spec.retryNote });
  let resumeId = spec.resumeId ?? null;
  let stdinText = resumeId ? `${CONTINUE_TEXT}\n` : fresh();

  for (let cycle = 0; cycle < MAX_LIMIT_CYCLES; cycle++) {
    const out = await spawnClaude(ctx, { ...spec, resumeId, stdinText });
    mergeApprovals(ctx, out.tracker, spec);
    const text = `${out.result?.result ?? ''}\n${out.stderrTail}`;

    // 1. Money: paid extra usage is never acceptable.
    if (out.tracker.overageUsed || out.killedBy === 'overage') {
      const why = 'extra usage is on: turn it off in claude.ai settings (Settings, Usage, Extra usage), then rerun.';
      recordStop(ctx, 'extra usage was drawn on', why);
      throw new DriverExit(4, `The session was drawing on paid extra usage and was killed.\n${why}`);
    }
    if (out.killedBy === 'api-key') {
      const why = 'Remove ANTHROPIC_API_KEY, ANTHROPIC_AUTH_TOKEN and any apiKeyHelper, then rerun: the build must run on the subscription.';
      recordStop(ctx, 'session would bill an API key', why);
      throw new DriverExit(5, `The session started with an API key as its credential, so it was killed.\n${why}`);
    }

    // 2. Permission mode. The driver never loosens the rules by itself: if auto mode is not available it
    // stops and tells the owner, who may opt in to the narrower dontAsk profile.
    const errored = !out.result || out.result.is_error === true;
    const mode = errored ? autoModeUnavailable(text) : null;
    if (out.killedBy === 'permission-mode' || (mode === 'permanent' && out.permission === 'auto')) {
      if (out.permission === 'dontAsk') throw new DriverExit(1, `The session did not start in dontAsk mode.\nOwner action: run "node scripts/autopilot/run.mjs --canary --permission-profile dontask" and read the init event in the newest log.`);
      throw new DriverExit(
        1,
        `Auto mode is not available for this session (${out.killedBy === 'permission-mode' ? 'claude did not start in auto mode' : 'claude reported it as unavailable'}).\n` +
          'Owner action: fix the cause (auto mode needs a plan and a model that support it, and no policy that disables it), or opt in to the dontAsk profile by rerunning with "--permission-profile dontask".\n' +
          'dontAsk has no classifier: it runs only what scripts/autopilot/settings-dontask.json allows (npm run, npm ci, node scripts/*, uv run, git, gh pr, and the shell basics), so read that list first. The guard hooks stay on in both profiles.',
      );
    }

    // 3. Auth: never retried.
    if (isAuthError({ result: out.result, stderr: out.stderrTail, exitCode: out.exitCode })) {
      const why = 'Run: claude auth login, then rerun the driver.';
      recordStop(ctx, 'claude authentication failed', why);
      throw new DriverExit(5, `Claude authentication failed: ${String(out.result?.result ?? out.stderrTail).trim().slice(0, 300)}\n${why}`);
    }

    // 4. Denials: stop and show every one so the owner can add an allow rule.
    const den = denialSummary(out.result, out.tracker.errorResults);
    out.rec.denials = den.counted;
    if (den.tooMany) {
      const why = 'Review the denials below. A needed action: add an allow rule to autoMode.allow in scripts/autopilot/settings.json (and the dontAsk list), or a deny of something it should never do. Then rerun.';
      recordStop(ctx, `${den.counted} permission denials in one session`, why);
      throw new DriverExit(3, `${den.aborted ? 'The session was aborted for too many classifier denials' : `${den.counted} permission denials in one session (limit 5)`}:\n${formatDenials(den).join('\n')}\n${why}`);
    }

    // 5. Usage limits: sleep until the reset, then resume the same session (not an attempt).
    const lim = limitPauseDecision({ rejections: [...out.tracker.rejected.values()], result: out.result, exitCode: out.exitCode, ...limitTimings() });
    if (lim) {
      await sleepUntil(ctx, lim.resumeAtMs, lim.opusWeekly ? `weekly Opus limit (judgement must not fall back to Sonnet)` : lim.reason);
      resumeId = out.sessionId ?? null;
      stdinText = resumeId ? `${CONTINUE_TEXT}\n` : fresh();
      continue;
    }

    // 6. Classifier outage: a plain failed attempt after a short wait.
    if (mode === 'transient') {
      say('the auto-mode classifier is unavailable; waiting 2 minutes before the next attempt');
      await sleep(120000);
      return { ...out, resumable: false, transient: true };
    }

    // 7. A watchdog kill leaves a session that can be resumed (and counts as an attempt).
    const watchdog = out.killedBy === 'watchdog-idle' || out.killedBy === 'watchdog-total';
    return { ...out, resumable: watchdog && Boolean(out.sessionId), transient: false };
  }
  throw new DriverExit(1, 'The usage limit did not clear after 60 sleeps; giving up.\nFix: check claude.ai usage, then rerun.');
}

/** Sleep until a wall-clock time, in short slices so a laptop sleep does not overshoot. */
export async function sleepUntil(ctx, wakeMs, reason) {
  const st = ctx.state.data;
  st.pause = { until: new Date(wakeMs).toISOString(), reason, since: new Date().toISOString() };
  ctx.state.save();
  say(`PAUSED (${reason}). Sleeping until ${new Date(wakeMs).toLocaleString()}`);
  while (Date.now() < wakeMs) await sleep(Math.min(60000, Math.max(1000, wakeMs - Date.now())));
  st.pause = null;
  ctx.state.save();
  say('pause over; resuming');
}
