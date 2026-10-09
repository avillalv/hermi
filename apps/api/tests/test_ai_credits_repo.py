# ruff: noqa: E501  (long SQL strings)
"""WF-041: runs admission, the credit ledger and the credit SQL functions through the repository modules.

Rows are arranged with the system login; the code under test runs as the app login with app.user_id set (RLS applies).
"""

import threading
import uuid

import psycopg
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from hermi import db
from hermi.errors import ApiError
from hermi.modules.ai import repo as ai_repo
from hermi.modules.credits import repo as credits_repo


@pytest.fixture
def engine(db_urls):
    e = create_engine(db.sqlalchemy_url(db_urls["app"]), pool_size=4, max_overflow=0)
    yield e
    e.dispose()


@pytest.fixture
def sys_engine(db_urls):
    e = create_engine(db.sqlalchemy_url(db_urls["system"]))
    yield e
    e.dispose()


def _trip(system_conn, owner):
    return system_conn.execute(
        "INSERT INTO trips (owner_user_id, name, home_currency) VALUES (%s, 'T', 'USD') RETURNING id", (owner,)
    ).fetchone()[0]


def _grant(system_conn, user, credits=100):
    system_conn.execute(
        "INSERT INTO credit_grants (user_id, kind, credits, remaining) VALUES (%s, 'promo', %s, %s)",
        (user, credits, credits),
    )


def _admit(engine, user, trip, kind="deep_research"):
    with db.request_transaction(engine, user) as s:
        return ai_repo.admit_run(s, trip_id=trip, user_id=user, kind=kind, provider="fake")


def test_second_agent_run_is_refused_with_409(engine, system_conn, make_user):
    user, _ = make_user()
    trip = _trip(system_conn, user)
    first = _admit(engine, user, trip, "fare_hunt")
    with pytest.raises(ApiError) as e:
        _admit(engine, user, trip, "deep_research")
    assert (e.value.status, e.value.code) == (409, "run_already_active")
    assert e.value.extra == {"active_run_id": str(first)}
    # A non-agent run and a finished agent run do not count.
    _admit(engine, user, trip, "explain")
    system_conn.execute("UPDATE runs SET status = 'failed', finished_at = now() WHERE user_id = %s AND kind = 'fare_hunt'", (user,))
    _admit(engine, user, trip, "deep_research")


def test_concurrent_agent_runs_admit_exactly_one(engine, system_conn, make_user):
    user, _ = make_user()
    trip = _trip(system_conn, user)
    barrier = threading.Barrier(2)
    results: list = []

    def go():
        try:
            with db.request_transaction(engine, user) as s:
                barrier.wait(timeout=10)
                results.append(ai_repo.admit_run(s, trip_id=trip, user_id=user, kind="deep_research", provider="fake"))
        except ApiError as exc:
            results.append(exc)

    threads = [threading.Thread(target=go) for _ in range(2)]
    [t.start() for t in threads]
    [t.join(timeout=30) for t in threads]
    errs = [r for r in results if isinstance(r, ApiError)]
    assert len(results) == 2 and len(errs) == 1 and errs[0].code == "run_already_active"
    n = system_conn.execute("SELECT count(*) FROM runs WHERE user_id = %s", (user,)).fetchone()[0]
    assert n == 1


