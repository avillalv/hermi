# Business plan

Part of the [business plan](README.md). The decisions of record in the README override anything here.

Written 2026-09-30. Tier and price detail is in [02-pricing-tiers.md](02-pricing-tiers.md). Every revenue stream beyond subscriptions and affiliate links, and the five-year scenarios, are in [09-revenue-expansion.md](09-revenue-expansion.md); the totals here agree with it.

## Executive summary

Hermi (working name until now: Trip Planner) is today a private app for two people on one Windows PC. It already has the parts of a credible trip product: flight price tracking (cached Travelpayouts fares and live Google Flights fares via SerpApi), a drag-and-drop day calendar, Geoapify places search, a lodging shortlist that never scrapes booking sites, Wikipedia destination summaries, a full-screen presentation mode, and agent routines that use Claude to hunt fares and research events with a source URL for every saved fact.

The plan is to turn it into a multi-user web and iOS product. It launches with Free, Plus, Family, Trip Pass, Group Trip Pass and credit packs. Pro is built behind a flag and launches later. Five beliefs drive the plan:

1. The product is a collaborative trip workspace with trustworthy price tracking, not an "AI trip planner". AI is a metered, capped extra.
2. Most users pay little or nothing. Money comes from a small paying minority, sold per trip first, plus affiliate commissions on bookings.
3. AI cost is controlled by design (per-account cost ceilings, run caps, shared cache, Batch API for offline jobs only), or heavy users lose money.
4. The consumer app alone (subscriptions plus affiliate links) is a side income: about $99k of revenue in year 3 in the base case, about $269k in year 5.
5. A bigger business needs more than one stream: a concierge booking lane through a host travel agency, group trips, and above all a paid web product for professional travel advisors. With those, the base case reaches about $572k in year 5. Anything above about $150k to $250k a year needs hiring: a solo founder tops out there.

