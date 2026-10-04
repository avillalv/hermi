// stdin/stderr plumbing shared by the PreToolUse hooks.
// Convention (Claude Code 2.1.288): exit 2 blocks the tool call and feeds stderr to the model;
// any other non-zero exit is only a non-blocking error, so the guards fail CLOSED with exit 2.

import fs from 'node:fs';

/** Write one line to stderr (synchronously, so exit cannot truncate it) and exit 2. */
export function blockAndExit(reason) {
  try {
    fs.writeSync(2, `${String(reason).replace(/\s*\n\s*/g, ' ').trim()}\n`);
  } finally {
    process.exit(2);
  }
}

/** The hook's JSON input from stdin. Unreadable, malformed or tool-less input blocks the call. */
export function readHookInput(name) {
  let raw = '';
  try {
    raw = fs.readFileSync(0, 'utf8');
  } catch {
    // fall through: parse fails below
  }
  try {
    const o = JSON.parse(raw);
    if (o && typeof o === 'object' && !Array.isArray(o) && o.tool_input && typeof o.tool_input === 'object') return o;
  } catch {
    // fall through
  }
  return blockAndExit(`${name}: could not read a tool call from the hook input, so the call is refused`);
}
