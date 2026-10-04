---
name: run-hermi-locally
description: Run the Hermi app locally and check it works end to end. Use in a ship session (prompt 06 on), in the FINAL session, or when asked to confirm a change in the real app. Runs doctor, setup on a scratch database, dev servers on fakes, the smoke test, then stops everything and cleans up.
---

# Run Hermi locally

Windows 11 with Git Bash, or Linux. Report pass or fail with a log tail for each of the 6 steps. `npm run setup` may create or fill `.env` itself; never read it, never edit it by hand, never print a secret, never leave a server or a scratch database behind.

1. **Doctor.** `npm run doctor`. Exit 1 means a required item is missing (names only are printed). Report the tail.
2. **Setup on a scratch database.** Pick a name `hermi_scratch<random digits>` (the autopilot may only create and drop `hermi_*` databases). Put these in the process environment for the command, with a throwaway password you invent, never in `.env`: `DATABASE_URL`, `DATABASE_URL_SYSTEM`, `DATABASE_URL_ADMIN`, `MIGRATION_DATABASE_URL` (all `postgresql+psycopg://<role>:<pw>@localhost/<scratch>` with roles `hermi_api_login`, `hermi_worker_login`, `hermi_admin_login`, `hermi_migrate_login`) and `TEST_DATABASE_URL` (api role, database `<scratch>_test`). Then `npm run setup`. The process environment overrides `.env`. Write each command out in full (the bash guard rejects variables in command names).
3. **Dev servers in the background.** With `AI_PROVIDER=fake SCHEDULER_ENABLED=false STORAGE_BACKEND=local EMAIL_BACKEND=file` in the process environment (plus the scratch URLs from step 2), start `npm run dev` with `run_in_background`. Never edit `.env` for this.
4. **Wait with a timeout.** `node scripts/wait-ready.mjs 60` waits for the API on 8100 (`/health/ready`, or `/health/live` until WF-008 adds ready) and the web app on 5173. Exit 1 on timeout: report the dev log tail.
5. **Smoke.** `npm run test:e2e:smoke`. Today it runs fetch checks against both servers; it becomes the Playwright smoke project (dev sign-in personas) when WF-130 lands.
6. **Stop and clean up.** Kill the whole tree (`taskkill /T /F /PID <pid>` on Windows, the process group elsewhere; `npm run dev` also stops both children when it receives SIGINT or SIGTERM). Confirm nothing listens on 8100 or 5173 (`npm run doctor` shows both ports as free). Drop the scratch databases (`<scratch>` and `<scratch>_test`) with psql as `postgres` through pgpass (`C:\Program Files\PostgreSQL\18\bin\psql.exe -X -w -h localhost -U postgres -d postgres -c "drop database <name>"`). The shared `hermi_*` roles stay, but step 2 reset their passwords to the scratch ones. So finish with `npm run db:init`, run with none of the database URL variables (`DATABASE_URL`, `DATABASE_URL_SYSTEM`, `DATABASE_URL_ADMIN`, `MIGRATION_DATABASE_URL`, `TEST_DATABASE_URL`, `TEST_DATABASE_URL_SYSTEM`, `TEST_MIGRATION_DATABASE_URL`) in the process environment. That resets the role passwords from `.env`. Report its exit code.

Final line: `PASS` only if all 6 steps passed and the ports are free.
