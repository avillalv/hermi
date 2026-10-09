# Month 2 gate

Date: 2026-10-09. Unit: 12. Verdict: fixed in this PR.

## Month exit

Exit: two people can plan a trip together on the web; restore drill passed once. Two people planning together: met locally on fakes (`invite.spec.ts`, `sync.spec.ts`, `stays.spec.ts` heart across two contexts). Restore drill: owner-only (row 44, backups set up in row 43). The restore script and runbook exist (`docs/runbooks/restore.md`).

## Agent-checked

| Item | Command | Pass condition | Result |
|---|---|---|---|
| Free owner invites one collaborator, the second invite shows the paywall, two people plan together (flows 3 and 4) | `npm run test:e2e:smoke` (fetch checks, then the Playwright smoke project on `npm run dev` with fakes) | exit 0, `invite.spec.ts` "a Free owner invites one person by link ... second invite shows the paywall with a close control" passes | pass: 43 of 43 Playwright smoke tests |
| Contrast test for every token pair | `npm run test:web` (`src/tokens.test.ts`) | exit 0 | pass: 613 passed in 55 files |
| Axe clean on the core screens in light and dark | `npm run test:kit` (`apps/web/e2e/kit/layout.spec.ts`) | exit 0, axe finds no violations on main routes and the error state in both schemes | pass: 75 passed. The checklist names `test:e2e:smoke` for axe, but the axe scans live in the kit project, so this is the command that covers the item |
| Log scan finds no tokens | `npm run test:api` saved to a log, then grep for `eyJ`, `Bearer `, `sk_`, `sk-`, `token=`; masking unit test `apps/api/tests/test_logging_masking.py` | tests pass, 0 matches | pass: 1331 passed, 1 skipped, 0 failed (tenancy suite included); 0 matches for each pattern |
| Local run check | `run-hermi-locally` skill | 6 steps pass, ports free | pass: doctor ok, setup on scratch DB ok, API and web ready, smoke 43 of 43, ports 8100 and 5173 free, scratch DBs dropped, db:init exit 0 |
| Lint and dash grep | `npm run lint`, `grep -rIl` for em and en dashes in `app-buildout` | clean | pass |

## Owner-only

| Item | Who does it | HUMAN_TASKS row |
|---|---|---|
| Restore drill passed once (PITR to a scratch database, smoke test against it) | The owner | Verify WF-039: run `restore-drill.sh` against the real backups (row 44), after setting up off-site backups (row 43) |
| Sentry and structured logs live in staging and production | The owner | Verify WF-037: a thrown error reaches the real Sentry project (rows 36 and 41) |
| Real import from the Trip Planner database | The owner | Verify WF-040 (row 45) |
| Real email delivery through Resend | The owner | Verify WF-047 (row 46) |

## Context audit

### context-graph --code

232 nodes, 723 edges, 4 findings: `main.py`, `errors.py`, `deps.py` and `security/jwt.py` are imported by 23 to 41 files and no rule covers them. A candidate for a rule later, not a break. No rule has a `paths` glob that matches nothing. The graph output was deleted.

### context-init cleanup (audit only)

CLAUDE.md 157 lines (cap 200). 7 rules, all with `paths`. 5 skills. 9 knowledge files, all in INDEX.md; none over 300 lines (the two largest are about 250). No duplicates across tiers found.

### Context sync

Routed: 4 new docs (month-1 gate, three runbooks) as INDEX.md pointers, no knowledge copies; `findings/LESSONS.md` rebuilt; 4 sources marked.

## Judge

Round 1 (opus-judge): fix now. The log scan had only its unit test run; the grep of a run log was missing, and the axe row named the wrong command. Fixed in this gate: the API run was saved to a log and grepped (0 matches) and the axe row now names `test:kit`. Cut list: not applied, no slippage. No code changed, so no review round.
