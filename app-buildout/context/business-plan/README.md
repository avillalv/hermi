# Hermi business plan: from a personal trip planner to an App Store product

The product name is **Hermi** (see [app-buildout/brand/](../../brand)). The build
specification for the new app lives in [app-buildout/](../../README.md).

Written 2026-09-30. This folder is a plan, not code: nothing in the app has changed yet.

Seven analysts each took one section, read the code, challenged the first round of
recommendations, and drafted their part. Their disagreements were then settled into one set of
decisions (below) that every file follows. Where a file argues against an earlier idea, it says
so in a closing section, so the reasoning stays visible.

## The short answer

- **Can it scale?** Yes, but not as built. Today the app runs on one Windows PC for one household,
  with a shared passcode, and its AI runs on the owner's personal Claude subscription (which cannot
  serve customers). Reaching the App Store means a hosted, multi-user backend, the Claude API, a
  mobile shell, and in-app purchases. Roughly 5 to 6 months of part-time work to a public launch.
- **Can it be profitable?** Yes, if AI is a metered, capped extra on top of cheap API features,
  and if the plan is sold per trip, not per month. Open-ended agents on a schedule would lose money on
  every active user. With the guardrails here, the illustrative month at 10,000 users has about
  54% gross margin from paid plans alone, 61% with affiliate income, and the base-case scenario
  breaks even around month 18 to 22.
- **Is it a big business?** The consumer app alone is a solid side income (base case about $99k
  revenue in year 3, about a third of it affiliate commissions). Going well past that needs more
  than one stream: a concierge booking lane through a host travel agency, group trips, and above all
  a paid version for professional travel advisors. With those, the base case reaches about $572k in
  year 5 and the ambitious case about $2.9M, but anything above about $250k a year needs hiring. The
  first milestone is still to validate demand before rewriting anything.

## Files

| File | What it covers |
|---|---|
| [01-business-plan.md](01-business-plan.md) | Customers, competitors, revenue model, 3-year scenarios, go-to-market, risks, KPIs, kill rule |
| [02-pricing-tiers.md](02-pricing-tiers.md) | Every feature mapped to a tier, AI credits, unit economics, guardrails, paywall moments |
| [03-ai-features-and-costs.md](03-ai-features-and-costs.md) | Moving from the Claude Code CLI to the Claude API, cost of each AI feature, cost controls, evals |
| [04-users-and-accounts.md](04-users-and-accounts.md) | Sign-in, accounts, trip sharing and roles, onboarding, privacy, account deletion, tenant isolation |
| [05-infrastructure.md](05-infrastructure.md) | Hosting, job queue, scheduling, CI/CD, observability, security, infra cost at each scale |
| [06-database-and-data-integrations.md](06-database-and-data-integrations.md) | Schema changes, data migration, flight and places providers and their terms, caching, affiliate tracking |
| [07-local-to-app-store.md](07-local-to-app-store.md) | Mobile approach, frontend changes, in-app purchases, App Review checklist, phased roadmap, launch plan |
| [08-affiliate-revenue.md](08-affiliate-revenue.md) | Every affiliate program researched (lodging, flights, cars, trains, tours, eSIM, insurance and more), higher-commission lanes (concierge through a host agency, group room blocks, in-app hotel booking), placement, compliance, tracking, revenue estimates |
| [09-revenue-expansion.md](09-revenue-expansion.md) | Revenue beyond consumer subscriptions and affiliate links: advisor SaaS, group trips, partner guides, printed trip books, white-label; 5-year scenarios and what it takes to reach $500k and $1M a year |
| [competitive-analysis/](../competitive-analysis/README.md) | TripIt, Trippy, Wanderlog and others: what they do better, what Hermi does better, the gaps, and a plan to win their users (HTML presentation plus brainstorm) |
| [app-buildout/](../../README.md) | Self-contained build specification for Hermi, split into Phase 1 (launch in six months), Phase 2 and Phase 3: product spec, architecture, database, API, UI, AI, monetization, admin control center, roadmap, quality and launch |

Suggested reading order: this page, 01, 02, 07 (the roadmap), then 03 to 06 as each phase starts.

## Decisions of record

Every file uses these. If a number changes, change it here first.

### Product and pricing

