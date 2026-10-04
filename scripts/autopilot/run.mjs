#!/usr/bin/env node
// Hermi autopilot driver. Builds Phase 1 unattended: S1..S3, 01..28, FINAL.
//
//   node scripts/autopilot/run.mjs [--dry-run] [--once] [--unit <id>] [--canary] [--permission-profile dontask] [--help]
//
// Per unit: a plan session (Opus), one ticket session per plan step (Sonnet, Opus verdicts through
// subagents), a ship session (Sonnet), then THIS PROGRAM waits for the required `ci` check and merges.
// Sessions never merge. State lives in git, GitHub, PROGRESS.md and .autopilot/state.json.
// Exit codes: 0 done, 1 error, 2 stopped (owner action), 3 permission denials, 4 extra usage,
// 5 authentication, 130 Ctrl+C. Tests: node --test "scripts/autopilot/**/*.test.mjs"

import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { buildChildEnv, buildClaudeArgs, formatCommand, modelForMode, SONNET_MODEL } from './lib/cmd.mjs';
import { CANARY_PROMPTS, evalAgentGuard, evalCommands, evalEnvRefused, evalSubagentModels } from './lib/canary.mjs';
import { classifyChecks, failedRunIds, hasLabel, hasNoChecks, LABEL_E2E, LABEL_STOPPED } from './lib/ci.mjs';
import { validatePlan } from './lib/plan.mjs';
import { isDoneForPr, parseProgress, progressCounts, rowForUnit, selectNextUnit } from './lib/progress.mjs';
import { approverFor, buildFailedChecksBlock, buildTaskLine, ciFixVerdictId, expectedBranch, FINAL_VERDICT_ID, formatDay, hasStepCommit, isShipSafePath, parsePromptTickets, promptFileForUnit, sessionName, shipVerdictId, slugFromPromptFile, uncoveredStepIds, unitKind } from './lib/task.mjs';
import { createCtx, DriverExit, FILES, newStateData, PATHS, releaseLock, readStopFile, ROOT, say, warn, writeStopFile } from './driver/ctx.mjs';
import { addLabel, autopilotEdits, branchFiles, branchOnOrigin, changedFiles, checkoutBranch, currentBranch, deleteLocalBranch, fetchBranch, fileExistsOnRef, gh, ghJson, git, isTransientGhError, originHead, prepareTree, prView, progressOnRef, pushLeftovers, showFile, stepSubjects } from './driver/git.mjs';
import { enforce, environmentChecks, freePorts, mainCiState, printResults } from './driver/preflight.mjs';
import { permissionFor, recordStop, runPhaseSession, spawnClaude } from './driver/session.mjs';
import { killTree, readJson, sleep, writeJsonAtomic } from './driver/sys.mjs';

const MAX_ATTEMPTS = 3; // per plan, ticket step or ship session
const MAX_CI_FIX = 3; // ci-fix sessions per PR
const CI_MAX_MS = 3 * 60 * 60 * 1000; // one wait for the ci check
const MAIN_CI_WAIT_MS = 30 * 60 * 1000;

// Tests shorten these through the environment; real runs poll every 30 s and give a missing ci check 10 minutes to appear.
const ciPollMs = () => Number(process.env.AUTOPILOT_CI_POLL_MS) || 30000;
const ciMissingRetries = () => Number(process.env.AUTOPILOT_CI_MISSING_RETRIES) || 20;

const USAGE = `Usage: node scripts/autopilot/run.mjs [options]
  --dry-run                    run every preflight check, change nothing, print the next unit and the exact command
  --once                       run one unit (merge it), then exit 0
  --unit <id>                  run only this unit (S1..S3, 01..28 or FINAL), even if PROGRESS says Done (a Stopped row still stops it)
  --canary                     four short sessions that prove the model pins, auto mode, hooks and denials (uses a little quota)
  --permission-profile dontask opt in to the dontAsk profile (scripts/autopilot/settings-dontask.json) instead of auto mode;
                               the driver never switches to it by itself
  --help                       this text
Exit codes: 0 done, 1 error, 2 stopped (owner action), 3 permission denials, 4 extra usage on, 5 authentication, 130 Ctrl+C.`;

export function parseArgs(argv) {
  const o = { dryRun: false, once: false, unit: null, canary: false, help: false, permissionProfile: 'auto' };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--dry-run') o.dryRun = true;
    else if (a === '--once') o.once = true;
    else if (a === '--canary') o.canary = true;
    else if (a === '--help' || a === '-h') o.help = true;
    else if (a === '--unit') {
      const v = argv[++i];
      if (!v || !/^(S[1-9]\d*|\d{2}|FINAL)$/.test(v)) throw new Error('--unit needs S1..S3, 01..28 or FINAL');
      o.unit = v;
    } else if (a === '--permission-profile') {
      const v = argv[++i];
      if (v !== 'dontask') throw new Error('--permission-profile only accepts "dontask" (auto mode is the default)');
      o.permissionProfile = v;
    } else throw new Error(`unknown option: ${a}`);
  }
  return o;
}

// ---------------------------------------------------------------------------------------------
// Stops
// ---------------------------------------------------------------------------------------------

/** The unit cannot continue without the owner: stop.json, state, label on the PR, exit 2. */
function stopUnit(ctx, { unit, pr, reason, ownerAction }) {
  const action = `${ownerAction}\nThen delete .autopilot/stop.json${pr ? ` and run: gh pr edit ${pr} --remove-label ${LABEL_STOPPED}` : ''}, and rerun the driver.`;
  writeStopFile({ unit, reason, ownerAction: action });
  recordStop(ctx, reason, action);
  if (pr && ctx.ghReady) addLabel(ctx, pr, LABEL_STOPPED);
  throw new DriverExit(2, `STOPPED on unit ${unit}: ${reason}\nOwner action: ${action}`);
}

/** A session may have written stop.json itself (the closed list of stop reasons), or the file may be unreadable: either way the run halts. */
function checkSessionStop(ctx) {
  const s = readStopFile();
  if (!s) return;
  recordStop(ctx, s.reason, s.ownerAction);
  throw new DriverExit(2, `The session stopped on unit ${s.unit}: ${s.reason}\nOwner action: ${s.ownerAction}\nThen delete .autopilot/stop.json, remove the autopilot:stopped label, and rerun.`);
}

/**
 * Sessions must never change scripts/autopilot/, .claude/agents/, .claude/settings.json or .mcp.json. The permission rules and the hook are the first line;
 * this is the backstop, and it runs again right before every merge (a ci-fix session is covered too).
 */
function checkNoAutopilotEdits(ctx, unit, { branch, pr }) {
  if (!branch) return;
  const f = fetchBranch(branch);
  if (f.code !== 0) throw new DriverExit(1, `git fetch origin ${branch} failed: ${(f.stderr || f.stdout).trim()}\nFix: check the network, then rerun.`);
  const edits = autopilotEdits(branch);
  if (edits.length) {
    stopUnit(ctx, {
      unit,
      pr,
      reason: `a session changed owner-controlled files (scripts/autopilot/, .claude/agents/, .claude/settings.json, .mcp.json): ${edits.join(', ')}`,
      ownerAction: `Review those changes on ${branch}. Revert them (restore the files from origin/main on the branch, commit, push) unless you want them.`,
    });
  }
}

