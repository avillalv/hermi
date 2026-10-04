import { run } from "./run.mjs";

process.exit(
  run(process.execPath, ["--test", "scripts/lib/local.test.mjs", "scripts/check-copy.test.mjs", "scripts/security-workflow.test.mjs", "infra/render/render.test.mjs", "infra/scripts/check-mail-auth.test.mjs"]) ||
    run(process.execPath, ["scripts/test-api.mjs"]) ||
    run(process.execPath, ["../../node_modules/vitest/vitest.mjs", "run"], { cwd: "apps/web" }),
);
