# ruff: noqa: E501
"""The claude_cli backend (06 section 2.7): one `claude -p` process per call, development only.

This is the only file that spawns a process (a forbidden-imports test enforces it). Ported from the Trip Planner
runner: STRIPPED_ENV, find_claude, auth_status, Watchdog, StderrDrain, the stdin writer thread, guard_problem and
explain_failure. Not ported: the MCP bridge. The process is spawned with Popen in a worker thread (asyncio
subprocesses need the Proactor loop, psycopg async needs the Selector loop on Windows).

Process-tree kill uses `taskkill /T /F` on Windows and a process group on POSIX; psutil is not in the stack.
"""

import asyncio
import contextlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import uuid
from collections import deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import IO, Any

from hermi.config import Settings, claude_cli_allowed
from hermi.modules.ai.metering import cli_cost_micros, usage_from_response
from hermi.modules.ai.policy import cli_disallowed_tools
from hermi.providers import ProviderError
from hermi.providers.ai.base import (
    AgentOutcome,
    ProviderRefused,
    ProviderRequest,
    ProviderResult,
    ToolRunner,
)
from hermi.providers.ai.claude_stream import WEB_TOOLS, EvidenceCollector, StreamParser, StreamState

WATCHDOG_SECONDS = 8 * 60  # 06 section 2.7
WATCH_SECONDS = 2  # how often the watchdog looks; tests shrink it
KEEP_RUN_DIRS = 30
DEFAULT_MAX_SEARCHES = 10  # the agent run caps of 06 section 2.4; callers pass the action's own caps in `extra`
DEFAULT_MAX_FETCHES = 10
SIGN_IN_HELP = (
    "Claude Code isn't signed in, or its sign-in expired. In a terminal on this PC, run claude and type "
    "/login, then try again."
)
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)  # no console flash on Windows
_SHIMS = (".cmd", ".bat", ".ps1")

# Set when the app stops; running calls are killed.
shutting_down = threading.Event()


# --- environment and binary ----------------------------------------------------------------


def _secret_env_names() -> frozenset[str]:
    """Env names of the app's own secrets: every Settings field that is a SecretStr or a database URL."""
    return frozenset(
        n.upper()
        for n, f in Settings.model_fields.items()
        if "SecretStr" in str(f.annotation) or n.startswith(("database_url", "test_database_url"))
    )


_SECRET_NAME = re.compile(r"SECRET|TOKEN|PASSWORD|PRIVATE_KEY|API_KEY|DATABASE_URL|ENCRYPTION_KEY|SERVICE_ROLE")


def strip_env(base: Mapping[str, str]) -> dict[str, str]:
    """The child environment: no ANTHROPIC_*, no CLAUDE_CODE_* (except the git-bash path), no CLAUDECODE and none
    of the app's own secrets. An inherited API key would silently move the run off the subscription."""
    secrets = _secret_env_names()
    out = {}
    for k, v in base.items():
        u = k.upper()
        if u == "CLAUDE_CODE_GIT_BASH_PATH":
            out[k] = v
        elif u.startswith(("ANTHROPIC_", "CLAUDE_CODE_")) or u == "CLAUDECODE" or u in secrets or _SECRET_NAME.search(u):
            continue
        else:
            out[k] = v
    return out


def find_claude(settings: Settings, which: Callable[[str], str | None] = shutil.which) -> list[str] | None:
    """The native claude binary: CLAUDE_CLI_PATH, else PATH. A .cmd, .bat or .ps1 shim is refused (cmd.exe would
    re-parse the arguments and a kill would hit the shim)."""
    path = settings.claude_cli_path or which("claude.exe" if sys.platform == "win32" else "claude")
    if not path or path.lower().endswith(_SHIMS):
        return None
    return [path]


@dataclass(frozen=True)
class ClaudeAuth:
    signed_in: bool | None  # None when the CLI could not say
    method: str | None = None


