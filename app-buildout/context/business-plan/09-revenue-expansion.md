# 09: Revenue expansion

Part of the [business plan](README.md). The decisions of record in the README override anything here.

Written 2026-09-30. Related files: [01-business-plan.md](01-business-plan.md) (plan, scenarios, risks), [02-pricing-tiers.md](02-pricing-tiers.md) (tiers and credits), [08-affiliate-revenue.md](08-affiliate-revenue.md) (affiliate programs and the higher-commission lanes), [07-local-to-app-store.md](07-local-to-app-store.md) (App Review, web checkout).

Conventions. "Reported, verify" marks a fact taken from a third-party page or search summary that could not be confirmed on the vendor's own page. "Assumption" marks a plan input, not data. Every number shows its inputs. Nothing here is a forecast. Consumer revenue is net of Apple's 15% (Small Business Program). Web-sold revenue (advisors, events, print) is net of about 3% card fees. Founder pay and taxes are excluded from profit.

## 1. Summary

1. The consumer app (subscriptions plus affiliate links) is a side income: about $99k in year 3 and about $269k in year 5 in the base case. A larger business needs streams aimed at people who plan trips for other people: advisors, group and event organizers, destination boards.
2. Base case with all modeled streams: $4.8k, $34.7k, $143.7k, $316.0k and $572.5k in years 1 to 5. Conservative: $0.7k, $3.5k, $11.5k, $22.8k, $38.2k. Ambitious: $19.3k, $187.9k, $687.9k, $1.57M, $2.87M (section 6).
3. Two lanes are kept out of those totals because they depend on founder hours or an untested merchant setup: the concierge booking lane and in-app hotel booking. If they work, base year 5 rises by about $126k (section 6.4).
4. $500k a year needs about 290k MAU on consumer economics alone, or about 1,600 advisor seats, or a mix such as 120k MAU plus 600 seats plus about $107k of group, partner and white-label income. $1M needs about 580k MAU, or about 3,200 seats, or a mix such as 250k MAU plus 1,000 seats plus about $116k of other income (section 7).
5. A solo founder tops out around $150k to $250k a year (roughly 60k to 100k MAU and 100 to 200 advisor seats). Beyond that the work is support, sales and compliance, and it needs 2 to 3 people at $500k and a small funded team at $1M (section 8).

| Stream | Starts | Effort | Base year 5 | In scenario totals | Main constraint |
|---|---|---|---|---|---|
| Consumer subscriptions, passes, packs | Launch | Built in plan | $148.8k | Yes | Conversion and retention |
| Affiliate links ([08](08-affiliate-revenue.md)) | Launch | Built in plan | $120.0k | Yes | $0.60 per MAU is unmeasured |
| Hermi for Advisors | Year 2 build, seats year 3 | Medium | $141.4k | Yes | Host-agency bundling, churn |
| Group trips: events, payments | Pass at launch, events and payments year 3 | Low to medium | $56.3k | Yes | Payments need legal review |
| Partner guides (tourism boards) | Year 2 pilot, first deal year 3 | Sales heavy | $36.0k | Yes | Needs proven audience, trust |
| White-label and API | Year 3 | Medium | $36.0k | Yes | Support and onboarding |
| Printed trip books | Year 2 | Medium | $31.2k (margin) | Yes | Needs photo and journal features |
| Creator paid guides | Year 2 | Low | $2.7k | Yes | Acquisition tool, not a line |
| Concierge lane via host agency | Year 1 | Founder hours | $54.0k | No (upside) | About 300 bookings a year solo |
| In-app hotel booking (LiteAPI) | Year 2 decision, year 3 build | High | $72.0k | No (upside) | Support load, rate parity |
| Credit card referrals | About 100k MAU | Low build, legal | not modeled | No | Issuer approval, trust |

## 2. Tier ladder: why it looks like this

### 2.1 The ladder

| | Free | Plus | Family | Group Trip Pass | Pro (later) |
|---|---|---|---|---|---|
| Price | $0 | $5.99 a month, $39.99 a year | $8.99 a month, $59.99 a year | $19.99 once | $11.99 a month, $99 a year |
| Who | Anyone; joins trips free | Frequent planner | Household or friend crew, up to 6 people | Organizer of a group trip, up to 12 travelers | Deal hunters, heavy planners, advisors' own trips |
| Credits a month | 12 | 60 | 150 pooled | 80 once (90 days) | 240 |
| Deep agent runs | 1 lifetime taster | About 1 a month | About 3 a month pooled | 2 | About 6 a month |
| Live routes | 1 cached alert | 3 | 5 | 3 | 6 |
| Provider-spend ceiling a month | $0.25 | $2.25 | $3.40 pooled | $3.60 per pass | $5.50 |

Trip Pass ($9.99 once, 90 days, 40 credits, 2 live routes) and credit packs ($2.99 for 50, $6.99 for 150, $14.99 for 400) sit beside the ladder. Trip Pass stays the lead offer when a dated trip is within 120 days.

### 2.2 Reasons for each step

- **Plus at $5.99 and $39.99, 60 credits.** Rival annual plans cluster at $39.99 to $49.99 (Wanderlog $39.99, TripIt $49, Layla about $49 to $50; reported, verify). The earlier $29.99 left $10 to $20 a year per payer unclaimed. The extra $10 of net pays for 60 credits instead of 40 and a $2.25 ceiling instead of $1.75. Annual is pre-selected with the real monthly figure ($3.33); paying monthly for a year costs 12 x $5.99 = $71.88, so annual is 44% less, a true figure. Monthly is listed, not hidden. No countdown timers. Test $34.99 against $39.99 before locking.
- **Free with a one-time taster run.** A free monthly deep run is unaffordable (table below). One lifetime taster shows the product's best feature and costs about $0.11 to $0.17 per new free user.
- **Family.** One payer, up to 6 people, pooled credits, invited in the app (Apple Family Sharing stays off). It answers "share my subscription" at $59.99 against six separate Plus plans.
- **Group Trip Pass at $19.99.** Group trips are the viral loop. The organizer pays, everyone else joins free, and one payment covers a 90-day trip. It has no money movement, so it carries little legal risk, and it costs half of a year of Splitwise Pro ($39.99 a year; reported, verify), which it partly replaces.
- **Pro later.** It exists for heavy agent users and launches only when measured agent cost is $0.60 or less per run over 200 runs, or when more than 15% of Plus payers buy agent-run credits. At $99 a year its 240 credits cost $8.25 a month. The same 240 credits bought on the $6.99 pack (4.66 cents each) cost about $11.19, so Pro annual is about 26% below packs. That is arithmetic, not a fake strike-through price.

