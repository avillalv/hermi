// PreToolUse hook for the Agent (Task) tool.
// Only the four judgement and coding agents may run, each on its own model tier.
// Allow: exit 0. Block: exit 2 with a one-line reason on stderr.

import { checkAgent } from '../lib/guards.mjs';
import { blockAndExit, readHookInput } from './io.mjs';

const input = readHookInput('agent-guard');
let reason = null;
try {
  reason = checkAgent(input.tool_input ?? {});
} catch (e) {
  blockAndExit(`agent-guard: internal error (${e.message}), so the call is refused`);
}
if (reason) blockAndExit(reason);
process.exit(0);
