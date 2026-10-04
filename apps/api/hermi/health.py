"""Readiness checks for /health/ready. Probes are module functions so tests replace them."""

import logging
import re
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
