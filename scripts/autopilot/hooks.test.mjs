// Tests for the PreToolUse hooks. The hooks are spawned with sample hook JSON on stdin, as Claude Code
// does: exit 0 allows, exit 2 blocks with a one-line reason on stderr. The guard logic is also driven
// directly with a table of commands (Windows path rules, injected current branch).

import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import { checkAgent, checkBash, parseShell, unwrap } from './lib/guards.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..', '..');
const AGENT_HOOK = path.join(HERE, 'hooks', 'agent-guard.mjs');
const BASH_HOOK = path.join(HERE, 'hooks', 'bash-guard.mjs');
const FILE_HOOK = path.join(HERE, 'hooks', 'file-guard.mjs');

function runHook(hook, input, { raw } = {}) {
  const r = spawnSync(process.execPath, [hook], { input: raw ?? JSON.stringify(input), encoding: 'utf8', env: { ...process.env, CLAUDE_PROJECT_DIR: ROOT } });
  return { code: r.status, stderr: r.stderr, stdout: r.stdout };
}
const agent = (tool_input, tool_name = 'Agent') => runHook(AGENT_HOOK, { hook_event_name: 'PreToolUse', tool_name, tool_input, cwd: ROOT });
const bash = (command, tool_name = 'Bash') => runHook(BASH_HOOK, { hook_event_name: 'PreToolUse', tool_name, tool_input: { command }, cwd: ROOT });

const oneLine = (s) => s.trim().split('\n').length === 1;

// ---------------------------------------------------------------------------------------------
// agent-guard (spawned)
// ---------------------------------------------------------------------------------------------

test('agent-guard allows the four agents on their own tier', () => {
  for (const input of [
    { subagent_type: 'sonnet-researcher', run_in_background: false },
    { subagent_type: 'sonnet-coder', model: 'sonnet', run_in_background: false },
    { subagent_type: 'sonnet-coder', model: 'claude-sonnet-5-5', run_in_background: false },
    { subagent_type: 'opus-reviewer', run_in_background: false },
    { subagent_type: 'opus-reviewer', model: 'opus', run_in_background: false },
    { subagent_type: 'opus-judge', model: 'claude-opus-5-5', run_in_background: false },
    { subagent_type: 'general-purpose', model: 'sonnet', run_in_background: false },
    { subagent_type: 'Explore', model: 'sonnet', run_in_background: false },
  ]) {
    const r = agent(input);
    assert.equal(r.code, 0, JSON.stringify(input));
    assert.equal(r.stderr, '');
  }
});

test('agent-guard blocks a model that does not match the agent, with one line naming the allowed agents', () => {
  for (const input of [
    { subagent_type: 'sonnet-coder', model: 'opus', run_in_background: false },
    { subagent_type: 'sonnet-researcher', model: 'inherit', run_in_background: false },
    { subagent_type: 'opus-reviewer', model: 'sonnet', run_in_background: false },
    { subagent_type: 'opus-judge', model: 'haiku', run_in_background: false },
    { subagent_type: 'general-purpose', run_in_background: false },
    { subagent_type: 'general-purpose', model: 'opus', run_in_background: false },
    { subagent_type: 'Explore', model: 'haiku', run_in_background: false },
    { prompt: 'no subagent_type means general-purpose, which needs model sonnet', run_in_background: false },
  ]) {
    const r = agent(input);
    assert.equal(r.code, 2, JSON.stringify(input));
    assert.ok(oneLine(r.stderr), r.stderr);
    assert.match(r.stderr, /^agent-guard: /);
  }
});

test('agent-guard blocks every other agent and names the allowed ones', () => {
  for (const type of ['Plan', 'claude', 'claude-code-guide', 'statusline-setup', 'fork', 'my-agent']) {
    const r = agent({ subagent_type: type, model: 'sonnet', run_in_background: false });
    assert.equal(r.code, 2, type);
    assert.match(r.stderr, /sonnet-researcher and sonnet-coder/);
    assert.match(r.stderr, /opus-reviewer and opus-judge/);
  }
  assert.equal(agent({ subagent_type: 'Plan', run_in_background: false }, 'Task').code, 2, 'the Task tool name is handled like Agent');
});

