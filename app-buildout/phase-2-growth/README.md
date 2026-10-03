# Phase 2: growth (months 7 to 12)

Part of the [Hermi build specification](../README.md). Written 2026-09-30. Phase 2 starts only after
[Phase 1](../phase-1-launch/README.md) is live and meets the entry criteria below. Its scope is taken
from the "Not in Phase 1" table of the Phase 1 README (scope is final there) and its content is extracted
from the full specifications ([01](../reference-full-spec/01-product-spec.md) to [10](../reference-full-spec/10-quality-security-launch.md)).

## 1. What Phase 2 is

Phase 1 ships a complete, polished app that already earns from Plus, Trip Pass, credit packs and
affiliate links. Phase 2 is the next six months: it adds the things that turn that app into a growing
business, one self-contained **feature pack** at a time. Each pack says exactly what it adds to the
Phase 1 database, API, screens, billing and admin, so it can be built on top without rereading the full
specs. Nothing in Phase 2 changes the non-negotiable rules
([../README.md](../README.md#non-negotiable-rules)): no banner ads, no ranking by commission, no
fetching of Airbnb, Vrbo or Booking.com pages, sources on every AI fact, account deletion and export on
every tier, secrets only in the environment, no em dashes in UI copy.

What Phase 2 adds:

| Theme | Packs | Why |
|---|---|---|
| More ways to pay | Family plan, Group Trip Pass, Pro | Raises revenue per paying user and gives every kind of traveler a fitting product |
| Win TripIt and Wanderlog users | Email-forward import, flight status alerts, comments, group tools | TripIt users love flight alerts and email forwarding; Wanderlog and Trippy have group tools |
| Earn more without ads | Direct affiliate programs, concierge lane, compensation prompt | Better rates and higher-value lanes that stay disclosed and optional |
| Reach and retention | Native Android, memories, "Year in travel" card | Android invitees, off-season reasons to open the app, a shareable asset |

Competitive context: the competitive analysis is in
[../context/competitive-analysis/README.md](../context/competitive-analysis/README.md) (see its
[win plan](../context/competitive-analysis/win-plan.md)), the business plan's competitor table and positioning in
[../context/business-plan/01-business-plan.md](../context/business-plan/01-business-plan.md) and the pricing rationale in
[../context/business-plan/02-pricing-tiers.md](../context/business-plan/02-pricing-tiers.md). Competitor facts in the packs are marked "reported,
verify" where they come from those files or from search results.

## 2. The packs

| # | Pack | File | Build month | Tickets | Money | Products |
|---|---|---|---|---|---|---|
| 01 | Family plan and households | [01-family-plan.md](01-family-plan.md) | 7 | P2-001 to P2-010 | Subscription | `hermi_family_monthly` $8.99, `hermi_family_annual` $59.99 |
| 02 | Group Trip Pass, polls, manual cost splitting, room-block request | [02-group-trip-pass-and-group-tools.md](02-group-trip-pass-and-group-tools.md) | 7 to 8 | P2-011 to P2-024 | Pass | `hermi_group_trip_pass` $19.99 |
| 03 | Comments | [03-comments.md](03-comments.md) | 8 | P2-025 to P2-031 | None (retention) | none |
| 04 | Email-forward import (plans@hermi.world) | [04-email-forward-import.md](04-email-forward-import.md) | 9 | P2-032 to P2-042 | Switching (credits at the margin) | none |
| 05 | Flight status alerts | [05-flight-status-alerts.md](05-flight-status-alerts.md) | 9 to 10 (bake-off from month 7) | P2-043 to P2-054 | Retention, tier coverage | none |
| 06 | Pro and scheduled agents | [06-pro-and-scheduled-agents.md](06-pro-and-scheduled-agents.md) | 11 (sold in 12 only if the gate is met) | P2-055 to P2-064 | Subscription | `hermi_pro_monthly` $11.99, `hermi_pro_annual` $99.00 |
| 07 | Concierge lane | [07-concierge-lane.md](07-concierge-lane.md) | 11 (legal from month 7) | P2-065 to P2-074 | Agency commission | none |
| 08 | Direct affiliate programs | [08-direct-affiliate-programs.md](08-direct-affiliate-programs.md) | applications month 7, adapters 9 to 10 | P2-075 to P2-083 | Affiliate commission | none |
| 09 | Native Android (and web billing) | [09-native-android.md](09-native-android.md) | 10 to 12 | P2-084 to P2-094, P2-105 | Same ladder on Google Play; web billing through RevenueCat Web Billing | Play equivalents of every Phase 2 product (`_gp` ids), `web_` price keys |
| 10 | After trip and memories | [10-after-trip-and-memories.md](10-after-trip-and-memories.md) | 10 (prompt), 12 (memories, December card) | P2-095 to P2-104 | Affiliate commission (compensation) | none |

Packs are numbered in the order they appear in the Phase 1 "Not in Phase 1" table and in the parent
README, which is not exactly the build order; the build order is in section 3. Phase 1 files also assign a
few smaller items to Phase 2 (early planning features, admin tools, web billing); they are in section 9
(tickets P2-105 to P2-112) rather than in a pack.

## 3. Build order and dependencies

### Order

1. **Family plan (01).** Cheapest revenue lift: schema, pool logic and entitlement algorithm were
   designed together; no new provider cost.
2. **Group Trip Pass and group tools (02).** The friend-group persona is the growth loop; polls and
   splitting make invitees active. Requires Trip Pass binding from Phase 1.
3. **Comments (03).** A week of work that completes the collaboration story (comments on polls and
   expenses need pack 02).
4. **Email-forward import (04).** The switching feature for TripIt users; builds on the Phase 1 booking
   import.
5. **Flight status alerts (05).** The other TripIt favorite; needs flight numbers, which packs 04 and the
   Phase 1 import supply. The provider bake-off runs in the background from month 7 because vendor
   terms and accuracy decide the design.
6. **Direct affiliate programs (08).** Applications start in month 7 (approvals take weeks and need real
   Phase 1 traffic and screenshots); adapters are built as approvals arrive.
7. **Concierge lane (07).** The legal and host agency work starts in month 7; the build follows once the
   regions and registrations are confirmed.
8. **Pro and scheduled agents (06).** Built dark, sold only when the gate is met (mean agent cost of $0.60
   or less over 200 runs, or over 15 percent of Plus payers buying agent-run credits).
9. **Native Android (09).** Mostly packaging, billing and push; scheduled late because it is the first
   cut if capacity is short, and because Google Play has a closed-test clock that can run in the
   background.
10. **After trip and memories (10).** The compensation prompt needs pack 05 data and the AirHelp program
    from pack 08; the Year in travel card is timed for December.

### Dependencies

| Pack | Needs from Phase 1 | Needs from other Phase 2 packs | Unblocks |
|---|---|---|---|
| 01 Family | Entitlements, RevenueCat webhook, credit ledger, paywall engine, invites | none | 06 (Family to Pro cross-grade), 09 (Family on Play) |
| 02 Group | Trips, `people`, roles, Trip Pass binding, `fx_rates`, offline queue, Resend | none (soft: 07 receives room-block requests) | 03 (comments on polls and expenses), 07 (queue), 10 (settle reminder) |
| 03 Comments | Collaboration, activity log, notifications, moderation queue | 02 for poll and expense threads (optional) | none |
| 04 Email | Booking import, redaction, calendar importer, Resend, R2, consents | none | 05 (auto tracking) |
| 05 Flight status | Chosen flights, booking import, notifications, calendar feed, provider pattern | 04 optional | 10 (delay hint), 09 (flight alert channel) |
| 06 Pro | Agent runs, credits, scheduler, flags, RevenueCat, Batch lane | 01 optional | none |
| 07 Concierge | Stays, consents, admin console, support inbox, Resend, R2 | 02 optional (room blocks) | Phase 3 Advisors (host split, advisor orgs) |
| 08 Direct affiliate | `/go`, templates, conversions import, disclosure, admin affiliate screen, traffic numbers | none | 10 (AirHelp), Phase 3 LiteAPI decision (click data) |
| 09 Android | iOS Capacitor shell, RevenueCat, push abstraction, deep links, offline | 01, 02, 06 products exist in the stores; 05 and 03 use the push layer | none |
| 10 After trip | Chosen flights, share links, R2 uploads, archive, affiliate redirect | 05 and 08 recommended, 02 for the settle reminder | Phase 3 printed trip books (memories) |

```
Phase 1 live (entry gate)
  |
  +-- 01 Family ----------------------------------------------+
  +-- 02 Group tools and Group Trip Pass --- 03 Comments       |
  |        \                                                   |
  |         +------ 07 Concierge (room blocks join its queue)  |
  +-- 04 Email forward --- 05 Flight status --- 10 After trip --+--- 09 Android (last)
  +-- 08 Direct affiliate (apply month 7) ---------- 10 (AirHelp)
  +-- 06 Pro (built dark, gated by measured cost) ------------+
```

### Long-lead items (start in month 7, none of them is engineering)

| Item | Pack | Why it starts early |
|---|---|---|
| Affiliate application packets and submissions | 08 | Approvals take weeks; they need live traffic and screenshots |
| Host agency selection, seller-of-travel counsel review, E&O insurance | 07 | Nothing can launch without them; registrations take time |
| Flight status provider bake-off and terms review | 05 | Vendor terms and accuracy decide the design and the budget |
| Google Play developer account and closed test | 09 | New personal accounts reported to need 12 opted-in testers for 14 days before production access |
| Privacy policy, App Privacy label and Play data safety updates | 04, 05, 09, 10 | New data types: forwarded emails, flight numbers, photos |
| Gate measurement setup for Pro (cost per run report, credit pack share) | 06 | The decision needs 200 measured runs |

## 4. Shared conventions (every pack follows these)

1. **Definition of done** (from [09 section 5](../reference-full-spec/09-build-roadmap.md), applied to every ticket):
   the change is on a branch, reviewed against the ticket's acceptance list and merged through a pull
   request, one commit per ticket with the message `P2-NNN title`; `npm run lint` and `npm test` pass
   locally and in CI and the tests named in the ticket exist and fail without the change; if any route or
   schema changed, `npm run gen:api` was run and the regenerated `apps/web/src/lib/api/schema.d.ts` is
   committed; if any model or migration changed, the migration follows
   `.claude/rules/database-migrations.md` (expand and contract, one head, tested from empty and from the
   previous revision); new environment variables are documented in `.env.example` and no secrets are in
   the repo; UI copy follows the copy rules (sentence case, plain verbs, no em dashes) and the Hermi
   design tokens; the work respects the non-negotiable rules.
2. **Sizes.** S is about 2 hours, M half a day, L a day (never larger; split instead). The 112 tickets
   total roughly 480 hours of build at those sizes; with support, launch work and bug fixing plan on
   about half of each month for building (one developer with Claude Code at 25 to 35 focused hours a
   week).
3. **Migrations.** Phase 2 revisions continue after Phase 1's last revision, `0015_seed`
   ([Phase 1 03 section 10](../phase-1-launch/03-database-schema.md)), and follow the same expand and contract
   rules. The numbers below are labels: Alembic keeps exactly one head, revisions are numbered in merge order,
   and two tickets that add migrations are never built in parallel. A table added after the RLS revision
   carries its own `GRANT`, `ENABLE ROW LEVEL SECURITY` and policies in the same migration, and is added to the
   automated cross-tenant suite. Phase 1 dropped every Phase 2 object on purpose
   ([Phase 1 03 section 1.1](../phase-1-launch/03-database-schema.md)) and lists what each pack adds in its
   section 14; the packs create them and reuse the definitions from the full
   [03](../reference-full-spec/03-database-schema.md).

   | Label | Pack | Creates or changes |
   |---|---|---|
   | `0016_households_family` | 01 | `households`, `household_members`, household columns, replacement `credit_balances` and `reserve_credits()`, Family plan and products |
   | `0017_group_tools`, `0018_room_block_requests` | 02 | `polls`, `poll_votes`, `expenses`, `expense_shares`, `settlements`, `room_block_requests`, pass upgrade column and constraints, limit keys, Group Trip Pass plan and product, consent kind |
   | `0019_comments` | 03 | `comments`, `comment_reads`, `comment_mentions`, `trips.comments_enabled`, report target |
   | `0020_inbound_email` | 04 | `user_email_addresses`, `forwarding_addresses`, `inbound_emails`, `trip_imports` source and column, webhook provider, consent kind |
   | `0021_flight_status` | 05 | `tracked_flights`, `flight_status_events`, `flight_status_subscriptions`, `chosen_flights.flight_numbers`, `itinerary_items.flight_number`, tier limits |
   | `0022_pro_routines` | 06 | `routines`, `runs` routine columns, run kinds and triggers, Pro plan and dark products |
   | `0023_concierge` | 07 | `concierge_requests`, `concierge_messages`, `concierge_commission_lines`, flags, support category |
   | `0024_direct_affiliate` | 08 | network and provider checks, direct program seeds, `affiliate_applications`, template constraint |
   | `0025_android` | 09 | store checks (`google`), `devices.push_provider`, Play and web product rows |
   | `0026_after_trip` | 10 | `trip_after_prompts`, `trip_reviews`, `trip_memories`, `share_cards`, `trips.completed_at`, share link kind, Compensair seed |

   Swapping a named check constraint (webhook providers, consent kinds, store values, notification kinds,
   network values) always restates the full current list plus the new values, so whichever pack merges
   second keeps what the first added. Phase 1 has a `notifications` outbox and inbox with a named check on
   `kind`; each pack lists the kinds it adds (comments, group tools, flight status, routines, concierge,
   after trip) and its notification ticket performs the swap. Plan limit keys that Phase 1 dropped are added
   with `UPDATE plans SET limits = limits || ...` and the merge treats a missing key as "not granted".
4. **Flags and kill switches.** Every pack ships behind a flag or a per-program switch, turned on for
   staff first, then 10 percent, then 100 percent. New switches: `email.inbound` (04),
   `provider.flight_status` (05), `ai.routines` (06), `memories.uploads` (10), `comments.write` (03); the
   Phase 1 switches `import.all`, `ai.import`, `ai.batch` and `affiliate.<code>` also apply to the new work.
   Seeds are idempotent `ON CONFLICT DO NOTHING`.
5. **Plans and limits.** Limits are `plans.limits` keys (numbers and booleans only, merged best-of per
   trip). New keys in Phase 2: `flight_status_legs`, `flight_status_realtime` (05),
   `memory_photos_per_trip` (10). Prices and limits are `UPDATE`s in the admin console (audited), not
   migrations. The client never decides; it reads `GET /me/entitlements` and `TripOut.capabilities`.
6. **Analytics.** Events are defined once in `packages/shared/src/events.ts`, snake_case and past tense,
   with enums and buckets only and no PII (no email, names, free text, trip titles, place names, notes or
   photo captions). The server rejects unknown names and properties. Every pack lists its new events.
7. **Paywall triggers.** Phase 2 turns on `household`, `group_tools`, `group_pass` and `routine` (after
   Pro launches) from the Phase 1 paywall table and adds two soft, client-initiated reasons
   (`flight_status_limit`, `memory_photo_limit`). All follow the paywall rules: server decides, one per
   session, "Not now" always visible, dismiss mutes 7 days, no countdowns or invented scarcity, no
   "unlimited" claims, none before first value, none beside an affiliate card, none during a flight
   disruption.
8. **App Store products.** New products are created in App Store Connect and RevenueCat with localized
   metadata and a paywall review screenshot, and are submitted with an app version for their first
   review. Product ids are in the packs; the subscription group `hermi_membership` holds Pro (level 1),
   Family (level 2) and Plus (level 3). Apple Family Sharing stays off. Google Play ids carry a `_gp`
   suffix (pack 09).
9. **Tests.** Each pack lists its tests. Always: tenant isolation for every new table, idempotent
   webhooks and jobs, RLS policies, accessibility checks (axe, VoiceOver and, from pack 09, TalkBack),
   and a sandbox purchase matrix rerun for any pack that adds a product.
10. **Privacy.** Packs 04, 05, 09 and 10 add data types (forwarded email, flight numbers, FCM tokens,
    photos). Each has a privacy policy, App Privacy label and Play data safety update ticket, an export
    step and an account deletion step. Nothing new is sent to Anthropic beyond what each pack states.

## 5. Entry criteria

Do not start Phase 2 feature packs until Phase 1 has been live long enough to measure. Thresholds marked
"suggested" are starting points for you to set; the targets come from the business plan and the full
roadmap ([09 section 1](../reference-full-spec/09-build-roadmap.md): D30 retention at least 15 percent, free-to-paid
conversion 3 to 5 percent, monthly subscriber churn under 8 percent, LTV to CAC above 3, all "targets,
not gates"; and the kill rule at month 9 after launch).

### Must be true (the gate)

| Area | Criterion |
|---|---|
| Live | Approved and live on the App Store and the web for at least 4 weeks; the Phase 1 exit criteria are met (crash-free sessions at least 99.5 percent, API error rate under 1 percent, no P0 in the first 72 hours after release) |
| Stability | No open P0 or P1 for 14 days; tenant-isolation suite green on the latest release; restore-from-backup drill done; spend alerts drilled |
| Money works | Real purchases flow end to end for Plus, Trip Pass and credit packs; RevenueCat reconcile clean for 7 days; at least one refund handled with clawback; credit ledger reconciliation shows zero mismatches |
| AI economics | Agent run cost measured over at least 50 runs (Phase 1 requirement) with the mean recorded; no account above its ceiling; global daily AI spend within the forecast |
| Support | Support inbox answered within 2 business days; macros live |

### Metrics (read from the admin overview and PostHog)

| Metric | Business plan target | Minimum to start Phase 2 (suggested) |
|---|---|---|
| Monthly active users | tracked | At least 1,000 over the last 30 days (Skyscanner's reported bar is 5,000 monthly uniques, so its application may wait) |
| Paying users (subscribers plus pass holders) as a share of monthly users | 3 to 5 percent free-to-paid | At least 1 percent (the kill rule's own floor), and a count of at least 50 paying users |
| D30 retention of new users | at least 15 percent | At least 10 percent |
| Monthly subscriber churn | under 8 percent | Under 12 percent |
| Affiliate income, annualized per monthly user | $0.10, $0.60, $1.50 in the scenarios; kill rule under $0.20 at month 9 | Clicks and conversions tracked with unmatched share under 10 percent; annualized figure visible and trending toward $0.20 |
| Activation (first itinerary item within 24 hours of sign-up) | tracked | Reported; no threshold |
| Refund rate on purchases | low | Under 5 percent of purchases |

### If the gate is not met

Do not start the revenue-dependent packs (Pro, concierge, Android). Work on retention and conversion first
(onboarding, paywall experiments, empty states). The no-regret items can still start because they do not
depend on monetization: pack 08 applications (they need traffic and stability, not revenue), pack 03
comments and the flight status bake-off. If the kill rule is already at risk (under 1 percent paying and
under $0.20 annualized affiliate income), hold all other Phase 2 spending and decide with the data.

## 6. Month plan

Months continue the project numbering (month 7 is the first month after the Phase 1 launch month).

| Month | Build | Long-lead and parallel work | Exit for the month |
|---|---|---|---|
| 7 | Entry gate review (first 2 weeks). Pack 01 Family (P2-001 to P2-010). Start pack 02: tables, gates, polls API (P2-011 to P2-013) | Start P2-043 provider bake-off, P2-065 legal and host agency, P2-075 and P2-076 affiliate packets and applications; privacy policy drafts | Family sold in the sandbox matrix and submitted with an app update; applications submitted |
| 8 | Finish pack 02 (P2-014 to P2-024); pack 03 Comments (P2-025 to P2-031) | Bake-off ends with a provider decision; respond to affiliate network questions | Group Trip Pass live, polls and splitting work on every tier rule; comments live behind a flag |
| 9 | Pack 04 Email forward (P2-032 to P2-042); start pack 05 schema and lookup (P2-044 to P2-046); first approved affiliate programs get adapters (P2-077) | Play Console enrollment and closed-test recruiting (P2-084); inbound provider DNS plan | Forwarding works end to end for staff, AI fallback inside eval targets |
| 10 | Finish pack 05 (P2-047 to P2-054); affiliate adapters and templates as approved (P2-078 to P2-083); pack 10 prompt, claim sheet and wrap-up (P2-095 to P2-097); start Android shell, push and links (P2-085, P2-088, P2-089) | Counsel confirms concierge regions and host terms | Flight status staged to 100 percent within budget; direct programs converting or documented |
| 11 | Pack 07 Concierge (P2-066 to P2-074) if legal is clear; pack 06 Pro built dark (P2-055 to P2-061, P2-063); continue Android: billing, server support, UX, tests, closed test running (P2-086, P2-087, P2-090 to P2-093) | Gate measurement for Pro continues; first concierge bookings | Concierge live in at least one region; Android in closed test with 12 or more active testers |
| 12 | Finish Android and release (P2-094); pack 10 memories and Year in travel (P2-098 to P2-104, card live 1 December); Pro launch only if the gate is met (P2-062, P2-064); Phase 2 review | Kill-rule trend report | Android live on Google Play; Year in travel card live; Phase 2 exit review |

Optional items from section 9 (P2-106 to P2-112) are placed where they fit: P2-106 (paste your group chat)
in month 8 as the first post-launch planning feature, P2-107 (repair-a-day) in month 10 after flight status
exists, P2-108 and P2-112 (read-only impersonation, comping) in month 9 when support volume grows, P2-109
(finance reports) and P2-110 (experiments) in month 12 when there is data to read, and P2-111 (win-back and
lifecycle messages) in month 12. P2-105 (web billing) belongs with the Android billing work in month 11.

Cut line if capacity is short (cut in this order, each leaves the product coherent): memories beyond the
compensation prompt and wrap-up, Android, mentions (P2-031), Pro launch, concierge. Never cut tests,
privacy work or the tenant-isolation suite.

## 7. Exit criteria

Phase 2 is done when all of these are true at the end of month 12:

| Area | Criterion |
|---|---|
| Delivery | Each pack is shipped or explicitly deferred with a reason and a date; acceptance criteria of shipped packs pass; flags are at 100 percent or removed |
| Products | Family and Group Trip Pass are on sale on iOS (and Android); Pro is either launched with its gate numbers recorded or still dark with the decision recorded; the sandbox purchase matrix is rerun for every new product |
| Quality | Crash-free sessions at least 99.5 percent on iOS and Android, API error rate under 1 percent, no open P0; tenant-isolation suite covers every new table; security review done for the inbound email endpoint, uploads and the Android build; privacy policy, App Privacy label and Play data safety form match the data collected |
| Growth metrics (targets, not gates) | D30 retention at least 15 percent; free-to-paid conversion 3 to 5 percent; monthly subscriber churn under 8 percent; LTV to CAC above 3 |
| Revenue | Annualized affiliate income per monthly user measured and at or above the kill-rule floor of $0.20 (or a written plan if not); at least 2 of the 5 direct programs approved and converting, or documented reasons; Family pooled spend not near its ceiling for more than 25 percent of households; first 10 concierge bookings completed with founder hours per booking recorded; flight status spend within its monthly budget |
| Engagement | Flight status and email import adoption reported (users with a tracked leg or a forwarded booking, and their D30); Year in travel share rate recorded |
| Kill-rule checkpoint | The formal decision is at month 9 after launch (project month 15); Phase 2 produces the trend report for it: paying share, annualized affiliate income per monthly user, cost per active user |
| Phase 3 readiness | Data for each Phase 3 decision exists: Group Trip Pass sales and expense usage (Stripe group payments), concierge ask and completion rates (Hermi for Advisors), memories usage (printed trip books), lodging click-to-booking and stay comparison reach (LiteAPI), partner guide demand |

## 8. Risks across Phase 2

| Risk | Mitigation |
|---|---|
| Solo capacity (112 tickets, several long-lead items) | Cut line in section 6; Android and memories are first to cut; keep half of each month for support and fixes |
| Scope creep in collaboration features | Comments are plain text with one reply level; mentions are optional; no real-time or chat |
| Cost growth (flight status provider, photo storage, agent runs) | Budgets, per-leg caps, tier limits, kill switches, measured gate for Pro, cost panels in admin |
| Legal and policy (seller of travel, inbound email privacy, Google Play and Apple policies, photos of children) | Region gates, counsel sign-off before concierge, consent flows, retention limits, re-read guidelines before each submission |
| Affiliate approvals slow or declined | Apply early, Travelpayouts and Stay22 stay active, report measured EPC |
| Paywall fatigue as products multiply | One paywall per session, mutes, server-side decisions, soft reasons only for new limits |
| Migration conflicts | One head, merge-order numbering, no parallel migration tickets |
| Two stores, two sets of billing states | Server is the source of truth, best-of entitlements, idempotent grants, sandbox matrices |

## 9. Ticket index

Tickets are numbered P2-001 to P2-112: P2-001 to P2-104 in pack order, then P2-105 (web billing, with pack 09)
and P2-106 to P2-112 (other Phase 2 work, below). "Needs" lists Phase 1 capabilities or earlier
tickets. Format and definition of done are in section 4.

### Pack 01: Family plan ([file](01-family-plan.md))

- P2-001 Household schema and RLS [M]
- P2-002 Household API [M]
- P2-003 Entitlement resolver household branch [M]
- P2-004 Pooled credits and monthly grant [M]
- P2-005 Family purchase lifecycle [L]
- P2-006 Churn guard and abuse controls [S]
- P2-007 Household UI [L]
- P2-008 Family paywall and plan comparison [S]
- P2-009 Admin household tools and alerts [S]
- P2-010 App Store products, purchase matrix and review assets [M]

### Pack 02: Group Trip Pass and group tools ([file](02-group-trip-pass-and-group-tools.md))

- P2-011 Group tables, RLS and seeds [L]
- P2-012 Capability flags and gates [M]
- P2-013 Polls API [M]
- P2-014 Poll UI and reminders [M]
- P2-015 Expenses and FX [M]
- P2-016 Balances and minimal transfers [M]
- P2-017 Settlements, confirm and write-off [M]
- P2-018 Group screens: People, Expenses, Settle up [L]
- P2-019 Offline expenses [M]
- P2-020 Group Trip Pass product, bind and upgrade [M]
- P2-021 Room-block request [M]
- P2-022 Group paywalls [S]
- P2-023 Admin room blocks, pass tools and alerts [S]
- P2-024 Purchase matrix and review assets [S]

### Pack 03: Comments ([file](03-comments.md))

- P2-025 Comments schema, RLS and flag [M]
- P2-026 Comments API [M]
- P2-027 Thread UI and badges [L]
- P2-028 Notifications and digest integration [M]
- P2-029 Moderation and admin [S]
- P2-030 Offline, export, deletion and privacy checks [M]
- P2-031 Mentions (optional, cut first) [M]

### Pack 04: Email-forward import ([file](04-email-forward-import.md))

- P2-032 Inbound provider decision and receiving endpoint [M]
- P2-033 Schema, RLS and retention [M]
- P2-034 Sender verification and forwarding addresses [M]
- P2-035 Authentication, limits and scanning [M]
- P2-036 Structured and ICS parsing [L]
- P2-037 AI fallback with redaction [M]
- P2-038 Trip matching and duplicate handling [M]
- P2-039 Bookings to review UI [L]
- P2-040 Onboarding and switcher path [S]
- P2-041 Admin health, kill switch and eval set [S]
- P2-042 Privacy, policy and load tests [S]

### Pack 05: Flight status alerts ([file](05-flight-status-alerts.md))

- P2-043 Provider bake-off and interface [M, starts month 7]
- P2-044 Schema, RLS, settings and flags [M]
- P2-045 Lookup and tracked flights API [M]
- P2-046 Auto tracking from chosen flights, imports and emails [M]
- P2-047 Poll scheduler and cost controls [L]
- P2-048 Webhook receiver and event detection [M]
- P2-049 Alert delivery and preferences [M]
- P2-050 Flight status UI [L]
- P2-051 Calendar feed and presentation updates [S]
- P2-052 Limits and soft paywall [S]
- P2-053 Admin panel, alerts and macros [S]
- P2-054 Attribution, privacy and launch checks [S]

### Pack 06: Pro and scheduled agents ([file](06-pro-and-scheduled-agents.md))

- P2-055 Routines schema additions and plan seed [S]
- P2-056 Routines API and validation [M]
- P2-057 Scheduler activation and pause rules [L]
- P2-058 Scan lane (Batch) [L]
- P2-059 Priority queue with aging and Pro concurrency [M]
- P2-060 Digests and notifications [M]
- P2-061 Routines UI and non-Pro sample [L]
- P2-062 Pro plan purchase flow, rollover and lifecycle [L]
- P2-063 Gate tooling and admin [M]
- P2-064 Pro launch checklist [S]

### Pack 07: Concierge lane ([file](07-concierge-lane.md))

- P2-065 Legal and host agency setup [M, starts month 7, no code]
- P2-066 Schema, RLS, flags and settings [M]
- P2-067 Concierge API, availability and messages [M]
- P2-068 Request form, consent sheet and entry cards [L]
- P2-069 Status timeline, thread and notifications [M]
- P2-070 Admin concierge queue [L]
- P2-071 Commission tracking and import [M]
- P2-072 Capacity, SLA and alerts [S]
- P2-073 Privacy, deletion and retention [S]
- P2-074 Review notes, staged launch and first bookings [S]

### Pack 08: Direct affiliate programs ([file](08-direct-affiliate-programs.md))

- P2-075 Application packets and terms review [S, starts month 7]
- P2-076 Applications tracker and submission [S]
- P2-077 Impact adapter and conversion import [L]
- P2-078 Expedia Group, Vrbo and Hotels.com deep links [M]
- P2-079 Booking.com direct [M]
- P2-080 Skyscanner links and licensed-fare evaluation [M]
- P2-081 Airalo eSIM [S]
- P2-082 GetYourGuide direct and tours dedupe [M]
- P2-083 Reporting, experiments and runbook [M]

### Pack 09: Native Android ([file](09-native-android.md))

- P2-084 Play Console, compliance and closed-test clock [S, starts month 9 or 10]
- P2-085 Capacitor Android project and build pipeline [M]
- P2-086 Play Billing through RevenueCat [L]
- P2-087 Server support for the Google store [M]
- P2-088 Push with FCM [M]
- P2-089 App Links and invite flows [M]
- P2-090 Android UX adaptations [M]
- P2-091 Offline and performance parity [M]
- P2-092 Device trust and security hardening [S]
- P2-093 Test matrix and Play sandbox runs [M]
- P2-094 Listing, review and staged release [L]
- P2-105 Web billing with RevenueCat Web Billing [L]

### Pack 10: After trip and memories ([file](10-after-trip-and-memories.md))

- P2-095 After-trip prompts engine and delay prompt [M]
- P2-096 Flight status link and partner wiring [S]
- P2-097 Trip reviews storage and settle reminder [M]
- P2-098 Memories schema, storage and photo pipeline [L]
- P2-099 Memories UI and recap [L]
- P2-100 Memory share pages [M]
- P2-101 Year in travel statistics [M]
- P2-102 Year card renderer and sharing [L]
- P2-103 Privacy, export, deletion and admin [M]
- P2-104 Launch checks and December rollout [S]

### Other Phase 2 work named in the Phase 1 files

These are not among the ten packs you asked for. They come from the Phase 1 README and roadmap, which
assign them to Phase 2, and from the competitive win plan. They are short tickets here rather than packs;
tell me if you would rather move any of them out of Phase 2. Sizes and order of build are in the month plan.

#### P2-106 "Paste your group chat" to draft a plan [M, month 8, needs Phase 1 `draft_trip`, evidence rules, consent]
- Source: Phase 1 README ("Early Phase 2: paste your group chat to draft a plan, answers Trippy") and
  [win plan F6](../context/competitive-analysis/win-plan.md).
- Description: paste or share-sheet exported chat text into a `draft_trip`-style action (4 credits, Sonnet) that
  lists dates mentioned, candidate places, stays with links (kept as plain text, never fetched), who said what
  about each (first names only) and a "still undecided" list; the owner accepts items into the trip. Names are
  stripped to first names before the model call (06 section 12.2), the raw chat text is not stored after
  extraction, the AI consent and the sources-on-every-fact rule apply, and the limit is 12,000 characters.
- Accept: nothing is saved before the owner accepts items; raw text is absent from every table and log; evals
  cover injection inside chats; privacy copy reviewed.
- Tests: extraction evals, redaction, credit settle and refund, privacy assertions.

#### P2-107 Repair-a-day [M, month 10, needs Phase 1 itinerary and places data, pack 05 for the proactive part]
- Source: Phase 1 README ("repair-a-day when plans change") and [win plan F8](../context/competitive-analysis/win-plan.md).
- Description: on any day, "Repair this day" shows the reason (for example "closed Mondays, source, checked
  date"), proposes 2 swaps with travel times, and applies only after the user accepts; one tap undoes it;
  1 credit (`draft_day` price). The proactive version prompts on the trip when a tracked flight changes
  (pack 05 events) and never pushes for it.
- Accept: no change without acceptance; every proposed swap cites a source and date; undo restores the day
  exactly.
- Tests: swap logic, undo, credit settle, proactive prompt from a fixture flight change.

#### P2-108 Admin read-only impersonation with consent [M, month 9, needs Phase 1 admin console and audit log]
- Source: [08 section 6.2](../reference-full-spec/08-admin-control-center.md); Phase 1 roadmap section 7 moves it to Phase 2.
- Description: support asks the user for consent, the API mints a 15 minute token bound to the admin and the
  user that rejects every non-GET request and hides secrets, payment details and note bodies, a banner with a
  countdown, every page fetch audited with `impersonation_id`, and "Support access log" in the user's
  Settings. No override exists, including for the owner.
- Accept: no impersonation without consent; token cannot write; audit rows complete.

#### P2-109 Admin finance reports and settings [M, month 12, needs Phase 1 admin console]
- Source: [08 sections 6.15 and 6.16](../reference-full-spec/08-admin-control-center.md); Phase 1 roadmap section 7.
- Description: monthly revenue by stream (subscriptions by tier, passes, credit packs, affiliate by network,
  concierge commission, later streams), net of store fees, costs by provider, CSV export (audited), and a
  Settings screen for price display rows, credit prices per action and the `setting_` flags, all with reasons
  and history.
- Accept: CSV exports audited; engineer role sees no fee lines; settings changes need step-up auth.

#### P2-110 Admin experiments and paywall experiments [M, month 12, needs Phase 1 flags screen and paywall engine]
- Source: [08 section 6.6](../reference-full-spec/08-admin-control-center.md), [07 section 6.7](../reference-full-spec/07-monetization-spec.md);
  Phase 1 roadmap section 7 (admin experiments) and WF-113 part.
- Description: experiment rows (`exp_` flags) with hypothesis, variants, allocation, primary metric and
  guardrails, sticky server-side assignment, Bayesian results table from PostHog and `store_transactions`,
  minimum runtime and sample, one experiment per surface, instant kill, and the seven paywall experiments in
  07 section 6.7 (price tests use separate product ids and RevenueCat offerings).
- Accept: no experiment can touch disclosure or ranking keys; assignment is sticky; guardrails shown.

#### P2-111 Win-back and lifecycle messages [M, month 12, needs Phase 1 RevenueCat webhook, notifications]
- Source: [07 section 7.10](../reference-full-spec/07-monetization-spec.md); Phase 1 roadmap section 7 (WF-113 part).
- Description: a one-question cancellation survey when `auto_renew` turns false, a win-back offer 7 days after
  expiry (an Apple promotional or win-back offer on the same product, shown once and clearly priced, configured
  in App Store Connect and delivered through RevenueCat), and a lifecycle email "Planning another trip?" to
  lapsed users with a trip in the next 120 days (opt-in, one-click unsubscribe, never a push).
- Accept: no dark patterns; frequency caps hold; opt-in respected.

#### P2-112 Comp subscriptions and Phase 2 admin user tools [S, month 9, needs Phase 1 admin users screen]
- Source: [08 section 3](../reference-full-spec/08-admin-control-center.md) permission matrix ("Comp a subscription: engineer up to
  90 days, owner up to 12 months; `plus` and `family` only"); Phase 1 roadmap section 7.
- Description: comp a subscription (an `entitlements` row with `source = 'comp'` and `valid_until`), with the
  household created for a comped Family, audited with a reason; the household, routines and pass panels from
  packs 01, 02 and 06 appear in the user detail.
- Accept: comps expire on time; every comp audited; limits by role enforced.

Not built in Phase 2 (named in the win plan as Phase 2 candidates, to be decided with data at the month 9
review): the "what is still open" list, screenshot and link import, offline map tiles, Live Activities and
widgets, a Hermi MCP server, documents attached to items, and an "export to ChatGPT" prompt.

## 10. Sources and notes

- Full specifications (the verbatim source for definitions reused in the packs):
  [01 product spec](../reference-full-spec/01-product-spec.md), [02 architecture](../reference-full-spec/02-architecture.md),
  [03 database schema](../reference-full-spec/03-database-schema.md), [04 API spec](../reference-full-spec/04-api-spec.md),
  [05 UI and UX](../reference-full-spec/05-ui-ux-spec.md), [06 AI agents](../reference-full-spec/06-ai-agents-spec.md),
  [07 monetization](../reference-full-spec/07-monetization-spec.md), [08 admin](../reference-full-spec/08-admin-control-center.md),
  [09 roadmap](../reference-full-spec/09-build-roadmap.md), [10 quality, security and launch](../reference-full-spec/10-quality-security-launch.md).
- Phase 1 files that the packs build on (same names as the full specs, scoped to Phase 1):
  [Phase 1 README](../phase-1-launch/README.md), and in the same folder
  [01](../phase-1-launch/01-product-spec.md), [02](../phase-1-launch/02-architecture.md),
  [03](../phase-1-launch/03-database-schema.md), [04](../phase-1-launch/04-api-spec.md),
  [05](../phase-1-launch/05-ui-ux-spec.md), [06](../phase-1-launch/06-ai-agents-spec.md),
  [07](../phase-1-launch/07-monetization-spec.md), [08](../phase-1-launch/08-admin-control-center.md),
  [09](../phase-1-launch/09-build-roadmap.md) and
  [10](../phase-1-launch/10-quality-security-launch.md). Where a Phase 1 file does not define something a
  pack needs, the pack creates it with `IF NOT EXISTS` statements or says so.
- Business reasoning: [../context/business-plan/01-business-plan.md](../context/business-plan/01-business-plan.md),
  [../context/business-plan/02-pricing-tiers.md](../context/business-plan/02-pricing-tiers.md),
  [../context/business-plan/08-affiliate-revenue.md](../context/business-plan/08-affiliate-revenue.md),
  [../context/business-plan/09-revenue-expansion.md](../context/business-plan/09-revenue-expansion.md).
- Differences found between the full specs, the Phase 1 files and the Phase 3 packs, which the packs resolve (so the builder is not surprised):
  the full specs call Stripe group payments "Phase 4" while the README scope says Phase 3 (Phase 3 is
  used here); the full roadmap sells Family and the Group Trip Pass at launch while the Phase 1 scope puts
  them in Phase 2 (Phase 2 is used here); leftover cents in splits go to the payer in 04 and by traveler
  order in 01 (traveler order is used); the Impact template needs `u=` but the full template check
  constraint blocks it (relaxed for deep links only, pack 08); the Impact sub-id fields are empty in the
  03 seed (filled in pack 08); the concierge and room-block tables reference `advisor_orgs` and
  `payment_collections` from Phase 3 (plain columns until then, packs 02 and 07; the Phase 3 advisors pack adds
  `concierge_requests.advisor_org_id`, so pack 07 does not create it); Phase 1 says web billing arrives with Android
  in Phase 2 while its 04 and 01 files describe web purchases through RevenueCat Web Billing (pack 09 builds it,
  ticket P2-105); Phase 1 already builds the wrap-up card and archive offer (F-AFT-2) but has no table for the
  rating (pack 10 adds `trip_reviews`); the Phase 3 Stripe pack expects Phase 2 to leave `settlements` with the
  `stripe` method, the `disputed` status, a plain `collection_id` column and the `group_payments` flag created off
  (pack 02 does exactly that); the Phase 1 working names `flight_status_subscriptions`, `flight_status_events`,
  `trip_memories`, `share_cards`, `forwarding_addresses`, `inbound_emails` and `provider.flight_status` are used as
  given.
- Statements about competitors, vendors, commission rates, store policies and prices are "reported,
  verify" unless a pack says otherwise; search results used for packs 05 and 09 are listed in those packs.
