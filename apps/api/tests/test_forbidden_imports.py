"""Code rules a grep can check: no Windows-only code, one subprocess file, no scheduler library."""

import ast
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SKIP_DIRS = {"node_modules", ".venv", "__pycache__", "dist", "build", ".next", "tests"}
CLAUDE_CLI = "apps/api/hermi/providers/ai/claude_cli.py"
WINDOWS_ONLY = re.compile(
    r"\b(win32api|win32con|win32com|pywin32|msvcrt|winreg|_winapi|ctypes\.windll)\b"
)
WINDOWS_FILES = (".ps1", ".bat", ".cmd")


def sources(*roots: str, suffixes: tuple[str, ...] = (".py",)):
    for root in roots:
        base = REPO / root
        if not base.exists():
            continue
        for path in base.rglob("*"):
            rel = path.relative_to(REPO).parts
            if SKIP_DIRS & set(rel) or not path.is_file() or path.suffix not in suffixes:
                continue
            yield path


def rel(path: Path) -> str:
    return path.relative_to(REPO).as_posix()


def imported_modules(code: str) -> set[str]:
    """Top-level module names imported by a source string (covers `import os, subprocess`)."""
    names: set[str] = set()
    for node in ast.walk(ast.parse(code)):
        if isinstance(node, ast.Import):
            names.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module.split(".")[0])
    return names


SPAWN_CALLS = {"os.system", "os.popen"}


def spawns_process(code: str) -> bool:
    """Calls to os.system, os.popen or asyncio.create_subprocess_* (any aliasing aside)."""
    for node in ast.walk(ast.parse(code)):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                name = f"{node.func.value.id}.{node.func.attr}"
                if name in SPAWN_CALLS or name.startswith("asyncio.create_subprocess_"):
                    return True
    return False


def imports(path: Path, module: str) -> bool:
    return module in imported_modules(path.read_text(encoding="utf-8", errors="ignore"))


def test_the_detectors_catch_hidden_forms() -> None:
    assert "subprocess" in imported_modules("import os, subprocess")
    assert "subprocess" in imported_modules("from subprocess import run")
    assert "apscheduler" in imported_modules("import apscheduler.schedulers.background")
    assert imported_modules("x = 'import subprocess'") == set()
    assert spawns_process("import os\nos.system('dir')")
    assert spawns_process("import os\nos.popen('dir')")
    assert spawns_process("import asyncio\nasyncio.create_subprocess_exec('a')")
    assert not spawns_process("import os\nos.path.join('a', 'b')")


def test_subprocess_only_in_the_claude_cli_provider() -> None:
    bad = []
    for p in sources("apps", "packages"):
        if rel(p) == CLAUDE_CLI:
            continue
        code = p.read_text(encoding="utf-8", errors="ignore")
        if "subprocess" in imported_modules(code) or spawns_process(code):
            bad.append(rel(p))
    assert bad == []


def test_apscheduler_is_not_used_anywhere() -> None:
    assert [rel(p) for p in sources("apps", "packages") if imports(p, "apscheduler")] == []
    for toml in sources("apps", "packages", suffixes=(".toml",)):
        assert "apscheduler" not in toml.read_text(encoding="utf-8").lower()


def test_no_windows_only_code_in_apps_or_packages() -> None:
    py = [
        rel(p)
        for p in sources("apps", "packages")
        if WINDOWS_ONLY.search(p.read_text(encoding="utf-8", errors="ignore"))
    ]
    files = [rel(p) for p in sources("apps", "packages", suffixes=WINDOWS_FILES)]
    assert py == [] and files == []
