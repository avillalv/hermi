// git and gh wrappers, plus the working-tree preparation the driver does before every session.

import fs from 'node:fs';
import path from 'node:path';
import { formatStamp } from '../lib/task.mjs';
import { LABEL_STOPPED } from '../lib/ci.mjs';
import { DriverExit, FILES, ROOT, say } from './ctx.mjs';
import { run, sleepSync } from './sys.mjs';

export const git = (args, o = {}) => run('git', args, { cwd: ROOT, ...o });

export function ghEnv(ctx) {
  const env = { ...process.env, GH_PROMPT_DISABLED: '1', GH_NO_UPDATE_NOTIFIER: '1', NO_COLOR: '1' };
  const key = Object.keys(env).find((k) => k.toLowerCase() === 'path') ?? 'PATH';
  if (ctx.extraPathDirs.length) env[key] = [...ctx.extraPathDirs, env[key]].join(path.delimiter);
  return env;
}

/** Run gh. Never throws; check .code. */
export function gh(ctx, args, o = {}) {
  if (!ctx.ghExe) return { code: -1, stdout: '', stderr: 'gh is not installed', error: null };
  return run(ctx.ghExe, [...(ctx.ghPre ?? []), ...args], { cwd: ROOT, env: ghEnv(ctx), ...o });
}

/** Network and API hiccups, which are worth a retry; anything else is a real answer. */
export const isTransientGhError = (text) => /timed? ?out|timeout|connect(?:ion|ing)|network|EOF|\b50[0-4]\b|rate limit|temporar|could not resolve host|no such host|dial tcp|TLS|try again/i.test(String(text ?? ''));

/** gh with JSON output. Retries transient errors (15 s, 45 s, 90 s) before failing the run. */
export function ghJson(ctx, args) {
  const waits = [15000, 45000, 90000];
  for (let i = 0; ; i++) {
    const r = gh(ctx, args);
    if (r.code === 0) {
      try {
        return JSON.parse(r.stdout);
      } catch {
        throw new DriverExit(1, `gh ${args.join(' ')} returned something that is not JSON`);
      }
    }
    const text = (r.stderr || r.stdout).trim();
    if (i >= waits.length || !isTransientGhError(text)) throw new DriverExit(1, `gh ${args.join(' ')} failed: ${text}`);
    say(`gh ${args.slice(0, 2).join(' ')} failed (${text.split('\n')[0].slice(0, 100)}); retrying in ${waits[i] / 1000} s`);
    sleepSync(waits[i]);
  }
}

// --- reading refs ---------------------------------------------------------------------------

export function currentBranch() {
  const r = git(['rev-parse', '--abbrev-ref', 'HEAD']);
  return r.code === 0 ? r.stdout.trim() : null;
}

export const fetchOrigin = () => git(['fetch', 'origin', '--prune'], { timeoutMs: 300000 });
export const fetchBranch = (branch) => git(['fetch', 'origin', branch], { timeoutMs: 300000 });

/** Is the branch on origin? An ls-remote that fails (network, auth) stops the run: "no" would start a second plan. */
export function branchOnOrigin(branch) {
  const r = git(['ls-remote', '--heads', 'origin', branch], { timeoutMs: 120000 });
  if (r.code !== 0) throw new DriverExit(1, `git ls-remote origin ${branch} failed: ${(r.stderr || r.stdout).trim()}\nFix: check the network and "gh auth status", then rerun.`);
  return r.stdout.trim() !== '';
}

/** The commit origin/<branch> points to (call fetchBranch first), or null. */
export function originHead(branch) {
  const r = git(['rev-parse', '--verify', '--quiet', `origin/${branch}`]);
  return r.code === 0 ? r.stdout.trim() : null;
}

/** Files that differ between two commits or refs (fetch first); null when git cannot say. */
export function changedFiles(from, to) {
  const r = git(['diff', '--name-only', from, to]);
  return r.code === 0 ? r.stdout.split(/\r?\n/).filter(Boolean) : null;
}

/** Subjects of the commits a branch holds beyond origin/main (call fetchBranch first). */
export function stepSubjects(branch) {
  const r = git(['log', `origin/main..origin/${branch}`, '--format=%s']);
  return r.code === 0 ? r.stdout.split(/\r?\n/).filter(Boolean) : [];
}

export const showFile = (ref, file) => {
  const r = git(['show', `${ref}:${file}`]);
  return r.code === 0 ? r.stdout : null;
};

export const fileExistsOnRef = (ref, file) => git(['cat-file', '-e', `${ref}:${file}`]).code === 0;

