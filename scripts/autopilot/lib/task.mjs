// Pure helpers: task lines, branch and log names, prompt ticket tables, commit subjects.
// No I/O here, so every function is covered by run.test.mjs.

export const MODES = ['plan', 'ticket', 'ship', 'ci-fix', 'final'];

const UNIT_SETUP_RE = /^S([1-9]\d*)$/;
const UNIT_BUILD_RE = /^(\d{2})$/;

/** 'setup' (S1..S3), 'build' (01..28), 'final', 'main' (ci-fix of a red main) or null. */
export function unitKind(unit) {
  if (UNIT_SETUP_RE.test(unit)) return 'setup';
  if (UNIT_BUILD_RE.test(unit)) return 'build';
  if (unit === 'FINAL') return 'final';
  if (unit === 'main') return 'main';
  return null;
}

/** MODE=ticket UNIT=07 STEP=WF-023 PR=123 ATTEMPT=1 (STEP and PR are optional). */
export function buildTaskLine({ mode, unit, step, pr, attempt }) {
  if (!MODES.includes(mode)) throw new Error(`unknown mode: ${mode}`);
  if (!unit) throw new Error('unit is required');
  const parts = [`MODE=${mode}`, `UNIT=${unit}`];
  if (step) parts.push(`STEP=${step}`);
  if (pr) parts.push(`PR=${pr}`);
  parts.push(`ATTEMPT=${attempt ?? 1}`);
  return parts.join(' ');
}

/**
 * What goes on the session's stdin: the task line, then optional blocks.
 * A ci-fix line is followed by a FAILED_CHECKS block. On a retry the driver adds a
 * RETRY_NOTE block saying what the previous attempt failed to produce.
 */
export function buildSessionInput({ taskLine, failedChecks, retryNote }) {
  let out = taskLine;
  if (failedChecks) out += `\nFAILED_CHECKS:\n${failedChecks.replace(/\s+$/, '')}`;
  if (retryNote) out += `\nRETRY_NOTE: ${retryNote.replace(/\s+/g, ' ').trim()}`; // one line, as AUTOPILOT.md promises
  return `${out}\n`;
}

export const CONTINUE_TEXT = 'Continue the task from where you stopped.';

/** '01-repo-foundation.md' -> 'repo-foundation'; 'S1-runtime.md' -> 'runtime'. */
export function slugFromPromptFile(fileName) {
  const m = /^(?:S[1-9]\d*|\d{2})-(.+)\.md$/.exec(fileName);
  return m ? m[1] : null;
}

/** Prompt file name for a unit out of a directory listing, or null. */
export function promptFileForUnit(unit, fileNames) {
  const prefix = `${unit}-`;
  return fileNames.find((f) => f.startsWith(prefix) && f.endsWith('.md') && slugFromPromptFile(f)) ?? null;
}

/** phase1/pNN-<slug>, spec/sN-<slug>, phase1/final. Null when the unit has no branch (main). */
export function expectedBranch(unit, slug) {
  const kind = unitKind(unit);
  if (kind === 'final') return 'phase1/final';
  if (kind === 'build') return `phase1/p${unit}-${slug}`;
  if (kind === 'setup') return `spec/s${unit.slice(1)}-${slug}`;
  return null;
}

/** Branch prefix a unit's plan may use. */
export function branchPrefixFor(unit) {
  const kind = unitKind(unit);
  if (kind === 'setup') return 'spec/';
  if (kind === 'build' || kind === 'final') return 'phase1/';
  return null;
}

export function sessionName({ unit, mode, step }) {
  return `hermi-${unit}-${mode}${step ? `-${safeName(step)}` : ''}`;
}

function safeName(s) {
  return String(s).replace(/[^A-Za-z0-9._-]/g, '_');
}

const pad = (n, w = 2) => String(n).padStart(w, '0');

/** yyyymmddThhmmss in local time. */
export function formatStamp(d = new Date()) {
  return `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}T${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`;
}

/** yyyymmdd in local time (fix/main-ci-<yyyymmdd>). */
export function formatDay(d = new Date()) {
  return formatStamp(d).slice(0, 8);
}

/** <unit>-<mode>[-<step>]-<yyyymmddThhmmss>.jsonl */
export function logFileName({ unit, mode, step, date }) {
  return `${unit}-${mode}${step ? `-${safeName(step)}` : ''}-${formatStamp(date)}.jsonl`;
}

/**
 * Rows of the "## Tickets, in this order" table of a prompt file: [{ticket, title}].
 * Header and separator rows are skipped. Returns [] when the section is missing.
 */
