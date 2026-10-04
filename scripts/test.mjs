import { run } from "./run.mjs";

process.exit(
  run(process.execPath, ["scripts/test-api.mjs"]) ||
    run(process.execPath, ["../../node_modules/vitest/vitest.mjs", "run"], { cwd: "apps/web" }),
);
