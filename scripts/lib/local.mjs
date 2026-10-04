// Helpers shared by the local run scripts (setup, db:init, doctor, dev, smoke). No values are ever printed here.
import { spawn, spawnSync } from "node:child_process";
import { randomBytes } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import net from "node:net";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

export const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
export const PLACEHOLDER = "change-me";
// Generated local secrets that start blank in .env.example. Format: url-safe base64 of 32 random bytes.
export const GENERATED_BLANKS = ["FIELD_ENCRYPTION_KEY", "ADMIN_SESSION_SECRET", "UNSUBSCRIBE_SECRET"];
export const ROLE_URL_KEYS = {
  api: "DATABASE_URL",
  worker: "DATABASE_URL_SYSTEM",
  admin: "DATABASE_URL_ADMIN",
  migrate: "MIGRATION_DATABASE_URL",
};
const TEST_URL_KEYS = {
  TEST_DATABASE_URL: "api",
  TEST_DATABASE_URL_SYSTEM: "worker",
  TEST_MIGRATION_DATABASE_URL: "migrate",
};

const secret = (bytes = 24) => randomBytes(bytes).toString("base64url");

/** Parse KEY=value lines (no export; strips one pair of surrounding quotes). */
export function parseEnv(text) {
  const out = {};
  for (const line of text.split(/\r?\n/)) {
    const m = /^([A-Za-z_][A-Za-z0-9_]*)=(.*)$/.exec(line);
    if (m) out[m[1]] = m[2].trim().replace(/^(["'])(.*)\1$/, "$2");
  }
  return out;
}

const urlRe = (key) => new RegExp(`^(${key}=[^:\\n]*://[^:\\n]+:)${PLACEHOLDER}(@.*)$`, "m");

/**
 * Fill generated secrets into .env text. Never overwrites a real value: only the placeholder
 * password in the role URLs (one fresh password per role, shared with its test URL) and the
 * blanks in GENERATED_BLANKS. Returns { text, changed } where changed lists key names only.
 */
export function fillSecrets(text, gen = secret) {
  const changed = [];
  let out = text;
  for (const key of Object.values(ROLE_URL_KEYS)) {
    if (urlRe(key).test(out)) {
      const pw = gen();
      out = out.replace(urlRe(key), (_, a, b) => `${a}${pw}${b}`);
      changed.push(key);
    }
  }
  for (const [key, role] of Object.entries(TEST_URL_KEYS)) {
    const pw = dbUrlParts(parseEnv(out)[ROLE_URL_KEYS[role]]).password;
    if (urlRe(key).test(out) && pw && pw !== PLACEHOLDER) {
      out = out.replace(urlRe(key), (_, a, b) => `${a}${pw}${b}`);
      changed.push(key);
    }
  }
  for (const key of GENERATED_BLANKS) {
    const re = new RegExp(`^${key}=[ \\t]*$`, "m");
    if (re.test(out)) {
      out = out.replace(re, `${key}=${gen(32)}`);
      changed.push(key);
    }
  }
  return { text: out, changed };
}

/** Split a postgresql URL into parts. */
export function dbUrlParts(url) {
  try {
    const u = new URL((url ?? "").replace(/^postgresql\+\w+:/, "postgresql:"));
    return {
      user: decodeURIComponent(u.username),
      password: decodeURIComponent(u.password),
      host: u.hostname || "localhost",
      port: u.port || "5432",
      database: u.pathname.replace(/^\//, ""),
    };
  } catch {
    return { user: "", password: "", host: "localhost", port: "5432", database: "" };
  }
}

/** Only `hermi` and `hermi_*` databases may be created or touched by these scripts. */
export const isHermiDb = (name) => /^hermi(_[a-z0-9_]+)?$/.test(name ?? "");

/** .env under the root (if any) overlaid by the process environment, which wins. */
export function loadEnv(rootDir = root, procEnv = process.env) {
  const p = join(rootDir, ".env");
  const file = existsSync(p) ? parseEnv(readFileSync(p, "utf8")) : {};
  return { ...file, ...Object.fromEntries(Object.entries(procEnv).filter(([, v]) => v !== undefined)) };
}

/** Where PostgreSQL 18 client tools might live, most specific first. */
export function pgBinCandidates(env = process.env, platform = process.platform) {
  const list = [];
  if (env.PG_BIN) list.push(env.PG_BIN);
  if (platform === "win32") {
    for (const base of [env.ProgramFiles, "C:\\Program Files"].filter(Boolean)) {
      list.push(join(base, "PostgreSQL", "18", "bin"));
    }
  } else {
    list.push(
      "/usr/lib/postgresql/18/bin",
      "/usr/pgsql-18/bin",
      "/opt/homebrew/opt/postgresql@18/bin",
      "/usr/local/opt/postgresql@18/bin",
    );
  }
  return list;
}

const exe = (name) => (process.platform === "win32" ? `${name}.exe` : name);

/** Path of the PostgreSQL 18 psql, or null. Falls back to PATH when it reports version 18. */
export function findPsql(env = process.env) {
  for (const dir of pgBinCandidates(env)) {
    const p = join(dir, exe("psql"));
    if (existsSync(p)) return p;
  }
  const r = spawnSync("psql", ["--version"], { encoding: "utf8" });
  return r.status === 0 && /\b18\./.test(r.stdout) ? "psql" : null;
}

export function pgpassPath(env = process.env, platform = process.platform) {
  if (env.PGPASSFILE) return env.PGPASSFILE;
  return platform === "win32"
    ? join(env.APPDATA ?? "", "postgresql", "pgpass.conf")
    : join(env.HOME ?? "", ".pgpass");
}

export function commandVersion(cmd, args = ["--version"]) {
  const r = spawnSync(cmd, args, { encoding: "utf8" });
  return r.status === 0 ? (r.stdout || r.stderr).trim().split(/\r?\n/)[0] : null;
}

function probe(port, host) {
  return new Promise((resolve) => {
    const s = net.connect({ port, host });
    s.once("connect", () => (s.destroy(), resolve(true)));
    s.once("error", () => resolve(false));
  });
}

/** True when something listens on the port on IPv4 or IPv6 loopback (Vite may bind only ::1). */
export async function portInUse(port) {
  return (await probe(port, "127.0.0.1")) || (await probe(port, "::1"));
}

/** Reject a password that psql \set would misread (used by db:init). */
export const isSafePsqlValue = (v) => !/[\\\r\n]/.test(String(v));

/** Kill a child and everything under it. */
export function killTree(child) {
  if (!child?.pid || child.exitCode !== null) return;
  if (process.platform === "win32") {
    spawnSync("taskkill", ["/T", "/F", "/PID", String(child.pid)], { stdio: "ignore" });
  } else {
    try {
      process.kill(-child.pid, "SIGTERM");
    } catch {
      child.kill("SIGTERM");
    }
  }
}

/** Start a child in its own process group (POSIX) so killTree reaches the whole tree. */
export function startChild(cmd, args, opts = {}) {
  return spawn(cmd, args, { stdio: "inherit", detached: process.platform !== "win32", ...opts });
}