// ---------------------------------------------------------------------------------------------
// Approvals: which Opus verdicts a merge needs, and which of them count
// ---------------------------------------------------------------------------------------------

/** Why an approval does not count, or null when it does. */
function approvalProblem(st, id, { branch, pr }) {
  const a = st.approvals[id];
  if (!a) return 'none was seen';
  const who = approverFor(id);
  if (!who.includes(a.agent)) return `it came from ${a.agent ?? 'an unnamed agent'}, and only ${who.join(' or ')} may give it`;
  if (a.branch && branch && a.branch !== branch) return `it was given for branch ${a.branch}, not ${branch}`;
  if (a.pr && pr && Number(a.pr) !== Number(pr)) return `it was given for PR #${a.pr}, not #${pr}`;
  return null;
}

/** Step ids of the commits on origin/<branch> beyond main that no valid approval covers: a commit nobody reviewed. Call fetchBranch first. */
function uncoveredStepCommits(ctx, { branch, pr }) {
  const st = ctx.state.data;
  return uncoveredStepIds(stepSubjects(branch), Object.keys(st.approvals).filter((id) => approvalProblem(st, id, { branch, pr }) === null));
}

/** Every verdict id a merge needs: each plan step, FINAL for the final gate, and the ship and ci-fix ids the driver found necessary. */
function neededApprovals(ctx, { unit, steps }) {
  return [...steps.map((s) => s.id), ...(unit === 'FINAL' ? [FINAL_VERDICT_ID] : []), ...Object.keys(ctx.state.data.required ?? {})];
}

const missingApprovals = (ctx, ids, where) => ids.filter((id) => approvalProblem(ctx.state.data, id, where));

/** Only the newest ci-fix attempt needs an approval: its reviewer reads the diff of every ci-fix commit on the PR so far. */
function requireCiFix(st, id) {
  for (const k of Object.keys(st.required)) if (k.startsWith('ci-fix-')) delete st.required[k];
  st.required[id] = { agent: 'opus-judge' };
}

// ---------------------------------------------------------------------------------------------
// Before every session
// ---------------------------------------------------------------------------------------------

/**
 * Preflight and cleanup: environment checks, free the dev ports, push leftovers, stash, main
 * up to date, main's CI green (else a ci-fix unit first), then the unit branch if one is wanted.
 * With resume: a session the watchdog killed is about to be resumed in the same checkout, so its
 * uncommitted work stays where it is (no stash, no checkout).
 */
async function beforeSession(ctx, { branch = null, skipMainCi = false, resume = false } = {}) {
  enforce(environmentChecks(ctx), ctx);
  enforce(freePorts(), ctx);
  if (resume && branch && currentBranch() === branch) return;
  prepareTree();
  if (!skipMainCi) await ensureMainGreen(ctx);
  if (branch) checkoutBranch(branch);
}

/** After a session: push its commits. A killed session that will be resumed keeps its tree; any other leaves it on main. */
function settleTree(out) {
  if (out.resumable) pushLeftovers();
  else prepareTree();
}

/** Wait (up to 30 min) for a running ci on main to settle. */
async function settledMainCi(ctx) {
  const t0 = Date.now();
  let cls = mainCiState(ctx);
  while (cls.state === 'running' && Date.now() - t0 < MAIN_CI_WAIT_MS) {
    say('the latest ci run on main is still running; waiting');
    await sleep(60000);
    cls = mainCiState(ctx);
  }
  if (cls.state === 'running') warn('the latest ci run on main is still running after 30 minutes; continuing');
  return cls;
}

/** A red main is repaired first, by ci-fix sessions (UNIT=main) and a fix/main-ci-<date> PR. */
async function ensureMainGreen(ctx) {
  let cls = await settledMainCi(ctx);
  for (let round = 1; cls.state === 'red' && round <= MAX_CI_FIX; round++) {
    say(`main CI is RED (run ${cls.run.databaseId}): ci-fix round ${round}/${MAX_CI_FIX}, branch fix/main-ci-${formatDay()}`);
    const saved = ctx.state.data;
    ctx.state.data = newStateData('main');
    try {
      const st = ctx.state.data;
      st.phase = 'ci'; // a ci-fix session: what status.mjs shows while main is repaired
      ctx.state.save();
      await beforeSession(ctx, { skipMainCi: true });
      const block = await failedBlockForRun(ctx, cls.run.databaseId);
      await runPhaseSession(ctx, { mode: 'ci-fix', unit: 'main', attempt: round, failedChecks: block });
      prepareTree(); // pushes commits the session left behind
      checkSessionStop(ctx);
      const pr = findMainFixPr(ctx);
      if (pr) {
        // The fix PR is the session's own work: it needs the opus-judge verdict ci-fix-<pr>-<round>.
        requireCiFix(st, ciFixVerdictId(pr.number, round));
        st.ciFixAttempts = round; // the attempts of this PR continue after the session that opened it, so verdict ids never repeat
        ctx.state.save();
        if (pr.isDraft) gh(ctx, ['pr', 'ready', String(pr.number)]);
        await ciAndMerge(ctx, { unit: 'main', pr: pr.number, branch: pr.headRefName, steps: [] });
      } else {
        warn('the ci-fix session did not open a fix/main-ci-* pull request');
      }
    } finally {
      saved.sessions = [...saved.sessions, ...ctx.state.data.sessions];
      ctx.state.data = saved;
      ctx.state.save();
    }
    prepareTree();
    cls = await settledMainCi(ctx);
  }
  if (cls.state === 'red') {
    stopUnit(ctx, { unit: 'main', pr: null, reason: `main CI is still red after ${MAX_CI_FIX} fix rounds`, ownerAction: `Look at the latest ci run on main (${cls.run?.url ?? 'gh run list --branch main'}) and fix it by hand.` });
  }
}

function findMainFixPr(ctx) {
  const list = ghJson(ctx, ['pr', 'list', '--state', 'open', '--limit', '50', '--json', 'number,headRefName,isDraft']);
  return list.filter((p) => p.headRefName.startsWith('fix/main-ci-')).sort((a, b) => b.number - a.number)[0] ?? null;
}

// ---------------------------------------------------------------------------------------------
// Units
// ---------------------------------------------------------------------------------------------

