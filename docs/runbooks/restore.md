# Restore runbook

Target: back to serving within 1 hour (RTO), losing at most the time since the last recovery point (RPO: minutes with PITR, up to 24 hours with a snapshot, up to 7 days with the off-provider dump).

## Backups in place

| Layer | What | Kept | Where |
| --- | --- | --- | --- |
| Point-in-time recovery | Continuous WAL, restore to any second | 7 days | Render, per database (basic plan and up) |
| Daily snapshot | Render logical or physical snapshot | 7 days at least | Render |
| Weekly dump | `infra/scripts/backup-dump.sh`: `pg_dump -Fc`, AES-256 (openssl, PBKDF2), meant to run Sunday 03:00 UTC by the `db_dump_offsite` job (prompt 12, not wired yet: the script only until then) | 35 days, R2 lifecycle rule on the bucket | R2 `R2_BUCKET_BACKUPS`, in a second Cloudflare account |

The encryption key `BACKUP_ENCRYPTION_KEY` lives in the password manager and the backup job's environment, never in Render's database group, never in the repo. Without the key a dump cannot be read, so confirm the key is in the password manager before the first drill.

Backups age out within 35 days, which the privacy policy states. Deleted accounts come back with a restore, so step "Re-apply deletions" is mandatory after every restore.

## When to use it

- Bad deploy or migration that corrupted data: PITR to just before it.
- Database lost or unusable, Render healthy: latest snapshot, or PITR.
- Render region down or account lost: dump restore into a new Render account.
- Quarterly, as a drill.

Page rule: last successful weekly dump older than 8 days, or PITR unhealthy (10 section on alerts).

## PITR restore (Render dashboard)

1. Put the API and worker in maintenance: suspend `hermi-worker-prod`, then `hermi-api-prod`.
2. Render dashboard, database `hermi-db-prod`, Recovery, Restore to a point in time. Pick a time before the damage (UTC). Render creates a new database instance; the old one is left alone.
3. Note the new instance's internal and external URLs. Do not delete the old instance yet.
4. Smoke test the new instance by hand with psql: the checks listed under "Smoke test" below (tables present, alembic version, deletions).
5. Point the services at it: set `DATABASE_URL`, `DATABASE_URL_SYSTEM`, `DATABASE_URL_ADMIN`, `MIGRATION_DATABASE_URL` on API and worker (they are `sync: false` in `render.yaml`, so set them in the dashboard), then resume the API and the worker.
6. Re-apply deletions (below). Check `/health/ready`, run `node infra/scripts/smoke.mjs`.
7. After a week without trouble, delete the old instance.

## Snapshot restore

Same as PITR, but in Recovery pick Restore from a snapshot instead of a time. Use it when the point-in-time window has passed (older than 7 days) or PITR is unhealthy.

## Dump restore into a new Render account (region down, account lost)

1. Create the new Render account and a workspace. Create the Postgres 18 database from `infra/render/render.yaml` (New, Blueprint, point at the repo). Staging blueprint first if you are only rehearsing.
2. Create the database roles: `psql "<admin url>" -f infra/db/bootstrap.sql` with the four role passwords supplied as in `npm run db:init`. Dumps keep owners and grants, so the roles must exist before the restore, and the restore runs as a superuser (or a role that can become them).
3. Fetch and restore the newest dump into the new database. With `BACKUP_ENCRYPTION_KEY` and the R2 values of the backup account in your shell:
   `RESTORE_ADMIN_URL=<admin url> bash infra/scripts/restore-drill.sh --keep --scratch-db hermi_restore` restores into a new `hermi_restore` database and keeps it. Either rename it (`ALTER DATABASE hermi_restore RENAME TO hermi`) after stopping connections, or point the services at `hermi_restore` in their URLs.
   To restore by hand: download the object from the backups bucket (`hermi-db/hermi-<UTC stamp>.dump.enc`), then `openssl enc -d -aes-256-cbc -pbkdf2 -iter 600000 -pass env:BACKUP_ENCRYPTION_KEY < dump.enc | pg_restore -d <database>` as a superuser or a role that can become `hermi_owner` and `hermi_definer` (dumps keep owners and grants, so run `infra/db/bootstrap.sql` first).
