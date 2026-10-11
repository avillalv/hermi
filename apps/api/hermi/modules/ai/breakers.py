# ruff: noqa: E501
"""Automatic breakers (WF-056.1; 06 sections 6.5 and 6.6, 08 sections 6.5 and 10). One `evaluate` pass, run every minute.

Spend is read from ai_usage for the UTC day, as a share of the daily budget (the lower of `setting_ai_global_daily_usd` and
AI_GLOBAL_DAILY_CAP_USD). 80 percent engages ai.free_tier (notify), 95 percent ai.all_but_paid (page), 90 percent of the
SerpApi monthly quota engages provider.serpapi (notify), spend above 1.5x the trailing 7-day mean engages ai.batch, and an
Anthropic 429/529 rate over 50 percent in 5 minutes engages provider.anthropic, which goes half-open after a cooldown:
the next recorded Anthropic call closes it (ok) or re-opens it (failed). A 5 percent rate over 10 minutes only notifies.

Half-open: admission (`ensure_anthropic_allowed`, used by the AI gate and the guest route) lets exactly one request through
per cooldown by claiming the probe with one atomic UPDATE on the kill_switches row (reason becomes "auto: probing",
engaged_at the claim time). `evaluate` judges only calls recorded since that claim. A server failure is a missing status,
5xx, 429 or 529; a 400 is our own request and never counts against the provider.

A breaker writes through flags.engage_switch as actor `system`, so audit_log and NOTIFY come for free. Its marker is
engaged_by NULL with a reason starting "auto:"; release clears only those, never an admin-set switch, and engaging
a switch that is already engaged (by anyone) does nothing, so nothing is written twice. If spend cannot be read it
counts as 100 percent (fail closed). Nothing here commits.

shortcut: the 90 percent SerpApi trip engages provider.serpapi, which turns off all live search, instead of narrowing to
top-value routes (a chosen flight or an active alert) first. Upgrade trigger: the per-route value ranking in the live gate.
shortcut: the error-rate breaker watches Anthropic only, not every provider (08 section 6.5 says any provider). Upgrade
trigger: the first non-Anthropic provider incident, then loop this over provider_calls.provider.
shortcut: the "five HTTP 400 config errors in 10 minutes turn the feature off" rule is not built (provider_calls does not
record the feature). Upgrade trigger: WF-056.2 or the first 400-loop incident.
"""

import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from hermi.db import system_session
from hermi.errors import ApiError
from hermi.modules.admin.flags import FlagRuntime, _audit, clear_switch, engage_switch

log = logging.getLogger("hermi.breakers")

AUTO = "auto:"
FREE_PCT, PAID_PCT, SERP_PCT = 80, 95, 90
SURGE_FACTOR = 1.5  # of the trailing 7-day mean
TRIP_RATE, TRIP_WINDOW = 0.5, timedelta(minutes=5)  # 08 6.5: trips the provider switch to half-open
NOTIFY_RATE, NOTIFY_WINDOW = 0.05, timedelta(minutes=10)  # 08 10: notify only
MIN_CALLS = 10  # fewer calls than this say nothing about a rate
COOLDOWN = timedelta(minutes=1)  # one probe a minute
ERROR_STATUSES = (429, 529)
ERROR_KEY = "provider.anthropic"
PROBING = AUTO + " probing"
# A provider-side failure: no status (network), 5xx, 429 or overloaded. A 400 is our own bad request.
FAIL = "(NOT ok AND (status_code IS NULL OR status_code >= 500 OR status_code = ANY(:bad)))"
BUDGET_SETTING = "setting_ai_global_daily_usd"
QUOTA_SETTING = "setting_serpapi_monthly_quota"

Alert = Callable[[str, str, str], None]  # (severity page|notify|info, switch key, message)


def log_alert(severity: str, key: str, message: str) -> None:
    """The page hook. shortcut: a structured log line only (log shipping pages on severity=page). Upgrade trigger: the
    pager integration, which replaces this one function."""
    log.warning("breaker_alert", extra={"severity": severity, "key": key, "alert_message": message})


def reached(used: int, limit: int, pct: int) -> bool:
    """Integer compare, so 79.99 percent never rounds up to 80."""
    return limit <= 0 or used * 100 >= limit * pct  # no budget set (or unreadable as 0): fail closed


def surged(today: int, prior_days: list[int]) -> bool:
    return bool(prior_days) and sum(prior_days) > 0 and today > SURGE_FACTOR * (sum(prior_days) / len(prior_days))


def _engaged_row(session: Session, key: str):
    return session.execute(
        text(
            "SELECT engaged_by, reason, engaged_at FROM kill_switches WHERE key = :k AND engaged "
            "AND (expires_at IS NULL OR expires_at > now())"
        ),
        {"k": key},
    ).one_or_none()


def _is_auto(row) -> bool:
    return row is not None and row.engaged_by is None and (row.reason or "").startswith(AUTO)