/** Files a branch changed relative to main (call fetchBranch first), optionally limited to pathspecs. Throws when git cannot look: never "no changes" by mistake. */
export function branchFiles(branch, pathspecs = []) {
  const r = git(['diff', '--name-only', `origin/main...origin/${branch}`, ...(pathspecs.length ? ['--', ...pathspecs] : [])]);
  if (r.code !== 0) throw new DriverExit(1, `git diff origin/main...origin/${branch} failed: ${(r.stderr || r.stdout).trim()}`);
  return r.stdout.split(/\r?\n/).filter(Boolean);
}

/** Owner-controlled files (scripts/autopilot/, the agent definitions, the Claude settings, the MCP config) that a branch changed relative to main (sessions must not). */
export const autopilotEdits = (branch) => branchFiles(branch, ['scripts/autopilot', '.claude/agents', '.claude/settings.json', '.mcp.json']);

// --- working tree ---------------------------------------------------------------------------

const OPS = [
  ['rebase-merge', ['rebase', '--abort']],
  ['rebase-apply', ['rebase', '--abort']],
  ['MERGE_HEAD', ['merge', '--abort']],
  ['CHERRY_PICK_HEAD', ['cherry-pick', '--abort']],
  ['REVERT_HEAD', ['revert', '--abort']],
];

function opsInProgress() {
  const dir = path.resolve(ROOT, git(['rev-parse', '--git-dir']).stdout.trim() || '.git');
  return OPS.filter(([name]) => fs.existsSync(path.join(dir, name)));
}

/**
 * Killing a session tree can interrupt a git command it was running and leave lock files behind,
 * which would break every later git call. Call only when no session is running.
 */
export function clearStaleGitLocks() {
  const r = git(['rev-parse', '--git-dir']);
  if (r.code !== 0) return [];
  const dir = path.resolve(ROOT, r.stdout.trim());
  const removed = [];
  for (const name of ['index.lock', 'HEAD.lock', 'config.lock', 'shallow.lock', 'packed-refs.lock']) {
    const p = path.join(dir, name);
    if (fs.existsSync(p)) {
      fs.rmSync(p, { force: true });
      removed.push(name);
    }
  }
  return removed;
}

const hasUpstream = () => git(['rev-parse', '--abbrev-ref', '@{u}']).code === 0;

function unpushedCount() {
  const base = hasUpstream() ? '@{u}' : 'origin/main';
  const r = git(['rev-list', '--count', `${base}..HEAD`]);
  return r.code === 0 ? Number(r.stdout.trim()) : 0;
}

const isUnitBranch = (b) => /^(phase1|spec|fix)\//.test(b ?? '');

function pushCurrent(branch) {
  const r = git(['push', '-u', 'origin', 'HEAD'], { timeoutMs: 300000 });
  if (r.code !== 0) throw new DriverExit(1, `could not push ${branch}: ${(r.stderr || r.stdout).trim()}\nFix: resolve the push error by hand (git push -u origin ${branch}), then rerun.`);
}

/**
 * Push the current unit branch's unpushed commits and touch nothing else: no stash, no checkout. Used
 * after a session the watchdog killed, because the next attempt RESUMES it and its uncommitted work must
 * still be in the tree.
 */
export function pushLeftovers() {
  const branch = currentBranch();
  if (isUnitBranch(branch) && (unpushedCount() > 0 || !hasUpstream())) pushCurrent(branch);
}

/**
 * Leave the tree on an up-to-date main: abort half-finished git operations, push a unit branch's
 * leftover commits, stash local changes (never discards), check out main and fast-forward it.
 * With dry: only describe. Returns {actions: string[], problems: string[]}.
 */
