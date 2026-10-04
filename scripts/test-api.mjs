import { run } from "./run.mjs";

let code = 0;
for (const dir of ["apps/api", "apps/worker"]) {
  code ||= run("uv", ["run", "--no-sync", "pytest", "-q"], { cwd: dir });
}
process.exit(code);
