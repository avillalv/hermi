# Prompt 25: Public pages, referrals, comparison pages, trust pages and Android web

Phase 1 build, step 25 of 28. Follow `app-buildout/prompts/AUTOPILOT.md` and `app-buildout/prompts/00-orchestrator.md` for how to run this prompt (the driver merges).

## Goal

Ship admin content reports, public sample trips and shared-trip pages, referral credits, the /vs comparison pages, the How we earn and How billing works pages with the cancel link, and the installable Android web app with its test pass.

## Tickets, in this order

Each ticket's description, dependencies, acceptance criteria, files and tests are in `app-buildout/phase-1-launch/09-build-roadmap.md`. The acceptance criteria are the definition of done.

| Ticket | Title |
|---|---|
| WF-106 | Admin content reports |
| WF-107 | Public sample trips and shared-trip pages |
| WF-108 | Referral credits |
| WF-109 | Comparison pages (/vs) |
| WF-124 | Trust pages: How we earn, How billing works and the cancel link |
| WF-127 | Android install: installable web app and install guide |
| WF-128 | Android Chrome test pass |

## Read before starting

- `app-buildout/prompts/PROGRESS.md` (what is already built, decisions made)
- `app-buildout/phase-1-launch/01-product-spec.md` (web pages, referrals)
- `app-buildout/phase-1-launch/05-ui-ux-spec.md` (6.34 to 6.37 and 6.40 to 6.42)
- `app-buildout/context/competitive-analysis/win-plan.md` (section 5)
- `app-buildout/phase-1-launch/README.md` (settled values)
- `app-buildout/phase-1-launch/design/DESIGN-LANGUAGE.md` and `app-buildout/phase-1-launch/design/tokens.css` (rules and tokens for the public, comparison and trust pages)

## Notes

- WF-107 runs as sub-steps: `WF-107.1` pages and `WF-107.2` sitemap.
- Owner verification pending: WF-109 (the owner's read-through for fairness), WF-127 (Chrome on Android offers Install app and the installed app opens a trip offline, on a real phone; the guide screenshots match the Chrome menus on release day) and WF-128 (the checklist on Chrome on a real Android phone).
- The plan sets `gate: month-5`.
- Comparison pages are honest: dated evidence per claim, a "where they win" section, no competitor logos or trademarks beyond their names.

## Owner-only steps

Add these to `app-buildout/prompts/HUMAN_TASKS.md` (do not block on them; use fakes, fixtures and flags until they are done):

- Review the comparison page claims against the competitors' current sites before publishing.

## Done when

- Every ticket above meets its acceptance criteria, with the tests the ticket names.
- `npm run lint` and `npm test` pass locally and in CI (and `npm run gen:api` is committed when routes changed, and the e2e smoke test passes when a user flow changed).
- No secrets, no em dashes in UI copy, no fetching of Airbnb, Vrbo or Booking.com pages.
- `PROGRESS.md` and `HUMAN_TASKS.md` are updated.
- The pull request `Phase 1 / P25: Public pages, referrals, comparison pages, trust pages and Android web` is ready with the `e2e` label and the `PROGRESS.md` row says Done; the driver merges it after `ci` passes.