export function prepareTree({ dry = false } = {}) {
  const actions = [];
  const problems = [];
  const act = (msg, fn) => {
    actions.push(msg);
    if (!dry) fn();
  };
  for (const [name, args] of opsInProgress()) act(`git ${args.join(' ')} (${name} was in progress)`, () => git(args));

  const branch = currentBranch();
  if (branch && branch !== 'main') {
    const ahead = unpushedCount();
    if (isUnitBranch(branch)) {
      if (ahead > 0 || !hasUpstream()) {
        act(`push ${branch} (${ahead} commit(s) not on origin)`, () => pushCurrent(branch));
      }
    } else if (ahead > 0) {
      problems.push(`branch ${branch} has ${ahead} commit(s) that are not pushed. Fix: git push (or merge or delete the branch) before the driver leaves it.`);
    }
  }
  if (git(['status', '--porcelain']).stdout.trim() !== '') {
    const msg = `autopilot-${formatStamp()}`;
    act(`git stash push -u -m ${msg}`, () => {
      const r = git(['stash', 'push', '-u', '-m', msg]);
      if (r.code !== 0) throw new DriverExit(1, `git stash failed: ${(r.stderr || r.stdout).trim()}`);
      say(`working tree was dirty: stashed it as "${msg}" (git stash list shows it; nothing was discarded)`);
    });
  }
  if (problems.length && !dry) throw new DriverExit(2, problems.join('\n'));
  if (branch !== 'main') {
    act('git checkout main', () => {
      const r = git(['checkout', 'main']);
      if (r.code !== 0) throw new DriverExit(1, `git checkout main failed: ${(r.stderr || r.stdout).trim()}`);
    });
  }
  act('git fetch origin --prune', () => {
    const r = fetchOrigin();
    if (r.code !== 0) throw new DriverExit(1, `git fetch failed: ${(r.stderr || r.stdout).trim()}\nFix: check the network and run "gh auth setup-git".`);
  });
  act('git pull --ff-only origin main', () => {
    const r = git(['pull', '--ff-only', 'origin', 'main'], { timeoutMs: 300000 });
    if (r.code !== 0) throw new DriverExit(1, `git pull --ff-only failed: ${(r.stderr || r.stdout).trim()}\nFix: local main has diverged. After saving anything you need: git checkout main && git reset --hard origin/main`);
    const ahead = Number(git(['rev-list', '--count', 'origin/main..main']).stdout.trim() || 0);
    if (ahead > 0) throw new DriverExit(2, `local main has ${ahead} commit(s) that are not on origin/main.\nFix: push them through a pull request, or git reset --hard origin/main if they are not needed.`);
  });
  return { actions, problems };
}

/** Check out a unit branch at origin's tip. Local leftovers were pushed or stashed by prepareTree. */
export function checkoutBranch(branch) {
  const f = fetchBranch(branch);
  if (f.code !== 0) throw new DriverExit(1, `git fetch origin ${branch} failed: ${(f.stderr || f.stdout).trim()}`);
  // checkout -B resets the local branch to origin's: refuse when that would drop local commits.
  if (git(['rev-parse', '--verify', '--quiet', `refs/heads/${branch}`]).code === 0) {
    const ahead = Number(git(['rev-list', '--count', `origin/${branch}..${branch}`]).stdout.trim() || 0);
    if (ahead > 0) throw new DriverExit(2, `local branch ${branch} has ${ahead} commit(s) that are not on origin/${branch}; the driver will not reset it.\nFix: git push origin ${branch} (or git branch -m ${branch} ${branch}-backup if you do not need them), then rerun.`);
  }
  const r = git(['checkout', '-B', branch, `origin/${branch}`]);
  if (r.code !== 0) throw new DriverExit(1, `git checkout ${branch} failed: ${(r.stderr || r.stdout).trim()}`);
}

/**
 * Delete the local copy of a merged branch, only when every local commit is part of the commit that
 * merged (mergedOid): a squash merge leaves origin without the branch, so "ahead of origin" cannot be asked.
 * Returns false (and keeps the branch) when it holds anything else.
 */
export function deleteLocalBranch(branch, mergedOid) {
  const tip = git(['rev-parse', '--verify', '--quiet', `refs/heads/${branch}`]);
  if (tip.code !== 0) return true; // no local branch
  const inMerged = mergedOid && git(['merge-base', '--is-ancestor', tip.stdout.trim(), mergedOid]).code === 0;
  if (!inMerged) return false;
  if (currentBranch() === branch) git(['checkout', 'main']);
  git(['branch', '-D', branch]);
  return true;
}

// --- PR helpers -----------------------------------------------------------------------------

export const prView = (ctx, pr, fields) => ghJson(ctx, ['pr', 'view', String(pr), '--json', fields]);

/** Add a label, creating it first if the repository does not have it yet. */
export function addLabel(ctx, pr, name) {
  let r = gh(ctx, ['pr', 'edit', String(pr), '--add-label', name]);
  if (r.code !== 0 && /not found|could not add label/i.test(`${r.stderr}${r.stdout}`)) {
    gh(ctx, ['label', 'create', name, '--force', '--description', name === LABEL_STOPPED ? 'The autopilot stopped on this PR: see .autopilot/stop.json' : 'Run the end-to-end suite']);
    r = gh(ctx, ['pr', 'edit', String(pr), '--add-label', name]);
  }
  return r.code === 0;
}

export function progressOnRef(ref) {
  return showFile(ref, FILES.progress);
}
