# ruff: noqa: E501
"""Usage reconciliation and the table-driven alert rules (WF-056.2; 08 section 10, 06 section 6.6).

`reconcile` compares the previous UTC day's Anthropic cost (the organization cost report, admin key) with the metered
`ai_usage` rows of provider anthropic_api, and alerts (notify) when |anthropic - ai_usage| / anthropic is above 3 percent.
It is skipped for claude_cli and fake (their cost is notional), and logs and skips without ANTHROPIC_ADMIN_API_KEY.
A fetch that fails with HTTP 4xx (a revoked or wrong key) alerts once per day; any other fetch failure only logs. The alert
is written once per day: a rerun finds the audit row and stays quiet.

`evaluate_rules` runs the rules of one group of RULES: "health" every minute (evaluate_alert_rules job) and "business"
every 15 minutes (evaluate_business_alerts job, 08 section 10). One firing writes an audit_log row as `system`, and the same subject does not
fire again for an hour. The alert hook is called after the rule's savepoint closes, so a later error cannot page twice.
Nothing here commits. The breaker rules (80 and 95 percent, 1.5x mean, 429 rate, SerpApi quota) are in
hermi.modules.ai.breakers.

Minimum samples (a rate on a handful of rows says nothing): 10 imports in the hour for the import failure rate, 20 cache
eligible research runs in each window for the cache hit rate, 10,000 prompt tokens in the hour for the prompt cache ratio.

shortcut: the 08 section 10 rules below are not built because the data they read has no writer yet, or is not a
database fact. Upgrade trigger: the one named on each line, then add a Rule row.
- scheduler idle over 3 minutes: this job is itself deferred by the scheduler leader, so it cannot see the leader die.
  Trigger: the Better Stack scheduler heartbeat monitor (BETTERSTACK_HEARTBEAT_SCHEDULER) is the check; build a rule
  only if a persisted scheduler tick table is added.
- cost per Plus payer above $2: needs a monthly payer count. Trigger: the admin overview metrics rollup.
- webhook backlog and RevenueCat lag, entitlement mismatches found by reconcile: the table exists but nothing writes it
  yet. Trigger: the billing webhook handler ticket.
- conversion import failed or unmatched share: no conversion import table. Trigger: the affiliate conversion import.
- /go 4xx and 5xx above 1 percent, clicks down 50 percent: no redirect log with status. Trigger: the /go redirect.
- support ticket past SLA: no SLA targets stored. Trigger: the support SLA setting in the admin console.
- Geoapify credits under 20 percent: no credit counter. Trigger: the Geoapify metering ticket.
- pasted-text keep rate under 60 percent over 100 imports, more than 10 feeds failing at once: the columns exist, no
  writer until the import tickets. Trigger: the import tickets that write items_applied and consecutive_failures.
- account ceiling counts ai_usage only, not provider spend, and leaves out work covered by an active Trip Pass.
  Trigger: the first account that exceeds a ceiling through provider spend alone, then reuse budget._provider_spend.
"""

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from hermi.modules.ai.breakers import Alert, log_alert
from hermi.modules.ai.cache import hit_rate

log = logging.getLogger("hermi.reconcile")

GAP = 0.03  # of the Anthropic figure
COOLDOWN = timedelta(hours=1)
CEILING_OVER_TENTHS = 11  # 1.1x, as an integer compare
QUEUE_AGE = timedelta(minutes=10)
EXPIRY_WINDOW = timedelta(minutes=15)
NON_METERED = ("claude_cli", "fake")
COST_URL = "https://api.anthropic.com/v1/organizations/cost_report"
IMPORT_MIN = 10  # imports in the hour before a failure share means anything
CACHE_MIN = 20  # cache eligible research runs per window before a hit rate means anything
PROMPT_MIN_TOKENS = 10_000  # prompt tokens in the hour before the read ratio means anything
PROMPT_RATIO = 0.70
Fetcher = Callable[[date], int]  # previous UTC day -> Anthropic cost in micro-dollars; raises on failure


def cost_micros(body: dict) -> int:
    """Sum a cost report page. `amount` is a decimal string in cents (USD); a micro-dollar is 1/10,000 of a cent."""
    total = sum((Decimal(r["amount"]) for b in body.get("data", []) for r in b.get("results", [])), Decimal(0))
    return int(total * 10_000)


