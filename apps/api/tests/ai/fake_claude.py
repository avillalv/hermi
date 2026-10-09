# ruff: noqa: E501
"""Stand-in for `claude` in tests (WF-131.2): prints scripted stream-json for a scenario. Run as
`python fake_claude.py <claude args>`; no .cmd shim. It reads the requested model, tools and schema from argv, so
one script serves the no-tool and the web-tool call.

FAKE_CLAUDE_SCENARIO picks the behavior. FAKE_CLAUDE_RECORD (a file) gets argv, prompt, cwd and the names of any
ANTHROPIC_*, CLAUDE_CODE_* and CLAUDECODE variables that leaked. FAKE_CLAUDE_CHILD_PIDFILE gets the pid of a sleeping grandchild.
"""

import json
import os
import subprocess
import sys
import time


def emit(event: dict) -> None:
    print(json.dumps(event), flush=True)


def arg(name: str, default: str | None = None) -> str | None:
    a = sys.argv
    return a[a.index(name) + 1] if name in a else default


def assistant(*blocks: dict, model: str) -> None:
    emit({"type": "assistant", "message": {"model": model, "role": "assistant", "content": list(blocks)}})


def tool_use(i: str, name: str, **inp: object) -> dict:
    return {"type": "tool_use", "id": i, "name": name, "input": inp}


def tool_result(i: str, text: str, is_error: bool = False) -> None:
    block = {"type": "tool_result", "tool_use_id": i, "content": [{"type": "text", "text": text}]}
    if is_error:
        block["is_error"] = True
    emit({"type": "user", "message": {"role": "user", "content": [block]}})


def result(**over: object) -> None:
    ev = {
        "type": "result", "subtype": "success", "is_error": False, "num_turns": 3, "duration_ms": 4200,
        "result": "done", "total_cost_usd": 0.1234,
        "usage": {"input_tokens": 1000, "cache_creation_input_tokens": 2000, "cache_read_input_tokens": 30000, "output_tokens": 1500},
        "modelUsage": {}, "terminal_reason": "completed",
    }  # fmt: skip
    ev.update(over)
    emit(ev)


def main() -> None:
    scenario = os.environ.get("FAKE_CLAUDE_SCENARIO", "success")
    if sys.argv[1:3] == ["auth", "status"]:
        ok = scenario != "signed_out"
        print(json.dumps({"loggedIn": ok, "authMethod": "claude.ai" if ok else "none"}))
        sys.exit(0 if ok else 1)
    prompt = sys.stdin.read()
    if rec := os.environ.get("FAKE_CLAUDE_RECORD"):
        leaked = sorted(k for k in os.environ if k.startswith(("ANTHROPIC", "CLAUDE_CODE")) or k == "CLAUDECODE")
        with open(rec, "w", encoding="utf-8") as f:
            json.dump({"argv": sys.argv[1:], "prompt": prompt, "cwd": os.getcwd(), "env_names": sorted(os.environ), "leaked": leaked}, f)
    if scenario == "crash":
        print("boom: something broke", file=sys.stderr, flush=True)
        sys.exit(3)

    model = arg("--model", "claude-sonnet-5-5")
    web = arg("--tools") not in ("", None)
    schema = "--json-schema" in sys.argv
    tools = (["WebFetch", "WebSearch"] if web else []) + (["StructuredOutput"] if schema else [])
    if scenario == "no_init":
        assistant({"type": "text", "text": "hi"}, model=model)
        result(structured_output={"ok": True}, result="x")
        return
    if scenario == "orphan":
        # exits at once, leaving a grandchild that holds our stdout open
        child = subprocess.Popen([getattr(sys, "_base_executable", sys.executable), "-c", "import time; time.sleep(120)"])
        if pf := os.environ.get("FAKE_CLAUDE_CHILD_PIDFILE"):
            with open(pf, "w", encoding="utf-8") as f:
                f.write(str(child.pid))
    if scenario in ("hang", "wrong_model"):
        # spawn before init: the runner kills the tree the moment it sees a bad init, so the pidfile must exist by then
        child = subprocess.Popen([getattr(sys, "_base_executable", sys.executable), "-c", "import time; time.sleep(120)"])
        if pf := os.environ.get("FAKE_CLAUDE_CHILD_PIDFILE"):
            with open(pf, "w", encoding="utf-8") as f:
                f.write(str(child.pid))
    emit({
        "type": "system", "subtype": "init", "model": "claude-sonnet-5" if scenario == "wrong_model" else model,
        "claude_code_version": "2.1.288", "tools": ["Bash"] + tools if scenario == "tools_mismatch" else tools,
        "mcp_servers": [{"name": "x", "status": "connected"}] if scenario == "mcp_present" else [], "permissionMode": "dontAsk",
        "apiKeySource": "ANTHROPIC_API_KEY" if scenario == "key_leak" else "none", "session_id": "fake",
    })  # fmt: skip

    if scenario in ("hang", "wrong_model"):
        assistant({"type": "text", "text": "working"}, model=model)
        time.sleep(120)
        return
    if scenario == "orphan":
        return
    if scenario == "midstream_model":
        assistant({"type": "text", "text": "x"}, model="claude-opus-4-1-20250805")
        time.sleep(120)
        return
    if scenario == "auth_error":
        msg = "Failed to authenticate: OAuth session expired"
        assistant({"type": "text", "text": msg}, model="<synthetic>")
        result(is_error=True, result=msg, subtype="success", num_turns=1, total_cost_usd=0)
        sys.exit(1)
    if scenario == "too_many_searches":
        for i in range(5):
            assistant(tool_use(f"s{i}", "WebSearch", query=f"q{i}"), model=model)
            tool_result(f"s{i}", 'Web search results for query: "q"\n\nLinks: [{"title":"A","url":"https://a.example/x"}]\n\nsummary')
        result()
        return
    if scenario == "too_many_fetches":
        for i in range(5):
            assistant(tool_use(f"f{i}", "WebFetch", url=f"https://a.example/{i}", prompt="p"), model=model)
            tool_result(f"f{i}", "answer")
        result()
        return
    if scenario == "blocked_fetch":
        assistant(tool_use("f1", "WebFetch", url="https://www.airbnb.co.kr/rooms/1", prompt="p"), model=model)
        time.sleep(120)  # the runner must kill us on the stream backstop
        return

    if web:
        assistant(tool_use("t1", "WebSearch", query="tokyo fares"), model=model)
        tool_result("t1", 'Web search results for query: "tokyo fares"\n\nLinks: [{"title":"ZIPAIR sale","url":"https://zipair.net/en/sale"},{"title":"B","url":"https://b.example/p"}]\n\nSummary text.')
        assistant(tool_use("t2", "WebFetch", url="https://zipair.net/en/sale", prompt="fares"), model=model)
        tool_result("t2", "Fares from 400 USD.")
    if scenario == "haiku_summary":
        assistant({"type": "text", "text": "page summary"}, model="claude-haiku-4-5-20251001")
    final = {"type": "text", "text": "ok"}
    assistant(final, model=model + "-20251001")
    if scenario == "max_turns":
        result(subtype="error_max_turns", is_error=True, result="", terminal_reason="max_turns")
    elif scenario == "budget":
        result(subtype="error_max_budget_usd", is_error=True, result="")
    elif schema:
        result(structured_output={"ok": True, "scenario": scenario}, result='{"ok": true}')
    else:
        result()


if __name__ == "__main__":
    main()
