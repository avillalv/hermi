// Spec lint for the Hermi repo. Node 22, standard library only.
//
//   node scripts/spec-lint.mjs            run checks 1 to 3
//   node scripts/spec-lint.mjs --links    also run check 4 (opt in: links can dangle while the spec is edited)
//
// 1. No em or en dash (U+2014, U+2013) in text files. findings/ is out of scope by design.
// 2. Every roadmap ticket is in exactly one build prompt table, and no table lists a stranger.
// 3. prompts/README.md, prompts/PROGRESS.md and each prompt file agree on that prompt's tickets.
// 4. Relative markdown links point at something that exists.
//
// Exit 0 when clean. Exit 1 with one "path:line: message" per problem.
import { existsSync, readdirSync, readFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const ROADMAP = 'app-buildout/phase-1-launch/09-build-roadmap.md';
const PROMPTS = 'app-buildout/prompts';
const FROZEN = 'app-buildout/reference-full-spec/'; // superseded spec: dash check covers it, link check skips it
const DASH_DIRS = ['app-buildout', 'knowledge', '.claude', 'scripts']; // plus CLAUDE.md and root *.md
const LINK_DIRS = ['app-buildout', 'knowledge', '.claude'];
const TEXT_FILE = /\.(svg|md|html|css|py|mjs|js|json|ya?ml|txt)$/;
const TICKET = /\b(?:WF-\d+|S\d\.\d+)\b/g; // WF-001 is a roadmap ticket, S1.1 a setup prompt ticket
const EM = String.fromCharCode(0x2014); // built from code points so this file passes its own check
const EN = String.fromCharCode(0x2013);
const DASHES = new RegExp(`[${EN}${EM}]`, 'g');
// Local-only paths. Keep in step with .gitignore so a scratch file cannot fail a local run.
const SKIP_NAMES = new Set(['.git', 'node_modules', '__pycache__']);
const SKIP_PATHS = new Set(['.claude/handoff', '.claude/settings.local.json']);

const args = process.argv.slice(2);
if (args.some((a) => a !== '--links')) {
  console.error('usage: node scripts/spec-lint.mjs [--links]');
  process.exit(2);
}

const problems = [];
const bad = (file, line, msg) => problems.push(`${file}:${line}: ${msg}`);
const read = (file) => readFileSync(join(ROOT, file), 'utf8').split(/\r?\n/);
const cells = (line) => line.split('|').slice(1, -1).map((c) => c.trim());
const present = (dirs) => dirs.filter((d) => existsSync(join(ROOT, d)));

/** Every file under dir as a repo-relative path with forward slashes, sorted. */
function walk(dir, out = []) {
  for (const e of readdirSync(join(ROOT, dir), { withFileTypes: true })) {
    const path = `${dir}/${e.name}`;
    if (SKIP_NAMES.has(e.name) || SKIP_PATHS.has(path)) continue;
    if (e.isDirectory()) walk(path, out);
    else out.push(path);
  }
  return out.sort();
}

// 1. Dashes ------------------------------------------------------------------------------
function checkDashes() {
  const rootDocs = readdirSync(ROOT).filter((f) => f.endsWith('.md'));
  for (const file of [...rootDocs, ...present(DASH_DIRS).flatMap((d) => walk(d))]) {
    if (!TEXT_FILE.test(file)) continue;
    read(file).forEach((text, i) => {
      const hits = text.match(DASHES);
      if (!hits) return;
      const what = [...new Set(hits)]
        .map((c) => (c === EM ? 'U+2014 em dash' : 'U+2013 en dash'))
        .join(' and ');
      bad(file, i + 1, file.startsWith(FROZEN)
        ? `${what} in the frozen reference-full-spec, which is never edited: find out how it got there`
        : `${what}, use a comma, a period or "to"`);
    });
  }
}

// 2 and 3. Tickets -----------------------------------------------------------------------
/** The "| Ticket | Title |" table of a prompt file: { line of header, rows: [{ id, line }] }, or null. */
function promptTable(lines) {
  const head = lines.findIndex((l) => /^\|\s*Ticket\s*\|\s*Title\s*\|/.test(l));
  if (head < 0) return null;
  const rows = [];
  for (let i = head + 1; i < lines.length && lines[i].startsWith('|'); i++) {
    const id = cells(lines[i])[0].match(TICKET)?.[0]; // the |---|---| row has none
    if (id) rows.push({ id, line: i + 1 });
  }
  return { line: head + 1, rows };
}

/** Rows like "| 04 | [title](04-x.md) | WF-011, WF-012 | ... |" as Map(NN -> { ids, line }). */
function indexRows(file) {
  const rows = new Map();
  read(file).forEach((text, i) => {
    if (!text.startsWith('|')) return;
    const [nn, , tickets = ''] = cells(text);
    if (!/^(\d\d|S\d)$/.test(nn)) return;
    if (rows.has(nn)) bad(file, i + 1, `second row for prompt ${nn}`);
    rows.set(nn, { ids: new Set(tickets.match(TICKET)), line: i + 1 });
  });
  return rows;
}

function checkTickets() {
  const road = new Map(); // WF id -> heading line
  read(ROADMAP).forEach((text, i) => {
    const id = /^#{1,6}\s+(WF-\d+)\b/.exec(text)?.[1];
    if (!id) return;
    if (road.has(id)) bad(ROADMAP, i + 1, `${id} is defined twice (first at line ${road.get(id)})`);
    else road.set(id, i + 1);
  });
  if (!road.size) bad(ROADMAP, 1, 'no "#### WF-NNN" ticket headings found, so this parser needs updating');

  const prompts = new Map(); // NN -> { file, line, ids }
  const first = new Map(); // ticket id -> "file:line" of its first prompt table row
  for (const name of readdirSync(join(ROOT, PROMPTS)).sort()) {
    const nn = /^(\d\d|S\d)-.*\.md$/.exec(name)?.[1];
    const file = `${PROMPTS}/${name}`;
    const table = nn && promptTable(read(file)); // 00-orchestrator.md has no ticket table
    if (!table) continue;
    if (prompts.has(nn)) bad(file, table.line, `second prompt file numbered ${nn}`);
    for (const { id, line } of table.rows) {
      if (first.has(id)) bad(file, line, `${id} is already in ${first.get(id)}, a ticket belongs to one prompt`);
      else first.set(id, `${file}:${line}`);
      if (id.startsWith('WF-') && !road.has(id)) bad(file, line, `${id} is not a ticket in ${ROADMAP}`);
    }
    prompts.set(nn, { file, line: table.line, ids: new Set(table.rows.map((r) => r.id)) });
  }
  for (const [id, line] of road) if (!first.has(id)) bad(ROADMAP, line, `${id} is in no build prompt table`);

  const index = new Map(['README.md', 'PROGRESS.md'].map((n) => [n, indexRows(`${PROMPTS}/${n}`)]));
  const numbers = new Set([...prompts.keys(), ...[...index.values()].flatMap((rows) => [...rows.keys()])]);
  for (const nn of [...numbers].sort()) {
    const p = prompts.get(nn);
    for (const [name, rows] of index) {
      const row = rows.get(nn);
      if (!p) {
        if (row) bad(`${PROMPTS}/${name}`, row.line, `row ${nn} has no prompt file with a ticket table`);
      } else if (!row) {
        bad(p.file, p.line, `prompt ${nn} has no row in ${name}`);
      } else {
        const missing = [...p.ids].filter((id) => !row.ids.has(id));
        const extra = [...row.ids].filter((id) => !p.ids.has(id));
        if (missing.length || extra.length) {
          bad(`${PROMPTS}/${name}`, row.line, `prompt ${nn} tickets differ from ${p.file}`
            + (missing.length ? `, missing ${missing.join(' ')}` : '')
            + (extra.length ? `, extra ${extra.join(' ')}` : ''));
        }
      }
    }
  }
  return { tickets: road.size, prompts: prompts.size };
}

// 4. Links -------------------------------------------------------------------------------
function checkLinks() {
  const docs = present(LINK_DIRS).flatMap((d) => walk(d)).filter((f) => f.endsWith('.md') && !f.startsWith(FROZEN));
  for (const file of docs) {
    let fence = null; // the opening ``` or ~~~ while inside a fenced code block
    read(file).forEach((raw, i) => {
      const mark = /^\s*(`{3,}|~{3,})/.exec(raw)?.[1];
      if (fence) {
        if (mark && mark[0] === fence[0] && mark.length >= fence.length && raw.trim() === mark) fence = null;
        return;
      }
      if (mark) {
        fence = mark;
        return;
      }
      for (const m of raw.replace(/`[^`]*`/g, '').matchAll(/\[[^\]]*\]\(([^)\s]+)[^)]*\)/g)) {
        const path = m[1].replace(/[#?].*$/, ''); // the anchor is not checked, only the file
        if (!path || /^([a-z][a-z0-9+.-]*:|\/\/)/i.test(path)) continue; // pure #anchor, http(s), mailto
        const target = path.startsWith('/') ? join(ROOT, path) : resolve(ROOT, dirname(file), path);
        if (!existsSync(target)) bad(file, i + 1, `broken link to ${m[1]}`);
      }
    });
  }
}

checkDashes();
const { tickets, prompts } = checkTickets();
if (args.includes('--links')) checkLinks();

if (problems.length) {
  console.log(problems.join('\n'));
  console.log(`spec-lint: ${problems.length} problem${problems.length === 1 ? '' : 's'}`);
  process.exit(1);
}
console.log(`spec-lint: clean (${tickets} tickets in ${prompts} prompts)`);