Why not one deep run a month for every free user (plan inputs: typical run $0.56, cache-served run about $0.05, Free ceiling $0.25):

| Option | Cost per free MAU per year | Verdict |
|---|---|---|
| 8 credits, no run (old plan) | $0.15 | Baseline |
| 1 run a month, 20% redeem each month | 0.20 x 12 x $0.56 = $1.34 | Reject: more than double base affiliate income per MAU ($0.60) |
| 1 run a month, 5% redeem each month | 0.05 x 12 x $0.56 = $0.34 | Reject: still 2.2 times baseline and unbounded if sharing lifts redemption |
| One lifetime taster, 30% of new free users redeem, 35% served from cache | per run 0.35 x $0.05 + 0.65 x $0.56 = $0.38; times 0.30 = $0.11 per new free user ($0.17 if nothing is cached) | Adopt |

The taster pays back if it lifts paid conversion by about 0.4 to 0.6 points: one point is worth 0.01 x $28.34 = $0.28 per MAU. That is an assumption to A/B test at launch. Guardrails: an Apple ID and a dated trip are required, the shared cache is tried first, and a global daily taster budget (for example $25) queues the rest.

### 2.3 Margins by product

Net is after Apple's 15%. Typical cost is an assumption. Worst case is the README ceiling plus infrastructure ($0.14 a month for one person, $0.20 for Family, $0.10 to $0.15 per pass). Margin = (net per month - cost) / net per month.

| Product | Gross | Net | Typical cost | Worst-case cost | Margin typical | Margin worst |
|---|---|---|---|---|---|---|
| Plus monthly | $5.99 | $5.09 | $1.00 | $2.39 | 80% | 53% |
| Plus annual | $39.99 | $33.99 ($2.83 a month) | $1.00 | $2.39 | 65% | 16% |
| Family monthly | $8.99 | $7.64 | $1.60 | $3.60 | 79% | 53% |
| Family annual | $59.99 | $50.99 ($4.25 a month) | $1.60 | $3.60 | 62% | 15% |
| Pro monthly | $11.99 | $10.19 | $3.53 | $5.58 | 65% | 45% |
| Pro annual | $99 | $84.15 ($7.01 a month) | $3.53 | $5.58 | 50% | 20% |
| Trip Pass | $9.99 | $8.49 | $0.84 | $1.90 | 90% | 78% |
| Group Trip Pass | $19.99 | $16.99 | $1.30 | $3.75 | 92% | 78% |

Reading: monthly plans and passes are healthy even at the ceiling. Annual Plus, Family and Pro are thin only if the ceiling is hit every month, which the usage pattern (2 to 4 active months a year) makes unlikely. Family annual is the weakest cell: alert at $3.00 of pooled spend and reprice if over 25% of families sit near the ceiling. Blended net per paying user is $28.34 a year (mix: 34% Plus annual, 8% Plus monthly, 34% Trip Pass, 8% Group Trip Pass, 8% Family, 8% Pro; gross $32.45, net $27.59, plus $0.75 of credit packs).

## 3. Streams beyond subscriptions and links

### 3.1 Concierge lane through a host agency

**How it works.** A "Have a human book this" button on shortlisted stays, cruises and complex trips. The user fills a short brief; the founder, registered as an independent advisor under a host agency (for example Fora), books the trip in the host's supplier portal and earns the agency commission. The user gets perks the public site does not show: daily breakfast, a property credit (for example $100), possible upgrade and late checkout at the same or better rate (reported, verify per property). The app never books by itself. Host-agency contracts are with a named advisor, and supplier portals expect a human, so automated booking under host credentials would probably breach terms (inference).

**Pricing to the user.** Nothing extra. The supplier pays the commission. Hermi discloses it: "Hermi is paid by the hotel. Perks are listed before you choose."

**What it earns (reported, verify all splits).**

| Item | Figure |
|---|---|
| Hotel commission to the agency | About 8 to 15%, average 12% reported for Fora Reserve |
| Cruise commission | 10 to 16%, river cruises 15 to 20% |
| Fora split | 70/30 to start, 80/20 at $300,000 of annual sales, 90/10 at $2M; $299 a year or $99 a quarter |
| Cheaper hosts | Outside Agents 80 to 90%, about $199 to start and $26 to $46 a month; KHM 80%, 90% after $5,000 paid commission |
| $600 Virtuoso-type stay at 10%, 70% split | $60 to the agency, $42 to Hermi |
| $3,000 cruise at 10 to 16%, 70% split | $210 to $336 to Hermi |
| Average used in the model | $90 per completed booking (85% hotels at $55, 10% cruises at $290, 5% packages at $225) |

**Costs.** Host fee about $400 a year, E&O insurance $400 to $1,200 a year for $1M per claim (reported, verify; host cover may apply), seller-of-travel registrations about $640 a year for CA, FL, WA and HI combined (reported: California $100, Florida $50 for independent agents, Washington $50 plus $222, Hawaii $146 to $215 plus a trust account). About $1.4k to $2.2k a year fixed, plus founder time of 30 to 60 minutes per booking. At 45 minutes, $90 per booking is about $120 an hour of founder time. Commissions arrive 30 to 90 days after travel, and cancelled stays pay nothing.

