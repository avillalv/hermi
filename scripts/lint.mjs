import { run } from "./run.mjs";

const code =
  run(process.execPath, ["node_modules/eslint/bin/eslint.js", "apps/web", "packages"]) ||
  run(process.execPath, ["node_modules/typescript/bin/tsc", "--noEmit", "-p", "apps/web"]) ||
  run("uv", ["run", "--no-sync", "ruff", "check", "apps/api", "apps/worker"]) ||
  run(process.execPath, ["scripts/spec-lint.mjs"]);
process.exit(code);
