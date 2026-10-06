# Owner migration runbook (WF-040)

Moves the two owners' trips from the old Trip Planner database into Hermi, once, before public launch. The command is `hermi import-legacy`. It copies the old database directly (no export file), maps it into the Hermi tables, verifies, and emails each owner a one-time claim link. The real run is owner-pending: nothing here has been run against real data.

## What the command does

1. Copies these old tables into the `legacy` schema of the hosted database: `people`, `trips`, `trip_travelers`, `trip_destinations`, `flight_routes`, `flight_quotes`, `itinerary_days`, `activities`, `lodging_options`, `lodging_votes`, `agent_notes`, `runs`, `run_events`, `ingest_rejections`, `api_calls`, `app_settings` and `activity_suggestions`. It also copies `routines`, which stays in `legacy` for the 30 day soak (routines arrive with Pro in Phase 2).
2. Maps them with SQL (03 section 12.1): UUIDv7 ids that keep each row's creation time, money to minor units, the primary owner as trip owner, the partner as editor, a shared fare observation plus a per-trip link for every flight quote, agent and research runs (`flight_agent` becomes `fare_hunt`, `research_agent` becomes `deep_research`, cost to micro-dollars, the prompt dropped, a run still queued or running becomes `interrupted`), run events and rejections from the last 30 days, API calls from the last 13 months as `provider_calls`, the home currency setting onto both users, and a comped Plus entitlement for both owners.
3. Verifies in the same transaction: row counts per table (source, documented skips, imported, unmapped), no `trip_people` row without a person, one owner member per trip, lodging money totals per currency (sum of rounded minor units on both sides). After a real commit it runs an RLS smoke test as the API login (the primary owner sees every imported trip, a stranger sees none).
4. A dry run, or a failed check before the commit, rolls the copy and mapping back, so no product rows are written. Two things outlive a rollback: the empty `legacy` schema and its grant to the worker role, which the owner login creates once. The command exits non-zero if anything fails, including a check that can only run after the commit (the RLS smoke test needs `DATABASE_URL`, the claim emails need a real mail backend). Fix the cause and run again.
5. After a real commit it emails each owner who has not claimed yet a link `/claim/<token>` (valid 7 days, works once).

The old database is opened read only. The command never prints a connection string, password or claim token. Documented skips, each reported as a count: agent flight quotes without a source URL and a chosen flight that points at one (their legacy ids are printed), scheduled price checks and assist runs, run events, rejections and API calls older than the windows above, server-wide settings, and `activity_suggestions` (copied to `legacy`, no Phase 1 table). Per-route price insights, the FX and airport tables, places cache, worker heartbeat and local files are not read.

It is safe to run again. Every inserted row is tracked by id in `legacy.legacy_id_map` (API calls by a hash in `request_hash`) and skipped on a re-run, and nobody is emailed twice unless a link expired or was never delivered. A re-run does not overwrite edits to imported rows, but it does bring back an imported row you deleted in Hermi, because the map still holds its id. Do not re-run after the owners have started cleaning up their data unless you want those rows back.

## Before you start

- Back up both sides. Old side: `pg_dump -Fc` of the Trip Planner database to a file you keep. Hosted side: confirm the latest Render snapshot and PITR are healthy (see `restore.md`), and take a manual snapshot.
- Run on staging first. Staging needs `DATABASE_URL`, `DATABASE_URL_SYSTEM` (the worker login) and `MIGRATION_DATABASE_URL` (used once to create the `legacy` schema), plus `EMAIL_BACKEND=resend`, `RESEND_API_KEY` and `PUBLIC_WEB_URL` so the link points at the right app. Use `EMAIL_BACKEND=file` for a rehearsal: the emails land in `.data/outbox` instead of an inbox. The `console` backend is refused for claim links, because it would write the token into the log.
- The old database must be reachable from where you run the command. Use a URL for a read only login. The URL goes in an environment variable or your shell history only, never in a file in the repo.
- The primary owner is the legacy person with the lowest id and the partner the next lowest, which is how the old app was set up. If that is wrong, pass `--primary-person-id` and `--partner-person-id`.
- Both emails must be addresses each owner can open: the claim link is the proof of ownership.

## Steps

1. Dry run, on staging:

   ```bash
   uv run hermi import-legacy --source-db "$OLD_DB_URL" --primary-email "$PRIMARY_EMAIL" --partner-email "$PARTNER_EMAIL" --dry-run
   ```

   Read the table. Every `unmapped` value must be 0 and every check must say PASS. If a step fails, the message names the step and the database error. Fix the data or report it, then dry run again.
2. Real run, on staging (same command without `--dry-run`). Check the report again, then open the app as each owner after claiming.
3. Claim: each owner opens the emailed link, signs in with that same email address (email code, Apple or Google) and sees their trips, people and stays. A used or expired link shows "Ask for a new link"; run the command again to send a new one.
4. Spot check against the old app: trip count, a few flight routes with their chosen flight, an itinerary day, a stay with its hearts, the notes.
5. Production: repeat steps 1 to 4 against the production database after the staging pass is clean and both owners have claimed on staging. Take the production snapshot first.

## After the migration

- Keep the old install running read only for 30 days. Stop its scheduler and worker so nothing writes to it, and do not delete the backup.
- After the 30 day soak, drop the `legacy` schema (`DROP SCHEMA legacy CASCADE`, as the owner login).
- Hero images are re-fetched by a follow-up job; local image files are not migrated.

## If something goes wrong

- A run that fails before the commit writes no product rows (one transaction). Fix the cause and run again.
- Wrong people picked as owners: restore the staging snapshot (`restore.md`), drop the `legacy` schema, and run again with the person id flags.
- An owner never got the email: run the command again. It only sends to owners who have not claimed and have no valid link.
