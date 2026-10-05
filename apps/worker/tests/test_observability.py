# ruff: noqa: E501
import json
import logging

import sentry_sdk
from sentry_sdk.transport import Transport

from hermi.config import Settings
from hermi_worker.observability import job_context, start


class Capture(Transport):
    events: list = []

    def capture_envelope(self, envelope):
        if envelope.get_event():
            self.events.append(envelope.get_event())


def test_job_lines_carry_job_and_run_ids(capsys):
    start(Settings(_env_file=None, environment="ci"))
    with job_context("j1", "r1"):
        logging.getLogger("w").info("working on ana@example.com")
    err = capsys.readouterr().err
    line = json.loads(err.splitlines()[-1])
    assert (line["job_id"], line["run_id"]) == ("j1", "r1")
    assert "ana@example.com" not in err


def test_worker_sentry_event_has_release_environment_and_job_tags(monkeypatch):
    import hermi_worker.observability as obs

    s = Settings(
        _env_file=None,
        environment="staging",
        release_sha="abc123d",
        sentry_dsn="https://k@o1.ingest.sentry.io/1",
    )
    t = Capture()
    t.events = []
    real = obs.init_sentry
    monkeypatch.setattr(obs, "init_sentry", lambda *a, **k: real(*a, transport=t, **k))
    assert start(s) is True
    try:
        with job_context("j9", "r9"):
            sentry_sdk.capture_exception(RuntimeError("x"))
        sentry_sdk.flush()
        (ev,) = t.events
        assert (ev["release"], ev["environment"]) == ("abc123d", "staging")
        assert (ev["tags"]["job_id"], ev["tags"]["run_id"]) == ("j9", "r9")
    finally:
        sentry_sdk.get_client().close()
        sentry_sdk.init()