| Decision | Value |
|---|---|
| Launch tiers | Phase 1 (launch, month 6): Free, Plus, Trip Pass, credit packs. Phase 2 (months 7 to 12): Family, Group Trip Pass with polls, manual cost splitting and room-block requests, Pro. Phase 3 (year 2+): Stripe group payments, advisors, print, LiteAPI. See [app-buildout/](../../README.md). |
| Free | $0. 2 active trips, 1 cached-fare route per trip, 12 AI credits a month, one lifetime deep agent run as a taster (served from the shared cache when possible), 1 price alert on cached fares, invite 1 collaborator per trip (couples plan free; competitors such as Wanderlog make collaboration free), offline reading, joins others' trips free, affiliate booking links, "Before you go" checklist |
| Plus | $5.99 a month or $39.99 a year (7-day trial on annual only; annual is pre-selected). Unlimited trips (fair use 25), 3 live-tracked routes checked daily within 120 days of departure, 60 credits a month (enough for one deep agent run plus extras), collaboration |
| Family | $8.99 a month or $59.99 a year. Everything in Plus for up to 6 people in one household, 150 pooled credits a month, 5 live routes. Apple Family Sharing stays off; members are invited in the app. |
| Trip Pass (lead offer) | $9.99 once. Upgrades one trip for 90 days: 2 live routes, at most 60 live checks, 40 credits, up to 6 collaborators. Sold as a non-renewing subscription in StoreKit, bound to the trip on the server. |
| Group Trip Pass | $19.99 once. Like Trip Pass for groups: up to 12 travelers, 3 live routes (at most 90 live checks), 80 credits, polls and cost splitting, room-block request. Non-renewing subscription bound to the trip. |
| Pro (later; was "Premium") | $11.99 a month or $99 a year. 240 credits a month (about 6 deep agent runs), 6 live routes, scheduled agent routines, priority queue. Launches when measured agent cost is $0.60 or less per run over 200 runs, or when more than 15% of Plus payers buy agent-run credits. |
| Credit packs | $2.99 for 50, $6.99 for 150, $14.99 for 400. Purchased credits last 12 months and are spent last. |
| Collaboration | Only the trip owner pays. Invitees join free and get the owner's tier on that trip. AI credits are charged to the person who starts the action. |
| Ads | No banner ads. Affiliate commissions are the free-tier income; see the affiliate table below. |
| Apple commission | 15% (Small Business Program, under $1M a year in proceeds) |

### AI credits and cost ceilings

| Decision | Value |
|---|---|
| Credit unit | 1 credit is a budget of up to $0.02 of provider spend (Claude, SerpApi, Geoapify) |
| Credit prices | Haiku explain 1, live flight or rental search 1, itinerary day 1, whole-trip draft 4, research question 8 (1 if served from the shared cache), deep agent run 40 (hard stop at $0.80; 8 if served from the shared cache) |
| Agent run caps | 20 turns, 10 web searches, 10 page fetches, effort `medium`, $0.80 hard stop, one run at a time per account |
| Research question caps | 5 searches, 8 fetches, $0.16 hard stop |
| Monthly provider-spend ceiling per account | Free $0.25 (plus the one-time $0.80 taster run), Plus $2.25, Family $3.40 pooled, Trip Pass $1.80 per pass, Group Trip Pass $3.60 per pass, Pro $5.50. Daily: Free $0.05, Plus, Family and passes $0.40, Pro $1.25. Cached data keeps working when a ceiling is hit. A deep agent run is admitted if the month has $0.80 of headroom, even above the daily budget; its spend still counts toward that day, so no other paid actions run until the next day. |
| Models | Claude Haiku 4.5 for short answers and page summaries; Claude Sonnet 5.5 for drafting, research and agents |
| Batch API | Only for offline jobs: shared-cache warming, nightly digests, scheduled fare scans. Never for multi-turn agents or anything a user is waiting on. |
| Scheduled agents | Off for everyone until Pro. Scheduled work is API price checks plus cheap batch scans, not agents. |

### Affiliate revenue

| Decision | Value |
|---|---|
| Who sees affiliate links | Every tier, in the same places. Paid tiers never lose them and free results are never degraded. |
| Launch networks | Travelpayouts (flights: Aviasales, Kiwi.com, Trip.com; stays: Booking.com, Agoda, Trip.com, Hostelworld; cars: DiscoverCars, Localrent; transfers; tours; eSIM; insurance), Viator's self-service partner API for things to do, Stay22 as the lodging challenger |
| From month 3 | Apply directly to Expedia Group (the only route to Vrbo, plus Expedia and Hotels.com), Booking.com (confirm its current network), Skyscanner, Airalo and GetYourGuide |
| Airbnb | No affiliate program an app can join (Associates closed in 2021; creator tracks are invite-only for influencers; host referrals pay for new hosts, not guest bookings). Airbnb listings get a plain link, never a converted one. |
| Pasted listing links | Stay exactly as pasted. A separate, labeled "Book via partner" button offers a partner link built from the URL text (never by fetching the page). |
| Pages of Airbnb, Vrbo and Booking.com | Never fetched by the hosted server, not even for a user-requested preview |
| Tracking | Our own redirect (`/go/<click_id>`) with a random per-click sub-id. No ad or attribution SDKs, no device ids, so no App Tracking Transparency prompt. |
| Disclosure | "We earn a commission if you book here." next to every partner button; an "Ad" label on UK and EU storefronts; lists say how they are sorted and are never ranked by commission |
| New surfaces | A "Before you go" checklist (at least half its items unmonetized; visas link to official sites first; insurance uses insurer-approved copy only and AI never gives insurance advice) and an after-trip "Was your flight delayed?" compensation prompt |
| Not at launch | Credit cards, VPNs, Amazon product data in the app |
| Revenue assumption | $0.10 / $0.60 / $1.50 per monthly user per year (conservative / base / optimistic), about $1 per planned trip in the base case; lodging is about 60% of it |