def test_ledger_idempotency_key_is_unique(engine, system_conn, make_user):
    user, _ = make_user()
    trip = _trip(system_conn, user)
    _grant(system_conn, user)
    key = f"{user}:{uuid.uuid4()}"
    with db.request_transaction(engine, user) as s:
        first = credits_repo.reserve_credits(s, user_id=user, trip_id=trip, amount=10, action="explain", run_id=None, idempotency_key=key)
    with db.request_transaction(engine, user) as s:  # a replay returns the original reservation and writes nothing
        again = credits_repo.reserve_credits(s, user_id=user, trip_id=trip, amount=10, action="explain", run_id=None, idempotency_key=key)
    assert again == first
    assert system_conn.execute("SELECT count(*) FROM credit_ledger WHERE idempotency_key = %s", (key,)).fetchone()[0] == 1
    assert system_conn.execute("SELECT sum(remaining) FROM credit_grants WHERE user_id = %s", (user,)).fetchone()[0] == 90
    gid = system_conn.execute("SELECT grant_id FROM credit_ledger WHERE idempotency_key = %s", (key,)).fetchone()[0]
    with pytest.raises(psycopg.errors.UniqueViolation):  # the index, not just the function, refuses a duplicate
        system_conn.execute(
            "INSERT INTO credit_ledger (user_id, grant_id, entry_type, delta, reservation_id, idempotency_key) VALUES (%s, %s, 'reserve', -1, %s, %s)",
            (user, gid, first, key),
        )
    nogrant = f"dup-nogrant:{uuid.uuid4()}"
    insert = "INSERT INTO credit_ledger (user_id, entry_type, delta, idempotency_key) VALUES (%s, 'clawback', -1, %s)"
    system_conn.execute(insert, (user, nogrant))
    with pytest.raises(psycopg.errors.UniqueViolation):  # a grant-less row with the same key and type
        system_conn.execute(insert, (user, nogrant))


def test_ai_usage_idempotency_key_is_unique(system_conn, make_user):
    user, _ = make_user()
    insert = "INSERT INTO ai_usage (user_id, action, idempotency_key) VALUES (%s, 'explain', %s)"
    key = f"{user}:{uuid.uuid4()}"
    system_conn.execute(insert, (user, key))
    with pytest.raises(psycopg.errors.UniqueViolation):
        system_conn.execute(insert, (user, key))


def test_reserve_refused_with_credit_debt_and_settle_pays_it(engine, sys_engine, system_conn, make_user):
    user, _ = make_user()
    trip = _trip(system_conn, user)
    _grant(system_conn, user, 20)
    with Session(sys_engine) as w:  # record_credit_debt and settle_credit_debt are worker-only
        credits_repo.record_credit_debt(w, user, 5, f"refund:{uuid.uuid4()}")
        w.commit()
    with pytest.raises(ApiError) as e:
        with db.request_transaction(engine, user) as s:
            credits_repo.reserve_credits(s, user_id=user, trip_id=trip, amount=10, action="explain", run_id=None, idempotency_key=f"k:{uuid.uuid4()}")
    assert (e.value.status, e.value.code, e.value.extra) == (402, "insufficient_credits", {"blocked": True})
    assert system_conn.execute("SELECT count(*) FROM credit_ledger WHERE user_id = %s AND entry_type = 'reserve'", (user,)).fetchone()[0] == 0
    with Session(sys_engine) as w:  # paying the debt down from the grant lifts the block
        assert credits_repo.settle_credit_debt(w, user) == 5
        w.commit()
    with db.request_transaction(engine, user) as s:
        res = credits_repo.reserve_credits(s, user_id=user, trip_id=trip, amount=10, action="explain", run_id=None, idempotency_key=f"k:{uuid.uuid4()}")
        assert credits_repo.settle_credits(s, res, 4) == 6  # 6 credits go back to the grant


def test_short_balance_is_402_and_grant_functions_are_idempotent(engine, system_conn, make_user):
    user, _ = make_user()
    trip = _trip(system_conn, user)
    with pytest.raises(ApiError) as e:
        with db.request_transaction(engine, user) as s:
            credits_repo.reserve_credits(s, user_id=user, trip_id=trip, amount=1, action="explain", run_id=None, idempotency_key=f"k:{uuid.uuid4()}")
    assert (e.value.status, e.value.code) == (402, "insufficient_credits")
    assert e.value.extra == {"credits": {"needed": 1, "balance": 0}}
    for _ in range(2):
        with db.request_transaction(engine, user) as s:
            credits_repo.ensure_free_monthly_grant(s, user)
            credits_repo.ensure_taster_grant(s, user)
    kinds = [r[0] for r in system_conn.execute("SELECT coalesce(period_key, kind::text) FROM credit_grants WHERE user_id = %s", (user,)).fetchall()]
    assert kinds.count("taster") == 1 and sum(k != "taster" for k in kinds) == 1