function unitMeta(unit) {
  const kind = unitKind(unit);
  if (kind === 'final') return { unit, kind, file: null, slug: 'final', branch: 'phase1/final', tickets: [] };
  const names = git(['ls-tree', '--name-only', 'main', `${FILES.promptsDir}/`]).stdout.split(/\r?\n/).filter(Boolean).map((p) => path.posix.basename(p));
  const file = promptFileForUnit(unit, names);
  if (!file) throw new DriverExit(1, `No prompt file for unit ${unit} in ${FILES.promptsDir}/ on main (expected ${unit}-<slug>.md).`);
  const md = showFile('main', `${FILES.promptsDir}/${file}`) ?? '';
  const slug = slugFromPromptFile(file);
  return { unit, kind, file, slug, branch: expectedBranch(unit, slug), tickets: parsePromptTickets(md) };
}

const planFile = (unit) => path.join(PATHS.plans, `${unit}.json`);

function loadPlan(meta, { quiet = false } = {}) {
  const f = planFile(meta.unit);
  if (!fs.existsSync(f)) return { plan: null, errors: [`.autopilot/plans/${meta.unit}.json was not written`] };
  let raw;
  try {
    raw = JSON.parse(fs.readFileSync(f, 'utf8'));
  } catch {
    return { plan: null, errors: [`.autopilot/plans/${meta.unit}.json is not valid JSON`] };
  }
  const v = validatePlan(raw, { unit: meta.unit, slug: meta.slug, promptTickets: meta.tickets });
  if (!quiet) for (const w of v.warnings) warn(`plan ${meta.unit}: ${w}`);
  return v.ok ? { plan: raw, errors: [] } : { plan: null, errors: v.errors };
}

/**
 * A session may have split a step (AUTOPILOT.md: "split the step") by editing the plan file: pick that
 * up. A file that is unreadable or invalid, or that names another branch or PR, is ignored.
 */
function reloadPlan(meta, plan) {
  const r = loadPlan(meta, { quiet: true });
  if (!r.plan) {
    if (r.errors.length) warn(`the plan file is not valid after the session (${r.errors.join('; ')}); keeping the plan the driver already holds`);
    return plan;
  }
  if (r.plan.branch !== plan.branch || r.plan.pr !== plan.pr) {
    warn(`the plan file now names ${r.plan.branch} and PR #${r.plan.pr}, not ${plan.branch} and PR #${plan.pr}; keeping the plan the driver already holds`);
    return plan;
  }
  return r.plan;
}

/** A plan is usable when its branch is on origin and its PR is open on that branch. */
function planUsable(ctx, plan) {
  if (!branchOnOrigin(plan.branch)) return { usable: false, why: `branch ${plan.branch} is not on origin` };
  let pr;
  try {
    pr = prView(ctx, plan.pr, 'state,headRefName');
  } catch (e) {
    // Only a PR that does not exist makes the plan unusable; any other gh failure stops the run
    // instead of planning (and opening a second PR) because of a network blip.
    if (!/could not resolve to a pullrequest|no pull request/i.test(e.message)) throw e;
    return { usable: false, why: `PR #${plan.pr} does not exist` };
  }
  if (pr.headRefName !== plan.branch) return { usable: false, why: `PR #${plan.pr} is on ${pr.headRefName}, not ${plan.branch}` };
  if (pr.state === 'MERGED') return { usable: false, merged: true, why: `PR #${plan.pr} is already merged` };
  if (pr.state !== 'OPEN') return { usable: false, why: `PR #${plan.pr} is ${pr.state}` };
  return { usable: true };
}

/**
 * FINAL has no plan session: its single `final` session opens phase1/final and the draft PR itself
 * (AUTOPILOT.md). A usable .autopilot/plans/FINAL.json is reused; otherwise the plan is synthesized
 * here and the PR number is looked up after the session (see refreshFinalPr).
 */
function ensureFinalPlan(ctx, meta) {
  const have = loadPlan(meta);
  if (have.plan) {
    const u = planUsable(ctx, have.plan);
    if (u.usable) return have.plan;
    if (u.merged) {
      stopUnit(ctx, { unit: meta.unit, pr: null, reason: u.why, ownerAction: `The final gate is not on main although PR #${have.plan.pr} merged. Check ${FILES.gate} on main.` });
    }
  }
  return { unit: meta.unit, branch: meta.branch, pr: null, gate: null, steps: [] };
}

/** Find the open phase1/final PR once the session has created it, and persist the plan. */
function refreshFinalPr(ctx, plan) {
  if (plan.pr) return;
  const l = gh(ctx, ['pr', 'list', '--head', plan.branch, '--state', 'open', '--json', 'number']);
  try {
    const n = JSON.parse(l.stdout)[0]?.number;
    if (n) {
      plan.pr = n;
      writeJsonAtomic(planFile(plan.unit), plan);
      ctx.state.data.pr = n;
      ctx.state.save();
    }
  } catch {
    // no PR yet
  }
}

async function ensurePlan(ctx, meta) {
  if (meta.kind === 'final') return ensureFinalPlan(ctx, meta);
  const st = ctx.state.data;
  const key = 'plan';
  let note = null;
  for (let attempt = (st.attempts[key] ?? 0) + 1; attempt <= MAX_ATTEMPTS; attempt++) {
    const have = loadPlan(meta);
    if (have.plan) {
      const u = planUsable(ctx, have.plan);
      if (u.usable) {
        say(`plan for ${meta.unit} exists (${have.plan.steps.length} step(s), branch ${have.plan.branch}, PR #${have.plan.pr})`);
        delete st.attempts[key];
        return have.plan;
      }
      if (u.merged) {
        stopUnit(ctx, { unit: meta.unit, pr: null, reason: u.why, ownerAction: `PROGRESS.md on main does not show ${meta.unit} as Done although its PR merged. Set the row to Done (#${have.plan.pr}) on main through a pull request, or fix PROGRESS.md by hand.` });
      }
      note = `the existing plan is unusable (${u.why}); write a new plan, branch and draft PR`;
    } else if (fs.existsSync(planFile(meta.unit))) {
      note = `the plan file is invalid: ${have.errors.join('; ')}`;
    }
    // The old plan file stays: AUTOPILOT.md tells the plan session to reuse and repair it.
    await beforeSession(ctx);
    st.phase = 'plan';
    // A new plan is about to be written: nothing approved under the old one counts.
    st.approvals = {};
    st.required = {};
    st.shipBase = null;
    st.shipHead = null;
    ctx.state.save();
    // Where the branch stood before the session, so a resumed branch (step commits already on it) is judged only by what this session added.
    const guess = have.plan?.branch ?? meta.branch;
    const base = guess && branchOnOrigin(guess) && fetchBranch(guess).code === 0 ? originHead(guess) : null;
    await runPhaseSession(ctx, { mode: 'plan', unit: meta.unit, attempt, retryNote: note });
    prepareTree(); // pushes commits the session left behind
    checkSessionStop(ctx);
    const after = loadPlan(meta);
    if (after.plan) {
      const u = planUsable(ctx, after.plan);
      if (u.usable) {
        // A plan session changes only the PROGRESS.md row (AUTOPILOT.md, MODE=plan step 8): code or docs on the branch were never reviewed.
        fetchBranch(after.plan.branch);
        const files = base && after.plan.branch === guess ? changedFiles(base, `origin/${after.plan.branch}`) : branchFiles(after.plan.branch);
        const extra = (files ?? ['(git could not list the plan diff)']).filter((f) => f !== FILES.progress);
        if (extra.length) {
          stopUnit(ctx, {
            unit: meta.unit,
            pr: after.plan.pr,
            reason: `the plan session changed files other than ${FILES.progress} on ${after.plan.branch}: ${extra.slice(0, 8).join(', ')}`,
            ownerAction: `Read the plan session's commits on ${after.plan.branch}. Revert those files (restore them from origin/main on the branch, commit, push) unless you want them.`,
          });
        }
        delete st.attempts[key];
        ctx.state.save();
        return after.plan;
      }
      note = `the plan was written but is unusable: ${u.why}`;
    } else {
      note = after.errors.join('; ');
    }
    st.attempts[key] = attempt;
    ctx.state.save();
    say(`plan attempt ${attempt}/${MAX_ATTEMPTS} did not produce a usable plan: ${note}`);
  }
  stopUnit(ctx, { unit: meta.unit, pr: null, reason: `the plan session failed ${MAX_ATTEMPTS} times: ${note}`, ownerAction: `Read the newest ${meta.unit}-plan log in .autopilot/logs/ and fix the cause (prompt file, AUTOPILOT.md, a missing dependency).` });
  return null;
}