def _engage(session: Session, key: str, reason: str, severity: str, alert: Alert) -> bool:
    if _engaged_row(session, key) is not None:  # already engaged by a breaker or an admin: leave it
        return False
    engage_switch(session, key, actor_type="system", reason=AUTO + reason)
    alert(severity, key, reason)
    return True


def _release(session: Session, key: str, reason: str) -> bool:
    if not _is_auto(_engaged_row(session, key)):  # an admin-set switch is never cleared here
        return False
    clear_switch(session, key, actor_type="system", reason=AUTO + reason)
    return True


def _budget_micros(session: Session, settings) -> int:
    row = session.execute(text("SELECT (rules ->> 'usd')::numeric FROM feature_flags WHERE key = :k"), {"k": BUDGET_SETTING}).first()
    cap = float(settings.ai_global_daily_cap_usd)
    return round((min(cap, float(row[0])) if row and row[0] is not None else cap) * 1_000_000)


def _spend(session: Session, since: datetime) -> int:
    return int(session.execute(text("SELECT coalesce(sum(cost_usd_micros), 0) FROM ai_usage WHERE created_at >= :s"), {"s": since}).scalar_one())


def _ai_spend(session: Session, settings, day: datetime, alert: Alert, out: dict) -> None:
    try:
        with session.begin_nested():
            used, limit = _spend(session, day), _budget_micros(session, settings)
        unreadable = None
    except Exception:
        log.exception("breaker_spend_unreadable")
        used, limit, unreadable = 1, 1, "spend view unreadable"  # fail closed: treat the budget as spent
    for key, pct, severity in (("ai.free_tier", FREE_PCT, "notify"), ("ai.all_but_paid", PAID_PCT, "page")):
        if reached(used, limit, pct):
            if _engage(session, key, unreadable or f"AI spend at {pct} percent of the daily budget", severity, alert):
                out["engaged"].append(key)
        elif _release(session, key, "AI spend below the daily threshold"):
            out["released"].append(key)
    if unreadable:
        return
    prior = [
        int(r[0])
        for r in session.execute(
            text(
                "SELECT coalesce(sum(u.cost_usd_micros), 0) FROM generate_series(1, 7) d LEFT JOIN ai_usage u "
                "ON u.created_at >= :day - d * interval '1 day' AND u.created_at < :day - (d - 1) * interval '1 day' GROUP BY d"
            ),
            {"day": day},
        )
    ]
    if surged(used, prior):
        if _engage(session, "ai.batch", "daily AI spend above 1.5x the 7-day mean", "page", alert):
            out["engaged"].append("ai.batch")
    elif _release(session, "ai.batch", "daily AI spend back under 1.5x the 7-day mean"):
        out["released"].append("ai.batch")


def _serpapi(session: Session, settings, now: datetime, alert: Alert, out: dict) -> None:
    row = session.execute(text("SELECT (rules ->> 'searches')::int FROM feature_flags WHERE key = :k"), {"k": QUOTA_SETTING}).first()
    cap = min([settings.serpapi_monthly_cap] + ([int(row[0])] if row and row[0] is not None else []))
    month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    used = session.execute(
        text("SELECT count(*) FROM provider_calls WHERE provider = 'serpapi' AND ok AND NOT cached AND created_at >= :s"), {"s": month}
    ).scalar_one()
    if reached(used, cap, SERP_PCT):
        if _engage(session, "provider.serpapi", f"SerpApi searches at {SERP_PCT} percent of the monthly quota", "page", alert):
            out["engaged"].append("provider.serpapi")
    elif _release(session, "provider.serpapi", "SerpApi quota below the threshold"):
        out["released"].append("provider.serpapi")


def _rate(session: Session, since: datetime, *, rate_limited_only: bool = False) -> tuple[int, int]:
    """(failed, total) of live Anthropic calls since `since`, or since the last time the switch was cleared if later."""
    cleared = session.execute(
        text("SELECT max(created_at) FROM audit_log WHERE entity_type = 'kill_switch' AND entity_id = :k AND action = 'killswitch.clear'"),
        {"k": ERROR_KEY},
    ).scalar_one()
    if cleared is not None and cleared > since:
        since = cleared  # failures before a recovery do not count again
    cond = "status_code = ANY(:bad)" if rate_limited_only else FAIL
    failed, total = session.execute(
        text(f"SELECT count(*) FILTER (WHERE {cond}), count(*) FROM provider_calls WHERE provider = 'anthropic' AND NOT cached AND created_at >= :s"),
        {"bad": list(ERROR_STATUSES), "s": since},
    ).one()
    return int(failed), int(total)


def probe_allowed(session: Session, now: datetime | None = None) -> bool:
    """True while provider.anthropic is auto-tripped and its cooldown has passed (read only; admission claims with claim_probe)."""
    row = _engaged_row(session, ERROR_KEY)
    return _is_auto(row) and (now or datetime.now(UTC)) >= row.engaged_at + COOLDOWN


