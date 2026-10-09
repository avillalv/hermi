# ruff: noqa: E501
"""WF-020.3: revision 0015_seed and `hermi seed` (03 sections 10 and 11), and the whole-chain checks.

Seed rows are read as the worker login (TEST_DATABASE_URL_SYSTEM): the seed tables are plain reference tables.
"""

import os
import re
from pathlib import Path

import psycopg
import pytest
from alembic import command
from alembic.script import ScriptDirectory
from tests.test_migrations import MIGRATE_URL, _alembic_cfg, _need_db

from hermi import cli, db

SPEC = Path(__file__).resolve().parents[3] / "app-buildout" / "phase-1-launch" / "03-database-schema.md"
SYSTEM_URL = os.environ.get("TEST_DATABASE_URL_SYSTEM")
SEED_TABLES = ["plans", "store_products", "credit_action_prices", "affiliate_programs", "feature_flags", "kill_switches"]


@pytest.fixture(scope="module")
def migrated():
    _need_db()
    if not SYSTEM_URL:
        msg = "TEST_DATABASE_URL_SYSTEM is not set (npm run test:api loads it from .env)"
        if os.environ.get("CI"):
            pytest.fail(msg)
        pytest.skip(msg)
    cfg = _alembic_cfg(MIGRATE_URL)
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    return cfg


@pytest.fixture
def sysc(migrated):
    with psycopg.connect(db.psycopg_url(SYSTEM_URL), autocommit=True) as c:
        yield c


def _counts(c):
    return {t: c.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in SEED_TABLES}


# --- chain (no database needed) ----------------------------------------------------------------------


def test_chain_is_one_linear_head_0001_to_0025():
    s = ScriptDirectory.from_config(_alembic_cfg())
    assert s.get_heads() == ["0025_notification_prefs"]
    revs = list(s.walk_revisions())  # head first
    assert len(revs) == 25
    ids = [r.revision for r in reversed(revs)]
    assert [i[:4] for i in ids] == [f"{n:04d}" for n in range(1, 26)]
    assert all(r.down_revision == (ids[i - 1] if i else None) for i, r in enumerate(reversed(revs)))


# --- every table of 03 section 5 exists --------------------------------------------------------------


def test_every_table_of_03_section_5_exists_and_nothing_else(sysc):
    text = SPEC.read_text(encoding="utf-8")
    sec5 = text[text.index("\n## 5. Tables (DDL)") : text.index("\n## 6. Row-level security")]
    spec = set(re.findall(r"^CREATE (?:UNLOGGED )?TABLE (\w+) \(", sec5, re.M))
    assert len(spec) > 60
    have = {
        r[0]
        for r in sysc.execute(
            "SELECT relname FROM pg_class WHERE relnamespace = 'public'::regnamespace AND relkind IN ('r', 'p') AND NOT relispartition"
        )
        if not r[0].startswith(("procrastinate_", "alembic_"))
    }
    assert spec - have == set(), "tables in 03 missing from the database"
    assert have - spec == set(), "tables in the database that 03 section 5 does not define"


# --- seed contents -----------------------------------------------------------------------------------


def test_seed_rows_match_03_section_11(sysc):
    assert _counts(sysc) == {
        "plans": 6,
        "store_products": 6,
        "credit_action_prices": 7,
        "affiliate_programs": 20,
        "feature_flags": 22,
        "kill_switches": 37 + 20,
    }
    free, plus, ppass = (
        sysc.execute("SELECT limits, monthly_credits, kind FROM plans WHERE code = %s", (c,)).fetchone() for c in ("free", "plus", "trip_pass")
    )
    assert free[0]["collaborators"] == 1 and free[0]["active_trips"] == 2 and free[0]["monthly_ceiling_micros"] == 250000 and free[1] == 12
    assert plus[0]["live_routes"] == 3 and plus[0]["hide_presentation_footer"] is True and plus[1] == 60
    assert ppass[2] == "pass" and ppass[0]["live_checks_max"] == 60 and "active_trips" not in ppass[0]
    assert sysc.execute("SELECT price_minor, currency, trial_days FROM store_products WHERE product_id = 'hermi_plus_annual'").fetchone() == (3999, "USD", 7)
    assert sysc.execute("SELECT credits, credits_cached, hard_stop_micros FROM credit_action_prices WHERE action = 'agent_run'").fetchone() == (40, 8, 800000)
    assert sysc.execute("SELECT credits, hard_stop_micros FROM credit_action_prices WHERE action = 'explain'").fetchone() == (1, 10000)
    assert sysc.execute("SELECT status FROM affiliate_programs WHERE code = 'travelpayouts_ekta'").fetchone() == ("planned",)
    assert sysc.execute("SELECT count(*) FROM affiliate_programs WHERE code ILIKE '%airbnb%'").fetchone() == (0,)
    assert sysc.execute("SELECT enabled FROM feature_flags WHERE key = 'serpapi_live_fares'").fetchone() == (False,)
    assert sysc.execute("SELECT rules->>'referrer' FROM feature_flags WHERE key = 'setting_referral_credits'").fetchone() == ("20",)
    assert sysc.execute("SELECT kind FROM feature_flags WHERE key = 'setting_calendar_polling'").fetchone() == ("setting",)
    assert sysc.execute("SELECT count(*) FROM kill_switches WHERE engaged").fetchone() == (0,)
    assert sysc.execute("SELECT count(*) FROM kill_switches WHERE key = 'affiliate.viator'").fetchone() == (1,)


def test_seed_twice_changes_nothing(migrated, sysc, monkeypatch):
    before = _counts(sysc)
    snapshot = sysc.execute("SELECT code, limits FROM plans ORDER BY code").fetchall()
    monkeypatch.setenv("MIGRATION_DATABASE_URL", MIGRATE_URL)
    cli.main(["seed"])
    cli.main(["seed"])
    assert _counts(sysc) == before
    assert sysc.execute("SELECT code, limits FROM plans ORDER BY code").fetchall() == snapshot


def test_seed_does_not_overwrite_an_admin_edit(migrated, sysc, monkeypatch):
    with psycopg.connect(db.psycopg_url(MIGRATE_URL), autocommit=True) as o:
        o.execute("UPDATE credit_action_prices SET credits = 2 WHERE action = 'explain'")
    monkeypatch.setenv("MIGRATION_DATABASE_URL", MIGRATE_URL)
    cli.main(["seed"])
    assert sysc.execute("SELECT credits FROM credit_action_prices WHERE action = 'explain'").fetchone() == (2,)
    with psycopg.connect(db.psycopg_url(MIGRATE_URL), autocommit=True) as o:
        o.execute("UPDATE credit_action_prices SET credits = 1 WHERE action = 'explain'")


def test_down_to_0014_and_up_again_keeps_the_seed_unchanged(migrated, sysc):
    before = _counts(sysc)
    command.downgrade(migrated, "0014_rls")
    assert _counts(sysc) == before  # 0015 downgrade is a no-op
    command.upgrade(migrated, "head")
    assert _counts(sysc) == before