**Effort.** Low build (a request form and a status screen), high founder time. One person serves about 300 bookings a year (150 to 300 hours). Beyond that, contracted advisors are needed, and Hermi keeps about half of the booking's net ($45).

**Regulatory.** Seller-of-travel registration in some states, host accreditation (IATA, ARC, CLIA or TRUE) through the host, E&O cover. Counsel confirms whether forwarding a request to a human advisor needs registration in each state (inference: referral only is usually outside, selling is not). Email Fora, Outside Agents and KHM before building to ask whether app-routed leads are allowed.

**User-experience impact.** None if the rules hold: the button is opt-in, never reorders results, shows perks next to the price, is not paywalled, and the normal "Book" link stays beside it.

**Starts.** Year 1 (an advisor sign-up in months 0 to 6, the button in phase 3 or 4).

**Revenue estimate (base).** Bookings = MAU x 0.6 trips x opt-in rate x 50% completed. Opt-in is 2% in years 1 and 2 and 3% after (assumption, range 2 to 4%). Revenue = bookings x $90, with solo capacity at 300 bookings and extra bookings at $45 through contracted advisors.

| Base | Y1 | Y2 | Y3 | Y4 | Y5 |
|---|---|---|---|---|---|
| Trips (MAU x 0.6) | 1,800 | 12,000 | 36,000 | 60,000 | 90,000 |
| Requests | 36 | 240 | 1,080 | 1,800 | 2,700 |
| Completed (50%) | 18 | 120 | 540 | 900 | 1,350 |
| Served | 18 | 120 | 300 | 600 | 900 |
| Revenue | $1.6k | $10.8k | $27.0k | $40.5k | $54.0k |

Year 3 example: 300 x $90 = $27,000. Year 5: 300 x $90 + 600 x $45 = $54,000. Per trip that is $0.75 in year 3 and $0.60 in year 5, below the $2 to $6 per trip the lane could earn without the capacity cap. At $300,000 of booked sales (about 300 bookings at a $935 average booked value) the Fora split rises to 80/20, worth roughly $13 more per booking; not counted.

### 3.2 Group trips: pass, polls, cost splitting, room blocks

**How it works.** Four layers, added in order.

1. Group Trip Pass ($19.99 once): up to 12 travelers, 80 credits, polls (dates, stay, activities), a shared budget and a "who owes what" ledger. No money moves. Year 1.
2. Room-block request: a form that sends the hotel's group sales team the dates and headcount and returns the hotel's own reservation link. Hermi signs no contract and takes on no attrition risk. Months 6 to 12.
3. Events workspace: $79 per event, up to 40 travelers, for offsites, destination weddings and school trips (school trips later because of child-data rules). Sold on the web. Year 3 in the model.
4. Payment collection: Stripe Connect with the organizer as the connected account, so Hermi never holds funds. Fee 1.5% of amounts collected on top of Stripe's card cost, passed through in plain view; below SquadTrip's reported all-in 6% (reported, verify). Needs legal review (money transmission, refunds, disputes, tax, sanctions). Year 3 at the earliest.

**Costs.** The pass has 78% to 92% margin (section 2.3). Events cost about $1.30 of AI and infrastructure. Stripe card cost is about 2.9% plus $0.30 and is shown to the organizer. Support for disputes and refunds is the real cost of layer 4.

**Regulatory.** Layers 1 and 2: minimal. Layer 3 and 4: real-world payments are outside Apple In-App Purchase (guideline 3.1.3(e)), but the $79 workspace is a digital feature. Selling it in the iOS app would need In-App Purchase at 15% (net $67.15, 12% below the $76.60 modeled), so it is sold on the web and opened in the app. Verify the current link-out rules in [07](07-local-to-app-store.md).

**User-experience impact.** Positive. Free blocks save organizers work, and cost splitting is the feature group trips most lack. Payments stay optional and the fee is shown before anything is charged.

**Revenue estimate.**

- Group Trip Pass: inside the consumer line (8% of payers, $19.99 x 1.2 purchases a year).
- Events: $79 x 0.97 = $76.60 net each. Base 50, 200 and 500 events in years 3 to 5: $3.8k, $15.3k, $38.3k.
- Payments: 0.6 trips per MAU x 25% group trips x 2% collecting in the app x $4,000 x 1.5% = $0.09 per MAU at the stated inputs. The model uses $0.08 in year 4 and $0.12 in year 5 (base), $0.15 to $0.25 (ambitious). Base year 5: 150,000 x $0.12 = $18.0k.
- Room-block commission: not modeled. A 30-room, 2-night block at $200 a night is $12,000 of room revenue and up to about $1,200 at a 10% commission (reported, verify), but it is unknown whether an app can be the payee (often only registered planners or agencies). If 10% of 500 events used a block at half that commission: 50 x $600 = $30k, upside.

### 3.3 In-app hotel booking through LiteAPI

**How it works.** Hotel search and booking inside Hermi using LiteAPI (Nuitee), a self-serve REST API with 2M+ hotels (reported, verify). Hermi sets a margin per search, Nuitee acts as merchant of record through its payment SDK, and payouts are weekly for confirmed bookings. Merchant-of-record by Nuitee keeps card data out of Hermi's scope.

**Pricing.** The user pays the displayed rate, which Hermi marks up by 5 to 15% above net. Bedbank rates are often priced to match public rates, so the usable margin is probably the low end (inference).

**Costs.** $600 stay at 8%: $48 gross. After card fees, cancellations, chargebacks and support the net is about $15 to $60; the model uses $30. Hermi also loses the affiliate commission it would have earned on that stay (about $10 assumed), so incremental revenue is $20 per booking. Build effort is high: search, prebook, cancel, vouchers, currency, tax and resort-fee display, "I arrived and there is no booking" support.

