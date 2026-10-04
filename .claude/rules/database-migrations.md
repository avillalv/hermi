---
description: Use when editing migrations, models, db.py or the database bootstrap. Roles, row-level security, money types and the migration chain have rules that fail silently when broken.
paths:
  - "apps/api/hermi/migrations/**"
  - "apps/api/hermi/**/models*.py"
  - "apps/api/hermi/db.py"
  - "infra/db/**"
---

# Database and migration rules

Authority: `03-database-schema.md` sections 2, 6 and 10 (S1 settles the role and row-level security edits listed
here) and `02-architecture.md` sections 4.3 and 12. If you need to break one of these, change the document in the
same commit and say why.

## Names and the migration chain

- Table and column names come only from 03. Do not invent, rename or add one. A change is an edit to 03 and a
  `DECISIONS.md` row in the same pull request.
- P04 lands 03's whole chain (migrations 0001 to 0015, section 10) with grants and row-level security. A later
  ticket that "creates a table" only adds the model; it adds no DDL that 03 already has. There are no Phase 2
  tables in Phase 1 (`routines` is out; the scheduler scans `flight_routes.next_check_at`).
- One migration per step, in 03's order, and never two migration steps in parallel: two open revisions make two
  Alembic heads. CI requires a single head.
- Write the downgrade and test the round trip (upgrade, downgrade, upgrade) from an empty database and from the
  last released revision.
- Tests run against a real PostgreSQL 18 (the native service locally, the `postgres:18` service in CI), through
  the app login, never as the owner.

## Roles and row-level security

- **Migrations never `CREATE ROLE`.** Roles and the `hermi` and `hermi_test` databases come from
  `infra/db/bootstrap.sql`, run by `npm run db:init`. The bootstrap is idempotent (`IF NOT EXISTS`, then
  `ALTER ... PASSWORD`). `hermi_owner` is NOLOGIN, so migrations connect as `hermi_migrate_login`, a member of it
  (`MIGRATION_DATABASE_URL`).
- **`FORCE ROW LEVEL SECURITY` on every tenant table**, next to `ENABLE`.
- **The app connection (the API, the app login used in pytest, startup) is never a superuser, a `BYPASSRLS`
  role, the table owner or a member of the owner role.** Startup and pytest assert it and refuse to run. Without
  that, row-level security can be off and every test still passes.
- Only fixtures use the system login: they write through the system connection (`TEST_DATABASE_URL_SYSTEM`, the
  worker login on `hermi_test`). Tenant tests read through the app login (`TEST_DATABASE_URL`) with `app.user_id`
  set.
- In policies and SQL use `app_user_id()` (03 section 3), never a raw `current_setting('app.user_id')::uuid`.
- A write the API must do synchronously, and a public read by token, goes through an allowlisted `SystemSession`
  or a `SECURITY DEFINER` function that checks `app_user_id()`. Test every such route under the real roles.

## Types

- Money is an integer in minor units plus an ISO 4217 currency, never a float. Provider spend is an integer in
  micro-dollars. Timestamps are `timestamptz` in UTC. Public ids are UUIDv7 (`uuidv7()` in PostgreSQL 18).

## What must not change without a decision

- **The append-only trigger on `credit_ledger`, and no delete on `audit_log` for the worker role.** Tidying them
  away removes the trail the credit and refund rules rely on.
- **Grants and policies land with the table**, in the same migration. The app role has DML only.
- **Who owns what.** Ownership of tables and `SECURITY DEFINER` helpers follows 03 section 6.1. With `FORCE` on,
  the owner of a helper decides what its queries can see, so do not move ownership to tidy a migration.

## Checkable by grep

```bash
# roles created in a migration (prints nothing when clean)
grep -rniE "CREATE ROLE|ALTER ROLE" apps/api/hermi/migrations
# every ENABLE needs a FORCE: the two counts must match
grep -rhoE "ENABLE ROW LEVEL SECURITY" apps/api/hermi/migrations | wc -l
grep -rhoE "FORCE ROW LEVEL SECURITY" apps/api/hermi/migrations | wc -l
# raw session-variable reads (only the app_user_id() definition may match)
grep -rn "current_setting('app.user_id'" apps/api/hermi
```

## Expand and contract (zero-downtime policy)

Authority: `03-database-schema.md` section 10. The first release creates the schema from empty, so P04's own
revisions may be plain. From the first production release on, every migration follows this policy.

- **Expand, migrate, contract, in separate releases.** Release 1 adds the new column, table or index (nullable or
  with a default, old code unaffected). Release 2 writes both and backfills in batches (a job, not the migration).
  Release 3 drops the old shape once no deployed code reads it. Never drop or rename in the release that adds.
- **A migration runs before the new code is deployed**, so the old code must keep working against the new schema.
  No `ALTER COLUMN ... TYPE` rewrite, no `SET NOT NULL` on a populated column without a validated check first.
- **Locks stay short** (03 says lock 3s, 02 section 12 says 5s; 3s is kept). `env.py` sets `lock_timeout = 3s` and `statement_timeout = 60s` on the migration
  session, so a migration that cannot get its lock fails and is retried instead of queueing traffic behind it.
- **Indexes on live tables:** `CREATE INDEX CONCURRENTLY` inside `with op.get_context().autocommit_block():`.
- **Foreign keys and checks:** add `NOT VALID`, then `VALIDATE CONSTRAINT` in a later step.
- **One migrator at a time:** `env.py` holds `pg_advisory_lock` for the whole run. Migrations run as one
  pre-deploy job, never at server start.
- **One head, linear chain.** `hermi.db.assert_single_head` runs in `env.py`, in `test_migrations.py` and in the CI
  "Single head" step. Rebase and renumber instead of merging two heads.
- **Downgrades exist for development and CI** (`downgrade base` then `upgrade head` on a scratch database).
  Production never downgrades; the fix for a bad release is a new forward migration.
- **0001 only checks roles** (`hermi.db.assert_roles_exist`) and stops with "run `npm run db:init`". Add a new
  role to `infra/db/bootstrap.sql` and to `hermi.db.REQUIRED_ROLES` together.
