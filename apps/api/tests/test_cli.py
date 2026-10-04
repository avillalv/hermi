import sys

import pytest

from hermi.cli import uvicorn_kwargs


@pytest.mark.parametrize(
    ("platform", "loop"), [("win32", "asyncio:SelectorEventLoop"), ("linux", "auto")]
)
def test_loop_by_platform(monkeypatch, platform, loop):
    monkeypatch.setattr(sys, "platform", platform)
    assert uvicorn_kwargs()["loop"] == loop