_CLAIM = text(
    "UPDATE kill_switches SET engaged_at = now(), reason = :r WHERE key = :k AND engaged AND engaged_by IS NULL "
    "AND reason LIKE 'auto:%' AND engaged_at <= now() - make_interval(secs => :cool) RETURNING key"
)


def claim_probe(session: Session) -> bool:
    """Atomically take the one half-open probe. Of two concurrent requests after the cooldown exactly one gets a row, because the
    loser re-checks engaged_at after the winner's UPDATE. Needs a role that may write kill_switches. Does not commit."""
    won = session.execute(_CLAIM, {"k": ERROR_KEY, "r": PROBING, "cool": COOLDOWN.total_seconds()}).first() is not None
    if won:  # same transaction as the claim
        _audit(session, action="killswitch.probe", key=ERROR_KEY, actor_type="system", actor_user_id=None,
               reason=PROBING, before=None, after={"engaged": True, "reason": PROBING})
    return won


def refuse_unless_probe_possible(flags: FlagRuntime, now: datetime | None = None) -> None:
    """Read only early check for a route that must not claim the probe before it has authenticated the caller: 503 when
    provider.anthropic is engaged and no probe could be claimed now. It claims nothing and writes nothing."""
    if not flags.switch_engaged(ERROR_KEY):
        return
    sw = flags.switch(ERROR_KEY)
    if sw is not None and sw.engaged_by is None and (sw.reason or "").startswith(AUTO) and sw.engaged_at is not None \
            and (now or datetime.now(UTC)) >= sw.engaged_at + COOLDOWN:
        return
    raise ApiError(503, "ai_unavailable", "This is paused for a moment. Try again soon.")


def ensure_anthropic_allowed(flags: FlagRuntime, *feature_keys: str, user_id=None, tier: str | None = None, route: str = "ai") -> None:
    """The admission gate for an anthropic_api call: every switch of `ensure_paid_allowed` plus provider.anthropic. When
    provider.anthropic is the only switch that blocks, the request is admitted only if it wins the half-open probe claim."""
    flags.ensure_paid_allowed(*feature_keys, user_id=user_id, tier=tier)  # first, so a refused request never uses the probe
    if not flags.switch_engaged(ERROR_KEY):
        return
    settings = getattr(flags, "settings", None)
    if settings is not None:
        try:
            with system_session("ai_single_call", settings=settings, route=route) as s:
                won = claim_probe(s)
            if won:
                flags.invalidate()
                return
        except Exception:
            log.exception("breaker_probe_claim_failed")  # fail closed
    raise ApiError(503, "ai_unavailable", "This is paused for a moment. Try again soon.")


def _error_rate(session: Session, now: datetime, alert: Alert, out: dict) -> None:
    row = _engaged_row(session, ERROR_KEY)
    if row is not None:
        if not _is_auto(row) or row.reason != PROBING:
            return  # an admin owns it, or it is open and no probe has been claimed
        last = session.execute(
            text(f"SELECT ok FROM provider_calls WHERE provider = 'anthropic' AND NOT cached AND created_at >= :s AND (ok OR {FAIL}) ORDER BY created_at DESC LIMIT 1"),
            {"s": row.engaged_at, "bad": list(ERROR_STATUSES)},
        ).one_or_none()
        if last is None:
            return  # half-open, the probe has not been recorded yet
        if last.ok:
            if _release(session, ERROR_KEY, "probe succeeded"):
                out["released"].append(ERROR_KEY)
                alert("info", ERROR_KEY, "Anthropic recovered, breaker closed")
        else:  # probe failed: open again, cooldown restarts
            engage_switch(session, ERROR_KEY, actor_type="system", reason=AUTO + "probe failed")
            alert("notify", ERROR_KEY, "Anthropic probe failed, breaker open again")
        return
    failed, total = _rate(session, now - TRIP_WINDOW)
    if total >= MIN_CALLS and failed / total > TRIP_RATE:
        if _engage(session, ERROR_KEY, f"Anthropic error rate {failed}/{total} over 5 minutes", "page", alert):
            out["engaged"].append(ERROR_KEY)
        return
    failed, total = _rate(session, now - NOTIFY_WINDOW, rate_limited_only=True)
    if total >= MIN_CALLS and failed / total > NOTIFY_RATE:
        alert("notify", ERROR_KEY, f"Anthropic 429/overloaded {failed}/{total} over 10 minutes")
        out["notified"].append(ERROR_KEY)


def evaluate(session: Session, settings, *, now: datetime | None = None, alert: Alert = log_alert) -> dict:
    """One pass of every breaker. Returns {"engaged": [...], "released": [...], "notified": [...]}."""
    now = now or datetime.now(UTC)
    day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    out: dict = {"engaged": [], "released": [], "notified": []}
    _ai_spend(session, settings, day, alert, out)
    _serpapi(session, settings, now, alert, out)
    _error_rate(session, now, alert, out)
    return out
