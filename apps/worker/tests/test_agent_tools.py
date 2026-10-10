# ruff: noqa: E501
"""WF-049.2: the client tool set and the executor's binding rules, without a database."""

import asyncio

from hermi_worker.agents.tools import (
    CLIENT_TOOLS,
    Evidence,
    ToolContext,
    ToolExecutor,
    ToolOutput,
    check_schema,
)


def names() -> list[str]:
    return [t["name"] for t in CLIENT_TOOLS]


def test_the_five_client_tools_are_strict_and_closed() -> None:
    assert names() == [
        "submit_flight_quotes",
        "add_note",
        "lookup_airports",
        "get_task",
        "finish_run",
    ]
    for t in CLIENT_TOOLS:
        assert t["strict"] is True and t["input_schema"]["additionalProperties"] is False
        assert set(t["input_schema"]["required"]) == set(t["input_schema"]["properties"])


def test_no_tool_takes_an_id_the_model_could_aim_at_another_account() -> None:
    forbidden = {"user_id", "trip_id", "run_id", "route_id", "account_id"}
    for t in CLIENT_TOOLS:
        props = t["input_schema"]["properties"]
        assert not forbidden & set(props)
        for sub in props.values():
            assert not forbidden & set((sub.get("items") or {}).get("properties", {}))


def test_executor_rejects_ids_the_schema_does_not_name_before_any_handler_runs() -> None:
    called: list = []
    ex = ToolExecutor(
        {"add_note": lambda a, c: called.append(a) or ToolOutput("ok")},
        ToolContext(Evidence(), lambda *a, **k: None),
    )
    bad = {
        "title": "t",
        "body": "b",
        "urls": ["https://example.com"],
        "topic": "events",
        "trip_id": "1",
    }
    out = asyncio.run(ex.run({"id": "x", "name": "add_note", "input": bad}))
    assert out["is_error"] is True and called == []
    assert check_schema(CLIENT_TOOLS[1]["input_schema"], bad) == "input.trip_id is not allowed"


def test_get_task_and_lookup_take_only_what_their_schema_names() -> None:
    by = {t["name"]: t["input_schema"] for t in CLIENT_TOOLS}
    assert (
        check_schema(by["get_task"], {}) is None
        and check_schema(by["get_task"], {"trip_id": "x"}) is not None
    )
    assert (
        check_schema(by["lookup_airports"], {"query": "Lisbon"}) is None
        and check_schema(by["lookup_airports"], {"query": "L"}) is not None
    )
