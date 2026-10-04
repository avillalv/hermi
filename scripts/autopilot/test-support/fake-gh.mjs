// A fake `gh` for driver.test.mjs. Run as: node fake-gh.mjs <gh arguments>.
// It answers only what the driver asks, from the state in FAKE_STATE_DIR, and performs real squash
// merges in the bare origin repository so the driver's git commands see real results.

import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { ghState, ORIGIN, scenario } from './fake-state.mjs';

const argv = process.argv.slice(2);
const [a, b] = argv;
const has = (f) => argv.includes(f);
const val = (f) => {
  const i = argv.indexOf(f);
  return i >= 0 ? argv[i + 1] : undefined;
};
const st = ghState.load();
const sc = scenario();
if (st.mainCi === null) st.mainCi = sc.mainCi ?? 'success';
st.calls.push(argv.join(' '));
if (st.calls.length > 400) st.calls.shift();

const finish = (code = 0) => {
  ghState.save(st);
  process.exit(code);
};
const json = (o) => {
  console.log(JSON.stringify(o));
  finish(0);
};
const fail = (msg, code = 1) => {
  console.error(msg);
  finish(code);
};

const gitOrigin = (...args) => spawnSync('git', ['--git-dir', ORIGIN(), ...args], { encoding: 'utf8' });
const headOf = (branch) => {
  const r = gitOrigin('rev-parse', `refs/heads/${branch}`);
  return r.status === 0 ? r.stdout.trim() : null;
};
const view = (pr) => ({
  number: pr.number,
  state: pr.state,
  isDraft: pr.isDraft,
  labels: pr.labels.map((name) => ({ name })),
  headRefName: pr.headRefName,
  headRefOid: headOf(pr.headRefName) ?? 'deleted',
  mergedAt: pr.state === 'MERGED' ? '2026-01-01T00:00:00Z' : null,
  title: pr.title,
});
const pick = (obj, fields) => Object.fromEntries(String(fields).split(',').map((k) => [k, obj[k]]));
const prArg = () => st.prs[argv[2]];

// sc.duringCi: things that happen while the driver waits for CI, once, when the first final result is returned:
// {stop: true} (stop.json appears), {label: 'autopilot:stopped'}, {draft: true}.
function applyDuringCi(pr) {
  if (!sc.duringCi || st.duringCiDone) return;
  st.duringCiDone = true;
  if (sc.duringCi.stop) {
    fs.mkdirSync('.autopilot', { recursive: true });
    fs.writeFileSync('.autopilot/stop.json', JSON.stringify({ unit: '01', reason: 'spec-conflict', ownerAction: 'Decide which document wins.' }));
  }
  if (sc.duringCi.label && !pr.labels.includes(sc.duringCi.label)) pr.labels.push(sc.duringCi.label);
  if (sc.duringCi.draft) pr.isDraft = true;
}

if (a === '--version') {
  console.log('gh version 2.102.0 (fake)');
  finish(0);
}
if (a === 'auth' && b === 'status') {
  console.error("github.com\n  - Logged in to github.com account fake (keyring)\n  - Token scopes: 'repo', 'workflow'");
  finish(0);
}
if (a === 'api') {
  const url = argv[1] ?? '';
  if (url.endsWith('/branches/main/protection')) {
    // sc.protection: 'none' (not protected), 'no-ci' (ci not required), 'no-admins' (not enforced for administrators), 'no-pr' (no pull request rule)
    if (sc.protection === 'none') {
      console.log(JSON.stringify({ message: 'Branch not protected', status: '404' })); // gh api prints the body, then fails
      console.error('gh: Branch not protected (HTTP 404)');
      finish(1);
    }
    json({ required_status_checks: { contexts: sc.protection === 'no-ci' ? ['lint'] : ['ci'] }, enforce_admins: { enabled: sc.protection !== 'no-admins' }, required_pull_request_reviews: sc.protection === 'no-pr' ? null : { required_approving_review_count: 0 } });
  }
  json({ full_name: 'fake/hermi', private: false, allow_squash_merge: true, permissions: { push: true } });
}
if (a === 'label') finish(0);

