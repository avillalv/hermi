// Preflight: environment checks (each failure names its exact fix), port cleanup, main's CI state.
// main must be protected, require the ci check and apply to administrators: the driver merges with
// the owner's own token, so protection is the only thing that makes a merge wait for a green ci.
// Every check returns {id, status: ok|warn|fail|info, msg, fix?, exit?} and never throws, so a dry
// run can report all of them. A real run stops at the first failure (see enforce).

import fs from 'node:fs';
import path from 'node:path';
import { assessBranchProtection, assessRepoSettings, classifyMainRun, isGhLoggedOut, parseTokenScopes } from '../lib/ci.mjs';
import { acquireLock, DriverExit, FILES, ROOT, readLock, readStopFile, warn } from './ctx.mjs';
import { clearStaleGitLocks, fileExistsOnRef, gh } from './git.mjs';
import { killTree, pidAlive, portListeners, processCommandLine, processName, run } from './sys.mjs';

export const PORTS = (() => {
  try {
    const p = JSON.parse(process.env.AUTOPILOT_PORTS ?? 'null');
    if (Array.isArray(p)) return p.map(Number);
  } catch {
    // use the defaults
  }
  return [8100, 5173];
})();

const r = (id, status, msg, extra = {}) => ({ id, status, msg, ...extra });

// The exact owner action for the protection check. Classic branch protection is what the API read answers;
// a repository ruleset alone does not show up there, so use the rule below.
const PROTECTION_FIX = [
  'GitHub, Settings, Branches, Add classic branch protection rule, branch name pattern: main.',
  'Tick "Require a pull request before merging" and leave "Require approvals" off (0 approvals).',
  'Tick "Require status checks to pass before merging" and add the check named ci.',
  'Tick "Do not allow bypassing the above settings" (this is "include administrators"), then Save changes.',
  'Or from PowerShell, as the repository owner: \'{"required_status_checks":{"strict":false,"contexts":["ci"]},"enforce_admins":true,"required_pull_request_reviews":{"required_approving_review_count":0},"restrictions":null}\' | gh api -X PUT repos/{owner}/{repo}/branches/main/protection --input -',
].join('\n');

export function checkTools(ctx) {
  const out = [];
  if (!ctx.claudeExe) {
    out.push(r('claude', 'fail', 'claude.exe not found', { exit: 1, fix: 'Install Claude Code (native build) or set AUTOPILOT_CLAUDE to the full path of claude.exe. Never use the .cmd shim.' }));
  } else {
    const v = run(ctx.claudeExe, [...ctx.claudePre, '--version'], { timeoutMs: 30000 });
    out.push(r('claude', 'ok', `claude ${v.stdout.trim() || '(version unknown)'} at ${ctx.claudeExe}`));
  }
  if (!ctx.ghExe) {
    out.push(r('gh', 'fail', 'gh (GitHub CLI) not found', { exit: 1, fix: 'winget install --id GitHub.cli -e, then open a new terminal (or add "C:\\Program Files\\GitHub CLI" to PATH).' }));
  } else {
    const v = run(ctx.ghExe, [...ctx.ghPre, '--version'], { timeoutMs: 30000 });
    out.push(r('gh', 'ok', `${v.stdout.split(/\r?\n/)[0] || 'gh'} at ${ctx.ghExe}${ctx.extraPathDirs.length ? ' (not on PATH: the driver adds it for sessions)' : ''}`));
  }
  const major = Number(process.versions.node.split('.')[0]);
  out.push(major >= 22 ? r('node', 'ok', `node ${process.versions.node}`) : r('node', 'fail', `node ${process.versions.node} is too old`, { exit: 1, fix: 'Install Node 22 or newer.' }));
  return out;
}

/** The files a session needs must be on main: the driver checks main out before every session. */
export function checkFiles() {
  const need = [FILES.appendPrompt, FILES.settings, FILES.settingsDontask, ...FILES.hooks, ...FILES.agents];
  const missing = need.filter((f) => !fileExistsOnRef('main', f));
  if (missing.length === 0) return [r('files', 'ok', `${need.length} required files are on main`)];
  return [r('files', 'fail', `not on main: ${missing.join(', ')}`, { exit: 1, fix: 'Merge the pull requests that add them (build/context-layer adds .claude/agents, build/autopilot adds AUTOPILOT.md and scripts/autopilot).' })];
}