function stepStatus(plan, step, st) {
  fetchBranch(plan.branch);
  const committed = hasStepCommit(stepSubjects(plan.branch), step.id);
  const problem = approvalProblem(st, step.id, plan);
  const approved = problem === null;
  let why = null;
  if (!committed && !approved) why = `no commit whose subject starts with "${step.id} " is on origin/${plan.branch}, and no Opus approval for ${step.id} was seen. Implement the step, run the opus-reviewer agent (model opus), commit as "${step.id} ${step.title}" and push.`;
  else if (committed && !approved) why = `the commit "${step.id} ..." is on origin/${plan.branch} but no "VERDICT: APPROVE ${step.id}" from an Opus subagent was seen in the stream (${problem}). Run the opus-reviewer agent (model opus) on it; its final message must end with the exact line VERDICT: APPROVE ${step.id} (or VERDICT: REQUEST_CHANGES ${step.id}).`;
  else if (!committed) why = `${step.id} is approved but no commit whose subject starts with "${step.id} " is on origin/${plan.branch}. Commit it as "${step.id} ${step.title}" and push.`;
  return { done: committed && approved, committed, approved, why };
}

/** Run ticket sessions for one step until it is committed and approved. Returns the plan to continue with (a session may split a step). */
async function ensureStep(ctx, meta, plan, step) {
  const st = ctx.state.data;
  const key = `ticket:${step.id}`;
  let resume = null;
  let note = null;
  for (let attempt = (st.attempts[key] ?? 0) + 1; attempt <= MAX_ATTEMPTS; attempt++) {
    const s0 = stepStatus(plan, step, st);
    if (s0.done) {
      delete st.attempts[key];
      ctx.state.save();
      return plan;
    }
    note = note ?? (attempt > 1 ? s0.why : null);
    await beforeSession(ctx, { branch: plan.branch, resume: Boolean(resume) });
    st.phase = 'ticket';
    ctx.state.save();
    const out = await runPhaseSession(ctx, { mode: 'ticket', unit: meta.unit, step: step.id, pr: plan.pr, branch: plan.branch, attempt, retryNote: note, resumeId: resume });
    settleTree(out);
    checkSessionStop(ctx);
    checkNoAutopilotEdits(ctx, meta.unit, plan);
    resume = out.resumable ? out.sessionId : null;
    plan = reloadPlan(meta, plan);
    if (!plan.steps.some((s) => s.id === step.id)) {
      say(`step ${step.id} was replaced in the plan (split into sub-steps); continuing with the new plan`);
      delete st.attempts[key];
      ctx.state.save();
      return plan;
    }
    const s1 = stepStatus(plan, step, st);
    if (s1.done) {
      say(`step ${step.id} done (committed, approved by ${st.approvals[step.id]?.agent ?? 'an Opus subagent'})`);
      delete st.attempts[key];
      ctx.state.save();
      return plan;
    }
    note = s1.why;
    st.attempts[key] = attempt;
    ctx.state.save();
    say(`step ${step.id} attempt ${attempt}/${MAX_ATTEMPTS} is incomplete: ${s1.why}`);
  }
  stopUnit(ctx, { unit: meta.unit, pr: plan.pr, reason: `step ${step.id} did not complete in ${MAX_ATTEMPTS} attempts: ${note}`, ownerAction: `Read the newest ${meta.unit}-ticket-${step.id} logs in .autopilot/logs/, fix what blocks the step (or finish it by hand on ${plan.branch}), then rerun.` });
  return plan;
}

/**
 * The ship session's diff (everything pushed from the first ship session until the ship completed) may touch only
 * documents, the status logs, knowledge, findings, project skills, the generated API types and the
 * seed. Anything else was not reviewed by any step, so it needs VERDICT: APPROVE ship-<unit> from opus-reviewer.
 */
function noteShipDiff(ctx, unit, plan) {
  const st = ctx.state.data;
  if (!st.shipBase) return;
  fetchBranch(plan.branch);
  const files = changedFiles(st.shipBase, st.shipHead ?? `origin/${plan.branch}`);
  const unsafe = files === null ? ['(git could not list the ship diff)'] : files.filter((f) => !isShipSafePath(f));
  const id = shipVerdictId(unit);
  if (unsafe.length) st.required[id] = { agent: 'opus-reviewer', files: unsafe.slice(0, 8) };
  else delete st.required[id];
  ctx.state.save();
}

/** The ship is done: commits pushed after this point (ci-fix) are not ship commits, so the ship diff ends here. */
function freezeShipDiff(ctx, mode, plan) {
  const st = ctx.state.data;
  if (mode === 'ship' && st.shipBase && !st.shipHead) {
    fetchBranch(plan.branch);
    st.shipHead = originHead(plan.branch);
  }
  ctx.state.save();
}

