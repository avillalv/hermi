import { run } from "./run.mjs";

process.exit(run("uv", ["run", "--no-sync", "ruff", "format", "apps/api", "apps/worker"]));