export function checkLock(dry) {
  const cur = readLock();
  if (dry) {
    const alive = cur && pidAlive(cur.pid) && /node/i.test(processName(cur.pid) ?? 'node');
    return [alive ? r('lock', 'fail', `another driver is running (pid ${cur.pid})`, { exit: 1, fix: 'Wait for it, or stop it (Ctrl+C in its window).' }) : r('lock', 'ok', cur ? 'a stale lock exists and would be taken over' : 'no lock')];
  }
  const got = acquireLock();
  if (!got.ok) return [r('lock', 'fail', `another driver is running (pid ${got.holder?.pid ?? '?'})`, { exit: 1, fix: 'Wait for it, or stop it (Ctrl+C in its window). If it is dead, delete .autopilot/lock.' })];
  if (got.tookOver) clearStaleGitLocks(); // the dead driver's session may have been killed mid-git
  return [r('lock', 'ok', got.tookOver ? 'took over a stale lock' : 'lock acquired')];
}

export function checkStopFile() {
  const s = readStopFile();
  if (!s) return [r('stop', 'ok', 'no .autopilot/stop.json')];
  return [r('stop', 'fail', `stopped on unit ${s.unit}: ${s.reason}`, { exit: 2, fix: `${s.ownerAction}\nThen delete .autopilot/stop.json (and remove the autopilot:stopped label from the PR) and rerun.` })];
}

