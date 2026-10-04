// Pure helper: validation of .autopilot/plans/<unit>.json written by the plan session.
//
// {"unit":"07","branch":"phase1/p07-...","pr":123,"gate":null|"month-1".."month-5",
//  "steps":[{"id":"WF-023","ticket":"WF-023","title":"...","ui":false,"kit":null|"...",
//            "migration":false,"owner_pending":["..."]}, ...]}

import { branchPrefixFor, expectedBranch, unitKind } from './task.mjs';

const STEP_ID_RE = /^[A-Za-z0-9][A-Za-z0-9._-]*$/;
const GATE_RE = /^month-[1-5]$/;

/**
 * @param obj parsed JSON
 * @param opts {unit, slug?, promptTickets?: [{ticket}]}
 * @returns {ok, errors, warnings}
 */
export function validatePlan(obj, { unit, slug, promptTickets = [] }) {
  const errors = [];
  const warnings = [];
  if (!obj || typeof obj !== 'object' || Array.isArray(obj)) {
    return { ok: false, errors: ['plan is not a JSON object'], warnings };
  }
  if (String(obj.unit) !== unit) errors.push(`unit is "${obj.unit}", expected "${unit}"`);

  const kind = unitKind(unit);
  const prefix = branchPrefixFor(unit);
  if (typeof obj.branch !== 'string' || obj.branch.trim() === '') {
    errors.push('branch is missing');
  } else if (prefix && !obj.branch.startsWith(prefix)) {
    errors.push(`branch "${obj.branch}" must start with "${prefix}"`);
  } else if (kind === 'final' && obj.branch !== 'phase1/final') {
    errors.push(`branch must be "phase1/final" for FINAL, got "${obj.branch}"`);
  } else if (slug) {
    const want = expectedBranch(unit, slug);
    if (want && obj.branch !== want) warnings.push(`branch "${obj.branch}" differs from the expected "${want}"`);
  }

  if (!Number.isInteger(obj.pr) || obj.pr <= 0) errors.push('pr must be a positive integer (the draft PR number)');

  if (obj.gate !== null && obj.gate !== undefined && !(typeof obj.gate === 'string' && GATE_RE.test(obj.gate))) {
    errors.push(`gate must be null or month-1..month-5, got ${JSON.stringify(obj.gate)}`);
  }

  if (!Array.isArray(obj.steps)) {
    errors.push('steps must be an array');
  } else {
    if (obj.steps.length === 0 && kind !== 'final') errors.push('steps is empty (only FINAL may have zero steps)');
    const ids = new Set();
    obj.steps.forEach((s, i) => {
      const at = `steps[${i}]`;
      if (!s || typeof s !== 'object') return errors.push(`${at} is not an object`);
      if (typeof s.id !== 'string' || !STEP_ID_RE.test(s.id)) errors.push(`${at}.id "${s.id}" must match ${STEP_ID_RE}`);
      else if (ids.has(s.id)) errors.push(`duplicate step id ${s.id}`);
      else ids.add(s.id);
      if (typeof s.ticket !== 'string' || s.ticket === '') errors.push(`${at}.ticket is missing`);
      if (typeof s.title !== 'string' || s.title.trim() === '') errors.push(`${at}.title is missing`);
      if (s.ui !== undefined && typeof s.ui !== 'boolean') errors.push(`${at}.ui must be a boolean`);
      if (s.migration !== undefined && typeof s.migration !== 'boolean') errors.push(`${at}.migration must be a boolean`);
      if (s.owner_pending !== undefined && !Array.isArray(s.owner_pending)) errors.push(`${at}.owner_pending must be an array`);
    });

    // Every ticket of the prompt's table must be covered by a step: WF-nnn for a build prompt,
    // Sn.k for a setup prompt. FINAL has no table.
    if (kind === 'build' || kind === 'setup') {
      const wanted = promptTickets.map((t) => t.ticket).filter((t) => (kind === 'build' ? /^WF-\d+$/.test(t) : /^S[1-9]\d*\.\d+$/.test(t)));
      const covered = new Set(obj.steps.filter((s) => s && typeof s === 'object').map((s) => s.ticket));
      const missing = wanted.filter((t) => !covered.has(t));
      if (missing.length) errors.push(`plan does not cover ticket(s): ${missing.join(', ')}`);
      const extra = [...covered].filter((t) => wanted.length && !wanted.includes(t));
      if (extra.length) warnings.push(`plan has step ticket(s) not in the prompt table: ${extra.join(', ')}`);
    }
  }
  return { ok: errors.length === 0, errors, warnings };
}