Five-year headline numbers (full tables in [Five-year scenarios](#five-year-scenarios)):

| Scenario | Year 3 MAU | Year 3 revenue | Year 5 MAU | Year 5 revenue | Year 5 profit (before founder pay) |
|---|---|---|---|---|---|
| Conservative | 12,000 | about $11.5k | 25,000 | about $38k | about +$11k |
| Base | 60,000 | about $144k | 150,000 | about $572k | about +$127k |
| Ambitious | 150,000 | about $688k | 500,000 | about $2.87M | about +$807k |

The base case needs two to three people by year 4. The ambitious case needs a proven sharing loop the product does not yet show, plus funding or reinvested profit. Affiliate income is $0.10, $0.60 and $1.50 per MAU per year in the three cases in year 1 to 3 (see [Affiliate revenue](#affiliate-revenue)); it is the least certain input.

The decision that matters most: do not rewrite for the App Store until milestone M0 (validate) shows people want it. See [Milestones](#milestones).

## Problem and target customers

Planning a trip is spread across a flight tab, a notes app, a spreadsheet, chat threads and hotel screenshots. Two pains are poorly served:

- Fare timing. People do not know if a price is good, and alerts from big apps are noisy and unexplained. Nobody shows "here is the page where I saw this fare".
- Group coordination. Several people editing one plan, with clear conflict handling (the app refuses stale edits and shows the latest version), is still clumsy in TripIt and Google Docs. Polls and cost splitting are the next gap.

| Persona | Who | What they pay for | Fit |
|---|---|---|---|
| Couple planner (primary) | Two adults planning 1 to 3 trips a year, one of them the organizer | Shared calendar, price alerts, presentation mode | Strong. The exact use case the app was built for. |
| Friend group organizer | 4 to 8 people, one organizer chases everyone | Collaboration, polls, cost splitting, lodging votes | Strong for growth (each trip invites 3 to 7 people). Only the organizer pays, which suits Trip Pass and Group Trip Pass. |
| Family planner | Parents, school-holiday limits, higher spend | Itinerary, printable PDF, lodging comparison, Family plan | Medium. Willing to pay, but needs kid-friendly filters not yet built. |
| Deal hunter | Flexible dates, chases fares | Live fare tracking, date grid, agent fare hunt | Best future Pro payer, but small (perhaps 5 to 10% of users), price sensitive, and the most likely to abuse free tiers. |
| Casual dreamer | Browses, rarely books | Nothing | Free tier. Feeds affiliate clicks and the shared cache. |
| Independent travel advisor (year 2 and later) | Books trips for clients, often under a host agency | Client workspaces, branded presentations, proposals, commission tracking | The largest single growth stream. Sold on the web as Hermi for Advisors; see [09](09-revenue-expansion.md). |

Launch target: couples and friend-group organizers who fly internationally at least once a year. Business travelers are out of scope (TripIt owns them).

## Value proposition and differentiation

1. Evidence-backed fare hunting. Agent results are marked "indicative" and always carry a public source link, route, dates and currency (enforced by the ingest API). Competitors show a price with no provenance. This is a real trust differentiator only if the hunt finds fares people cannot find in Google Flights (budget carriers, sales, deal posts).
2. Prices tracked over time in one place: history chart, date grid, per-night cost, cheapest by trip length.
3. Collaborative planning with safe concurrent edits. Only the trip owner pays; invitees join free.
4. Presentation mode: a full-screen deck and printable PDF of the trip. Demo-friendly and shareable, so the best organic marketing asset, and the base of the advisor product.
5. A lodging shortlist that respects site terms (bookmarklet and pasted links, no scraping) with side-by-side compare. This is a legal moat as much as a feature.

None of these is hard to copy. Wanderlog already has collaboration and maps at about $40 a year. The defensible part is the combination, the evidence rule and execution speed. Do not pitch "AI-powered": ChatGPT, Layla and Mindtrip own that message.

Positioning: "Plan the trip together, and never overpay for the flight without knowing why."

## Market and competitors

Prices below come from third-party review sites (checked 2026-09-30). Verify each on the vendor's own page before publishing any comparison.

| Competitor | Free tier | Paid price found | Notes |
|---|---|---|---|
| Wanderlog | Generous, ad supported | Pro about $39.99 a year (range $39.99 to $49.99 in mid 2026) | Closest rival: collaborative itinerary, maps, offline. Reported $1M revenue in June 2024 with 5 staff (reported, verify). |
| TripIt | Basic organizing from email | Pro $49 a year, 30 day trial | Business travelers and frequent flyers. |
| Layla | Limited free chats | Premium about $49 to $50 a year | AI chat planner, live pricing, price alerts. |
| Mindtrip | Core planning free | No subscription found; moving to book-and-earn commission in 2026 | Same affiliate strategy we use. |
| Hopper | Free app | No subscription found; earns from booking fees and add-ons | Price-prediction brand. Do not compete head on. |
| Google Flights | Free | Free | Price tracking and date grid are free. This caps what tracking alone can charge. |
| ChatGPT | Free and $20 a month plans | $20 a month | Free to ask "plan 5 days in Lisbon". |
| Tern, Travefy, TravelJoy | Trials | Advisor software from $19 to $49 a seat a month (reported, verify) | Price anchors for Hermi for Advisors. |

What the prices tell us:

- Direct rivals sell annual plans at $40 to $50. Plus at $39.99 a year matches Wanderlog and undercuts TripIt and Layla, and the $5.99 monthly plan is a clearly worse deal than annual (12 x $5.99 = $71.88). Pro at $99 a year is about double, so it must offer something rivals lack. That is one reason Pro launches later.
- Google Flights tracks fares free, so "live tracking" alone converts poorly. People pay for tracking bundled with the workspace, or for a hunt that finds what Google cannot.
- Nobody charges for an AI planner by itself (Mindtrip and Tripadvisor are free), so AI is sold as an allowance inside the workspace, not as the headline.
- There is no verified market-size figure here and none is invented. Tens of millions of people plan trips with apps each year; the constraint is acquisition cost, not market size.

## Revenue model

The lead offer is Trip Pass, then annual Plus. Family, Group Trip Pass and credit packs are extras; Pro follows later. Beyond subscriptions and links, six more streams are planned (full detail, pricing, costs, regulatory needs and math in [09-revenue-expansion.md](09-revenue-expansion.md)).

| Stream | Starts | Base case year 3 | Base case year 5 | Notes |
|---|---|---|---|---|
| Subscriptions, passes and packs (Plus, Family, Trip Pass, Group Trip Pass, Pro, credit packs) | Launch | $59.5k (41%) | $148.8k (26%) | Sold through the App Store at 15% (Small Business Program, under $1M a year in proceeds). Trip Pass and Group Trip Pass are non-renewing subscriptions bound to the trip on the server. |
| Affiliate links (lodging first, then tours, flights, cars, transfers, eSIM, insurance, post-trip compensation) | Launch | $39.0k (27%) | $120.0k (21%) | Earned on free and paid users alike, in the same places on every tier. Payout is delayed and lumpy. Lodging is about 60% of it. See [08](08-affiliate-revenue.md). |
| Hermi for Advisors (web SaaS, $29 a seat a month or $24 billed annually) | Year 2 build, seats in year 3 | $18.9k (13%) | $141.4k (25%) | Largest growth stream. Sold on the web through Stripe. |
| Group trips: events workspace ($79 an event) and payment collection (1.5% fee) | Pass at launch; events and payments in year 3 | $3.8k (3%) | $56.3k (10%) | Payments need legal review. Stripe, outside In-App Purchase. |
| Partner guides (labeled tourism-board guides) and white-label | Year 2 pilot, year 3 revenue | $12.0k (8%) | $72.0k (13%) | Sales heavy. Never mixed into rankings. |
| Printed trip books and creator guides | Year 2 | $10.5k (7%) | $33.9k (6%) | Print on demand, shown at contribution. |
| Concierge lane via a host agency | Year 1 | Not in totals, about $27k | Not in totals, about $54k | Optional "Have a human book this", fulfilled by the founder. Capped at about 300 bookings a year solo. |
| In-app hotel booking (LiteAPI) | Year 3 | Not in totals, about $11k | Not in totals, about $72k | Only after click data shows booking intent. |

Shares are of the base total ($143.7k in year 3, $572.5k in year 5) and are rounded, so year 5 sums to 101%. Concierge and LiteAPI are left out of the totals because they depend on founder hours or an untested merchant setup; if both work they add about $126k to base year 5 (see [09](09-revenue-expansion.md), section 6.4). Credit cards are deferred to about 100k MAU.

Pack revenue is counted inside the subscription line in the scenarios.

### Why no banner ads

- At 10k to 60k MAU, ads earn under $1 per MAU per year and compete with affiliate links for the same attention.
- Ad SDKs add tracking and consent flows (ATT, GDPR) and lower the trust the fare-evidence story depends on.
- Ads next to a price list look like they influence which fare is shown.
- They slow the app and presentation mode, the shareable showpiece.

Decision: no ad networks. Affiliate links are labeled and never change fare ranking. Also rejected: selling user data, cashback that ranks by commission, and lifetime plans (reasons in [09](09-revenue-expansion.md), section 4).

### Affiliate revenue

Affiliate links appear on every tier in the same places (see [02-pricing-tiers.md](02-pricing-tiers.md)). The full program research, placement map, compliance, tracking design and the higher-commission lanes (concierge through a host agency, group room blocks, in-app booking) are in [08-affiliate-revenue.md](08-affiliate-revenue.md). Summary:

- **Categories, in order of expected money:** lodging first (about 60% of affiliate income), then tours and activities, flights, cars, transfers, eSIM, travel insurance, and post-trip flight-delay compensation. Flights are a service feature more than a revenue line: airline commissions are tiny (a flat few dollars or about 1% of the fare).
- **Launch networks:** Travelpayouts (flights, Booking.com, Agoda, Trip.com and Hostelworld stays, cars, transfers, tours, eSIM, insurance), Viator's self-service partner API for things to do, and Stay22 as the lodging challenger. From month 3, apply directly to Expedia Group, Booking.com, Skyscanner, Airalo and GetYourGuide.
- **Airbnb:** no affiliate program an app can join. The old Associates program closed in 2021, the current creator and demand tracks are invite-only for influencers and bloggers, and the host-referral reward pays for new hosts, not guest bookings. Airbnb listings get a plain link with no tracking, never a converted one.
- **Vrbo:** reachable only through the Expedia Group affiliate program (which also covers Expedia and Hotels.com, run on Impact), with Stay22 as a second route. Reported Vrbo rates are about 2 to 6% and inconsistent, so the plan uses the low side.
- **Tracking:** an own redirect (`/go/<click_id>`) with a random per-click sub-id, no ad or attribution SDKs and no device ids, so no App Tracking Transparency prompt. Attribution can still be lost in in-app browsers and across devices, which is built into the numbers below.
- **Apple:** links to physical travel services are allowed; digital goods (our plans) must use in-app purchase. Confirm the current guideline text (3.1.1 and 3.1.3(e)) and US external-purchase rules before launch.

Assumption per MAU per year, from the model in 08 (real trips per MAU x attribution survival x clicks x click-to-booking x net commission, summed over categories). The scenarios use $0.10, $0.60 and $1.50 in years 1 to 3; the base case rises to $0.80 by year 5 as direct programs are added.

| | Conservative | Base | Ambitious |
|---|---|---|---|
| Affiliate revenue per MAU per year | $0.10 | $0.60 | $1.50 |
| Per MAU per month | about $0.01 | $0.05 | about $0.13 |

The $0.60 base case is about $1 per planned trip. The per-MAU figures are guesses built from third-party rate reports (the official partner sites could not be read), and they are the first thing to measure. Treat them as a floor that pays for infrastructure, not the growth plan. The higher-commission lanes could lift revenue per trip from about $1.04 to roughly $4 to $17, but only with founder hours, tested attach rates and (for in-app booking) a support process; see [08](08-affiliate-revenue.md) section 13.

## Unit economics per tier

Net revenue is after Apple's 15%. The worst-case cost is the per-account monthly provider-spend ceiling plus infrastructure; typical users spend far less. Full detail is in [02-pricing-tiers.md](02-pricing-tiers.md) and [09](09-revenue-expansion.md) section 2, and AI costs in [03-ai-features-and-costs.md](03-ai-features-and-costs.md).

| Tier | Price | Net after Apple | Ceiling a month | Worst-case margin | Typical margin |
|---|---|---|---|---|---|
| Free | $0 | $0 | $0.25, plus a one-time taster run (about $0.11 to $0.17 per new free user) | Roughly break-even: typical cost $0.01 to $0.02 against affiliate income of about $0.05 a month in the base case | n/a |
| Plus monthly | $5.99 | $5.09 | $2.25 | 53% | 80% |
| Plus annual | $39.99 | $33.99 ($2.83 a month) | $2.25 | 16% | 65% |
| Family monthly | $8.99 | $7.64 | $3.40 pooled | 53% | 79% |
| Family annual | $59.99 | $50.99 ($4.25 a month) | $3.40 pooled | 15% | 62% |
| Trip Pass | $9.99 once | $8.49 | $1.80 per pass | 78% | 90% |
| Group Trip Pass | $19.99 once | $16.99 | $3.60 per pass | 78% | 92% |
| Pro monthly (later) | $11.99 | $10.19 | $5.50 | 45% | 65% |
| Pro annual (later) | $99 | $84.15 ($7.01 a month) | $5.50 | 20% | 50% |

Worst-case margins include $0.10 to $0.20 a month of infrastructure. Annual Plus and Family are thin only if the ceiling is hit every month, which the usage pattern (2 to 4 active months a year) makes unlikely; Family is watched with an alert at $3.00 of pooled spend.

The Pro allowance is the whole margin. 240 credits a month is about 6 deep agent runs, each hard-stopped at $0.80, and the $5.50 monthly ceiling caps the total. Pro launches only when measured agent cost is $0.60 or less per run over 200 runs, or when over 15% of Plus payers buy agent-run credits.

Blended assumptions used in the scenarios:

- Blended net revenue per paying user per year (ARPPU): $28.34 in all three cases (mix of 34% Plus annual, 8% Plus monthly, 34% Trip Pass, 8% Group Trip Pass, 8% Family, 8% Pro, plus packs).
- Variable AI and data cost: $0.30 per free MAU per year (including the taster) and $9 per paying user per year (after the ceilings and caches).
- Payment processing is inside Apple's 15% for consumer plans, and about 3% for web-sold advisor, event and print revenue.

## Cost structure

| Cost | Estimate | Notes |
|---|---|---|
| Apple Developer Program | $99 a year | Required. |
| iOS build machine | Mac mini or Xcode Cloud | iOS builds need macOS. |
| Hosting (Render API, worker, managed Postgres; Cloudflare DNS, WAF, R2, Pages) | $40 to $150 a month in year 1 | Enough for the first 10k MAU. Move to AWS or Google Cloud around 50k MAU or $1,500 a month. See [05-infrastructure.md](05-infrastructure.md). |
| Sign-in and payments | Supabase Auth; RevenueCat over StoreKit 2; Stripe for web revenue | Verify current pricing and free limits. |
| SerpApi (live Google Flights) | Unverified at scale; budget $75 to $300 a month | Behind a feature flag at launch (legal risk flagged), with a licensed source (Skyscanner Partners) applied for. Per-search cost drives the live-check caps. |
| Travelpayouts cached fares | Free | Free baseline for cached fares. Terms for a public app must be checked. |
| Geoapify | Free up to a daily limit, then paid | Results cached for a week. Check commercial terms. |
| Claude API | Variable, see [Unit economics](#unit-economics-per-tier) | Haiku 4.5 for short answers, Sonnet 5.5 for drafting, research and agents. |
| Email, push, analytics, error tracking | $30 to $100 a month | |
| Legal (privacy policy, terms, affiliate disclosures) and accounting | $1,500 to $4,000 in year 1 | |
| Concierge lane: host agency fee, E&O insurance, seller-of-travel registrations | About $1.4k to $2.2k a year (reported, verify) | Fora about $99 a quarter, E&O $400 to $1,200, state registrations about $640. See [09](09-revenue-expansion.md). |
| Support | Founder time | Budget 5 to 10 hours a week from 5,000 MAU, plus about 10 hours a week per 100 advisor seats. |

What must change technically (owned by the other files) drives cost and timeline: real accounts instead of one passcode ([04-users-and-accounts.md](04-users-and-accounts.md)), a multi-tenant database ([06-database-and-data-integrations.md](06-database-and-data-integrations.md)), a hosted worker with a queue, per-account quotas, and moving agents from `claude -p` on a personal subscription to the Claude API. That last change is a legal and cost necessity: a personal subscription cannot serve customers.

## Five-year scenarios

All figures are US dollars, rounded. Year 1 is the first year after public launch. "Avg MAU" is the average over the year. Net profit excludes founder pay and taxes. These are planning models, not forecasts. They are the same scenarios as [09-revenue-expansion.md](09-revenue-expansion.md), which holds the full assumptions and worked lines.

All three scenarios use the launch lineup (Free, Plus, Family, Trip Pass, Group Trip Pass, packs), with Pro included in the payer mix. Advisor seats begin in year 3 in the conservative and base cases and in year 2 in the ambitious case.

### Assumptions

| Assumption | Conservative | Base | Ambitious |
|---|---|---|---|
| Avg MAU years 1 to 5 | 1k, 5k, 12k, 18k, 25k | 3k, 20k, 60k, 100k, 150k | 8k, 50k, 150k, 300k, 500k |
| Paid conversion (of MAU) | 2% | 3.5% | 5% |
| Blended net ARPPU per year | $28.34 | $28.34 | $28.34 |
| Affiliate per MAU per year, years 1 to 5 | $0.10, 0.10, 0.10, 0.12, 0.15 | $0.60, 0.62, 0.65, 0.72, 0.80 | $1.00, 1.20, 1.40, 1.50, 1.60 |
| Advisor seats, average, years 1 to 5 | 0, 0, 10, 30, 60 | 0, 0, 60, 200, 450 | 0, 100, 400, 1,000, 2,000 |
| Variable cost | $0.30 per free MAU, $9 per payer | same | same |
| Fixed (infrastructure, tools, legal) years 1 to 5 | $4k, 6k, 6k, 8k, 10k | $6k, 10k, 18k, 30k, 45k | $10k, 25k, 50k, 90k, 150k |
| Marketing years 1 to 5 | $1k, 2k, 3k, 4k, 5k | $5k, 10k, 20k, 40k, 60k | $10k, 80k, 150k, 250k, 350k |
| Paid team years 1 to 5 | $0 | $0, 0, 40k, 120k, 250k | $0, 120k, 350k, 700k, 1,200k |

Marketing is deliberately low in the first two scenarios: they assume organic growth only. Other stream inputs (events, partner guides, white-label, print) are in [09](09-revenue-expansion.md) section 6.1.

### Results

Conservative:

| | Y1 | Y2 | Y3 | Y4 | Y5 |
|---|---|---|---|---|---|
| Paying users | 20 | 100 | 240 | 360 | 500 |
| Subscriptions, passes, packs | $0.6k | $2.8k | $6.8k | $10.2k | $14.2k |
| Affiliate | $0.1k | $0.5k | $1.2k | $2.2k | $3.8k |
| Advisor seats | 0 | 0 | $3.1k | $9.4k | $18.9k |
| Print and creator guides | 0 | $0.2k | $0.4k | $1.0k | $1.4k |
| Total revenue | $0.7k | $3.5k | $11.5k | $22.8k | $38.2k |
| Net profit | -$4.8k | -$6.9k | -$3.2k | +$2.3k | +$11.3k |

Base:

| | Y1 | Y2 | Y3 | Y4 | Y5 |
|---|---|---|---|---|---|
| Paying users | 105 | 700 | 2,100 | 3,500 | 5,250 |
| Subscriptions, passes, packs | $3.0k | $19.8k | $59.5k | $99.2k | $148.8k |
| Affiliate | $1.8k | $12.4k | $39.0k | $72.0k | $120.0k |
| Advisor seats | 0 | 0 | $18.9k | $62.9k | $141.4k |
| Events, groups, payments | 0 | 0 | $3.8k | $23.3k | $56.3k |
| Partner guides, white-label | 0 | 0 | $12.0k | $36.0k | $72.0k |
| Print and creator guides | 0 | $2.4k | $10.5k | $22.6k | $33.9k |
| Total revenue | $4.8k | $34.7k | $143.7k | $316.0k | $572.5k |
| Variable cost | $1.8k | $12.1k | $36.3k | $60.5k | $90.7k |
| Net profit | -$8.0k | +$2.6k | +$29.4k | +$65.5k | +$126.8k |

Ambitious:

| | Y1 | Y2 | Y3 | Y4 | Y5 |
|---|---|---|---|---|---|
| Paying users | 400 | 2,500 | 7,500 | 15,000 | 25,000 |
| Subscriptions, passes, packs | $11.3k | $70.8k | $212.5k | $425.0k | $708.4k |
| Affiliate | $8.0k | $60.0k | $210.0k | $450.0k | $800.0k |
| Advisor seats | 0 | $31.4k | $125.7k | $314.3k | $628.6k |
| Events, groups, payments | 0 | $1.5k | $37.8k | $136.3k | $278.3k |
| Partner guides, white-label | 0 | $14.0k | $56.0k | $140.0k | $280.0k |
| Print and creator guides | 0 | $10.1k | $45.9k | $107.4k | $178.9k |
| Total revenue | $19.3k | $187.9k | $687.9k | $1,573.0k | $2,874.1k |
| Variable cost | $5.9k | $36.8k | $110.3k | $220.5k | $367.5k |
| Net profit | -$6.6k | -$73.9k | +$27.7k | +$312.5k | +$806.6k |

Totals by year, revenue: conservative $0.7k, $3.5k, $11.5k, $22.8k, $38.2k; base $4.8k, $34.7k, $143.7k, $316.0k, $572.5k; ambitious $19.3k, $187.9k, $687.9k, $1.57M, $2.87M.

Consumer-only view, for comparison with the earlier plan (subscriptions plus affiliate): base year 1 to 3 is $4.8k, $32.2k, $98.5k (year 3: $59.5k + $39.0k); conservative year 3 is $8.0k; ambitious year 3 is $422.5k. The old three-year base case ($99k in year 3) is this consumer-only line, so nothing earlier was overstated; the new streams add about $45k in year 3 and most of the growth after it.

Arithmetic, year 3 base: 60,000 MAU x 3.5% = 2,100 payers x $28.34 = $59.5k; affiliate 60,000 x $0.65 = $39.0k; advisors 60 x $314.28 = $18.9k; events 50 x $76.60 = $3.8k; 1 partner deal plus 1 white-label account = $12.0k; print and guides $10.5k. Total $143.7k, less $36.3k variable, $18k fixed, $20k marketing and $40k team = +$29.4k.

### Break-even

- Fixed costs of about $10k a year need about 520 paying users (each contributes $28.34 less $9 of variable cost = $19.34), or about 9,900 MAU at the base consumer contribution of $1.01 per MAU a year.
- Base-case monthly break-even with the year 2 cost base ($20k a year of fixed and marketing, about $1,670 a month): each MAU contributes 3.5% x $28.34 = $0.99 of subscription revenue, plus $0.62 of affiliate income and about $0.12 of print and guide margin, less about $0.60 of variable cost (0.965 x $0.30 + 0.035 x $9), or about $1.13 a year. Break-even needs about 17,700 MAU ($20,000 / $1.13). With MAU growing about 1,400 a month through year 2, that is roughly **month 18 to 22**. Year 2 as a whole is slightly profitable (+$2.6k) because MAU ends the year well above the break-even level.
- The conservative case does not break even on cash before year 4: in year 3 contribution is $11.5k - $5.7k = $5.8k, so fixed and marketing costs would have to stay under about $6k a year.
- A funded team of two (about $240k a year loaded) needs about 12,400 paying users on consumer alone ($240k / $19.34). Only the ambitious case reaches that (year 4: 15,000). In the base case, advisor seats and partner income fund the team instead: year 5 team cost is $250k against $141k of seat revenue and $72k of partner revenue.

### What has to be true

1. Conversion of 3.5% needs a free tier limited enough to create a need and generous enough to hook users. The benchmark median download-to-paid is about 2.0% to 2.4% (RevenueCat, reported, verify), so 2% is the safer planning number. At 2%, base year 5 consumer subscription revenue falls from $148.8k to about $85k.
2. 60,000 MAU in 3 years needs a working acquisition loop. Paid installs for a travel app are expensive (an unverified $2 to $6) and would erase Plus margin. Organic loops (shared trips, SEO, invites) are mandatory.
3. Retention is the structural problem. People use a trip app for 1 to 3 months before a trip, then leave. AI apps also churn faster than others (reported about 30%). This is why Trip Pass and annual plans lead.
4. Affiliate at $0.60 per MAU is unproven. At $0.20, base year 3 revenue falls by about $24k (60,000 x $0.40).
5. The advisor market is real but unmeasured: 60,000 core advisors is the owner's figure, a trade report says 310,000 (reported, verify), and host agencies bundle tools. The base case needs 450 average seats by year 5 (0.75% of 60,000). Interview 15 advisors before building.
6. Agent cost must be measured before Pro goes live: $0.60 or less per run over 200 runs. The cost ceilings limit the damage if it is not.
7. Apple's 15% applies only under $1M a year in proceeds, which no scenario exceeds (ambitious consumer gross in year 5 is about $0.83M). Above that it is 30% in the first subscription year.

## Go-to-market

| Channel | Tactic | Cost | Expected role |
|---|---|---|---|
| Referral via shared trips | Every invite to a co-planner is a signup; invitees join free. A small organizer reward is to be tested. | Low | Main viral loop, especially friend groups. |
| Reddit and forums | r/travel, r/solotravel, r/digitalnomad, r/awardtravel. Share fare findings with evidence; mention the app only when relevant, within each subreddit's rules. | Time | Good for deal hunters. |
| TikTok and Reels | 20 to 40 second clips: "I tracked this flight for 30 days", screen recordings of presentation mode. | Time, small creator budget | Awareness and downloads more than conversion. |
| Product Hunt and travel newsletters | One launch plus pitches to small newsletters | Low | One-off spike. |
| ASO (App Store search) | Keywords: trip planner, flight price tracker, group itinerary | Low | Steady trickle. |
| Shareable trip pages (SEO) | Public read-only pages from presentation mode ("5 days in Lisbon for two") with a "Copy this trip" button. Built in phase 4. | Engineering | Primary long-term engine. Needs quality content, not spam. |
| Creators and travel bloggers | Copy-this-trip attribution and a share of affiliate income, 10 to 20 invited creators | Variable | Test in year 2. |
| Wedding and event planners | Group Trip Pass and room-block requests for destination weddings and offsites | Low | Year 1 to 2, feeds the events workspace. |
| Advisor communities and host agencies | Pilot with 10 to 20 advisors, host-agency partnerships, content | Founder time | Year 2, the channel for Hermi for Advisors. |
| Paid ads | Not before organic acquisition cost is known | High | Avoid in year 1. |

Launch sequence (the roadmap is in [07-local-to-app-store.md](07-local-to-app-store.md)):

1. Invite-only hosted web beta with 50 to 100 couples and friend groups from Reddit and personal networks.
2. iOS TestFlight, then the public iOS launch with the lead offer: Trip Pass first, annual Plus second, monthly Plus lower on the paywall.
3. Growth: Android, shareable trip pages, then Pro, the concierge lane and group trips, then Hermi for Advisors.

Positioning rules:

- Lead with "plan together" and "know why a fare is cheap". Mention AI second.
- Show the source link on every agent-found fare in marketing screenshots.
- Publish factual, dated comparison pages (vs Wanderlog, vs TripIt) for SEO.

## Milestones

Effort is part time, solo, with Claude Code: about 5 to 6 months from the start of phase 0 to a public launch.

| Milestone | Effort | Exit criteria |
|---|---|---|
| M0: validate (no rewrite) | 2 to 4 weeks | Landing page, waitlist and 10 user interviews give a clear signal that people want it. Suggested bar: 500 waitlist emails and at least 30% of interviewed couples willing to invite a second person. |
| Phase 0: foundations | 3 to 4 weeks | Agents run on the Claude API with metering; Docker image; CI. |
| Phase 1: hosted web beta | 6 to 8 weeks | Accounts, sharing, entitlements, ledger. 4-week retention measured. |
| Phase 2: iOS TestFlight | 5 to 7 weeks | Capacitor app, purchases, push, account deletion. |
| Phase 3: public launch | 3 to 4 weeks | App Review passed, support and monitoring in place. Group Trip Pass and polls ship with it. |
| Year 1 to 2: concierge and groups | Founder hours | Advisor sign-up under a host agency and seller-of-travel registrations in the states that need them (months 0 to 6 after launch); the "Have a human book this" button; cost splitting (no money moved); hotel room-block request (months 6 to 12). Exit: measured ask rate and commission per booking. |
| Phase 4: growth | Ongoing | Android, shareable trip pages for SEO, Pro (once its gate is met). |
| Year 2: advisors, print, guides | 3 to 4 months of build | Interview 15 advisors first. Hermi for Advisors pilot (web, Stripe), print-on-demand trip books, first partner-guide pilot. Decide on in-app hotel booking (LiteAPI) only if click data shows booking intent. |
| Year 3 and later | Team | First paid partner-guide deals, events workspace and payment collection after legal review, white-label accounts, LiteAPI launch if approved. Revisit credit cards at about 100k MAU. |

Scale decision at month 18 to 24: if MAU is above 15,000 and paying users above 500, invest in growth; otherwise run it as a lean side business.

**Kill rule:** at month 9 after launch, if under 1% of monthly users pay and affiliate income is under $0.20 per monthly user per year (annualized), stop investing and keep it as a personal tool.

## Risks and mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| AI cost overruns | High | High | Per-account monthly and daily cost ceilings, hard stops per run, shared research cache, Haiku for short answers, Batch API for offline jobs only, credits for extras, kill switch on daily spend. The free tier gets one taster run under a global daily budget. Scheduled agents stay off until Pro. |
| Low conversion and high churn (episodic use) | High | High | Trip Pass first, annual Plus second, price by trip not by month, reactivation email before the next trip. |
| Google, Skyscanner or Wanderlog add the same features free | Medium | High | Lean on evidence-backed hunting and collaboration; keep costs low. |
| Data provider terms or cost (SerpApi, Travelpayouts, Geoapify) | Medium | High | Verify commercial terms in M0; SerpApi stays behind a feature flag with a licensed source applied for; cached fares as the free baseline; behind a provider interface so sources can be swapped. |
| Scraping and site terms | Low today | High | Keep the rule: no Airbnb, Vrbo or Booking automation, no scraper libraries. |
| Wrong or stale fares harm trust | Medium | Medium | Keep the "indicative" label, source link, evidence rules and "last checked" time. |
| Apple review or rule changes | Medium | Medium | Read guidelines 3.1.1 and 3.1.3 early; keep a web checkout path where permitted (a proposed 15% fee on link-outs is reported, verify); label affiliate links. |
| Privacy (dates, places, who is traveling) | Medium | High | Data minimization, delete account and export, GDPR and CCPA basics, no selling data, encrypted backups. See [04-users-and-accounts.md](04-users-and-accounts.md). |
| Rewrite from single-user local to multi-tenant slips | High | Medium | Scope tightly: auth, tenancy, quotas first; Pro and agents behind a flag. |
| Seller-of-travel compliance (concierge lane, in-app booking, group payments) | Medium | High | The app refers and a human advisor books under a host agency's credentials. Register where required (for example California, Florida, Washington, Hawaii; reported, verify), carry E&O insurance, get counsel to confirm whether forwarding a request triggers registration, ask the host agency in writing whether app-routed leads are allowed, and never sign hotel contracts for users. Group payment collection waits for legal review and runs through Stripe Connect so Hermi holds no funds. |
| Founder time (concierge bookings, advisor support, partner sales, dual roles) | High | High | Cap concierge at about 300 bookings a year solo and say no beyond that; hire advisors at a 50% split. Add support contractors before 60k MAU or 100 seats; budget 5 to 10 hours a week from 5,000 MAU plus about 10 hours a week per 100 seats. A solo founder tops out around $150k to $250k a year. |
| Advisor market smaller or bundled away | Medium | Medium | Interview 15 advisors before building; pilot through host agencies; keep the product useful to consumers without it. |
| Sponsorship erodes trust | Medium | High | Partner guides are labeled, hideable and never mixed into rankings or search; contracts forbid paid placement. |
| Solo founder support load | Medium | Medium | Self-serve help, in-app status, one platform at launch. |
| Affiliate income much lower than assumed | High | Medium | Measure early; if under $0.20 per MAU per year, shift weight to Trip Pass and Plus. |
| Affiliate rates unverified, and attribution lost in in-app browsers | High | Medium | All rates come from third-party reports because the partner sites were unreadable; confirm each rate card and cookie window at sign-up, and replace the model inputs with measured data by month 3. Open links in SFSafariViewController, use a server-side sub-id per click and nightly conversion pulls instead of cookies alone, watch the unmatched-conversion share (over 10% means a tracking break), and treat attribution survival (0.60 to 0.90 in the model) as a key metric. See [08-affiliate-revenue.md](08-affiliate-revenue.md). |

## KPIs

Acquisition and activation:

- Installs and signups per channel; cost per install for any paid test.
- Activation: share of new users who create a trip and add a flight route or day plan within 7 days (target above 40%).
- Invite rate: share of trips with at least one collaborator (target above 30%); invites per organizer.

Engagement and retention:

- MAU, weekly actives, trips per user, trips departing in the next 90 days.
- Retention by trip cohort (D30, D90) and reactivation at the next trip.

Monetization:

- Free-to-paid conversion (target 2 to 4%), by tier: Trip Pass vs Plus annual vs Plus monthly vs Family vs Group Trip Pass.
- Taster run: share of new free users who redeem it, and the conversion lift (break-even is about 0.4 to 0.6 points).
- ARPPU, monthly churn on monthly plans, annual renewal rate.
- Affiliate clicks per MAU, click-to-booking rate, revenue per MAU, days to payout.
- Share of Plus payers buying credit packs (over 15% is a Pro trigger).
- Concierge ask rate per trip, completed bookings, commission per booking, founder hours per booking.
- Advisor seats, seat churn, support hours per 100 seats.
- MRR, ARR, LTV to CAC (target above 3).

Cost and quality:

- Agent cost per run (Pro gate: $0.60 or less over 200 runs), cost per user, cost per trip; research cache hit rate (target above 50%).
- Share of accounts hitting their monthly ceiling; live-check count per user; provider cost per MAU.
- Gross margin, blended (the illustrative 10,000-user month in [02-pricing-tiers.md](02-pricing-tiers.md) is about 54% before affiliate income and 61% with it) and per tier.
- Fare quality: share of agent fares passing evidence checks; user reports of wrong prices.
- Support tickets per 1,000 MAU, crash rate, App Store rating (target 4.5 or above).

## Where this plan changed the initial idea

Each point below records an earlier idea, the concern, and the final decision.

1. **Name.** The working name was Trip Planner. The product is now Hermi (see [app-buildout/brand/](../../brand)).
2. **Pro runs and price.** The initial idea was 10 to 15 agent runs a month at $11.99 or $79 a year under the name "Premium". At $0.50 to $1.50 per run that costs $5 to $22 a month against $10.19 net (monthly) or $5.60 net (annual). Decision: Pro is $11.99 a month or $99 a year with 240 credits (about 6 deep runs), a $0.80 hard stop per run, a $5.50 monthly ceiling, and it launches later, when measured cost is $0.60 or less per run over 200 runs or over 15% of Plus payers buy run credits.
3. **Pro price against rivals.** Rivals charge $40 to $50 a year (Wanderlog $39.99, TripIt $49, Layla about $49), and the first draft suggested testing $49.99 to $59.99. The concern stands: $99 is about double, so Pro must clearly offer something they lack. But at $49.99 to $59.99 a year the net is only $3.54 to $4.25 a month, too little for a $5.50 ceiling. Decision: $99 is the launch price because of the ceiling. Pro's price will be tested once measured agent cost drops, and credit packs carry heavy users meanwhile.
4. **Plus price and allowance.** The earlier plan had Plus at $4.99 a month or $29.99 a year with 40 credits. Rivals sit at $39.99 to $49.99, so $29.99 left money on the table, and the extra $10 of net pays for a bigger allowance. Decision: Plus is $5.99 a month or $39.99 a year with 60 credits and a $2.25 ceiling.
5. **Family tier and Group Trip Pass.** The plan had no answer to "share my subscription" or one-off group trips. Decision: Family ($8.99 a month, $59.99 a year, up to 6 people, 150 pooled credits, invited in the app with Apple Family Sharing off) and Group Trip Pass ($19.99 once, up to 12 travelers, polls and cost splitting).
6. **Free gets one taster run, not a monthly run.** A monthly deep run for every free user would cost $0.34 to $1.34 per free MAU a year against $0.60 of affiliate income. Decision: 12 credits a month and one lifetime deep agent run, served from the shared cache when possible, under a global daily budget.
7. **Live tracking as a headline.** Google Flights tracks prices free. Decision: Plus includes 3 live-tracked routes checked daily within 120 days of departure, but the pitch is "tracked with the reason and the source", and value comes from the workspace plus evidence-backed hunts.
8. **Research per month.** Use is episodic, so a fixed monthly quota fits badly. Decision: AI is priced in credits (1 credit is up to $0.02 of provider spend). Trip Pass gives a burst of 40 credits for one trip over 90 days; Plus gives 60 a month; purchased credits last 12 months.
9. **Affiliate as main free-tier income.** Plausible but unproven. At $0.10 to $1.50 per MAU per year it pays for infrastructure, not a salary. Decision: affiliate links are the free-tier income (no banner ads), treated as a floor, not the growth plan.
10. **Apple's commission.** 15% is not an advantage on a $5.99 plan. Decision: lead with Trip Pass and annual Plus, and check whether web checkout for US users is allowed to save fees.
11. **Monthly as the lead offer.** Wrong for episodic use. Decision: Trip Pass ($9.99 once) leads, annual Plus ($39.99, 7-day trial on annual only) is second, monthly Plus ($5.99) sits lower on the paywall.
12. **Where the paywall triggers.** Not on the first trip, since the shared trip is the growth loop. Decision: Free keeps 2 active trips and lets people join others' trips free; the paywall appears on collaboration size, live routes and credits.
13. **Banner ads.** Agreed to avoid them. Also rejected: selling data, cashback ranked by commission, and lifetime plans.
14. **Launch lineup and order of work.** The first draft launched all three tiers and a rewrite before proof of demand. Decision: validate first (M0), launch with Free, Plus, Family, Trip Pass, Group Trip Pass and packs, build Pro behind a flag, and keep scheduled agents off until Pro.
15. **A consumer app alone is a side business.** The earlier base case ($35k profit in year 3) was a side income and a venture-style outcome needed the optimistic case. Decision: add streams that reach people who plan trips for others: a concierge lane through a host agency (year 1 to 2), group trips (year 1 to 2), and Hermi for Advisors (year 2). With them the base case is about $144k of revenue in year 3 and $572k in year 5, at the cost of seller-of-travel compliance, more support, and a team of 2 to 3 people above about $250k.
16. **Five-year scenarios.** The earlier plan stopped at three years and assumed only subscriptions and affiliate income. Decision: model five years by stream, keep concierge and in-app booking outside the totals as untested upside, and state plainly that a solo founder tops out around $150k to $250k a year.