def make_fetcher(admin_key: str, *, client: httpx.Client | None = None) -> Fetcher:
    """The real fetcher. shortcut: follows at most 10 pages of one day. Upgrade trigger: a day with more buckets than that."""

    def fetch(day: date) -> int:
        start = datetime(day.year, day.month, day.day, tzinfo=UTC)
        fmt = "%Y-%m-%dT%H:%M:%SZ"
        params: dict = {"starting_at": start.strftime(fmt), "ending_at": (start + timedelta(days=1)).strftime(fmt), "bucket_width": "1d"}
        headers = {"x-api-key": admin_key, "anthropic-version": "2023-06-01"}
        total = 0
        with client or httpx.Client(timeout=15) as c:
            for _ in range(10):
                r = c.get(COST_URL, params=params, headers=headers)
                r.raise_for_status()
                body = r.json()
                total += cost_micros(body)
                if not body.get("has_more") or not body.get("next_page"):
                    break
                params["page"] = body["next_page"]
        return total

    return fetch


def _fire(session: Session, rule: str, subject: str, severity: str, message: str, alert: Alert | None, since: datetime | None, scope: str = "") -> bool:
    """Audit as system, then the hook (when given one), unless this subject already fired since `since` (None: ever).
    `scope` only separates dedupe keys (tests: audit_log is append-only). True if it fired."""
    entity = f"{rule}:{subject}" + (f"@{scope}" if scope else "")
    seen = session.execute(
        text(
            "SELECT 1 FROM audit_log WHERE entity_type = 'alert' AND entity_id = :e AND action = 'alert.fired' "
            "AND (CAST(:s AS timestamptz) IS NULL OR created_at > :s) LIMIT 1"
        ),
        {"e": entity, "s": since},
    ).first()
    if seen:
        return False
    session.execute(
        text(
            "INSERT INTO audit_log (actor_type, action, entity_type, entity_id, after, reason, retention_class) "
            "VALUES ('system', 'alert.fired', 'alert', :e, CAST(:after AS jsonb), :msg, 'standard')"
        ),
        {"e": entity, "after": json.dumps({"severity": severity}), "msg": message},
    )
    if alert is not None:
        alert(severity, f"{rule}:{subject}", message)
    return True


def reconcile(session: Session, settings, *, fetch: Fetcher | None = None, alert: Alert = log_alert, now: datetime | None = None) -> dict:
    if settings.ai_provider in NON_METERED:
        return {"skipped": "provider"}
    key = settings.anthropic_admin_api_key.get_secret_value() if settings.anthropic_admin_api_key else ""
    if not key:
        log.info("usage_reconcile_skipped_no_admin_key")
        return {"skipped": "no_key"}
    day = ((now or datetime.now(UTC)) - timedelta(days=1)).date()
    start = datetime(day.year, day.month, day.day, tzinfo=UTC)
    try:
        theirs = (fetch or make_fetcher(key))(day)
    except Exception as e:  # not a gap: nothing to compare. The next run retries.
        log.exception("usage_reconcile_fetch_failed")
        out = {"skipped": "fetch_failed"}
        if isinstance(e, httpx.HTTPStatusError) and 400 <= e.response.status_code < 500:  # a revoked or wrong admin key
            msg = f"Anthropic cost report refused the admin key (HTTP {e.response.status_code}), reconciliation for {day} did not run"
            out["alerted"] = _fire(session, "usage_reconcile_fetch", day.isoformat(), "notify", msg, alert, None)
        return out
    ours = int(
        session.execute(
            text("SELECT coalesce(sum(cost_usd_micros), 0) FROM ai_usage WHERE provider = 'anthropic_api' AND created_at >= :s AND created_at < :e"),
            {"s": start, "e": start + timedelta(days=1)},
        ).scalar_one()
    )
    gap = abs(theirs - ours) / max(theirs, 1)
    out = {"day": day.isoformat(), "anthropic_micros": theirs, "ai_usage_micros": ours, "gap": gap, "alerted": False}
    if gap > GAP:
        msg = f"Anthropic cost {theirs} and ai_usage {ours} micro-dollars differ by {gap:.1%} for {day}"
        out["alerted"] = _fire(session, "usage_reconcile", day.isoformat(), "notify", msg, alert, None)
    return out


# --- alert rules ------------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Rule:
    id: str
    severity: str  # page | notify | info
    find: Callable[[Session, object, datetime], list[tuple[str, str]]]  # -> [(subject, message)]
    group: str = "health"  # health: spend and queue, every minute. business: scans of unindexed columns, every 15 minutes.