def auth_status(claude: list[str], env: Mapping[str, str]) -> ClaudeAuth:
    """Ask `claude auth status` (no model call) whether runs would be signed in."""
    try:
        out = subprocess.run(
            [*claude, "auth", "status"], capture_output=True, stdin=subprocess.DEVNULL, text=True,
            encoding="utf-8", errors="replace", timeout=20, check=False, env=strip_env(env),
            creationflags=NO_WINDOW,
        )  # fmt: skip
        data = json.loads(out.stdout)
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return ClaudeAuth(None)
    if not isinstance(data, dict) or "loggedIn" not in data:
        return ClaudeAuth(None)
    return ClaudeAuth(bool(data["loggedIn"]), data.get("authMethod"))


# --- command -------------------------------------------------------------------------------


def build_command(
    claude: list[str],
    *,
    model: str,
    system_file: Path,
    web: bool,
    schema: dict[str, Any] | None,
    max_budget_usd: float,
    max_turns: int,
) -> list[str]:
    """The one place the command line is built (06 section 2.7). The prompt goes on stdin."""
    argv = [
        *claude, "-p", "--model", model, "--output-format", "stream-json", "--verbose",
        "--safe-mode", "--restricted", "--strict-mcp-config", "--no-session-persistence",
        "--permission-mode", "dontAsk", "--permission-prompts", "none", "--disable-slash-commands",
        "--system-prompt-file", str(system_file),
    ]  # fmt: skip
    if web:
        argv += ["--tools", ",".join(WEB_TOOLS), "--allowedTools", *WEB_TOOLS]
        argv += ["--disallowedTools", *cli_disallowed_tools()]
    else:
        argv += ["--tools", ""]
    if schema is not None:
        argv += ["--json-schema", json.dumps(schema, separators=(",", ":"))]
    return [*argv, "--max-budget-usd", f"{max_budget_usd:.6f}", "--max-turns", str(max_turns)]


# --- processes -----------------------------------------------------------------------------


_SWEEP = (
    "$all = Get-CimInstance Win32_Process; $ids = @({pid}); "
    "do {{ $n = @($all | Where-Object {{ $ids -contains $_.ParentProcessId -and $ids -notcontains $_.ProcessId }} "
    "| ForEach-Object {{ $_.ProcessId }}); $ids += $n }} while ($n.Count -gt 0); "
    "$ids | Where-Object {{ $_ -ne {pid} }} | ForEach-Object {{ Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }}"
)


def kill_tree(proc: subprocess.Popen) -> None:
    """Kill the process and everything it started, also after the parent exited (a grandchild can still hold
    the stdout pipe). The saved pid doubles as the process group id on POSIX (start_new_session)."""
    if sys.platform == "win32":
        if proc.poll() is None:
            cmd = ["taskkill", "/T", "/F", "/PID", str(proc.pid)]
        else:  # taskkill cannot walk a tree whose root is gone; Windows keeps ParentProcessId on the children
            cmd = ["powershell", "-NoProfile", "-NonInteractive", "-Command", _SWEEP.format(pid=proc.pid)]
        subprocess.run(cmd, capture_output=True, check=False, creationflags=NO_WINDOW, timeout=30)
    else:
        with contextlib.suppress(OSError):
            os.killpg(proc.pid, signal.SIGKILL)
    with contextlib.suppress(OSError):
        proc.kill()


class Watchdog(threading.Thread):
    """Stops the process on timeout, on cancel, or when the app shuts down."""

    def __init__(self, proc: subprocess.Popen, deadline: float, is_cancelled: Callable[[], bool] | None) -> None:
        super().__init__(daemon=True, name="claude-watchdog")
        self.proc, self.deadline, self.is_cancelled = proc, deadline, is_cancelled
        self.reason: str | None = None
        self.finished = threading.Event()

    def stop(self, reason: str) -> None:
        if self.reason is None:
            self.reason = reason
        kill_tree(self.proc)

    def run(self) -> None:
        while not self.finished.wait(WATCH_SECONDS):
            if self.proc.poll() is not None:
                # The parent is gone. If the reader is still blocked a tick later, a grandchild holds our
                # pipes: sweep it, then stop watching.
                if not self.finished.wait(WATCH_SECONDS):
                    kill_tree(self.proc)
                return
            if shutting_down.is_set():
                self.stop("shutdown")
            elif time.monotonic() >= self.deadline:
                self.stop("timeout")
            elif self.is_cancelled:
                with contextlib.suppress(Exception):
                    if self.is_cancelled():
                        self.stop("cancelled")


