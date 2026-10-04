// Pure helpers: the `claude` command line and the child environment for one session.

export const OPUS_MODEL = 'claude-opus-5-5';
export const SONNET_MODEL = 'claude-sonnet-5-5';

/** Plan and FINAL sessions judge, so they run on Opus. Everything else runs on Sonnet. */
export const MODE_MODEL = { plan: OPUS_MODEL, final: OPUS_MODEL, ticket: SONNET_MODEL, ship: SONNET_MODEL, 'ci-fix': SONNET_MODEL };

export const MODE_MAX_TURNS = { plan: 150, ticket: 300, ship: 200, 'ci-fix': 200, final: 300 };

export const DISALLOWED_TOOLS = ['AskUserQuestion', 'EnterPlanMode', 'EnterWorktree', 'CronCreate', 'RemoteTrigger', 'ScheduleWakeup', 'Workflow', 'Monitor'];

// The one set of file names (driver/ctx.mjs re-exports them in FILES).
export const APPEND_PROMPT_FILE = 'app-buildout/prompts/AUTOPILOT.md';
export const SETTINGS_FILE = 'scripts/autopilot/settings.json';
export const SETTINGS_DONTASK_FILE = 'scripts/autopilot/settings-dontask.json';
export const HOOK_FILES = ['scripts/autopilot/hooks/agent-guard.mjs', 'scripts/autopilot/hooks/bash-guard.mjs', 'scripts/autopilot/hooks/file-guard.mjs'];

export function modelForMode(mode) {
  const m = MODE_MODEL[mode];
  if (!m) throw new Error(`no model for mode ${mode}`);
  return m;
}

/**
 * Arguments for claude.exe. The prompt is NOT an argument: the task line goes on stdin.
 * permission: 'auto' (default) or 'dontAsk' (opt-in profile with a fixed allow list, run.mjs --permission-profile dontask).
 * --strict-mcp-config with no --mcp-config means no MCP server at all, so the owner's claude.ai connectors
 * (Gmail, Drive) are not loaded; both settings files also set disableClaudeAiConnectors.
 */
export function buildClaudeArgs({ model, permission = 'auto', name, resumeId, appendPromptFile = APPEND_PROMPT_FILE, hookEvents = false }) {
  const args = ['-p', '--model', model];
  if (appendPromptFile) args.push('--append-system-prompt-file', appendPromptFile);
  args.push(
    '--settings', permission === 'dontAsk' ? SETTINGS_DONTASK_FILE : SETTINGS_FILE,
    '--permission-mode', permission,
    '--permission-prompts', 'none',
    '--output-format', 'stream-json',
    '--verbose',
    '--forward-subagent-text',
    '--strict-mcp-config',
  );
  if (hookEvents) args.push('--include-hook-events');
  args.push('--disallowedTools', ...DISALLOWED_TOOLS);
  args.push('--name', name);
  if (resumeId) args.push('--resume', resumeId);
  return args;
}

// Variables that would point a child session at the wrong account or at a parent session.
const STRIP_EXACT = new Set(['ANTHROPIC_API_KEY', 'ANTHROPIC_AUTH_TOKEN', 'CLAUDECODE', 'CLAUDE_PID', 'CLAUDE_EFFORT', 'CLAUDE_PROJECT_DIR']);
// CLAUDE_CODE_* is inherited from a parent Claude session when the driver is started from one.
// These carry the owner's own configuration and stay.
const KEEP_EXACT = new Set(['CLAUDE_CODE_OAUTH_TOKEN', 'CLAUDE_CODE_GIT_BASH_PATH', 'CLAUDE_CONFIG_DIR']);

export function prependPath(env, dirs) {
  if (!dirs.length) return env;
  const key = Object.keys(env).find((k) => k.toLowerCase() === 'path') ?? 'PATH';
  const sep = process.platform === 'win32' ? ';' : ':';
  env[key] = [...dirs, env[key]].filter(Boolean).join(sep);
  return env;
}

/** Environment for the child: no API key, no parent-session markers, per-mode turn cap. */
export function buildChildEnv(base, { mode, extraPathDirs = [] } = {}) {
  const env = {};
  for (const [k, v] of Object.entries(base)) {
    if (v === undefined) continue;
    if (STRIP_EXACT.has(k)) continue;
    if ((k.startsWith('CLAUDE_CODE_') || k.startsWith('CLAUDE_AGENT_')) && !KEEP_EXACT.has(k)) continue;
    env[k] = v;
  }
  env.CLAUDE_CODE_DISABLE_AUTO_MEMORY = '1';
  env.CLAUDE_CODE_MAX_TURNS = String(MODE_MAX_TURNS[mode] ?? 200);
  env.MSYS_NO_PATHCONV = '1';
  return prependPath(env, extraPathDirs);
}

/** A command line for humans (dry run, logs). Not for execution. */
export function formatCommand(exe, args) {
  const q = (s) => (/^[\w@%+=:,./\\-]+$/.test(s) ? s : `"${String(s).replace(/"/g, '\\"')}"`);
  return [exe, ...args].map(q).join(' ');
}