/** Ship (units) or the final session (FINAL): its outcome is read from GitHub and git, never from the model. */
async function completionState(ctx, meta, plan) {
  const st = ctx.state.data;
  const missing = [];
  if (meta.kind === 'final') refreshFinalPr(ctx, plan);
  if (!plan.pr) return { ok: false, missing: [`the pull request for ${plan.branch} has not been opened yet (open it as a draft, then finish with prepare-pr)`] };
  const pr = prView(ctx, plan.pr, 'isDraft,labels,state'); // a gh failure stops the run; it never costs a session
  fetchBranch(plan.branch);
  if (pr.state !== 'OPEN') missing.push(`PR #${plan.pr} is ${pr.state}`);
  if (pr.isDraft) missing.push('the PR is still a draft: finish with the prepare-pr skill (gh pr ready)');
  if (meta.kind === 'final') {
    if (!fileExistsOnRef(`origin/${plan.branch}`, FILES.gate)) missing.push(`${FILES.gate} is not on origin/${plan.branch}`);
    const p = approvalProblem(st, FINAL_VERDICT_ID, plan);
    if (p) missing.push(`no "VERDICT: APPROVE ${FINAL_VERDICT_ID}" from the opus-judge agent (model opus) was seen (${p}); ask opus-judge for the completeness verdict and end with that exact line`);
  } else {
    const md = progressOnRef(`origin/${plan.branch}`);
    const row = md ? rowForUnit(parseProgress(md), meta.unit) : null;
    if (!row || !isDoneForPr(row.status, plan.pr)) missing.push(`the PROGRESS.md row for ${meta.unit} on ${plan.branch} does not say "Done (#${plan.pr})" (it says "${row?.statusText ?? 'nothing'}")`);
    noteShipDiff(ctx, meta.unit, plan);
    const id = shipVerdictId(meta.unit);
    if (st.required[id]) {
      const p = approvalProblem(st, id, plan);
      if (p) missing.push(`the ship commits change files outside docs, the status logs, knowledge/, findings/, .claude/skills/, the generated API types and the seed (${(st.required[id].files ?? []).join(', ')}), so they need "VERDICT: APPROVE ${id}" from the opus-reviewer agent (model opus) (${p}); run opus-reviewer on the ship diff and end with that exact line`);
    }
  }
  if (!hasLabel(pr.labels, LABEL_E2E)) {
    // The label is harmless and idempotent: add it rather than spend a session on it.
    if (missing.length === 0 && addLabel(ctx, plan.pr, LABEL_E2E)) say(`added the ${LABEL_E2E} label to PR #${plan.pr}`);
    else missing.push(`the ${LABEL_E2E} label is missing`);
  }
  return { ok: missing.length === 0, missing };
}

async function ensureCompletion(ctx, meta, plan) {
  const st = ctx.state.data;
  const mode = meta.kind === 'final' ? 'final' : 'ship';
  const key = mode;
  const verdictId = mode === 'final' ? FINAL_VERDICT_ID : shipVerdictId(meta.unit);
  let resume = null;
  let note = null;
  for (let attempt = (st.attempts[key] ?? 0) + 1; attempt <= MAX_ATTEMPTS; attempt++) {
    const c0 = await completionState(ctx, meta, plan);
    if (c0.ok) {
      delete st.attempts[key];
      freezeShipDiff(ctx, mode, plan);
      return;
    }
    note = note ?? (attempt > 1 ? c0.missing.join('; ') : null);
    // FINAL's first session creates its own branch, so there may be nothing to check out yet.
    const onOrigin = branchOnOrigin(plan.branch);
    await beforeSession(ctx, { branch: onOrigin ? plan.branch : null, resume: Boolean(resume) && onOrigin });
    st.phase = 'ship';
    st.shipHead = null; // a ship that has to run again is not finished
    if (mode === 'ship' && !st.shipBase) {
      fetchBranch(plan.branch);
      st.shipBase = originHead(plan.branch);
    }
    delete st.approvals[verdictId]; // the verdict must come from this attempt, after its changes
    ctx.state.save();
    const out = await runPhaseSession(ctx, { mode, unit: meta.unit, pr: plan.pr, branch: plan.branch, attempt, retryNote: note, resumeId: resume });
    settleTree(out);
    checkSessionStop(ctx);
    checkNoAutopilotEdits(ctx, meta.unit, plan);
    resume = out.resumable ? out.sessionId : null;
    const c1 = await completionState(ctx, meta, plan);
    if (c1.ok) {
      say(`${mode} complete for ${meta.unit}`);
      delete st.attempts[key];
      freezeShipDiff(ctx, mode, plan);
      return;
    }
    note = c1.missing.join('; ');
    st.attempts[key] = attempt;
    ctx.state.save();
    say(`${mode} attempt ${attempt}/${MAX_ATTEMPTS} is incomplete: ${note}`);
  }
  stopUnit(ctx, { unit: meta.unit, pr: plan.pr, reason: `the ${mode} session did not complete in ${MAX_ATTEMPTS} attempts: ${note}`, ownerAction: `Read the newest ${meta.unit}-${mode} logs in .autopilot/logs/ and finish what is missing on ${plan.branch}: ${note}` });
}

// ---------------------------------------------------------------------------------------------
// CI and merge (the driver, never a session)
// ---------------------------------------------------------------------------------------------

async function failedBlockForRun(ctx, runId) {
  const jobs = gh(ctx, ['run', 'view', String(runId), '--json', 'jobs']);
  let checks = [];
  try {
    checks = JSON.parse(jobs.stdout).jobs.filter((j) => j.conclusion === 'failure').map((j) => ({ name: j.name, bucket: 'fail', link: j.url }));
  } catch {
    // names are optional
  }
  const log = gh(ctx, ['run', 'view', String(runId), '--log-failed'], { timeoutMs: 180000 });
  return buildFailedChecksBlock({ checks, logs: [{ runId, text: log.stdout || log.stderr }] });
}

async function failedBlockForChecks(ctx, failed) {
  const logs = [];
  for (const id of failedRunIds(failed).slice(0, 3)) {
    const l = gh(ctx, ['run', 'view', id, '--log-failed'], { timeoutMs: 180000 });
    logs.push({ runId: id, text: l.stdout || l.stderr });
  }
  return buildFailedChecksBlock({ checks: failed.map((c) => ({ name: c.name, bucket: c.bucket, link: c.link })), logs });
}

/**
 * Wait for the check named `ci`: {state: pass|fail, failed: [...]}. Only that check decides (see
 * classifyChecks): a green lint job, a skipped ci or an empty list never passes, and the driver keeps
 * polling (up to 3 hours, or ~10 minutes while no ci check exists at all).
 */
async function waitForChecks(ctx, pr) {
  const t0 = Date.now();
  let lastBeat = t0;
  for (let unseen = 0; ; ) {
    if (Date.now() - t0 > CI_MAX_MS) throw new DriverExit(2, `CI on PR #${pr} did not finish within ${CI_MAX_MS / 3600000} hours.\nFix: look at the checks of the PR on GitHub, then rerun.`);
    const j = gh(ctx, ['pr', 'checks', String(pr), '--json', 'name,bucket,state,link,workflow'], { timeoutMs: 120000 });
    let cls = null;
    try {
      cls = classifyChecks(JSON.parse(j.stdout));
    } catch {
      // No readable check list: a network or API hiccup, or "no checks reported yet". NOT a red CI: never start a ci-fix for it.
    }
    if (!cls || cls.state === 'none') {
      const said = (j.stderr || j.stdout).trim().split('\n')[0].slice(0, 120);
      if (++unseen > ciMissingRetries()) {
        throw new DriverExit(2, `No check named "ci" has passed or failed on PR #${pr} (${hasNoChecks(`${j.stdout}\n${j.stderr}`) ? 'none was reported' : cls ? 'it is missing or skipped' : `could not read the checks: ${said}`}).\nFix: check that .github/workflows/ci.yml runs on pull_request and that its always-running aggregator job is named ci, and check the network and "gh auth status"; then rerun.`);
      }
      say(`no usable "ci" check on PR #${pr} yet${said ? ` (${said})` : ''}; waiting`);
    } else if (cls.state === 'pending') {
      unseen = 0;
      if (Date.now() - lastBeat > 5 * 60 * 1000) {
        lastBeat = Date.now();
        say(`still waiting for CI on PR #${pr} (${Math.round((Date.now() - t0) / 60000)} min)`);
      }
    } else {
      return { state: cls.state, failed: cls.failed };
    }
    await sleep(ciPollMs());
  }
}