class StderrDrain(threading.Thread):
    """Reads stderr so the pipe never fills, keeping the last lines."""

    def __init__(self, stream: IO[str]) -> None:
        super().__init__(daemon=True, name="claude-stderr")
        self.stream = stream
        self.lines: deque[str] = deque(maxlen=15)

    def run(self) -> None:
        for line in self.stream:
            if line.strip():
                self.lines.append(line.strip())

    def tail(self) -> str:
        return " ".join(self.lines)[-600:]


def _send_prompt(stdin: IO[str], prompt: str) -> None:
    with contextlib.suppress(OSError, ValueError):
        stdin.write(prompt)
        stdin.close()


def prepare_run_dir(root: Path) -> Path:
    """A fresh empty scratch folder; only the most recent ones are kept."""
    root.mkdir(parents=True, exist_ok=True)
    folders = sorted((p for p in root.iterdir() if p.is_dir()), key=lambda p: p.stat().st_mtime, reverse=True)
    for stale in folders[KEEP_RUN_DIRS - 1 :]:
        shutil.rmtree(stale, ignore_errors=True)
    run_dir = root / uuid.uuid4().hex
    run_dir.mkdir()
    return run_dir


def explain_failure(text: str) -> str:
    lower = text.lower()
    if any(k in lower for k in ("authenticat", "oauth", "/login", "not logged in", "log in")):
        return SIGN_IN_HELP
    if "usage limit" in lower or "rate limit" in lower or "limit reached" in lower:
        return "Your Claude usage limit was reached. Try again after it resets."
    if "overloaded" in lower:
        return "Claude was overloaded. Try again in a few minutes."
    return text or "Claude Code reported an error."


def guard_problem(
    state: StreamState, model: str, allowed_models: tuple[str, ...], expected_tools: set[str]
) -> str | None:
    """After the `init` event: the model, tool list, key source and MCP servers must be what the call asked for."""
    if not state.inited and (state.models_seen or state.tool_names or state.result is not None):
        return "Claude didn't report its setup, so the run was stopped."
    if state.inited:
        if state.model != model:
            return f"Claude started with {state.model} instead of {model}, so the run was stopped."
        if set(state.tools) != expected_tools:
            return f"Claude started with tools {sorted(state.tools)} instead of {sorted(expected_tools)}, so the run was stopped."
        if state.api_key_source != "none":
            return f"Claude would bill through {state.api_key_source} instead of the subscription, so the run was stopped."
        if state.mcp_servers:
            return "Claude started with MCP servers, so the run was stopped."
    for seen in state.models_seen:
        if not seen.startswith(allowed_models):
            return f"Claude used {seen} instead of {model}, so the run was stopped."
    return None


_PROBLEMS = {
    "timeout": "The call ran past its time limit and was stopped.",
    "cancelled": "The call was cancelled.",
    "shutdown": "The app stopped before this call finished.",
}


@dataclass
class CliRun:
    status: str  # ok | guard | cap_exceeded | blocked_domain | timeout | cancelled | shutdown | no_result
    problem: str | None
    result: dict[str, Any] | None
    state: StreamState
    evidence: EvidenceCollector
    events: list[dict[str, Any]] = field(default_factory=list)
    exit_code: int | None = None
    stderr_tail: str = ""

    @property
    def searches(self) -> int:
        return self.state.searches

    @property
    def fetches(self) -> int:
        return self.state.fetches


class CliRunFailed(ProviderError):
    """The call did not finish cleanly. `status` says why; `run` keeps the stream, counters and evidence."""

    def __init__(self, status: str, message: str, run: CliRun | None = None) -> None:
        super().__init__(message)
        self.status, self.run = status, run