def _accounts_over_ceiling(session: Session, settings, now: datetime) -> list[tuple[str, str]]:
    day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    rows = session.execute(
        text(
            """SELECT u.user_id, sum(u.cost_usd_micros) AS spend, (pl.limits ->> 'daily_ceiling_micros')::bigint AS ceiling
                 FROM ai_usage u
                 LEFT JOIN entitlements e ON e.user_id = u.user_id AND (e.valid_until IS NULL OR e.valid_until > :now)
                 JOIN plans pl ON pl.code = coalesce(e.tier_code, 'free')
                WHERE u.user_id IS NOT NULL AND u.created_at >= :day
                  AND NOT EXISTS (SELECT 1 FROM trip_passes tp WHERE tp.trip_id = u.trip_id AND tp.status = 'active'
                                   AND tp.starts_at <= u.created_at AND tp.expires_at > u.created_at)
                GROUP BY u.user_id, pl.limits
               HAVING sum(u.cost_usd_micros) * 10 > (pl.limits ->> 'daily_ceiling_micros')::bigint * :tenths"""
        ),
        {"now": now, "day": day, "tenths": CEILING_OVER_TENTHS},
    ).all()
    return [(str(r.user_id), f"Account spent {r.spend} micro-dollars today against a {r.ceiling} ceiling") for r in rows]


def _stuck_queues(session: Session, settings, now: datetime) -> list[tuple[str, str]]:
    rows = session.execute(
        text(
            """SELECT j.queue_name, min(coalesce(j.scheduled_at, e.at)) AS since
                 FROM procrastinate_jobs j
                 LEFT JOIN LATERAL (SELECT min(at) AS at FROM procrastinate_events WHERE job_id = j.id AND type = 'deferred') e ON true
                WHERE j.status = 'todo' AND (j.scheduled_at IS NULL OR j.scheduled_at <= :now)
                GROUP BY j.queue_name"""
        ),
        {"now": now},
    ).all()
    return [(r.queue_name, f"Oldest {r.queue_name} job has waited since {r.since:%H:%M} UTC") for r in rows if r.since and now - r.since > QUEUE_AGE]


def _expiring_switches(session: Session, settings, now: datetime) -> list[tuple[str, str]]:
    rows = session.execute(
        text("SELECT key, expires_at FROM kill_switches WHERE engaged AND expires_at > :now AND expires_at <= :soon"),
        {"now": now, "soon": now + EXPIRY_WINDOW},
    ).all()
    return [(r.key, f"Kill switch {r.key} disengages at {r.expires_at:%H:%M} UTC") for r in rows]


def _runs_over_limits(session: Session, settings, now: datetime) -> list[tuple[str, str]]:
    """Runs of the last day past 20 turns, past their action's hard dollar stop, or running for over 8 minutes."""
    rows = session.execute(
        text(
            """SELECT r.id, r.status, r.turns_used, r.cost_usd_micros
                 FROM runs r LEFT JOIN credit_action_prices p ON p.action = r.action
                WHERE r.created_at >= :since AND r.provider = 'anthropic_api'
                  AND (r.turns_used > 20
                       OR (p.hard_stop_micros IS NOT NULL AND r.cost_usd_micros > p.hard_stop_micros)
                       OR (r.status = 'running' AND r.started_at < :eight))"""
        ),
        {"since": now - timedelta(days=1), "eight": now - timedelta(minutes=8)},
    ).all()
    return [(str(r.id), f"Run {r.id} is {r.status}: {r.turns_used or 0} turns, {r.cost_usd_micros} micro-dollars") for r in rows]


def _old_reports(session: Session, settings, now: datetime) -> list[tuple[str, str]]:
    n = session.execute(
        text("SELECT count(*) FROM content_reports WHERE status = 'open' AND created_at < :t"), {"t": now - timedelta(hours=12)}
    ).scalar_one()
    return [("open", f"{n} moderation reports have been open for over 12 hours")] if n else []


def _import_failures(session: Session, settings, now: datetime) -> list[tuple[str, str]]:
    failed, total = session.execute(
        text("SELECT count(*) FILTER (WHERE status = 'failed'), count(*) FROM trip_imports WHERE created_at >= :t"),
        {"t": now - timedelta(hours=1)},
    ).one()
    if total >= IMPORT_MIN and failed * 5 > total:  # above 20 percent
        return [("hour", f"{failed} of {total} imports failed in the last hour")]
    return []


def _blocked_fetches(session: Session, settings, now: datetime) -> list[tuple[str, str]]:
    """Assumes one trip_imports row per blocked fetch. The import code that writes error_code blocked_source must keep that
    contract, or this count changes."""
    rows = session.execute(
        text(
            "SELECT user_id, count(*) AS n FROM trip_imports WHERE error_code = 'blocked_source' AND created_at >= :t "
            "GROUP BY user_id HAVING count(*) > 20"
        ),
        {"t": now - timedelta(hours=1)},
    ).all()
    return [(str(r.user_id), f"Account had {r.n} blocked import fetches in the last hour") for r in rows]


def _code_redemptions(session: Session, settings, now: datetime) -> list[tuple[str, str]]:
    rows = session.execute(
        text("SELECT code, count(*) AS n FROM referral_rewards WHERE created_at >= :t GROUP BY code HAVING count(*) > 5"),
        {"t": now - timedelta(hours=24)},
    ).all()
    return [(r.code, f"Referral code {r.code} was redeemed {r.n} times in 24 hours") for r in rows]