/**
 * The last look before `gh pr merge`, after CI said pass. Returns 'ok', 'moved' (the head changed: wait
 * for CI again) or 'merged'; anything wrong stops the unit. Checked here, not earlier, because hours
 * may have passed and a session or the owner may have acted since: stop.json, the autopilot:stopped
 * label, a draft PR, edits to scripts/autopilot/, every needed Opus verdict, and the Done (#n) row.
 */
function preMergeGate(ctx, { unit, pr, branch, steps, headOid }) {
  checkSessionStop(ctx);
  checkNoAutopilotEdits(ctx, unit, { branch, pr });
  const v = prView(ctx, pr, 'state,isDraft,labels,headRefOid');
  if (v.state === 'MERGED') return 'merged';
  if (v.state !== 'OPEN') stopUnit(ctx, { unit, pr, reason: `PR #${pr} is ${v.state}`, ownerAction: `Reopen PR #${pr} or discard the unit.` });
  if (hasLabel(v.labels, LABEL_STOPPED)) stopUnit(ctx, { unit, pr, reason: `PR #${pr} is labelled ${LABEL_STOPPED}`, ownerAction: `Read why (the PR, .autopilot/stop.json, PROGRESS.md) and fix the cause; the label was put there by a session or by you.` });
  if (v.isDraft) stopUnit(ctx, { unit, pr, reason: `PR #${pr} is a draft again`, ownerAction: `Mark it ready: gh pr ready ${pr}` });
  if (v.headRefOid !== headOid) return 'moved';
  const missing = missingApprovals(ctx, neededApprovals(ctx, { unit, steps }), { branch, pr });
  if (missing.length) {
    stopUnit(ctx, {
      unit,
      pr,
      reason: `CI is green but there is no valid Opus APPROVE for: ${missing.join(', ')}`,
      ownerAction: `Have the diff reviewed (opus-reviewer for steps and ship-<unit>; opus-judge for FINAL and ci-fix-<pr>-<n>; each ends with VERDICT: APPROVE <id>), or merge PR #${pr} by hand after reading it.`,
    });
  }
  const uncovered = uncoveredStepCommits(ctx, { branch, pr });
  if (uncovered.length) {
    stopUnit(ctx, {
      unit,
      pr,
      reason: `${branch} holds commit(s) for ${uncovered.join(', ')} that no valid Opus APPROVE covers (a step outside the plan, or one that was never reviewed)`,
      ownerAction: `Read those commits on ${branch}. Have them reviewed (opus-reviewer ends with VERDICT: APPROVE <step id>), drop them, or merge PR #${pr} by hand after reading it.`,
    });
  }
  const kind = unitKind(unit);
  if (kind === 'build' || kind === 'setup') {
    const md = progressOnRef(`origin/${branch}`);
    const row = md ? rowForUnit(parseProgress(md), unit) : null;
    if (!row || !isDoneForPr(row.status, pr)) {
      stopUnit(ctx, { unit, pr, reason: `the PROGRESS.md row for ${unit} on ${branch} no longer says "Done (#${pr})" (it says "${row?.statusText ?? 'nothing'}")`, ownerAction: `Check what changed the row on ${branch} and restore "Done (#${pr})", then rerun.` });
    }
  } else if (kind === 'final' && !fileExistsOnRef(`origin/${branch}`, FILES.gate)) {
    stopUnit(ctx, { unit, pr, reason: `${FILES.gate} is not on origin/${branch}`, ownerAction: `Restore the gate document on ${branch}, then rerun.` });
  }
  return 'ok';
}

async function ciAndMerge(ctx, { unit, pr, branch, steps }) {
  const st = ctx.state.data;
  st.phase = 'ci';
  ctx.state.save();
  for (;;) {
    prepareTree(); // pushes leftovers (moves the head before we read it), leaves main checked out
    const head = prView(ctx, pr, 'headRefOid,state,isDraft');
    if (head.state === 'MERGED') return afterMerge(ctx, { unit, pr, branch, mergedOid: head.headRefOid });
    if (head.state !== 'OPEN') stopUnit(ctx, { unit, pr, reason: `PR #${pr} is ${head.state}`, ownerAction: `Reopen PR #${pr} or discard the unit.` });
    if (head.isDraft) stopUnit(ctx, { unit, pr, reason: `PR #${pr} is still a draft`, ownerAction: `Mark it ready: gh pr ready ${pr}` });
    say(`waiting for the ci check on PR #${pr} (head ${head.headRefOid.slice(0, 8)})`);
    const res = await waitForChecks(ctx, pr);
    const after = prView(ctx, pr, 'headRefOid').headRefOid;
    if (after !== head.headRefOid) {
      say('the PR head moved while waiting for CI; waiting again');
      continue;
    }
    if (res.state === 'pass') {
      const gate = preMergeGate(ctx, { unit, pr, branch, steps, headOid: head.headRefOid });
      if (gate === 'merged') return afterMerge(ctx, { unit, pr, branch, mergedOid: head.headRefOid });
      if (gate === 'moved') {
        say('the PR head moved while the driver checked it; waiting for CI again');
        continue;
      }
      say(`CI is green on PR #${pr}; every needed Opus verdict is in; merging (squash)`);
      let merged = false;
      let why = '';
      for (let tries = 1; tries <= 3 && !merged; tries++) {
        const m = gh(ctx, ['pr', 'merge', String(pr), '--squash', '--delete-branch', '--match-head-commit', head.headRefOid], { timeoutMs: 180000 });
        merged = prView(ctx, pr, 'state,mergedAt').state === 'MERGED'; // the outcome is read from GitHub, not from gh's exit code
        why = (m.stderr || m.stdout).trim().slice(0, 300);
        if (!merged && !isTransientGhError(why)) break;
        if (!merged && tries < 3) {
          say(`gh pr merge failed with what looks like a network error; retrying in 20 s (${why.slice(0, 80)})`);
          await sleep(20000);
        }
      }
      if (!merged) {
        stopUnit(ctx, { unit, pr, reason: `gh pr merge did not merge PR #${pr}: ${why}`, ownerAction: `Look at PR #${pr} (merge conflicts, branch protection) and merge it by hand, or fix the cause.` });
      }
      return afterMerge(ctx, { unit, pr, branch, mergedOid: head.headRefOid });
    }
    // CI is red.
    if (st.ciFixAttempts >= MAX_CI_FIX) {
      stopUnit(ctx, { unit, pr, reason: `CI is still red on PR #${pr} after ${MAX_CI_FIX} ci-fix sessions`, ownerAction: `Fix the failing checks on ${branch} by hand: ${res.failed.map((c) => c.name).join(', ')}` });
    }
    st.ciFixAttempts += 1;
    const attempt = st.ciFixAttempts;
    const fixId = ciFixVerdictId(pr, attempt);
    delete st.approvals[fixId]; // the verdict must come from this attempt
    ctx.state.save();
    say(`CI failed on PR #${pr} (${res.failed.map((c) => c.name).join(', ') || 'unknown check'}); ci-fix ${attempt}/${MAX_CI_FIX}`);
    const block = await failedBlockForChecks(ctx, res.failed);
    await beforeSession(ctx, { branch, skipMainCi: true });
    fetchBranch(branch);
    const before = originHead(branch);
    await runPhaseSession(ctx, { mode: 'ci-fix', unit, pr, branch, attempt, failedChecks: block });
    prepareTree(); // pushes commits the session left behind
    checkSessionStop(ctx);
    fetchBranch(branch);
    if (originHead(branch) !== before) requireCiFix(st, fixId); // new commits after the last review need opus-judge's ci-fix verdict
    checkNoAutopilotEdits(ctx, unit, { branch, pr });
    st.phase = 'ci';
    ctx.state.save();
  }
}