export function checkHandoff() {
  const dir = path.join(ROOT, FILES.handoffDir);
  let active = [];
  try {
    active = fs.readdirSync(dir).filter((f) => f.endsWith('.md')).filter((f) => {
      const fm = /^---\r?\n([\s\S]*?)\r?\n---/.exec(fs.readFileSync(path.join(dir, f), 'utf8'));
      return fm !== null && /^status:\s*["']?active["']?\s*$/im.test(fm[1]);
    });
  } catch {
    // no handoff directory
  }
  if (active.length === 0) return [r('handoff', 'ok', 'no active PR-train handoff')];
  return [r('handoff', 'fail', `active PR-train handoff: ${active.join(', ')}`, { exit: 2, fix: `Finish the train and set "status: complete" in .claude/handoff/${active[0]} (the autopilot is not a PR train).` })];
}

/** .claude/settings.local.json overrides the settings files, so it can switch the guard hooks off for a session. */
export function checkLocalSettings() {
  if (!fs.existsSync(path.join(ROOT, '.claude', 'settings.local.json'))) return [r('local-settings', 'ok', 'no .claude/settings.local.json')];
  return [r('local-settings', 'fail', '.claude/settings.local.json exists in the checkout, and it can disable the guard hooks of a session', { exit: 2, fix: 'delete .claude/settings.local.json (it can disable the hooks)' })];
}

export function checkGhAuth(ctx) {
  if (!ctx.ghExe) return [r('gh-auth', 'fail', 'gh is not installed', { exit: 5, fix: 'Install gh first (see the gh check).' })];
  const s = gh(ctx, ['auth', 'status']);
  const text = `${s.stdout}\n${s.stderr}`;
  if (s.code !== 0 || isGhLoggedOut(text)) {
    return [r('gh-auth', 'fail', 'gh is not logged in', { exit: 5, fix: 'Run: gh auth login (GitHub.com, HTTPS, browser), then: gh auth setup-git, then: gh auth refresh -s workflow' })];
  }
  ctx.ghReady = true;
  const scopes = parseTokenScopes(text);
  if (scopes && !scopes.includes('workflow')) {
    return [r('gh-auth', 'fail', `gh token lacks the workflow scope (has: ${scopes.join(', ')})`, { exit: 5, fix: 'Run: gh auth refresh -s workflow (pushes that touch .github/workflows are rejected without it).' })];
  }
  return [r('gh-auth', scopes ? 'ok' : 'warn', scopes ? `gh logged in, scopes: ${scopes.join(', ')}` : 'gh logged in; the token scopes are not shown, so the workflow scope is unverified')];
}

export function checkClaudeAuth(ctx) {
  const out = [];
  if (!ctx.claudeExe) return [r('claude-auth', 'fail', 'claude is not installed', { exit: 5, fix: 'Install Claude Code first.' })];
  const s = run(ctx.claudeExe, [...ctx.claudePre, 'auth', 'status', '--json'], { timeoutMs: 60000 });
  let j = null;
  try {
    j = JSON.parse(s.stdout);
  } catch {
    // handled below
  }
  if (!j || j.loggedIn !== true) {
    out.push(r('claude-auth', 'fail', 'claude is not logged in', { exit: 5, fix: 'Run: claude auth login (use the Claude Max account) and rerun.' }));
  } else if (/api[_ -]?key/i.test(String(j.authMethod)) || (j.apiProvider && j.apiProvider !== 'firstParty')) {
    out.push(r('claude-auth', 'fail', `claude authenticates with ${j.authMethod} (${j.apiProvider}): the build would bill the API`, { exit: 5, fix: 'Log out and use the subscription: claude auth logout, then claude auth login (claude.ai account).' }));
  } else {
    out.push(r('claude-auth', 'ok', `claude logged in via ${j.authMethod}, plan ${j.subscriptionType ?? '?'}`));
  }
  if (process.env.ANTHROPIC_API_KEY) {
    out.push(r('api-key-env', 'warn', 'ANTHROPIC_API_KEY is set in this shell (the driver removes it from sessions, but it bills the API anywhere else)', { fix: 'Remove it: in PowerShell, Remove-Item Env:ANTHROPIC_API_KEY' }));
  }
  return out;
}

export function checkGitignore() {
  const ig = run('git', ['check-ignore', '-q', '.autopilot/state.json'], { cwd: ROOT });
  if (ig.code === 0) return [r('gitignore', 'ok', '.autopilot/ is gitignored')];
  return [r('gitignore', 'fail', '.autopilot/ is not gitignored (a stash or commit would swallow the driver state)', { exit: 1, fix: 'Add ".autopilot/" to .gitignore (PR 0, chore/context-baseline, adds it) and merge it.' })];
}

export function checkRepo(ctx) {
  if (!ctx.ghReady) return [r('repo', 'info', 'repository checks skipped (gh is not logged in)')];
  const out = [];
  const repo = gh(ctx, ['api', 'repos/{owner}/{repo}']);
  let rj = null;
  try {
    rj = JSON.parse(repo.stdout);
  } catch {
    // reported below
  }
  if (!rj) {
    out.push(r('repo', 'fail', `cannot read the repository: ${(repo.stderr || repo.stdout).trim().slice(0, 200)}`, { exit: 1, fix: 'Check that "git remote -v" points at github.com/avillalv/hermi and the gh account can push to it.' }));
    return out;
  }
  const settings = assessRepoSettings(rj);
  for (const p of settings.problems) out.push(r('repo', 'fail', p, { exit: 2, fix: 'GitHub, Settings, General, Pull Requests: allow squash merging.' }));
  if (rj.permissions && rj.permissions.push === false) {
    out.push(r('repo', 'fail', 'the gh account cannot push to the repository', { exit: 2, fix: 'Log in with an account that has write access (gh auth login).' }));
  }
  const prot = gh(ctx, ['api', 'repos/{owner}/{repo}/branches/main/protection']);
  let pj = null;
  try {
    pj = JSON.parse(prot.stdout);
  } catch {
    // treated as unprotected
  }
  const a = assessBranchProtection(pj);
  const fail = (msg) => out.push(r('protection', 'fail', msg, { exit: 2, fix: PROTECTION_FIX }));
  if (!a.protected) fail('main has no branch protection, so nothing but this program stops a merge with a red or missing ci');
  else {
    if (!a.requiresPr) fail('main protection does not require a pull request, so a commit whose ci passed can be pushed to main directly');
    if (!a.requiresCi) fail('main protection does not require the "ci" status check');
    if (!a.enforceAdmins) fail('main protection is not enforced for administrators, so the owner account (and a token that carries it) can bypass every rule');
    for (const p of a.problems) fail(p);
    if (a.requiresPr && a.requiresCi && a.enforceAdmins && a.problems.length === 0) out.push(r('protection', 'ok', 'main is protected: a pull request and ci are required and the rules apply to administrators'));
  }
  if (out.every((x) => x.status !== 'fail') && !out.some((x) => x.id === 'repo')) out.unshift(r('repo', 'ok', `repository ${rj.full_name ?? ''} ${rj.private ? '(private)' : '(public)'}, squash merging allowed`));
  return out;
}

export function checkStoppedPrs(ctx) {
  if (!ctx.ghReady) return [r('stopped-prs', 'info', 'skipped (gh is not logged in)')];
  const l = gh(ctx, ['pr', 'list', '--label', 'autopilot:stopped', '--state', 'open', '--json', 'number,title,headRefName']);
  let list = [];
  try {
    list = JSON.parse(l.stdout);
  } catch {
    return [r('stopped-prs', 'warn', `could not list PRs: ${(l.stderr || l.stdout).trim().slice(0, 160)}`)];
  }
  if (list.length === 0) return [r('stopped-prs', 'ok', 'no PR is labelled autopilot:stopped')];
  const first = list[0];
  return [r('stopped-prs', 'fail', `PR #${first.number} (${first.headRefName}) is labelled autopilot:stopped`, { exit: 2, fix: `Read the PR, fix the cause, then: gh pr edit ${first.number} --remove-label autopilot:stopped (and delete .autopilot/stop.json), and rerun.` })];
}

// --- ports ----------------------------------------------------------------------------------

function ours(cmdline) {
  const c = cmdline.toLowerCase().replace(/\\/g, '/');
  return c.includes(ROOT.toLowerCase().replace(/\\/g, '/')) || c.includes('hermi');
}

/**
 * Free ports 8100 and 5173. Stray Hermi dev servers (their command line names this repo or hermi)
 * are killed with their whole tree. Anything else is NOT killed: the owner decides.
 */
export function freePorts({ dry = false } = {}) {
  const out = [];
  for (const port of PORTS) {
    const pids = portListeners(port);
    if (pids.length === 0) {
      out.push(r(`port-${port}`, 'ok', `port ${port} is free`));
      continue;
    }
    for (const pid of pids) {
      const name = processName(pid) ?? '?';
      const cmd = processCommandLine(pid);
      if (!ours(cmd)) {
        out.push(r(`port-${port}`, 'fail', `port ${port} is held by ${name} (pid ${pid}), which is not part of Hermi: ${cmd.slice(0, 120)}`, { exit: 1, fix: `Stop that program (taskkill /PID ${pid} /T /F) or free port ${port}.` }));
      } else if (dry) {
        out.push(r(`port-${port}`, 'info', `would kill stray ${name} (pid ${pid}) holding port ${port}`));
      } else {
        killTree(pid);
        out.push(r(`port-${port}`, 'ok', `killed stray ${name} (pid ${pid}) holding port ${port}`));
      }
    }
  }
  return out;
}

// --- main CI --------------------------------------------------------------------------------

/** Latest run of ci.yml on main: {state: none|running|green|red|other, run}. */
export function mainCiState(ctx) {
  if (!ctx.ghReady) return { state: 'none', run: null, note: 'gh is not logged in' };
  const l = gh(ctx, ['run', 'list', '--branch', 'main', '--workflow', 'ci.yml', '--limit', '1', '--json', 'conclusion,status,databaseId,headSha,url']);
  if (l.code !== 0) return { state: 'none', run: null, note: (l.stderr || l.stdout).trim().slice(0, 160) };
  try {
    return classifyMainRun(JSON.parse(l.stdout));
  } catch {
    return { state: 'none', run: null, note: 'unreadable gh output' };
  }
}

// --- reporting ------------------------------------------------------------------------------

const TAG = { ok: '[ ok ]', warn: '[warn]', fail: '[FAIL]', info: '[info]' };

export function printResults(results) {
  for (const x of results) {
    console.log(`  ${TAG[x.status]} ${x.msg}`);
    if (x.fix && x.status !== 'ok') console.log(`         Fix: ${x.fix.replace(/\n/g, '\n              ')}`);
  }
}

/** Real run: print warnings once per run, stop at the first failure with its exit code and fix. */
export function enforce(results, ctx) {
  for (const x of results) {
    if (x.status !== 'warn') continue;
    const msg = `${x.msg}${x.fix ? ` Fix: ${x.fix}` : ''}`;
    if (ctx?.warned?.has(msg)) continue;
    ctx?.warned?.add(msg);
    warn(msg);
  }
  const bad = results.find((x) => x.status === 'fail');
  if (bad) throw new DriverExit(bad.exit ?? 1, `${bad.msg}\nFix: ${bad.fix ?? 'see above'}`);
}

const REMOTE_TTL_MS = 10 * 60 * 1000;

/**
 * Environment checks that run before every session. The ones that need a network round trip or a
 * subprocess (tool versions, gh and claude login, repository settings and protection) are cached for
 * ten minutes per run and only when they all passed; the cheap local ones run every time.
 */
export function environmentChecks(ctx, { dry = false } = {}) {
  let remote = ctx.remoteChecks && !dry && Date.now() - ctx.remoteChecks.at < REMOTE_TTL_MS ? ctx.remoteChecks.results : null;
  if (!remote) {
    remote = [...checkTools(ctx), ...checkGhAuth(ctx), ...checkClaudeAuth(ctx), ...checkRepo(ctx)];
    if (!dry && remote.every((x) => x.status !== 'fail')) ctx.remoteChecks = { at: Date.now(), results: remote };
  }
  return [
    ...remote,
    ...checkFiles(),
    ...checkLock(dry),
    ...checkStopFile(),
    ...checkHandoff(),
    ...checkLocalSettings(),
    ...checkGitignore(),
    ...checkStoppedPrs(ctx),
  ];
}
