// Pure helpers: usage limits, overage, auth errors, permission denials, auto-mode availability.
// rate_limit_info (Claude Code 2.1.288): {status: allowed|allowed_warning|rejected, resetsAt (epoch s),
// rateLimitType: five_hour|seven_day|seven_day_opus|seven_day_sonnet|seven_day_overage_included|overage,
// utilization, overageStatus, overageDisabledReason, isUsingOverage, overageInUse, unifiedWindows}.

export const DEFAULT_LIMIT_WAIT_MS = 30 * 60 * 1000;
export const LIMIT_GRACE_MS = 60 * 1000;
export const DENIAL_LIMIT = 5;

/** Normalise a rate_limit_info object. Missing fields are fine. */
export function assessRateLimit(info) {
  if (!info || typeof info !== 'object') return null;
  const type = info.rateLimitType ?? null;
  const status = info.status ?? 'allowed';
  const resetsAt = Number.isFinite(info.resetsAt) ? info.resetsAt : info.unifiedWindows?.[type]?.resetsAt;
  const utilization = info.utilization ?? info.unifiedWindows?.[type]?.utilization ?? null;
  return {
    status,
    type,
    rejected: status === 'rejected',
    warning: status === 'allowed_warning',
    resetsAtMs: Number.isFinite(resetsAt) ? resetsAt * 1000 : null,
    utilization,
    // Paid extra usage is being drawn on. overageStatus alone only says it is enabled.
    usingOverage: info.isUsingOverage === true || info.overageInUse === true || type === 'overage',
    overageEnabled: info.overageStatus === 'allowed' || info.overageStatus === 'allowed_warning',
    overageStatus: info.overageStatus ?? null,
    opusWeekly: type === 'seven_day_opus',
  };
}

const LIMIT_TEXT_RE = /you['’]ve hit your|usage limit|rate limit|limit reached|out of usage|weekly limit|5-hour limit|session limit|opus limit/i;
const SHORT_ERROR_MAX = 600; // API errors are short; a long final summary is not an error banner

const shortErrorText = (result) => {
  const t = String(result?.result ?? '');
  return result?.is_error && t.length <= SHORT_ERROR_MAX ? t : '';
};

/**
 * Did the session end because a usage limit was hit? rejections: active rejected assessments
 * (see StreamTracker). Returns null, or {resumeAtMs, type, opusWeekly, known, reason}.
 * The caller sleeps until resumeAtMs (reset + 60 s, or +30 min when the reset is unknown),
 * then resumes the same session. A weekly Opus rejection also pauses the whole run.
 */
export function limitPauseDecision({ rejections = [], result, exitCode, nowMs = Date.now(), graceMs = LIMIT_GRACE_MS, defaultWaitMs = DEFAULT_LIMIT_WAIT_MS }) {
  const errored = !result || result.is_error === true || (exitCode ?? 0) !== 0;
  if (!errored) return null;
  const textHit = LIMIT_TEXT_RE.test(shortErrorText(result)) || result?.api_error_status === 429;
  if (rejections.length === 0 && !textHit) return null;
  const futureResets = rejections.map((r) => r.resetsAtMs).filter((ms) => ms !== null && ms + graceMs > nowMs);
  const known = futureResets.length > 0;
  const resumeAtMs = known ? Math.max(...futureResets) + graceMs : nowMs + defaultWaitMs;
  const type = rejections.find((r) => r.opusWeekly)?.type ?? rejections[0]?.type ?? null;
  return {
    resumeAtMs,
    type,
    opusWeekly: rejections.some((r) => r.opusWeekly),
    known,
    reason: `${type ?? 'usage'} limit`,
  };
}

const AUTH_RE = /not logged in|please run \/login|failed to authenticate|authentication_error|invalid api key|oauth (?:token|session)|authentication required|\b401\b/i;
const AUTH_TRANSIENT_RE = /another claude code process is refreshing/i;

/** Login/401 errors are never retried: the owner has to sign in again. */
export function isAuthError({ result, stderr = '', exitCode } = {}) {
  const errored = !result || result.is_error === true || (exitCode ?? 0) !== 0;
  if (!errored) return false;
  if (result?.api_error_status === 401) return true;
  const text = `${shortErrorText(result)}\n${stderr}`;
  return AUTH_RE.test(text) && !AUTH_TRANSIENT_RE.test(text);
}

/** 'permanent' (plan, model or settings rule it out), 'transient' (classifier outage) or null. */
export function autoModeUnavailable(text) {
  const t = String(text ?? '');
  if (/no safety verdict/i.test(t)) return 'transient';
  if (/auto mode (?:isn['’]t available|is unavailable|unavailable|disabled)|does not support auto mode/i.test(t)) return 'permanent';
  return null;
}

const GUARD_RE = /\b(?:bash|agent|file)-guard:/;

/**
 * Permission denials of a session. Denials caused by our own PreToolUse guards are listed but not
 * counted: they are deliberate feedback to the model, and an allow rule would not help the owner.
 * errorResults: [{id, tool, input, text}] tool results with is_error (see StreamTracker).
 */
export function denialSummary(result, errorResults = []) {
  const list = Array.isArray(result?.permission_denials) ? result.permission_denials : [];
  const byId = new Map(errorResults.filter((e) => e.id).map((e) => [e.id, e]));
  const isGuard = (text) => GUARD_RE.test(String(text ?? ''));
  let items = list.map((d) => {
    const err = byId.get(d.tool_use_id);
    return { tool: d.tool_name ?? '?', input: d.tool_input ?? null, guard: isGuard(err?.text), reason: err?.text ?? null };
  });
  const aborted = /too many classifier denials/i.test(String(result?.result ?? ''));
  if (items.length === 0 && aborted) {
    items = errorResults.map((e) => ({ tool: e.tool, input: e.input, guard: isGuard(e.text), reason: e.text }));
  }
  const counted = items.filter((i) => !i.guard).length;
  return { items, total: items.length, counted, aborted, tooMany: aborted || counted >= DENIAL_LIMIT };
}

/** One line per denial for the exit-3 report. */
export function formatDenials(summary) {
  return summary.items.map((d, i) => {
    const input = d.input == null ? '' : ` ${JSON.stringify(d.input).slice(0, 300)}`;
    return `  ${i + 1}. ${d.tool}${input}${d.guard ? ' [blocked by a guard hook]' : ''}${d.reason ? `\n     reason: ${String(d.reason).replace(/\s+/g, ' ').slice(0, 200)}` : ''}`;
  });
}