async function afterMerge(ctx, { unit, pr, branch, mergedOid }) {
  const st = ctx.state.data;
  prepareTree();
  if (!deleteLocalBranch(branch, mergedOid)) warn(`kept the local branch ${branch}: it holds commits that were not part of the merged PR (git log origin/main..${branch})`);
  if (unit !== 'main') {
    const kind = unitKind(unit);
    if (kind === 'final') {
      if (!fileExistsOnRef('main', FILES.gate)) {
        stopUnit(ctx, { unit, pr: null, reason: `PR #${pr} merged but ${FILES.gate} is not on main`, ownerAction: 'Add the gate document to main through a pull request.' });
      }
    } else {
      const row = rowForUnit(parseProgress(showFile('main', FILES.progress) ?? ''), unit);
      if (!row || row.status.kind !== 'done') {
        stopUnit(ctx, { unit, pr: null, reason: `PR #${pr} merged but PROGRESS.md on main says "${row?.statusText ?? 'nothing'}" for ${unit}`, ownerAction: `Set the ${unit} row to Done (#${pr}) on main through a pull request.` });
      }
    }
  }
  st.phase = 'merged';
  st.stopped = null;
  ctx.state.save();
  ctx.merged.push(unit);
  say(`MERGED: ${unit} (PR #${pr}) is on main`);
}

async function runUnit(ctx, unit) {
  const meta = unitMeta(unit);
  say(`### unit ${unit}${meta.file ? ` (${meta.file})` : ''}: branch ${meta.branch}`);
  const st = ctx.state;
  if (st.data.unit !== unit || st.data.phase === 'merged') st.startUnit(unit);
  else {
    // The owner cleared a stop: the unit gets a fresh round of attempts instead of stopping again at once.
    if (st.data.stopped || st.data.phase === 'stopped') {
      st.data.attempts = {};
      st.data.ciFixAttempts = 0;
    }
    st.data.stopped = null;
    st.data.pause = null;
    st.save();
  }
  let plan = await ensurePlan(ctx, meta);
  st.data.branch = plan.branch;
  st.data.pr = plan.pr;
  st.save();
  const done = new Set();
  for (let step = plan.steps.find((s) => !done.has(s.id)); step; step = plan.steps.find((s) => !done.has(s.id))) {
    plan = await ensureStep(ctx, meta, plan, step);
    done.add(step.id);
  }
  await ensureCompletion(ctx, meta, plan);
  await ciAndMerge(ctx, { unit, pr: plan.pr, branch: plan.branch, steps: plan.steps });
}

// ---------------------------------------------------------------------------------------------
// Main loop, dry run, canary
// ---------------------------------------------------------------------------------------------

function selectUnit(ctx) {
  const md = showFile('main', FILES.progress);
  if (!md) throw new DriverExit(1, `${FILES.progress} is not on main.`);
  const rows = parseProgress(md);
  if (ctx.args.unit) {
    // --unit may repeat a Done unit, but never runs over a Stopped row.
    const row = rowForUnit(rows, ctx.args.unit);
    if (row?.status.kind === 'stopped') return { action: 'stopped', unit: row.id, reason: row.status.detail || 'no reason recorded' };
    return { action: 'run', unit: ctx.args.unit };
  }
  return selectNextUnit(rows, { finalGateExists: fileExistsOnRef('main', FILES.gate) });
}

async function mainLoop(ctx) {
  for (;;) {
    await beforeSession(ctx);
    const sel = selectUnit(ctx);
    if (sel.action === 'error') throw new DriverExit(1, sel.reason);
    if (sel.action === 'stopped') {
      throw new DriverExit(2, `PROGRESS.md says ${sel.unit} is Stopped (${sel.reason}).\nOwner action: fix the cause, set the row back to Not started or In progress on main, and rerun.`);
    }
    if (sel.action === 'complete') {
      say('Phase 1 complete');
      return 0;
    }
    await runUnit(ctx, sel.unit);
    if (ctx.args.once || ctx.args.unit) return 0;
  }
}

function nextSessionPreview(ctx, sel) {
  const unit = sel.unit;
  const kind = unitKind(unit);
  const plan = readJson(planFile(unit), null);
  let mode = kind === 'final' ? 'final' : 'plan';
  let step;
  if (plan && Array.isArray(plan.steps)) {
    const next = plan.steps.find((s) => !ctx.state.data.approvals?.[s.id]);
    mode = next ? 'ticket' : kind === 'final' ? 'final' : 'ship';
    step = next?.id;
  }
  const model = modelForMode(mode);
  const permission = permissionFor(ctx);
  const line = buildTaskLine({ mode, unit, step, pr: plan?.pr, attempt: 1 });
  const args = buildClaudeArgs({ model, permission, name: sessionName({ unit, mode, step }), appendPromptFile: ctx.appendPrompt });
  const env = buildChildEnv({}, { mode });
  return { mode, step, model, line, command: formatCommand(ctx.claudeExe ?? 'claude.exe', args), env: `CLAUDE_CODE_DISABLE_AUTO_MEMORY=${env.CLAUDE_CODE_DISABLE_AUTO_MEMORY} CLAUDE_CODE_MAX_TURNS=${env.CLAUDE_CODE_MAX_TURNS} MSYS_NO_PATHCONV=${env.MSYS_NO_PATHCONV} (ANTHROPIC_API_KEY, ANTHROPIC_AUTH_TOKEN and inherited CLAUDE_CODE_* markers are removed)` };
}

