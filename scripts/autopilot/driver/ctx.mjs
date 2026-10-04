// Driver context: paths, console output, the exit type, state.json and the PID lock.

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { APPEND_PROMPT_FILE, HOOK_FILES, SETTINGS_DONTASK_FILE, SETTINGS_FILE } from '../lib/cmd.mjs';
import { findExecutable, killTree, pidAlive, preArgs, processCommandLine, processName, readJson, resolveClaude, resolveGh, writeJsonAtomic } from './sys.mjs';

export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..', '..');
export const AP_DIR = path.join(ROOT, '.autopilot');
export const PATHS = {
  state: path.join(AP_DIR, 'state.json'),
  lock: path.join(AP_DIR, 'lock'),
  stop: path.join(AP_DIR, 'stop.json'),
  plans: path.join(AP_DIR, 'plans'),
  logs: path.join(AP_DIR, 'logs'),
};
export const FILES = {
  progress: 'app-buildout/prompts/PROGRESS.md',
  promptsDir: 'app-buildout/prompts',
  appendPrompt: APPEND_PROMPT_FILE,
  settings: SETTINGS_FILE,
  settingsDontask: SETTINGS_DONTASK_FILE,
  hooks: HOOK_FILES,
  agents: ['opus-reviewer', 'opus-judge', 'sonnet-coder', 'sonnet-researcher'].map((a) => `.claude/agents/${a}.md`),
  gate: 'docs/gates/phase-1-complete.md',
  handoffDir: '.claude/handoff',
};

// Exit codes: 0 done, 1 other error, 2 stopped (owner action), 3 denials, 4 overage, 5 auth, 130 Ctrl+C.
export class DriverExit extends Error {
  constructor(code, message, extra = {}) {
    super(message);
    this.code = code;
    Object.assign(this, extra);
  }
}

const stamp = () => new Date().toTimeString().slice(0, 8);
export const say = (msg) => console.log(`${stamp()} ${msg}`);
export const warn = (msg) => console.log(`${stamp()} WARN ${msg}`);

const freshState = (unit) => ({
  unit,
  phase: 'plan',
  branch: null,
  pr: null,
  approvals: {}, // verdict id -> {model, agent, at, source, branch, pr}
  required: {}, // verdict ids the merge needs beyond the plan's steps: ship-<unit>, ci-fix-<pr>-<n>
  shipBase: null, // origin/<branch> before the first ship session
  shipHead: null, // origin/<branch> when the ship session completed: the ship diff is shipBase..shipHead (later ci-fix commits are not ship commits)
  ciFixAttempts: 0,
  sessions: [],
  stopped: null,
  attempts: {},
  pause: null,
  updatedAt: null,
});

export const newStateData = freshState;

/** .autopilot/state.json. Driver-owned; skills and `status.mjs` only read it. */
export class State {
  constructor() {
    this.data = freshState(null);
  }

  load() {
    this.data = { ...freshState(null), ...(readJson(PATHS.state, {}) ?? {}) };
    return this.data;
  }

  save() {
    this.data.updatedAt = new Date().toISOString();
    if (this.data.sessions.length > 300) this.data.sessions = this.data.sessions.slice(-300);
    writeJsonAtomic(PATHS.state, this.data);
  }

  /** Begin a unit: everything starts from scratch. */
  startUnit(unit) {
    this.data = freshState(unit);
    this.save();
  }
}

export function createCtx(args) {
  const ghExe = resolveGh();
  const ghOnPath = findExecutable(['gh']) !== null;
  return {
    args,
    dry: args.dryRun === true,
    state: new State(),
    claudeExe: resolveClaude(),
    claudePre: preArgs('AUTOPILOT_CLAUDE_PREARGS'),
    ghPre: preArgs('AUTOPILOT_GH_PREARGS'),
    ghExe,
    extraPathDirs: ghExe && !ghOnPath ? [path.dirname(ghExe)] : [],
    appendPrompt: FILES.appendPrompt,
    ghReady: false,
    warned: new Set(),
    cost: 0,
    child: null,
    merged: [],
    startedAt: Date.now(),
  };
}

// --- PID lock -------------------------------------------------------------------------------

export const readLock = () => readJson(PATHS.lock, null);

const holderAlive = (cur) => pidAlive(cur.pid) && /node/i.test(processName(cur.pid) ?? 'node');

/**
 * The only process a takeover may kill: a claude.exe that THIS driver started (its command line carries
 * --name hermi-<unit>-<mode>). The pid in a dead driver's lock may since belong to anything else.
 */
export const isOurClaude = (name, commandLine) => /^claude/i.test(String(name ?? '')) && /--name hermi-/.test(String(commandLine ?? ''));

/** Take the lock, or take over a stale one (killing the orphaned claude child it recorded). */
export function acquireLock() {
  fs.mkdirSync(AP_DIR, { recursive: true });
  const mine = { pid: process.pid, startedAt: new Date().toISOString(), childPid: null };
  let tookOver = false;
  for (let i = 0; i < 3; i++) {
    try {
      fs.writeFileSync(PATHS.lock, JSON.stringify(mine), { flag: 'wx' });
      return { ok: true, tookOver };
    } catch (e) {
      if (e.code !== 'EEXIST') throw e;
    }
    const cur = readLock();
    if (cur?.pid === process.pid) return { ok: true, tookOver };
    if (cur && holderAlive(cur)) return { ok: false, holder: cur };
    if (cur?.childPid && isOurClaude(processName(cur.childPid), processCommandLine(cur.childPid))) {
      killTree(cur.childPid);
      say(`killed an orphaned claude process (pid ${cur.childPid}) left by a dead driver`);
    }
    fs.rmSync(PATHS.lock, { force: true });
    tookOver = true;
  }
  return { ok: false, holder: null };
}

export function updateLock(patch) {
  const cur = readLock();
  if (cur?.pid === process.pid) writeJsonAtomic(PATHS.lock, { ...cur, ...patch });
}

export function releaseLock() {
  const cur = readLock();
  if (cur?.pid === process.pid) fs.rmSync(PATHS.lock, { force: true });
}

export function writeStopFile({ unit, reason, ownerAction }) {
  writeJsonAtomic(PATHS.stop, { unit, reason, ownerAction, at: new Date().toISOString() });
}

/**
 * .autopilot/stop.json, or null when there is none. A file that exists but cannot be read as a JSON
 * object still counts as a stop (a session may have died mid-write): the owner decides.
 */
export function readStopFile() {
  if (!fs.existsSync(PATHS.stop)) return null;
  const s = readJson(PATHS.stop, null);
  if (s && typeof s === 'object' && !Array.isArray(s)) return { ...s, unit: s.unit ?? '?', reason: String(s.reason ?? 'no reason recorded'), ownerAction: String(s.ownerAction ?? 'Read .autopilot/stop.json.') };
  return { unit: '?', reason: '.autopilot/stop.json exists but is not valid JSON', ownerAction: 'Open .autopilot/stop.json, do what it asks (or delete it if it is junk).' };
}
