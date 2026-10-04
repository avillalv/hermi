# 09: Build roadmap (Phase 1, months 1 to 6)

Part of the [Hermi build specification](../README.md) and of [Phase 1](README.md). The shared decisions in the [root README](../README.md) (tier codes, credit codes, table names) and the Phase 1 scope and month plan in the [Phase 1 README](README.md) are final; this file sequences the work.

This file has two halves. The first is the plan: what each month is for, week-level milestones, the critical path, a capacity check and what to cut first. The second is an ordered backlog of 133 tickets (WF-001 to WF-133, numbered for Phase 1 only; WF-116 to WF-129 were appended for the features adopted from the competitive analysis and sit inside their months; WF-130 to WF-133 are new in Phase 1 and have no old ID: the kit port and shell, the AI provider seam, the AI sheet and action screens, and the demo seed with sample trips), each small enough for one Claude Code session. One of them (WF-129) is already on the cut list and is not counted in the committed plan (section 4). A section at the end explains how to work through it with Claude Code.

Effort assumes one developer with Claude Code working about 25 to 30 focused hours a week (the plan uses 27.5). Paths follow the repository layout in [02-architecture.md](02-architecture.md) section 2 (`apps/api`, `apps/worker`, `apps/web`, `apps/ios`, `packages/shared`, `packages/tokens`, `infra/`, `docs/`); if a path here differs from that tree, 02 wins. Spec references use the file numbers in the Phase 1 README table. Tickets that were in the full build roadmap keep their substance and get a new Phase 1 number; the map at the end of this file links old and new IDs.

## 1. Month plan

The month table is copied from the Phase 1 README. Months 3 and 5 are five weeks long because they carry the most work; the rest are four. Total: 26 weeks.

| Month | Weeks | Goal | Exit |
|---|---|---|---|
| 1 | 1 to 4 | Validate and set up: landing page and waitlist, 10 interviews, repo, CI, Docker, database, auth, tenancy | Demand signal; a signed-in user can create a trip on staging |
| 2 | 5 to 8 | Core planning: trips, collaboration, flights (cached), stays, itinerary, places, map, the sync indicator | Two people can plan a trip together on the web |
| 3 | 9 to 13 | AI and credits: Claude API loop, explain, drafts, research, agent runs, taster, ledger, ceilings, shared cache, evidence labels with the 14-day freshness flag and recheck | Agent run cost measured over 50 runs; ceilings enforced |
| 4 | 14 to 17 | Money: RevenueCat, Plus, Trip Pass, packs, paywalls (iOS purchases only), affiliate redirect and reporting, checklist; imports with entries named for TripIt, Tripsy and Wanderlog; Verify this plan; admin essentials | Sandbox purchases work end to end; clicks and conversions tracked |
| 5 | 18 to 22 | iOS and polish: Capacitor shell, push, offline, calendar feed and opt-in feed polling, Verify this plan screens, presentation, accessibility, performance, onboarding, empty and error states, status banner; TestFlight beta | 30 beta testers, crash-free sessions above 99.5% |
| 6 | 23 to 26 | Launch: App Review, privacy labels, support, monitoring, runbooks, SEO pages, comparison pages, trust pages, Android install guide and testing, Verify evals, launch campaign | Live on the App Store and web |

Do not start a month's feature work until the previous exit is met, except for the long-lead items in section 3. Each exit gets a short gate review written to `docs/gates/month-N.md` (see section 8). The biggest schedule risks are Month 3 (AI cost and ceilings) and Month 5 (the first native build, on a GitHub macOS runner; see knowledge/ios-builds-on-ci.md).

### Month 1 (weeks 1 to 4): validate and set up

Tickets WF-001 to WF-019 and WF-130. About 90 ticket hours plus about 20 hours of interviews and price testing.

| Week | Milestone | Tickets |
|---|---|---|
| 1 | Landing page live with waitlist; repo scaffolded; written "yes" signal agreed before the first interview call; Apple Developer enrollment started | WF-001, 002, 003, 004, 006 |
| 2 | CI green on Linux; Docker image builds; reusable modules ported; interviews 1 to 6 done | WF-005, 007, 008, 010 |
| 3 | Merge to `main` deploys to staging; database at head with roles; identity and trips schema; JWT verification; interviews 7 to 10 done; go or no-go decision record signed | WF-009, 011, 012, 013 |
| 4 | Data access layer, row-level security and cross-tenant leak tests green; kit port and shell (WF-130) before every UI ticket; web client signs in; a signed-in user creates a trip on staging | WF-014, 015, 016, 017, 130, 018, 019 |

Exit: demand signal recorded (a "no-go" stops the backlog after week 3); a signed-in user can create a trip on staging; zero leaks in the tenant suite. Gate checklist: 10 section 7.1, run in the ship session of prompt 07; `[agent]` items are checked with a command, `[owner]` items become `HUMAN_TASKS.md` rows.

### Month 2 (weeks 5 to 8): core planning

Tickets WF-020 to WF-040, WF-125 and WF-133. About 100 ticket hours.

| Week | Milestone | Tickets |
|---|---|---|
| 5 | All planning and billing tables exist; seeds loaded; entitlement resolver enforcing trip limits; error reporting live | WF-020, 021, 022, 023, 037 |
| 6 | People, invites and roles work; a Free owner can invite 1 collaborator; activity feed; rate limits; notes; responsive layout with empty and error states | WF-024, 025, 026, 027, 028, 035, 036 |
| 7 | Cached fares and alerts rules; itinerary with calendar and ICS export; places and map; FX; analytics base; the "Synced N seconds ago" indicator | WF-029, 030, 031, 032, 033, 038, 125 |
| 8 | Lodging with hearts and compare (and the shared SSRF guard); backup and restore drill; the owner's own trips migrated so the owner and a partner plan a real trip together on staging; the demo seed, sample trips and the Discover tab | WF-034, 039, 040, 133 |

Exit: two people can plan a trip together on the web; restore drill passed once. Gate checklist: 10 section 7.1, run in the ship session of prompt 12; `[agent]` items are checked with a command, `[owner]` items become `HUMAN_TASKS.md` rows.

### Month 3 (weeks 9 to 13): AI and credits

Tickets WF-041 to WF-062, WF-120, WF-131 and WF-132. About 134 ticket hours. The admin cost-control screens (foundation, audit, kill switches, AI spend) are built here, not in Month 4, because the 50-run measurement and the spend drill need them; the rest of the admin console follows in months 4 to 6.

| Week | Milestone | Tickets |
|---|---|---|
| 9 | AI, credit and run schema; flags and kill switches; metering; credit ledger with taster and monthly grants | WF-041, 042, 043, 044 |
| 10 | Spend ceilings; job queue and lanes; AI provider seam (WF-131, before the Claude client); notification service and email; scheduler and price-check jobs | WF-045, 046, 131, 047, 051 |
| 11 | Claude client with `explain`, drafts and packing list; agent loop; research with shared cache; consent; guest mode and claim | WF-048, 049, 050, 054, 062 |
| 12 | Live fare provider behind its flag; agent runs API and screen with the taster; evidence labels; global breakers; first 50-run cost batch starts | WF-052, 053, 055, 056, 057 |
| 13 | Admin foundation, audit log, kill switch console and AI spend screen; evidence freshness flag and one-tap recheck; the AI sheet and action screens; 50 runs measured; a spend drill and a kill switch drill recorded | WF-058, 059, 060, 061, 120, 132 |

Exit: agent run cost measured over 50 runs and inside the $0.80 cap; every ceiling enforced; AI off switch stops AI in under 30 seconds. Gate checklist: 10 section 7.2, run in the ship session of prompt 16; `[agent]` items are checked with a command, `[owner]` items become `HUMAN_TASKS.md` rows.

### Month 4 (weeks 14 to 17): money, imports, admin essentials

Tickets WF-063 to WF-079 and WF-116, 117 and 121. About 104 ticket hours plus 2 hours of checking rival help pages. Apple's Paid Applications Agreement, tax forms and App Store Connect products must be ready by week 14 (start in Month 1).

