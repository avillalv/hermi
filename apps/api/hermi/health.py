"""Readiness checks for /health/ready. Probes are module functions so tests replace them."""

import logging
import re
import time
from pathlib import Path

VERSIONS_DIR = Path(__file__).resolve().parent / "migrations" / "versions"
_REV = re.compile(r"""^revision\s*(?::[^=]+)?=\s*["']([^"']+)["']""", re.M)
_DOWN = re.compile(r"""^down_revision\s*(?::[^=]+)?=\s*["']([^"']+)["']""", re.M)

log = logging.getLogger(__name__)


def psycopg_url(url: str) -> str:
    """SQLAlchemy style `postgresql+psycopg://` to the plain DSN psycopg accepts."""
    return url.replace("+psycopg", "", 1)


def expected_head(versions_dir: Path = VERSIONS_DIR) -> str | None:
    """The migration head from the revision files, or None when there are no migrations yet."""
    revs, downs = set(), set()
    for f in versions_dir.glob("*.py") if versions_dir.is_dir() else []:
        text = f.read_text(encoding="utf-8")
        revs.update(_REV.findall(text))
        downs.update(_DOWN.findall(text))
    heads = sorted(revs - downs)
    # Several heads is a broken graph: return a value no database revision equals (ready: stale).
    return ",".join(heads) if heads else None


def probe_db(url: str) -> str | None:
    """SELECT 1, then return the stored Alembic revision (None when the table is absent)."""
    import psycopg

    with psycopg.connect(psycopg_url(url), connect_timeout=2) as conn:
        conn.execute("SELECT 1")
        if conn.execute("SELECT to_regclass('alembic_version')").fetchone()[0] is None:
            return None
        row = conn.execute("SELECT version_num FROM alembic_version").fetchone()
        return row[0] if row else None


def check_ready(database_url: str | None, ai_provider: str) -> tuple[bool, dict[str, str]]:
    """Returns (ready, body). Errors are reduced to a word so a DSN never leaks."""
    body = {"status": "fail", "database": "not_configured", "migrations": "unknown"}
    if database_url:
        try:
            current = probe_db(database_url)
        except Exception as e:
            log.warning("database probe failed: %s", type(e).__name__)
            body["database"] = "unreachable"
        else:
            body["database"] = "ok"
            head = expected_head()
            if head is None:
                body["migrations"] = "none"
            else:
                body["migrations"] = "ok" if current == head else "stale"
    ok = body["database"] == "ok" and body["migrations"] in ("ok", "none")
    body["status"] = "ok" if ok else "fail"
    body["ai_provider"] = ai_provider
    return ok, body


def queue_stats(url: str) -> dict[str, dict[str, int]]:
    """Per lane: jobs waiting to run now (todo, not scheduled later), and the oldest one's age
    in seconds, counted from its scheduled time, else its deferral. Scaling reads this (02 1.2)."""
    import psycopg

    from hermi.jobs import LANES

    out = {lane: {"depth": 0, "oldest_age_seconds": 0} for lane in LANES}
    with psycopg.connect(psycopg_url(url), connect_timeout=2) as conn:
        rows = conn.execute(
            """SELECT j.queue_name, count(*),
                      COALESCE(max(EXTRACT(EPOCH FROM
                          now() - COALESCE(j.scheduled_at, e.at))), 0)::int
                 FROM procrastinate_jobs j
                 LEFT JOIN LATERAL (
                      SELECT min(at) AS at FROM procrastinate_events
                       WHERE job_id = j.id AND type = 'deferred') e ON true
                WHERE j.status = 'todo'
                  AND (j.scheduled_at IS NULL OR j.scheduled_at <= now())
                GROUP BY j.queue_name"""
        ).fetchall()
    for lane, depth, age in rows:
        if lane in out:
            out[lane] = {"depth": depth, "oldest_age_seconds": max(age, 0)}
    return out


_QUEUE_TTL_SECONDS = 5
_queue_cache: dict[str, tuple[float, dict]] = {}


def queue_stats_cached(url: str) -> dict[str, dict[str, int]]:
    """queue_stats, reused for a few seconds so a busy scraper does not open a connection per hit.
    Failures are not cached."""
    now = time.monotonic()
    hit = _queue_cache.get(url)
    if hit and now - hit[0] < _QUEUE_TTL_SECONDS:
        return hit[1]
    stats = queue_stats(url)
    _queue_cache[url] = (now, stats)
    return stats
