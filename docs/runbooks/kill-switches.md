# Kill switches runbook

A kill switch stops a feature in seconds without a deploy. Rows live in `kill_switches` (`engaged = true` means stopped). Every API process caches the tables for 5 seconds, and a `NOTIFY` on the `hermi_flags` channel drops that cache at once, so a change shows up in under 5 seconds even if the listener is down. If the tables cannot be read, paid AI calls are refused (fail closed) until they can.

Every engage and clear writes an `audit_log` row (`killswitch.engage`, `killswitch.clear`, `retention_class = extended`) in the same transaction as the change. A manual switch needs an expiry (1, 4, 24 or 72 hours); only `provider.*` may be left until cleared, and only by the owner. An expired switch counts as cleared immediately.

## Practice drill (quarterly, in a non-production database or on prod at a quiet hour)

1. Note the time. In the admin console, Switches, engage `ai.all` with reason "drill" and expiry 1 hour. (Without the console: call `engage_switch(session, "ai.all", actor_type="admin", actor_user_id=<your id>, reason="drill", expires_at=<now + 1h>)` from `hermi.modules.admin.flags` in a transaction as the admin or system login.)
2. Start any AI action in the app (for example an explain). Within 5 seconds it must answer "paused for a moment" (`503 ai_unavailable`). Cached answers and non-AI features keep working.
3. Clear `ai.all` in the console (`clear_switch` from code). Within 5 seconds the same AI action works again.
4. Check the audit trail:

   ```sql
   SELECT created_at, action, actor_type, actor_user_id, reason, retention_class
   FROM audit_log WHERE entity_type = 'kill_switch' AND entity_id = 'ai.all' ORDER BY id DESC LIMIT 2;
   ```

   Expect `killswitch.clear` then `killswitch.engage`, both `extended`, both with your id and `actor_type = admin`.
5. Record the drill date and the measured delay in the incident log. If blocking took more than 5 seconds, check that the API role can read `kill_switches` and that the clock on the host is right.

## Unreadable tables

If the database is down or `kill_switches` cannot be read, paid AI calls return `503 ai_unavailable` and flags use the last good copy. Nothing to do here but restore the database (see `restore.md`).
