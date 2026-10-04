// Run a command with inherited stdio and return its exit code. No shell.
import { spawnSync } from "node:child_process";

export function run(cmd, args, opts = {}) {
  const r = spawnSync(cmd, args, { stdio: "inherit", ...opts });
  if (r.error) {
    console.error(`failed to run ${cmd}: ${r.error.message}`);
    return 1;
  }
  return r.status ?? 1;
}