### Revenue beyond subscriptions and links

| Decision | Value |
|---|---|
| Concierge lane (year 1 to 2) | Optional "Have a human book this" on stays, cruises and complex trips, fulfilled by the founder as an advisor under a host travel agency (for example Fora). Earns the agency commission (hotels about 8 to 15%, cruises 10 to 16%, host split 70 to 90%) and gives users perks (breakfast, credits, upgrades). Disclosed, never pushed. |
| Group trips (year 1 to 2) | Group Trip Pass, polls, cost splitting, and hotel room-block requests for weddings and events. Payments for real-world costs go through Stripe, outside Apple In-App Purchase. |
| In-app hotel booking (year 2+) | LiteAPI (Nuitee) as merchant of record, 5 to 15% margin, only after click data shows strong booking intent |
| Hermi for Advisors (year 2+) | Web SaaS for independent travel advisors: client trip workspaces, branded presentation mode, proposals, commission tracking. $29 a seat a month or $24 annual, billed by Stripe on the web. The largest single growth stream. |
| Partner guides (year 2+) | Tourism boards and hotel brands sponsor clearly labeled destination guides. Never mixed into rankings, never paid placement in search results. |
| Printed trip books (year 2) | Print-on-demand trip books and posters from presentation mode, ordered on the web |
| White-label and API (year 3+) | Licensed planner for agencies and tour operators |
| Not doing | Selling user data, banner ads, cashback that ranks by commission, lifetime subscriptions |
| Scenarios | Year 5 revenue: conservative about $38k, base about $572k, ambitious about $2.9M. A solo founder tops out around $150k to $250k a year; beyond that needs 2 to 3 people, and $1M+ needs a small funded team. Details in [09-revenue-expansion.md](09-revenue-expansion.md). |

### Technology

| Decision | Value |
|---|---|
| AI integration | Claude Messages API with tool use, run in our own worker. The existing ingest tools (`submit_flight_quotes`, `add_note`, `finish_run`) become in-process client tools, and the evidence rules and blocked domains (Airbnb, Vrbo, Booking) stay. Managed Agents was considered and deferred. |
| Identity | Supabase Auth for sign-in only (Sign in with Apple, Google, email code). Our own `users` table in our own database. |
| Hosting | Render (API, worker, managed Postgres with point-in-time recovery) behind Cloudflare (DNS, WAF, R2 storage, Pages for the web app). Move to AWS or Google Cloud around 50k MAU or $1,500 a month. |
| Jobs | Postgres-backed queue (Procrastinate). No Redis until about 10k MAU. |
| Database | Postgres with Alembic migrations run as a pre-deploy step, not at server start. Trip-scoped membership (`trip_members`), UUID public ids, row-level security as a second layer behind app checks. The existing `people` table is kept and gains `owner_user_id` and `linked_user_id`. |
| Flight data | Travelpayouts cached fares as the free baseline. Live fares go through a provider interface: SerpApi behind a feature flag at launch (legal risk flagged), with a licensed source (Skyscanner Partners) applied for now. |
| Mobile | Capacitor around the existing React app, bundled (not a remote URL). The hosted web beta ships before iOS. |
| Payments | RevenueCat over StoreKit 2, with entitlements stored on our server |
| Build machine | iOS builds need macOS: a Mac mini or Xcode Cloud |

### Roadmap

| Phase | Effort (part time, solo, with Claude Code) | Gate to move on |
|---|---|---|
| M0: validate | 2 to 4 weeks | Landing page, waitlist, 10 user interviews, a clear signal people want it |
| 0: foundations | 3 to 4 weeks | Agents run on the Claude API with metering; Docker image; CI |
| 1: hosted web beta | 6 to 8 weeks | Accounts, sharing, entitlements, ledger; 4-week retention measured |
| 2: iOS TestFlight | 5 to 7 weeks | Capacitor app, purchases, push, account deletion |
| 3: public launch | 3 to 4 weeks | App Review passed, support and monitoring in place |
| 4: growth | Ongoing | Android, shareable trip pages for SEO, Pro, Hermi for Advisors |

**Kill rule:** at month 9 after launch, if under 1% of monthly users pay and affiliate income is
under $0.20 per monthly user per year (annualized), stop investing and keep it as a personal tool.

## Open questions to verify before launch

These could not be confirmed from here and could change the numbers:

1. SerpApi's current price per search and whether its terms allow use in a paid consumer app
   (Google sued SerpApi in December 2025; the case was still active in September 2026).
2. Geoapify's commercial-use and caching terms on paid plans.
3. Affiliate commission rates, cookie windows and app eligibility for every program in
   [08-affiliate-revenue.md](08-affiliate-revenue.md): the official partner sites were blocked
   from here, so all rates came from third-party reports.
4. The real cost of an API agent run: measure 200 runs before setting Pro live.
5. Apple's current rules on linking out to web checkout in the US.
6. Competitor prices (taken from third-party reviews on 2026-09-30).
