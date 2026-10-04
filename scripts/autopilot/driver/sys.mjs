// Impure helpers shared by run.mjs and status.mjs: processes, ports, files, tool lookup.
// Everything with a decision in it lives in the pure modules next to this one.

import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

export const IS_WIN = process.platform === 'win32';

const MB = 1024 * 1024;

/** Run a command to completion. Never throws: {code, stdout, stderr, error}. */
export function run(cmd, args = [], { cwd, env, input, timeoutMs = 120000 } = {}) {
  const r = spawnSync(cmd, args, { cwd, env, input, encoding: 'utf8', windowsHide: true, timeout: timeoutMs, maxBuffer: 64 * MB });
  return { code: r.status ?? (r.error ? -1 : 1), stdout: r.stdout ?? '', stderr: r.stderr ?? '', error: r.error ?? null, signal: r.signal ?? null };
}

/** Kill a process and everything it started. */
export function killTree(pid) {
  if (!pid) return;
  if (IS_WIN) {
    spawnSync('taskkill', ['/PID', String(pid), '/T', '/F'], { windowsHide: true, stdio: 'ignore' });
    return;
  }
  try {
    process.kill(-pid, 'SIGKILL');
  } catch {
    try {
      process.kill(pid, 'SIGKILL');
    } catch {
      // already gone
    }
  }
}

export function pidAlive(pid) {
  if (!Number.isInteger(pid) || pid <= 0) return false;
  try {
    process.kill(pid, 0);
    return true;
  } catch (e) {
    return e.code === 'EPERM';
  }
}

/** Image name of a pid ("node.exe", "claude.exe") or null if it is gone. */
export function processName(pid) {
  if (IS_WIN) {
    const r = run('tasklist', ['/FI', `PID eq ${pid}`, '/FO', 'CSV', '/NH'], { timeoutMs: 15000 });
    const m = /^"([^"]+)"/.exec(r.stdout.trim());
    return m ? m[1] : null;
  }
  const r = run('ps', ['-o', 'comm=', '-p', String(pid)], { timeoutMs: 5000 });
  return r.stdout.trim() || null;
}

export function processCommandLine(pid) {
  if (IS_WIN) {
    const r = run('powershell', ['-NoProfile', '-NonInteractive', '-Command', `(Get-CimInstance Win32_Process -Filter 'ProcessId=${Number(pid)}').CommandLine`], { timeoutMs: 20000 });
    return r.stdout.trim();
  }
  return run('ps', ['-o', 'command=', '-p', String(pid)], { timeoutMs: 5000 }).stdout.trim();
}

/**
 * Pids listening on a TCP port in the text of `netstat -ano`: IPv4 (0.0.0.0:8100, 127.0.0.1:8100) and
 * IPv6 ([::]:8100, [::1]:8100) lines alike. A dev server often binds only [::1].
 */
export function parseNetstat(text, port) {
  const pids = new Set();
  for (const line of String(text).split(/\r?\n/)) {
    const f = line.trim().split(/\s+/);
    if (f.length >= 5 && /^TCP/i.test(f[0]) && f[3] === 'LISTENING' && f[1].endsWith(`:${port}`)) pids.add(Number(f[4]));
  }
  return [...pids];
}

/** Pids listening on a TCP port. Windows: netstat -ano (IPv4 and IPv6). POSIX: lsof. */
export function portListeners(port) {
  const pids = new Set();
  if (IS_WIN) {
    for (const p of parseNetstat(run('netstat', ['-ano'], { timeoutMs: 30000 }).stdout, port)) pids.add(p);
  } else {
    const r = run('lsof', ['-ti', `tcp:${port}`, '-sTCP:LISTEN'], { timeoutMs: 15000 });
    for (const p of r.stdout.split(/\s+/)) if (p) pids.add(Number(p));
  }
  pids.delete(0);
  pids.delete(4); // System
  return [...pids];
}

/** First existing executable among the PATH entries and extra directories. */
export function findExecutable(names, extraDirs = []) {
  const exts = IS_WIN ? ['.exe'] : [''];
  const pathKey = Object.keys(process.env).find((k) => k.toLowerCase() === 'path') ?? 'PATH';
  const dirs = [...(process.env[pathKey] ?? '').split(path.delimiter).filter(Boolean), ...extraDirs];
  for (const dir of dirs) {
    for (const n of names) {
      for (const e of exts) {
        const p = path.join(dir, n + e);
        try {
          if (fs.statSync(p).isFile()) return p;
        } catch {
          // keep looking
        }
      }
    }
  }
  return null;
}

/** claude.exe by absolute path (never the .cmd shim). AUTOPILOT_CLAUDE overrides. */
export function resolveClaude() {
  if (process.env.AUTOPILOT_CLAUDE && fs.existsSync(process.env.AUTOPILOT_CLAUDE)) return process.env.AUTOPILOT_CLAUDE;
  const home = path.join(os.homedir(), '.local', 'bin', IS_WIN ? 'claude.exe' : 'claude');
  if (fs.existsSync(home)) return home;
  return findExecutable(['claude']);
}

/**
 * Leading arguments for claude or gh, from a JSON array in an environment variable. Unset in real
 * runs. It exists so driver.test.mjs can run the real driver against fake executables (node + a script).
 */
export function preArgs(envName) {
  try {
    const a = JSON.parse(process.env[envName] ?? '[]');
    return Array.isArray(a) ? a.map(String) : [];
  } catch {
    return [];
  }
}

/** gh from PATH, else the default install location. AUTOPILOT_GH overrides (tests only). */
export function resolveGh() {
  if (process.env.AUTOPILOT_GH && fs.existsSync(process.env.AUTOPILOT_GH)) return process.env.AUTOPILOT_GH;
  const onPath = findExecutable(['gh']);
  if (onPath) return onPath;
  const candidates = IS_WIN ? ['C:\\Program Files\\GitHub CLI\\gh.exe', 'C:\\Program Files (x86)\\GitHub CLI\\gh.exe'] : ['/usr/local/bin/gh', '/opt/homebrew/bin/gh'];
  return candidates.find((p) => fs.existsSync(p)) ?? null;
}

export function readJson(file, fallback = null) {
  try {
    return JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch {
    return fallback;
  }
}

/** Write JSON through a temp file so a crash never leaves a half-written state file. */
export function writeJsonAtomic(file, obj) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const tmp = `${file}.${process.pid}.tmp`;
  fs.writeFileSync(tmp, `${JSON.stringify(obj, null, 2)}\n`);
  fs.renameSync(tmp, file);
}

export const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/** Blocking sleep for the few synchronous retry loops (nothing else runs in the driver meanwhile). */
export const sleepSync = (ms) => Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms);

/** Last `bytes` of a file as text (the first line may be cut). */
export function readTail(file, bytes) {
  const fd = fs.openSync(file, 'r');
  try {
    const { size } = fs.fstatSync(fd);
    const start = Math.max(0, size - bytes);
    const buf = Buffer.alloc(size - start);
    fs.readSync(fd, buf, 0, buf.length, start);
    return { text: buf.toString('utf8'), truncatedStart: start > 0, size };
  } finally {
    fs.closeSync(fd);
  }
}