4. Create the env groups (`hermi-prod-shared`, `hermi-prod-api`, `hermi-prod-worker`) from the password manager and set the four database URLs.
5. Deploy the services: push the blueprint, then run the `deploy-prod` workflow with the last good image digest (update the `RENDER_PROD_*_SERVICE_ID` secrets to the new service ids first).
6. Re-apply deletions, then repoint Cloudflare.

## Cloudflare repoint

1. DNS (Cloudflare dashboard, zone `hermi.world`): change the `api` record to the new Render service hostname. Keep it proxied.
2. If the Pages project survived, nothing else changes; the app calls `api.hermi.world`.
3. Check `https://api.hermi.world/health/ready`, then `node infra/scripts/smoke.mjs` with `PROD_API_URL` and `PROD_WEB_URL` set.
4. Webhooks (Resend, Stripe later, Apple) call the API hostname, so they need no change. Re-check Supabase auth redirect URLs only if the hostname changed.

## Re-apply deletions

A restore can bring back an account that was deleted after the recovery point. `deletion_requests` rows survive the purge (no foreign key, kept 12 months), so replay them:

1. Count them: `SELECT count(*) FROM deletion_requests d JOIN users u ON u.id = d.user_id WHERE d.status = 'completed';`
2. For each such user, run the account purge again (admin console, deletion requests, or the purge job in the worker) before the API takes traffic.
3. Requests in `pending` or `grace` resume on their own.

The drill's smoke test fails if that count is not 0 in the restored copy.

## Smoke test

`restore-drill.sh` runs it. It is SQL checks against the scratch database, not `smoke.mjs`. It checks that `users`, `trips`, `trip_members` and `deletion_requests` exist and counts their rows, that `alembic_version` is a known revision (and warns if it is not the repo head), that no completed deletion still has a user row, and that roles, grants and row level security survived: no security definer function owned by anyone but `hermi_definer`, none executable by public except the three RLS helpers and the `trips_add_owner_member` trigger, which 03 leaves public, `hermi_app` can still read `trips`, and `FORCE ROW LEVEL SECURITY` is still set on the tenant tables. The drill refuses to run until `infra/db/bootstrap.sql` has been applied to the server. In `--local` it also compares row counts with the source database.

## Drill procedure (quarterly)

1. Make sure the weekly dump ran: newest object in the backups bucket is under 8 days old.
2. On a machine with PostgreSQL 18 client tools, openssl and curl (Git Bash on Windows is fine), and a throwaway Postgres 18 server you can create databases on (a local one is fine):
   ```
   export BACKUP_ENCRYPTION_KEY=...   # from the password manager
   export R2_ENDPOINT_URL=... R2_ACCESS_KEY_ID=... R2_SECRET_ACCESS_KEY=... R2_BUCKET_BACKUPS=...
   export RESTORE_ADMIN_URL=postgresql://postgres:...@localhost/postgres
   bash infra/scripts/restore-drill.sh
   ```
   Read-only R2 credentials for the backup account are enough. The script creates `hermi_drill_<time>`, restores, smoke tests, prints PASS or FAIL against the 3600 s RTO and drops the database. It refuses any name not starting with `hermi_`.
3. Once a year, also do the PITR path on staging: restore `hermi-db-staging` to a point 10 minutes ago, and time it. Record the time.
4. Add a row to the log below. A FAIL or an elapsed time over 3600 s is a launch blocker: fix it and repeat.

Rehearse without R2 or Render at any time: `bash infra/scripts/restore-drill.sh --local` (also run by `npm test`).

Schedule: first drill before launch (Month 2 exit), then every quarter (January, April, July, October).

## Drill log

| Date (UTC) | Who | What | Elapsed | Result | Notes |
| --- | --- | --- | --- | --- | --- |
| 2026-10-05 | build agent | `restore-drill.sh --local`, local dev database (Postgres 18, Windows 11, Git Bash), alembic 0022_vote_tombstone | 4 s | PASS | Dump, encrypt, restore, smoke test with row counts equal to the source. No R2 or Render involved. |
| Pending | Owner | Real Render and R2 drill: newest weekly dump from the backup account into a scratch database | | Pending | Owner: real Render and R2 drill, pending. Needs the R2 backups bucket, the second Cloudflare account, `BACKUP_ENCRYPTION_KEY` and a first weekly dump. |