def run_cli(
    argv: list[str],
    prompt: str,
    cwd: Path,
    *,
    model: str,
    allowed_models: tuple[str, ...],
    expected_tools: set[str],
    max_searches: int,
    max_fetches: int,
    timeout_s: float = WATCHDOG_SECONDS,
    is_cancelled: Callable[[], bool] | None = None,
    env: Mapping[str, str] | None = None,
) -> CliRun:
    """Spawn, feed the prompt, read the stream, enforce caps, guard and watchdog; kill the tree on any breach."""
    try:
        proc = subprocess.Popen(
            argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd,
            env=strip_env(os.environ if env is None else env), text=True, encoding="utf-8", errors="replace",
            creationflags=NO_WINDOW, start_new_session=sys.platform != "win32",
        )  # fmt: skip
    except OSError as e:
        raise CliRunFailed("no_start", f"Couldn't start Claude Code: {e}") from e
    assert proc.stdin and proc.stdout and proc.stderr
    watchdog = Watchdog(proc, time.monotonic() + timeout_s, is_cancelled)
    stderr = StderrDrain(proc.stderr)
    watchdog.start()
    stderr.start()
    # From a thread: if Claude fills stdout before reading its prompt, neither side blocks.
    threading.Thread(target=_send_prompt, args=(proc.stdin, prompt), daemon=True).start()

    parser = StreamParser(max_searches, max_fetches)
    problem: str | None = None
    status: str | None = None
    for line in proc.stdout:
        parser.feed(line)
        if status is None:
            if parser.violation:
                status, problem = parser.violation, parser.problem
            elif p := guard_problem(parser.state, model, allowed_models, expected_tools):
                status, problem = "guard", p
            if status:
                watchdog.stop(status)
    try:
        exit_code = proc.wait(timeout=30)
    except subprocess.TimeoutExpired:
        kill_tree(proc)
        exit_code = proc.wait()
    watchdog.finished.set()
    stderr.join(timeout=5)

    if status is None and watchdog.reason:
        status, problem = watchdog.reason, _PROBLEMS[watchdog.reason]
    if status is None and not parser.state.inited and parser.state.result is not None:
        status, problem = "guard", "Claude didn't report its setup, so the run was stopped."
    if status is None:
        status = "ok" if parser.state.result is not None else "no_result"
        if status == "no_result":
            detail = stderr.tail()
            problem = f"Claude Code exited (code {exit_code}) without finishing."
            problem = f"{problem} {explain_failure(detail)}" if detail else problem
    return CliRun(status, problem, parser.state.result, parser.state, parser.evidence, parser.events, exit_code, stderr.tail())


# --- the provider --------------------------------------------------------------------------

_slots: dict[int, threading.Semaphore] = {}


def _slot(n: int) -> threading.Semaphore:
    return _slots.setdefault(n, threading.Semaphore(max(1, n)))


def _text(x: Any) -> str:
    if isinstance(x, str):
        return x
    if isinstance(x, list):
        return "\n".join(b.get("text", "") for b in x if isinstance(b, dict) and b.get("type") == "text")
    return ""