test('agent-guard blocks an Agent call that is not run_in_background: false', () => {
  const valid = { subagent_type: 'sonnet-coder', model: 'sonnet' };
  for (const input of [valid, { ...valid, run_in_background: true }]) {
    const r = agent(input);
    assert.equal(r.code, 2, JSON.stringify(input));
    assert.match(r.stderr, /run_in_background: false/);
    assert.ok(oneLine(r.stderr));
  }
  assert.equal(agent({ ...valid, run_in_background: false }).code, 0);
});

test('all three hooks refuse unreadable input (fail closed)', () => {
  for (const hook of [AGENT_HOOK, BASH_HOOK, FILE_HOOK]) {
    for (const raw of ['', 'not json', '[]', 'null', '{}', '{"tool_name":"Bash"}', '{"tool_input":"x"}']) {
      const r = runHook(hook, null, { raw });
      assert.equal(r.code, 2, `${path.basename(hook)} with ${JSON.stringify(raw)}`);
      assert.ok(oneLine(r.stderr));
    }
  }
});

// ---------------------------------------------------------------------------------------------
// bash-guard (spawned): one case per rule, and things that must stay allowed
// ---------------------------------------------------------------------------------------------

const BLOCKED = [
  ['git push --force origin phase1/p07-x', /force-pushing/],
  ['git push -f origin phase1/p07-x', /force-pushing/],
  ['git push --force-with-lease origin phase1/p07-x', /force-pushing/],
  ['git push origin +phase1/p07-x', /\+ refspec/],
  ['git push origin HEAD:main', /pushing to main/],
  ['git push origin main', /pushing to main/],
  ['git push --mirror origin', /--mirror/],
  ['gh pr merge 12 --squash', /gh pr merge/],
  ['gh api repos/avillalv/hermi/pulls/12/merge -X PUT', /never changed through gh api/],
  ['gh pr merge 12 --admin', /--admin/],
  ['cat .env', /\.env/],
  ['cat apps/api/.env.local', /\.env\.local/],
  ['cp .env.example .env', /mention \.env/],
  ['psql -U postgres -c "DROP DATABASE production"', /DROP of "production"/],
  ['psql -c "drop role alice"', /DROP of "alice"/],
  ['dropdb -U postgres production', /dropdb "production"/],
  ['dropuser alice', /dropuser "alice"/],
  ['rm -rf /', /filesystem or drive root/],
  ['rm -rf ~', /home directory/],
  ['rm -rf ../elsewhere', /outside the repository/],
  ['git filter-branch --tree-filter x HEAD', /filter-branch/],
  ['echo x > scripts/autopilot/run.mjs', /scripts\/autopilot/],
  ['sed -i s/a/b/ scripts/autopilot/settings.json', /scripts\/autopilot/],
  ['rm scripts/autopilot/lib/task.mjs', /scripts\/autopilot/],
  ['echo x | tee scripts/autopilot/x', /scripts\/autopilot/],
  ['bash -c "git push origin main"', /pushing to main/],
];

test('bash-guard blocks with exit 2 and a one-line reason', () => {
  for (const [command, re] of BLOCKED) {
    const r = bash(command);
    assert.equal(r.code, 2, command);
    assert.ok(oneLine(r.stderr), `${command}: ${r.stderr}`);
    assert.match(r.stderr, re, command);
    assert.match(r.stderr, /^bash-guard: /);
    assert.equal(r.stdout, '');
  }
});