**Regulatory.** Consumer law, refunds and probably seller-of-travel registration as a seller rather than a referrer (inference, counsel to confirm). Hotelbeds, WebBeds and Expedia Rapid are not solo options and are skipped.

**User-experience impact.** Mixed. A native checkout converts better than a redirect, but Hermi then owns every hotel problem, and the "we send you to the real site" trust is lost. It starts only after click data shows strong booking intent and a support process exists.

**Starts.** Decision in year 2, build and launch in year 3 (base), year 2 (ambitious).

**Revenue estimate.** Bookings = trips x attach (3% to 5% of trips, assumption) x $20 incremental.

| | Y3 | Y4 | Y5 |
|---|---|---|---|
| Base trips | 36,000 (half year) | 60,000 | 90,000 |
| Attach | 3% | 3% | 4% |
| Bookings | 540 | 1,800 | 3,600 |
| Revenue at $20 | $10.8k | $36.0k | $72.0k |

### 3.4 Hermi for Advisors

**How it works.** A web product for independent travel advisors: a client trip workspace, branded presentation mode (already built), client proposals with price options, a shared client page, the fare and research tools with source links, and a commission tracker. It is sold on the web through Stripe, not the App Store, so Apple's cut does not apply (verify current link-out rules in [07](07-local-to-app-store.md)). Hermi holds no host credentials and does not book for advisors.

**Pricing.** $29 a seat a month, or $24 a seat a month billed annually. Incumbents (reported, verify): Tern $49 monthly or $35 annual, Travefy from $39 a month, TravelJoy from $19 a month, Safari Portal $199 to $299 a month per team. Net per seat: blended $27 a month x 12 x 0.97 = $314 a year.

**Costs.** Each seat includes Plus-level credits (60 a month, assumption). Net per seat month is $26.19; ceiling plus infrastructure is $2.39, so margin is 91% worst case and 96% at typical use ($1.00). The real cost is support: add about 10 hours a week per 100 seats (assumption), on top of the consumer load of 5 to 10 hours a week from 5,000 MAU.

**Effort.** Medium: client portal, proposals, teams, billing and a commission tracker on the existing workspace. About 3 to 4 months for one person (assumption). Interview 15 advisors before building.

**Regulatory.** Hermi is a tool vendor, not a seller of travel. Client personal data (names, dates, sometimes passport details) means data-processing terms and no storage of passport numbers. Sales tax on SaaS varies by state. Advisors disclose their own commissions to clients; the tool records them but does not advise.

**User-experience impact.** None for consumers. Advisor features sit in a separate web surface, and consumer screens never show advisor branding unless a client opens an advisor's trip.

**Starts.** Build and pilot in year 2 (first paying seats late in year 2, under 10 average seats, modeled as zero in base). Year 3 is the first modeled year.

