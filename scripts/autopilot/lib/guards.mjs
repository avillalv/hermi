// Pure decision logic for the three PreToolUse hooks (hooks/agent-guard.mjs, hooks/bash-guard.mjs,
// hooks/file-guard.mjs). checkAgent, checkBash and checkFileTool return a one-line reason to BLOCK,
// or null to allow.
//
// The bash guard is a best-effort tripwire for the mistakes a model is likely to make, not a
// sandbox: it reads the command text only. The permission deny rules, the auto-mode classifier and
// the driver's post-session checks sit behind it.

import path from 'node:path';

// ---------------------------------------------------------------------------------------------
// Agent guard
// ---------------------------------------------------------------------------------------------

const isSonnet = (m) => m === 'sonnet' || /^claude-sonnet/i.test(m);
const isOpus = (m) => m === 'opus' || /^claude-opus/i.test(m);

export const AGENT_HELP =
  'allowed agents: sonnet-researcher and sonnet-coder (model sonnet or unset), opus-reviewer and opus-judge (model opus or unset), general-purpose and Explore (model "sonnet" only)';

/** toolInput of the Agent (Task) tool: {subagent_type?, model?, ...}. */
export function checkAgent(toolInput = {}) {
  // A worktree or another working directory moves the agent out of the checkout the other guards watch.
  if (toolInput.isolation || toolInput.cwd) return 'agent-guard: Agent calls may not set isolation or cwd; the agent runs in this checkout';
  // A headless session that ends its turn while a background agent runs exits and kills that agent, so every call must block.
  if (toolInput.run_in_background !== false) return 'agent-guard: Agent calls must pass run_in_background: false; a headless session that ends its turn while a background agent runs exits and kills that agent';
  const type = toolInput.subagent_type || 'general-purpose';
  const model = toolInput.model ? String(toolInput.model) : '';
  switch (type) {
    case 'sonnet-researcher':
    case 'sonnet-coder':
      if (model && !isSonnet(model)) return `agent-guard: ${type} must run on Sonnet, not "${model}"; omit model or pass "sonnet"`;
      return null;
    case 'opus-reviewer':
    case 'opus-judge':
      if (model && !isOpus(model)) return `agent-guard: ${type} must run on Opus, not "${model}"; omit model or pass "opus"`;
      return null;
    case 'general-purpose':
    case 'Explore':
      if (!isSonnet(model)) return `agent-guard: ${type} needs model "sonnet" explicitly (got ${model ? `"${model}"` : 'none'}); ${AGENT_HELP}`;
      return null;
    default:
      return `agent-guard: agent "${type}" is not allowed; ${AGENT_HELP}`;
  }
}

// ---------------------------------------------------------------------------------------------
// Shell tokenizer
// ---------------------------------------------------------------------------------------------

/**
 * Split a command into simple commands. Understands quotes, ; && || | & newlines, > >> redirections,
 * heredocs (bodies are removed from `stripped`), $(...) and backtick substitutions (parsed as extra
 * commands). Backslashes are literal so Windows paths survive.
 * Returns {segments: [{words, redirects}], stripped}.
 */
