// PreToolUse hook for the Read, Grep and Glob tools.
// Blocks any path or glob that names .env or .env.* (only .env.example may be read). The deny rules in
// settings.json cover Read of .env itself; a deny rule cannot carve out .env.example, so this hook does.
// Allow: exit 0. Block: exit 2 with a one-line reason on stderr.

import { checkFileTool } from '../lib/guards.mjs';
import { blockAndExit, readHookInput } from './io.mjs';

const input = readHookInput('file-guard');
let reason = null;
try {
  reason = checkFileTool(input.tool_name, input.tool_input ?? {});
} catch (e) {
  blockAndExit(`file-guard: internal error (${e.message}), so the call is refused`);
}
if (reason) blockAndExit(reason);
process.exit(0);
