// npm run setup: prerequisites, .env, dependencies, database roles, migrations, demo seed. Safe to re-run.
// Ported from the Trip Planner scripts/setup.mjs. Never prints a secret value.
import { copyFileSync, existsSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { run } from "./run.mjs";
import { commandVersion, fillSecrets, root } from "./lib/local.mjs";

const step = (m) => console.log(`\n> ${m}`);
function fail(m) {
  console.error(`\nsetup failed: ${m}`);
  process.exit(1);
}
function must(cmd, args, opts = {}) {
  if (run(cmd, args, { cwd: root, ...opts }) !== 0) fail(`"${cmd} ${args.join(" ")}" failed, see the output above.`);
}

step("Checking prerequisites");
const [major, minor] = process.versions.node.split(".").map(Number);
if (major < 22 || (major === 22 && minor < 12)) fail(`Node.js 22.12 or newer is required (found ${process.versions.node}).`);
const uv = commandVersion("uv");
if (!uv) fail("uv is not installed or not on PATH. Install it with: winget install --id astral-sh.uv -e (Windows) or see https://docs.astral.sh/uv/ ");
console.log(`  node ${process.versions.node}, ${uv}`);

step("Preparing .env");
const envPath = join(root, ".env");
if (!existsSync(envPath)) {
  copyFileSync(join(root, ".env.example"), envPath);
  console.log("  Created .env from .env.example");
}
const { text, changed } = fillSecrets(readFileSync(envPath, "utf8"));
if (changed.length) {
  writeFileSync(envPath, text);
  console.log(`  Generated ${changed.length} missing secret(s): ${changed.join(", ")}`);
} else {
  console.log("  .env already complete");
}

step("Installing JavaScript dependencies");
// shortcut: npm is a .cmd shim on Windows and we never spawn .cmd files, so run npm's own cli script.
const npmCli = process.env.npm_execpath;
if (npmCli && existsSync(npmCli)) must(process.execPath, [npmCli, "install", "--no-fund", "--no-audit"]);
else console.log("  (not started from npm; run npm install yourself)");

step("Installing Python dependencies");
must("uv", ["sync"]);

step("Creating database roles and databases");
must(process.execPath, ["scripts/db-init.mjs"]);

if (existsSync(join(root, "apps", "api", "alembic.ini"))) {
  step("Applying migrations");
  must("uv", ["run", "--no-sync", "alembic", "upgrade", "head"], { cwd: join(root, "apps", "api") });
} else {
  console.log("\n(no migrations yet, skipping)");
}

if (existsSync(join(root, "apps", "api", "hermi", "seed"))) {
  step("Seeding demo data");
  must("uv", ["run", "--no-sync", "hermi", "seed", "--demo"]);
}

console.log("\nSetup complete. Start the app with:\n\n    npm run dev\n\nthen open http://localhost:5173\n");