if (a === 'pr' && b === 'list') {
  let list = Object.values(st.prs).filter((p) => (val('--state') ?? 'open') === 'all' || p.state === 'OPEN');
  if (val('--label')) list = list.filter((p) => p.labels.includes(val('--label')));
  if (val('--head')) list = list.filter((p) => p.headRefName === val('--head'));
  json(list.map((p) => pick(view(p), val('--json') ?? 'number')));
}
if (a === 'pr' && b === 'view') {
  const pr = prArg();
  if (!pr) fail(`no pull request ${argv[2]}`);
  json(pick(view(pr), val('--json')));
}
if (a === 'pr' && b === 'edit') {
  const pr = prArg();
  if (!pr) fail('no such pull request');
  if (val('--add-label') && !pr.labels.includes(val('--add-label'))) pr.labels.push(val('--add-label'));
  if (val('--remove-label')) pr.labels = pr.labels.filter((l) => l !== val('--remove-label'));
  finish(0);
}
if (a === 'pr' && b === 'ready') {
  const pr = prArg();
  if (!pr) fail('no such pull request');
  pr.isDraft = false;
  finish(0);
}
if (a === 'pr' && b === 'checks') {
  const pr = prArg();
  if (!pr) fail('no such pull request');
  // The driver polls `gh pr checks --json`. The result of the ci check is picked per head commit: the first
  // head gets sc.ci[0], the next head (after a ci-fix push) sc.ci[1], and so on. sc.pendingPolls makes the
  // first n polls of each head say "pending". sc.checks picks another shape of the list.
  const seq = sc.ci?.[pr.number] ?? sc.ci?.default ?? ['pass'];
  const head = headOf(pr.headRefName);
  const cur = (st.ciHeads[pr.number] ??= { head: null, idx: -1, polls: 0 });
  if (cur.head !== head) {
    cur.head = head;
    cur.idx += 1;
    cur.polls = 0;
  }
  if (sc.checks === 'none') fail(`no checks reported on the '${pr.headRefName}' branch`);
  let res = seq[Math.min(cur.idx, seq.length - 1)];
  if (cur.polls++ < (sc.pendingPolls ?? 0)) res = 'pending';
  if (res !== 'pending') applyDuringCi(pr);
  const link = `https://github.com/fake/hermi/actions/runs/${100 + pr.number}/job/1`;
  const state = { pass: 'SUCCESS', fail: 'FAILURE', pending: 'IN_PROGRESS', skipping: 'SKIPPED' }[res];
  const ci = { name: 'ci', bucket: res, state, link, workflow: 'ci' };
  if (sc.checks === 'other-only') json([{ name: 'lint', bucket: 'pass', state: 'SUCCESS', link, workflow: 'ci' }]);
  if (sc.checks === 'with-other') json([{ name: 'lint', bucket: 'pass', state: 'SUCCESS', link, workflow: 'ci' }, ci]);
  json([ci]);
}
if (a === 'pr' && b === 'merge') {
  const pr = prArg();
  if (!pr) fail('no such pull request');
  const match = val('--match-head-commit');
  const head = headOf(pr.headRefName);
  if (match && match !== head) fail(`Head branch was modified. Review and try the merge again. (${match} != ${head})`);
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'fake-merge-'));
  const g = (...args) => {
    const r = spawnSync('git', args, { cwd: tmp, encoding: 'utf8' });
    if (r.status !== 0) fail(`merge failed: git ${args.join(' ')}: ${r.stderr}`);
    return r;
  };
  spawnSync('git', ['clone', '--quiet', '-c', 'core.autocrlf=false', ORIGIN(), tmp], { encoding: 'utf8' });
  g('config', 'user.name', 'Fake GitHub');
  g('config', 'user.email', 'fake@example.com');
  g('config', 'core.autocrlf', 'false');
  g('checkout', 'main');
  g('merge', '--squash', `origin/${pr.headRefName}`);
  g('commit', '-m', `${pr.title} (#${pr.number})`);
  g('push', 'origin', 'HEAD:main');
  if (has('--delete-branch')) gitOrigin('update-ref', '-d', `refs/heads/${pr.headRefName}`);
  fs.rmSync(tmp, { recursive: true, force: true });
  pr.state = 'MERGED';
  if (pr.headRefName.startsWith('fix/main-ci-')) st.mainCi = 'success';
  finish(0);
}

if (a === 'run' && b === 'list') {
  json([{ status: 'completed', conclusion: st.mainCi, databaseId: 900, headSha: 'abc123', url: 'https://github.com/fake/hermi/actions/runs/900' }]);
}
if (a === 'run' && b === 'view') {
  if (has('--log-failed')) {
    console.log('FAILED tests/test_money.py::test_ceiling\nAssertionError: ceiling not enforced');
    finish(0);
  }
  json({ jobs: [{ name: 'ci', conclusion: 'failure', url: 'https://github.com/fake/hermi/actions/runs/900/job/1' }] });
}

fail(`fake gh: unsupported command: gh ${argv.join(' ')}`, 64);