const ALLOWED = [
  'git status --short',
  'git push -u origin phase1/p07-entitlements',
  'git push origin HEAD:phase1/p07-entitlements',
  'git commit -m "WF-023 Entitlements"',
  'gh pr create --draft --base main --head phase1/p07-x --title "Phase 1 / P07: Entitlements"',
  'gh pr ready 12 && gh pr edit 12 --add-label e2e',
  'gh pr checks 12 --required',
  'gh api repos/avillalv/hermi/pulls/12',
  'npm run doctor',
  'npm run lint && npm run test:api',
  'cat .env.example',
  'git add .env.example',
  'node -e "console.log(process.env.HOME)"',
  'psql -U postgres -c "DROP DATABASE IF EXISTS hermi_test"',
  'dropdb --if-exists -U postgres hermi_scratch',
  'rm -rf node_modules dist coverage',
  'rm -f apps/web/dist/index.html',
  'node scripts/autopilot/status.mjs',
  'cat scripts/autopilot/settings.json',
  'node scripts/spec-lint.mjs > lint.txt',
  'taskkill /T /F /PID 4242',
  'timeout 600 npm run test:e2e',
];

test('bash-guard allows ordinary build commands (exit 0, silent)', () => {
  for (const command of ALLOWED) {
    const r = bash(command);
    assert.equal(r.code, 0, `${command}: ${r.stderr}`);
    assert.equal(r.stderr, '');
  }
});

// ---------------------------------------------------------------------------------------------
// Finding 15: bypasses. Every one of these must be blocked, and the ordinary commands next to them must not.
// ---------------------------------------------------------------------------------------------

const BS = '\\'; // one backslash, so a test line reads like the command a model would send
const BYPASSES = [
  'eval "git push origin HEAD:main"',
  `gh pr m${BS}erge 12 --squash`,
  `git push origin HEAD:ma${BS}in`,
  `git push --for${BS}ce origin phase1/p07-x`,
  `git push origin phase1/x:ma${BS}in`,
  'B=main; git push origin HEAD:$B',
  'git push origin HEAD:${B}',
  'git push origin {main,x}',
  '"$GIT" push origin HEAD:main',
  '$GH pr merge 12',
  'gh pr m`erge 12',
  'Invoke-Expression "gh pr merge 12"',
  'iex "gh pr merge 12"',
  'Start-Process gh -ArgumentList "pr merge 12"',
  'powershell -EncodedCommand ZwBpAHQAIABwAHUAcwBoAA==',
  'pwsh -enc ZwBpAHQA',
  'powershell -e ZwBpAHQA',
  'git -c remote.origin.push=HEAD:main push',
  'git -c remote.origin.push=HEAD:main push origin',
  'git config remote.origin.push HEAD:main',
  'GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=remote.origin.push GIT_CONFIG_VALUE_0=HEAD:main git push',
  'gh alias set m "pr merge"',
  'gh -R avillalv/hermi pr merge 12',
  'echo "$(git push origin main)"',
  'cat < .env',
  `cat .e${BS}nv`,
];

test('bash-guard blocks every bypass of the finding (unescaping, eval, iex, -EncodedCommand, git -c remote.*, gh alias, $ in a command word or refspec)', () => {
  const bad = BYPASSES.filter((c) => bash(c).code !== 2);
  assert.deepEqual(bad, []);
  const direct = BYPASSES.filter((c) => !checkBash(c, win));
  assert.deepEqual(direct, []);
});

