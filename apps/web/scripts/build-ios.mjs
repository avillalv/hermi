// npm run build:ios: the web build for the Capacitor shell. VITE_BUILD_TARGET=ios drops the admin route group
// (08 section 2.1). A node script so it sets the variable the same way on Windows, macOS and Linux.
import { spawnSync } from "node:child_process";
import process from "node:process";

const r = spawnSync("npm run build", { stdio: "inherit", shell: true, env: { ...process.env, VITE_BUILD_TARGET: "ios" } });
process.exit(r.status ?? 1);