export function parseShell(command, depth = 0) {
  const s = String(command);
  const segments = [];
  let cur = { words: [], redirects: [], inputs: [] };
  let word = null;
  const removed = []; // [start, end) ranges of heredoc bodies
  const heredocs = []; // pending {tag, dash}
  let i = 0;

  const pushWord = () => {
    if (word !== null) cur.words.push(word);
    word = null;
  };
  const pushSeg = () => {
    pushWord();
    if (cur.words.length || cur.redirects.length) segments.push(cur);
    cur = { words: [], redirects: [], inputs: [] };
  };
  const readQuoted = (start) => {
    // s[start] is ' or "; returns {text, next}
    const q = s[start];
    if (q === "'") {
      const j = s.indexOf("'", start + 1);
      const end = j < 0 ? s.length : j;
      return { text: s.slice(start + 1, end), next: end + 1 };
    }
    let j = start + 1;
    let buf = '';
    while (j < s.length && s[j] !== '"') {
      if (s[j] === '\\' && (s[j + 1] === '"' || s[j + 1] === '\\')) {
        buf += s[j + 1];
        j += 2;
      } else {
        buf += s[j];
        j++;
      }
    }
    return { text: buf, next: j + 1 };
  };
  const readWordAt = (start) => {
    // a redirect target: skip spaces, read one word with quotes
    let j = start;
    while (j < s.length && (s[j] === ' ' || s[j] === '\t')) j++;
    let text = '';
    while (j < s.length && !/[\s;&|<>()]/.test(s[j])) {
      if (s[j] === "'" || s[j] === '"') {
        const q = readQuoted(j);
        text += q.text;
        j = q.next;
      } else {
        text += s[j++];
      }
    }
    return { text, next: j };
  };

  while (i < s.length) {
    const c = s[i];
    if (c === "'" || c === '"') {
      const q = readQuoted(i);
      // Substitutions run inside double quotes too: echo "$(git push origin main)".
      if (c === '"' && depth < 4) for (const inner of substitutions(q.text)) segments.push(...parseShell(inner, depth + 1).segments);
      word = (word ?? '') + q.text;
      i = q.next;
    } else if (c === '$' && s[i + 1] === '(' && depth < 4) {
      const p = parenInner(s, i + 1);
      const sub = parseShell(p.inner, depth + 1);
      segments.push(...sub.segments);
      word = (word ?? '') + `$(${p.inner})`;
      i = p.next;
    } else if (c === '`' && depth < 4) {
      const j = s.indexOf('`', i + 1);
      const end = j < 0 ? s.length : j;
      const inner = s.slice(i + 1, end);
      segments.push(...parseShell(inner, depth + 1).segments);
      word = (word ?? '') + `\`${inner}\``;
      i = end + 1;
    } else if (c === '\n') {
      pushSeg();
      i++;
      // heredoc bodies start on the next line
      while (heredocs.length) {
        const h = heredocs.shift();
        const bodyStart = i;
        for (;;) {
          if (i >= s.length) break;
          let eol = s.indexOf('\n', i);
          if (eol < 0) eol = s.length;
          const line = s.slice(i, eol).replace(/\r$/, '');
          i = Math.min(eol + 1, s.length);
          if ((h.dash ? line.trim() : line) === h.tag) break;
        }
        removed.push([bodyStart, i]);
      }
    } else if (c === ';' || c === '(' || c === ')') {
      pushSeg();
      i++;
    } else if (c === '&' || c === '|') {
      if (c === '&' && s[i + 1] === '>') {
        // &> file
        pushWord();
        const t = readWordAt(i + (s[i + 2] === '>' ? 3 : 2));
        if (t.text) cur.redirects.push(t.text);
        i = t.next;
      } else {
        pushSeg();
        i += s[i + 1] === c || (c === '|' && s[i + 1] === '&') ? 2 : 1;
      }
    } else if (c === '>' || c === '<') {
      if (c === '<' && s[i + 1] === '<' && s[i + 2] !== '<') {
        // heredoc
        pushWord();
        let j = i + 2;
        const dash = s[j] === '-';
        if (dash) j++;
        while (s[j] === ' ' || s[j] === '\t') j++;
        const t = readWordAt(j);
        heredocs.push({ tag: t.text, dash });
        i = t.next;
      } else if (c === '<') {
        pushWord();
        const here = s[i + 1] === '<'; // <<< is a here-string: text, not a file
        i += here ? 3 : 1;
        const t = readWordAt(i);
        if (!here && t.text) cur.inputs.push(t.text);
        i = t.next;
      } else {
        // > or >> or >| or >&
        if (word !== null && /^\d+$/.test(word)) word = null; // 2> : the digits are the fd
        else pushWord();
        let j = i + 1;
        if (s[j] === '>') j++;
        if (s[j] === '|') j++;
        if (s[j] === '&') {
          // >&2 or >&- : fd duplication, no file
          const t = readWordAt(j + 1);
          i = t.next;
          continue;
        }
        const t = readWordAt(j);
        if (t.text) cur.redirects.push(t.text);
        i = t.next;
      }
    } else if (c === '\\' && s[i + 1] === '\n') {
      i += 2; // line continuation
    } else if (c === '#' && word === null) {
      while (i < s.length && s[i] !== '\n') i++;
    } else if (/\s/.test(c)) {
      pushWord();
      i++;
    } else {
      word = (word ?? '') + c;
      i++;
    }
  }
  pushSeg();

  let stripped = '';
  let last = 0;
  for (const [a, b] of removed) {
    stripped += s.slice(last, a);
    last = b;
  }
  stripped += s.slice(last);
  return { segments, stripped, heredocs: removed.map(([a, b]) => s.slice(a, b)) };
}

/** s[start] is the '(' after a '$': the text inside the matching parentheses, and where it ends. */
function parenInner(s, start) {
  let d = 0;
  let j = start;
  for (; j < s.length; j++) {
    if (s[j] === '(') d++;
    else if (s[j] === ')' && --d === 0) break;
  }
  return { inner: s.slice(start + 1, j), next: j + 1 };
}

/** The $(...) and backtick bodies inside a double-quoted string. */
function substitutions(text) {
  const out = [];
  for (let i = 0; i < text.length; i++) {
    if (text[i] === '$' && text[i + 1] === '(') {
      const p = parenInner(text, i + 1);
      out.push(p.inner);
      i = p.next - 1;
    } else if (text[i] === '`') {
      const j = text.indexOf('`', i + 1);
      const end = j < 0 ? text.length : j;
      out.push(text.slice(i + 1, end));
      i = end;
    }
  }
  return out;
}