test('fix 3: gh api never moves a ref, changes protection or rulesets, or merges; wildcard and heads/ refspecs cannot reach main', () => {
  const blocked = [
    'gh api -X PATCH repos/avillalv/hermi/git/refs/heads/main -f sha=abc',
    'gh api -X DELETE repos/avillalv/hermi/branches/main/protection',
    "gh api graphql -f query='mutation{updateRef(input:{}){clientMutationId}}'",
    "gh api graphql -f query='mutation{mergeBranch(input:{}){clientMutationId}}'",
    'gh api graphql --input q.json',
    'gh api graphql --input=q.json',
    'gh api graphql -F query=@q.graphql',
    'gh api -X POST repos/avillalv/hermi/rulesets --input r.json',
    'gh api -X POST repos/avillalv/hermi/merges -f base=main -f head=x',
    "gh api graphql -f query='mutation{createBranchProtectionRule(input:{}){clientMutationId}}'",
    "gh api graphql -f query='mutation{deleteRef(input:{}){clientMutationId}}'",
    'git push origin HEAD:heads/main',
    'git push origin HEAD:refs/heads/main',
    "git push origin 'refs/heads/*:refs/heads/*'",
    'git push origin phase1/*',
  ];
  for (const c of blocked) {
    const r = bash(c);
    assert.equal(r.code, 2, c);
    assert.ok(oneLine(r.stderr), `${c}: ${r.stderr}`);
    assert.match(r.stderr, /^bash-guard: /);
  }
  assert.match(bash('gh api -X PATCH repos/avillalv/hermi/git/refs/heads/main -f sha=abc').stderr, /never changed through gh api/);
  assert.match(bash("git push origin 'refs/heads/*:refs/heads/*'").stderr, /wildcard/);
  assert.match(bash('git push origin HEAD:heads/main').stderr, /pushing to main/);
  for (const c of ['gh api repos/avillalv/hermi/pulls/7', 'gh pr view 7 --json state', 'git push -u origin phase1/p07-entitlements-and-collaboration', 'gh api repos/avillalv/hermi/pulls/7/comments', 'gh api graphql -f query=\'{ viewer { login } }\'']) {
    const r = bash(c);
    assert.equal(r.code, 0, `${c}: ${r.stderr}`);
    assert.equal(r.stderr, '');
  }
});

test('fix 4: .claude/settings*.json, .claude/agents/ and .mcp.json are owner-controlled like scripts/autopilot', () => {
  const blocked = [
    'echo {} > .claude/settings.local.json',
    'sed -i s/a/b/ .claude/settings.json',
    'rm .claude/agents/opus-judge.md',
    'cp /tmp/x .claude/agents/new.md',
    'echo {} > .mcp.json',
    'git checkout -- .claude/settings.json',
    'tee C:/Users/matic/code/hermi/.claude/settings.local.json',
    'mv /tmp/x .claude' + BS + 'settings.json',
  ];
  for (const c of blocked) {
    const r = bash(c);
    assert.equal(r.code, 2, c);
    assert.match(r.stderr, /\.claude\/settings\*\.json, \.claude\/agents\/ and \.mcp\.json are owner-controlled/, c);
  }
  for (const c of ['cat .claude/settings.json', 'cat .mcp.json', 'git diff -- .claude/agents', 'ls .claude/agents', 'cp .claude/settings.json /tmp/x', 'git add .claude/rules/x.md']) {
    assert.equal(bash(c).code, 0, c);
  }
  // a relative name resolved against a cwd inside .claude, and the mcp file by absolute path
  const inClaude = { ...win, cwd: 'C:/Users/matic/code/hermi/.claude' };
  assert.ok(checkBash('rm settings.json', inClaude), 'rm settings.json inside .claude');
  assert.ok(checkBash('rm agents/opus-judge.md', inClaude), 'rm agents/x inside .claude');
  assert.ok(checkBash('rm settings.local.json', inClaude), 'settings.local.json inside .claude');
  assert.equal(checkBash('rm rules/x.md', inClaude), null, 'other .claude content stays writable');
  assert.ok(checkBash('touch C:/Users/matic/code/hermi/.mcp.json', win));
  assert.equal(checkBash('touch C:/Users/matic/code/hermi/apps/.mcp.jsonx', win), null);
});

test('bash-guard blocks clean -x/-X, stash clear/drop and push --delete (finding 16)', () => {
  for (const c of ['git clean -fdx', 'git clean -xfd', 'git clean -X', 'git stash clear', 'git stash drop', 'git stash drop stash@{0}', 'git push --delete origin phase1/p07-x', 'git push origin :phase1/p07-x', 'git push -d origin phase1/p07-x']) {
    assert.equal(bash(c).code, 2, c);
  }
  for (const c of ['git clean -fd', 'git clean -n', 'git stash list', 'git stash push -u -m x', 'git stash pop']) assert.equal(bash(c).code, 0, c);
});

