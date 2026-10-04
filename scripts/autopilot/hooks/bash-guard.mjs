// PreToolUse hook for the Bash and PowerShell tools.
// Blocks force pushes, pushes to main, merges, .env access, DROP outside hermi*, recursive deletes
// outside the repo, history rewrites and writes into scripts/autopilot/ (see lib/guards.mjs).
// Allow: exit 0. Block: exit 2 with a one-line reason on stderr.

import { execFileSync } from 'node:child_process';
import { checkBash } from '../lib/guards.mjs';
import { blockAndExit, readHookInput } from './io.mjs';

const input = readHookInput('bash-guard');
const command = input.tool_input?.command ?? '';
const cwd = input.cwd || process.cwd();
const repoRoot = process.env.CLAUDE_PROJECT_DIR || cwd;

// Only asked for when a push has no explicit destination, so most calls never spawn git.
const currentBranch = () => {
  try {
    return execFileSync('git', ['rev-parse', '--abbrev-ref', 'HEAD'], { cwd, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'], timeout: 5000 }).trim();
  } catch {
    return null;
  }
};

let reason = null;
try {
  reason = checkBash(command, { repoRoot, cwd, currentBranch });
} catch (e) {
  blockAndExit(`bash-guard: internal error (${e.message}), so the call is refused`);
}
if (reason) blockAndExit(reason);
process.exit(0);
