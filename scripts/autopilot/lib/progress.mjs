// Pure helpers: PROGRESS.md tables and next-unit selection.
//
// PROGRESS.md holds two tables with the columns `| # | Prompt | Tickets | Status |`:
// "## Setup prompts" (rows S1..S3) above "## Prompts" (rows 01..28). Either may be missing.
// Rows are recognised by their first cell, so headings and other tables are ignored.

const ID_RE = /^(S[1-9]\d*|\d{2})$/;

/** Status text -> {kind, detail}. Kinds: not-started, in-progress, in-review, done, stopped, unknown. */
export function parseStatus(text) {
  const t = String(text).replace(/[*`_]/g, '').trim();
  let m;
  if (/^not started$/i.test(t)) return { kind: 'not-started', detail: '' };
  if ((m = /^in progress(?:\s*\((.*)\))?$/i.exec(t))) return { kind: 'in-progress', detail: (m[1] ?? '').trim() };
  if ((m = /^in review(?:\s*\((.*)\))?$/i.exec(t))) return { kind: 'in-review', detail: (m[1] ?? '').trim() };
  if ((m = /^done\b\s*(?:\((.*)\))?/i.exec(t))) return { kind: 'done', detail: (m[1] ?? '').trim() };
  if ((m = /^stopped\b\s*(?:\((.*)\))?/i.exec(t))) return { kind: 'stopped', detail: (m[1] ?? '').trim() };
  return { kind: 'unknown', detail: t };
}

/** Rows of every unit table in the file, in file order. */
export function parseProgress(md) {
  const rows = [];
  const seen = new Set();
  for (const raw of String(md).split(/\r?\n/)) {
    const line = raw.trim();
    if (!line.startsWith('|')) continue;
    const cells = line.split('|').slice(1, -1).map((c) => c.trim());
    if (cells.length < 4) continue;
    const id = cells[0].replace(/[*`]/g, '').trim();
    if (!ID_RE.test(id) || seen.has(id)) continue;
    seen.add(id);
    const link = /^\[([^\]]*)\]\(([^)]*)\)$/.exec(cells[1]);
    const statusText = cells[cells.length - 1];
    rows.push({
      id,
      kind: id.startsWith('S') ? 'setup' : 'build',
      title: link ? link[1] : cells[1],
      file: link ? link[2] : null,
      tickets: cells[2] ? cells[2].split(/[,\s]+/).filter(Boolean) : [],
      statusText,
      status: parseStatus(statusText),
    });
  }
  return rows;
}

const orderKey = (row) => (row.kind === 'setup' ? 0 : 1000) + Number(row.id.replace(/^S/, ''));

/** Setup rows (S1..S3) first, then 01..28, regardless of file order. */
export function sortUnits(rows) {
  return [...rows].sort((a, b) => orderKey(a) - orderKey(b));
}

export function rowForUnit(rows, unitId) {
  return rows.find((r) => r.id === unitId) ?? null;
}

export function progressCounts(rows) {
  return { done: rows.filter((r) => r.status.kind === 'done').length, total: rows.length };
}

/** Done (#<pr>) for exactly this PR number. */
export function isDoneForPr(status, pr) {
  if (status.kind !== 'done') return false;
  const m = /\d+/.exec(status.detail);
  return m !== null && Number(m[0]) === Number(pr);
}

/**
 * The first row that is not Done decides:
 *   Stopped -> {action: 'stopped'}; anything else -> {action: 'run', unit: row.id}.
 * When every row is Done: run FINAL until docs/gates/phase-1-complete.md exists on main,
 * then {action: 'complete'}.
 */
export function selectNextUnit(rows, { finalGateExists }) {
  if (rows.length === 0) return { action: 'error', reason: 'PROGRESS.md has no unit rows (expected S1..S3 and 01..28)' };
  for (const row of sortUnits(rows)) {
    if (row.status.kind === 'done') continue;
    if (row.status.kind === 'stopped') {
      return { action: 'stopped', unit: row.id, reason: row.status.detail || 'no reason recorded' };
    }
    return { action: 'run', unit: row.id, row };
  }
  return finalGateExists ? { action: 'complete' } : { action: 'run', unit: 'FINAL', row: null };
}