// ---------------------------------------------------------------------------------------------
// Command normalisation
// ---------------------------------------------------------------------------------------------

const ASSIGN_RE = /^[A-Za-z_][A-Za-z0-9_]*=/;
const WRAPPERS = new Set(['sudo', 'command', 'builtin', 'exec', 'time', 'nohup', 'nice', 'env', '&', 'call', 'stdbuf']);

const baseCmd = (w) => String(w ?? '').replace(/^.*[\\/]/, '').replace(/\.exe$/i, '').toLowerCase();

/**
 * Strip env assignments and wrappers (sudo, env, timeout, xargs ...). Returns
 * {cmd, word, args, viaXargs, assigns} where cmd is the lower-case base name of the real command,
 * word is that command as written, and assigns are the NAME=value words that preceded it.
 */
export function unwrap(words) {
  let w = [...words];
  let viaXargs = false;
  const assigns = [];
  for (let guard = 0; guard < 12 && w.length; guard++) {
    if (ASSIGN_RE.test(w[0])) {
      assigns.push(w.shift());
      continue;
    }
    const b = baseCmd(w[0]);
    if (WRAPPERS.has(b)) {
      w.shift();
      while (w.length && (w[0].startsWith('-') || ASSIGN_RE.test(w[0]))) w.shift();
      continue;
    }
    if (b === 'timeout') {
      w.shift();
      while (w.length && w[0].startsWith('-')) w.shift();
      w.shift(); // the duration
      continue;
    }
    if (b === 'xargs') {
      viaXargs = true;
      w.shift();
      while (w.length && w[0].startsWith('-')) w.shift();
      continue;
    }
    break;
  }
  return { cmd: baseCmd(w[0]), word: w[0] ?? '', args: w.slice(1), viaXargs, assigns };
}

/**
 * Inline scripts: bash -c "...", pwsh -Command "...", cmd /c ... -> {text, idx} (the script and the
 * indexes of the args that hold it), else null.
 */
function inlineScript(cmd, args) {
  const tail = (i) => ({ text: args.slice(i + 1).join(' '), idx: new Set(args.slice(i + 1).map((_, k) => i + 1 + k)) });
  if (['bash', 'sh', 'zsh', 'dash', 'ash', 'ksh'].includes(cmd)) {
    const i = args.findIndex((a) => /^-[a-zA-Z]*c[a-zA-Z]*$/.test(a));
    return i >= 0 && args[i + 1] != null ? { text: args[i + 1], idx: new Set([i + 1]) } : null;
  }
  if (['pwsh', 'powershell'].includes(cmd)) {
    const i = args.findIndex((a) => a.length > 1 && a.startsWith('-') && 'command'.startsWith(a.slice(1).toLowerCase())); // -c, -com, -Command
    return i >= 0 ? tail(i) : null;
  }
  if (cmd === 'cmd') {
    const i = args.findIndex((a) => /^\/[ck]$/i.test(a));
    return i >= 0 ? tail(i) : null;
  }
  return null;
}

// ---------------------------------------------------------------------------------------------
// Rules
// ---------------------------------------------------------------------------------------------

const PROTECTED_BRANCHES = new Set(['main', 'master']);
const norm = (p) => String(p ?? '').replace(/\\/g, '/');

