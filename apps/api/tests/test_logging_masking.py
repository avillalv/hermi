import json
import logging
import sys

from hermi.logging_setup import JsonFormatter, setup_logging

JWT = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.sig_abc-123"
SECRETS = [JWT, "abc123tok", "sk_live_abcdef123456", "sk-ant-abcdef123456", "hunter2"]


def _fmt(msg, **extra):
    r = logging.makeLogRecord({"msg": msg, "levelname": "INFO", "name": "t", **extra})
    return json.loads(JsonFormatter().format(r))


def test_sensitive_keys_redacted_nested():
    out = _fmt(
        "x",
        api_key="a",
        Authorization="b",
        meta={"password": "c", "ok": 1},
        items=[{"cookie": "d"}],
    )
    out2 = _fmt("x", field_encryption_key="a", private_key="b", trip_id="t1", request_id="r1")
    assert out2["field_encryption_key"] == out2["private_key"] == "[redacted]"
    assert (out2["trip_id"], out2["request_id"]) == ("t1", "r1")
    assert out["api_key"] == out["Authorization"] == "[redacted]"
    assert out["meta"] == {"password": "[redacted]", "ok": 1}
    assert out["items"] == [{"cookie": "[redacted]"}]


def test_secret_shaped_strings_redacted():
    msg = (
        f"Bearer abc123tok {JWT} sk_live_abcdef123456 sk-ant-abcdef123456 "
        "https://x/?token=abc123tok&q=1 api_key=hunter2"
    )
    out = _fmt(msg, note=f"Bearer {JWT}")
    for s in SECRETS:
        assert s not in json.dumps(out)
    assert "q=1" in out["msg"]


def test_exc_masked():
    try:
        raise ValueError("bad password=hunter2")
    except ValueError:
        info = sys.exc_info()
        r = logging.makeLogRecord({"msg": "e", "levelname": "ERROR", "name": "t", "exc_info": info})
    assert "hunter2" not in JsonFormatter().format(r)


def test_setup_logging_output_has_no_secrets(capsys):
    setup_logging("info")
    logging.getLogger("t").info("auth Bearer abc123tok jwt %s", JWT, extra={"token": "abc123tok"})
    err = capsys.readouterr().err
    assert err
    for s in SECRETS:
        assert s not in err


def test_non_json_values_masked_via_str():
    class Obj:
        def __str__(self):
            return "Bearer abc123tok"

    assert "abc123tok" not in json.dumps(_fmt("x", obj=Obj()))