export function parsePromptTickets(md) {
  const lines = String(md).split(/\r?\n/);
  const start = lines.findIndex((l) => /^##\s+Tickets,\s+in this order\s*$/i.test(l.trim()));
  if (start < 0) return [];
  const rows = [];
  for (let i = start + 1; i < lines.length; i++) {
    const line = lines[i].trim();
    if (/^##\s/.test(line)) break;
    if (!line.startsWith('|')) continue;
    const cells = line.split('|').slice(1, -1).map((c) => c.trim());
    if (cells.length < 1) continue;
    if (/^-+$/.test(cells[0].replace(/[:\s]/g, ''))) continue; // separator
    if (/^ticket$/i.test(cells[0])) continue; // header
    rows.push({ ticket: cells[0], title: cells[1] ?? '' });
  }
  return rows;
}

// --- verdict ids -------------------------------------------------------------------------------
// A step is approved by `VERDICT: APPROVE <step id>`. Three more ids guard the commits no step review covers.

export const FINAL_VERDICT_ID = 'FINAL';
export const ciFixVerdictId = (pr, n) => `ci-fix-${pr}-${n}`;
export const shipVerdictId = (unit) => `ship-${unit}`;

/** Who may issue a verdict id: the final gate and ci-fix diffs go to opus-judge, a ship diff to opus-reviewer. */
export function approverFor(id) {
  if (id === FINAL_VERDICT_ID || /^ci-fix-\d+-\d+$/.test(id)) return ['opus-judge'];
  if (/^ship-/.test(id)) return ['opus-reviewer'];
  return ['opus-reviewer', 'opus-judge'];
}

/**
 * The only verdict ids a session may earn, by mode. Everything else it prints is ignored, so a ticket
 * session cannot approve another step, and a ship session cannot approve a ci-fix. spec: {mode, unit, step, pr, attempt}.
 */
export function verdictAllowed({ mode, unit, step, pr, attempt }) {
  switch (mode) {
    case 'ticket':
      return (id) => id === step;
    case 'ship':
      return (id) => id === shipVerdictId(unit);
    case 'ci-fix':
      // A red main: the session opens its own PR, so the number is not known yet.
      return pr ? (id) => id === ciFixVerdictId(pr, attempt) : (id) => new RegExp(`^ci-fix-\\d+-${Number(attempt)}$`).test(id);
    case 'final':
      return (id) => id === FINAL_VERDICT_ID;
    default:
      return () => false;
  }
}

// What a ship session may change without a second review: documents, the status logs, knowledge,
// findings, project skills, the generated API types and the seed data.
const SHIP_SAFE = [
  /^docs\//,
  /^knowledge\//,
  /^findings\//,
  /^\.claude\/skills\//,
  /^apps\/web\/src\/lib\/api\//,
  /^apps\/api\/hermi\/seed\//,
  /^infra\/scripts\/seed-staging\.py$/,
  /^app-buildout\/prompts\/(?:PROGRESS|HUMAN_TASKS|DECISIONS)\.md$/,
];

export const isShipSafePath = (file) => SHIP_SAFE.some((re) => re.test(String(file).replace(/\\/g, '/')));

/** True when a commit subject starts with "<step id> " (WF-005 must not match WF-005.1). */
export function commitSubjectMatches(subject, stepId) {
  return subject.startsWith(`${stepId} `);
}

export function hasStepCommit(subjects, stepId) {
  return subjects.some((s) => commitSubjectMatches(s, stepId));
}

// A step commit ("WF-023 title", "WF-005.1 title", "S1.2 title"): its id is what an Opus verdict must name.
const STEP_COMMIT_RE = /^((?:WF-\d+|S\d+\.\d+)(?:\.\d+)?) /;

/**
 * Step ids named by commit subjects that no approved id covers. An id is covered when it is approved, or
 * when it was split and its sub-steps (<id>.<k>) are approved. Subjects that are not step commits are ignored.
 */
export function uncoveredStepIds(subjects, approvedIds) {
  const ids = new Set(subjects.map((s) => STEP_COMMIT_RE.exec(s)?.[1]).filter(Boolean));
  return [...ids].filter((id) => !approvedIds.some((a) => a === id || a.startsWith(`${id}.`)));
}

export function tailLines(text, n) {
  const lines = String(text).replace(/\s+$/, '').split(/\r?\n/);
  return lines.slice(-n).join('\n');
}

export const FAILED_LOG_LINES = 200;
export const FAILED_BLOCK_MAX_CHARS = 60000;

/**
 * Body of the FAILED_CHECKS block for a ci-fix task: the failed check names, then the tail
 * (last 200 lines) of `gh run view <id> --log-failed` per failed run.
 * checks: [{name, bucket, link}]; logs: [{runId, text}]
 */
export function buildFailedChecksBlock({ checks = [], logs = [] }) {
  const parts = [];
  for (const c of checks) parts.push(`- ${c.name}${c.bucket ? ` (${c.bucket})` : ''}${c.link ? ` ${c.link}` : ''}`);
  for (const l of logs) {
    parts.push('', `--- gh run view ${l.runId} --log-failed (last ${FAILED_LOG_LINES} lines) ---`, tailLines(l.text, FAILED_LOG_LINES));
  }
  let out = parts.join('\n');
  if (out.length > FAILED_BLOCK_MAX_CHARS) out = `[truncated]\n${out.slice(out.length - FAILED_BLOCK_MAX_CHARS)}`;
  return out;
}