class ClaudeCliProvider:
    """`req.extra` keys read here: `max_searches`, `max_fetches`, `timeout_s`, `is_cancelled` (agent_run) and
    `stop_micro` (single_call budget). `last_run` holds the stream, counters and evidence of the latest call."""

    name = "claude_cli"

    def __init__(
        self,
        settings: Settings,
        *,
        bind_host: str,
        user_email: str | None = None,
        claude: list[str] | None = None,
    ) -> None:
        # The guard again, so building the provider by hand cannot skip the factory (06 section 2.7).
        if not claude_cli_allowed(settings, bind_host, user_email):
            raise ProviderRefused("claude_cli is not allowed for this environment, host or user")
        self._s, self._claude = settings, claude
        self.last_run: CliRun | None = None

    def _argv_prefix(self) -> list[str]:
        if self._claude is not None:
            return self._claude
        if found := find_claude(self._s):
            return found
        raise CliRunFailed("no_start", "Claude Code wasn't found. Install it, or set CLAUDE_CLI_PATH to claude.exe's full path.")

    async def _call(self, req: ProviderRequest, *, web: bool, max_turns: int, stop_micro: int) -> tuple[CliRun, dict[str, Any]]:
        prefix = self._argv_prefix()
        root = Path(self._s.ai_cli_scratch_dir)
        run_dir = prepare_run_dir(root)
        system_file = root / f"{run_dir.name}.system.md"
        system_file.write_text(_text(req.system), encoding="utf-8")
        argv = build_command(prefix, model=req.model, system_file=system_file, web=web,
                             schema=req.output_schema, max_budget_usd=stop_micro / 1_000_000, max_turns=max_turns)  # fmt: skip
        x = req.extra
        tools = {*WEB_TOOLS} if web else set()
        if req.output_schema is not None:
            tools.add("StructuredOutput")

        def go() -> CliRun:
            with _slot(self._s.ai_cli_max_concurrency):
                return run_cli(
                    argv, "\n\n".join(_text(m.get("content")) for m in req.messages), run_dir,
                    model=req.model, allowed_models=(req.model, self._s.ai_model_fast), expected_tools=tools,
                    max_searches=x.get("max_searches", DEFAULT_MAX_SEARCHES) if web else 0,
                    max_fetches=x.get("max_fetches", DEFAULT_MAX_FETCHES) if web else 0,
                    timeout_s=x.get("timeout_s", WATCHDOG_SECONDS), is_cancelled=x.get("is_cancelled"),
                )  # fmt: skip

        try:
            run = await asyncio.to_thread(go)
        finally:
            system_file.unlink(missing_ok=True)
        self.last_run = run
        if run.status != "ok":
            raise CliRunFailed(run.status, run.problem or run.status, run)
        assert run.result is not None
        return run, run.result

    def _result(self, req: ProviderRequest, run: CliRun, res: dict[str, Any]) -> ProviderResult:
        so = res.get("structured_output")
        text = json.dumps(so) if so is not None else str(res.get("result") or "")
        return ProviderResult(
            provider=self.name,
            model=req.model,
            content=[{"type": "text", "text": text}],
            stop_reason="end_turn",
            usage=replace(usage_from_response(res.get("usage") or {}), web_searches=run.searches),
            cost_usd_micros=cli_cost_micros(float(res.get("total_cost_usd") or 0)),  # notional
            server_tool_use={"web_search_requests": run.searches} if run.searches else {},
        )

    @staticmethod
    def _error(run: CliRun, res: dict[str, Any]) -> CliRunFailed:
        text = str(res.get("result") or res.get("subtype") or "")
        return CliRunFailed("error", explain_failure(text), run)

    async def single_call(self, req: ProviderRequest) -> ProviderResult:
        # A --json-schema call needs at least 2 turns (the StructuredOutput tool call), so never 1.
        run, res = await self._call(req, web=False, max_turns=3, stop_micro=req.extra.get("stop_micro", 500_000))
        if res.get("is_error") or str(res.get("subtype", "")).startswith("error"):
            raise self._error(run, res)
        return self._result(req, run, res)

    async def agent_run(
        self,
        req: ProviderRequest,
        *,
        max_turns: int = 20,
        stop_micro: int = 800_000,
        run_tool: ToolRunner | None = None,  # unused: the CLI runs its own loop and has no client tools
    ) -> AgentOutcome:
        run, res = await self._call(req, web=True, max_turns=max_turns, stop_micro=stop_micro)
        sub = str(res.get("subtype") or "")
        stop = {"error_max_turns": "turn_limit", "error_max_budget_usd": "spend_limit"}.get(sub)
        if stop is None and (res.get("is_error") or sub.startswith("error")):
            raise self._error(run, res)
        r = self._result(req, run, res)
        usage = r.usage
        cost = r.cost_usd_micros
        return AgentOutcome(
            stop or "end_turn", r, int(res.get("num_turns") or 1), usage, cost,
            [*req.messages, {"role": "assistant", "content": r.content}],
        )  # type: ignore[arg-type]  # fmt: skip
