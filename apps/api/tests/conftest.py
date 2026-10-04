import os

import pytest

from hermi.config import refuse_tests_in_production

# Tests never run against production settings (02 section 7.1, ENVIRONMENT).
refuse_tests_in_production()
# ENVIRONMENT has no default; tests run as ci unless the caller says otherwise.
os.environ.setdefault("ENVIRONMENT", "ci")
# Tests never use a real AI provider (CLAUDE rules: AI_PROVIDER=fake).
os.environ["AI_PROVIDER"] = "fake"


@pytest.fixture(autouse=True)
def _no_root_env(monkeypatch, tmp_path):
    # A developer's root .env must not leak into create_app() or cli tests.
    monkeypatch.setattr("hermi.config.ROOT_ENV_FILE", tmp_path / "no-such.env")