test('bash-guard keeps the normal build commands allowed, including text that merely talks about .env (finding 19)', () => {
  for (const c of [
    'npm run test:api',
    'git commit -m "mentions .env.example"',
    'git commit -m "document how .env is loaded"',
    'git commit -am "fix .env handling" --no-verify',
    'gh pr create --body "uses .env files, see DROP TABLE notes" --title "Phase 1 / P07: .env docs" --draft',
    'uv run pytest',
    'rg "' + BS + '.env" -n',
    'grep -rn ".env" docs',
    'git push -u origin phase1/p07-x',
    'git config --get remote.origin.url',
    'gh pr view 12 --json state',
    'gh -R avillalv/hermi pr view 12',
    'echo "$(date)"',
    'node scripts/spec-lint.mjs --links',
    'rm -rf apps' + BS + 'web' + BS + 'dist',
  ]) {
    const r = bash(c);
    assert.equal(r.code, 0, `${c}: ${r.stderr}`);
  }
  // ...while an operand that is a file is still checked
  for (const c of ['grep DATABASE_URL .env', 'rg -n DATABASE_URL .env', 'git commit -F .env', 'git add .env', 'cat .env # -m "x"']) assert.equal(bash(c).code, 2, c);
});

test('DROP and TRUNCATE through psql need a hermi* database, and every listed name is checked (finding 20)', () => {
  for (const c of [
    'psql -U postgres -c "TRUNCATE users"',
    'psql -U postgres -d production -c "DROP TABLE users"',
    'psql -d postgres -c "drop schema public cascade"',
    'psql "postgresql://postgres@localhost/production" -c "TRUNCATE users"',
    'psql -U postgres -c "DROP ROLE hermi_a, alice"',
    'psql -U postgres -c "DROP DATABASE hermi_a; DROP DATABASE prod"',
    'psql -U postgres -d hermi_test <<EOF\n\\c production\nTRUNCATE users;\nEOF',
    'psql -U postgres <<EOF\nTRUNCATE users;\nEOF',
  ]) {
    assert.equal(bash(c).code, 2, c);
  }
  for (const c of [
    'psql -U postgres -d hermi_test -c "TRUNCATE users"',
    'psql -U postgres --dbname=hermi_e2e -c "DROP TABLE IF EXISTS trips CASCADE"',
    'psql "postgresql://postgres@localhost/hermi_test" -c "TRUNCATE users"',
    'psql -U postgres -c "DROP DATABASE IF EXISTS hermi_test"',
    'psql -U postgres -c "DROP ROLE IF EXISTS hermi_app, hermi_owner"',
    'git commit -m "drop table notes"',
  ]) {
    assert.equal(bash(c).code, 0, c);
  }
});

test('file-guard blocks Read, Grep and Glob on .env and .env.* but not .env.example (finding 19)', () => {
  const file = (tool_name, tool_input) => runHook(FILE_HOOK, { hook_event_name: 'PreToolUse', tool_name, tool_input, cwd: ROOT });
  for (const [name, input] of [
    ['Read', { file_path: 'C:/Users/matic/code/hermi/.env' }],
    ['Read', { file_path: 'apps/api/.env.local' }],
    ['Read', { file_path: 'apps' + BS + 'api' + BS + '.env.production' }],
    ['Grep', { pattern: 'KEY', path: '.', glob: '.env*' }],
    ['Grep', { pattern: 'KEY', path: 'apps/api/.env' }],
    ['Glob', { pattern: '**/.env.*' }],
    ['Glob', { pattern: '.env*', path: 'apps' }],
  ]) {
    const r = file(name, input);
    assert.equal(r.code, 2, `${name} ${JSON.stringify(input)}`);
    assert.match(r.stderr, /^file-guard: /);
    assert.ok(oneLine(r.stderr));
  }
  for (const [name, input] of [
    ['Read', { file_path: '.env.example' }],
    ['Read', { file_path: 'apps/api/.env.example' }],
    ['Read', { file_path: 'src/environment.ts' }],
    ['Read', { file_path: 'a/.envrc' }],
    ['Grep', { pattern: '\\.env', path: 'docs' }],
    ['Glob', { pattern: '**/*.ts' }],
    ['Edit', { file_path: 'x' }],
  ]) {
    assert.equal(file(name, input).code, 0, `${name} ${JSON.stringify(input)}`);
  }
  assert.equal(runHook(FILE_HOOK, null, { raw: 'not json' }).code, 2, 'unreadable input fails closed');
});