// A word the shell rewrites before running it (variable, substitution, brace expansion) cannot be
// checked, so it is refused where it matters: the command word, git and gh subcommands, push refspecs.
const DYNAMIC_RE = /[$`]|\{[^}]*(?:,|\.\.)[^}]*\}/;
const isDynamic = (w) => DYNAMIC_RE.test(String(w ?? ''));

function gitSubcommand(args) {
  let i = 0;
  const config = []; // values of -c and --config-env
  while (i < args.length) {
    const a = args[i];
    if (a === '-c' || a === '--config-env') {
      config.push(args[i + 1] ?? '');
      i += 2;
    } else if (a.startsWith('--config-env=')) {
      config.push(a.slice('--config-env='.length));
      i += 1;
    } else if (['-C', '--git-dir', '--work-tree', '--namespace', '--exec-path'].includes(a)) i += 2;
    else if (a.startsWith('-')) i += 1;
    else break;
  }
  return { sub: args[i], rest: args.slice(i + 1), config };
}

function checkGitPush(rest, ctx) {
  const flags = [];
  const pos = [];
  for (let i = 0; i < rest.length; i++) {
    const a = rest[i];
    if (a === '--') {
      pos.push(...rest.slice(i + 1));
      break;
    }
    if (a.startsWith('--')) {
      const name = a.split('=')[0];
      flags.push(name);
      if (['--push-option', '--repo', '--receive-pack', '--exec'].includes(name) && !a.includes('=')) i++;
    } else if (a.startsWith('-') && a.length > 1) {
      flags.push(a);
      if (a === '-o') i++;
    } else {
      pos.push(a);
    }
  }
  const forced = flags.some((f) => ['--force', '--force-with-lease', '--force-if-includes'].includes(f) || /^-[a-zA-Z]*f[a-zA-Z]*$/.test(f));
  if (forced) return 'bash-guard: force-pushing is not allowed';
  if (flags.includes('--mirror')) return 'bash-guard: git push --mirror is not allowed';
  if (flags.includes('--all')) return 'bash-guard: git push --all is not allowed (it would include main); push the branch by name';
  if (flags.some((f) => f === '--delete' || /^-[a-zA-Z]*d[a-zA-Z]*$/.test(f))) return 'bash-guard: git push --delete is not allowed; remote branches are never deleted from a session';
  const refspecs = pos.slice(1);
  const current = () => (ctx.currentBranch ? ctx.currentBranch() : null);
  if (refspecs.length === 0) {
    const b = current();
    if (b && PROTECTED_BRANCHES.has(b)) return `bash-guard: you are on ${b}; create a phase1/*, spec/* or fix/* branch before pushing`;
    return null;
  }
  for (const spec of refspecs) {
    if (isDynamic(spec)) return `bash-guard: the refspec "${spec}" uses a variable, substitution or brace expansion, so its destination cannot be checked; write the branch name out`;
    if (spec.startsWith('+')) return 'bash-guard: a + refspec forces the push and is not allowed';
    if (spec.startsWith(':')) return `bash-guard: the refspec "${spec}" deletes a remote branch and is not allowed`;
    if (spec.includes('*')) return `bash-guard: the refspec "${spec}" is a wildcard and could update main; name the branch`;
    let dest = spec.includes(':') ? spec.slice(spec.lastIndexOf(':') + 1) : spec;
    dest = dest.replace(/\/+/g, '/').replace(/\/\.(?=\/|$)/g, '').replace(/^refs\//, '').replace(/^heads\//, '');
    if (dest === 'HEAD' || dest === '@' || dest === '') {
      const b = current();
      if (b && PROTECTED_BRANCHES.has(b)) return `bash-guard: HEAD is ${b}; pushing to ${b} is not allowed`;
      continue;
    }
    if (PROTECTED_BRANCHES.has(dest)) return `bash-guard: pushing to ${dest} is not allowed; the driver merges pull requests`;
  }
  return null;
}

const GIT_CONFIG_READ = new Set(['--get', '--get-all', '--get-regexp', '--get-urlmatch', '--list', '-l']);

function checkGit(args, ctx) {
  const { sub, rest, config } = gitSubcommand(args);
  if (isDynamic(sub)) return `bash-guard: the git subcommand "${sub}" uses a variable or substitution and cannot be checked`;
  if (config.some((c) => /^remote\./i.test(c))) return 'bash-guard: git -c remote.* can send a push to main and is not allowed';
  if (sub === 'config' && rest.some((a) => /^remote\./i.test(a)) && !rest.some((a) => GIT_CONFIG_READ.has(a))) {
    return 'bash-guard: changing a git remote setting (remote.*) can send a push to main and is not allowed';
  }
  if (sub === 'filter-branch' || sub === 'filter-repo') return `bash-guard: git ${sub} rewrites history and is not allowed`;
  if (sub === 'clean' && rest.some((a) => /^-[a-zA-Z]*[xX][a-zA-Z]*$/.test(a))) return 'bash-guard: git clean -x or -X deletes ignored files (.env, node_modules, .autopilot) and is not allowed';
  if (sub === 'stash' && (rest[0] === 'clear' || rest[0] === 'drop')) return `bash-guard: git stash ${rest[0]} would delete work the driver saved for the owner and is not allowed`;
  if (sub === 'push') return checkGitPush(rest, ctx);
  return null;
}

/** The group and subcommand of a gh call (`pr merge`), skipping flags and the value of -R/--repo. */
function ghWords(args) {
  const pos = [];
  for (let i = 0; i < args.length && pos.length < 2; i++) {
    const a = args[i];
    if (a === '-R' || a === '--repo' || a === '--hostname') i++;
    else if (!a.startsWith('-')) pos.push(a);
  }
  return pos;
}

// gh api paths and GraphQL names that move a ref, change protection or rulesets, or merge.
const GH_API_FORBIDDEN = /(^|\/)git\/refs(\/|$)|\/branches\/[^/\s]+\/protection|(^|\/)rulesets\b|(^|\/)merges?($|[/?])|\b(?:mergePullRequest|enablePullRequestAutoMerge|mergeBranch|createRef|updateRefs?|deleteRef|(?:create|update|delete)BranchProtectionRule|(?:create|update|delete)RepositoryRuleset)\b/i;

function checkGh(args) {
  const [group, sub] = ghWords(args);
  if (isDynamic(group) || isDynamic(sub)) return 'bash-guard: a gh command word uses a variable or substitution and cannot be checked';
  if (group === 'alias') return 'bash-guard: gh alias can hide a merge behind another name and is not allowed';
  if (group === 'pr' && sub === 'merge') return 'bash-guard: gh pr merge is not allowed; the driver merges after CI and review';
  if (group === 'api') {
    const reason = 'bash-guard: refs, branch protection, rulesets and merges are never changed through gh api';
    if (args.some((a) => GH_API_FORBIDDEN.test(a))) return reason;
    // a GraphQL query read from a file cannot be checked
    if (args.includes('graphql') && args.some((a) => a === '--input' || a.startsWith('--input=') || /query=@/i.test(a))) return reason;
  }
  return null;
}

// --- SQL: DROP and TRUNCATE only on hermi* names ---

const hermiName = (n) => String(n ?? '').trim().toLowerCase().startsWith('hermi');
const firstName = (s) => /^\s*["'`]?([^\s"'`;(),]+)/.exec(s)?.[1] ?? '';
const DROP_NAMED_RE = /\bdrop\s+(database|role|user|group)\s+(?:if\s+exists\s+)?([^;]*)/gi;
const SQL_RISKY_RE = /\b(?:drop\s+(?!(?:database|role|user|group)\b)[a-z]+|truncate\b)/i;

/** The database a psql call connects to (-d, --dbname, a URI, a conninfo string or the first operand), or null. */
function psqlDatabase(args, assigns = []) {
  const withValue = new Set(['-h', '--host', '-p', '--port', '-U', '--username', '-c', '--command', '-f', '--file', '-v', '--set', '--variable', '-o', '--output', '-F', '--field-separator', '-R', '--record-separator', '-P', '--pset', '-T', '--table-attr', '-L', '--log-file']);
  const positional = [];
  let named = null;
  for (let i = 0; i < args.length; i++) {
    const a = args[i];
    if (a === '-d' || a === '--dbname') named = args[++i] ?? '';
    else if (a.startsWith('--dbname=')) named = a.slice('--dbname='.length);
    else if (/^-d./.test(a)) named = a.slice(2);
    else if (withValue.has(a)) i++;
    else if (!a.startsWith('-')) positional.push(a);
  }
  let raw = named ?? positional[0] ?? assigns.map((x) => /^PGDATABASE=(.*)$/.exec(x)?.[1]).find((x) => x !== undefined) ?? null;
  if (raw == null) return null;
  const uri = /^postgres(?:ql)?:\/\/[^/]*\/([^?]*)/i.exec(raw);
  if (uri) raw = uri[1];
  const info = /(?:^|\s)dbname=(\S+)/i.exec(raw);
  if (info) raw = info[1];
  return raw.replace(/^['"]|['"]$/g, '');
}

/**
 * sqlTexts: heredoc bodies and the words of the command (minus exempt ones). psqlCalls: [{args, assigns}].
 * DROP DATABASE and DROP ROLE name every target; any other DROP and TRUNCATE need every psql call to
 * connect to a hermi* database.
 */
function checkSql(sqlTexts, psqlCalls) {
  const text = sqlTexts.join('\n');
  for (const m of text.matchAll(DROP_NAMED_RE)) {
    const names = m[1].toLowerCase() === 'database' ? [firstName(m[2])] : m[2].split(',').map(firstName);
    const bad = names.find((n) => !hermiName(n));
    if (bad !== undefined) return `bash-guard: DROP of "${bad}" is not allowed; only databases and roles named hermi or hermi_* may be dropped`;
  }
  if (psqlCalls.length && SQL_RISKY_RE.test(text)) {
    for (const c of psqlCalls) {
      const db = psqlDatabase(c.args, c.assigns);
      if (!hermiName(db)) return `bash-guard: DROP or TRUNCATE through psql needs -d hermi_<name> (this call connects to ${db ? `"${db}"` : 'the default database'}); only hermi or hermi_* databases may be changed this way`;
    }
    for (const m of text.matchAll(/\\c(?:onnect)?\s+(\S+)/gi)) {
      if (!hermiName(m[1])) return `bash-guard: DROP or TRUNCATE after \\connect ${m[1]} is not allowed; only hermi or hermi_* databases`;
    }
  }
  return null;
}

function checkDropCli(cmd, args) {
  if (cmd !== 'dropdb' && cmd !== 'dropuser') return null;
  const withValue = new Set(['-U', '-h', '-p', '--username', '--host', '--port', '--maintenance-db']);
  const names = [];
  for (let i = 0; i < args.length; i++) {
    const a = args[i];
    if (withValue.has(a)) i++;
    else if (a.startsWith('-')) continue;
    else names.push(a);
  }
  const bad = names.find((n) => !n.toLowerCase().startsWith('hermi'));
  if (bad !== undefined) return `bash-guard: ${cmd} "${bad}" is not allowed; only names starting with hermi may be dropped`;
  if (names.length === 0) return `bash-guard: ${cmd} without a name is not allowed`;
  return null;
}

const ENV_RE = /(?<![\w.-])(\.env(?:\.[A-Za-z0-9_-]+)*)(?![\w-])/gi;

function envProblem(text) {
  for (const m of String(text ?? '').matchAll(ENV_RE)) {
    if (m[1].toLowerCase() !== '.env.example') {
      return `bash-guard: commands may not mention ${m[1]} (only .env.example); run "npm run doctor" to see which variables are set`;
    }
  }
  return null;
}

// Words that are prose or a search pattern rather than a file: a commit message, a PR title or body,
// the pattern of grep or rg. They may talk about .env; a file operand may not.
const MESSAGE_FLAGS = new Set(['-m', '--message', '--body', '--title', '--notes']);
const SEARCH_CMDS = new Set(['grep', 'egrep', 'fgrep', 'rg', 'ag', 'ack', 'findstr', 'select-string', 'sls']);
const SEARCH_VALUE_FLAGS = new Set(['-A', '-B', '-C', '-m', '-g', '-t', '-T', '-d', '-D', '-j', '-M', '-f', '--glob', '--iglob', '--type', '--type-not', '--file', '--include', '--exclude', '--exclude-dir', '--max-count', '--context', '--after-context', '--before-context', '--max-depth', '--threads', '--max-columns', '--sort', '--sortr', '--encoding', '--colors']);

/** Indexes of the args that hold prose or a search pattern (exempt from the .env mention check). */
function proseArgs(cmd, args) {
  const ex = new Set();
  if (cmd === 'git' || cmd === 'gh') {
    args.forEach((a, i) => {
      if (MESSAGE_FLAGS.has(a) || (cmd === 'gh' && (a === '-b' || a === '-t')) || (cmd === 'git' && /^-(?!-)[a-zA-Z]*m$/.test(a))) ex.add(i + 1);
      else if (/^--(?:message|body|title|notes)=/.test(a) || (cmd === 'git' && /^-(?!-)[a-zA-Z]*m.+$/.test(a))) ex.add(i);
    });
  }
  if (SEARCH_CMDS.has(cmd)) {
    let pattern = null;
    let explicit = false;
    for (let i = 0; i < args.length; i++) {
      const a = args[i];
      if (a === '-e' || a === '--regexp') {
        ex.add(i + 1);
        explicit = true;
        i++;
      } else if (a.startsWith('--regexp=')) {
        ex.add(i);
        explicit = true;
      } else if (SEARCH_VALUE_FLAGS.has(a)) i++;
      else if (!a.startsWith('-') && pattern === null) pattern = i;
    }
    if (!explicit && pattern !== null) ex.add(pattern);
  }
  return ex;
}

/** .env anywhere in a segment's words, assignments and redirect targets, minus the exempt and inline-script words. */
function checkEnvSegment({ seg, word, args, assigns, skip }) {
  const words = [...assigns, word, ...args.filter((_, i) => !skip.has(i)), ...seg.redirects, ...seg.inputs];
  for (const w of words) {
    const p = envProblem(w);
    if (p) return p;
  }
  return null;
}

/** Read, Grep and Glob must not touch .env or .env.* (only .env.example). Returns a reason or null. */
export function checkFileTool(toolName, toolInput = {}) {
  const candidates = [];
  if (toolName === 'Read') candidates.push(toolInput.file_path);
  else if (toolName === 'Grep') candidates.push(toolInput.path, toolInput.glob);
  else if (toolName === 'Glob') candidates.push(toolInput.pattern, toolInput.path);
  else return null;
  for (const c of candidates) {
    if (typeof c !== 'string') continue;
    // A glob such as **/.env* or .env.* names the family; a path names one file.
    for (const m of norm(c).matchAll(/(?<![\w.-])(\.env(?:\.[A-Za-z0-9_*?[\]{},-]+|[*?{])*)(?![\w-])/gi)) {
      if (m[1].toLowerCase() !== '.env.example') return `file-guard: ${toolName} may not touch ${m[1]} (only .env.example); run "npm run doctor" to see which variables are set`;
    }
  }
  return null;
}

// --- recursive deletes ---

const DELETE_CMDS = new Set(['rm', 'rmdir', 'rd', 'del', 'erase', 'ri', 'remove-item', 'unlink']);

function isRecursiveDelete(cmd, args) {
  if (!DELETE_CMDS.has(cmd)) return false;
  return args.some((a) => /^-[a-zA-Z]*[rR][a-zA-Z]*$/.test(a) || a === '--recursive' || /^-r(e(c(u(r(s(e)?)?)?)?)?)?$/i.test(a) || /^\/s$/i.test(a));
}

const isSwitch = (a) => a.startsWith('-') || /^\/[a-zA-Z]$/.test(a);

function pathApi(ctx) {
  return ctx.windows ? path.win32 : path.posix;
}

/** msys /c/Users/x -> C:/Users/x (Windows only); backslashes -> slashes. */
function normalizePath(p, ctx) {
  let x = norm(p);
  if (ctx.windows) {
    const m = /^\/([a-zA-Z])(\/|$)/.exec(x);
    if (m) x = `${m[1].toUpperCase()}:/${x.slice(m[0].length)}`;
  }
  return x;
}

function isInside(api, root, target) {
  const rel = api.relative(root, target);
  return rel === '' || (!rel.startsWith('..') && !api.isAbsolute(rel));
}

function deleteTargetProblem(arg, ctx) {
  const raw = arg.trim();
  if (raw === '') return null;
  if (/^[$%`]/.test(raw)) return `delete target "${raw}" cannot be verified (it starts with a variable or substitution)`;
  if (raw === '~' || raw.startsWith('~/') || raw.startsWith('~\\')) return `recursive delete in the home directory (${raw}) is not allowed`;
  const api = pathApi(ctx);
  const p = normalizePath(raw, ctx);
  const globAt = p.search(/[*?[]/);
  const base = globAt >= 0 ? p.slice(0, globAt) : p;
  const resolved = api.resolve(ctx.cwd, base === '' ? '.' : base);
  if (api.parse(resolved).root === resolved || /^\/+$/.test(p) || /^[A-Za-z]:\/*$/.test(p)) {
    return `recursive delete of a filesystem or drive root (${raw}) is not allowed`;
  }
  const repo = api.resolve(ctx.repoRoot ?? ctx.cwd);
  if (!isInside(api, repo, resolved)) return `recursive delete outside the repository (${raw}) is not allowed`;
  if (api.relative(repo, resolved) === '') return 'recursive delete of the repository root is not allowed';
  if (isInside(api, api.join(repo, '.git'), resolved)) return 'recursive delete inside .git is not allowed';
  return null;
}

function checkDelete(cmd, args, viaXargs, ctx) {
  if (!isRecursiveDelete(cmd, args)) return null;
  const targets = args.filter((a) => !isSwitch(a));
  if (viaXargs && targets.length === 0) return `bash-guard: recursive ${cmd} through xargs has unverifiable targets`;
  for (const t of targets) {
    const problem = deleteTargetProblem(t, ctx);
    if (problem) return `bash-guard: ${problem}`;
  }
  return null;
}

// --- writes into scripts/autopilot ---

const WRITE_ALL = new Set([
  'rm', 'rmdir', 'rd', 'del', 'erase', 'ri', 'remove-item', 'unlink', 'touch', 'truncate', 'mkdir', 'md', 'chmod', 'chown', 'ln',
  'tee', 'set-content', 'sc', 'add-content', 'ac', 'out-file', 'clear-content', 'new-item', 'ni', 'rename-item', 'rni', 'ren', 'mv',
  'move', 'move-item', 'mi', 'patch',
]);
const WRITE_DEST_LAST = new Set(['cp', 'copy', 'copy-item', 'cpi', 'rsync', 'install', 'xcopy', 'robocopy']);
const IN_PLACE = new Set(['sed', 'perl', 'ruby']);

// Owner-controlled paths: the driver, its settings and hooks, the agent definitions, the Claude settings
// files (including settings.local.json, which can disable the hooks) and the MCP configuration.
const OWNER_PATH_RE = /(^|\/)(scripts\/autopilot(\/|$)|\.claude\/(settings[^/]*\.json|agents(\/|$))|\.mcp\.json$)/;

function pathUnderAutopilot(p, ctx) {
  const x = normalizePath(p, ctx).toLowerCase();
  if (OWNER_PATH_RE.test(x)) return true;
  if (!ctx.repoRoot) return false;
  const api = pathApi(ctx);
  try {
    const repo = api.resolve(ctx.repoRoot);
    const abs = api.resolve(ctx.cwd ?? ctx.repoRoot, normalizePath(p, ctx));
    return isInside(api, repo, abs) && OWNER_PATH_RE.test(norm(api.relative(repo, abs)).toLowerCase());
  } catch {
    return false;
  }
}

function checkAutopilotWrite(cmd, args, redirects, ctx) {
  const reason = 'bash-guard: scripts/autopilot/, .claude/settings*.json, .claude/agents/ and .mcp.json are owner-controlled and may not be written from a session';
  if (redirects.some((r) => pathUnderAutopilot(r, ctx))) return reason;
  const operands = args.filter((a) => !a.startsWith('-'));
  if (WRITE_ALL.has(cmd) && operands.some((a) => pathUnderAutopilot(a, ctx))) return reason;
  if (WRITE_DEST_LAST.has(cmd)) {
    const t = args.findIndex((a) => a === '-t' || a === '--target-directory' || /^-destination$/i.test(a));
    const dest = t >= 0 ? args[t + 1] : operands[operands.length - 1];
    if (dest && pathUnderAutopilot(dest, ctx)) return reason;
  }
  if (IN_PLACE.has(cmd) && args.some((a) => /^-[a-zA-Z]*i/.test(a) || a === '--in-place') && operands.some((a) => pathUnderAutopilot(a, ctx))) return reason;
  if (cmd === 'dd' && args.some((a) => a.startsWith('of=') && pathUnderAutopilot(a.slice(3), ctx))) return reason;
  if (cmd === 'git') {
    const { sub, rest } = gitSubcommand(args);
    if (['checkout', 'restore', 'rm', 'mv', 'clean', 'reset', 'apply', 'am'].includes(sub) && rest.some((a) => pathUnderAutopilot(a, ctx))) return reason;
  }
  return null;
}

// ---------------------------------------------------------------------------------------------
// Entry point
// ---------------------------------------------------------------------------------------------

// Commands that run text the guard cannot read, or start a process outside its view.
const OPAQUE_CMDS = new Set(['eval', 'iex', 'invoke-expression', 'invoke-command', 'icm', 'start-process', 'saps']);

// PowerShell takes any unambiguous prefix of a parameter name: -e, -enc, -EncodedCommand, -ec.
const isEncodedCommandFlag = (a) => {
  const f = String(a).slice(1).toLowerCase();
  return String(a).startsWith('-') && f.length > 0 && (f === 'ec' || 'encodedcommand'.startsWith(f));
};

function checkSegments(infos, ctx, depth) {
  for (const { seg, cmd, word, args, viaXargs, assigns, inline } of infos) {
    if (assigns.some((a) => /^GIT_CONFIG/i.test(a))) return 'bash-guard: git configuration through the environment (GIT_CONFIG_*) can redirect a push and is not allowed';
    if (!cmd) {
      const r = checkAutopilotWrite('', [], seg.redirects, ctx);
      if (r) return r;
      continue;
    }
    if (isDynamic(word)) return `bash-guard: the command "${word}" uses a variable, substitution or brace expansion, so it cannot be checked; write the command out`;
    if (OPAQUE_CMDS.has(cmd)) return `bash-guard: ${cmd} runs text the guard cannot check and is not allowed; run the command directly`;
    if ((cmd === 'powershell' || cmd === 'pwsh') && args.some(isEncodedCommandFlag)) return 'bash-guard: -EncodedCommand hides the command from the guard and is not allowed';
    if (args.includes('--admin')) return 'bash-guard: --admin is not allowed';
    if (inline) {
      const inner = checkBash(inline.text, ctx, depth + 1);
      if (inner) return inner;
    }
    const r =
      (cmd === 'git' && checkGit(args, ctx)) ||
      (cmd === 'gh' && checkGh(args)) ||
      checkDropCli(cmd, args) ||
      checkDelete(cmd, args, viaXargs, ctx) ||
      checkAutopilotWrite(cmd, args, seg.redirects, ctx);
    if (r) return r;
  }
  return null;
}

/** One reading of a command text: .env mentions, then SQL, then the per-command rules. */
function checkReading(text, ctx, depth) {
  const { segments, heredocs } = parseShell(text);
  const infos = segments.map((seg) => {
    const u = unwrap(seg.words);
    const inline = depth < 3 ? inlineScript(u.cmd, u.args) : null; // checked as a script of its own below
    const skip = new Set([...(inline?.idx ?? []), ...proseArgs(u.cmd, u.args)]);
    return { seg, ...u, inline, skip };
  });
  for (const info of infos) {
    const p = checkEnvSegment(info);
    if (p) return p;
  }
  const sqlTexts = [...heredocs, ...infos.flatMap((i) => [i.word, ...i.args.filter((_, k) => !i.skip.has(k))])];
  const sql = checkSql(sqlTexts, infos.filter((i) => i.cmd === 'psql').map((i) => ({ args: i.args, assigns: i.assigns })));
  return sql || checkSegments(infos, ctx, depth);
}

/**
 * @param command text of the Bash or PowerShell tool call
 * @param ctx {repoRoot, cwd, windows?, currentBranch?: () => string|null}
 *
 * The text is read twice: as written (a backslash is a Windows path separator) and unescaped the way
 * bash and PowerShell read it (g\it, gh pr m\erge, HEAD:ma\in, --for\ce, a PowerShell backtick). A
 * block on either reading blocks the call.
 */
export function checkBash(command, ctx = {}, depth = 0) {
  const text = String(command ?? '');
  const c = { ...ctx, windows: ctx.windows ?? process.platform === 'win32', cwd: ctx.cwd ?? process.cwd() };
  const unescaped = text.replace(/`/g, '').replace(/\\(?=[^\r\n])/g, '');
  return checkReading(text, c, depth) || (unescaped === text ? null : checkReading(unescaped, c, depth));
}
