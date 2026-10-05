# Month 1 gate

Date: 2026-10-05. Unit: 07. Verdict: fixed in this PR.

## Month exit

Exit: demand signal recorded (a "no-go" stops the backlog after week 3); a signed-in user can create a trip on staging; zero leaks in the tenant suite. Zero leaks in the tenant suite: met (`npm run test:api`, 741 passed). Create a trip: met locally on fakes by the API and web tests; on staging it is owner-only (row 34). Demand signal: owner-only (row 28), with the provisional go in `DECISIONS.md`.

## Agent-checked

| Item | Command | Pass condition | Result |
|---|---|---|---|
| Tenant-isolation test green, RLS tested (direct SQL and no-variable pass), zero leaks, zero unclassified routes | `npm run test:api` (includes `tests/tenancy`, `tests/test_rls_runtime.py`, `tests/test_migrations_rls_isolation.py`, `tests/test_tenancy.py`) | exit 0, no failure, tenancy tests run (not skipped) | pass: 741 passed, 0 failed, 0 skipped. On staging: owner-only part, not run |
| A signed-in user creates a trip (smoke flow 2) | `npm run test:e2e:smoke` (fetch checks, then the Playwright smoke project against `npm run dev` on fakes) | exit 0, test "new user creates a first trip in three steps" passes | pass: 2 of 2 fetch checks and 18 of 18 Playwright smoke tests, including `sign-in.spec.ts:119` and the invite flows (`invite.spec.ts`, early Month 2 evidence). `test:e2e:smoke` and `e2e.yml` now run the Playwright project (fix now, judge round 1) |
| Contrast test for every token pair | `npm run test:web` (`src/tokens.test.ts`) | exit 0 | pass: 291 web tests, 37 in tokens.test.ts. Axe in light and dark is WF-036 (prompt 10) and moves to the Month 2 gate, not ticked here |
| Log scan finds no tokens | `npm run test:api` then grep of its log for `eyJ`, `Bearer `, `sk_`, `sk-`, `token=`; masking unit test `apps/api/tests/test_logging_masking.py` | tests pass, grep prints 0 matches | pass after the gate-1 fix (the masking did not exist before): 741 passed, 0 matches. Reviewed `VERDICT: APPROVE gate-1` |
| Local run check | `run-hermi-locally` skill | 6 steps pass, ports free | pass: doctor ok, setup on scratch DB ok, API and web ready, smoke 2 of 2, ports 8100 and 5173 free, scratch DB dropped, db:init exit 0 |
| Lint and dash grep | `npm run lint`, `grep -rIl` for em and en dashes in `app-buildout` | clean | pass |

## Owner-only

| Item | Who does it | HUMAN_TASKS row |
|---|---|---|
| Demand signal against the written "yes", go decision signed | The owner | Run the 10 interviews and the price test (row 28) |
| Sign in with a real Supabase email code on staging and create a trip | The owner | Verify WF-018: a new user reaches a created trip in under 2 minutes on staging (row 34) |
| Sentry and structured logs live in staging and production | The owner | Verify Sentry and structured logs are live in staging and production (row 36) |

## Context audit

### context-graph --code

218 nodes, 551 edges, 9 findings. Five modules are imported by 13 to 21 files with no rule (`hermi/main.py`, `security/jwt.py`, `deps.py`, `errors.py`, `tests/test_migrations.py`): a candidate for a rule later, not a break. Four skills were flagged for descriptions without "use when"; fixed in this PR. No rule has a `paths` glob that matches nothing. The graph output was deleted.

### context-init cleanup (audit only)

CLAUDE.md 157 lines (cap 200). 7 rules, all with `paths`. 5 skills. 7 knowledge files, all in INDEX.md; none over 300 lines. CLAUDE.md names no individual knowledge file. No duplicates across tiers found.

### Context sync

Routed: INDEX.md gained pointers to the repo docs and the 5 skills, 4 skill descriptions reworded as triggers, 8 sources marked; `findings lessons-stale` remains (LESSONS.md is built by `/finding` aggregate, not done in this gate).

## Judge

Round 1 (opus-judge): fix now. The Playwright smoke project existed but nothing ran it, and the axe scans belong to the Month 2 gate (WF-036). Fixed in `ship: 07`: `test:e2e:smoke` runs the fetch checks then the Playwright smoke project, `e2e.yml` installs Chromium, Playwright reuses the dev servers in CI, and the log masking the 7.1 item needs was built (`APPROVE gate-1`). Round 2: pass. Cut list: not applied, the build is ahead of the week 4 exit. DECISIONS.md row: "Month 1 gate" dated 2026-10-05. The 7.1 smoke item is only fully proven when the `e2e` workflow on this PR is green.