**Revenue estimate.** Serviceable base is about 60k core independent advisors (the owner's figure). A trade report says 310,000 in 2025 and Fora reports 15,000 advisors, 97% new to travel (Open Jaw, TravelPulse; reported, verify). The definitions differ, so the model uses 60k. Host agencies bundle tools and cap what advisors pay.

| Average seats | Y1 | Y2 | Y3 | Y4 | Y5 |
|---|---|---|---|---|---|
| Conservative | 0 | 0 | 10 | 30 | 60 |
| Base | 0 | 0 | 60 | 200 | 450 |
| Ambitious | 0 | 100 | 400 | 1,000 | 2,000 |

Revenue = seats x $314.28. Base year 5: 450 x $314.28 = $141.4k (0.75% of 60k advisors). Ambitious year 5: 2,000 x $314.28 = $628.6k (3.3%). Differentiator to test: fares with source links that advisors can show clients. Go-to-market: host-agency partnerships, advisor communities, content; no paid ads assumed.

### 3.5 Partner guides from tourism boards

**How it works.** A clearly labeled "Partner guide" shelf: an official destination guide funded by a tourism board or hotel brand, with itinerary templates users can copy. Every card says "Sponsored by X". Sponsors never appear inside fare, lodging or ranked results, cannot buy rank, cannot see user-level data, and users can hide the shelf.

**Pricing.** $5,000 to $8,000 per destination per quarter; the model uses $6,000 (base) and $8,000 (ambitious). Benchmarks (reported, verify): tourism-board creator campaigns run from EUR 1,000 to EUR 50,000; micro creator posts $250 to $2,500. Proof to sell with: measured copies and saved trips.

**Costs.** Mostly sales time: about 1 paid deal per 15 to 25 pitches (assumption), so 6 deals a year needs 90 to 150 pitches. Design and reporting add a few hours per deal.

**Regulatory.** Disclosure as advertising ("Ad" on UK and EU storefronts, the FTC rules in [08](08-affiliate-revenue.md) section 7.4), contracts that bar ranking influence, and no sharing of personal data with sponsors.

**User-experience impact.** Contained if the shelf is separate, labeled and hideable. It is the easiest place to lose the trust the product sells, so a rule is written into every contract: no paid placement in search or ranking.

**Starts.** Pilot in year 2 (one free or discounted destination to prove copies), first paid deal in year 3, which needs an audience of about 50k MAU.

**Revenue estimate.** Deals per year, base 1, 3, 6 in years 3 to 5: $6k, $18k, $36k. Ambitious 1, 4, 10, 20 in years 2 to 5 at $8,000: $8k, $32k, $80k, $160k.

### 3.6 Printed trip books and posters

**How it works.** A print-on-demand trip book (30-page hardcover, 8x8, built from the itinerary, notes and photos) or a poster or printed itinerary, ordered on the web or with Apple Pay. No inventory; a print provider ships. Physical goods are outside In-App Purchase (guideline 3.1.3(e); confirm current text).

**Pricing and unit economics (print costs reported, verify; get quotes from Prodigi, Peecho, Lulu and Printful).**

| Product | Price | Cost | Contribution |
|---|---|---|---|
| Trip book, 30 pages | $44.99 plus shipping at cost | Print $16 + card $1.60 + returns and support $1.00 | $26.39 |
| Poster or printed itinerary | $24.99 | Print $7 + card $1.03 + support $0.50 | $16.47 |

Reference point: Polarsteps reportedly earns most of its revenue from printed books, at EUR 36 to 150 each, with 20M users (reported, verify).

**Effort and regulatory.** Medium. It needs a photo and journal feature the app does not have, plus a print API integration, sales tax or VAT on physical goods (Stripe Tax), and return handling. Start with a single book size and ship to the US only.

**User-experience impact.** None. It is an optional export from presentation mode, offered once after a trip ends.

**Starts.** Year 2.

**Revenue estimate.** Units = MAU x attach rate; revenue counted as contribution at $26 a unit, so gross sales are about 1.7 times higher ($44.99 / $26.39). Base attach 0.4%, 0.6%, 0.8%, 0.8% in years 2 to 5. Paid creator guides add 0.008 guides per MAU at $2.29 app share.

| Base | Y2 | Y3 | Y4 | Y5 |
|---|---|---|---|---|
| MAU | 20k | 60k | 100k | 150k |
| Books and posters at $26 | $2.1k | $9.4k | $20.8k | $31.2k |
| Creator guides | $0.4k | $1.1k | $1.8k | $2.7k |
| Total | $2.4k | $10.5k | $22.6k | $33.9k |

Example, year 5: 150,000 x 0.8% x $26 = $31,200; 150,000 x 0.008 x $2.29 = $2,748. Creator guides (10 to 20 invited creators, Apple's 15%, then 70/30 creator to app) are an acquisition and affiliate-yield tool, not a revenue line.

### 3.7 White-label and API

**How it works.** The planner, presentation mode and group workspace licensed to agencies and tour operators, with their branding and domain. It is the same code as Hermi for Advisors packaged for accounts rather than seats.

**Pricing.** $500 a month per account ($6,000 a year); ambitious case at the same price.

**Costs and effort.** Medium: multi-brand theming, a custom domain, a data-processing agreement, onboarding. Support per account is the real cost. Do not start before the advisor product is stable.

**Regulatory.** Data-processing agreements, child-data rules for school operators (COPPA, FERPA), service-level promises kept minimal.

**User-experience impact.** None for consumer users.

**Starts.** Year 3.

**Revenue estimate.** Base accounts 1, 3, 6 in years 3 to 5: $6k, $18k, $36k. Ambitious 1, 4, 10, 20 in years 2 to 5: $6k, $24k, $60k, $120k. A paid API is the same packaging and adds nothing to the totals.

### 3.8 Credit cards (later)

Card referral pays $50 to $200 per approval (reported: CardRatings $50 to $200, Bankrate $50 to $175). Issuers screen publishers, review all copy and require approved terms; AI-written copy and "best card for Japan" drift toward advice. It pays nothing in the totals. Revisit at about 100k MAU with counsel and a specialist network. Potential at 100k MAU: 0.5% approved x $100 = $50k at the low end, 1.0% x $150 = $150k at the high end, but only if it can be shown without pushing users. It would never appear inside the planner flow, only in a clearly labeled money section of "Before you go". This matches the decision in [08](08-affiliate-revenue.md) section 4.3.

### 3.9 Deferred or poor fits in years 1 to 3

| Idea | Why not now |
|---|---|
| Flights as merchant (Duffel) | Markup 1 to 5% of fare; net $5 to $25 per ticket before support; refunds, schedule changes and fraud sit with the seller |
| Expedia Rapid, Hotelbeds, WebBeds direct | Partner-only, certification, six-figure cost (reported), not solo work |
| Viator merchant API | Could double or triple the take per tour over the 8% affiliate rate (inference), but needs certification and cancellation support; revisit after affiliate volume exists |
| Insurance licence | Referral pays $8 to $25; a licence might lift it to $20 to $60 but adds exams and conduct limits |

## 4. What is rejected

| Idea | Decision | Reason |
|---|---|---|
| Selling user data or insights | No | A 60k MAU panel is not representative, buyers use panels of tens of millions, and GDPR and CCPA purpose limits plus the privacy label make it a trust cost. Not reconsidered below 500k MAU, and then opt-in, aggregated only. |
| Banner ads and ad networks | No | Under $1 per MAU per year, compete with affiliate links, need ATT and consent flows, and sit next to price lists. See [01](01-business-plan.md). |
| Cashback or rankings driven by commission | No | Lists are never ranked by commission. Sharing commission as cash is refused for the reasons in [08](08-affiliate-revenue.md) section 13.6. |
| Lifetime plans | No | Buyers are the heaviest users and cost never stops. Annual Plus at 30% renewal is worth about $48.60 (33.99 / 0.70); a $99.99 lifetime nets $85.00, and three years at the $2.39 ceiling (3 x 12 x $2.39 = $86) already exceeds it. It also removes the renewal income the model counts on. |
| Hard paywall | No | Would end the free sharing loop the model depends on. |

## 5. What each stream needs from the product

| Stream | New product work | Already built |
|---|---|---|
| Concierge | Request form, status screen | Shortlist, presentation mode |
| Group trips | Polls, ledger, room-block form, Stripe Connect (later) | Collaboration, invite links |
| LiteAPI | Booking, prebook, cancel, voucher, support tools | Lodging shortlist |
| Advisors | Client portal, proposals, teams, billing, commission tracker | Presentation mode, PDF, workspace |
| Partner guides | Sponsored shelf, reporting | Shareable trip pages (phase 4) |
| Print | Photo and journal, print API | Presentation mode |
| White-label | Theming, custom domain | Advisor product |

## 6. Five-year scenarios

All figures are US dollars in thousands unless stated; "k" is $1,000. Year 1 is the first year after public launch. Totals are computed before rounding, so a column can differ from the sum of its rounded lines by $0.1k.

### 6.1 Assumptions

| Input | Conservative | Base | Ambitious |
|---|---|---|---|
| Average MAU, years 1 to 5 | 1k, 5k, 12k, 18k, 25k | 3k, 20k, 60k, 100k, 150k | 8k, 50k, 150k, 300k, 500k |
| Paid conversion of MAU | 2.0% | 3.5% | 5.0% |
| Net per paying user per year | $28.34 | $28.34 | $28.34 |
| Affiliate per MAU, years 1 to 5 | $0.10, 0.10, 0.10, 0.12, 0.15 | $0.60, 0.62, 0.65, 0.72, 0.80 | $1.00, 1.20, 1.40, 1.50, 1.60 |
| Advisor seats, average | 0, 0, 10, 30, 60 | 0, 0, 60, 200, 450 | 0, 100, 400, 1,000, 2,000 |
| Events ($76.60 each) | 0 | 0, 0, 50, 200, 500 | 0, 20, 200, 800, 2,000 |
| Group payments, $ per MAU | 0 | 0, 0, 0, 0.08, 0.12 | 0, 0, 0.15, 0.25, 0.25 |
| Partner deals a year | 0 | 0, 0, 1, 3, 6 at $6k | 0, 1, 4, 10, 20 at $8k |
| White-label accounts ($6k) | 0 | 0, 0, 1, 3, 6 | 0, 1, 4, 10, 20 |
| Print attach (at $26), from year 2 | 0.1%, 0.1%, 0.2%, 0.2% | 0.4%, 0.6%, 0.8%, 0.8% | 0.6%, 1.0%, 1.2%, 1.2% |
| Creator guides per MAU ($2.29), from year 2 | 0.002 | 0.008 | 0.02 |
| Variable cost | $0.30 per free MAU a year (taster $0.11 to $0.17 plus $0.15) and $9 per paying user a year | same | same |

Fixed costs (infrastructure, tools, legal), marketing and paid team (founder pay excluded):

| | Y1 | Y2 | Y3 | Y4 | Y5 |
|---|---|---|---|---|---|
| Conservative fixed / marketing / team | 4k / 1k / 0 | 6k / 2k / 0 | 6k / 3k / 0 | 8k / 4k / 0 | 10k / 5k / 0 |
| Base fixed / marketing / team | 6k / 5k / 0 | 10k / 10k / 0 | 18k / 20k / 40k | 30k / 40k / 120k | 45k / 60k / 250k |
| Ambitious fixed / marketing / team | 10k / 10k / 0 | 25k / 80k / 120k | 50k / 150k / 350k | 90k / 250k / 700k | 150k / 350k / 1,200k |

The team line is contractors first, then hires (support and advisor success in year 3, an engineer and advisor sales in years 4 and 5). Paying users are about 2,100 (base year 3) and 5,250 (base year 5): 60,000 x 3.5% and 150,000 x 3.5%.

### 6.2 Results by stream

Conservative (side project):

| | Y1 | Y2 | Y3 | Y4 | Y5 |
|---|---|---|---|---|---|
| Paying users | 20 | 100 | 240 | 360 | 500 |
| Consumer subscriptions, passes, packs | 0.6k | 2.8k | 6.8k | 10.2k | 14.2k |
| Affiliate | 0.1k | 0.5k | 1.2k | 2.2k | 3.8k |
| Advisor seats | 0 | 0 | 3.1k | 9.4k | 18.9k |
| Events, groups, DMO, white-label | 0 | 0 | 0 | 0 | 0 |
| Print and guides | 0 | 0.2k | 0.4k | 1.0k | 1.4k |
| **Total revenue** | **0.7k** | **3.5k** | **11.5k** | **22.8k** | **38.2k** |
| Profit | -4.8k | -6.9k | -3.2k | +2.3k | +11.3k |

Base:

| | Y1 | Y2 | Y3 | Y4 | Y5 |
|---|---|---|---|---|---|
| Paying users | 105 | 700 | 2,100 | 3,500 | 5,250 |
| Consumer subscriptions, passes, packs | 3.0k | 19.8k | 59.5k | 99.2k | 148.8k |
| Affiliate | 1.8k | 12.4k | 39.0k | 72.0k | 120.0k |
| Advisor seats | 0 | 0 | 18.9k | 62.9k | 141.4k |
| Events, groups and payments | 0 | 0 | 3.8k | 23.3k | 56.3k |
| Partner guides and white-label | 0 | 0 | 12.0k | 36.0k | 72.0k |
| Print and creator guides | 0 | 2.4k | 10.5k | 22.6k | 33.9k |
| **Total revenue** | **4.8k** | **34.7k** | **143.7k** | **316.0k** | **572.5k** |
| Variable cost | 1.8k | 12.1k | 36.3k | 60.5k | 90.7k |
| Profit | -8.0k | +2.6k | +29.4k | +65.5k | +126.8k |

Ambitious (needs a proven viral loop and funding or reinvested profit):

| | Y1 | Y2 | Y3 | Y4 | Y5 |
|---|---|---|---|---|---|
| Paying users | 400 | 2,500 | 7,500 | 15,000 | 25,000 |
| Consumer subscriptions, passes, packs | 11.3k | 70.8k | 212.5k | 425.0k | 708.4k |
| Affiliate | 8.0k | 60.0k | 210.0k | 450.0k | 800.0k |
| Advisor seats | 0 | 31.4k | 125.7k | 314.3k | 628.6k |
| Events, groups and payments | 0 | 1.5k | 37.8k | 136.3k | 278.3k |
| Partner guides and white-label | 0 | 14.0k | 56.0k | 140.0k | 280.0k |
| Print and creator guides | 0 | 10.1k | 45.9k | 107.4k | 178.9k |
| **Total revenue** | **19.3k** | **187.9k** | **687.9k** | **1,573.0k** | **2,874.1k** |
| Variable cost | 5.9k | 36.8k | 110.3k | 220.5k | 367.5k |
| Profit | -6.6k | -73.9k | +27.7k | +312.5k | +806.6k |

Scenario totals (revenue, years 1 to 5): conservative about $0.7k, $3.5k, $11.5k, $22.8k, $38.2k ($76.7k cumulative); base about $4.8k, $34.7k, $143.7k, $316.0k, $572.5k ($1.07M cumulative, profit $216k cumulative); ambitious about $19.3k, $187.9k, $687.9k, $1.57M, $2.87M ($5.34M cumulative).

### 6.3 Worked lines (base, year 5)

- Consumer: 150,000 MAU x 3.5% = 5,250 payers x $28.34 = $148.8k.
- Affiliate: 150,000 x $0.80 = $120.0k.
- Advisors: 450 x $314.28 = $141.4k.
- Events and payments: 500 x $76.60 + 150,000 x $0.12 = $38.3k + $18.0k = $56.3k.
- Partner guides and white-label: 6 x $6k + 6 x $6k = $72.0k.
- Print and guides: $31.2k + $2.7k = $33.9k.
- Variable cost: 150,000 x 0.965 x $0.30 + 5,250 x $9 = $43.4k + $47.3k = $90.7k.
- Profit: $572.5k - $90.7k - $45k - $60k - $250k = $126.8k.

### 6.4 Upside not in the totals

Concierge (section 3.1) and LiteAPI (section 3.3) are left out of the README scenario totals because neither is tested. Concierge conservative uses 0.3 trips per MAU, 1% opt-in, 50% completed, $70 a booking; base and ambitious use the rules above (ambitious 0.8 trips per MAU, 3% opt-in, 300 solo bookings, the rest at $45). LiteAPI is zero in conservative.

| Upside | Y1 | Y2 | Y3 | Y4 | Y5 |
|---|---|---|---|---|---|
| Conservative concierge | 0.1k | 0.5k | 1.3k | 1.9k | 2.6k |
| Base concierge | 1.6k | 10.8k | 27.0k | 40.5k | 54.0k |
| Base LiteAPI | 0 | 0 | 10.8k | 36.0k | 72.0k |
| **Base total upside** | **1.6k** | **10.8k** | **37.8k** | **76.5k** | **126.0k** |
| Ambitious concierge | 8.6k | 40.5k | 94.5k | 175.5k | 283.5k |
| Ambitious LiteAPI | 0 | 12.0k | 96.0k | 192.0k | 400.0k |
| **Ambitious total upside** | **8.6k** | **52.5k** | **190.5k** | **367.5k** | **683.5k** |
| Base with upside | 6.4k | 45.5k | 181.5k | 392.5k | 698.5k |

Base year 5 with upside is about $698.5k, versus the $572.5k of record. Ambitious with upside is about $3.56M in year 5 (2,874.1 + 683.5).

### 6.5 How uncertain each line is

| Line | Base year 5 | Confidence | What would break it |
|---|---|---|---|
| Consumer subscriptions | $148.8k | Medium | Conversion at 2.0% (the RevenueCat median) instead of 3.5% cuts it to $85k |
| Affiliate | $120.0k | Low | $0.80 per MAU is unmeasured; at $0.30 it is $45k |
| Advisor seats | $141.4k | Low to medium | Host agencies bundling free tools; advisor churn among part-timers |
| Partner guides, white-label | $72.0k | Low | Sales cycles; needs 90 to 150 pitches a year |
| Events and payments | $56.3k | Low | Legal review of payments; event volume is distribution-bound |
| Print | $33.9k | Medium | Photo and journal feature must exist; real print quotes differ |

Ambitious depends on 500k MAU and $1.60 affiliate per MAU, both more than double base and not yet measured. Treat it as a ceiling on what the streams could do, not a target. Apple's 30% tier above $1M of proceeds is not reached in any scenario (ambitious consumer gross in year 5 is about $0.83M including packs).

## 7. Paths to $500k and $1M

Revenue per MAU at different economics = conversion x $28.34 + affiliate + other per-MAU income (print, guides, group payments; $0.02, $0.12, $0.35).

| Economics | Revenue per MAU a year | MAU for $500k | MAU for $1M |
|---|---|---|---|
| Conservative (2%, $0.10 affiliate) | 0.02 x 28.34 + 0.10 + 0.02 = $0.69 | 728k | 1.46M |
| Base (3.5%, $0.60) | 0.035 x 28.34 + 0.60 + 0.12 = $1.71 | 292k | 584k |
| Ambitious (5%, $1.50) | 0.05 x 28.34 + 1.50 + 0.35 = $3.27 | 153k | 306k |

Advisors alone: $314 a seat. $500k needs 1,591 seats (2.7% of 60k advisors). $1M needs 3,182 seats (5.3%).

| Target | Consumer | Advisor seats | Other | Total | Team |
|---|---|---|---|---|---|
| $500k, consumer heavy | 292k MAU x $1.71 = $500k | 0 | 0 | $500k | 4 to 5: founder, 2 engineers, support, growth |
| $500k, mixed | 120k MAU x $1.71 = $205k | 600 x $314 = $188k | Events, partner and white-label about $107k (6 deals $36k, 6 accounts $36k, 500 events $38k, less rounding) | about $500k | 3 to 4: founder, engineer, support and advisor success, part-time sales |
| $500k, advisor heavy | 50k MAU x $1.71 = $86k | 1,000 x $314 = $314k | About $100k | about $500k | 3 to 4: founder, advisor success, sales, contractor engineer |
| $1M, mixed | 250k MAU at 4%, $1.00, $0.15 = $2.28 a MAU = $570k | 1,000 x $314 = $314k | About $116k (10 deals $60k, 6 accounts $36k, events $20k) | about $1.0M | 6 to 8, probably funded |
| $1M, advisor heavy | 100k MAU x $1.71 = $171k | 2,200 x $314 = $691k | About $140k | about $1.0M | 6 to 10: advisor sales team, support desk, two engineers |

Reading the paths. Consumer-heavy paths need about 290k MAU without paid ads (shareable trip pages, creators, ASO), which no part of the product proves yet. Advisor-heavy paths need 1,000 seats (1.7% of 60k advisors, or 7% of Fora's reported 15,000) and a sales and support desk. The mixed $500k path is the most realistic because no single input has to be extreme. The $1M paths add roughly 3 to 5 more people and a funded runway, because each $100k of advisor revenue brings about 300 seats to support.

## 8. What a solo founder can do

A solo founder tops out around $150k to $250k a year. The arithmetic: 60k MAU x $1.71 = $103k, plus 100 seats x $314 = $31k, plus about $15k of partner, print and group income is about $150k. At 100k MAU and 200 seats it is $171k + $63k + about $0 to $15k, about $235k to $250k. That is 60k to 100k MAU and 100 to 200 seats, which already means support, advisor onboarding and partner sales on top of the build.

| Revenue level | Realistic owner | Why |
|---|---|---|
| Up to about $50k | Solo, part time | Base-case shape in year 2: 20k MAU, affiliate plus Trip Pass |
| $50k to $150k | Solo, full time, plus a support contractor | About 60k MAU or 100 seats. Support is 5 to 10 hours a week from 5,000 MAU plus 10 hours a week per 100 seats (assumption) |
| $150k to $250k | Solo at the limit | Concierge caps at about 300 bookings a year; partner sales and payments compliance compete with building |
| $250k to $500k | 2 to 3 people: engineer, support and advisor success, part-time sales | Reinvest profit; no funding strictly needed if margins hold (base profit in years 4 and 5 is $65k to $127k after team cost) |
| $500k to $1M | 4 to 6 people, possibly funded | Payments legal, partner sales, print operations, moderation |
| Above $1M | Funded team | Apple's 30% tier may apply above $1M of proceeds; prepaid credit and payment rules; multiple platforms |

Things that do not scale solo: advisor onboarding and support, partner sales cycles, payment disputes and refunds, creator moderation, print returns, and concierge bookings beyond about 300 a year.

## 9. Risks and what to verify

1. Advisor market: 60k core versus 310k reported; competitor prices come from search summaries; host agencies may bundle tools and cap price at zero. Interview 15 advisors before building.
2. Concierge: confirm in writing with Fora, Outside Agents and KHM that app-routed leads are allowed, and get counsel to confirm seller-of-travel rules for a request-forwarding app in each state where users live.
3. Affiliate per MAU ($0.60 to $1.60) is the biggest swing factor in every scenario ([01](01-business-plan.md) risks). Measure before growth spending.
4. Free taster cost and conversion lift are assumptions; A/B test and watch cost per activated user against the $0.28 per MAU value of one conversion point.
5. Conversion benchmarks (RevenueCat, reported: 2.0% to 2.4% download-to-paid median; AI apps earn about 41% more per payer but churn about 30% faster) come from summaries, not the full report.
6. Print prices and print-API costs are unverified; get real quotes.
7. Apple's proposed link-out fee (15%, 5% for Small Business Program members; reported August 2026, verify, not approved) would change web-checkout savings of about 10 points on US revenue. Not counted.
8. Payments and group collection need legal review before any build.
9. Sponsorship must never touch fare or lodging ranking.
10. All cost inputs depend on the open items in the README: SerpApi terms and price, Geoapify terms, and agent cost per run measured over 200 runs.

## 10. Sources

Accessed 2026-09-30, all third-party summaries (reported, verify).

- Competitors and benchmarks: RevenueCat State of Subscription Apps 2026 (https://www.revenuecat.com/state-of-subscription-apps); Wanderlog Pro pricing (https://monkeyeatingmango.com/blog/wanderlog-pricing-2026/); TripIt Pro (https://www.tripit.com/web/pro/pricing); Layla (https://layla.ai/blog/ai-travel-planners-comparison); Polarsteps Travel Book (https://support.polarsteps.com/hc/en-us/articles/24003935464466-What-is-the-price-of-a-Travel-Book).
- Advisors and host agencies: Open Jaw (https://openjaw.com/newsroom/retail/2026/09/30/from-190000-to-310000-us-travel-advisor-numbers-explode/); TravelPulse on host agencies (https://www.travelpulse.com/news/host/travel-experts-shares-why-independent-travel-advisors-should-join-a-host-agency); Fora commissions (https://www.foratravel.com/join/resources/travel-agent-commission); Tern pricing (https://tern.travel/pricing); Safari Portal (https://www.safariportal.app/pricing).
- Groups and payments: SquadTrip fees (https://help.squadtrip.com/en/articles/9794592-payments-and-fees); Groups360 (https://groups360.com/blog/event-planner-hotel-commissions-guide/); Splitwise Pro (https://getfinny.app/blog/splitwise-pricing-2026).
- Hotel booking: LiteAPI revenue management (https://docs.liteapi.travel/docs/revenue-management-and-commission) and payments (https://docs.liteapi.travel/docs/implementing-payment).
- Print and sponsorship: photo book costs (https://www.wtpbiz.com/blog/how-to-price-photobooks); Prodigi (https://www.prodigi.com/products/books-and-magazines/hardcover-photo-book/); tourism board campaign rates (https://max-haase.com/en/collaboration-influencers-guide-tourism-boards/).
- Apple link-out proposal: https://techcrunch.com/2026/08/14/apple-proposes-to-take-a-15-cut-of-purchases-made-outside-the-app-store/
- Commission and licensing sources for the concierge and group lanes are listed in [08-affiliate-revenue.md](08-affiliate-revenue.md).
