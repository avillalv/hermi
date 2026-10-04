#!/usr/bin/env node
// Autopilot status: one screen, no big files loaded. Always exits 0.
//   node scripts/autopilot/status.mjs

import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { parseLine } from './lib/stream.mjs';
import { parseProgress, progressCounts, sortUnits } from './lib/progress.mjs';
import { hasLabel } from './lib/ci.mjs';
import { FILES, PATHS, readLock, ROOT } from './driver/ctx.mjs';
import { gh, showFile } from './driver/git.mjs';
import { pidAlive, readJson, readTail, resolveGh } from './driver/sys.mjs';

const TAIL_BYTES = 256 * 1024;
const LAST_LINES = 15;

/** The last assistant text lines of a stream-json log (main thread only), from its tail. */
export function lastAssistantLines(tailText, truncatedStart, n = LAST_LINES) {
  const lines = tailText.split('\n');
  if (truncatedStart) lines.shift(); // the first line is cut
  const out = [];
  for (const raw of lines) {
    const o = parseLine(raw);
    if (!o || o.type !== 'assistant' || o.parent_tool_use_id) continue;
    for (const b of o.message?.content ?? []) {
      if (b.type !== 'text') continue;
      for (const l of String(b.text).split(/\r?\n/)) if (l.trim()) out.push(l.trim().slice(0, 200));
    }
  }
  return out.slice(-n);
}

function newestLog() {
  try {
    const files = fs.readdirSync(PATHS.logs).filter((f) => f.endsWith('.jsonl')).map((f) => ({ f, t: fs.statSync(path.join(PATHS.logs, f)).mtimeMs }));
    files.sort((a, b) => b.t - a.t);
    return files[0] ? { file: path.join(PATHS.logs, files[0].f), name: files[0].f, mtime: files[0].t } : null;
  } catch {
    return null;
  }
}

export function main() {
  const state = readJson(PATHS.state, null);
  console.log('Hermi autopilot status');
  console.log('----------------------');

  const lock = readLock();
  console.log(`driver:   ${lock && pidAlive(lock.pid) ? `running (pid ${lock.pid}, since ${lock.startedAt}${lock.childPid ? `, session pid ${lock.childPid}` : ''})` : 'not running'}`);

  if (!state) {
    console.log('state:    none yet (.autopilot/state.json does not exist)');
  } else {
    const approved = Object.keys(state.approvals ?? {}).length;
    const last = (state.sessions ?? []).at(-1);
    console.log(`unit:     ${state.unit ?? '-'}   phase: ${state.phase}   branch: ${state.branch ?? '-'}   PR: ${state.pr ? `#${state.pr}` : '-'}`);
    console.log(`          approvals: ${approved}, ci-fix attempts: ${state.ciFixAttempts ?? 0}, sessions: ${(state.sessions ?? []).length}`);
    if (last) console.log(`last:     ${last.mode}${last.step ? ` ${last.step}` : ''} ${last.result ?? 'running'} (started ${last.startedAt})`);
    if (state.pause) console.log(`PAUSED:   sleeping until ${state.pause.until} (${state.pause.reason})`);
    if (state.stopped) console.log(`STOPPED:  ${state.stopped.reason}\n          ${state.stopped.ownerAction}`);
  }

  const stop = readJson(PATHS.stop, null);
  if (stop) console.log(`\nstop.json: unit ${stop.unit}: ${stop.reason}\n           ${stop.ownerAction}`);

  let md = showFile('main', FILES.progress);
  if (!md) {
    try {
      md = fs.readFileSync(path.join(ROOT, FILES.progress), 'utf8');
    } catch {
      md = null;
    }
  }
  if (md) {
    const rows = parseProgress(md);
    const c = progressCounts(rows);
    const cur = sortUnits(rows).find((r) => r.status.kind !== 'done');
    console.log(`\nprogress: ${c.done} of ${c.total} prompts Done on main${cur ? `; current row ${cur.id} "${cur.title}": ${cur.statusText}` : '; all rows Done'}`);
  } else {
    console.log('\nprogress: PROGRESS.md not readable');
  }

  const ghExe = resolveGh();
  if (ghExe) {
    const r = gh({ ghExe, extraPathDirs: [], ghPre: [] }, ['pr', 'list', '--json', 'number,title,isDraft,labels,headRefName', '--limit', '20']);
    try {
      const prs = JSON.parse(r.stdout);
      console.log(`\nopen PRs: ${prs.length}`);
      for (const p of prs) console.log(`  #${p.number} ${p.isDraft ? '[draft] ' : ''}${hasLabel(p.labels, 'autopilot:stopped') ? '[STOPPED] ' : ''}${p.headRefName}: ${p.title}`);
    } catch {
      console.log(`\nopen PRs: not available (${(r.stderr || r.stdout).trim().split('\n')[0] || 'gh failed'})`);
    }
  } else {
    console.log('\nopen PRs: gh is not installed');
  }

  const log = newestLog();
  if (log) {
    const { text, truncatedStart, size } = readTail(log.file, TAIL_BYTES);
    console.log(`\nnewest log: ${log.name} (${Math.round(size / 1024)} KB, modified ${new Date(log.mtime).toLocaleString()})`);
    const lines = lastAssistantLines(text, truncatedStart);
    if (lines.length === 0) console.log('  (no assistant text in the last 256 KB)');
    for (const l of lines) console.log(`  | ${l}`);
  } else {
    console.log('\nnewest log: none');
  }
}

if (process.argv[1] && pathToFileURL(path.resolve(process.argv[1])).href === import.meta.url) {
  try {
    main();
  } catch (e) {
    console.log(`status could not finish: ${e.message}`);
  }
  process.exit(0);
}
