# Tiers, pricing, and AI credits

Part of the [business plan](README.md). The decisions of record in the README override anything here.

Date: 2026-09-30.
Scope: feature-to-tier matrix, tier limits, the AI credits system, unit economics, guardrails, launch configuration, paywall moments. This file is the pricing source of truth; the AI cost build-up is in [03-ai-features-and-costs.md](03-ai-features-and-costs.md). The product is named Hermi; section 1 inventories the local Trip Planner it grows from.

Data caveats:
- SerpApi pricing could not be verified on 2026-09-30 (serpapi.com was blocked by the research sandbox's egress proxy). The plan ladder used is from memory: about $25 per 1,000 searches, $75 per 5,000, $150 per 15,000, $275 per 30,000, which is 0.9 to 2.5 cents per search. The model uses **1.5 cents** and treats it as unverified. Re-check before launch.
- Geoapify paid pricing, Travelpayouts commission rates, and infra costs are estimates.
- Claude prices used: Sonnet 5.5 $2 in / $10 out per 1M tokens, Haiku 4.5 $1 / $5, web search $10 per 1,000.
- Competitor prices (Wanderlog Pro $39.99 a year, TripIt Pro $49, Layla Premium $49 to $49.99, Splitwise Pro $39.99) come from third-party pages checked on 2026-09-30, not vendor pages. The RevenueCat 2026 benchmarks (AI apps: median download-to-paid 2.4% at day 35, about 41% more revenue per payer, about 30% faster churn, 12-month annual retention 21.1% against 30.7% for non-AI apps) come from summaries of the report. Verify both before quoting them outside this plan.
- The taster inputs (30% of new Free users redeem it, 35% of taster runs served from the shared cache) are assumptions, not measurements.

## 1. What the app does today (feature inventory)

Every row is something a user can do today, taken from the routers in `backend/tripplanner/api/`, the services, the frontend routes, and the app README.

| Area | Feature (source) | Cost driver | Nature |
|---|---|---|---|
| Trips | Create, edit, delete trips; multiple destinations; home currency (`trips.py`, `settings.py`) | DB only | Core |
| Trips | Destination lookup and autocomplete (`geo.py`, Geoapify) | Geoapify call | API |
| Trips | Destination summary, photo, local time, money info (`trips.py refresh-info`, Wikipedia) | Free API | API |
| Travelers | Traveler profiles with home airports (`people.py`) | DB only | Core |
| Flights | Airport search and nearby airports (`geo.py`) | Local dataset | Free |
| Flights | Routes: up to 4 airports per side, departure window, nights or return window (`flights.py`) | DB only | Core |
| Flights | Cached fare calendars (Travelpayouts/Aviasales), per adult, economy | Free API | API, cheap |
| Flights | Live Google Flights checks on a schedule, default twice a day (`serpapi_budget.py`, `search_planner.py`) | SerpApi, about $0.015 per search | API, costly |
| Flights | Price history chart, date grid, cheapest options, sort and filters, cheapest by trip length (`flights.py`) | DB only | Core |
| Flights | Choose a flight (sets trip dates), compare price movement vs chosen flight | DB only | Core |
| Itinerary | Day cards, drag-and-drop day calendar, ideas list, move between days, optimistic-lock conflict handling (`itinerary.py`) | DB only | Core |
| Places | Places search by category or name, map, hours, website (`places.py`, Geoapify, cached 1 week) | Geoapify call | API |
| Places | Wikipedia place summary (`places.py /wiki`) | Free API | API |
| Lodging | Shortlist, manual add, bookmarklet import, link preview, hearts, status, compare 2 to 4 (`lodging.py`) | DB only (preview fetches one page) | Core |
| Lodging | Rental search via Google Hotels partners (`search-rentals`, cached 12h) | SerpApi search | API, costly |
| Lodging | Price per night and per person, FX conversion (ECB rates, `fx.py`) | Free API | API |
| Presentation | Full-screen slide mode, keyboard and swipe, print to PDF (`presentation.py`) | DB only | Core |
| Agents | Flight-search agent routine (Claude, web search and fetch, 40 turns today) (`routines.py`, `runs.py`) | $0.50 to $1.50 per run | AI, costly |
| Agents | Research agent routine, notes with sources, shown as "Found by agents" (`runs.py /notes`) | $0.50 to $1.50 per run | AI, costly |
| Agents | Run log, stop run, rejected-items view, ingest API with evidence rules (`agent.py`, `agent_ingest.py`) | DB only | Trust feature |
| Ops | Backups, restore, setup checklist, passcode login, LAN and Tailscale sharing | n/a | Local-only, replaced by cloud accounts |

Features that exist only because the app is local (backups, passcode, setup checklist, LAN and Tailscale sharing, `.env` keys, SerpApi budget page) disappear or become server internals. Users get "your data is always synced" and "export your trip" instead. Export stays free on every tier.

New features the product needs that do not exist yet (all cheap or gated): accounts (see [04-users-and-accounts.md](04-users-and-accounts.md)), collaboration and invites, push alerts, itinerary drafting (AI), a quick "explain" assistant (Haiku), subscription state, households for the Family plan, and the one-time agent taster.

## 2. Principles

1. **Everything cheap stays free.** DB-only features and cached API data cost almost nothing, so they are the hook. Never gate the itinerary calendar, lodging shortlist, or presentation mode behind money. They are the reason people stay and share.
2. **Gate on marginal cost, not on features that feel premium.** Three things cost real money per use: live SerpApi searches, Sonnet calls with web search, and agent runs. Everything else is nearly free.
3. **Meter the expensive things with one unit (credits), and put a hard dollar ceiling on every account.** Users see credits; finance sees dollars.
4. **Travel is episodic.** People plan 1 to 3 trips a year, intensely for 4 to 12 weeks. Sell them the trip, not the month. The one-trip pass is the lead product; the subscription is for frequent planners.
5. **Never hold data hostage.** Archived trips stay readable and exportable forever on Free.
6. **Let people see the best feature once, at a bounded cost.** The deep agent run is the feature that sells Plus, and a free monthly run for everyone is unaffordable (section 5.6). A single lifetime taster, served from the shared cache when possible, costs about $0.11 to $0.17 per new Free user and is the test of whether showing it pays.

## 3. Tier definitions

Launch tiers: **Free**, **Plus**, **Family**, **Trip Pass** (upgrades one trip for 90 days), **Group Trip Pass** (the same for a group, up to 12 travelers), and credit packs. **Pro** (called Premium in earlier drafts) is built behind a flag and launches later (section 8).

### 3.1 Limits table

| Limit | Free | Plus | Family | Trip Pass (per trip) | Group Trip Pass (per trip) | Pro (later) |
|---|---|---|---|---|---|---|
| Price (US) | $0 | $5.99/mo or $39.99/yr | $8.99/mo or $59.99/yr | $9.99 once | $19.99 once | $11.99/mo or $99/yr |
| People covered | 1 | 1 | Up to 6 in one household | The trip owner | The trip organizer | 1 |
| Active trips | 2 | Unlimited (fair use 25) | Unlimited (fair use 25 per member) | 1 (the passed trip) | 1 (the passed trip) | Unlimited (fair use 50) |
| Archived trips (read and export) | Unlimited | Unlimited | Unlimited | Unlimited | Unlimited | Unlimited |
| Travelers per trip (profiles) | 2 | 8 | 8 | 8 | 12 | 12 |
| Collaborators who can edit | 0 (joins others' trips free) | 6 per trip | 6 per trip, plus the household members | 6 | 11 (12 travelers with the organizer) | 12 per trip |
| Flight routes per trip | 1 (cached fares) | 5 | 5 | 3 | 5 | 8 |
| Airports per side of a route | 2 | 4 | 4 | 4 | 4 | 4 |
| Cached fare refresh (Travelpayouts) | Daily, server side | Daily | Daily | Daily | Daily | Daily |
| Live Google Flights tracking | No (a live peek costs 1 credit) | Up to 3 live routes account-wide, 1 check per day each, only within 120 days of departure | Up to 5 live routes pooled across the household, same rules | Up to 2 routes, 1 check per day, at most 60 checks total | Up to 3 routes, 1 check per day, at most 90 checks total | Up to 6 live routes, 1 check per day each, plus 2 per day on 1 "watch" route |
| "Refresh now" (live) | 1 credit | 1 credit | 1 credit | 1 credit | 1 credit | 1 credit |
| Price-drop alerts (push) | 1 route, on cached fares | 3 routes, live and cached | 5 routes, live and cached | 2 routes, live and cached | 3 routes, live and cached | 6 routes, live, plus deal alerts |
| Saved lodging per trip | 8 | Unlimited (fair use 100) | Unlimited (fair use 100) | 30 | 30 | Unlimited |
| Lodging compare | 2 places | 4 | 4 | 4 | 4 | 4 |
| Rental search (SerpApi) | 1 credit each | 1 credit each | 1 credit each | 1 credit each | 1 credit each | 1 credit each |
| Places search | 30 per day, cached | 100 per day | 100 per day per member | 100 per day | 100 per day | 200 per day |
| Presentation mode | Yes, small "Made with" footer, PDF watermark | No footer or watermark | No footer or watermark | No footer or watermark | No footer or watermark | No footer or watermark |
| AI credits | 12 per month (no rollover) | 60 per month (no rollover) | 150 per month, pooled (no rollover) | 40 once, for the 90 days of the pass | 80 once, for the 90 days of the pass | 240 per month (one month rolls over, capped at 240) |
| Deep agent runs | 1 lifetime taster (per Apple ID, needs a trip with dates, served from the shared cache when possible); later runs from packs, 40 credits each | 1 a month from credits (40 of 60); more from packs | About 3 a month from the pooled credits (3 x 40 = 120 of 150) | 1 from credits (40) | 2 from credits (2 x 40 = 80) | About 6 a month from credits; scheduled routines allowed |
| Scheduled agent routines | No | No | No | No | No | Yes: up to 3 per trip, max 1 run per day per routine |
| Priority queue | No | No | No | No | No | Yes (agents and drafts jump the queue) |
| Group tools (polls, cost splitting, room-block request) | No | No | No | No | Yes | No |
| Data export (JSON, ICS, PDF) | Yes | Yes | Yes | Yes | Yes | Yes |
| Affiliate booking links | Yes, same places | Yes, same places | Yes, same places | Yes, same places | Yes, same places | Yes, same places (never removed) |
| "Before you go" checklist | Yes | Yes | Yes | Yes | Yes | Yes |
| After-trip prompt ("Was your flight delayed?") | Yes | Yes | Yes | Yes | Yes | Yes |

Notes on the choices:
- **Affiliate links are on every tier, in the same places, and are never a paid feature.** A paid tier never removes them (they are the same helpful booking buttons, labeled with "We earn a commission if you book here."). Free is never degraded: results, ordering and detail are identical on every tier, and lists are never ranked by commission. Affiliate income is therefore earned on all MAU, free and paid alike. Program details, placement and disclosure are in [08-affiliate-revenue.md](08-affiliate-revenue.md).
- **The "Before you go" checklist and the after-trip prompt are free features on every tier.** The checklist (documents, visas, insurance, eSIM, transfers and similar) has at least half its items unmonetized, links visas to official sites first, and uses insurer-approved copy only. The after-trip prompt asks "Was your flight delayed?" and links to a compensation service. Neither costs credits, and AI never gives insurance advice.
- **Free gets 2 active trips, not 1.** Two people planning a couple's trip and a second idea (a weekend away) is normal. One trip makes users feel cornered; three makes Plus unnecessary for most.
- **Free gets 12 credits and one deep agent run for life.** The credits let a new user try drafting and a research question; the taster lets them see the agent find something real for their own trip. After the taster, the result stays on the trip and the next run costs credits (section 4.7).
- **Free cannot host collaboration but can join it.** Only the trip owner pays. Invitees join free and get the owner's tier on that trip. That is the viral loop: every paying trip pulls in 1 to 5 new accounts at almost no cost beyond an idle account. AI credits are charged to the person who starts the action.
- **Family is one payer, up to 6 people, one pool.** Members are invited in the app (Apple Family Sharing stays off). Credits (150) and the monthly ceiling ($3.40) are pooled, so six members cost no more than their shared allowance, which is what made earlier Apple-style sharing unsafe. One deep run at a time per household. For a couple it is cheaper than two Plus plans: $59.99 against 2 x $39.99 = $79.98, 25% less, with 150 pooled credits against 2 x 60 = 120.
- **Group Trip Pass is the organizer's pass for one group trip.** Up to 12 travelers, 80 credits, polls, cost splitting (no money moves through Hermi) and a room-block request. It is bound to one trip on the server like Trip Pass. Its live-route limits (3 routes, 90 checks) scale Trip Pass's 2 routes and 60 checks by 1.5.
- **Live tracking is limited by routes, frequency, and date window, not by credits.** Users hate seeing a price tracker burn a credit meter every morning. The ceiling in section 6 keeps it safe underneath.
- **The 120-day window matters.** Fares more than about 4 months out rarely move meaningfully, so live checks there are wasted spend. Cached fares cover those trips.
- **Alerts on cached fares are free.** Push costs nothing and drives return visits.
- **Trip Pass and Group Trip Pass are non-renewing subscriptions in StoreKit, bound to one trip on the server.** StoreKit only records the purchase and its 90-day term; our server decides which trip it upgrades, tracks the 90 days, and can move it at most once (section 6.2). A consumable would not carry a term or show up in restore.

### 3.2 API-only vs AI, by tier

| Class | Examples | Who gets it |
|---|---|---|
| API-only, free to us | Itinerary, lodging, presentation, airports, Wikipedia, ECB FX | Everyone, unmetered |
| API-only, cached | Travelpayouts fares, Geoapify places (1 week cache) | Everyone, soft daily caps |
| API-only, live and paid per call | SerpApi flights and rentals (behind a feature flag at launch, see [06-database-and-data-integrations.md](06-database-and-data-integrations.md)) | Plus, Family and the passes on schedule; anyone via credits |
| AI, cheap (Haiku, under $0.01) | "Explain this fare", "Is this place good for kids", short answers | Everyone via credits |
| AI, medium (Sonnet, no web, $0.03 to $0.10) | Itinerary drafting | Everyone via credits; more allowance on paid tiers |
| AI, research (Sonnet plus web search, $0.05 to $0.15, $0.16 hard stop) | Single research question | Everyone via credits; shared research cache |
| AI, agent (multi-turn, $0.50 to $1.50 today, $0.80 hard stop) | Fare-hunt agent, research agent, scheduled routines | One taster for every Free user; credits on any tier for manual runs; Pro allowance and scheduled routines once Pro launches |

## 4. AI credits system

### 4.1 Unit definition

**1 credit is a budget of up to 2 cents of provider spend** (Claude, SerpApi, Geoapify). Actual cost is usually lower, and the gap is margin. Users never see dollars.

Why credits and not "N runs": one word covers three unlike things (a Haiku answer under 1 cent, a SerpApi search at 1.5 cents, an agent run at 80 cents). A single balance lets a user pick what to spend it on and lets us reprice a cost line without changing the plan promise.

### 4.2 Credit cost per action

| Action | Credits | Typical real cost | Max real cost (enforced) | Notes |
|---|---|---|---|---|
| Haiku explain or short answer | 1 | $0.003 to $0.008 | $0.01 | Output capped at 400 tokens |
| Live flight search on demand ("Refresh now") | 1 | $0.015 | $0.02 | Cached result under 6h old is free and says so |
| Rental search | 1 | $0.015 | $0.02 | Repeat within 12h is free (already in app) |
| Itinerary draft, one day | 1 | $0.02 | $0.03 | Sonnet, no web, cached system prompt |
| Itinerary draft, whole trip | 4 | $0.06 to $0.09 | $0.10 | Up to 14 days; longer trips bill per 14 days |
| Research question (Sonnet plus web search) | 8 | $0.05 to $0.15 | **$0.16 hard stop** | Max 5 searches, 8 fetches |
| Research question served from shared cache | 1 | about $0 | $0.005 | Same destination, same topic, under 7 days old |
| Deep agent run (flight-hunt or research) | 40 | $0.50 to $1.50 today | **$0.80 hard stop** | Caps in 4.6 |
| Deep agent run served from shared cache | 8 | about $0.05 | $0.15 | "Someone already researched this last week" |
| Deep agent run, free taster (once per Apple ID) | 0 | $0.56 typical, about $0.05 from cache | **$0.80 hard stop** | Same caps as a deep run; cache first; own ledger line (4.7) |

Every price above equals its enforced maximum divided by $0.02 (8 x $0.02 = $0.16; 40 x $0.02 = $0.80), so a credit is never worth less than the most it can cost us. The taster is the one exception by design: it is a $0.80 action given away once, budgeted separately in 4.7 and 5.3.

Refund rules: any action that fails, times out, or returns nothing saved is refunded automatically; a taster that fails or saves nothing is not consumed. An agent run stopped by the user is billed pro rata by turns used (minimum 8 credits).

### 4.3 Monthly allowances

| Tier | Credits | Max provider cost of allowance | What it buys |
|---|---|---|---|
| Free | 12 per month, plus the one-time taster run | $0.24 (taster separate, $0.80 stop) | 12 explains, or 1 research question (8) plus 4 explains, or 2 live peeks plus 10 explains |
| Plus | 60 per month | $1.20 | One deep agent run plus extras (table below), or 7 research questions |
| Family | 150 pooled per month | $3.00 | 3 deep runs (120) plus 3 research questions (24) plus 6 explains (6) = 150, or 18 research questions (144) plus 6 explains |
| Trip Pass | 40 once | $0.80 | 1 whole-trip draft (4) plus 4 research questions (32) plus 4 refreshes (4) = 40, or one deep agent run |
| Group Trip Pass | 80 once | $1.60 | 2 deep runs (80), or 1 deep run (40) plus 4 research questions (32) plus 2 drafts (8) = 80 |
| Pro (later) | 240 per month | $4.80 | About 6 deep agent runs (6 x 40 = 240), or 30 research questions (30 x 8 = 240) |

What 60 credits buy on Plus (each line sums to 60):

| Way to spend them | Arithmetic |
|---|---|
| One deep run plus the trip basics (the typical heavy month) | 40 (run) + 4 (whole-trip draft) + 8 (research question) + 8 (explains or refreshes) = 60 |
| Research-heavy | 7 research questions (56) + 4 explains = 60 |
| Draft-heavy | 3 whole-trip drafts (12) + 6 research questions (48) = 60 |
| Live-heavy | 60 "Refresh now" checks or rental searches = 60 |
| Cache-friendly | 1 deep run (40) + 10 cache-served research questions (10) + 10 explains = 60 |

The old 40 credits gave exactly one deep run or 5 research questions and nothing else. The 20 extra credits are what make a Plus month feel like a real month: a deep run and the trip basics, with no decision about which one to give up. The deep run is the only reason to spend 40 at once, and the confirm step (section 9.2) shows the cost first.

### 4.4 Top-up packs (consumable in-app purchases)

Price per credit must sit above 2 cents to cover the maximum cost, plus Apple's 15%, plus margin. Target 50% gross margin on worst-case use.

| Pack | Price | Credits | Price per credit | Net after Apple | Margin if all credits spent at max cost |
|---|---|---|---|---|---|
| Small | $2.99 | 50 | 6.0 cents | $2.54 | 61% (cost $1.00) |
| Medium | $6.99 | 150 | 4.7 cents | $5.94 | 49% (cost $3.00) |
| Large | $14.99 | 400 | 3.75 cents | $12.74 | 37% (cost $8.00) |

Real margin is higher because actual cost is usually 40 to 60% of the maximum. One deep agent run costs the user 40 credits, about $1.87 on the Medium pack. One research question costs 8 credits, about $0.37 on the Medium pack. Sell a run as "one deep research run, about $2". The Small pack (50 credits) covers one deep run plus 10 credits, which is the natural next step after the taster for a user who is not ready for a plan.

### 4.5 Rollover and expiry rules

- **Monthly allowance credits do not roll over** on Free, Plus or Family, including annual subscribers (allowances are granted monthly on the renewal date; the Family pool is granted to the household owner's account). Pro rolls over one month's worth: the balance after rollover is capped at 240 before the new grant.
- **The taster is not a credit.** It is a single entitlement per Apple ID, kept on the server, that does not expire and does not reset if the account is deleted and re-created (section 6.2).
- **Purchased credits last 12 months** from purchase and are spent last. Some jurisdictions treat prepaid balances as liabilities, so expiry is generous and disclosed on the pack screen.
- **Spend order:** monthly allowance first, then Trip Pass or Group Trip Pass credits, then purchased credits (oldest first). In a Family, every member's action is charged to the pool first, then to the member's own purchased credits.
- **Downgrade or lapse:** purchased credits stay usable on Free. Allowance credits vanish. A lapsed Family drops its members to Free (each keeps the taster state of their own Apple ID).
- **Refunds (Apple):** on a refund notification (App Store Server Notifications v2), remove unspent credits from that purchase. If already spent, flag the account and stop further top-ups.
- **Balance is server-side.** Hermi shows the balance but never decides it.

### 4.6 Agent run cost control (needed for the numbers to work)

Today a run allows 40 turns and about 30 fetches. To make 40 credits ($0.80) a real ceiling, every agent run gets these caps:
- **20 turns, 10 web searches, 10 page fetches, effort `medium`, $0.80 hard stop, one run at a time per account (per household on Family).**
- Token budget tracked live against the $0.80 stop.
- Fetched pages are summarized with Haiku before Sonnet sees them (cuts input tokens by more than half in practice).
- Prompt caching on the fixed system prompt and trip context (cache reads $0.20 per 1M).
- Research questions have their own smaller caps: 5 searches, 8 fetches, $0.16 hard stop.
- The Batch API does not fit multi-turn tool loops (each turn waits on the previous), so its 50% discount is only for offline jobs: shared-cache warming, nightly destination digests, scheduled fare scans. See [03-ai-features-and-costs.md](03-ai-features-and-costs.md).

### 4.7 The free taster run

Every Free account gets one deep agent run for life, to see the feature do real work on its own trip.

| Rule | Setting |
|---|---|
| Who | Each Apple ID, once. Keyed to the Apple ID and the device (App Attest), so deleting and re-creating an account does not reset it |
| Needs | A trip with dates and at least one route or a destination, so the run has something to find |
| Served how | Shared cache first: if a fresh result exists for the same route and dates, show it (cost about $0.05). Otherwise a normal capped run ($0.80 hard stop, typical $0.56). The result is written back to the shared cache |
| Instructions | None. No free-text instructions, so the result can be cached and shared (03, section 6.5) |
| Budget | Outside the Free monthly ceiling ($0.25), on its own ledger line, so it neither uses the ceiling up nor is blocked by the $0.05 daily budget. Inside the global circuit breakers (6.3) and a global daily taster budget (assumption: $25 a day, then the taster queues for the next day) |
| Not consumed if | The run fails, is refused, or saves nothing |
| What happens next | The result is shown in full and stays on the trip, then the Plus offer appears (9.1). Nothing found is ever blurred or held back |

Taster economics, per new Free user (assumptions: 30% of new Free users redeem it, 35% of runs are served from the shared cache, a cached run costs $0.05, an uncached run $0.56):
- Expected cost per run: 0.35 x $0.05 + 0.65 x $0.56 = $0.0175 + $0.364 = $0.3815, about $0.38.
- Per new Free user: 0.30 x $0.3815 = $0.1145, about **$0.11**.
- With nothing cached: 0.30 x $0.56 = **$0.17**. With every run at the $0.80 stop and no cache: 0.30 x $0.80 = $0.24.
- Payback: one point of paid conversion is worth about 0.01 x $28.34 = $0.28 of net revenue per MAU a year, where $28.34 is the blended net revenue per paying user per year. So the taster pays for itself if it lifts conversion by about 0.4 to 0.6 points ($0.11 / $0.28 = 0.4; $0.17 / $0.28 = 0.6). That lift is an assumption to test with an A/B split at launch, not a fact. If the test shows less, cut the taster to cache-only results.

## 5. Unit economics

### 5.1 Revenue per subscriber after Apple's 15%

| Product | Gross | Net (85%) | Net per month |
|---|---|---|---|
| Plus monthly | $5.99 | $5.09 | $5.09 |
| Plus annual | $39.99 | $33.99 | $2.83 (33.99 / 12) |
| Family monthly | $8.99 | $7.64 | $7.64 |
| Family annual | $59.99 | $50.99 | $4.25 (50.99 / 12) |
| Trip Pass | $9.99 | $8.49 | per purchase |
| Group Trip Pass | $19.99 | $16.99 | per purchase |
| Pro monthly | $11.99 | $10.19 | $10.19 |
| Pro annual | $99.00 | $84.15 | $7.01 |
| Plus annual at $29.99 (earlier draft) | $29.99 | $25.49 | $2.12 (for comparison, see 7) |
| Pro annual at $79 (initial idea) | $79.00 | $67.15 | $5.60 |

The Small Business Program gives 15% while the developer stays under $1M a year in proceeds. Above that, standard rates apply (30% in the first year of a subscription, 15% after one year of paid retention). US web checkout (link out to Stripe, about 3% plus a fixed fee) is possible margin upside and out of scope here.

### 5.2 Cost assumptions

| Cost line | Assumption | Basis |
|---|---|---|
| SerpApi | $0.015 per search | Unverified, see caveats |
| Shared-cache dedupe on live checks | 35% of typical-user checks are served from another user's identical search | Popular routes overlap heavily; assumption to validate |
| Geoapify | About $0.0005 per uncached search after the free tier | Estimate; 1 week cache |
| Haiku explain | $0.005 | Under 1 cent |
| Credits used, typical | $0.012 each | Flat average across drafts, research and explains, uncached (conservative; 03 shows the cache-adjusted AI cost) |
| Full-trip draft | $0.08 | Sonnet, about 20k in, 5k out, with caching |
| Research question | $0.10 typical, $0.16 hard stop | $0.05 to $0.15 range |
| Deep agent run | $0.80 cap, $0.56 to $0.60 average with the controls in 4.6 | Uncapped today: $0.50 to $1.50 |
| Taster run | $0.56 uncached, about $0.05 from the shared cache, 30% redeem, 35% cache hit | Section 4.7; assumptions |
| Infra share (DB, workers, push, email, bandwidth, monitoring) | $0.03 per Free MAU, $0.06 per paid user per month; Trip Pass $0.10, Group Trip Pass $0.15, Family $0.12 typical per household | Estimate at 10k MAU; fixed costs excluded (see [05-infrastructure.md](05-infrastructure.md)) |

The figures below were recomputed for the new ladder (Plus at 60 credits and $2.25, Family, Group Trip Pass, the taster). Credit costs per action are unchanged; allowances, ceilings and prices moved.

### 5.3 Cost and margin per user type

"Typical" is measured as a share of allowance and is an assumption to validate in the first 60 days after launch. Margin = (net per month - cost) / net per month.

**Free**

| User | Behavior | Monthly cost |
|---|---|---|
| Light | Browses, 1 cached route, 5 places searches | $0.03 |
| Typical | Cached route, 20 places searches, 4 Haiku, alert pushes | $0.06 |
| Heavy (abuse case) | Maxes 12 credits and places soft cap | $0.25 (hard limited) |
| Taster, one time, per new user who redeems it | One deep run: $0.56 typical, about $0.05 from cache, $0.80 stop | $0.11 expected per new Free user (30% redeem), $0.17 with no cache |

Free revenue is affiliate only: about $0.05 per MAU per month in the base case ($0.60 a year; the range across the conservative and optimistic cases is $0.01 to $0.13 a month, from $0.10 to $1.50 a year). Every tier earns it, so it is not counted in the per-user margins here; section 5.5 shows it separately. It is unverified.

**Plus (monthly subscriber, net $5.09; annual, net $2.83 per month)**

| User | Behavior (in an active month) | Cost | Margin monthly | Margin annual |
|---|---|---|---|---|
| Light | 1 route, about 10 checks after dedupe (10 x $0.015 = $0.15), 10 credits ($0.12), places $0.01, infra $0.06 | $0.34 | 93% | 88% |
| Typical | 2 routes, 60 checks less 35% dedupe = 39 x $0.015 = $0.59, 25 credits x $0.012 = $0.30, places $0.03, infra $0.06 | $0.98 | 81% | 65% |
| Heavy | 3 routes daily (90 checks, $1.35), all 60 credits at max ($1.20): $2.55, cut to the ceiling $2.25, plus places and infra $0.14 | $2.39 | 53% | 16% |
| Worst case (ceiling hits) | Ceiling $2.25 plus infra and places $0.14 | $2.39 | 53% | 16% |

Margins: (5.09 - 0.98) / 5.09 = 81%; (2.83 - 0.98) / 2.83 = 65%; (5.09 - 2.39) / 5.09 = 53%; (2.83 - 2.39) / 2.83 = 16%. Earlier draft at $29.99 and a $1.75 ceiling: typical annual 59%, worst annual 11%.

The ceiling is what saves the annual plan: without it the parts sum to 90 live searches ($1.35) plus 60 credits at max ($1.20) plus $0.14 = $2.69 against $2.83 of net, a 5% margin, and a SerpApi price above 1.5 cents would push it negative. With the ceiling, provider spend cannot exceed $2.25.

**Family (household of up to 6; monthly net $7.64; annual net $4.25 per month)**

| User | Behavior (in an active month) | Cost | Margin monthly | Margin annual |
|---|---|---|---|---|
| Light | 2 routes, 30 checks less dedupe = 20 x $0.015 = $0.30, 20 credits ($0.24), places $0.03, infra $0.10 | $0.67 | 91% | 84% |
| Typical | 3 routes, 90 checks less 35% dedupe = 59 x $0.015 = $0.89, 50 credits x $0.012 = $0.60, places $0.06, infra $0.12 | $1.67 | 78% | 61% |
| Heavy or worst (pooled ceiling hits) | Ceiling $3.40 plus infra and places $0.20 | $3.60 | 53% | 15% |

Margins: (7.64 - 1.67) / 7.64 = 78%; (4.25 - 1.67) / 4.25 = 61%; (7.64 - 3.60) / 7.64 = 53%; (4.25 - 3.60) / 4.25 = 15%. The parts sum to 150 credits at max ($3.00) plus 150 live checks ($2.25) = $5.25, so without the pooled ceiling a household that uses everything loses money. Family annual at the ceiling is the thinnest cell in the plan besides Plus annual: set a pooled-ceiling alert at $3.00 and reprice if more than 25% of families sit near it.

**Trip Pass (net $8.49, one purchase covers 90 days of one trip)**

| User | Behavior | Cost | Margin |
|---|---|---|---|
| Light | 1 route, 25 live checks ($0.38), 10 credits ($0.10), infra $0.10 | $0.58 | 93% |
| Typical | 2 routes, 45 checks ($0.68, about $0.44 after dedupe), 25 credits ($0.30), infra $0.10 | $0.84 | 90% |
| Heavy or worst | 60 checks ($0.90), all 40 credits at max ($0.80), infra $0.10 | $1.80 | 79% |

Margins: (8.49 - 0.58) / 8.49 = 93%; (8.49 - 0.84) / 8.49 = 90%; (8.49 - 1.80) / 8.49 = 79%. Trip Pass is a high-margin product because its cost is capped per trip and it has built-in breakage.

**Group Trip Pass (net $16.99, one purchase covers 90 days of one group trip)**

| User | Behavior | Cost | Margin |
|---|---|---|---|
| Light | 2 routes, 40 live checks ($0.60), 20 credits ($0.24), infra $0.12 | $0.96 | 94% |
| Typical | 3 routes, 70 checks less 35% dedupe = 45.5 x $0.015 = $0.68, 45 credits ($0.54), infra $0.15 | $1.37 | 92% |
| Heavy or worst | 90 checks ($1.35), all 80 credits at max ($1.60), infra $0.15 | $3.10 | 82% |

Margins: (16.99 - 0.96) / 16.99 = 94%; (16.99 - 1.37) / 16.99 = 92%; (16.99 - 3.10) / 16.99 = 82%. The $3.60 ceiling sits $0.50 above the limits-based worst case, so it guards against price drift rather than binding; at the ceiling plus infra ($3.75) the margin is (16.99 - 3.75) / 16.99 = 78%.

**Pro (later; monthly net $10.19, annual $99 net $7.01 per month)**

| User | Behavior | Cost | Margin monthly | Margin annual ($99) |
|---|---|---|---|---|
| Light | 2 routes live, 30 credits | $1.00 | 90% | 86% |
| Typical | 4 routes live ($1.35 after dedupe), 2 deep runs ($1.60) and 5 research questions ($0.50), infra $0.08 | $3.53 | 65% | 50% |
| Heavy | 6 routes, 240 credits used at cost | $5.58 | 45% | 20% |
| Worst case (ceiling $5.50 plus infra) | | $5.58 | 45% | 20% |

Margins: (10.19 - 3.53) / 10.19 = 65%; (7.01 - 3.53) / 7.01 = 50%; (10.19 - 5.58) / 10.19 = 45%; (7.01 - 5.58) / 7.01 = 20%. At $79 a year the worst case is $5.58 against $5.60 of net monthly revenue: zero margin. That is why the price is $99.

### 5.4 Why 10 to 15 agent runs in Pro does not work

At $0.50 to $1.50 per run, 10 to 15 runs cost $5 to $22.50 a month against $10.19 net. Even at the low end plus live tracking, the annual plan goes negative. It only works if the average run drops below about $0.40. Sonnet 5.5 pricing is not the problem; the 40-turn, 30-fetch design was. So a run is capped at $0.80 (20 turns, 10 searches, 10 fetches), Pro allows about 6 (240 credits / 40), and heavier users buy credit packs (37% to 61% margin at worst case).

### 5.5 Illustrative month at 10,000 monthly active users

Assumption: 4% pay (140 + 80 + 30 + 100 + 20 + 30 = 400 payers, counting Trip Pass and Group Trip Pass buyers in the month), and 1,500 new Free accounts a month (15% of MAU), each eligible for the taster. This is a sanity check, not a forecast. Against a reported 2.0% to 2.4% download-to-paid median (RevenueCat), 4% of MAU is a stretch that works only because MAU leaves out churned installers; 03 shows 3% as a sensitivity.

| Line | Count | Net revenue | Cost |
|---|---|---|---|
| Free MAU | 9,600 | $0 (subscription revenue) | 9,600 x $0.05 = $480 |
| Free taster | 1,500 new accounts | $0 | 1,500 x $0.1145 = $172 |
| Plus annual | 140 | 140 x $2.83 = $396 | 140 x $0.98 = $137 |
| Plus monthly | 80 | 80 x $5.09 = $407 | 80 x $0.98 = $78 |
| Family (20 annual, 10 monthly) | 30 | 20 x $4.25 + 10 x $7.64 = $85 + $76 = $161 | 30 x $1.67 = $50 |
| Trip Pass purchases per month | 100 | 100 x $8.49 = $849 | 100 x $0.84 = $84 |
| Group Trip Pass purchases per month | 20 | 20 x $16.99 = $340 | 20 x $1.37 = $27 |
| Pro (blended) | 30 | 30 x $8.00 = $240 | 30 x $3.53 = $106 |
| Credit packs | 60 packs | 60 x $5.00 net = $300 | about $110 |
| Affiliate (all 10,000 MAU, base case) | 10,000 | 10,000 x $0.05 = about $500 | none extra |
| Total without affiliate | | $396 + 407 + 161 + 849 + 340 + 240 + 300 = $2,693 | $480 + 172 + 137 + 78 + 50 + 84 + 27 + 106 + 110 = $1,244 |
| Total with affiliate | | $2,693 + $500 = $3,193 | $1,244 |

Gross margin without affiliate: (2,693 - 1,244) / 2,693 = 54%. With base-case affiliate income (10,000 x $0.05 = $500 a month, from $0.60 per MAU per year): (3,193 - 1,244) / 3,193 = 61%. Both are before fixed costs (developer, hosting minimums, support). The earlier ladder gave 56% and 64%: the higher prices and the Family and Group Trip Pass lines add margin, and the taster takes it back (without the $172 taster the same month is (2,693 - 1,072) / 2,693 = 60% without affiliate and (3,193 - 1,072) / 3,193 = 66% with it, so the taster costs about 6 points).

Pro lines are included as a later-stage sanity check; without the 30 Pro users the total is $2,453 revenue and $1,138 cost, still (2,453 - 1,138) / 2,453 = 54% without affiliate and (2,953 - 1,138) / 2,953 = 61% with it.

Three lessons: Free users and their tasters are 52% of variable cost ((480 + 172) / 1,244), so the Free tier must stay near $0.05 per user and the taster has to earn its cost; Trip Pass, Group Trip Pass and packs carry $1,489 of the $2,693 (55%) against $1,204 (45%) from Plus, Family and Pro, so at this scale the passes matter more than subscriptions; and Family plus Group Trip Pass add $501 a month for $77 of cost, the best margin in the mix.

### 5.6 Why not one free deep run a month for every Free user

Inputs: deep run typical $0.56, cache-served run about $0.05, affiliate about $0.60 per MAU per year.

| Option | Cost per Free MAU per year | Verdict |
|---|---|---|
| 12 credits, no run (baseline) | about $0.15 | Baseline |
| 1 run a month for every Free user, 20% redeem each month | 0.20 x 12 x $0.56 = $1.34 | Reject: more than double the affiliate income per MAU |
| 1 run a month, 5% redeem each month | 0.05 x 12 x $0.56 = $0.34 | Reject: 2.2 times baseline for one feature, and it grows if sharing lifts redemption |
| One lifetime taster | $0.11 to $0.17 per new Free user (4.7) | Adopt |
| Earned extra runs: invite a friend who creates a trip, both get 20 credits | $0.40 of credits per activated referral, paid only on activation | A later retention lever, not part of launch |

## 6. Guardrails

The design goal: no account can cost more than its net revenue, whatever it does.

### 6.1 Per-account dollar ceilings (server enforced, invisible to users)

| Tier | Monthly provider-spend ceiling | Daily budget | When the ceiling hits |
|---|---|---|---|
| Free | $0.25, plus the one-time taster run (own $0.80 stop, own ledger line) | $0.05 | Live and AI actions off; cached data still works; upgrade prompt |
| Plus | $2.25 | $0.40 | Live tracking drops to cached only until the 1st; message says "checks resume on the 1st" |
| Family | $3.40 pooled across the household | $0.40 | Live tracking drops to cached only for the household until the 1st; the usage screen shows each member's share |
| Trip Pass | $1.80 per pass | $0.40 | Live checks pause; credit packs offered |
| Group Trip Pass | $3.60 per pass | $0.40 | Live checks pause; credit packs offered to the organizer |
| Pro (later) | $5.50 | $1.25 | Scheduled agents pause; top-up offered |

The ceiling counts SerpApi, Claude, and Geoapify spend attributed to the account. The ledger is the new `provider_calls` and `ai_usage` tables described in [06-database-and-data-integrations.md](06-database-and-data-integrations.md), which generalize today's `ApiCall` table (provider, units, cached) with user, trip, and cost in dollars. Purchased credits raise the ceiling by the pack's cost value, since that spend is separately paid.

Why each ceiling sits where it does: it is above typical use and below the sum of the parts, so the ceiling binds only for heavy users. Plus: typical $0.98 and parts $1.20 (60 credits at max) + $1.35 (90 live checks) = $2.55 against $2.25. Family: typical $1.67 and parts $3.00 + $2.25 = $5.25 against $3.40. Group Trip Pass: parts $1.60 + $1.35 = $2.95 against $3.60, a margin for price drift. Pro: parts $4.80 + $1.85 (20 scans) = $6.65 against $5.50. Scheduled scans and tracking pause first, user-started actions last.

A deep agent run ($0.80 hard stop) costs more than the $0.40 daily budget on Plus, Family and the passes, so the rule is: a run is admitted when the month has at least $0.80 of headroom, even if it pushes past the daily budget. Its spend still counts toward that day, so no other paid actions run until the next day. The taster is the exception: it is admitted outside the Free ceiling and daily budget, because it is budgeted on its own line.

### 6.2 Rate and abuse limits

- One agent run at a time per account (per household on Family), and one global concurrent-run cap per worker pool. Queue the rest (Pro first).
- Max 1 scheduled run per day per routine, min 12 hours between runs of the same routine (Pro only).
- Per-endpoint rate limits: AI endpoints 10 per minute per account; places search 30 per minute.
- One Free account per Apple ID (Sign in with Apple), device check with App Attest, plus IP velocity limits on signups (maximum 5 new accounts per IP per day).
- Taster abuse: the entitlement is stored against the Apple ID and the device, not the account, so a new account cannot claim a second one. It needs a trip with dates, the global daily taster budget caps a burst of signups, and the taster never runs with free-text instructions.
- Family abuse: members join by in-app invite, at most 6 per household, a person belongs to one household at a time and can switch at most once every 30 days, and the pooled credits and ceiling mean extra members add no cost.
- Trip Pass and Group Trip Pass fraud: the pass is tied to the Apple ID and bound to one trip on the server; it can be moved at most once.
- Refund clawback (see 4.5); repeated refund abuse blocks purchases.
- Input controls: max 2,000 characters on prompts, max 14 days per draft call, identical requests within 6 hours return the earlier result free.
- No user-supplied URL for agent fetching beyond the allowed evidence rules (existing ingest checks and blocked domains stay).
- Prompt caching and the shared research cache are mandatory for every AI call, so repeated destinations cost near zero.

### 6.3 Global circuit breakers

- SerpApi budget: the existing monthly-cap logic in `serpapi_budget.py` generalizes to a global daily budget. If spend passes 90% of the plan's monthly quota, live checks go to top-value routes only (routes with a chosen flight or an active alert), then cached only.
- Anthropic spend: global daily limit; at 80% disable Free-tier AI and queue the taster, at 95% disable everything but paid tiers.
- Alert when cost per active payer exceeds $2.50 (Plus), $3.75 (Family) or $6 (Pro), each just above the ceiling-plus-infra worst case.
- Fail closed: if the ledger cannot be read, do not run paid calls.

## 7. Pricing alternatives considered

| Option | Verdict | Reasoning |
|---|---|---|
| Monthly only | Reject as the lead | Travel is episodic: users subscribe for planning weeks, then cancel. Expect short lives (2 to 3 months). Kept as an option, not the headline. |
| Annual | Keep, pre-selected | $39.99 is 44% under 12 x $5.99 = $71.88 and sits at the bottom of the $39.99 to $49.99 band rivals charge. Best retention, lowest net per month, so it needs the ceiling. |
| One-trip Trip Pass at $9.99 | Lead product | Matches how people buy: "I have a trip in March". High margin (79% to 93%). Low commitment, so it converts Free users who would never subscribe. |
| Group Trip Pass at $19.99 | Keep | Organizers of group trips pay once for up to 12 travelers ($1.67 each at 12). Margin 82% to 94%. No money moves through Hermi, so no payments risk. |
| Family plan at $8.99 or $59.99 | Keep, in-app invites | Pooled credits and a pooled ceiling mean up to 6 people cost no more than one allowance, which solves the problem that made Apple Family Sharing unsafe. $59.99 is 25% under two Plus annual plans for a couple. Apple Family Sharing itself stays off. |
| Free trial | Annual Plus only, 7 days | Trial exposure is about $0.45 typical and is capped at $0.90 by a trial-week ceiling (40% of the $2.25 monthly ceiling). Expected conversion of 35 to 45% makes it worth it: $0.45 / 0.40 = about $1.13 of trial cost per converted customer against $33.99 net. No trial for Family (a trial would give 6 people a week of pooled credits; revisit after the Plus trial data), the passes or Pro. |
| Free monthly deep run for every Free user | Reject | $1.34 a year per Free MAU at 20% monthly redemption, more than double the affiliate income (5.6). A lifetime taster replaces it. |
| Hard paywall before first use | Reject | RevenueCat reports 10.7% trial-to-paid for hard paywalls against 2.1% for freemium, but that is of trial starters, not of installs, and a hard paywall would close the free sharing loop. Invitees must be able to join free. |
| Lifetime purchase | Reject | Unbounded AI and live-search cost against one payment. |
| Credits only (no subscription) | Reject as primary | Users resent metering everything; the pass and Plus give predictability. Credits stay as the top-up. |
| Pay per AI action with no allowance | Reject | Kills discovery of the best feature; small allowances and the taster let people try it. |
| Ads on Free | Reject | Clutters a planner; affiliate links already monetize Free without hurting the UI. |

### Why $39.99 and not $29.99

1. **Competitors charge $39.99 to $49.99.** Wanderlog Pro is $39.99 a year, TripIt Pro $49, Layla Premium $49 to $49.99, and Splitwise Pro (the cost-splitting anchor) $39.99. At $29.99 Plus would sit $10 to $20 below every paid rival for a larger AI allowance than any of them sells, and nobody charges for an AI planner alone, so the workspace has to carry the price.
2. **$29.99 loses money at the ceiling.** With 60 credits and a $2.25 ceiling the worst case costs $2.39 a month. At $29.99 net is $25.49, or $2.12 a month: (2.12 - 2.39) / 2.12 = -13%. At $39.99 it is +16%. Typical use: (2.12 - 0.98) / 2.12 = 54% at $29.99 against 65% at $39.99.
3. **The extra $10 is $8.50 of net a year** per annual payer (85% of $10). At the 10,000 MAU month, 140 annual Plus payers bring $8.50 x 140 / 12 = about $99 a month more.
4. **AI apps churn about 30% faster** (RevenueCat, reported), with 12-month annual retention of 21.1% against 30.7% for non-AI apps. Fewer renewals means each payer has to earn more in the first year.
5. **$34.99 is the floor.** Net $29.74 is $2.48 a month, so the worst case is (2.48 - 2.39) / 2.48 = 4% and there is no room for a SerpApi price above 1.5 cents. Test $34.99 against $39.99 before locking, never below $34.99.

### Price points and price testing
- Plus: $5.99 per month or $39.99 per year. Annual is the pre-selected option and shows its real monthly equivalent ($3.33 a month; 12 x $5.99 = $71.88, so annual is 44% less than paying monthly, a true figure). Test $34.99 for annual as a variant; a higher price with a 7-day trial often lifts revenue.
- Family: $8.99 per month or $59.99 per year (12 x $8.99 = $107.88, so annual is 44% less; $5.00 a month equivalent).
- Trip Pass: $9.99 (Apple tier 10). Test $7.99 and $12.99 in a paywall experiment.
- Group Trip Pass: $19.99. Test $24.99.
- Pro: $11.99 per month or $99 per year.
- Launch US-priced with Apple's regional tiers. Do not localize by hand at launch.

## 8. Launch configuration

Ship this on day one (roadmap in [07-local-to-app-store.md](07-local-to-app-store.md)):

| Item | Launch setting |
|---|---|
| Tiers visible | Free, Plus, Family, Trip Pass, Group Trip Pass, credit packs |
| Pro | Entitlements built, shipped behind a flag. Launches when measured agent cost is $0.60 or less per run over 200 runs, or when more than 15% of Plus payers buy agent-run credits |
| Plus | $5.99 per month, $39.99 per year, 60 credits, 3 live routes. Annual pre-selected with its monthly equivalent shown; monthly listed beside it. 7-day trial on annual only |
| Family | $8.99 per month, $59.99 per year, up to 6 people, 150 pooled credits, 5 live routes, in-app invites. Annual pre-selected, no trial |
| Trip Pass | $9.99, non-renewing subscription in StoreKit, bound to one trip on the server, 90 days, 40 credits, 2 live routes, at most 60 live checks |
| Group Trip Pass | $19.99, non-renewing subscription in StoreKit, bound to one trip on the server, 90 days, up to 12 travelers, 80 credits, 3 live routes, at most 90 live checks, polls, cost splitting, room-block request |
| Credit packs | $2.99 for 50, $6.99 for 150, $14.99 for 400 |
| Free | 2 active trips, 1 cached route per trip, 12 credits per month, one lifetime deep agent taster (per Apple ID, cache first), free guest joining, 1 alert on cached fares, affiliate booking links, "Before you go" checklist, after-trip prompt |
| Guardrails | Per-account ceilings, per-day budget, global circuit breakers, taster daily budget, ledger from day one |
| Apple Family Sharing | Off |
| Paywall defaults | Annual pre-selected on the Plus and Family screens; no countdown timers; price and renewal date stated on the trial screen |

Why hold Pro back: agent routines are the riskiest cost and the least proven feature. Selling credits for manual agent runs (40 credits, $0.80 hard stop) and giving one taster tests demand and real cost without a monthly promise. Scheduled agents stay off for everyone until Pro; scheduled work before then is API price checks plus cheap batch scans.

Default paywall order, best converting first: Trip Pass, annual Plus, monthly Plus. Show the Trip Pass first when the user has a trip with dates within 120 days; show annual Plus first when they have 2 or more active trips, and after the taster. Show Family when a trip has 3 or more collaborators or an owner asks to share a plan, Group Trip Pass when a trip passes 8 travelers or asks for polls, cost splitting or a room block, and Pro (once launched) after a user has used an agent run.

## 9. Paywall moments and anti-patterns

### 9.1 Where the upgrade prompt appears

| Moment | Trigger | What we show | Best offer |
|---|---|---|---|
| After the free taster run | The taster finishes (or is served from the cache) | The full result first: fares found, notes with sources, nothing blurred. Then "Want this every month? Plus gives 60 credits, about one deep run a month with the trip basics, and 3 live routes" | Annual Plus; Trip Pass beside it when departure is within 120 days |
| Start a second deep run | Free, taster used | "You have used your free run. One run is 40 credits" | Small pack (50 credits), or Plus |
| Create a third active trip | Free limit reached | "Two trips are active. Archive one, or upgrade" | Annual Plus |
| Add a second route on Flights | Free: 1 route per trip | Preview of the second route's cached fares, unlock | Trip Pass |
| Tap "Track live" or "Refresh now" | No live access | "Live prices for this route, checked daily" plus a credit spend option | Trip Pass or 1 credit |
| Price-drop alert set up | Free alert used up | Explain what live alerts add | Trip Pass |
| Invite a collaborator | Free owner | "Plan together: they join free" | Trip Pass (best fit) |
| Share the plan with a partner or household | Plus owner invites someone to share credits and live routes, or a trip has 3 or more collaborators who each run out of credits | "One plan for up to 6 people, 150 shared credits" | Family |
| Plan a group trip | The 7th collaborator on a Trip Pass, the 9th traveler, or a tap on polls, cost splitting or room block | "Up to 12 travelers, 80 credits, polls and cost splitting" | Group Trip Pass |
| "Draft my itinerary" | Out of credits | Blurred preview of the first day, then unlock | Credit pack or Plus |
| "Research this" or "Ask" | Out of credits | Offer 8 credits for one question | Small pack |
| Start a scheduled agent routine | Not Pro | Sample result from the shared cache | Credits for one manual run, or Pro once launched |
| Presentation "Made with" footer and PDF watermark | Every Free share | Soft, at export | Trip Pass |
| Saving the 9th lodging option | Free limit | Keep saving to a locked "later" list | Trip Pass |
| 14 days before departure with a Free trip | Lifecycle | "Your fares moved this week" email or push | Trip Pass |
| After booking a flight through the affiliate link | Success moment | No paywall; only a soft prompt to plan the days | None |

Rules for each: the free path is always visible; the prompt says what the user gets on this trip; no more than one paywall per session; dismissing it once mutes the same prompt for 7 days. The taster moment appears once, right after the result, and never blocks it.

### 9.2 Anti-patterns to avoid

1. **Paywalling before value.** No paywall at first launch. Let people build a trip, see cached fares, and add plans first. Prompt only at a limit they hit, or after the taster has shown what the agent can do.
2. **Meters that punish core use.** Do not charge credits for editing the calendar, saving lodging, or scheduled live tracking.
3. **Surprise deductions.** Show the credit cost before every AI action, with a confirm for anything at 6 credits or more (research questions and agent runs). The taster says plainly that it is free and used once.
4. **Hiding the free path.** Always show "Not now" and keep affiliate links visible and honest, in the same places on every tier. Do not degrade free results to push upgrades, and do not remove affiliate links from paid tiers.
5. **Hostage data.** Never lock, delete, or hide a trip on downgrade. Read and export always work.
6. **Dark patterns on trials.** State the price and renewal date on the trial screen. Send a reminder before conversion. Pre-selecting annual is fine only while monthly is shown beside it with its real price.
7. **Fake urgency.** No countdown timers or invented "only 2 spots" messages.
8. **Unbounded promises.** Never write "unlimited AI" or "unlimited live tracking" in marketing. Use "generous" and state real numbers.
9. **Selling what we cannot guarantee.** Agent results are indicative and cite sources; do not promise "lowest price" or "we found the best deal".
10. **Pricing by a feature that costs nothing.** Do not gate presentation mode itself, the itinerary, or the lodging list. Only the footer and watermark.
11. **Free tier that leaks cost.** Never let Free trigger live SerpApi or Sonnet calls without spending credits, apart from the one taster, which has its own budget.
12. **Subscription lock-in for an episodic need.** Make cancellation and pausing easy; offer a 3-month pause instead of losing the customer.
13. **Family sharing by accident.** Leave Apple Family Sharing off. The Family plan is its own product with in-app invites, a pooled allowance and a pooled ceiling.
14. **Currency confusion.** Show credits and prices in the store currency; show fares in the trip currency, as the app does today.
15. **Holding the taster hostage.** Never blur, truncate or expire what the taster found to force an upgrade. The result is the pitch.

## 10. Where this plan changed the initial idea

Final decisions are in the README; this section keeps the reasoning.

1. **Pro (earlier Premium) cannot include 10 to 15 agent runs a month.** At $0.50 to $1.50 per run that is $5 to $22.50 against $10.19 net (monthly) or $5.60 net (annual at $79). Final: a run is capped at $0.80 (20 turns, 10 searches, 10 fetches, effort medium), Pro allows about 6 (240 credits), and heavy users buy packs. The tier was renamed from Premium to Pro because it reads as a step up from Plus rather than a separate luxury.
2. **Pro annual is $99, not $79.** At $79 the worst-case margin is about zero. $99 gives 20% at the ceiling and about 50% for a typical user.
3. **Pro ships later.** Launch is Free, Plus, Family, Trip Pass, Group Trip Pass, and credit packs. Agents are the unproven cost line, so demand is tested by selling manual runs in credits and by the taster first. Pro launches at $0.60 or less measured cost per run over 200 runs, or when more than 15% of Plus payers buy agent-run credits.
4. **Alerts are not Plus-only.** Push alerts on cached fares cost nothing and drive return visits. Free gets 1 alert route; paid tiers get live-fare alerts and more routes.
5. **Live tracking is limited by routes, frequency, and a 120-day window, not by credits.** Charging credits for a background tracker feels like a meter running. The account-level dollar ceiling is the real protection.
6. **The Batch API does not fit agent runs.** Multi-turn tool loops wait on each response; Batch is for cache warming, digests, scheduled fare scans, and non-interactive regeneration only. No 50% discount is counted in agent cost.
7. **Collaboration is free to join.** Only the trip owner pays; guests get that tier on that trip. This drives sign-ups.
8. **Trip Pass is the lead offer**, with 40 credits and a hard cap of 60 live checks. The initial idea listed it as a third price point; episodic travel favors it. It is a non-renewing subscription in StoreKit bound to one trip on the server, not a consumable.
9. **Plus is $5.99 and $39.99, with 60 credits and a $2.25 ceiling, not $4.99 and $29.99 with 40 credits and $1.75.** Rivals charge $39.99 to $49.99; at $29.99 the new allowance would lose 13% at the ceiling. The extra $10 of net pays for 20 more credits (enough for a deep run plus the trip basics) and a higher ceiling. Plus annual margin moved from 59% to 65% typical and from 11% to 16% worst case.
10. **Free gets 12 credits and one deep agent taster, not 8 credits and no run.** Nobody pays for a feature they have not seen, and the agent is the feature that sells Plus. The cost is about $0.11 to $0.17 per new Free user, which pays back if it lifts paid conversion by 0.4 to 0.6 points; that is an assumption to A/B test. A free run every month for everyone was rejected at $1.34 a year per Free MAU.
11. **Family and Group Trip Pass are new.** The first draft kept Apple Family Sharing off because shared allowances multiply cost. A separate Family product with pooled credits and a pooled ceiling removes that risk, and a one-time Group Trip Pass sells to the organizer of a group trip without any money moving through Hermi. Together they add about $500 a month of net revenue for about $77 of variable cost in the 10,000 MAU month.
12. **The 10,000 MAU month moved to 54% without affiliate and 61% with it** (from 56% and 64%), on net revenue of $2,693 (from $2,301) and variable cost of $1,244 (from $1,012). The taster is about 6 points of it.
13. **"About 5 research runs a month" became 60 credits**, so users can spend on drafting, research or a deep run as they wish. With research at 8 credits (a $0.16 hard stop and caps of 5 searches and 8 fetches), 60 credits is 7 research questions, or a deep run plus a draft, a research question and 8 explains.
14. **Apple Family Sharing is still off at launch.** It would multiply allowances and live routes per payment; the Family plan covers that need.
15. **SerpApi at 1 to 2 cents is unverified.** Live fares go through SerpApi behind a feature flag at launch (legal risk flagged), with a licensed source (Skyscanner Partners) applied for. If the real cost per search is above 2.5 cents, cut Plus's live-route limit to 2 or raise the price; re-check before setting limits.

## 11. Open items for other files

- Backend ([06-database-and-data-integrations.md](06-database-and-data-integrations.md)): the `provider_calls` and `ai_usage` ledger, and an entitlement service driven by App Store Server Notifications v2, including the Trip Pass and Group Trip Pass binding to a trip, the Family household (members, pooled credits, pooled ceiling), and the taster entitlement keyed to the Apple ID with its own ledger line.
- Legal and policy: SerpApi commercial terms for a consumer app; affiliate terms for in-app use (Travelpayouts, Viator, Stay22, and the direct applications in [08-affiliate-revenue.md](08-affiliate-revenue.md)); prepaid credit disclosure rules.
- Measurement plan: track cost per active payer, credits used share, Trip Pass vs Plus split, paywall conversion by moment, and agent-run cost distribution. Add taster redemption (assumed 30%), taster cache hit rate (assumed 35%), paid conversion of tasted against untasted users (the taster needs a lift of 0.4 to 0.6 points), the share of Family households near the $3.00 pooled alert, and Group Trip Pass cost against its $3.10 limits-based worst case. Review the "typical usage" assumptions in 5.3 after 60 days.