def _referral_credits(session: Session, settings, now: datetime) -> list[tuple[str, str]]:
    day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    total = session.execute(
        text(
            "SELECT coalesce(sum(referee_credits + CASE WHEN referrer_capped THEN 0 ELSE referrer_credits END), 0) "
            "FROM referral_rewards WHERE status = 'granted' AND granted_at >= :d"
        ),
        {"d": day},
    ).scalar_one()
    return [("day", f"{total} referral credits were granted today")] if total > 1000 else []


def _cache_hit_drop(session: Session, settings, now: datetime) -> list[tuple[str, str]]:
    """Research cache hit rate over the last 24 hours against the 6 days before it."""
    d7, d1 = hit_rate(session, since=now - timedelta(days=7)), hit_rate(session, since=now - timedelta(days=1))
    base_hits, base_misses = d7.hits - d1.hits, d7.misses - d1.misses
    recent, base = d1.hits + d1.misses, base_hits + base_misses
    if recent < CACHE_MIN or base < CACHE_MIN:
        return []
    if (base_hits * recent - d1.hits * base) * 5 > base * recent:  # a drop of more than 20 points, in integers
        return [("day", f"Research cache hit rate fell from {base_hits / base:.0%} to {d1.hits / recent:.0%} over 24 hours")]
    return []


def _prompt_cache_ratio(session: Session, settings, now: datetime) -> list[tuple[str, str]]:
    read, other = session.execute(
        text(
            "SELECT coalesce(sum(cache_read_tokens), 0), coalesce(sum(cache_write_tokens + input_tokens), 0) "
            "FROM ai_usage WHERE provider = 'anthropic_api' AND created_at >= :t"
        ),
        {"t": now - timedelta(hours=1)},
    ).one()
    total = int(read) + int(other)
    if total < PROMPT_MIN_TOKENS:  # also the zero-denominator guard
        return []
    if int(read) < PROMPT_RATIO * total:
        return [("hour", f"Prompt cache read ratio is {int(read) / total:.0%} over the last hour")]
    return []


def _reward_farming(session: Session, settings, now: datetime) -> list[tuple[str, str]]:
    day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    signups = session.execute(text("SELECT count(*) FROM users WHERE created_at >= :d"), {"d": day}).scalar_one()
    rewards = session.execute(text("SELECT count(*) FROM trip_imports WHERE reward_granted_at >= :d"), {"d": day}).scalar_one()
    if signups > 0 and rewards * 100 > signups * 5:  # above 5 percent of today's sign-ups
        return [("day", f"{rewards} import reward passes against {signups} sign-ups today")]
    return []


RULES = (
    Rule("account_over_ceiling", "page", _accounts_over_ceiling),
    Rule("queue_oldest_job", "page", _stuck_queues),
    Rule("kill_switch_expiring", "info", _expiring_switches),
    Rule("run_limit", "page", _runs_over_limits),
    Rule("moderation_report_age", "notify", _old_reports, "business"),
    Rule("import_failure_rate", "notify", _import_failures, "business"),
    Rule("blocked_fetches", "notify", _blocked_fetches, "business"),
    Rule("referral_code_redemptions", "notify", _code_redemptions, "business"),
    Rule("referral_credits_daily", "notify", _referral_credits, "business"),
    Rule("import_reward_farming", "notify", _reward_farming, "business"),
    Rule("cache_hit_drop", "notify", _cache_hit_drop, "business"),
    Rule("prompt_cache_ratio", "notify", _prompt_cache_ratio, "business"),
)


def evaluate_rules(session: Session, settings, *, now: datetime | None = None, alert: Alert = log_alert, scope: str = "", group: str | None = None) -> dict:
    """One pass of RULES (of one `group`, or all when None). A rule that errors (a missing table, say) is logged and skipped. {"fired": [...], "errors": [...]}
    Alerts go out after each rule's savepoint closes. `scope` only separates dedupe keys (tests)."""
    now = now or datetime.now(UTC)
    out: dict = {"fired": [], "errors": []}
    for rule in (r for r in RULES if group in (None, r.group)):
        sent: list[tuple[str, str]] = []
        try:
            with session.begin_nested():
                for subject, msg in rule.find(session, settings, now):
                    if _fire(session, rule.id, subject, rule.severity, msg, None, now - COOLDOWN, scope):
                        sent.append((subject, msg))
        except Exception:
            log.exception("alert_rule_failed", extra={"rule": rule.id})
            out["errors"].append(rule.id)
            continue
        for subject, msg in sent:
            out["fired"].append(f"{rule.id}:{subject}")
            alert(rule.severity, f"{rule.id}:{subject}", msg)
    return out
