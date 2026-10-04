// npm run dev: API on 8100 and Vite on 5173. npm start (--preview) builds the web app and serves the build.
// Config comes from .env overlaid by the process environment (the process wins). Stops the whole tree on exit.
import { existsSync } from "node:fs";
import { join } from "node:path";
import { run } from "./run.mjs";
import { killTree, loadEnv, portInUse, root, startChild } from "./lib/local.mjs";

const preview = process.argv.includes("--preview");
const env = loadEnv();
const vite = join(root, "node_modules", "vite", "bin", "vite.js");
if (!existsSync(vite)) {
  console.error("vite is not installed. Run npm run setup.");
  process.exit(1);
}
for (const port of [8100, 5173]) {
  if (await portInUse(port)) {
    console.error(`port ${port} is already in use. Stop the other process first.`);
    process.exit(1);
  }
}
const webDir = join(root, "apps", "web");
if (preview && run(process.execPath, [vite, "build"], { cwd: webDir, env }) !== 0) process.exit(1);

const children = [
  startChild("uv", ["run", "--no-sync", "--package", "hermi-api", "hermi", "api"], { cwd: root, env }),
  startChild(process.execPath, [vite, ...(preview ? ["preview", "--port", "5173", "--strictPort"] : [])], { cwd: webDir, env }),
];

let stopping = false;
function stop(code) {
  if (stopping) return;
  stopping = true;
  children.forEach(killTree);
  process.exit(code);
}
for (const c of children) {
  c.on("error", (e) => (console.error(`failed to start: ${e.message}`), stop(1)));
  c.on("exit", (code) => stop(code ?? 1)); // one dies, both go
}
for (const sig of ["SIGINT", "SIGTERM", "SIGHUP"]) process.on(sig, () => stop(0));
process.on("exit", () => children.forEach(killTree));