test('agent-guard blocks Agent calls that set isolation or cwd (finding 14), whatever the agent and model', () => {
  for (const input of [
    { subagent_type: 'sonnet-coder', model: 'sonnet', isolation: 'worktree' },
    { subagent_type: 'opus-reviewer', isolation: 'worktree' },
    { subagent_type: 'sonnet-researcher', cwd: 'C:/Users/matic/Documents' },
    { subagent_type: 'general-purpose', model: 'sonnet', cwd: '..' },
  ]) {
    const r = agent(input);
    assert.equal(r.code, 2, JSON.stringify(input));
    assert.match(r.stderr, /isolation or cwd/);
    assert.ok(oneLine(r.stderr));
  }
  assert.equal(agent({ subagent_type: 'sonnet-coder', model: 'sonnet', run_in_background: false }).code, 0);
});

test('bash-guard also guards the PowerShell tool', () => {
  assert.equal(bash('Remove-Item -Recurse -Force C:\\Windows\\Temp\\x', 'PowerShell').code, win32Only(2));
  assert.equal(bash('Set-Content scripts\\autopilot\\run.mjs "x"', 'PowerShell').code, 2);
  assert.equal(bash('Get-Content .env', 'PowerShell').code, 2);
  assert.equal(bash('Get-ChildItem apps', 'PowerShell').code, 0);
});

// PowerShell paths with drive letters only make sense on Windows; elsewhere they are relative names.
function win32Only(code) {
  return process.platform === 'win32' ? code : 0;
}

// ---------------------------------------------------------------------------------------------
// guard logic (direct): Windows path rules, implicit push destinations, wrappers, heredocs
// ---------------------------------------------------------------------------------------------

const win = { repoRoot: 'C:/Users/matic/code/hermi', cwd: 'C:/Users/matic/code/hermi', windows: true, currentBranch: () => 'phase1/p01-x' };
const onMain = { ...win, currentBranch: () => 'main' };