| Week | Milestone | Tickets |
|---|---|---|
| 14 | RevenueCat webhooks idempotent in staging; credit grants and refund reversal; Trip Pass binding; paywall decided by the server | WF-063, 064, 065, 066 |
| 15 | `/go` redirect, disclosure and placements; conversion import; "Before you go" checklist; import entries named for TripIt, Tripsy and Wanderlog with pasted places | WF-067, 068, 069, 070, 121 |
| 16 | Switching import: ICS file, ICS feed (SSRF guarded), pasted confirmations; first import earns a free Trip Pass; Verify this plan schema and reading a pasted plan | WF-071, 072, 073, 074, 116 |
| 17 | Booked-fare drop alert; a throwaway sandbox purchase harness proves every product end to end; admin users, subscriptions and overview; Verify this plan item checks and credit settlement (runs about 4 hours over the week's hours; week 14 has about 7 spare) | WF-075, 076, 077, 078, 079, 117 |

Exit: sandbox purchases work end to end (harness build); affiliate clicks and conversions tracked in the overview; all three import paths and the named entries work on staging; a pasted plan can be read and checked through the API on staging. Gate checklist: 10 section 7.3, run in the ship session of prompt 21; `[agent]` items are checked with a command, `[owner]` items become `HUMAN_TASKS.md` rows.

### Month 5 (weeks 18 to 22): iOS and polish, TestFlight beta

Tickets WF-080 to WF-103 and WF-118, 122, 123 and 126. About 134 ticket hours (WF-122 is built and counted here). This month builds on a GitHub macOS runner (see knowledge/ios-builds-on-ci.md), with device checks owner-pending, and it is the most loaded month (106 percent of its hours, section 3): the Verify screens and feed polling are web work that can run while a device build waits.

| Week | Milestone | Tickets |
|---|---|---|
| 18 | Capacitor shell runs on a device against staging; native plugins; Sign in with Apple; App Attest; opt-in calendar feed polling and change preview | WF-080, 081, 082, 083, 123 |
| 19 | In-app purchases through RevenueCat; universal links; push; TestFlight internal build from the pipeline | WF-084, 085, 086, 087, 101 |
| 20 | Offline reading and edit queue; calendar subscription feed; account deletion and export; settings, consents and legal pages | WF-088, 089, 090, 092, 093, 094 |
| 21 | Presentation mode and PDF; onboarding switching question; accessibility; performance pass; analytics events; external TestFlight beta opens (30 testers) | WF-091, 095, 096, 097, 098 |
| 22 | Admin affiliate revenue; uptime and status page; public status summary and banner; Verify this plan screens; Google Maps export file import; purchase matrix passed; beta report | WF-099, 100, 102, 103, 118, 122, 126 |

Exit: 30 beta testers, crash-free sessions above 99.5 percent over 100 or more sessions, purchase matrix passed, a trip fully browsable in airplane mode on a real device. Gate checklist: 10 section 7.4, run in the ship session of prompt 25; `[agent]` items are checked with a command, `[owner]` items become `HUMAN_TASKS.md` rows.

### Month 6 (weeks 23 to 26): launch

Tickets WF-104 to WF-115 and WF-119, 124, 127 and 128. About 92 ticket hours. It is no longer as light as planned (98 percent of its hours, section 3): App Review takes one to four days per cycle, and this month absorbs fixes, so the Verify evals and the Android work are web or server only and can continue during review.

| Week | Milestone | Tickets |
|---|---|---|
| 23 | Store listing and privacy labels; support inbox; content reports; public sample and shared-trip pages live; How we earn, How billing works and the cancel link | WF-104, 105, 106, 107, 124 |
| 24 | Referral credits; comparison pages; penetration test fixed; review notes and demo account; Verify this plan evals and release gate; **build submitted to App Review at the end of the week** | WF-108, 109, 110, 111, 119, 115 (submit) |
| 25 | Load test at 10 times launch traffic; runbooks drilled; admin user actions and flags and health screens; Android install guide and Android Chrome test pass; answer review feedback | WF-112, 113, 114, 115, 127, 128 |
| 26 | Release (manual), launch campaign, 72-hour monitoring | WF-115 |

Exit: live on the App Store and web; the Verify evals pass their gates or the `verify_plan` flag stays off; Android Chrome tested; no P0 in the first 72 hours; crash-free at least 99.5 percent; API error rate under 1 percent. Gate checklist: 10 section 7.5; `[agent]` items are checked with a command, `[owner]` items become `HUMAN_TASKS.md` rows.

## 2. Critical path

The single longest chain of dependencies; a slip anywhere on it moves the launch date.

```
WF-004 scaffold -> WF-007 CI -> WF-008 Docker -> WF-011 migrations -> WF-012 identity schema
  -> WF-013 JWT -> WF-014 data access -> WF-015 RLS -> WF-016 leak tests      (Month 1 gate)
  -> WF-041 AI schema -> WF-044 ledger -> WF-045 ceilings -> WF-131 AI provider seam -> WF-048 Claude client
  -> WF-049 agent loop -> WF-057 50-run cost measurement                       (Month 3 gate)
  -> WF-022 billing schema -> WF-023 resolver -> WF-063 RevenueCat webhook
  -> WF-076 sandbox harness (runner)                                            (Month 4 gate)
  -> WF-080 Capacitor shell -> WF-084 purchases in the app -> WF-102 purchase matrix
  -> WF-101 TestFlight pipeline -> WF-104 store listing -> WF-111 review notes
  -> WF-115 submit and launch                                                  (Month 6 gate)
```

WF-130 (kit port and shell) follows WF-017 and comes before every UI ticket (the one exception is WF-002, the prompt 01 landing page): each screen ticket depends on it directly or through WF-018. WF-131 (AI provider seam) comes before WF-048, and WF-132 (AI sheet) after the AI features it shows.

Verify this plan (WF-116, 117, 118, 119) hangs off the AI path (Claude client WF-048, evidence labels WF-055, credits WF-044) and the redaction built in WF-073; it is server-side except the screens, so it can be switched off with the `verify_plan` flag if its evals are not ready. Switching import (WF-071 to WF-074, 121, 123), offline (WF-088, WF-089), the calendar feed, referral credits and the public pages hang off this path: they must finish before the binary is submitted in week 24 only where they ship inside the app (offline, import screens, referral screen, onboarding question, Verify screens, the cancel row and the sync indicator). Web-only work (public pages, `/vs` pages, most admin screens) can finish during review.

Long-lead items that are off the code path but on the calendar path: Apple Developer enrollment (days to weeks; start in week 1), Paid Applications Agreement and tax forms, the GitHub macOS runner setup (see knowledge/ios-builds-on-ci.md), Travelpayouts approval, Viator and Stay22 approvals, booking the outside penetration test firm (book by week 18 for week 23), and App Review itself.

## 3. Capacity check

Assumption: one developer, Claude Code for implementation and review, 25 to 30 focused hours a week. Sizes are focused hours including the Claude session, your review, the fix loop and the pull request: S about 2 hours, M about 4 (half a day), L about 8 (a day, never larger). Non-ticket work is planned separately because it does not shrink with better tooling.

| Month | Weeks | Hours at 25 a week | Hours at 27.5 | Hours at 30 | Ticket hours | Non-ticket hours | Load at 27.5 |
|---|---|---|---|---|---|---|---|
| 1 | 4 | 100 | 110 | 120 | 90 | 20 (10 interviews, price test, Apple enrollment) | 100% |
| 2 | 4 | 100 | 110 | 120 | 100 | 4 (partner dogfooding sessions) | 95% |
| 3 | 5 | 125 | 138 | 150 | 134 | 6 (reading the 50-run cost report) | 101% |
| 4 | 4 | 100 | 110 | 120 | 104 | 8 (affiliate approvals, tax forms, products, checking the rival help pages behind the import entries) | 102% |
| 5 | 5 | 125 | 138 | 150 | 134 | 12 (beta tester support and feedback) | 106% |
| 6 | 4 | 100 | 110 | 120 | 92 | 16 (App Review replies, support, launch campaign) | 98% |
| Total | 26 | 650 | 716 | 780 | 654 | 66 | 100.6% |

Recomputed in two steps. First, the features adopted from the competitive analysis (WF-116 to WF-129, 62 hours plus 2 non-ticket hours) took the plan to 690 of 716 hours, 96.4 percent, so the Google Maps export file import (WF-122, 4 hours) and status page polish (WF-129, 2 hours) were moved to the cut list, giving 618 ticket hours plus 66 non-ticket hours, 684 of 716, 95.5 percent. Second, the runtime, data and business fixes added four tickets (WF-130 kit port and shell, L, 8 hours; WF-131 AI provider seam, L, 8 hours; WF-132 AI sheet and action screens, L, 8 hours; WF-133 demo seed, sample trips and Discover, M, 4 hours; 28 hours in all), brought WF-122 back into the plan (4 hours, so it leaves the cut list and is built) and grew WF-022 from M to L (4 extra hours). That is 36 hours more: 654 ticket hours plus 66 non-ticket hours, 720 of 716 hours at 27.5 a week, 100.6 percent. This is 4 hours over the available hours and 40 hours above the 95 percent line (680 hours). The Month 6 reserve is used first: if the total passes the 95 percent line, take the overrun from Month 6 before touching any other month, then run the cut list in section 4. WF-129 (2 hours) stays on the cut list and out of the committed hours. The pasted-places import and the named Tripsy and Wanderlog entries (WF-121) and the basic hosted status page (WF-100 and WF-126) stay in the plan.

Reading the table:

- At 27.5 hours the plan uses 720 of 716 hours, which is 4 hours over with no reserve. At 30 hours the reserve is about 60 hours. At 25 hours the plan is 70 hours over (720 of 650), so the cut list in section 4 will almost certainly be needed, and the first things on it are listed there.
- Months 3, 4 and 5 are now the tightest (101, 102 and 106 percent of their hours), as well as Month 1 (100 percent) and Month 6 (98 percent). Month 4 and Month 5 carry the new work that needs earlier tickets (Verify this plan, feed polling); if either month exits more than a week behind, run the cut list before starting the next month. Month 1 is full because validation runs beside setup; if week 4 slips, defer the second half of WF-005 (port only the flight and provider modules, the rest when first needed).
- Month 3 has the most variance: Procrastinate and the agent loop are new to this codebase, and the 50-run batch takes calendar time, not just hours. Start the batch by week 12.
- Month 6 is no longer under-loaded (98 percent). What keeps it safe is that its new work is web or server only (Verify evals, trust pages, Android guide and testing), so a failed App Review cycle delays the binary without blocking those tickets; do not add more to Month 6, and the Month 6 reserve is used first for the overrun, then the cut list in section 4.
- If more than two weeks behind at a month exit, stop and run the cut list before starting the next month.
- Two or three parallel sessions help with wall-clock time but not with your review hours, so the plan counts review hours once.

## 4. What to cut first if behind schedule

**Already cut to keep the plan near 95 percent** (section 3): the repair items (repair-a-day and paste-your-group-chat) were already moved to Phase 2, so nothing more comes out there; status page polish (WF-129, 2 hours) is on the cut list and out of the committed hours. The Google Maps export file import (WF-122) left the cut list and is built in Month 5. If a month ends ahead of plan, build WF-129 only. If the plan falls behind, do not wait for it: go to the table below.

Cut in this order. Each item keeps the product honest and launchable; none touches tenancy, credits, purchases, deletion, consent or disclosure. Hours are the ticket estimate saved.

| Order | Cut | Tickets | Saves | What happens instead |
|---|---|---|---|---|
| 1 | Referral credits | WF-108 | 8 h | Ship in 1.1, about 3 weeks after launch |
| 2 | `/vs` comparison pages | WF-109 | 4 h | Publish after launch; the landing page covers switching |
| 3 | Admin flags, provider and system health screens | WF-114 | 8 h | Kill switch screen plus Better Stack and provider dashboards |
| 4 | Admin user actions | WF-113 | 8 h | Audited command-line scripts for credit grants and sign-out |
| 5 | Admin affiliate revenue screens | WF-099 | 4 h | SQL views in Metabase |
| 6 | Offline edit queue (keep offline reading) | WF-089 | 4 h | Edits need a connection; reading works offline (this is what App Review checks) |
| 7 | Calendar subscription feed (keep ICS export) | WF-090 | 4 h | Export file only |
| 8 | ICS feed import (keep file import and pasted import) | WF-072 | 8 h | Also removes the feed SSRF surface at launch |
| 9 | Booked-fare drop alert | WF-075 | 4 h | Ship in 1.1; price alerts still work |
| 10 | Live flight provider (keep cached fares) | WF-052 | 8 h | `serpapi_live_fares` stays off; Plus shows cached fares with age labels |
| 11 | Evals beyond the fare set | WF-057 | 4 h | Keep the cost measurement, run the other evals after launch |
| 12 | Opt-in calendar feed polling (keep the one-time feed import and manual refresh) | WF-123 | 8 h | "Keep checking this calendar" arrives in 1.1; nothing else changes |
| 13 | Android install guide page and card (keep the manifest) | WF-127 | 2 h of 4 | The Android web app still installs from Chrome's menu; the guide follows after launch |

Verify this plan (WF-116 to WF-119) is not on this list: it is the main funnel from the largest competitor and its credit pricing funds itself. If it slips, ship it behind the `verify_plan` flag in 1.0.1 rather than cutting it, because it is server-side except for its screens.

Cutting items 1 to 5 saves 32 hours; 1 to 8 saves 48; 1 to 11 saves 64; 1 to 13 saves 74. Never cut: WF-014 to WF-016 (tenancy), WF-044 and WF-045 (credits), WF-063 (purchases), WF-092 and WF-093 (deletion, export), WF-054 (AI consent), WF-068 (disclosure), WF-106 (content reports, needed for Guideline 1.2), WF-110 (security review). If you must drop an iOS feature, drop native polish before you drop offline reading.

## 5. Risk register

| # | Risk | Likelihood | Impact | Mitigation | Owner ticket |
|---|---|---|---|---|---|
| 1 | No demand | Medium | High | Month 1 gate before any rewrite; kill rule at month 9 after launch | WF-003, WF-079 |
| 2 | Cross-tenant data leak | Low | Severe | Data access layer, RLS, automated leak tests, penetration test | WF-014 to WF-016, WF-110 |
| 3 | AI cost overrun or runaway agent | Medium | High | Hard stops, ceilings, reserve then settle, breakers, kill switches, alerts | WF-043 to WF-045, WF-056, WF-060, WF-061 |
| 4 | SerpApi terms block live fares | Medium | Medium | Provider interface, flag, cached Travelpayouts baseline | WF-003, WF-052 |
| 5 | App Review rejection (4.2, 3.1.2, 5.1.1(v), 1.2, privacy labels) | Medium | Medium | Offline, push, Restore, deletion, report and block, review notes, TestFlight self-check | WF-080 to WF-102, WF-111 |
| 6 | Entitlement mismatch or double credit grant | Medium | Medium | Idempotent webhooks keyed on transaction id, nightly reconcile, replay tool | WF-063, WF-064, WF-078 |
| 7 | Affiliate disclosure or tracking failure | Low | High | Disclosure component with tests, no ranking by commission test, no fetching of Airbnb, Vrbo or Booking.com pages | WF-067, WF-068 |
| 8 | No Mac available | Certain | Medium | Builds run on a GitHub macOS runner, free for this public repository; device checks wait for the owner's iPhone | WF-076, WF-080 |
| 9 | Import abuse: SSRF through feed URLs, hostile ICS files, PII leaking to the AI | Medium | High | Shared SSRF guard, sandboxed parser with limits, fuzzing, redaction before every model call | WF-071 to WF-073, WF-110 |
| 10 | Import reward and referral farming | Medium | Medium | One reward per account, at least 3 items including a flight or a stay, verified email, no active Plus, referrer caps of 5 per 30 days and 10 per year, device and IP checks, revocation | WF-074, WF-108 |
| 11 | Public pages leak private data or host abusive content | Low | High | Redaction tests, noindex by default, report queue, one-click takedown | WF-106, WF-107 |
| 12 | WebView jank on maps and calendar | Medium | Medium | Simplify the phone calendar, cluster markers, profile early | WF-032, WF-033, WF-097 |
| 13 | Migration error on the owner's data | Low | Medium | Dry run, row counts, idempotent importer, backup before import | WF-040 |
| 14 | Solo bus factor and burnout | High | High | Strict month exits; use the cut list before cutting quality; runbooks | WF-112 |
| 15 | Web users cannot buy (purchases are in the iOS app only in Phase 1) | High | Low | The web paywall says "Upgrade in the iOS app" with no price list or purchase button; Android and web billing are Phase 2 work | WF-066 |
| 16 | Verify this plan shows a wrong fact as confirmed (a false green) | Medium | High | Verdicts are decided in code, every green or amber needs a cited page containing the value, evals gate release (false green under 2 percent, invented places never green), thumbs and "Price was different" style reports feed the eval set, flag and kill switch | WF-117, WF-119 |
| 17 | Calendar polling stores a secret feed address or hammers a host | Low | Medium | Encrypted only while polling is on, 3 polled feeds per person, 6-hour interval, 60 fetches an hour per host, three failures stop it, kill switch `import.polling` | WF-123 |
| 18 | The Android web app feels unfinished on real devices | Medium | Low | Android Chrome test pass before launch, install guide states what works and what does not, native Android is Phase 2 | WF-127, WF-128 |

## 6. Backlog

Conventions for every ticket:

- **Heading:** `WF-NNN title [month, size]`. Sizes: S (about 2 hours), M (half a day), L (a day; never larger, split instead).
- **Depends on:** the tickets that must be merged first.
- **Definition of done (DoD)**, applied to every ticket and written once here. Each ticket's Done line adds only what is extra.
  1. The change is on a branch, reviewed against the ticket's acceptance list, and merged to `main` through a pull request; one commit per ticket, message `WF-NNN title`.
  2. `npm run lint` and `npm test` pass locally and in CI. The tests named in the ticket exist and fail without the change.
  3. If any route or schema changed: `npm run gen:api` was run and the regenerated `apps/web/src/lib/api/schema.d.ts` is committed.
  4. If any model or migration changed: the migration follows `.claude/rules/database-migrations.md` (expand and contract, one head, tested from empty and from the previous revision).
  5. New environment variables are documented in `.env.example`; no secrets in the repo.
  6. UI copy follows the copy rules (sentence case, plain verbs, no em dashes) and the Hermi design tokens.
  7. The work respects the non-negotiable rules in the [root README](../README.md) (no ranking by commission, no fetching Airbnb, Vrbo or Booking.com pages, sources on every AI fact).
  8. A new analytics event is added to the catalogue in [10-quality-security-launch.md](10-quality-security-launch.md) section 4 and to `packages/shared/src/events.ts` before it fires.
  9. UI tickets match their `Kit:` mockup (`npm run test:kit` passes) and the DL section 11 checklist was run.
  10. Every state listed for the screen in 05 section 6 is built and has a component test; offline and error also have a Playwright test.
  11. `scripts/check-copy.mjs` and stylelint pass.

### Month 1: validate and set up

#### WF-001 Name, domain and email [M1, S]
- Depends on: none.
- Description: produce the documents and scripts to confirm the name Hermi: the trademark search checklist (classes 9, 39, 42, for the attorney opinion on the Hermio and Hermès risks in [brand/BRAND.md](../brand/BRAND.md)), the DNS and mail record list for `hermi.world` (and `heyhermi.com` as a redirect), `support@`, `no-reply@` and the Resend sending domain with SPF, DKIM and DMARC, and the `check-mail-auth` script. The trademark opinion, the domain purchase, the Apple Developer enrollment and the App Store name "Hermi: Group Trip Planner" are owner tasks in `HUMAN_TASKS.md`. If the search or the opinion blocks the name, the fallback names are in the same brand file. Spec: [02-architecture.md](02-architecture.md).
- Accept: `docs/adr/0001-name.md` holds the search checklist and a provisional name decision, and `infra/scripts/check-mail-auth` exists and takes a domain.
- Touches: `docs/adr/`, `infra/cloudflare/` (record list in `rules.md`), `infra/scripts/`.
- Tests: a script `infra/scripts/check-mail-auth` that queries the DNS records and exits non-zero if any is missing.
- Done: "Done (docs)" and a provisional "go" row in `DECISIONS.md`.

#### WF-002 Landing page and waitlist [M1, M]
- Depends on: WF-001, WF-004, WF-006.
- Description: a static page on Cloudflare Pages with the positioning line "Plan together. Know the fare.", the logo, a waitlist form (email plus "who do you plan trips with" and "which app do you use today"), and a privacy note. Waitlist entries are logged (structured log, deduplicated in memory) and added to the Resend audience when `RESEND_API_KEY` is set; there is no waitlist table in Phase 1.
- Accept: form submit logs one entry per email (duplicates ignored in memory) and adds it to the Resend audience when `RESEND_API_KEY` is set; confirmation email sent; page scores 90 or more on Lighthouse mobile; no ad or tracking SDKs; privacy text links to a policy page.
- Touches: `apps/web/public/` (static landing page deployed to Cloudflare Pages), a small `POST /v1/waitlist` route in `apps/api/hermi/modules/notifications/`.
- Kit: 05 6.1; screens/01-welcome.html
- Tests: route accepts valid email, rejects invalid, dedupes, rate limits; Playwright submit flow.
- Done: DoD. "Page live on the production domain" is owner-pending (it needs the domain and the Cloudflare Pages account, `HUMAN_TASKS.md`); the rest is checked locally and in CI.

#### WF-003 Interview kit, price test and terms checklist [M1, S]
- Depends on: WF-001.
- Description: write the interview script, the written "yes" signal, the paywall and price test cards (Trip Pass $9.99; Plus $5.99 a month or $39.99 a year), a question on switching from TripIt, Tripsy or Wanderlog (would a free Trip Pass for importing a trip change your mind?), and the provider terms checklist (SerpApi terms and the Google lawsuit, Geoapify caching terms, Travelpayouts rates and app eligibility).
- Accept: the interview script, the written "yes" signal, the price test cards, the switching question and the terms checklist are in `docs/validation/` and a provisional "go" is in `DECISIONS.md`. The interviews, the price test and the signed decision are owner tasks.
- Touches: `docs/validation/`.
- Tests: none (documentation); checklist reviewed by the owner.
- Done: "Done (docs)". The owner can still record a no-go by stopping the driver and writing it in `DECISIONS.md`.

#### WF-004 Scaffold the repository [M1, M]
- Depends on: WF-003.
- Description: create the Hermi monorepo with the tree in [02-architecture.md](02-architecture.md) section 2: `apps/api` (Python 3.13, uv, FastAPI), `apps/worker`, `apps/web` (Vite, React 19, TanStack Query, Tailwind 4), `packages/shared`, `packages/tokens`, `packages/eslint-config`, `infra/`, `.github/` (workflows and Dependabot), `docs/` (`apps/ios` arrives in WF-080), a uv workspace and npm workspaces, root `package.json` scripts (`setup`, `start`, `dev`, `test`, `lint`, `format`, `gen:api`, `gen:shared`, `test:api`, `test:web`, `test:e2e`, `test:e2e:smoke`, `test:kit`, `evals`, `db:init`, `doctor` and `smoke:live`), `.env.example`. The scripts are node scripts (or use `cross-env`), so they run on Windows and Linux; dev scripts use `uv run --no-sync`. `db:init` runs `infra/db/bootstrap.sql` as `postgres` through `pgpass.conf` and finds the PostgreSQL 18 `bin` directory; `setup` runs `db:init`, generates local secrets into `.env` if absent (never overwriting), migrates when migrations exist and seeds `--demo` when WF-133 exists; `doctor` reports what is set and what is optional and never prints a value (ported from the Trip Planner `scripts/setup.mjs` and `setup_db.py`). `dev` serves the API on 8100 and Vite on 5173 (`envDir: '../..'`). Register the `posix_only` pytest marker; `cli.py` sets the Selector event loop on win32. The context layout already exists (CLAUDE.md, .claude/rules/, .claude/skills/, .claude/agents/, knowledge/): WF-004 does not create CLAUDE.md or rule stubs. It adds only the Commands section to CLAUDE.md after the commands run, extends an existing rule when a new path needs it, and creates the `run-hermi-locally` skill.
- Accept: `npm run setup && npm test && npm run lint` pass on a clean clone on Windows and Linux with no Docker; `GET /health/live` returns 200.
- Touches: repo root (`package.json`, `pyproject.toml`), `apps/api/pyproject.toml`, `apps/web/package.json`, `packages/`, `infra/`, `.github/`, `.claude/`.
- Tests: one pytest for the health route, one vitest smoke render.
- Done: DoD plus the README explains setup in under 10 lines.

#### WF-005 Port reusable modules [M1, L]
- Depends on: WF-004.
- Description: copy and adapt from the Trip Planner repo the modules that carry over: flight route and fare logic, itinerary and lodging logic, presentation mode, Hermi design tokens ([05-ui-ux-spec.md](05-ui-ux-spec.md) section 2; the values replace the old repo's, only the plumbing and neutral names are ported; into `packages/tokens`, including every token that section marks new, such as `--tp-edge`, `--tp-warning-ink` and `--tp-sky`), Travelpayouts, Geoapify, Wikipedia and Frankfurter providers, evidence rules in `services/agent_ingest.py`, and agent prompts. Leave behind passcode auth, the Claude CLI runner and the MCP bridge (WF-131 adapts the CLI runner as the dev-only provider), APScheduler, Windows scripts and Tailscale sharing. The Airbnb, Vrbo and Booking.com never-fetch list is one constant `BLOCKED_HOSTS` in `apps/api/hermi/modules/ai/policy.py` (06 section 2.4) holding the brands `airbnb`, `vrbo` and `booking`, matched on the registrable-domain label with any ending and any subdomain (so `airbnb.co.kr`, `www.airbnb.co.uk`, `vrbo.com` and `secure.booking.com` are refused), with no setting, flag or admin screen that can change it, imported by `security/ssrf.py` and the ingest checks. The API list and the CLI `--disallowedTools` rules are generated from it (the CLI rules add `WebFetch(domain:<brand>.*.*)` and `WebFetch(domain:*.<brand>.*.*)` to the `<brand>.*` and `*.<brand>.*` forms) and the stream check stays as a backstop. Fonts and tokens: install the three `@fontsource-variable` packages (`fredoka`, `atkinson-hyperlegible-next`, `atkinson-hyperlegible-mono`; OFL, bundled) and add `theme.css`. Follow the module map in [02-architecture.md](02-architecture.md). Port the flight and provider modules first; the rest may land as each feature ticket needs it.
- Accept: ported modules import cleanly and keep their original unit tests passing; a vitest test parses 05 sections 2.1 to 2.3, asserts they equal `tokens.css` and recomputes every WCAG ratio; a `docs/porting-map.md` lists each source file and its new home; no Windows-only code in `apps/` or `packages/`.
- Touches: `apps/api/hermi/providers/`, `apps/api/hermi/modules/ai/policy.py`, `apps/api/hermi/security/ssrf.py`, `apps/api/hermi/modules/*/service.py` (ported logic), `packages/tokens/`, `apps/web/src/lib/`.
- Tests: the original tests for each ported module, adapted; a test that greps for forbidden imports (`subprocess` is allowed only in `apps/api/hermi/providers/ai/claude_cli.py`; `apscheduler` is forbidden); one test covers the four hosts `airbnb.co.kr`, `www.airbnb.co.uk`, `vrbo.com` and `secure.booking.com`.
- Done: DoD plus the porting map reviewed.

#### WF-006 Typed configuration and environments [M1, M]
- Depends on: WF-004.
- Description: a settings module (`config.py`, the only place environment variables are read) with `ENVIRONMENT` (`local`, `ci`, `preview`, `staging`, `production`) as in 02 section 7. It covers `AUTH_MODE`, `ADMIN_AUTH_MODE`, `AI_PROVIDER`, `PROVIDERS_MODE`, `EMAIL_BACKEND` (`console`, `file`, `resend`), `STORAGE_BACKEND`, `IMPORT_SANDBOX`, the Local column of 02 section 7.1, and process environment overrides `.env`. Keyless: a provider with no key raises `NotConfigured`. `.env.example` is local-ready with `AI_PROVIDER=claude_cli`. Config refuses these outside `local` and `ci`: `AUTH_MODE=dev`, `ADMIN_AUTH_MODE=dev`, `STORAGE_BACKEND=local`, `EMAIL_BACKEND` other than `resend`, `PROVIDERS_MODE=fake`. Config allows `AI_PROVIDER=claude_cli` only when `ENVIRONMENT=local`, the server is bound to loopback (`127.0.0.1`, `::1`, `localhost`) and `AUTH_MODE=dev` or the user is in `AI_CLI_ALLOWED_EMAILS`; the provider factory re-checks the user part on every call. Staging and production need `ANTHROPIC_API_KEY` and `AI_PROVIDER=anthropic_api` (`render.yaml` pins it). The app refuses to start without the required secrets for its environment, keeps scheduled agents off (scheduled agent runs are not part of Phase 1), and tests refuse to run when `ENVIRONMENT=production`. There is no personal or single-household mode.
- Accept: settings load from env with typed validation; missing required secrets fail fast with a clear message listing names only; `.env.example` lists every variable; the refusal matrix holds (each rule above is refused as described, one test per rule).
- Touches: `apps/api/hermi/config.py`, `.env.example`, `apps/api/tests/test_config.py`.
- Tests: settings matrix (each environment), refusal when production, required-secret errors, and the refusal matrix: one test per rule above (the dev modes, `STORAGE_BACKEND=local`, an `EMAIL_BACKEND` other than `resend` and `PROVIDERS_MODE=fake` refused outside `local` and `ci`; `claude_cli` refused unless `ENVIRONMENT=local`, loopback and the auth or allowlist rule all hold; staging and production refused without `ANTHROPIC_API_KEY` and `AI_PROVIDER=anthropic_api`).
- Done: DoD plus `.env.example` checked against `config.py` in CI.

#### WF-007 CI pipeline [M1, M]
- Depends on: WF-004.
- Description: GitHub Actions `ci.yml` in `.github/workflows/`: lint, tests with a `postgres:18` service, OpenAPI drift check, migration test from empty and from the previous release, image build; `e2e.yml` for the Playwright smoke test. One aggregator job `ci` needs every other job and always runs (red if any needed job failed or was cancelled); it is the required check. WF-007 replaces the placeholder `.github/workflows/ci.yml` that already exists on `main`, and the rewrite keeps two things from it: the always-running job named exactly `ci` (branch protection requires that check name, and the driver merges only after the check named `ci` passes) and its "Autopilot tests" step (`node --test "scripts/autopilot/**/*.test.mjs"`, the driver's own tests). Deploy and live-eval jobs are gated on repository variables so `main` stays green without secrets. Dependency audits are non-blocking. The `e2e` workflow runs on pull requests with the `e2e` label and on `main`. Add a nightly `windows-latest` job. Copy lint runs in CI: `scripts/check-copy.mjs` over `locales/en.json` (created in WF-018; the script passes when the file does not exist yet), stylelint `declaration-strict-value`, and `jsx-a11y`.
- Accept: a PR with a failing test, lint error, API drift or two Alembic heads turns CI red; a clean PR is green in under 10 minutes.
- Touches: `.github/workflows/ci.yml`, `.github/workflows/e2e.yml`, `scripts/check-copy.mjs`.
- Tests: a deliberately broken branch for each check (recorded in the PR).
- Done: DoD plus branch protection requires CI on `main`.

#### WF-008 Docker image, compose and health endpoints [M1, M]
- Depends on: WF-007.
- Description: multi-stage Dockerfile (`node:22` builds the web, `python:3.13-slim` with `uv sync --frozen --no-dev`, non-root), commands `api`, `worker`, `scheduler`, `migrate`; `infra/docker/compose.yml` (Postgres 18, Mailpit, MinIO), optional for local development (native PostgreSQL 18 is the default path); `/health/live` and `/health/ready` (database reachable, migrations at head; it also reports `ai_provider`).
- Accept: `docker compose up` serves the API (checked in a CI job on a Linux runner with Docker, not on the owner's PC, which has no Docker); image runs as non-root; ready fails when migrations are behind; image scanned with Trivy in CI.
- Touches: `infra/docker/Dockerfile`, `infra/docker/compose.yml`, `apps/api/hermi/main.py` (health routes).
- Tests: readiness test with a stale migration; container smoke test in a CI job (a Linux runner with Docker).
- Done: DoD plus image size noted in the PR.

#### WF-009 Render and Cloudflare environments and deploy workflows [M1, L]
- Depends on: WF-008.
- Description: `infra/render/render.yaml` for API, worker and Postgres 18 (PITR) for staging and production, pinning `AI_PROVIDER=anthropic_api`; pre-deploy migration command with an advisory lock; Cloudflare DNS, TLS and WAF, Pages for the web build; `deploy-staging.yml` (on merge) and `deploy-prod.yml` (manual approval, promote the same image digest, rollback on failed health check). Deploy jobs skip cleanly without secrets; the account steps are owner-pending. Spec: [02-architecture.md](02-architecture.md).
- Accept: a merge to `main` reaches staging with migrations applied in under 10 minutes; production deploy needs approval; secrets live only in platform env groups.
- Touches: `infra/render/render.yaml`, `.github/workflows/deploy-staging.yml`, `.github/workflows/deploy-prod.yml`, `infra/cloudflare/`.
- Tests: post-deploy smoke test script; a forced failing health check triggers rollback (recorded).
- Done: DoD plus separate Anthropic workspace keys for staging and production.

#### WF-010 Security scanning workflows [M1, S]
- Depends on: WF-007.
- Description: `security.yml` (pip-audit, npm audit, gitleaks, CodeQL, Trivy), Dependabot grouped weekly, GitHub secret scanning and push protection. The audits report and do not block.
- Accept: a planted fake secret is caught by gitleaks in a test branch; workflows run weekly and on PR.
- Touches: `.github/workflows/security.yml`, `.github/dependabot.yml`.
- Tests: the planted-secret branch (not merged).
- Done: DoD plus findings triaged.

#### WF-011 Migration framework and database roles [M1, M]
- Depends on: WF-008.
- Description: the first range of the chain (`0001`) and the foundation under every later range. `infra/db/bootstrap.sql` (idempotent, run as `postgres` by `npm run db:init`) creates the roles of [03-database-schema.md](03-database-schema.md) section 6.1 (`hermi_owner`, `hermi_app`, `hermi_worker`, `hermi_admin`, `hermi_definer` and the `hermi_migrate_login`, `hermi_api_login`, `hermi_worker_login` and `hermi_admin_login` logins) and the `hermi` and `hermi_test` databases; migrations never `CREATE ROLE` and log in as `hermi_migrate_login`. Alembic on PostgreSQL 18 with `lock_timeout` and `statement_timeout`, an advisory lock around `upgrade head`, a head check, a UUIDv7 helper, and `0001_setup` (extensions, domains, `set_updated_at`, `bump_version`, helper-trigger functions, `currency_exponent`, `app_user_id`, and the check that the roles exist, which stops with "run `npm run db:init`" when one is missing). Write the expand and contract policy into `.claude/rules/database-migrations.md`. See [08-admin-control-center.md](08-admin-control-center.md) for the admin role.
- Accept: `npm run db:init` is idempotent; `0001` runs from empty; two heads fail CI; `hermi_app` cannot run DDL; `0001` fails with the clear message when a role is missing; the rules file documents the policy.
- Touches: `infra/db/bootstrap.sql`, `apps/api/hermi/migrations/` (`0001_setup`), `apps/api/hermi/db.py`, `.claude/rules/database-migrations.md`.
- Tests: migration-from-empty test, head-count test, role privilege tests, role-missing test.
- Done: DoD plus the rules file updated.

#### WF-012 Identity and trips schema [M1, M]
- Depends on: WF-011.
- Description: the range `0002` to `0004` of 03 section 10: `0002_identity` (`users`, `auth_identities`, `device_attestations`, `guest_allowances`, `devices`), `0003_reference_catalog` (`airports`, `fx_rates`, `places_cache`, `fx_convert_minor`, `CREATE TYPE ai_action`, `plans`, `store_products`, `credit_action_prices`) and `0004_trips_people` (`trips` with its owner-member trigger, `trip_members`, `trip_invites`, `trip_share_links`, `trip_destinations`, `activity_log`, `people` with `owner_user_id` and `linked_user_id`, `trip_people`, `redeem_trip_invite`, `transfer_trip_owner`). `trips` carries `version`, `editors_can_invite` and `calendar_token_hash`; `users` carries the `suspended` status and the column-level update grant of 03 section 6.1. No household tables (Phase 2). UUIDv7 public ids, `timestamptz`, money as integer minor units. DDL in [03-database-schema.md](03-database-schema.md).
- Accept: migrations `0002` to `0004` apply cleanly; constraints and indexes match 03; models and Pydantic schemas exist.
- Touches: `apps/api/hermi/migrations/versions/` (`0002` to `0004`), `apps/api/hermi/modules/{auth,trips,collaboration}/models.py`.
- Tests: constraint tests (unique member per trip, valid roles), schema-vs-DDL comparison test.
- Done: DoD plus seed data for two test users and a shared trip.

#### WF-013 JWT verification and user provisioning [M1, M]
- Depends on: WF-012.
- Description: `AUTH_MODE=supabase|dev`. In `supabase` mode verify Supabase JWTs (signature by JWKS with `kid`, issuer, audience, expiry); in `dev` mode verify tokens from the local key pair, refused outside `local` and `ci`. Map `sub` to `users` and `auth_identities`, create the user on first sign-in (with the "Me" `people` row), and retire the passcode path. First sign-in checks `identity_hashes` (a deleted and re-created account does not get the taster or first-import pass again). Build the dev routes `GET /v1/dev/personas` and `POST /v1/dev/session` (04 section 1.2); the first dev session creates the Free, Plus and admin personas (WF-133 adds only the demo trip and the sample trips). Spec: [04-api-spec.md](04-api-spec.md).
- Accept: expired, wrong-audience and tampered tokens get 401; the algorithm allowlist rejects `none` and mismatched algorithms; dev mode is refused outside `local` and `ci`; a deleted and re-created account gets no second taster or first-import pass; first request creates exactly one user under concurrency; Apple "Hide My Email" addresses are accepted.
- Touches: `apps/api/hermi/security/jwt.py`, `apps/api/hermi/modules/auth/`, `apps/api/hermi/deps.py`.
- Tests: token matrix with a local JWKS, the JWT algorithm allowlist test (reject `none` and mismatched algorithms), dev persona and session route tests, identity-hash test, concurrent first-login test.
- Done: DoD plus `SUPABASE_URL` documented.

#### WF-014 Tenant-scoped data access layer [M1, L]
- Depends on: WF-013.
- Description: one data-access layer every route uses: `require_trip_access(user, trip_id, min_role)` from `trip_members`, and query helpers that always filter by tenant. No route queries trip tables directly; an import-linter rule and a test enforce it. The `SystemSession` allowlist is one constant with one test, and `app_user_id()` is the database side of the user.
- Accept: all existing routes use the layer; a lint rule or test fails if a route imports a trip model directly; roles `owner`, `editor`, `viewer` enforced.
- Touches: `apps/api/hermi/deps.py` (`require_trip`), `apps/api/hermi/db.py`, every module's `repo.py` and `router.py`.
- Tests: permission matrix tests per role and endpoint.
- Done: DoD.

#### WF-015 Row-level security [M1, M]
- Depends on: WF-014.
- Description: Postgres RLS as a second lock: policies on trip-scoped tables keyed to a session variable set per request (`app.user_id`), the `hermi_app` role subject to RLS, `hermi_admin` with explicit admin policies. The policies themselves landed in `0014_rls` (P04), so there are no new tables: this ticket wires `app.user_id` per transaction, adds the startup refusal (superuser, `BYPASSRLS`, table owner), verifies `FORCE`, and tests the policies as `hermi_api_login`.
- Accept: a query with no session variable returns zero rows; a forced bug (app check removed) still cannot read another tenant's data.
- Touches: `apps/api/hermi/db.py` (set variable per transaction, startup refusal), `apps/api/tests/`.
- Tests: policy tests that bypass the app layer and query as `hermi_api_login`; `FORCE` verification; the startup refusal test.
- Done: DoD plus policy list documented.

#### WF-016 Cross-tenant leak tests [M1, M]
- Depends on: WF-015.
- Description: first add the `Idempotency-Key` middleware (required on every POST that reserves credits or writes money, 24 hour replay from `idempotency_keys`) and `If-Match` handling (`428 precondition_required`); then an automated suite that creates two accounts and tries to read, write and delete the other's trip, place, credit balance, webhook and export through every route (generated from the OpenAPI schema, under the real roles, for every route including the public token routes), with every route classified in `tests/route_policy.py` (see [10-quality-security-launch.md](10-quality-security-launch.md) section 1.3).
- Accept: every route returns 403 or 404 for the wrong tenant; the suite runs in CI and fails on any new unclassified or unprotected route.
- Touches: `apps/api/tests/tenancy/`, `apps/api/hermi/security/` (idempotency and precondition middleware).
- Tests: the suite itself, plus a mutation check (remove one guard and see it fail).
- Done: DoD plus recorded as Month 1 gate evidence.

#### WF-017 Web API client, environment config and bearer auth [M1, M]
- Depends on: WF-013.
- Description: `client.ts` with `VITE_API_BASE_URL`, `Authorization` middleware (default API base `http://localhost:8100`, bearer only, no cookies), one refresh attempt on 401, CORS origins for web, staging and Capacitor, and public keys (`VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `VITE_REVENUECAT_KEY_IOS`, `VITE_SENTRY_DSN`, `VITE_POSTHOG_KEY`) documented.
- Accept: the client works against staging; 401 triggers refresh then sign-out; no cookies used for hosted mode.
- Touches: `apps/web/src/lib/api/client.ts`, `apps/web/src/lib/env.ts`, `apps/api/hermi/main.py` (CORS).
- Tests: vitest client tests with a mock server; CORS preflight test.
- Done: DoD.

#### WF-130 Kit port, shell and kit tests [M1, L]
- Depends on: WF-005, WF-007, WF-017.
- Description: port the design kit so every screen starts from kit blocks. `packages/tokens` holds `tokens.css` (values equal 05 section 2) and `hermi.css`, imported verbatim; React wrappers in `apps/web/src/components/kit/` emit the `h-` classes (class names do not change). Build the Logo (from the `brand/` files; `generate_logo.py` is extended to emit transparent lockups, a light wordmark and the web icon set), RoutePattern, and the ticket, sheet, tab bar and section strip components. Build the scrolling shell from DL section 3: a sticky strip (a `nav` element with `aria-current="page"`), a scrolling sheet under it, the tab bar floating above the safe-area inset, an icon rail at 768 to 1199 px and the 248 px sidebar from 1200 px. The tabs are Trips, Discover, Activity and Account (each routes to a placeholder until its ticket lands). Add the kit test projects the `verify-ui-against-kit` skill uses: Playwright projects that screenshot the kit HTML and the app on a kit fixture with a frozen clock and Google Fonts routed to the bundled files, compared with pixelmatch inside one run (no committed baselines); a `kit-metrics` test that compares the computed styles of the `h-` components with the kit's; `npm run test:kit` runs them.
- Accept: `npm run test:kit` passes; `kit-metrics` and component parity pass for every block in `components.html`; the shell shows the rail at 768 and 1199 px and the sidebar at 1200 px; `document.fonts.check` is true for the three variable families and no request goes to `googleapis` or `gstatic`; every shell control has a 3 px solid focus ring and a logical tab order.
- Touches: `packages/tokens/` (`tokens.css`, `hermi.css`, `index.ts`), `apps/web/src/components/kit/`, `apps/web/src/shell/`, `apps/web/e2e/kit/`, `brand/generate_logo.py`, `apps/web/public/` (icons), root `package.json` (`test:kit`).
- Kit: 05 4.20, 4.21, 5.2, 5.3, 10; none, follow DL sections 3 and 11
- Tests: kit-metrics, component parity, shell layout at 390, 768, 1023, 1024, 1199, 1200 and 1440 px, the fonts and network check.
- Done: DoD plus the DL section 11 checklist run on the shell.

#### WF-018 Sign-in and first-trip wizard [M1, M]
- Depends on: WF-017, WF-130.
- Description: Sign in with Apple, Google and email code screens (when `AUTH_MODE=dev` the sign-in screen shows a persona picker: Free, Plus, admin); a short intro; "Create your first trip" wizard (destination, dates, who is going); the age gate; `locales/en.json` is created here; the profile screen (05 6.4) is built here (moved early). The "Coming from TripIt, Tripsy or Wanderlog?" question arrives in WF-095 and guest mode in WF-062. Spec: [05-ui-ux-spec.md](05-ui-ux-spec.md).
- Accept: new user reaches a created trip in under 2 minutes on staging; sign-out clears state; copy follows the rules.
- Touches: `apps/web/src/routes/auth/`, `apps/web/src/routes/onboarding/`.
- Kit: 05 6.1, 6.3, 6.4, 6.6; screens/01-welcome.html
- Tests: component tests, Playwright sign-in with a test identity. Smoke flow 1 (10 section 1.6), the dev sign-in persona flow: pick the Free persona and land on an empty Trips screen.
- Done: DoD.

#### WF-019 Trips module [M1, M]
- Depends on: WF-014, WF-018.
- Description: trips CRUD, destinations, dates and currency, archive, duplicate, trip switcher; the Overview (05 6.7) including the "Happening now" state (F-TRP-3, F-TRP-7); trash and restore (the `purge_trash` job is registered by WF-046); place autocomplete and the destination time zone (shared with WF-032; the keyboard alternative to drag and drop is in WF-032). Limits (2 active trips on Free) are enforced by the resolver in WF-023.
- Accept: create, edit, archive and duplicate work for the owner and are refused for viewers; a signed-in user creates a trip on staging.
- Touches: `apps/api/hermi/modules/trips/`, `apps/web/src/routes/trips/`.
- Kit: 05 6.5, 6.7, 4.4; screens/02-trips-home.html and screens/03-trip-overview.html
- Tests: CRUD, archive and duplicate tests; tenancy cases. Smoke flow 26 (10 section 1.6, 01 section 3.11): archive a past trip, then duplicate it into a new trip that appears in Trips.
- Done: DoD.

### Month 2: core planning

#### WF-020 Operations schema and seed data [M2, M]
- Depends on: WF-012.
- Description: the last range `0012` to `0015` of 03 section 10: `0012_admin_privacy` (`admin_users`, `feature_flags`, `kill_switches`, `audit_log` append only with update and delete rejected by trigger and the `retention_class` of 03 section 8, `support_tickets`, `content_reports`, `consents`, `data_exports`, `deletion_requests`, `rate_limit_counters`, and `idempotency_keys`, the 24 hour replay store for `Idempotency-Key`, created here because 03 creates it in `0012`), `0013_notifications_samples` (`notifications`, `sample_trips`, `plan_verifications`, `plan_verification_items`), `0014_rls` (helper functions, `trip_member_profiles`, `purge_trash`, `retention_sweep`, `maintain_partitions`, `drop_old_log_partitions`, `partition_default_rows`, policies with `FORCE` RLS for every table, grants and `SECURITY DEFINER` changes) and `0015_seed` (the Phase 1 plans, store products, credit prices, flags and kill switches, 03 section 11, idempotent; airports and FX rates are not in the seed: they load through `hermi seed-airports` and `hermi refresh-fx`, not a migration, 03 section 10). Product analytics stay in PostHog, so there is no `analytics_events` table.
- Accept: migrations `0012` to `0015` apply and the whole chain `0001` to `0015` is one linear chain that creates every table, type, function, policy and seed in 03; `audit_log` rejects `UPDATE` and `DELETE`; the 03 section 6.5 grants-and-RLS test passes; seeds are idempotent.
- Touches: `apps/api/hermi/migrations/versions/` (`0012` to `0015`), `apps/api/hermi/modules/{admin,auth,flights,notifications}/models.py`, `apps/api/hermi/seed/`.
- Tests: trigger test, seed idempotency test, the grants-and-RLS test, a test that the chain has one head and no table of 03 is missing.
- Done: DoD.

#### WF-021 Planning schema [M2, M]
- Depends on: WF-012.
- Description: the range `0009` to `0011` of 03 section 10: `0009_flights` (`flight_routes`, `fare_observations`, `trip_fare_links`, `chosen_flights`, `route_price_insights`, `booked_fare_drops`, `price_alerts`), `0010_itinerary_lodging` (`itinerary_days`, `saved_places`, `itinerary_items` with its foreign key to `trip_imports`, `lodging_options`, `lodging_votes`, `saved_place_votes`) and `0011_checklist_notes` (`checklist_items`, `notes`). No polls, expenses or settlements (Phase 2). Rows that two people edit carry `version` (03 convention 11).
- Accept: migrations `0009` to `0011` apply; every trip-scoped table has `trip_id` for RLS; indexes on common lookups.
- Touches: `apps/api/hermi/migrations/versions/` (`0009` to `0011`), `apps/api/hermi/modules/{flights,itinerary,places,lodging,trips}/models.py`.
- Tests: schema-vs-DDL test; foreign key and cascade tests.
- Done: DoD.

#### WF-022 Billing and revenue schema [M2, L]
- Depends on: WF-012.
- Description: the range `0005` to `0008` of 03 section 10, in ticket order (it may run as sub-steps, for example `WF-022.1` for `0005` and `0006`, `WF-022.2` for `0007` and `0008`): `0005_ai` (`runs`, `run_events` partitioned, `ai_usage`, `provider_calls` partitioned, `provider_call_rollups`, `shared_research_cache`, `my_provider_spend_micros`, the partition functions and first partitions, and Procrastinate's own schema with the `job_heartbeats` view), `0006_billing_credits` (`store_transactions`, `subscriptions`, `entitlements`, `trip_passes` with a `source` of `purchase` or `import_reward`, `webhook_events`, `credit_grants`, `credit_ledger` with its append-only trigger, `credit_debts`, `credit_balances`, `identity_hashes`, `identity_hashes_for`, `assert_credit_caller`, `reserve_credits`, `settle_credits`, `release_stale_reservations`, `expire_credit_grants`, `record_credit_debt`, `settle_credit_debt`, `ensure_free_monthly_grant`, `ensure_taster_grant`), `0007_imports_referrals` (`trip_imports`, `grant_import_reward`, `set_import_polling`, `referral_codes`, `referral_rewards`, `ensure_referral_code`, `my_referral_code`, `redeem_referral`, `grant_referral_reward`) and `0008_affiliate` (`affiliate_programs`, `affiliate_link_templates`, `link_clicks` partitioned, `affiliate_conversions` unique on program and network transaction id, `affiliate_payouts`, materialized views). No Stripe, concierge, partner guide, print or advisor tables.
- Accept: migrations `0005` to `0008` apply in order; uniqueness on store transaction id and webhook event id; one active pass per trip; `credit_ledger` rejects `UPDATE` and `DELETE`; the schema-vs-DDL test passes. WF-022 owns the migrations and that test; the models for the ai, credits and referrals tables are owned by WF-041 and WF-108.
- Touches: `apps/api/hermi/migrations/versions/` (`0005` to `0008`), `apps/api/hermi/modules/{billing,affiliate}/models.py`, `apps/api/tests/` (schema-vs-DDL test).
- Tests: uniqueness and idempotency constraint tests, append-only trigger test, schema-vs-DDL test.
- Done: DoD.

#### WF-023 Entitlement resolver and limit enforcement [M2, L]
- Depends on: WF-022, WF-019, WF-014.
- Description: a resolver that returns a trip's capabilities as the best of its owner's tier (`free`, `plus`) and any pass on that trip; enforces the limits of the Phase 1 tier table (active trips: Free 2, Plus fair use 25; cached-fare route per trip: Free 1; live routes: Plus 3, Trip Pass 2; alerts; collaborators: Free 1, Plus and Trip Pass 6); `GET /v1/me/entitlements`; paywall triggers `third_trip`, `invite`, `track_live` and `out_of_credits_*` (04 section 2.2 `PaywallHint`), and the other triggers follow 07 section 6.2 (`second_route`, `alert_limit`, `ninth_stay`, `export_footer`, `lifecycle_14d` with their mute caps from 6.5). A per-tier table test covers every limit key. Plan limits and missing entitlements return 402 with the `paywall` hint (403 stays for role, account and consent). Credit charging attaches when the ledger lands (WF-044).
- Accept: every limited route calls the resolver; creating a third active trip on Free returns 402 with the `third_trip` paywall hint (403 only for role, account and consent) and archived trips do not count; Plus with a Trip Pass takes the higher limit; invitees get the owner's tier on that trip only.
- Touches: `apps/api/hermi/modules/billing/` (resolver), `apps/api/hermi/modules/trips/service.py` (`trip_capabilities()`), `packages/shared/src/entitlements.ts`.
- Tests: table-driven tier and pass tests, invitee tests.
- Done: DoD.

#### WF-024 People (travelers) [M2, M]
- Depends on: WF-014, WF-130.
- Description: `people` with `owner_user_id` and `linked_user_id`, `trip_people`, "Which traveler are you?" linking; the Group screen (05 6.21). Children are a first name and a color only. Households are not built in Phase 1.
- Accept: a person can be linked to a user and unlinked; removal keeps history; no birthdate or email fields exist for travelers.
- Touches: `apps/api/hermi/modules/trips/` (people), `apps/web/src/routes/trips/`.
- Kit: 05 6.21; none, follow DL section 11
- Tests: link, unlink and removal tests.
- Done: DoD.

#### WF-025 Invites, roles and share links [M2, M]
- Depends on: WF-014, WF-130.
- Description: invite by link (`trip_invites`), accept, roles (owner, editor, viewer), leave, transfer ownership, and read-only `trip_share_links` with revoke, available on every tier (a Free owner's share page carries the "Made with Hermi" footer); invitees join free and get the trip's capabilities on that trip. Tokens are 128-bit random, stored as SHA-256 hashes.
- Accept: expired and used invites fail; owner cannot be removed without transfer; revoked link stops working immediately; a Free owner can create a share link; the collaborator limit hooks into the resolver (enforced in WF-026).
- Touches: `apps/api/hermi/modules/collaboration/`, `apps/web/src/routes/invite/`.
- Kit: 05 6.8; none, follow DL section 11
- Tests: invite lifecycle tests, role change tests, link revoke test.
- Done: DoD.

#### WF-026 Free owners invite 1 collaborator [M2, S]
- Depends on: WF-023, WF-025.
- Description: enforce the Phase 1 collaborator rule: a Free owner can have 1 collaborator (accepted or pending, editor or viewer) per trip, so couples plan free; Plus and Trip Pass owners up to 6; joining someone else's trip is always free. A second Free invite returns 402 with the `invite` paywall hint (reason `sharing`); the Invite sheet shows "1 of 1 on Free" and keeps the free path visible. If an owner's Plus or pass lapses, collaborators beyond the limit become viewers and nothing is deleted.
- Accept: a Free owner invites one person and sees the paywall on the second; pending invites count; lapse handling demotes extras and sets a banner flag; the invitee never needs a plan to join.
- Touches: `apps/api/hermi/modules/collaboration/service.py`, `apps/api/hermi/modules/billing/` (resolver hook), `apps/web/src/routes/invite/`.
- Kit: 05 6.8; none, follow DL section 11
- Tests: Free, Plus, pass and lapse tests; invitee-on-Free test; paywall body test. Smoke flows 3 and 4 (10 section 1.6): a Free owner invites one person by link and a second context accepts; the second invite shows the paywall with a visible close control.
- Done: DoD.

#### WF-027 Activity log and feed [M2, S]
- Depends on: WF-025.
- Description: `activity_log` writes for trip changes (who added, moved or removed what) with actor attribution, and a feed endpoint and screen: the Activity inbox and its tab (05 6.24). Notes marked private never appear.
- Accept: an edit by one member appears in the other's feed within 30 seconds; private notes excluded; deleted users show as "Deleted user".
- Touches: `apps/api/hermi/modules/collaboration/` (activity), `apps/web/src/routes/activity/`.
- Kit: 05 6.24; none, follow DL section 11
- Tests: write-on-change tests, privacy test.
- Done: DoD.

#### WF-028 Rate limits and abuse controls [M2, M]
- Depends on: WF-013, WF-020.
- Description: a Postgres token bucket per account and route class (AI endpoints 10 a minute, places search 30, outbound 60 an hour, import classes from [10-quality-security-launch.md](10-quality-security-launch.md) section 2.3), Cloudflare rules on auth and public routes, signup limits (5 accounts per IP per day), disposable-email blocking, `Retry-After` on 429. Limits are read from settings so they can change without a deploy.
- Accept: limits enforced per route class; 429 bodies use the shared error format; new route classes can be added with one config entry.
- Touches: `apps/api/hermi/security/rate_limit.py`, `infra/cloudflare/rules.md`.
- Tests: bucket tests with a fake clock, signup velocity test.
- Done: DoD.

#### WF-029 Currency and FX [M2, S]
- Depends on: WF-020.
- Description: a daily Frankfurter job into `fx_rates`; money display in original and converted currency; integer minor units everywhere.
- Accept: conversion rounds consistently; stale rates show a notice.
- Touches: `apps/worker/hermi_worker/jobs/refresh_fx_rates.py`, `apps/web/src/lib/money.ts`.
- Kit: 05 7.3; none, follow DL section 11
- Tests: conversion tests, stale-rate test.
- Done: DoD.

#### WF-030 Cached fares module [M2, M]
- Depends on: WF-014, WF-021, WF-005, WF-020, WF-130.
- Description: flight routes and Travelpayouts cached fares as the free baseline, fare observations and links to trips, chosen flight (with "Mark as booked" and the price paid, used by WF-075).
- Accept: Free gets 1 cached-fare route per trip; cached reads never spend credits; observations dedupe; every fare shows its age; the screen has a price calendar, price history, a cheapest highlight, 330 days ahead, and "Choose".
- Touches: `apps/api/hermi/modules/flights/`, `apps/api/hermi/providers/travelpayouts.py`, `apps/web/src/routes/flights/`.
- Kit: 05 6.9, 6.10, 4.5, 4.6; screens/05-fare-detail.html
- Tests: provider mocked tests, limit tests, dedupe tests.
- Done: DoD.

#### WF-031 Price alerts on cached fares [M2, M]
- Depends on: WF-030.
- Description: `price_alerts` rules on cached fares (1 on Free, more with live routes), drop detection as a pure function over `fare_observations`, alert list and create screens. The scheduled check arrives with WF-051 and delivery with WF-047.
- Accept: the detection function triggers once per drop; duplicate triggers blocked by a unique key; limit per tier enforced by the resolver.
- Touches: `apps/api/hermi/modules/flights/`, `apps/web/src/routes/flights/`.
- Kit: 05 6.9, 4.5; screens/05-fare-detail.html
- Tests: threshold tests, idempotent trigger test. Smoke flow 20 (10 section 1.6, 01 section 3.4): add a route, see cached fares, choose a fare, set an alert.
- Done: DoD.

#### WF-032 Itinerary, calendar view and ICS export [M2, L]
- Depends on: WF-014, WF-021, WF-130.
- Description: itinerary days and items, drag and drop, calendar view with a phone-friendly list mode and a "Move to..." sheet, conflict hints, ICS file export.
- Accept: day reorder works on web and phone; ICS file imports into Apple Calendar; edits by viewers rejected; two editors changing one item get a 409 with the latest row; place autocomplete and the destination time zone work (shared with WF-019); a keyboard alternative to drag and drop exists.
- Touches: `apps/api/hermi/modules/itinerary/`, `apps/web/src/routes/itinerary/`.
- Kit: 05 6.12, 6.13; screens/04-plan-day.html
- Tests: CRUD and role tests, ICS golden file, component tests, conflict test. Smoke flow 2 (10 section 1.6): create a trip with two destinations, add an itinerary item, reload, it persists.
- Done: DoD.

#### WF-033 Places and map [M2, M]
- Depends on: WF-014, WF-021, WF-130.
- Description: Geoapify search with `places_cache`, saved places, ideas list, MapLibre map with clustering, "Open in Apple Maps" handoff, attributions (OpenStreetMap, Wikimedia), Wikipedia summaries; the places-per-day cap.
- Accept: repeated searches hit the cache; places search rate limited at 30 a minute; map remains smooth with 200 markers.
- Touches: `apps/api/hermi/modules/places/`, `apps/web/src/routes/places/`.
- Kit: 05 6.14; none, follow DL section 11
- Tests: cache tests, rate limit test, marker clustering test. Smoke flow 22 (10 section 1.6, 01 section 3.6): drag items onto days, then use Add activity with place search and the map.
- Done: DoD.

#### WF-034 Lodging, hearts and compare [M2, M]
- Depends on: WF-014, WF-021, WF-130.
- Description: lodging options, pasted links, hearts (`lodging_votes`), compare view for 2 to 4 stays. Pasted links stay exactly as pasted; the server never fetches Airbnb, Vrbo or Booking.com pages; a separate labeled "Book via partner" button is built from the URL text only (wired in WF-068). Builds the shared SSRF guard `security/ssrf.py` and `providers/link_preview.py` that WF-072 reuses, with the hostile URL table of 10 section 2.5.
- Accept: no outbound request to those domains in tests (network blocked in test); hearts counted once per member; sort order is stated and never by commission; hostile URLs are refused; the bookmarklet works; each stay shows a per-night price; exactly one stay can be "Booked"; the compare cap is enforced.
- Touches: `apps/api/hermi/modules/lodging/`, `apps/api/hermi/security/ssrf.py`, `apps/api/hermi/providers/link_preview.py`, `apps/web/src/routes/lodging/`.
- Kit: 05 6.11, 4.10; screens/06-stays-vote.html
- Tests: network-blocked test, heart tests, link preservation test, SSRF table test. Smoke flows 5 and 21 (10 section 1.6): heart a stay in both contexts and the tally updates within 30 seconds; paste a stay link, heart it, compare two to four stays, mark one Booked.
- Done: DoD.

#### WF-035 Notes with sources [M2, S]
- Depends on: WF-021, WF-130.
- Description: trip, day, item and stay notes with optional `source_url`, `source_site`, `checked_at` and a private flag; a shared source chip component; the notes screen (05 6.18). AI-found notes must carry a source (enforced in WF-049 and WF-055).
- Accept: notes save with sources; private notes are visible only to their author; chips open the source.
- Touches: `apps/api/hermi/modules/trips/` (notes), `apps/web/src/components/`.
- Kit: 05 6.18; none, follow DL section 11
- Tests: CRUD and privacy tests.
- Done: DoD.

#### WF-036 Responsive layout, empty and error states [M2, L]
- Depends on: WF-017, WF-130.
- Description: built from 05 sections 4.20, 5.3 and 10 on top of the WF-130 shell: the bottom tab bar (Trips, Discover, Activity, Account) as a floating pill under 768 px, the icon rail from 768 to 1199 px, the 248 px sidebar from 1200 px, safe areas, 44 pt targets, 16 px inputs, bottom sheets for dialogs, and every empty and error state of 05 section 4 (offline, 401, out of credits, 429, maintenance, forced update included).
- Accept: every main route works at 390 px wide and at widths 1023, 1024, 1199, 1200 and 1440; no horizontal scroll; Playwright mobile project (iPhone 15 profile) passes.
- Touches: `apps/web/src/app/` (layout), `apps/web/src/routes/errors.tsx`, `apps/web/playwright.config.ts`.
- Kit: 05 5.3, 10, 4.15 to 4.18; none, follow DL section 11
- Tests: mobile viewport smoke test, axe checks in light and dark, and the contrast unit test over the Hermi palette token pairs in [05-ui-ux-spec.md](05-ui-ux-spec.md) section 2.3, including `--tp-edge` (control borders), `--tp-warning-ink` (small warning text) and `--tp-sky-ink` on `--tp-sky`.
- Done: DoD.

#### WF-037 Sentry and structured logs [M2, S]
- Depends on: WF-009.
- Description: JSON logs with `request_id`, `job_id`, `run_id`, opaque `user_id`; Sentry in API, worker and web with PII scrubbing; `RedactSecrets` covers `Authorization` and `x-api-key`; prompts and feed URLs never logged above DEBUG.
- Accept: a thrown error reaches Sentry with release and environment; a log scan test finds no emails, tokens or feed URLs.
- Touches: `apps/api/hermi/logging.py`, `apps/web/src/lib/sentry.ts`.
- Tests: redaction tests.
- Done: DoD.

#### WF-038 PostHog analytics base [M2, M]
- Depends on: WF-018.
- Description: the typed `analytics.capture` helper on server and client with the first events (`signup_completed`, `trip_created`, `first_itinerary_item_added`, `invite_sent`, `invite_accepted`); session replay off or masked; opt-out respected; no ad SDKs. Events beyond these arrive with each feature and are completed in WF-098.
- Accept: events fire once; opt-out stops all events; unknown names and properties are rejected server side.
- Touches: `apps/web/src/lib/analytics.ts`, `apps/api/hermi/analytics.py`, `packages/shared/src/events.ts`.
- Tests: event firing tests, opt-out test, unknown-property test.
- Done: DoD.

#### WF-039 Backups and restore drill [M2, M]
- Depends on: WF-009.
- Description: PITR enabled, daily snapshots, a weekly encrypted `pg_dump` to R2 in another account, and a scripted restore to a scratch database with the smoke test run against it.
- Accept: restore completes within the 1 hour RTO target; the drill is repeated quarterly (calendar entry).
- Touches: `infra/render/` (backup settings), `infra/scripts/restore-drill.sh`.
- Tests: the drill itself.
- Done: DoD plus drill result in `docs/runbooks/restore.md`.

#### WF-040 Migrate the owner's existing data [M2, L]
- Depends on: WF-024, WF-030, WF-032, WF-034.
- Description: `hermi import-legacy --source-db <url> --primary-email <email> --partner-email <email>` does a direct database copy (no export file) from the local Trip Planner database: transform (UUIDs, `owner_user_id`, `linked_user_id`, money to minor units), import into hosted with a dry run, row-count and checksum verification, and a manual walk-through of each trip. The owner's data is claimed through the one-time link emailed to the verified address and redeemed with `POST /me/legacy-claim` (04 section 5.1). Back up both sides first. The real run is owner-pending. The two owners then plan a real trip together on staging (Month 2 exit).
- Accept: dry run reports zero unmapped rows; counts match per table; both owners claim their data through the emailed one-time link, sign in and see their trips (owner verification pending for the real run); the import is idempotent.
- Touches: `apps/api/hermi/cli.py` (`import-legacy`, which replaces the old `infra/scripts/import_trip_planner.py` plan), `docs/runbooks/owner-migration.md`.
- Tests: import run against a fixture copy of a real-shaped database, idempotency test.
- Done: DoD plus the old install kept read-only for 30 days and the Month 2 gate review recorded.

#### WF-125 "Synced N seconds ago" indicator [M2, S]
- Depends on: WF-025, WF-035.
- Description: the sync indicator in every trip header (05 section 4.21): "Synced 12 s ago" from the last successful conditional sync response (200 or 304) or accepted queued edit, refreshed every 5 seconds, with the states Syncing, "Offline, N edits waiting" (wired to the offline queue when WF-089 lands) and "Could not sync, retrying" after three failed polls; tap runs a sync now. Text plus icon, state changes announced politely, never the ticking seconds. Sync uses conditional polling every 15 to 30 seconds; a conflict opens a "Keep mine" and "Use theirs" sheet.
- Accept: after a successful poll the header reads "Synced 0 s ago" and counts up; with the network off it reads the offline state within 5 seconds; a failed server poll never resets the timer; VoiceOver hears state changes only.
- Touches: `apps/web/src/components/sync-indicator/`, `apps/web/src/lib/sync.ts`.
- Kit: 05 6.41, 4.21; none, follow DL section 11
- Tests: fake-timer component tests for every state, an aria-live test, a Playwright test that cuts the network, and a two-context Playwright conflict test. Smoke flow 18 (10 section 1.6): the header shows "Synced N s ago" and "Offline, 1 edit waiting" when the network is cut (the degraded status banner half is in WF-126 Tests).
- Done: DoD.

#### WF-133 Demo seed, sample trips and Discover [M2, M]
- Depends on: WF-013, WF-019, WF-030, WF-032, WF-034, WF-130.
- Description: `hermi seed --demo`, run by `npm run setup`, adds the demo trip "Lisbon in March" to the Plus persona: a route with fake fares, a chosen flight, 3 stays with hearts, 4 itinerary days, a checklist and an evidence-labelled agent note (inserted by SQL against the tables that exist since P04, so later tickets only add models). The Free, Plus and admin personas are not created here: WF-013 builds `GET /v1/dev/personas` and `POST /v1/dev/session` and creates the personas on the first dev session, and the seed uses that same path. The seed also adds the sample trips (`sample_trips` rows with `tags` and `suits`, each backed by an ordinary trip owned by a content account). This ticket builds the three 04 section 5.28 sample routes (`GET /public/sample-trips`, `GET /public/sample-trips/{slug}` and `POST /public/sample-trips/{slug}/copy`); WF-107 reuses them. The Discover tab (05 section 6.23) shows the sample trips as a gallery: open one read-only, then "Use this plan" copies it into the user's trips. Later prompts extend the seed for their features.
- Accept: after `npm run setup` the Plus persona signs in and finds the demo trip, and any persona finds the gallery; a sample opens read-only; "Use this plan" calls `POST /public/sample-trips/{slug}/copy`, creates an editable copy (days, items and saved places, never flights or prices) and respects the active-trip limit (402 `limit_reached` and the `third_trip` paywall on Free); a guest builds a local copy with no server write; the seed is idempotent and creates no second persona.
- Touches: `apps/api/hermi/seed/demo.py`, `apps/api/hermi/api/public.py` (the 5.28 sample routes), `apps/api/hermi/modules/trips/` (copy from a sample), `apps/api/hermi/cli.py`, `apps/web/src/routes/discover/`, `apps/web/e2e/discover/`.
- Kit: 05 6.23, 6.35; screens/02-trips-home.html (card pattern)
- Tests: seed idempotency, sample read-only and copy route tests, and a Playwright flow that opens a sample and taps "Use this plan". Smoke flow 19 (10 section 1.6), the Discover flow: open a sample trip, tap "Use this plan", and see it as a new trip in Trips.
- Done: DoD plus the demo trip shown in the PR.

### Month 3: AI and credits

#### WF-041 AI, credit and run schema [M3, M]
- Depends on: WF-012.
- Description: models, repository and tests for `runs`, `run_events`, `ai_usage`, `credit_ledger`, `credit_grants`, `credit_debts`, `credit_action_prices`, `provider_calls`, `provider_call_rollups`, `shared_research_cache` (the tables exist since P04, migrations `0003` and `0005` to `0006`), including the `provider` columns on `ai_usage` and `runs` that are already created; the unique partial index `uq_runs_one_active_agent`; `idempotency_key` uniques; the repository calls to the credit functions of 03 section 5.13 (`reserve_credits`, `settle_credits`, `record_credit_debt`, `settle_credit_debt`, `ensure_free_monthly_grant`, `ensure_taster_grant`), which exist since P04.
- Accept: the models match the P04 tables; a second concurrent agent run for one account is refused at admission (409 `run_already_active`); ledger idempotency key unique; `reserve_credits` refuses an account with a credit debt.
- Touches: `apps/api/hermi/modules/ai/models.py`, `modules/credits/models.py`.
- Tests: concurrency test for the one-run-per-account admission check; duplicate idempotency key rejected.
- Done: DoD plus costs stored as micro-dollars.

#### WF-042 Feature flags and kill switches [M3, M]
- Depends on: WF-020.
- Description: models, repository and runtime for `feature_flags` and `kill_switches` (the tables exist since P04, `0012_admin_privacy`; the rows come from `0015_seed`) (`key`, `kind`, `enabled`, `rollout_pct`, `rules`, `variants`; switches carry `reason`, `engaged_by`, `expires_at`, `auto_rule`; admin-set switches must carry an expiry) and a runtime that evaluates flags (cached 5 seconds per process, invalidated by `NOTIFY`) and **fails closed** for paid calls if the tables cannot be read. Seed keys are in [03-database-schema.md](03-database-schema.md) section 11.5, plus the Phase 1 switches `import.ics`, `import.feed`, `import.paste`, `referrals` and `public_pages`, which are present in the `0015_seed` rows (not added by this ticket) and mirrored in `packages/shared/src/flags.ts`. `serpapi_live_fares` defaults off, and `setting_ai_global_daily_usd` is 150.
- Accept: flipping `ai.all` blocks AI calls within 5 seconds; engaging or clearing a switch writes `audit_log`; unreadable table blocks paid calls; each new switch blocks only its feature.
- Touches: `apps/api/hermi/modules/admin/flags.py`, `packages/shared/src/flags.ts`.
- Tests: evaluation rules (percent, tier, platform), fail-closed test, audit test.
- Done: DoD plus a practice drill written in `docs/runbooks/kill-switches.md`.

#### WF-043 AI metering and price constants [M3, M]
- Depends on: WF-041.
- Description: a versioned price constant in `ai/pricing.py` (06 section 6.1; not a database table) holding the model prices (Claude Haiku 4.5 `claude-haiku-4-5`, Claude Sonnet 5.5 `claude-sonnet-5-5`, web search per use) and a provider-neutral metering wrapper (it records `provider` on `ai_usage` and `runs`) that converts `response.usage` (input, output, cache read and write, web searches) into micro-dollars and writes an `ai_usage` row in the same transaction as the run event. Spec: [06-ai-agents-spec.md](06-ai-agents-spec.md).
- Accept: cost matches a hand calculation for 5 sample responses; Batch calls are halved on tokens; `provider_calls` records SerpApi and Geoapify spend with account and trip.
- Touches: `apps/api/hermi/modules/ai/metering.py`, `modules/ai/pricing.py`.
- Tests: table-driven cost tests, rollback test (no usage row if the event insert fails).
- Done: DoD plus price table never edited in place.

#### WF-044 Credit ledger service [M3, L]
- Depends on: WF-041.
- Description: reserve, settle, refund, expire and adjust operations on `credit_ledger` with `credit_grants`; spend order (allowance, pass credits, purchased credits oldest first); `SELECT ... FOR UPDATE` on the balance; lazy monthly grants (Free 12, Plus 60); Trip Pass credits are a trip pool; the one-time lifetime taster grant for one deep agent run, which draws its own grant; the API-callable credit functions check `p_user = app_user_id()`; `credit_ledger` is append-only; `release_stale_reservations` runs as a job; purchased credits expire after 12 months. Action prices: `explain` 1, `live_search` 1, `draft_day` 1, `draft_trip` 4, `research` 8 (1 from cache), `agent_run` 40 (8 from cache).
- Accept: parallel reservations never overspend; a failed or empty action is refunded; a stopped agent run is billed pro rata with an 8 credit minimum; negative balance after a refund blocks new actions; the taster is granted once per account; a function called with another user's `p_user` is refused; an update or delete on `credit_ledger` fails.
- Touches: `apps/api/hermi/modules/credits/`, `packages/shared/src/credits.ts`.
- Tests: committed multi-connection concurrency test with 20 parallel reservations; every ledger `kind`; expiry; spend order; taster once.
- Done: DoD plus balance shown from the ledger, never cached without a version.

#### WF-045 Spend ceilings and budget service [M3, L]
- Depends on: WF-044.
- Description: per-account monthly and daily provider-spend ceilings (Free $0.25 and $0.05 plus the one-time taster, Plus $2.25 and $0.40, Trip Pass $1.80 and $0.40), reserve-then-settle in one transaction with the job enqueue, the agent-run admission rule (month headroom of $0.80 even above the daily budget), counted under the lock from open reservations' hard stops over the calendar month, with the Trip Pass named as payer when it pays, and cached data still working when a ceiling is hit.
- Accept: a ceiling stops paid work but never cached reads; a run is admitted with $0.80 monthly headroom even if the day is exhausted, and then blocks other paid actions that day; ledger unreadable means refuse.
- Touches: `apps/api/hermi/modules/credits/budget.py`.
- Tests: boundary tests per tier, admission rule, a parallel admission test, fail-closed test.
- Done: DoD plus ceilings read from settings (changeable through [08-admin-control-center.md](08-admin-control-center.md)).

#### WF-046 Job queue and worker lanes [M3, L]
- Depends on: WF-041.
- Description: Procrastinate on Postgres with lanes `api`, `ai`, `notify`, `batch`; per-account concurrency caps (Free 2, Plus 4), fair claim by least recently served account, retries with backoff and jitter, dead-letter state, stale-heartbeat reaper, graceful SIGTERM; `runs` remains the user-visible record. Sub-steps queue and fairness register the jobs `release_stale_reservations`, `maintain_partitions` and `purge_trash` (the other jobs of 02 section 5.1 belong to the tickets that own them: `scan_due_routes` to WF-051, `retention_sweep` to WF-092, the reminders and digest to WF-047 and WF-051); local concurrency is 4, 2, 4 and 1 for the lanes `api`, `ai`, `notify` and `batch`, and `claude_cli` jobs run only on lane `ai` with concurrency 1 or 2.
- Accept: a job enqueued in the same transaction as its budget reservation; 2 workers never run a job twice; a killed worker's job is requeued; a busy account cannot starve others; WF-046 registers exactly these three jobs.
- Touches: `apps/api/hermi/jobs.py`, `apps/worker/hermi_worker/app.py`, `apps/worker/hermi_worker/jobs/`.
- Tests: two-worker test, reaper test, fairness test, retry classification test.
- Done: DoD plus queue depth and oldest job age exposed to health endpoints.

#### WF-131 AI provider seam [M3, L]
- Depends on: WF-005, WF-006, WF-041, WF-043, WF-046.
- Description: `apps/api/hermi/providers/ai/` holds the `AiProvider` protocol (`single_call`, `agent_run`) and three backends: `anthropic_api` (the Messages API client with tools and server tools; the production path), `claude_cli` (development only; the recipe in 06 section 2.7) and `fake` (recorded Messages responses that replay `server_tool_use`, `pause_turn` and `refusal`, plus a fake `claude` for CLI tests). `modules/ai/client.py` becomes a facade over a factory that reads `AI_PROVIDER`. Metering is provider-neutral and records `ai_usage.provider` and `runs.provider`. Port and adapt from the Trip Planner repo: `services/claude_cli.py` (`STRIPPED_ENV`, `find_claude`, `auth_status`, `NO_WINDOW`), `worker/agents/runner.py` (Watchdog, StderrDrain, stdin writer, `psutil` `kill_tree`, `guard_problem`, `explain_failure`), `worker/agents/stream.py`, the `agent_ingest.py` checks, `tests/fake_claude.py` and `worker/agents/smoke.py` (it becomes `hermi ai-smoke`). Do not port `agent_bridge/`. Guard: config allows `claude_cli` only when `ENVIRONMENT=local`, the server is bound to loopback, and `AUTH_MODE=dev` or the user is in `AI_CLI_ALLOWED_EMAILS`; the factory re-checks at call time; `/health/ready` reports the provider; `infra/render/render.yaml` pins `anthropic_api`.
- Accept: each AI feature of 06 runs through the seam on `fake`; `claude_cli` runs only under the guard; the CLI command has the flags of 06 section 2.7, the stripped environment and the init-event assertions; search and fetch caps, the 8 minute watchdog and cancel (tree kill) work against a fake `claude`; a CLI run's cost is `total_cost_usd` times 1e6 and is notional; `hermi ai-smoke` makes one no-tools and one capped web-tool call.
- Touches: `apps/api/hermi/providers/ai/`, `apps/api/hermi/modules/ai/client.py`, `apps/api/hermi/config.py`, `apps/api/hermi/cli.py`, `apps/api/tests/ai/`, `infra/render/render.yaml`, `knowledge/ai-provider-claude-cli.md`.
- Tests: a matrix test (environment, provider, auth mode, user allowed) for the guard; the factory re-check; a stripped-environment test (no `ANTHROPIC_API_KEY`, no `CLAUDE_CODE_*`, no `CLAUDECODE`); stream counter, watchdog and cancel tests; `fake` replay tests; a test that `render.yaml` pins `anthropic_api`.
- Done: DoD plus `hermi ai-smoke` documented in `knowledge/ai-provider-claude-cli.md`.

#### WF-047 Notification service and email [M3, M]
- Depends on: WF-046.
- Description: a `notify` lane service with preferences by type, quiet hours, per-trip mute, unique keys per user and alert, and Resend email templates for invites, price drops, booked-fare drops, run results, pre-trip reminders and deletion confirmation, plus unsubscribe handling. Jobs: the 7-day pre-departure reminder, the hourly activity digest and the trial-ending reminder (WF-051 wires the trial-ending trigger), each deduplicated per user and trip. Delivery follows `EMAIL_BACKEND` (`console`, `file`, `resend`). Push delivery is added in WF-086.
- Accept: a retried job never sends twice; each `EMAIL_BACKEND` value delivers as named; quiet hours defer; marketing needs opt-in.
- Touches: `apps/api/hermi/modules/notifications/`, `apps/worker/hermi_worker/jobs/send_email.py`.
- Tests: dedupe test, quiet hours test, preference test.
- Done: DoD.

#### WF-048 Claude client and single-call features [M3, M]
- Depends on: WF-043, WF-044, WF-131.
- Description: the Claude client is the facade over the provider seam (WF-131); the Messages API path has a prompt caching layout (tools, system, task, volatile tail), model allowlist, `max_tokens` per feature, and the single-call actions `explain` (Haiku), `packing_list` (Haiku, 1 credit in the `explain` price class, `POST /trips/{id}/ai/packing-list`, personal data redacted before the call), `draft_day` and `draft_trip` (Sonnet) with schema-validated output and source links. The `booking_import` action is built in WF-073.
- Accept: each action reserves, calls, meters, settles; outputs fail validation closed; AI output is labeled as a suggestion; the kill switch blocks calls.
- Touches: `apps/api/hermi/modules/ai/client.py`, `modules/ai/features/`.
- Tests: recorded-response tests with a fake client; hard-stop tests ($0.01, $0.03, $0.10); kill switch tests (`ai.all`, `ai.explain`, `ai.packing`, `ai.draft`); packing list sends placeholders, never names.
- Done: DoD plus prompt cache read ratio logged.

#### WF-049 Agent loop [M3, L]
- Depends on: WF-048, WF-045, WF-131.
- Description: the multi-turn agent (sub-steps loop and ingest) on the Messages API with server web search and fetch tools and in-process client tools `submit_flight_quotes`, `add_note`, `finish_run`. Caps: 20 turns, 10 searches, 10 fetches, `medium` effort, 8 minutes, $0.80 hard stop, one run at a time. Keep evidence rules (fares must be seen on a page during the run) and blocked domains Airbnb, Vrbo and Booking.com enforced in the fetch tool. Port the prompts from the old `agent_ingest.py` rules. The loop runs on `anthropic_api`; on `claude_cli` the stream counters enforce the caps. Manual fare hunt and deep research only; scheduled agent runs are not in Phase 1.
- Accept: a run stops at each cap and keeps saved work, marked `partial`; a fare without page evidence is rejected; blocked domains never fetched; prompt-injection test pages cannot write outside the account; every saved note carries a source URL.
- Touches: `apps/worker/hermi_worker/agents/` (`AgentLoop`, tools, prompts), `apps/api/hermi/modules/ai/ingest.py`, `modules/ai/context.py`, `apps/worker/hermi_worker/jobs/run_agent.py`.
- Tests: fake-tool loop tests for every cap; evidence tests; blocked-domain tests; injection fixtures.
- Done: DoD plus a manual staging run under $0.80 recorded.

#### WF-050 Research action and shared cache [M3, M]
- Depends on: WF-049.
- Description: the `research` action (5 searches, 8 fetches, $0.16) with `shared_research_cache` keyed by destination, rounded window, topic and prompt version; single-flight advisory lock; hits cost 1 credit, cold requests 8; poisoning defenses (validators, instruction-like text classifier, report flag sets `flagged`); jobs with free-text instructions bypass the cache. `research` uses the provider seam (WF-131); the CLI path validates the final JSON with the ported ingest checks.
- Accept: 50 concurrent requests for one key cause one model run; no user text enters a shared prompt; flagged entries are not served.
- Touches: `apps/api/hermi/modules/ai/research.py`, `modules/ai/cache.py`.
- Tests: single-flight test, bypass test, flagged entry test, credit pricing test.
- Done: DoD plus hit rate computed from `ai_usage.cache_hit`.

#### WF-051 Scheduler and price-check jobs [M3, M]
- Depends on: WF-046, WF-031.
- Description: one leader (advisory lock) scans `flight_routes.next_check_at` every 30 to 60 seconds with `FOR UPDATE SKIP LOCKED` (the `scan_due_routes` job), enqueues due jobs with a stable per-route jitter, advances the slot; jobs `refresh_cached_fares` (every 6 hours for routes with alerts), `check_fare_route` (live routes daily within 120 days of departure, within tier limits) and `evaluate_price_alerts` (notify lane). It only schedules API price checks; no agent job is ever scheduled in Phase 1. It also schedules the 7-day pre-departure reminder, the hourly activity digest and the trial-ending reminder as jobs, each deduplicated per user and trip.
- Accept: two schedulers never double-fire; an outage fires one check, not twelve; no agent job is ever scheduled; an alert triggers once per drop and hands a request to the notify lane.
- Touches: `apps/worker/hermi_worker/scheduler.py`, `apps/worker/hermi_worker/jobs/scan_due_routes.py`, `jobs/evaluate_price_alerts.py`.
- Tests: two-leader test, jitter stability test, misfire test, idempotent notification test.
- Done: DoD plus scheduler heartbeat exposed.

#### WF-052 Live flight provider and search cache [M3, L]
- Depends on: WF-030, WF-045, WF-042.
- Description: a provider interface with SerpApi behind the `serpapi_live_fares` flag (default off; `setting_ai_global_daily_usd` is 150), a canonical search key and shared `provider_calls` result cache (6 hours for fares), single-flight, per-account ceiling checks, `live_search` costs 1 credit, a cached result under 6 hours old is free and says so.
- Accept: 10 users searching one route cause one provider call; the flag defaults off and off hides live search; provider kill switch works; no Airbnb, Vrbo or Booking.com fetches. Rental search sits behind the same flag.
- Touches: `apps/api/hermi/providers/serpapi.py`, `apps/api/hermi/modules/flights/` (search cache), `apps/api/hermi/modules/lodging/` (rental search).
- Tests: dedupe test, flag test, ceiling test, provider error test.
- Done: DoD.

#### WF-053 Agent runs API, screen and taster [M3, M]
- Depends on: WF-049, WF-014, WF-130.
- Description: start, stream events (server-sent events), cancel and list runs; one at a time per account; credit preview before start; results saved as notes and fares with source links; the one-time lifetime taster ("Try a fare hunt, free") and the post-taster card. Cancel kills the CLI process tree; the watchdog stops a run at 8 minutes.
- Accept: a second start while one runs returns a clear error; cancel stops at the next checkpoint and settles pro rata; events show sources; the taster works once and then shows the credit price.
- Touches: `apps/api/hermi/modules/ai/router.py`, `apps/web/src/routes/agents/`.
- Kit: 05 6.16, 6.17; screens/09-agent-run.html
- Tests: API tests, SSE test, cancel test, taster test.
- Done: DoD.

#### WF-054 AI consent, labels and reports [M3, S]
- Depends on: WF-053.
- Description: first-use consent ("Your trip details and questions are sent to Anthropic to generate suggestions") stored in `consents` with timestamp, an AI off toggle, "AI suggestion, check details before booking" labels, thumbs up or down that doubles as a content report.
- Accept: no AI call without consent; toggle off blocks AI; reports create moderation items (queue screen in WF-106).
- Touches: `apps/web/src/components/ai/`, `apps/api/hermi/modules/auth/` (consents).
- Kit: 05 6.15, 4.21; none, follow DL section 11
- Tests: consent gating test, report creation test.
- Done: DoD.

#### WF-055 Evidence labels [M3, M]
- Depends on: WF-035, WF-049.
- Description: a shared component that shows "Found on [site], checked [date]" on every AI-found fact (fares, notes, research items, imported confirmations show "From your pasted text" instead), opens the source, shows age for fares, and offers "Price was different" on agent-found fares (feeds the eval set). The server rejects any AI-saved fact without `source_url` and `checked_at` (the `checked_at` column on notes and items is added here; the 14-day freshness flag and the recheck are WF-120).
- Accept: no AI-found fact renders without a label; a fact without a source is rejected at ingest; labels are readable (body-size text, contrast tokens) and work with VoiceOver.
- Touches: `apps/web/src/components/evidence/`, `apps/api/hermi/modules/ai/ingest.py`, `apps/api/hermi/modules/trips/` (notes).
- Kit: 05 6.18, 4.21; none, follow DL section 11
- Tests: component snapshot tests, ingest rejection test, a test that scans AI-saved rows for missing sources.
- Done: DoD.

#### WF-056 Global breakers and usage reconciliation [M3, M]
- Depends on: WF-042, WF-045.
- Description: automatic breakers (80 percent of daily Anthropic budget turns off Free AI, 95 percent stops all but paid, 90 percent of SerpApi quota narrows live checks, provider error-rate trips), a daily job that pulls the Anthropic usage and cost admin API (`ANTHROPIC_ADMIN_API_KEY`) and compares it with `ai_usage` (alert above 3 percent); it is skipped for `claude_cli` and logs and skips when the key is missing, and the alert rules in [08-admin-control-center.md](08-admin-control-center.md) section 10.
- Accept: a simulated spend surge trips the right breaker and pages; reconciliation gap alert fires in a drill; breakers are logged to `audit_log` as `system`.
- Touches: `apps/api/hermi/modules/ai/breakers.py`, `apps/worker/hermi_worker/jobs/reconcile_anthropic_usage.py`.
- Tests: threshold tests, half-open probe test, reconciliation diff test.
- Done: DoD.

#### WF-057 Evals and run-cost measurement [M3, M]
- Depends on: WF-049.
- Description: an eval harness for agent and research quality (source present, fares verified, refusals, injection resistance) and a script that reports real cost per run over a window. Run 50 real agent runs on staging across at least 10 routes to measure cost; this is the Month 3 exit number and the live run is owner-pending. `shortcut:` CLI numbers are provisional, certified numbers need `anthropic_api`.
- Accept: `npm run evals` runs against fixtures with a fake client and live only with `EVALS_LIVE=1` and `--max-usd` on a low-limit key (one path, `npm run evals`, with `--provider`); certified only on `anthropic_api`; cost report prints mean, p95 and count of runs; the 50-run report shows the p95 under $0.80.
- Touches: `apps/worker/tests/evals/`, `infra/scripts/run_cost_report.py`.
- Tests: the harness has its own self-test with known outputs.
- Done: DoD plus eval results and the 50-run report saved in `docs/evals/`.

#### WF-058 Admin foundation [M3, L]
- Depends on: WF-020, WF-013, WF-130.
- Description: `admin.hermi.world` route group (excluded from the iOS build), `/v1/admin` router, Cloudflare Access JWT check (`ADMIN_AUTH_MODE=cf_access|dev`, `CF_ACCESS_TEAM_DOMAIN`, `CF_ACCESS_AUD`, a fake-Access signer for local and ci, the first admin through `hermi admin-grant <email>`; 08 is the authority), `admin_users`, WebAuthn and TOTP 2FA with step-up, roles (`support`, `ops`, `finance`, `owner`) and the permission table, admin DB role, rate limits, strict CSP. Spec: [08-admin-control-center.md](08-admin-control-center.md) sections 2, 3 and 9.
- Accept: customer tokens rejected on admin and the reverse; unknown identities get 403; permission matrix test passes; disabled admin loses access in 60 seconds.
- Touches: `apps/api/hermi/modules/admin/`, `apps/web/src/routes/admin/`, `infra/cloudflare/` (access policy or docs).
- Kit: 08 section 5 and the 08 6.1 shell (sign-in in 08 section 2.2); none, follow DL section 11
- Tests: role by route matrix test, step-up tests, session expiry tests.
- Done: DoD plus Cloudflare Access configured and documented.

#### WF-059 Audit log service and screen [M3, M]
- Depends on: WF-058.
- Description: `audit_log` writer used in the same transaction as every admin write, redaction, `denied` rows, nightly hash chain to R2 object lock, and the audit viewer.
- Accept: each admin write yields one row with before and after and reason; update and delete rejected; viewer filters work.
- Touches: `apps/api/hermi/modules/admin/audit.py`, `apps/web/src/routes/admin/audit/`.
- Kit: 08 section 5 and 08 section 4 (the audit viewer has no 6.x screen); none, follow DL section 11
- Tests: atomicity test, redaction test.
- Done: DoD.

#### WF-060 Admin kill switches and breakers [M3, M]
- Depends on: WF-058, WF-042, WF-056.
- Description: the switches screen with state, expiry and effect counts, confirmation dialog with typed key and step-up, mandatory expiry, auto-expiry notification, breaker history.
- Accept: every manual off has an expiry; `ai.all` off blocks AI within 5 seconds; expiry writes a `system` audit row; drill recorded.
- Touches: `apps/api/hermi/modules/admin/killswitches.py`, `apps/web/src/routes/admin/killswitches/`.
- Kit: 08 section 5 and 08 6.5; none, follow DL section 11
- Tests: expiry and fail-closed tests, UI confirmation tests.
- Done: DoD plus a timed drill (under 30 seconds to stop AI).

#### WF-061 Admin credits and AI spend [M3, L]
- Depends on: WF-058, WF-043, WF-045.
- Description: spend by feature, tier and model, top spenders, ceiling hits, runaway detection, live runs, cancel a run, reconciliation gap, cache hit rates.
- Accept: a seeded runaway appears in the list; cancel settles pro rata; numbers match `ai_usage`.
- Touches: `apps/api/hermi/modules/admin/ai_spend.py`, `apps/web/src/routes/admin/ai-spend/`.
- Kit: 08 section 5 and 08 6.4; none, follow DL section 11
- Tests: detection rule tests, cancel test.
- Done: DoD plus the Month 3 gate review recorded.

#### WF-062 Guest mode and claim [M3, M]
- Depends on: WF-018, WF-019, WF-132, WF-130.
- Description: a guest can create and edit a local trip on the device without an account (`guest_trip_created`); the "Save your trip" sheet appears when the guest tries to invite, sync, use AI, export or buy; on sign-up the local trips are claimed into the new account exactly once (`guest_claimed`). Guest data is local-only: `POST /me/claim` carries the trip JSON and a client-generated claim id, and there is no `is_guest` flag. The guest attestation endpoints and the `guest_allowances` table (F-ACC-2) back the one guest AI route. Guests cannot invite. Guest AI uses a device-attested allowance. On sign-up the user chooses "Merge" or "Keep separate" with counts shown, and over-limit claims are archived.
- Accept: guest creates a trip with no network account; claim moves trips to the new user once and is idempotent; guest requests never reach tenant tables without a claim; nothing is stored server side for an unclaimed guest; a repeated claim with the same claim id returns the first result; `POST /guest/ai/draft-day` works only with a valid App Attest assertion and draws from `guest_allowances`.
- Touches: `apps/web/src/features/guest/`, `apps/api/hermi/modules/auth/` (claim), `apps/api/hermi/modules/trips/`.
- Kit: 05 6.2; none, follow DL section 11
- Tests: claim idempotency test, guest draft-day assertion and allowance test, guest restriction tests, Playwright guest flow.
- Done: DoD.

#### WF-120 Evidence freshness and one-tap recheck [M3, M]
- Depends on: WF-055, WF-048, WF-044.
- Description: adds the "May be out of date" flag and the recheck. The evidence label (WF-055) shows an amber chip when `checked_at` is more than 14 days old (computed at read time, `stale` and `stale_after_days` on `Evidence` and `Note`, 04 section 5.14), nothing hidden or removed. `POST /notes/{id}/recheck` and `POST /items/{id}/recheck` run the `recheck` feature (06 section 5.12): Haiku 4.5, one fetch of the stored source URL through the SSRF-safe fetcher (not CLI web tools), strict JSON result (`confirmed`, `changed`, `not_shown`, `unreachable`), code-grounded `current_value`, 1 credit in the `explain` price class (run kind `recheck`, kill switch `ai.recheck`, flag `evidence_recheck`), refunded when unreachable. `confirmed` moves `checked_at` to today; `changed` and `not_shown` change nothing and offer "Save as a note". Editors and owners see the button at any age, viewers the chip only. Fares are not rechecked.
- Accept: a 15-day-old finding shows the chip and a 13-day-old one does not; a recheck of an unchanged page moves the date and charges 1 credit; an unreachable page refunds; a changed page leaves the old text and shows the new value with its source; a blocked host is never fetched; no search is ever run.
- Touches: `apps/api/hermi/modules/ai/features/recheck.py`, `apps/api/hermi/modules/trips/` (notes evidence), `apps/web/src/components/evidence/`.
- Kit: 05 6.39, 6.18; none, follow DL section 11
- Tests: freshness boundary test (14 days), grounding test for `current_value`, refund test, role test, injection fixture on a fetched page, blocked-host test, component test for the chip and result sheet.
- Done: DoD plus the recheck eval set (60 page pairs, 06 section 10) committed in `docs/evals/`.

#### WF-132 AI sheet and action screens [M3, L]
- Depends on: WF-044, WF-048, WF-050, WF-053, WF-054, WF-120, WF-130.
- Description: the AI sheet (05 section 6.15, mockup 08): entry from fares, places, plan items and the trip header; Explain, Draft day and Draft trip (a preview, then "Accept all" or pick items), Research and the packing list, each with its credit chip showing which pool pays (your credits or the trip's Trip Pass pool); the consent gate of WF-054; the credits balance and history (05 section 6.26) and the out-of-credits paywall moments of 07 section 6.2. It carries the acceptance criteria of F-AI-1, F-AI-2, F-AI-3 and F-AI-9: a repeat of the same question within 6 hours is free, every drafted place is grounded in place data, and at 0 credits day one of a draft is shown blurred behind the paywall.
- Accept: each action works end to end on `fake` with its states (loading, empty, error, offline, limit); credit chips show the right price and pool; the free repeat within 6 hours charges nothing; a draft at 0 credits shows the blurred day one and the `out_of_credits_draft` paywall; the balance and history match the ledger.
- Touches: `apps/web/src/routes/ai/`, `apps/web/src/components/ai/`, `apps/web/e2e/ai/`.
- Kit: 05 6.15, 6.26, 4.11; screens/08-ai-actions.html
- Tests: component tests for every state; one Playwright test per action (explain, draft day, draft trip, research, packing list, credits history); the free-repeat and blurred-day tests. Smoke flow 6 (10 section 1.6): the AI consent screen appears on first use (WF-054 owns the consent gating), declining leaves the app usable, accepting runs `explain` and shows 1 credit spent. Smoke flow 23 (10 section 1.6, 01 sections 3.6 and 3.7): draft a day and a trip, run research and an agent with its live log (fake Anthropic).
- Done: DoD plus the DL section 11 checklist run.

### Month 4: money, imports, admin essentials

#### WF-063 RevenueCat webhook and reconcile [M4, L]
- Depends on: WF-022, WF-023, WF-044.
- Description: `POST /v1/webhooks/revenuecat` (sub-steps webhook and reconcile; the provider list equals the 03 CHECK: `revenuecat`, `travelpayouts`, `viator`, `stay22`, `resend`, `supabase`, no `apple`; secret header compared in constant time, idempotent on event id in `webhook_events`), `entitlements` and `subscriptions` updates for Plus monthly and annual (7-day trial on annual only), `POST /v1/purchases/sync`, nightly reconcile against the RevenueCat REST API (`reconcile_entitlements`), `app_user_id` linked to the account UUID; grants cross-checked by a REST fetch.
- Accept: a provider outside the 03 CHECK list is refused; replayed webhooks change nothing; grace, billing retry, expiry and refund handled; reconcile flags mismatches; sync unlocks instantly before the webhook arrives.
- Touches: `apps/api/hermi/modules/billing/revenuecat.py`, `apps/worker/hermi_worker/jobs/reconcile_entitlements.py`.
- Tests: fixture event suite (every event type in 10 section 1.4), replay test, out-of-order test.
- Done: DoD.

#### WF-064 Credit grants and refund reversal [M4, M]
- Depends on: WF-063, WF-044.
- Description: monthly allowance grants on renewal (Plus, 60) or calendar month (Free, lazy), pack grants `credits_50`, `credits_150`, `credits_400` keyed by store transaction id (12 month expiry, spent last), `REFUND` reversal allowing negative balance; jobs `grant_monthly_credits` and `expire_credits`.
- Accept: a transaction id grants exactly once; a refund reverses the grant and blocks AI until positive; ledger history shows each step.
- Touches: `apps/api/hermi/modules/billing/grants.py`, `apps/worker/hermi_worker/jobs/`.
- Tests: duplicate event test, refund test, expiry test.
- Done: DoD.

#### WF-065 Trip Pass binding [M4, M]
- Depends on: WF-063.
- Description: `trip_pass` non-renewing subscription handling, buy then pick a trip, transaction recorded in `store_transactions` (`kind = 'pass'`) and, once a trip is known, in `trip_passes`, 90 days from binding, an unapplied pass waiting in Settings (`GET /v1/me/passes`), `POST /v1/me/passes/{pass_id}/bind` and `POST /v1/me/passes/{pass_id}/move` (once); limits (2 live routes, 60 live checks, 40 credits, up to 6 collaborators); job `expire_trip_passes`. Binding verifies the buyer owns the trip; a paid second pass that cannot bind grants its credits, opens a support ticket and sends the refund to support.
- Accept: a pass binds to exactly one trip and only for the trip's owner; a paid second pass that cannot bind grants 40 credits, opens a support ticket and returns `bound: false`; expiry handled on the server; pass shown in trip settings; a second apply attempt is refused.
- Touches: `apps/api/hermi/modules/billing/passes.py`, `apps/web/src/routes/trip-settings/`.
- Kit: 05 6.26, 6.27; none, follow DL section 11
- Tests: bind, expire, move-once tests.
- Done: DoD.

#### WF-066 Paywall logic and screens [M4, M]
- Depends on: WF-023, WF-018, WF-132, WF-130.
- Description: server-decided paywall moments (Trip Pass first when a trip is within 120 days, annual Plus first with 2 or more active trips, credit packs when credits run out, `invite` when a Free owner invites a second person, `track_live` for live routes), `GET /paywall`, purchase screens with price, period and trial terms, Terms and Privacy links, Restore, and a visible free path. Purchases happen only in the iOS app; on the web the same sheet returns `purchasable: false` and shows what the upgrade gives, the free path and "Upgrade in the iOS app" with an App Store link, and no price, purchase button or checkout (there are no web purchases in Phase 1). The paywall legal row links to "How billing works" (WF-124). Adds the trigger `out_of_credits_verify` for plan checks and rechecks. Paywall reason codes follow 04 section 2.2 and 07 section 6.2 (`third_trip` is `trip_limit`; `second_route`, `track_live` and `alert_limit` are `live_routes`; `invite` is `sharing`; the four `out_of_credits_*` triggers are `credits`). Anti-patterns avoided: no fake urgency. Builds a paywall screen for every 07 section 6.2 trigger; the Account and Subscription screens (05 6.25, 6.26) are shared with WF-094 and WF-132.
- Accept: the reason code returned by the server (the 402 `paywall` hint or `GET /paywall`) drives the screen and matches the 07 section 6.2 mapping; Plus annual is shown first with the trial only on annual; the close control is always visible; web shows "Upgrade in the iOS app" and no price or purchase control.
- Touches: `apps/web/src/routes/paywall/`, `apps/api/hermi/modules/billing/router.py`.
- Kit: 05 4.14, 6.27, 8; screens/07-paywall.html
- Tests: decision table tests, component tests. Smoke flow 17 (10 section 1.6): on web the paywall says "Upgrade in the iOS app" with no price or purchase button (the public pages `/how-we-earn` and `/billing` load without sign-in and pass axe: WF-124 Tests).
- Done: DoD.

#### WF-067 Outbound API and redirect [M4, M]
- Depends on: WF-022, WF-014.
- Description: `POST /v1/outbound` (checks trip access, picks program by flags, geography and cell, inserts `link_clicks`, returns `/go/{click_id}`) and `GET /go/{click_id}` (fresh under 10 minutes, single use, 302 from a stored template, `Cache-Control: no-store`, `Referrer-Policy: no-referrer`), with the outcomes of 04 section 5.21 and 07 section 6.2: an expired or used id or an off kill switch is a 302 to the plain non-affiliate destination, an unknown id is a 404 with an empty body, and `/go` carries no paywall reason code. No open redirects; user id, trip id and email never in URLs.
- Accept: expired or reused ids and an off kill switch 302 to the plain destination, unknown ids 404 with an empty body; no `url=` parameter path exists; repeat clicks within 30 seconds deduped; 60 an hour rate limit.
- Touches: `apps/api/hermi/modules/affiliate/router.py`, `modules/affiliate/service.py`.
- Tests: redirect tests, open-redirect attack tests, dedupe test. Smoke flow 9 (10 section 1.6): a partner card shows the disclosure, `/go/{click_id}` answers 302 to the template host (intercepted).
- Done: DoD.

#### WF-068 Link builders, disclosure and placements [M4, L]
- Depends on: WF-067, WF-130.
- Description: link template builders for Travelpayouts, Viator and Stay22; a shared `PartnerButton` component that always renders "We earn a commission if you book here.", an "Ad" label on UK and EU storefronts, sort explanations on lists, a "Hide booking links" setting; placements on lodging, flights, things to do, cars and eSIM cards; Airbnb listings get plain links only. Public pages carry no partner buttons in Phase 1.
- Accept: a component test fails if a partner button renders without disclosure; no list sorts by commission (a test checks ordering code); all placements go through `/go`.
- Touches: `apps/web/src/components/partner-button.tsx`, `apps/api/hermi/modules/affiliate/`.
- Kit: 05 4.13; none, follow DL section 11
- Tests: disclosure snapshot tests, ordering test, country label test.
- Done: DoD plus placement map in `docs/affiliate-placements.md`.

#### WF-069 Conversion import [M4, M]
- Depends on: WF-067, WF-046.
- Description: nightly jobs that pull Travelpayouts, Viator and Stay22 booking statistics and payments, idempotent upsert on program and network transaction id with status history, match by sub-id, and track the unmatched share.
- Accept: a rerun changes nothing; status transitions (pending, approved, rejected, paid) recorded; unmatched share computed; failure alerts.
- Touches: `apps/worker/hermi_worker/jobs/import_affiliate_conversions.py`.
- Tests: fixture payloads, idempotency test, unmatched share test.
- Done: DoD.

#### WF-070 Checklist "Before you go" [M4, M]
- Depends on: WF-021, WF-068.
- Description: `checklist_items` by destination: official visa and entry links first, then labeled partner items (eSIM, insurance referral, transfers, bookings). At least half of the items are unmonetized; insurance uses insurer-approved copy only; the AI gives no insurance, visa or legal advice. The after-trip flight compensation prompt is Phase 2.
- Accept: checklist templates generated by destination; at least half of the items have no partner link; each item can be marked "Not needed" and custom items can be added; copy reviewed against [08-affiliate-revenue.md](../context/business-plan/08-affiliate-revenue.md) rules.
- Touches: `apps/api/hermi/modules/trips/` (checklist), `apps/web/src/routes/checklist/`.
- Kit: 05 6.20; none, follow DL section 11
- Tests: template tests (ratio of monetized items), copy lint for forbidden advice phrases. Smoke flow 24 (10 section 1.6, 01 section 3.9): after a stay is Booked the checklist shows on the Overview; one item done and one not needed persist after reload.
- Done: DoD.

#### WF-071 Switching import: ICS file [M4, M]
- Depends on: WF-032, WF-014, WF-019.
- Description: import a trip from a calendar file (TripIt, Tripsy or Google Calendar export; the optional `origin` records which entry was used). `POST /imports/ics-file` accepts one `.ics` file under the single limits table of 04 section 5.26 (2 MB, 500 events, 20 previews a day), status `applied` after confirm, and the raw file is never stored; a strict parser in a resource-limited sandbox set by `IMPORT_SANDBOX=strict|timeout_only` (CPU 5 seconds, memory 256 MB; on win32 a timeout plus a `psutil` memory kill) reads `VEVENT`s, handles `VTIMEZONE`, floating times and all-day events, caps events at the table limit, ignores `ATTACH` and never fetches any URL it finds; events map to itinerary items, flights and stays with an `import` source; a preview screen ("We found 12 items") lets the user deselect before saving; duplicates are skipped by `UID`. Kill switch `import.all`.
- Accept: golden files from TripIt, Google Calendar and Apple Calendar import correctly; re-importing the same file adds nothing; malformed, oversized and hostile files fail with a clear message and never crash the worker; no network access during parsing.
- Touches: `apps/api/hermi/modules/trips/import_ics.py`, `apps/api/hermi/modules/itinerary/`, `apps/web/src/routes/import/`.
- Kit: 05 6.30; none, follow DL section 11
- Tests: golden files, dedupe test, property-based fuzzing of the parser (Hypothesis in CI, corpus committed), limits tests (size, event count, recurrence explosion), no-network test, a sandbox-mode test for `strict` and `timeout_only`.
- Done: DoD plus the fuzz corpus and regression files committed.

#### WF-072 Switching import: ICS feed [M4, L]
- Depends on: WF-071, WF-046, WF-034.
- Description: import from a calendar feed URL (TripIt iCal feed, Google Calendar secret address). The user pastes the URL (`webcal://` is rewritten to `https://`); a `fetch_ics_feed` job in the `api` lane fetches it once through the shared SSRF guard (public addresses only, pinned IP, at most 3 manual redirects, 3 second connect and 5 second total timeout, 2 MB cap counted after decompression, `text/calendar` only) and hands the body to the WF-071 parser and preview. The feed URL is a secret: it is never logged or sent to analytics, it is held (encrypted) only until the preview is confirmed or discarded, and it is kept after that only when the person turns on "Keep checking this calendar" (WF-123); otherwise the user repastes it to refresh. Airbnb, Vrbo and Booking.com hosts are refused. Kill switches `import.all` and, for polling, `import.polling`.
- Accept: the hostile URL table (loopback, link-local, private and mapped addresses, decimal and hex IPs, rebinding, redirect to private, loops, `file:` and `gopher:`, userinfo, non-standard ports, oversized and compressed bodies) is refused; the URL never appears in logs, Sentry, `provider_calls` or events; limit of 5 feed registrations a day (04 section 5.26); status `applied` after confirm and the raw body is never stored.
- Touches: `apps/api/hermi/providers/ics_feed.py`, `apps/api/hermi/security/ssrf.py`, `apps/worker/hermi_worker/jobs/fetch_ics_feed.py`, `apps/web/src/routes/import/`.
- Kit: 05 6.30; none, follow DL section 11
- Tests: SSRF table test with a fake resolver, redirect tests, gzip bomb test, log and Sentry scrub test, rate limit test, `IMPORT_SANDBOX` mode test.
- Done: DoD plus the threat model updated with the feed import.

#### WF-073 Switching import: pasted confirmations [M4, L]
- Depends on: WF-048, WF-071.
- Description: the `booking_import` action. The user pastes booking confirmation text (up to 12,000 characters, the single limits table of 04 section 5.26; the raw text is never stored, status `applied` after confirm); the server redacts personal data before any model call (names become "Traveler 1", emails, phone numbers, booking and confirmation codes, card-like and passport-like numbers, home addresses are removed; booking codes are re-attached locally from the original text, never taken from the model), Haiku extracts flights, stays and reservations as schema-validated items, each shown in a preview as "From your pasted text" (evidence label) before saving. 1 credit in the `explain` price class, refunded on an empty or failed extraction, AI consent required. Links inside pasted text are never fetched. Kill switch `ai.import`.
- Accept: the outbound model request contains none of the test PII; output that fails validation is discarded; instructions hidden in pasted text do not change behavior; a pasted Airbnb or Vrbo confirmation works without any fetch; the user confirms every item before it is saved.
- Touches: `apps/api/hermi/modules/ai/features/booking_import.py`, `apps/api/hermi/modules/trips/import_paste.py`, `apps/web/src/routes/import/`.
- Kit: 05 6.30; none, follow DL section 11
- Tests: a redaction corpus of 40 real-shaped confirmations asserting zero PII in the recorded request, extraction eval set (10 section 1.5), injection fixtures, refund test, consent test. Smoke flow 8 (10 section 1.6): paste a sample confirmation with the model faked, the preview shows "From your pasted text" labels, nothing is saved before confirming.
- Done: DoD plus the redaction corpus and eval results saved in `docs/evals/`.

#### WF-074 First-import Trip Pass reward [M4, M]
- Depends on: WF-065, WF-071.
- Description: the first qualifying import on a trip (calendar file, calendar feed or pasted confirmations) earns a free Trip Pass for that trip, once per account, with the same limits as a paid Trip Pass (WF-065) and 90 days from grant, recorded as a `trip_passes` row with `source = 'import_reward'` (no store transaction) and an idempotent 40-credit grant. Conditions (settled): at least 3 items saved from the import including a flight or a stay, a verified email, no active pass on that trip and no active Plus; `grant_import_reward()` in 03 section 5.9 enforces them. Google Maps and pasted-places imports and calendar change confirmations never qualify. Plus owners are thanked but get no reward. Nothing is granted for empty or duplicate imports, and an import that does not qualify does not consume the reward. The reward is applied on confirm, when the import reaches status `applied` (04 section 5.26).
- Accept: the reward is granted once per account and never twice for the same file or trip; junk imports under 3 items, imports with no flight or stay, unverified emails and Plus owners grant nothing and keep the reward available; the pass appears in trip settings as free; expiry works like a paid pass; admin can revoke it.
- Touches: `apps/api/hermi/modules/billing/passes.py`, `apps/api/hermi/modules/trips/` (import hook), `apps/web/src/routes/import/`.
- Kit: 05 6.30; none, follow DL section 11
- Tests: once-per-account test, idempotency test under concurrent imports, minimum item test, flight-or-stay test, verified-email test, Plus owner test, places-only import test, revoke test. Smoke flow 7 (10 section 1.6): import a sample TripIt `.ics`, the free Trip Pass banner appears once, importing the file again adds nothing.
- Done: DoD.

#### WF-075 Booked-fare drop alert [M4, M]
- Depends on: WF-031, WF-047, WF-051, WF-030.
- Description: on a chosen flight the user can add what they paid ("Mark as booked" plus price, stored as `chosen_flights.paid_minor` with `paid_currency`); the daily check reads the `booked_fare_drops` view, which matches airline, flight number and party size as well as route and dates, and applies the `setting_booked_fare_drop` thresholds times 100 (minor units); it compares current fares for the same route and dates and alerts when one is lower: "You paid $X, it is now $Y. Check the airline's change and credit rules." The copy never promises a refund or rebooking. The columns and the view exist since P04. Free accounts use cached fares (their one alert can be a booked-fare watch); Plus and Trip Pass follow live route limits. Settled thresholds: the fare must be at least 5 percent and at least $10 (converted) below what was paid, at most one alert per flight every 7 days, never a partner link; email now and push after WF-086. A booked fare with no check for 48 hours pauses the watch (stale pause) and says so. The "What did you pay?" prompt opens after "Yes, mark as booked" and after an imported flight is accepted, and the "Your booked fare" card shows on the chosen-flight and route cards (05 sections 6.10 and 6.32).
- Accept: a lower fare that clears both thresholds triggers exactly one alert and a second within 7 days triggers none; a drop under 5 percent or under $10, and an equal or higher fare, trigger none; the alert shows the fare's source and age; copy passes the no-advice lint; a flight marked as departed stops watching; a booked fare with no matching observation in 48 hours pauses with a stale message; the "What did you pay?" prompt and the "Your booked fare" card show, including for an imported flight.
- Touches: `apps/api/hermi/modules/flights/`, `apps/worker/hermi_worker/jobs/evaluate_price_alerts.py`, `apps/web/src/routes/flights/`.
- Kit: 05 6.32; none, follow DL section 11
- Tests: view matching test (airline, flight number, party), 48 hour stale pause test, prompt and card component tests, threshold tests (5 percent and $10 edges, times 100), 7-day repeat test, currency test, no-partner-link test, copy lint test.
- Done: DoD.

#### WF-076 Sandbox purchase harness [M4, M]
- Depends on: WF-063, WF-064, WF-065.
- Description: a throwaway iOS test app (StoreKit configuration plus the RevenueCat SDK, `app_user_id` set to `users.id`) used to prove every product end to end before the Capacitor shell exists: Plus monthly, Plus annual (trial), Trip Pass, credit packs, cancel, refund, restore. It is deleted after WF-084 ships the real purchase flow. Builds on a GitHub macOS runner (see knowledge/ios-builds-on-ci.md), with the device checks owner-pending; App Store Connect products and the sandbox tester must exist.
- Accept: each product purchased in the sandbox unlocks the right entitlement within seconds against staging; replaying the webhook grants nothing twice; results written to `docs/qa/purchase-harness.md`.
- Touches: `apps/ios/harness/` (temporary), `docs/qa/`.
- Kit: 05 8; none, follow DL section 11
- Tests: the scenario list itself.
- Done: DoD plus product metadata entered in App Store Connect.

#### WF-077 Admin users: read, search, reveal [M4, M]
- Depends on: WF-058, WF-059.
- Description: search by email hash, id and other keys, masked list, profile tabs, per-record reveal with reason and rate limit.
- Accept: no raw email or name in any list response; reveal audited; search never returns partial PII matches.
- Touches: `apps/api/hermi/modules/admin/users.py`, `apps/web/src/routes/admin/users/`.
- Kit: 08 section 5 and 08 6.2; none, follow DL section 11
- Tests: serializer masking scan test, reveal limit test.
- Done: DoD.

#### WF-078 Admin subscriptions, store transactions and webhook replay [M4, M]
- Depends on: WF-063, WF-058.
- Description: the subscriptions and store transactions screens, RevenueCat sync status, failed webhook list, dry-run replay, reconcile button, refund reversal visibility. Spec: [08](08-admin-control-center.md) section 6.3.
- Accept: a failed event can be replayed without double grants; mismatches listed.
- Touches: `apps/api/hermi/modules/admin/billing.py`, `apps/web/src/routes/admin/subscriptions/`.
- Kit: 08 section 5 and 08 6.3; none, follow DL section 11
- Tests: replay idempotency test, permission tests.
- Done: DoD.

#### WF-079 Admin overview and metric rollups [M4, L]
- Depends on: WF-058, WF-023.
- Description: rollup jobs every 5 minutes and the overview (MAU, DAU, signups, trials, conversions, MRR, revenue by stream, AI spend versus budget, affiliate clicks and EPC, import and referral counts, alerts, kill rule card), with stale-data indicators. Spec: [08](08-admin-control-center.md) section 6.1.
- Accept: each tile matches a hand query on seeded data; stale rollups warn; the kill rule numbers are correct; affiliate clicks and conversions appear (Month 4 exit).
- Touches: `apps/api/hermi/modules/admin/overview.py`, `apps/worker/hermi_worker/jobs/rollups.py`, `apps/web/src/routes/admin/overview/`.
- Kit: 08 section 5 and 08 6.1; none, follow DL section 11
- Tests: rollup tests with fixtures, tile rendering tests.
- Done: DoD plus the Month 4 gate review recorded.

#### WF-121 Import entries named for TripIt, Tripsy and Wanderlog, and pasted places [M4, M]
- Depends on: WF-071, WF-072, WF-073, WF-033.
- Description: the import screen lists entries named for TripIt, Tripsy, Wanderlog, Google Calendar and Google Maps (plain text, no logos), each opening the matching method with two or three steps for getting the data out of that app (05 section 6.30); `trip_imports.origin` records the entry (03 section 5.9) and the `origin` event property carries it. Adds the `places_text` source: `POST /imports/places` takes pasted place names (one per line, up to 20,000 characters and 200 places), matches each by place search (Geoapify, no AI, no credits) and returns candidates of kind `place` that import as ideas with no day; a single Google Maps list link returns `422 list_link_not_readable` (never opened) and the screen offers to keep the link as a note. The rival instructions are checked against each app's current help pages before merge and again before launch (2 non-ticket hours); where an app has no export the entry says so.
- Accept: each entry opens the right method; pasting Wanderlog or Maps place names gives a preview with matched places and "Not the right place"; a pasted Maps list link is never requested (no network call, asserted); a places-only import never triggers the first-import reward; the entry is stored and no other parsing changes; no third-party logos.
- Touches: `apps/api/hermi/modules/trips/import_places.py`, `apps/api/hermi/modules/places/`, `apps/web/src/routes/import/`.
- Kit: 05 6.30; none, follow DL section 11
- Tests: place-matching golden set (30 lists), no-network test for list links, reward exclusion test, origin analytics test, copy lint. Smoke flow 15 (10 section 1.6): the TripIt, Tripsy, Wanderlog and Google Maps entries each open the right method.
- Done: DoD plus the rival help-page check dated in `docs/import-sources.md`.

#### WF-116 Verify this plan: schema, endpoints and reading a pasted plan [M4, M]
- Depends on: WF-048, WF-055, WF-073, WF-044.
- Description: models, repository and tests for `plan_verifications` and `plan_verification_items` (the tables, policies and grants exist since P04, 03 section 5.20 and 6), the run kinds `verify_extract` and `verify_plan`, the `verify_plan` credit action and price row, flag `verify_plan` and kill switch `ai.verify`. `POST /trips/{id}/verify-plan` redacts the pasted text (the WF-073 redactor), calls Haiku once with a strict schema and no tools (06 section 5.11, up to 8,000 characters and 25 items), applies the grounding checks (every name, hours and price must appear in the text), stores only the items (never the text) and returns the price of step 2. Also `GET`, `PUT selection` (cap by `verify_items_per_run`: Free 5, Plus and Trip Pass 12), `DELETE`. 1 credit in the `explain` price class, refunded when nothing is recognized.
- Accept: the recorded model request contains none of the test PII; a name not in the text is dropped; over-cap selection is refused; the pasted text is in no table, log or event; a viewer cannot start a check; a member cannot update verdicts or evidence columns (grants test).
- Touches: `apps/api/hermi/modules/verification/`, `apps/api/hermi/modules/ai/features/verify_extract.py`, models for 03 section 5.20.
- Tests: grounding tests, redaction corpus reuse, grants and RLS tests, refund test, idempotency test, consent and kill switch tests.
- Done: DoD plus the 03 section 5.20 models reviewed against the P04 tables.

#### WF-117 Verify this plan: item checks, verdicts and credit settlement [M4, L]
- Depends on: WF-116, WF-033, WF-050, WF-049.
- Description: `POST /plan-verifications/{id}/check` and the `run_verify_plan` worker job (06 section 5.11), through the provider seam (WF-131); the CLI path validates the final JSON with the ported ingest checks. Per selected item (4 at a time): place search match (name similarity 0.8, 30 km), shared cache lookup (`place_check`, 14 days), then at most one Haiku request with `web_search` (1) and `web_fetch` (1, 4,000 content tokens) and a strict schema; the verdict (green, amber, red, unchecked) is decided in code after grounding every reported value in a tool result, with hours compared as weekday windows and prices within 15 percent; green and amber always carry a cited page and date. Reserves 1 credit per item, settles to the items that ended green, amber or red, refunds the rest (provider error, budget stop, blocked source), admits like an agent run (month headroom for items x $0.02), per-item $0.02 and per-run 3 minute caps, cancel between items. `POST /plan-verifications/{id}/import` writes the ticked items as itinerary items (`source = 'verify_plan'`, `check_url`, `checked_at`).
- Accept: a fixture plan of 9 items with known truths yields the expected verdicts; an invented place is never green; a value the model reports that is not in the fetched content is discarded; Airbnb, Vrbo and Booking.com pages are never opened; credits charged equal the items checked and the rest are returned; a stopped run refunds unchecked items; the import carries evidence into the trip.
- Touches: `apps/api/hermi/modules/verification/`, `apps/worker/hermi_worker/jobs/run_verify_plan.py`, `apps/api/hermi/modules/ai/features/verify_check.py`, `apps/api/hermi/modules/places/` (hours parser).
- Tests: verdict table tests, hours and price comparison tests, grounding tests, injection fixtures in fetched pages, budget stop test, refund and settle tests, concurrency test, blocked-domain test, cache hit test, fake Messages client with recorded fixtures (06 section 10).
- Done: DoD plus the first accuracy numbers written to `docs/evals/verify-plan.md`.

### Month 5: iOS and polish, TestFlight beta

#### WF-080 Capacitor shell, signing and CI [M5, L, GitHub macOS runner]
- Depends on: WF-017, WF-036.
- Description: `apps/ios` Capacitor project (bundled, no `server.url`), bundle id `world.hermi.ios` with Push, Associated Domains, Sign in with Apple, In-App Purchase and App Attest, icon and splash from the brand files, signing with an App Store Connect API key on a GitHub macOS runner (`ios.yml`), build flag that excludes admin routes. The iOS app is locked to portrait on phones.
- Accept: the app launches on a device against staging; the release build contains no admin code; CI produces a signed build.
- Touches: `apps/ios/`, `.github/workflows/ios.yml`, `apps/web/vite.config.ts`.
- Kit: 05 5.2, 6.1; screens/01-welcome.html
- Tests: native launch smoke test; bundle inspection script.
- Done: DoD plus Apple Developer and Paid Applications Agreement status noted.

#### WF-081 Native plugins [M5, M]
- Depends on: WF-080.
- Description: push plugin wiring, share, haptics, status bar, keyboard resize, secure storage (Keychain), in-app review (at most 3 a year, never after an error, never tied to a reward), app URL open, and `SFSafariViewController` through the Capacitor Browser plugin for affiliate links; a document picker for `.ics` import. Add `@capacitor/text-zoom`; text-bearing shapes use `min-height`; Playwright runs the main screens at 310 percent text zoom; old markup that breaks is rebuilt from kit blocks.
- Accept: each plugin has a web fallback; partner links open in `SFSafariViewController`; the ICS file picker hands a file to WF-071; attribution loss measured against Safari and recorded.
- Touches: `apps/web/src/lib/native/`, `apps/ios/plugins/`.
- Kit: 05 5.2, 9.3, 11; none, follow DL section 11
- Tests: plugin mock tests, device checklist.
- Done: DoD.

#### WF-082 Sign in with Apple native [M5, M]
- Depends on: WF-080, WF-013.
- Description: native Apple sign-in exchanged through Supabase, Keychain session storage, "Hide My Email" relay handling, server-to-server notification handling for email changes and deletion.
- Accept: sign in works on device; token revoke on deletion works (tested with WF-092); reviewers can sign in with the demo account.
- Touches: `apps/web/src/lib/native/apple-sign-in.ts`, `apps/api/hermi/modules/auth/apple.py`.
- Tests: exchange tests, notification handler tests.
- Done: DoD.

#### WF-083 App Attest and device trust [M5, M]
- Depends on: WF-080, WF-013.
- Description: App Attest as in [10-quality-security-launch.md](10-quality-security-launch.md) section 2.4: challenge and attestation endpoints, assertions on the first AI action of a session and on account creation, one attested device per Free allowance per 30 days, and the stricter fallback (half the Free AI allowance, email verification, per-IP limits) when attestation is unavailable. The same attested-device signal feeds the referral and import-reward checks.
- Accept: attestation verifies on a real device; fallback verified; normal planning is never blocked; a second account on one device does not get a second Free allowance.
- Touches: `apps/api/hermi/security/attest.py`, `apps/api/hermi/modules/auth/` (devices), `apps/web/src/lib/native/`.
- Tests: attestation fixture tests, counter replay test, fallback test; device test.
- Done: DoD.

#### WF-084 Purchases in the app [M5, L]
- Depends on: WF-063, WF-066, WF-080, WF-082.
- Description: `@revenuecat/purchases-capacitor`, `logIn` and `logOut` tied to sign-in, products in App Store Connect (`hermi_plus_monthly`, `hermi_plus_annual` with 7-day trial on annual only, `hermi_trip_pass`, credit packs; ids as in [03-database-schema.md](03-database-schema.md) section 11.2), paywall purchase flow with price and period first, trial length and after-trial price, Terms and Privacy links, Restore on the paywall and in Settings, sync call after purchase. Replaces the WF-076 harness.
- Accept: every sandbox purchase unlocks within seconds; Restore works on a second device; paywall text meets Guideline 3.1.2.
- Touches: `apps/web/src/lib/native/purchases.ts`, `apps/web/src/routes/paywall/`.
- Kit: 05 4.14, 6.27, 8; screens/07-paywall.html
- Tests: mocked purchase flow tests; sandbox checklist in WF-102.
- Done: DoD plus product metadata and review screenshots uploaded.

#### WF-085 Universal links and invite flow [M5, M]
- Depends on: WF-080, WF-025.
- Description: `/.well-known/apple-app-site-association` (JSON, no redirect), routes `/invite/:token`, `/trips/:id`, `/s/:shareId`, `appUrlOpen` routing into React Router, cold start from a deep link tested.
- Accept: tapping an invite in Messages opens the app on the invite screen; without the app it opens the web invite.
- Touches: `infra/cloudflare/aasa.json`, `apps/web/src/lib/native/links.ts`.
- Tests: route mapping tests; device test.
- Done: DoD.

#### WF-086 APNs, devices and push [M5, M]
- Depends on: WF-047, WF-081.
- Description: `devices` registration, direct APNs with a `.p8` key over HTTP/2, 410 cleanup, collapse ids, topics (price drop, booked-fare drop, run result, invite accepted, trip starts tomorrow), local notifications for "leave for the airport". Permission is requested after the first invite or alert.
- Accept: a price drop arrives on device within 30 minutes of the check; dead tokens deleted; asking for permission happens after the first alert, not at launch.
- Touches: `apps/api/hermi/providers/apns.py`, `apps/api/hermi/modules/notifications/`, `apps/web/src/lib/native/push.ts`.
- Tests: APNs client tests with a fake, 410 cleanup test.
- Done: DoD.

#### WF-087 Notification preferences UI [M5, S]
- Depends on: WF-086.
- Description: preference center by type, quiet hours, per-trip mute.
- Accept: preferences respected by the service; no marketing push without opt-in.
- Touches: `apps/web/src/routes/settings/notifications.tsx`.
- Kit: 05 6.29; none, follow DL section 11
- Tests: component tests, service preference tests.
- Done: DoD.

#### WF-088 Offline reading [M5, L]
- Depends on: WF-036, WF-080.
- Description: trips are readable offline on every tier. A persisted TanStack Query cache for trip-scoped queries (30 day `gcTime`, `offlineFirst`), SQLite for critical data on iOS, "Download for offline" with automatic download within 7 days of departure, an offline banner, cached evidence labels and map tiles for the trip area where provider terms allow.
- Accept: a full trip is browsable in airplane mode on a device on Free and Plus; the cache is cleared on sign-out and on account deletion; stale data is labeled.
- Touches: `apps/web/src/lib/offline/`, `apps/web/src/app/providers.tsx`.
- Kit: 05 6.33; none, follow DL section 11
- Tests: persister tests, sign-out purge test, device test in airplane mode.
- Done: DoD.

#### WF-089 Offline edit queue [M5, M]
- Depends on: WF-088.
- Description: offline edits for notes, checkmarks and itinerary moves queue locally and sync on reconnect (last write wins per field, 409 conflicts shown with the latest row).
- Accept: queued edits sync on reconnect; rejected edits show a toast; no edit is lost on app restart.
- Touches: `apps/web/src/lib/offline/queue.ts`.
- Kit: 05 6.33; none, follow DL section 11
- Tests: mutation replay tests, conflict test, restart test.
- Done: DoD.

#### WF-090 Calendar subscription feed [M5, M]
- Depends on: WF-032.
- Description: a live subscribable feed `GET /calendar/{token}.ics` (follows 04 section 5.29: token in the path, `If-None-Match`, privacy rules) authenticated by a per-trip secret token (stored as `calendar_token_hash`, rotated by `POST /trips/{id}/calendar-token`), with itinerary items and booked flights and stays as events with stable UIDs and correct time zones, an "Add to calendar" button (`webcal://`), `Cache-Control: private, max-age=300`. Private notes and exact prices are excluded.
- Accept: a calendar app shows edits within its refresh interval; rotating the token kills the old URL immediately; the token never appears in logs; 120 requests an hour per token and 600 an hour per IP (04 section 5.29).
- Touches: `apps/api/hermi/modules/itinerary/` (calendar feed), `apps/web/src/routes/trip-settings/`.
- Kit: 05 6.31; none, follow DL section 11
- Tests: golden file, token rotation test, privacy test, rate limit test, log scrub test. Smoke flow 25 (10 section 1.6, 01 section 3.10): the Overview shows "Happening now", the trip reads offline, and the calendar feed can be subscribed to and its token rotated.
- Done: DoD.

#### WF-091 Presentation mode, read-only share view and PDF export [M5, L]
- Depends on: WF-025, WF-032.
- Description: full-screen presentation with a swipe story view in portrait and wake lock; a shareable read-only link view from `trip_share_links` (noindex by default, redacted address, prices and notes); PDF export from present mode (Free adds a small footer); the PDF uses a wheels-only PDF library (for example `reportlab` or `fpdf2`, not WeasyPrint).
- Accept: share view shows no private notes or email; present mode works offline once cached; PDF matches the presentation; the Free footer is small and only on Free.
- Touches: `apps/web/src/routes/present/`, `apps/api/hermi/modules/collaboration/` (share links), `apps/api/hermi/modules/itinerary/` (presentation data, PDF).
- Kit: 05 6.19; none, follow DL section 11
- Tests: privacy test on share payload, Playwright present-mode test, PDF golden test. Smoke flow 12 (10 section 1.6): present mode opens full screen and swipes through days; the PDF downloads with the Free footer.
- Done: DoD.

#### WF-092 Account deletion [M5, M]
- Depends on: WF-013, WF-047.
- Description: in-app deletion request with re-authentication, 30 day grace, hard delete of trip data and files (including import previews, referral links and calendar tokens), transfer or delete shared trips, delete the Supabase Auth user, revoke the Sign in with Apple token, warning that an Apple subscription is not cancelled. Adds `DELETE /me/ai-history`, writes the identity hash on deletion (so a re-created account does not get the taster or first-import pass again) and owns the `retention_sweep` job (WF-046 does not register it).
- Accept: `DELETE /me/ai-history` removes the user's AI history; deletion writes the identity hash; the `retention_sweep` job runs here; after the sweep no row in any table references the user; shared trips transfer or delete as chosen; the confirmation email is sent; backups purge on their cycle (documented).
- Touches: `apps/api/hermi/modules/auth/` (deletion), `apps/worker/hermi_worker/jobs/delete_account.py`.
- Kit: 05 6.25, 6.28; none, follow DL section 11
- Tests: end-to-end deletion test over all tables, grace cancel test. Smoke flow 11 (10 section 1.6): account deletion needs re-authentication and lists its effects.
- Done: DoD.

#### WF-093 Data export [M5, M]
- Depends on: WF-092.
- Description: "Export my data" as JSON plus ICS (and a PDF with a wheels-only library such as `reportlab` or `fpdf2`, not WeasyPrint) through a job, stored in R2, emailed link with expiry, available on every tier. Formats: PDF, CSV and per-trip export; the disclosure text is snapshotted into the PDF and the email.
- Accept: export includes all user-owned data (checked against a list generated from the schema); link expires; another user cannot fetch it.
- Touches: `apps/api/hermi/modules/auth/` (export), `apps/worker/hermi_worker/jobs/export_user_data.py`.
- Kit: 05 6.25, 6.28; none, follow DL section 11
- Tests: completeness test, expiry test, authorization test. Smoke flow 10 (10 section 1.6): the export request shows a pending state in Settings.
- Done: DoD.

#### WF-094 Settings, consents and legal pages [M5, M]
- Depends on: WF-054, WF-092.
- Description: profile and settings screens (AI toggle, analytics opt-out, hide booking links, notifications, export, delete), privacy policy, terms, affiliate disclosure, AI disclaimer, licenses screen (data attributions, listing the licences of the three fonts), consent history, "Sign out everywhere" and preferences.
- Accept: pages public and linked from Settings and sign-in; policy names Anthropic, affiliate click logging and how imports are processed.
- Touches: `apps/web/src/routes/legal/`, `apps/web/src/routes/settings/`.
- Kit: 05 6.25, 6.28; none, follow DL section 11
- Tests: link presence tests.
- Done: DoD plus counsel review noted or explicitly deferred.

#### WF-095 Onboarding: switching question [M5, S]
- Depends on: WF-018, WF-071, WF-072, WF-073, WF-074, WF-121.
- Description: the onboarding question "Coming from TripIt, Tripsy or Wanderlog?" with answers (TripIt, Tripsy, Wanderlog, another app, starting fresh); the first three lead to the matching entry on the import screen (WF-121) and mention the free Trip Pass for a first import that adds 3 or more items including a flight or a stay, only to accounts without Plus; "starting fresh" continues to the first-trip wizard. Skippable. The answer is stored as an enum for analytics only.
- Accept: each answer leads to the right screen; skipping loses nothing; the reward is described accurately and only to Free accounts.
- Touches: `apps/web/src/routes/onboarding/`.
- Kit: 05 6.1; screens/01-welcome.html
- Tests: component tests, Playwright switching flow.
- Done: DoD.

#### WF-096 Accessibility, i18n base and privacy manifest [M5, M]
- Depends on: WF-080.
- Description: VoiceOver labels and focus order, Dynamic Type, reduce motion, axe in Playwright, the contrast unit test over every Hermi palette token pair (05 section 2.3) including `--tp-edge`, `--tp-warning-ink` and `--tp-sky-ink` on `--tp-sky` with Increase Contrast swapping `--tp-rule` and `--tp-edge` to ink, `react-i18next` extraction of copy, `PrivacyInfo.xcprivacy` with required-reason API declarations, Info.plist purpose strings, privacy label answers matching click logging.
- Accept: no axe critical issues; the token pairs pass in light, dark and Increase Contrast; all permission strings present; label answers match the policy.
- Touches: `apps/web/src/lib/i18n/`, `apps/ios/App/PrivacyInfo.xcprivacy`, `packages/tokens/` (contrast test).
- Kit: 05 2.3, 9; none, follow DL section 11
- Tests: axe suite, token contrast test, string extraction test.
- Done: DoD.

#### WF-097 Performance and empty-state polish [M5, L]
- Depends on: WF-036, WF-088.
- Description: profile and fix the cold start (under 2 seconds to interactive on an iPhone 12 with a cached trip), main JS chunk under 500 kB gzip, map and calendar smoothness in the WebView, empty and error states checked on every screen, skeletons, reduced-motion behavior; the checks widen to error, limit and offline states.
- Accept: budgets met and recorded; no screen lacks an empty state; map stays smooth with 200 markers on a device.
- Touches: `apps/web/src/` (routes and components), `apps/web/vite.config.ts`.
- Kit: 05 4.16 to 4.18 and 6 (every screen); none, follow DL section 11
- Tests: bundle size check in CI, a timed cold start script, Playwright empty-state sweep.
- Done: DoD.

#### WF-098 Analytics events for Phase 1 [M5, M]
- Depends on: WF-038.
- Description: fire every event in the Phase 1 catalogue ([10-quality-security-launch.md](10-quality-security-launch.md) section 4), including the new ones for imports (`import_started` with `origin`, `import_previewed`, `import_completed`, `import_failed`, `import_reward_granted`, `calendar_polling_enabled`, `calendar_changes_found`, `calendar_changes_applied`), onboarding switching, collaborator limit, offline, calendar feed, booked-fare watch and alert, evidence and rechecks, Verify this plan (`verify_started`, `verify_items_read`, `verify_checked`, `verify_imported`), trust pages and the cancel link, the sync indicator, the status banner, the Android install card, public pages, content reports, `/vs` pages and referrals. Funnels: activation, invite loop, paywall, AI, affiliate, switching (onboarding answer to import completed to reward to first itinerary edit).
- Accept: each event fires once with only enum and bucket properties; no URL, file name, pasted text or trip title is ever an event property; opt-out stops every event.
- Touches: `apps/web/src/lib/analytics.ts`, `apps/api/hermi/analytics.py`, `packages/shared/src/events.ts`, `docs/analytics.md`.
- Tests: event firing tests, property allowlist test, opt-out test.
- Done: DoD plus `docs/analytics.md` matches section 4 of 10.

#### WF-099 Admin affiliate revenue screens [M5, M]
- Depends on: WF-067, WF-069, WF-058.
- Description: revenue by network, program and placement, conversion import status, unmatched share, and a disclosure audit that lists every placement and whether it renders the disclosure. Spec: [08](08-admin-control-center.md) section 6.7 (the link checker and two-person template approval are Phase 2). Adds the "Mark a payout received" action and `POST /v1/admin/affiliate/payouts`.
- Accept: numbers match `affiliate_conversions`; a placement without disclosure shows as a failure; "Mark a payout received" posts to `POST /v1/admin/affiliate/payouts` and the screen shows it.
- Touches: `apps/api/hermi/modules/admin/affiliate.py`, `apps/web/src/routes/admin/`.
- Kit: 08 section 5 and 08 6.7; none, follow DL section 11
- Tests: aggregation tests, disclosure audit test.
- Done: DoD.

#### WF-100 Uptime, alerts and status page [M5, M]
- Depends on: WF-037.
- Description: probes on `/health/ready` from two regions, a synthetic sign-in and trip-load check, heartbeat monitors (scheduler, nightly jobs, queue), public status page on Better Stack with the five components of 02 section 8.1 (web app, API, AI features, fare data, push) and a first incident template, alert routing (phone for outage, data loss risk and spend runaway only), and the Phase 1 alerts of [10-quality-security-launch.md](10-quality-security-launch.md) section 5.3.
- Accept: stopping the worker in staging raises a page within 5 minutes; the status page is live, hosted outside Render and Cloudflare Pages, and shows the five components.
- Touches: `infra/render/render.yaml` (heartbeats), `docs/runbooks/`.
- Tests: drill recorded.
- Done: DoD.

#### WF-101 Maestro tests and TestFlight pipeline [M5, M]
- Depends on: WF-080.
- Description: Maestro native smoke flows (sign in, create trip, import an ICS file, open offline, purchase in sandbox), automated TestFlight upload with dSYM and source map upload to Sentry, internal testers from week 19 and external testers (30) from week 21.
- Accept: a tagged build reaches TestFlight automatically; crash reports symbolicated.
- Touches: `.github/workflows/ios.yml` (GitHub macOS runner; see knowledge/ios-builds-on-ci.md), `apps/web/e2e/maestro/`.
- Kit: 05 6.3, 6.6, 6.27, 6.30, 6.33; none, follow DL section 11
- Tests: the Maestro flows. A flow manifest check compares the Playwright smoke flows with the list in 10 section 1.6.
- Done: DoD.

#### WF-102 Sandbox purchase matrix [M5, M]
- Depends on: WF-084, WF-065.
- Description: run and record every scenario for the Phase 1 products: purchase Plus monthly and annual (trial), cancel, switch monthly and annual, refund, restore on a second device, billing retry, Trip Pass bound to a trip, free import-reward pass (no purchase), credit pack grant once, expired pass.
- Accept: each scenario passes or has a fixed bug; results in `docs/qa/purchase-matrix.md`.
- Touches: `docs/qa/`.
- Tests: the matrix.
- Done: DoD.

#### WF-103 Beta operations and metrics report [M5, M]
- Depends on: WF-079, WF-098, WF-101.
- Description: invite tooling for 30 to 50 TestFlight testers (plus waitlist invites), a weekly feedback loop, and a report with crash-free sessions, import completion, activation, week 1 retention and AI cost per active user against ceilings.
- Accept: testers can be invited in batches; the report produces the Month 5 exit numbers.
- Touches: `apps/api/hermi/modules/admin/invites.py`, `infra/scripts/beta_report.py`.
- Tests: cohort calculation tests.
- Done: DoD plus the Month 5 gate review recorded.

#### WF-123 Keep checking this calendar: opt-in polling and change preview [M5, L]
- Depends on: WF-072, WF-046, WF-086.
- Description: after a feed import is applied the person can switch on "Keep checking this calendar" (off by default, never turned on for them): `PUT /imports/{id}/polling` calls `set_import_polling()` (03 section 5.9), keeps the feed URL encrypted (`feed_url_enc`, `FIELD_ENCRYPTION_KEY`) only while on, at most 3 polled feeds per account. The `poll_import_feeds` scheduler job (every 30 minutes, leader only) enqueues `fetch_import_feed` for due rows; each feed is read every 6 hours through the SSRF guard with a conditional request and a content hash (`last_content_hash`). A change builds a diff against the import's items (by `import_uid`) into `pending_changes`, sends a push and in-app notice, and the "Calendar changed" sheet lists new, changed (before and after) and removed events; `POST /imports/{id}/changes/confirm` applies only the ticked changes; nothing is ever applied automatically and removed events are never deleted for the person. Polling stops after 3 failures in a row (`calendar_poll_stopped`), 7 days after the trip ends, or when switched off (URL and pending changes deleted). Kill switches `import.polling` and `import.all`; flag `calendar_feed_polling`; `setting_calendar_polling`.
- Accept: an unchanged feed creates no preview; a changed feed creates one preview and one notice; nothing changes in the trip until the person confirms; turning the switch off deletes the stored URL; the third failure stops polling and tells the person; the fourth polled feed is refused; the URL never appears in logs, Sentry, `provider_calls` or events; a polling confirmation never earns the import reward.
- Touches: `apps/api/hermi/modules/imports/`, `apps/worker/hermi_worker/jobs/poll_import_feeds.py`, `apps/web/src/routes/import/`.
- Kit: 05 6.30; none, follow DL section 11
- Tests: poll schedule test (6 hours), content hash test, diff test (added, changed, removed), confirm-only-ticked test, failure and stop tests, encryption and deletion tests, log scrub test, limit test, SSRF table reuse. Smoke flow 16 (10 section 1.6): turning the calendar switch on and changing the fake feed produces a "Calendar changed" sheet; nothing changes until "Apply".
- Done: DoD plus the threat model updated for stored feed addresses.

#### WF-118 Verify this plan: screens [M5, L]
- Depends on: WF-117, WF-066, WF-121.
- Description: the four-step flow in 05 section 6.38: paste, choose what to check (price shown first, per-run cap, confirm at 6 credits or more), results with verdict chips and evidence labels, and "Add to trip"; entry points on the Trips home "+" menu, the trip menu, the import screen and the AI sheet; "Plan checks" list with 30-day retention; credit-out paywall `out_of_credits_verify` (web says "Upgrade in the iOS app"); the recheck control from WF-120 on imported items; events in 10 section 4. Words and icons, never color alone.
- Accept: a Free account cannot tick more than 5 items and sees the price before the check; results show the evidence label for every green and amber row; red rows are unticked for import; the header reads "Checked 7 of 9..." and never says the plan is verified; leaving mid-run and returning shows progress; axe passes on every step.
- Touches: `apps/web/src/routes/verify/`, `apps/web/src/components/verdict-chip/`, `apps/web/src/routes/trips/`.
- Kit: 05 6.38; none, follow DL section 11
- Tests: component tests per state, Playwright end-to-end with a fake Anthropic client, axe checks, a copy lint test for the forbidden words ("verified", "safe to book"). Smoke flow 14 (10 section 1.6): verify a plan end to end with fake Anthropic and fake place data.
- Done: DoD.

#### WF-126 Public status summary and in-app status banner [M5, S]
- Depends on: WF-100, WF-037, WF-130.
- Description: `GET /public/status` (04 section 5.28) mirrors the five component states of the hosted status page (02 section 8.1) and is cached 30 seconds; the app shows the quiet banner "Fares are delayed right now. Saved trips still work." with a "Service status" link only when a component is degraded, and Settings has "Service status". The banner never appears for one person's failed request.
- Accept: degrading a component in staging shows the banner within a minute and clearing it removes it; the endpoint answers without auth and without touching the database more than once a minute; offline the app shows the offline banner instead.
- Touches: `apps/api/hermi/modules/admin/` (status read), `apps/api/hermi/api/public.py`, `apps/web/src/components/status-banner/`.
- Kit: 05 6.41; none, follow DL section 11
- Tests: endpoint contract test, banner component tests, caching test. Smoke flow 18, second half (10 section 1.6): a degraded component in the fake status source shows the status banner.
- Done: DoD.

#### WF-122 Google Maps export file import [M5, M]
- Depends on: WF-121.
- Description: `POST /imports/maps-file` reads a Google Takeout saved-list export (CSV, GeoJSON or KML, up to 5 MB and 200 places) locally and matches each title by place search (no AI, no credits); candidates of kind `place` import as ideas; notes and any Google Maps URLs stay as plain text and are never followed; a pasted list link is never opened (WF-121 already guides the export).
- Accept: golden exports from 3 Takeout variants import with the right matches; a file with no places says so; 201 places import the first 200 and warn; no network request is made for any URL in the file.
- Touches: `apps/api/hermi/modules/trips/import_maps.py`, `apps/web/src/routes/import/`.
- Kit: 05 6.30; none, follow DL section 11
- Tests: golden files (CSV, GeoJSON, KML), no-network test, limits test, reward exclusion test.
- Done: DoD.

### Month 6: launch

#### WF-104 Store listing and privacy labels [M6, M]
- Depends on: WF-101, WF-096.
- Description: app name "Hermi: Group Trip Planner", subtitle "Plan together. Know the fare.", keywords (no competitor names), promotional text, description, six 6.9 inch screenshots (trip overview, itinerary on map, price-drop alert, import from another app, AI plan with evidence labels, offline mode; a shared trip or present mode if room), 1024 icon without alpha, age rating questionnaire, privacy labels, localizations (en-US, es, de). Products for Phase 1 only: Plus, Trip Pass, credit packs.
- Accept: all App Store Connect fields complete; screenshots from real builds; privacy labels match the policy, click logging and import processing.
- Touches: `docs/store/`.
- Tests: checklist review.
- Done: DoD.

#### WF-105 Admin support inbox and macros [M6, L]
- Depends on: WF-058, WF-047.
- Description: ticket intake (in-app contact with version, device, user id and error id attached; email to support), linking to users, replies via Resend, macros from `admin/macros/*.md` (including import problems and refund rules), SLA timers. Spec: [08](08-admin-control-center.md) section 6.11.
- Accept: a ticket links to its user automatically; a reply uses a macro; overdue tickets flag; refund replies prompt an audited action.
- Touches: `apps/api/hermi/modules/admin/support.py`, `apps/web/src/routes/admin/support/`.
- Kit: 08 section 5 and 08 6.11; none, follow DL section 11
- Tests: intake tests, macro rendering tests, SLA tests.
- Done: DoD.

#### WF-106 Admin content reports [M6, M]
- Depends on: WF-058, WF-091.
- Description: the basic content reports queue for reported shared trips, public sample trips and AI answers; actions (dismiss, hide, disable link, flag a research cache entry, suspend sharing for a user); in-app "Report" and "Block"; 24 hour response alert. Shared and public pages link here.
- Accept: a report reaches the queue; disabling a link takes effect immediately and removes the page from the sitemap; flagged cache entries are not served; the reporter gets an acknowledgement.
- Touches: `apps/api/hermi/modules/admin/moderation.py`, `apps/web/src/components/report/`, `apps/web/src/routes/admin/`.
- Kit: 08 section 5 and 08 6.12; none, follow DL section 11
- Tests: queue tests, action tests, takedown timing test.
- Done: DoD.

#### WF-107 Public sample trips and shared-trip pages [M6, L]
- Depends on: WF-091, WF-106, WF-025, WF-133.
- Description: server-rendered pages (sub-steps pages and sitemap; this ticket builds only the server-rendered pages) that work without JavaScript: sample trips at `/samples/{slug}` (written by Hermi from a system account, always indexable, reusing the WF-133 sample routes of 04 section 5.28, with "Use this plan" into the visitor's account after sign-up) and shared-trip pages at `/s/{shareId}` (owner-chosen; public pages carry `noindex` unless `trip_share_links.indexable`, and an "Let search engines find this trip" toggle that adds a sitemap entry). Both redact addresses, prices, notes and traveler names; carry Open Graph tags, a sitemap, a report link, the evidence labels and a sign-up call to action; no partner buttons in Phase 1. Kill switch `public_pages`.
- Accept: pages render without JavaScript; private data never appears in the HTML, JSON or meta tags; disabling a link returns 410 and drops it from the sitemap within 5 minutes; robots rules match the owner's choice (`noindex` unless `trip_share_links.indexable`); "Use this plan" on a sample creates an independent trip.
- Touches: `apps/api/hermi/modules/collaboration/` (public pages), `apps/web/src/routes/public/`, `apps/web/public/` (robots and sitemap), `apps/web/vite.config.ts`.
- Kit: 05 6.34, 6.35; none, follow DL section 11
- Tests: privacy scan of rendered pages against sentinel strings, sitemap test, takedown test, no-JavaScript render test, Lighthouse check. Smoke flow 13 (10 section 1.6): a public sample trip loads with JavaScript disabled, shows no partner buttons and has a working Report link.
- Done: DoD.

#### WF-108 Referral credits [M6, L]
- Depends on: WF-044, WF-064, WF-083, WF-094.
- Description: each user gets a referral link in Settings ("Invite friends"); when a referred person signs up, verifies their email and creates their first trip with dates, both accounts get 20 credits (settled values in the `setting_referral_credits` flag; `credit_grants` kind `promo`, expiring after 12 months; referral credits never raise the provider-spend ceiling). Uses the `referral_codes` and `referral_rewards` tables and the functions in 03 section 5.9. Abuse controls: no self-referral (same device key, IP hash or normalized email), a referrer is paid for at most 5 rewards in a rolling 30 days and 10 in a calendar year (the referred person still gets theirs), unique per referred account, rewards only from attested devices or verified email, reversal on refund or abuse flag, never tied to a rating or review. Kill switch `referrals.grant`. The `/r/<code>` landing page is built here.
- Accept: a valid referral grants 20 credits to both sides once, expiring in 12 months; the sixth reward in 30 days and the eleventh in a calendar year pay the referrer nothing and the referred person in full; self, duplicate and farmed referrals grant nothing and are logged; admin can revoke and the ledger reverses; the referral link carries no user id or email.
- Touches: `apps/api/hermi/modules/credits/` (grants), `apps/api/hermi/modules/auth/` (referrals), `apps/web/src/routes/settings/`.
- Kit: 05 6.37; none, follow DL section 11
- Tests: reward-once test, self-referral tests, velocity and cap tests (5 per 30 days, 10 per year), expiry test, no-ceiling-raise test, reversal test, idempotency under concurrency.
- Done: DoD.

#### WF-109 Comparison pages (/vs) [M6, M]
- Depends on: WF-107.
- Description: honest, server-rendered `/vs/tripit`, `/vs/wanderlog` and `/vs/tripsy` pages (more later) with a fact table where every claim has a public source URL and a "checked on" date in `docs/vs/facts.json`, what the other app does better, how to switch (a link to the import chooser), and a correction email. Facts are checked by hand; nothing is scraped. No competitor names in App Store metadata.
- Accept: each fact has a source and date under 90 days old (CI warns); pages render without JavaScript; no claim is unsourced; pages link to sign-up and the import flow.
- Touches: `apps/web/src/routes/vs/`, `apps/web/public/` (sitemap), `docs/vs/facts.json`.
- Kit: 05 6.36; none, follow DL section 11
- Tests: facts schema and freshness test, no-JavaScript render test, broken link check.
- Done: DoD plus the owner's read-through for fairness.

#### WF-110 Security review and penetration test fixes [M6, L]
- Depends on: WF-016, WF-072, WF-107, WF-108.
- Description: an outside penetration test scoped to auth, tenant isolation, purchase and credit flows, `/go`, link preview, ICS file and feed import, pasted import, public pages and reports, referral abuse and admin, the `claude_cli` guard and the never-fetch constant `BLOCKED_HOSTS`; fix every high and critical finding; run the parser fuzzers for an extended hour; rerun dependency audit and secret scan; rotate secrets used during the beta; update the threat model.
- Accept: no open high or critical findings; fuzz run clean; threat model and data map updated.
- Touches: `docs/security/`, code fixes as needed.
- Tests: regression tests for every finding.
- Done: DoD plus the report and fix list in `docs/security/pentest.md`.

#### WF-111 Review notes and demo account [M6, S]
- Depends on: WF-102, WF-104, WF-124.
- Description: demo accounts (a Plus account with a loaded trip and a Free account, using the server-allowlisted "Reviewer sign in" path, not Sign in with Apple) with a working sandbox purchase path, sample `.ics` file and sample confirmation text attached to the notes, review notes covering AI, import, deletion location, push, offline, public pages and report, affiliate links under Guideline 3.1.3(e), no ATT prompt, live servers and a phone number; the notes also cover the trust pages `/how-we-earn` and `/billing`.
- Accept: a fresh device signs in with the demo account against production; Restore, deletion, import and report paths are visible.
- Touches: `docs/store/review-notes.md`.
- Tests: manual pass on a clean device.
- Done: DoD.

#### WF-112 Load test and runbooks [M6, L]
- Depends on: WF-100, WF-039.
- Description: load test at 10 times expected launch traffic and 5,000 synthetic routes, runbooks for the top incidents (provider outage, bad deploy, leaked key, runaway AI spend, restore, Supabase Auth outage, import abuse, referral abuse, public page takedown), on-call alert routing test, status page copy.
- Accept: p95 latency and queue wait within targets; each runbook exercised once; key rotation list complete.
- Touches: `docs/runbooks/`, `infra/scripts/loadtest/`.
- Tests: the load test.
- Done: DoD.

#### WF-113 Admin user actions [M6, L]
- Depends on: WF-077, WF-044.
- Description: grant credits, extend a pass, revoke an import-reward pass or referral credit, force sign-out, start export, queue or process deletion, hold AI; role limits and confirmation tiers. Comping subscriptions and impersonation are Phase 2.
- Accept: limits enforced (for example support 50 credits a grant); each action audited with before and after.
- Touches: `apps/api/hermi/modules/admin/user_actions.py`.
- Kit: 08 section 5 and 08 6.2; none, follow DL section 11
- Tests: limit tests per role, audit tests, idempotency tests.
- Done: DoD.

#### WF-114 Admin flags, provider and system health [M6, L]
- Depends on: WF-058, WF-042.
- Description: feature flags screen, provider health (SerpApi, Travelpayouts, Geoapify, Anthropic, Resend, RevenueCat), system health (queues, failures, webhook backlog, deploys), job retry. Spec: [08](08-admin-control-center.md) sections 6.6, 6.13 and 6.14. Experiments are Phase 2.
- Accept: flags cannot touch disclosure or ranking keys; retry is idempotent; provider status matches probes.
- Touches: `apps/api/hermi/modules/admin/flags.py`, `providers.py`, `system.py`, `apps/web/src/routes/admin/`.
- Kit: 08 section 5 and 08 6.6, 6.13 and 6.14; none, follow DL section 11
- Tests: guardrail tests, retry idempotency test.
- Done: DoD.

#### WF-115 Submission, review handling and launch [M6, M]
- Depends on: WF-110, WF-111, WF-112, WF-108.
- Description: re-read Apple guidelines on the day, recheck open questions (SerpApi status, external purchase rules), submit at the end of week 24 with manual release, handle up to two review cycles, release after the load test and runbook drills pass, phased release, launch content (waitlist email, Product Hunt, Reddit, import-from-TripIt message), 72-hour monitoring.
- Accept: app approved and live; first 72 hours have no P0; crash-free at least 99.5 percent; API error rate under 1 percent.
- Touches: `docs/launch/`.
- Tests: post-launch smoke test script.
- Done: DoD plus the Month 6 gate review recorded.

#### WF-119 Verify this plan: evals and release gate [M6, L]
- Depends on: WF-118, WF-057.
- Description: the Verify suites in 06 section 10: extraction (40 pasted itineraries, hand-labeled), checking (120 place claims: 50 correct, 25 wrong hour or price, 25 invented, 20 closed or renamed, from saved place data and saved pages, never fetched live), injection and blocked sites, recheck (60 page pairs) and cost replay. Gates: extraction recall 95 percent or more with 0 hallucinated names; false green under 2 percent and no invented place ever green; false red under 5 percent; every green or amber cites a page containing the value; blocked pages opened 0; plan check p95 under $0.02 per item. The suites run through the Batch API and record against the `prompt_version`; live runs only with `EVALS_LIVE=1` and `--max-usd`, through `npm run evals` with `--provider`, certified only on `anthropic_api` (`shortcut:` CLI numbers are provisional); the live run is owner-pending. If a gate fails, the flag `verify_plan` stays off at launch.
- Accept: suites run in CI against recorded fixtures and nightly through Batch; results are committed; the failing-gate path (flag off) is tested; a prompt change cannot ship without a passing run.
- Touches: `backend/evals/` (verify suites), `docs/evals/verify-plan.md`, CI workflow.
- Tests: the suites themselves, plus a test that the gate script fails on a seeded false green.
- Done: DoD plus the gate result recorded in the Month 6 review.

#### WF-124 Trust pages: How we earn, How billing works and the cancel link [M6, M]
- Depends on: WF-068, WF-066, WF-094, WF-084.
- Description: the public pages `/how-we-earn` (from `GET /public/how-we-earn`, built from `affiliate_programs` so every active partner is listed, with the rules, a sample labeled button and live counts) and `/billing` (plain billing text, prices from the same configuration as the paywall), both in the marketing shell and in the app from Account and the paywall legal row; the plan card gets a first-level "Cancel subscription" row that opens the App Store's subscription sheet (`Purchases.showManageSubscriptions()`; on the web "Cancel in the iOS app" with the store page link); `Entitlements.cancel_url`; the trial reminder, receipt and billing problem emails carry the cancel link; `/vs` pages and the App Store listing link to `/how-we-earn`. No affiliate card, paywall or survey on any of these.
- Accept: adding an active `affiliate_programs` row makes it appear on `/how-we-earn` with no code change; the prices on `/billing` match the paywall (a test compares them); the cancel row is reachable in one tap from the Account screen and opens the subscription sheet in the sandbox build; the trial reminder email contains the link; the pages pass axe and have no em dashes.
- Touches: `apps/web/src/routes/how-we-earn/`, `apps/web/src/routes/billing/`, `apps/api/hermi/api/public.py`, `apps/api/hermi/modules/affiliate/`, `apps/web/src/routes/account/`.
- Kit: 05 6.40; none, follow DL section 11
- Tests: partner-list generation test, price-match test, cancel row test, email template test, copy lint. Smoke flow 17, second half (10 section 1.6): the public pages `/how-we-earn` and `/billing` load without sign-in and pass axe.
- Done: DoD.

#### WF-127 Android install: installable web app and install guide [M6, M]
- Depends on: WF-088, WF-036.
- Description: the web app manifest (name, icons, theme color sky `#2AA5FF`, standalone display, start URL), a service worker that keeps opened trips readable offline on the web (reusing WF-088), the public page `/install/android` (three steps with screenshots for Chrome, a note for Samsung Internet, what works and what does not yet, 05 section 6.42), the dismissible "Add Hermi to your home screen" card on Android Chrome after the first trip (once every 30 days at most, the browser's own install prompt), and a "Install on Android" row in Help. Copy never claims a Play Store app or push notifications.
- Accept: Chrome on Android offers "Install app"; the installed app opens a trip offline; the card never shows before a trip exists, on iOS or when already installed; the guide's screenshots match the current Chrome menus on the day of release.
- Touches: `apps/web/public/manifest.webmanifest`, `apps/web/src/sw.ts`, `apps/web/src/routes/install/`, `apps/web/src/components/install-card/`.
- Kit: 05 6.42; none, follow DL section 11
- Tests: Lighthouse PWA check in CI, component tests for the card rules, Playwright Pixel 7 test for the manifest and offline read.
- Done: DoD.

#### WF-128 Android Chrome test pass [M6, S]
- Depends on: WF-127, WF-118.
- Description: the Android Chrome checklist in [10-quality-security-launch.md](10-quality-security-launch.md) sections 1.9 and 7.5: a Playwright project on Chromium with a Pixel 7 profile in CI, plus one manual pass on a real Android phone and one tablet (or the cloud device lab) before the release: sign-in, create and edit a trip, invite and share, import, Verify this plan, offline reading, install flow, keyboard and screen reader basics with TalkBack. Defects go to the Month 6 review.
- Accept: the checklist passes on Chrome on a real Android phone; every defect found is fixed or written into the known-issues list in the review notes; the CI project runs on every pull request.
- Touches: `apps/web/e2e/`, `docs/qa/android-chrome.md`.
- Tests: the Playwright Android project and the manual checklist record.
- Done: DoD plus the checklist result saved in `docs/qa/`.

#### WF-129 Status page polish [M6, S] (cut list, not in the committed plan)
- Depends on: WF-100, WF-126.
- Description: incident templates written in plain words, email subscription, component history export, custom domain and styling for the hosted status page (02 section 8.1). The basic page, five monitors and the in-app banner ship without this. Cut from the committed hours (section 3): build it only in reserve time.
- Accept: a practice incident is posted from a template in under 2 minutes and subscribers receive it.
- Touches: `docs/runbooks/status-page.md`, the hosted status page settings.
- Tests: a recorded drill.
- Done: DoD.

## 7. Moved to Phase 2 or 3

These tickets from the full build roadmap are out of scope for Phase 1. The "Old ID" column is the ticket number in the full [roadmap](../reference-full-spec/09-build-roadmap.md).

| Old ID | Title | Moves to | Note |
|---|---|---|---|
| WF-038 (part) | Households and Family members | Phase 2 | The people (travelers) part is WF-024 |
| WF-045 | Polls and expenses | Phase 2 | Polls, manual cost splitting |
| WF-046 (part) | After-trip "Was your flight delayed?" prompt | Phase 2 | Checklist and notes are WF-035 and WF-070 |
| WF-061 | Admin impersonation | Phase 2 | Not in the Phase 1 admin list |
| WF-077 | Family plan | Phase 2 | |
| WF-078 | Pro behind a flag | Phase 2 | Includes scheduled agent runs |
| WF-093 (part) | Admin experiments | Phase 2 | Flags and provider and system health are WF-114 |
| WF-094 (part) | Admin link checker and two-person template approval | Phase 2 | Revenue screens and disclosure audit are WF-099 |
| WF-095 | Admin finance reports and settings | Phase 2 | Not in the Phase 1 admin list |
| WF-099 | Direct affiliate application pack | Phase 2 | Expedia Group and Vrbo, Booking.com, Skyscanner, Airalo, GetYourGuide |
| WF-101 | Direct affiliate adapters | Phase 2 | |
| WF-102 | Stripe group payments | Phase 3 | |
| WF-103 | Admin concierge and group payments screens | Phase 2 (concierge), Phase 3 (group payments) | |
| WF-104 | Concierge flow | Phase 2 | |
| WF-105 | Pro launch | Phase 2 | |
| WF-106 | Partner guides | Phase 3 | |
| WF-107 | Hermi for Advisors: organizations, seats, workspaces | Phase 3 | |
| WF-108 | Advisor billing and admin | Phase 3 | |
| WF-109 | Printed trip books | Phase 3 | |
| WF-110 | LiteAPI hotel booking | Phase 3 | |
| WF-111 | Android | Phase 2 | Android users get the web app in Phase 1 |
| WF-113 (part) | Paywall experiments, win-back offers, lifecycle messages | Phase 2 | Referral is WF-108 |
| WF-114 | Group Trip Pass and room-block request | Phase 2 | |

Schema parts that move with them: `households` and `household_members` (Phase 2), `polls`, `poll_votes`, `expenses`, `expense_shares` (Phase 2), `payment_collections` and `settlements` with Stripe (Phase 3), `concierge_requests` and `room_block_requests` (Phase 2), `partner_guides` and `print_orders` (Phase 3), `advisor_orgs`, `advisor_seats` and `advisor_clients` (Phase 3), `affiliate_payouts` (Phase 2).

Two decisions to confirm: admin impersonation, finance reports and experiments are not named in any phase README, so they are placed in Phase 2 here because they are not in the Phase 1 admin list.

### Old to new ID map (kept tickets)

| Old | New | Old | New | Old | New |
|---|---|---|---|---|---|
| 001 to 011 | 001 to 011 | 041 | 031 | 072 | 040 |
| 012 | 012 | 042 | 032 | 073 | 103 |
| 013 | 041 | 043 | 033 | 074 | 063 |
| 014 | 042 | 044 | 034 | 075 | 064 |
| 015 | 043 | 046 (part) | 070, 035 | 076 | 065 |
| 016 | 044 | 047 | 091, 107 | 079 | 078 |
| 017 | 045 | 048 | 029 | 080 to 082 | 080 to 082 |
| 018 | 046 | 049 | 053 | 083 | 084 |
| 019 | 048 | 050 | 054 | 084 | 085 |
| 020 | 049 | 051 | 023 | 085 | 086 |
| 021 | 050 | 052 | 066 | 086 | 087 |
| 022 | 051 | 053 to 055 | 067 to 069 | 087 | 088, 089 |
| 023 | 056 | 056 | 058 | 088 | 096 |
| 024 | 057 | 057 | 059 | 089 | 101 |
| 025 | 021 | 058 | 079 | 090 | 102 |
| 026 | 022 | 059 | 077 | 091 | 105 |
| 027 | 020 | 060 | 113 | 092 | 106 |
| 028 | 013 | 062 | 060 | 093 (part) | 114 |
| 029 | 014 | 063 | 061 | 094 (part) | 099 |
| 030 | 015 | 064 | 047 | 096 | 104 |
| 031 | 016 | 065 | 092 | 097 | 111 |
| 032 | 025, 026 | 066 | 093 | 098 | 112 |
| 033 | 028 | 067 | 094 | 100 | 115 |
| 034 | 017 | 068 | 037 | 112 | 107 |
| 035 | 018, 062, 095 | 069 | 038, 098 | 113 (part) | 108 |
| 036 | 036 | 070 | 100 | | |
| 037 | 019 | 071 | 039 | | |
| 038 (part) | 024 | | | | |
| 039 | 030 | | | | |
| 040 | 052 | | | | |

New in Phase 1 (no old ID): WF-026 (Free owners invite 1 collaborator, split from old 032), WF-055 (evidence labels), WF-071 to WF-075 (switching import, reward, booked-fare alert), WF-076 (sandbox purchase harness), WF-083 (App Attest), WF-088 and WF-089 (offline reading and edit queue, split from old 087), WF-090 (calendar subscription feed), WF-095 (onboarding switching question), WF-107 (public sample and shared-trip pages, extends old 112), WF-108 (referral credits, from old 113), WF-109 (`/vs` pages), WF-110 (penetration test and fixes), and WF-116 to WF-129, appended in the integration pass for the features adopted from the competitive analysis: WF-116 to WF-119 (Verify this plan), WF-120 (evidence freshness and recheck), WF-121 (import entries named for TripIt, Tripsy and Wanderlog, and pasted places), WF-122 (Google Maps export file), WF-123 (opt-in calendar polling), WF-124 (How we earn, How billing works, cancel link), WF-125 (sync indicator), WF-126 (public status summary), WF-127 and WF-128 (Android install and Chrome testing), WF-129 (status page polish, on the cut list), and WF-130 to WF-133 (kit port and shell; AI provider seam; AI sheet and action screens; demo seed, sample trips and Discover), added in the runtime and business pass.

## 8. How to work with Claude Code

- **One ticket, one session.** Start a fresh session per ticket. Tell Claude: "Do WF-0NN from `phase-1-launch/09-build-roadmap.md`. Read the ticket, its dependencies, and the spec files it names first." A ticket that cannot be finished in one session is too big: split it and add the new ticket under the same month.
- **Keep the session small.** Aim for about 400 changed lines and at most one migration. If context grows long, finish, commit and start a new session rather than continuing.
- **Plan before code.** For L tickets, ask for a short plan (files, tests, risks) and approve it, then build.
- **Tests first.** Write or ask for the failing tests named in the ticket before the implementation. The acceptance criteria are the test list. For the import tickets (WF-071 to WF-073) write the hostile inputs first: the fuzz corpus, the SSRF table and the PII corpus are the specification.
- **Always run the checks.** Before declaring done, run `npm run lint` and `npm test` (and `npm run gen:api` when routes changed, the e2e smoke test when a flow changed). Paste the result in the PR. Do not accept "tests should pass".
- **Use Sonnet for subagents.** Any subagent spawned while building this project must use the Sonnet model (`claude-sonnet-5-5`). Use subagents for read-heavy work (searching the spec, reviewing a diff), not for writing migrations.
- **Commit per ticket.** One commit or one small PR per ticket with the message `WF-0NN title`; never mix tickets. Tickets that add migrations merge one at a time.
- **Read the rules first.** Read `.claude/rules/database-migrations.md` before any model or migration change, the agent rules before touching the worker or agent code, and the frontend rules before UI copy or styling.
- **Do not grow the project instructions unprompted.** If something seems worth keeping, say so in one line and let the owner decide. Reference and procedures go in `docs/` or `.claude/skills/`; a procedure that repeats becomes a skill.
- **Safety rules apply in every session.** No secrets in the repo; no fetching of Airbnb, Vrbo or Booking.com pages; no scraper libraries; no ranking by commission; no em dashes in copy. Feed URLs, pasted confirmations and calendar tokens are secrets or personal data: never log them, never put them in analytics.
- **Parallelism.** Run 2 or 3 sessions in parallel only when tickets touch different modules and at most one adds a migration. Use separate branches and merge the migration ticket first. Two tickets that both add an Alembic migration must never run at once; they would create two heads.
- **macOS-bound work.** WF-076 and WF-080 to WF-102 build on a GitHub macOS runner (see knowledge/ios-builds-on-ci.md) and their device checks are owner-pending; do the web and backend parts first and batch the device steps (Month 5 weeks 18 and 19 are the heavy device weeks).
- **When stuck.** If acceptance criteria conflict with a spec, stop and ask; the root README's shared decisions win, then the Phase 1 README, then the topic spec, then this file.
- **Gate reviews.** The gate checklist is `10-quality-security-launch.md` section 7 (7.1 to 7.5), split into `[agent]` items (a session checks them with a command and a pass condition) and `[owner]` items (they become `HUMAN_TASKS.md` rows). The gate for month N runs in the ship session of the prompt after the one that ends the month (prompts 07, 12, 16, 21 and 25) and writes `docs/gates/month-N.md` before the next month starts. If the review shows more than two weeks of slip, run the cut list in section 4 first.
