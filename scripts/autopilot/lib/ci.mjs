// Pure helpers: classify the JSON and text that `gh` returns about checks, runs and protection.

export const CI_CHECK_NAME = 'ci';
export const LABEL_E2E = 'e2e';
export const LABEL_STOPPED = 'autopilot:stopped';

/**
 * gh pr checks --json name,bucket,state,link,workflow. ONLY checks named `name` (the required `ci`
 * aggregator) count: a green lint job or a skipped ci is never a pass.
 * bucket: pass | fail | pending | skipping | cancel. Result state: pending, fail, pass, or none
 * (no such check yet, or it was skipped). Order of precedence: pending, fail, pass.
 */
export function classifyChecks(checks, name = CI_CHECK_NAME) {
  const own = Array.isArray(checks) ? checks.filter((c) => c && c.name === name) : [];
  const failed = own.filter((c) => c.bucket === 'fail' || c.bucket === 'cancel');
  const pending = own.filter((c) => c.bucket === 'pending');
  const passed = own.filter((c) => c.bucket === 'pass');
  const other = own.length - failed.length - pending.length - passed.length; // skipping, unknown buckets
  const state = pending.length ? 'pending' : failed.length ? 'fail' : passed.length > 0 && other === 0 ? 'pass' : 'none';
  return { state, failed, pending, passed };
}

export function runIdFromLink(link) {
  const m = /\/actions\/runs\/(\d+)/.exec(String(link ?? ''));
  return m ? m[1] : null;
}

/** Distinct run ids of the failed checks, in order. */
export function failedRunIds(failed) {
  return [...new Set(failed.map((c) => runIdFromLink(c.link)).filter(Boolean))];
}

/** True when `gh pr checks` says it has nothing to show yet. */
export function hasNoChecks(text) {
  return /no (?:required )?checks reported/i.test(String(text ?? ''));
}

/**
 * gh run list --branch main --workflow ci.yml --limit 1 --json conclusion,status,databaseId,headSha,url
 * -> {state: none|running|green|red|other, run}
 */
export function classifyMainRun(runs) {
  const run = Array.isArray(runs) ? runs[0] : null;
  if (!run) return { state: 'none', run: null };
  if (run.status && run.status !== 'completed') return { state: 'running', run };
  if (run.conclusion === 'success') return { state: 'green', run };
  if (['failure', 'timed_out', 'startup_failure'].includes(run.conclusion)) return { state: 'red', run };
  return { state: 'other', run }; // cancelled, skipped, neutral, stale, action_required
}

/** "Token scopes: 'gist', 'read:org', 'repo', 'workflow'" from `gh auth status`, or null if not shown. */
export function parseTokenScopes(text) {
  const m = /Token scopes:\s*(.+)/i.exec(String(text ?? ''));
  if (!m) return null;
  return [...m[1].matchAll(/['"]?([A-Za-z0-9:_-]+)['"]?/g)].map((x) => x[1]).filter((s) => s.toLowerCase() !== 'none');
}

export function isGhLoggedOut(text) {
  return /not logged into|gh auth login|no accounts? (?:is )?logged/i.test(String(text ?? ''));
}

/**
 * gh api repos/{owner}/{repo}/branches/main/protection (parsed JSON, or {message:"Branch not protected"}).
 * Returns {protected, requiresPr, requiresCi, enforceAdmins, requiredReviews, problems[]}. The driver needs
 * all of: protected, a pull request required (else a commit whose ci passed can be pushed to main directly),
 * the `ci` check required, enforced for administrators (the owner account is an admin, so without it every
 * rule can be bypassed), and no required reviews (the driver cannot approve).
 */
export function assessBranchProtection(json) {
  if (!json || typeof json !== 'object' || /not protected|not found/i.test(String(json.message ?? ''))) {
    return { protected: false, requiresPr: false, requiresCi: false, enforceAdmins: false, requiredReviews: 0, problems: [] };
  }
  const rsc = json.required_status_checks;
  const names = [...(rsc?.contexts ?? []), ...((rsc?.checks ?? []).map((c) => c.context))];
  const requiresCi = names.includes(CI_CHECK_NAME);
  const requiredReviews = json.required_pull_request_reviews?.required_approving_review_count ?? 0;
  const problems = [];
  if (requiredReviews > 0) problems.push(`main requires ${requiredReviews} approving review(s), so the driver cannot merge`);
  return { protected: true, requiresPr: json.required_pull_request_reviews != null, requiresCi, enforceAdmins: json.enforce_admins?.enabled === true, requiredReviews, problems };
}

/** gh api repos/{owner}/{repo}: the merge settings the driver depends on. */
export function assessRepoSettings(json) {
  const problems = [];
  if (json && json.allow_squash_merge === false) problems.push('squash merging is disabled on the repository (the driver merges with --squash)');
  return { problems };
}

/** True when the labels array of gh pr view --json labels holds a label by name. */
export function hasLabel(labels, name) {
  return Array.isArray(labels) && labels.some((l) => (typeof l === 'string' ? l : l?.name) === name);
}