async function dryRun(ctx) {
  console.log('Hermi autopilot, dry run: nothing is changed.\n');
  ctx.state.load();
  const results = environmentChecks(ctx, { dry: true });
  results.push(...freePorts({ dry: true }));
  const tree = prepareTree({ dry: true });
  for (const p of tree.problems) results.push({ id: 'tree', status: 'fail', msg: p, exit: 2, fix: p });
  for (const a of tree.actions) results.push({ id: 'tree', status: 'info', msg: `would run: ${a}` });
  const ci = mainCiState(ctx);
  results.push(
    ci.state === 'red'
      ? { id: 'main-ci', status: 'warn', msg: `the latest ci run on main is RED: a ci-fix session would run before anything else (${ci.run?.url ?? ''})` }
      : { id: 'main-ci', status: 'ok', msg: `main CI: ${ci.state}${ci.note ? ` (${ci.note})` : ''}` },
  );
  console.log('Checks:');
  printResults(results);

  console.log('\nNext unit:');
  let sel;
  try {
    sel = selectUnit(ctx);
  } catch (e) {
    console.log(`  cannot read PROGRESS.md on main: ${e.message}`);
  }
  if (sel?.action === 'run') {
    const kind = unitKind(sel.unit);
    let meta = null;
    try {
      meta = unitMeta(sel.unit);
    } catch (e) {
      console.log(`  ${e.message}`);
    }
    const rows = parseProgress(showFile('main', FILES.progress) ?? '');
    const c = progressCounts(rows);
    console.log(`  ${sel.unit}${kind === 'final' ? ' (FINAL)' : ''} (${c.done} of ${c.total} prompts Done): ${meta?.file ?? ''}`);
    if (meta?.branch) console.log(`  branch: ${meta.branch}${meta.tickets.length ? `, ${meta.tickets.length} ticket(s): ${meta.tickets.map((t) => t.ticket).join(', ')}` : ''}`);
    const p = nextSessionPreview(ctx, sel);
    console.log(`\nNext session: ${p.mode}${p.step ? ` ${p.step}` : ''} on ${p.model}`);
    console.log(`  stdin:   ${p.line}`);
    console.log(`  command: ${p.command}`);
    console.log(`  env:     ${p.env}`);
  } else if (sel?.action === 'stopped') {
    console.log(`  PROGRESS.md says ${sel.unit} is Stopped (${sel.reason}): a real run would halt (exit 2).`);
  } else if (sel?.action === 'complete') {
    console.log('  Phase 1 complete');
  } else if (sel?.action === 'error') {
    console.log(`  ${sel.reason}`);
  }
  const fails = results.filter((x) => x.status === 'fail');
  console.log(`\n${fails.length ? `${fails.length} check(s) would stop a real run.` : 'All checks pass: a real run would start.'}`);
  return fails.length ? fails[0].exit ?? 1 : 0;
}

async function canary(ctx) {
  console.log('Hermi autopilot canary: four short sessions with the real flags and settings.\n');
  ctx.state.load();
  await beforeSession(ctx, { skipMainCi: true });
  if (!fileExistsOnRef('HEAD', FILES.appendPrompt)) {
    ctx.appendPrompt = null;
    warn(`${FILES.appendPrompt} is missing: the canary runs without it`);
  }
  const cases = [
    { id: 'a', title: `opus-judge runs on Opus, sonnet-researcher on Sonnet, ${permissionFor(ctx)} mode is on`, check: (t) => evalSubagentModels(t, permissionFor(ctx)) },
    { id: 'b', title: 'everyday commands run with zero permission denials', check: evalCommands },
    { id: 'c', title: 'cat .env.canary (a decoy name) is blocked by the bash-guard hook', check: evalEnvRefused },
    { id: 'd', title: 'a general-purpose agent on Opus is blocked by the agent-guard hook', check: evalAgentGuard },
  ];
  let failed = 0;
  for (const c of cases) {
    const out = await spawnClaude(ctx, { mode: c.id, unit: 'canary', model: SONNET_MODEL, stdinText: `${CANARY_PROMPTS[c.id]}\n`, hookEvents: true, maxTurns: 20, noState: true, name: `hermi-canary-${c.id}` });
    const r = c.check(out.tracker);
    if (!r.pass) failed++;
    console.log(`\n${r.pass ? 'PASS' : 'FAIL'}  canary ${c.id}: ${c.title}`);
    for (const d of r.details) console.log(`      ${d}`);
    console.log(`      log: ${path.relative(ROOT, out.logFile)}`);
  }
  console.log(`\n${failed ? `${failed} canary check(s) FAILED` : 'All canaries PASS'}.`);
  return failed ? 1 : 0;
}

// ---------------------------------------------------------------------------------------------
// Entry
// ---------------------------------------------------------------------------------------------

const MEANING = { 0: 'done', 1: 'error', 2: 'stopped, owner action needed', 3: 'permission denials', 4: 'extra usage is on', 5: 'authentication', 130: 'interrupted' };

function installSignalHandlers(ctx) {
  const bye = (sig) => {
    console.log(`\n${sig}: stopping the session and releasing the lock`);
    if (ctx.child?.pid) killTree(ctx.child.pid);
    releaseLock();
    process.exit(130);
  };
  for (const s of ['SIGINT', 'SIGTERM', 'SIGHUP', 'SIGBREAK']) process.on(s, () => bye(s));
  process.on('exit', () => releaseLock());
}

async function main() {
  let args;
  try {
    args = parseArgs(process.argv.slice(2));
  } catch (e) {
    console.error(`${e.message}\n\n${USAGE}`);
    process.exit(1);
  }
  if (args.help) {
    console.log(USAGE);
    return;
  }
  const ctx = createCtx(args);
  installSignalHandlers(ctx);
  let code = 0;
  try {
    if (args.dryRun) code = await dryRun(ctx);
    else if (args.canary) code = await canary(ctx);
    else {
      ctx.state.load();
      if (args.permissionProfile === 'dontask') warn('running with the dontAsk profile (scripts/autopilot/settings-dontask.json): no auto-mode classifier, only its allow list');
      code = await mainLoop(ctx);
    }
  } catch (e) {
    if (e instanceof DriverExit) {
      console.error(`\n${e.message}`);
      code = e.code;
    } else {
      console.error(e?.stack ?? e);
      code = 1;
    }
  } finally {
    releaseLock();
  }
  const mins = Math.round((Date.now() - ctx.startedAt) / 60000);
  console.log(`\nautopilot: exit ${code} (${MEANING[code] ?? 'error'}) | merged this run: ${ctx.merged.join(', ') || 'none'} | ${mins} min | notional cost $${ctx.cost.toFixed(2)}`);
  process.exit(code);
}

if (process.argv[1] && pathToFileURL(path.resolve(process.argv[1])).href === import.meta.url) {
  main();
}