const TABLE = [
  // pushes with an implicit destination depend on the current branch
  ['git push', win, false],
  ['git push', onMain, true],
  ['git push -u origin HEAD', win, false],
  ['git push -u origin HEAD', onMain, true],
  ['git push origin HEAD:refs/heads/main', win, true],
  ['git push origin :main', win, true],
  ['git push --delete origin main', win, true],
  ['git push --all', win, true],
  ['git push -fu origin phase1/x', win, true],
  ['git -C apps/api push origin phase1/x', win, false],
  ['git push --follow-tags origin phase1/x', win, false],
  // recursive deletes
  ['rm -rf C:/Users/matic/Documents', win, true],
  ['rm -rf /c/Users/matic/Documents', win, true],
  ['rm -rf C:\\', win, true],
  ['rm -rf /c/Users/matic/code/hermi/apps/web/dist', win, false],
  ['rm -rf C:/Users/matic/code/hermi/apps/web/dist', win, false],
  ['rm -rf .', win, true],
  ['rm -rf *', win, true],
  ['rm -rf .git', win, true],
  ['rm -rf .git/hooks', win, true],
  ['rm -rf $TMP/x', win, true],
  ['rm -rf dist', win, false],
  ['rm -f notes.txt', win, false],
  ['Remove-Item -Recurse -Force C:\\Windows\\Temp\\x', win, true],
  ['Remove-Item -Recurse -Force .\\apps\\web\\dist', win, false],
  ['rmdir /s /q C:\\foo', win, true],
  ['git ls-files | xargs rm -rf', win, true],
  ['timeout 5 rm -rf /', win, true],
  ['sudo rm -rf /', win, true],
  ['FOO=1 rm -rf /', win, true],
  ['cd apps && rm -rf ../..', { ...win, cwd: 'C:/Users/matic/code/hermi/apps/web' }, true],
  ['rm -rf dist', { ...win, cwd: 'C:/Users/matic/code/hermi/apps/web' }, false],
  // wrappers and inline scripts
  ['bash -c "rm -rf /"', win, true],
  ["sh -c 'cat .env'", win, true],
  ['powershell -Command "Remove-Item -Recurse C:\\x"', win, true],
  ['echo $(cat .env)', win, true],
  // heredoc bodies are text, not commands, except for SQL
  ["cat <<'EOF' > notes.md\ngit push --force origin main\nrm -rf /\nEOF", win, false],
  ["cat <<'EOF' > notes.md\nsome text about .env handling\nEOF", win, false],
  ['psql -U postgres <<EOF\nDROP DATABASE production;\nEOF', win, true],
  ['psql -U postgres <<EOF\nDROP DATABASE IF EXISTS hermi_test;\nEOF', win, false],
  ['git commit -m "$(cat <<\'EOF\'\nWF-001 name\nEOF\n)"', win, false],
  // scripts/autopilot writes versus reads
  ['cp scripts/autopilot/run.mjs /tmp/x', win, false],
  ['cp /tmp/x scripts/autopilot/run.mjs', win, true],
  ['cp -t scripts/autopilot /tmp/x', win, true],
  ['mv scripts/autopilot/run.mjs /tmp/x', win, true],
  ['sed -n 1,5p scripts/autopilot/run.mjs', win, false],
  ['git checkout -- scripts/autopilot', win, true],
  ['git diff -- scripts/autopilot', win, false],
  ['echo hi >> scripts/autopilot/lib/x.mjs', win, true],
  ['echo hi > out.txt 2>&1', win, false],
  ['node scripts/autopilot/status.mjs > out.txt', win, false],
  ['touch C:/Users/matic/code/hermi/scripts/autopilot/new.mjs', win, true],
  ['cd scripts/autopilot && rm run.mjs', { ...win, cwd: 'C:/Users/matic/code/hermi' }, false], // not resolvable per segment
  ['rm run.mjs', { ...win, cwd: 'C:/Users/matic/code/hermi/scripts/autopilot' }, true],
];

test('guard logic table', () => {
  const bad = [];
  for (const [command, ctx, wantBlock] of TABLE) {
    const r = checkBash(command, ctx);
    if (Boolean(r) !== wantBlock) bad.push(`${wantBlock ? 'should block' : 'should allow'}: ${JSON.stringify(command)} -> ${r ?? 'allowed'}`);
  }
  assert.deepEqual(bad, []);
});

test('checkAgent: missing subagent_type is general-purpose', () => {
  assert.match(checkAgent({ run_in_background: false }), /general-purpose needs model "sonnet"/);
  assert.equal(checkAgent({ model: 'sonnet', run_in_background: false }), null);
});

test('parseShell splits commands, redirects and subshells; unwrap strips wrappers', () => {
  const { segments } = parseShell('echo a 2>&1 | tee x > y && ls; (cd z && rm -rf q)');
  assert.deepEqual(
    segments.map((s) => s.words.join(' ')),
    ['echo a', 'tee x', 'ls', 'cd z', 'rm -rf q'],
  );
  assert.deepEqual(segments[1].redirects, ['y']);
  assert.deepEqual(parseShell('echo "a b" \'c d\'').segments[0].words, ['echo', 'a b', 'c d']);
  assert.deepEqual(unwrap(['FOO=1', 'sudo', 'timeout', '5', 'rm', '-rf', 'x']), { cmd: 'rm', word: 'rm', args: ['-rf', 'x'], viaXargs: false, assigns: ['FOO=1'] });
  assert.equal(unwrap(['xargs', '-0', 'rm', '-rf']).viaXargs, true);
  assert.deepEqual(unwrap(['C:\\Program Files\\GitHub CLI\\gh.exe', 'pr', 'merge']), { cmd: 'gh', word: 'C:\\Program Files\\GitHub CLI\\gh.exe', args: ['pr', 'merge'], viaXargs: false, assigns: [] });
});
