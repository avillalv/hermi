# 08: Affiliate revenue

Part of the [business plan](README.md). The decisions of record in the README override anything here.

Written 2026-09-30. This file covers how Hermi earns commissions. Related files: [09-revenue-expansion.md](09-revenue-expansion.md) (every other revenue stream and the five-year scenarios), [06-database-and-data-integrations.md](06-database-and-data-integrations.md) (schema, providers, section 6 affiliate integration), [07-local-to-app-store.md](07-local-to-app-store.md) (App Review, roadmap, feature flags), [02-pricing-tiers.md](02-pricing-tiers.md) (tiers), [01-business-plan.md](01-business-plan.md) (revenue scenarios).

Evidence caveat: the official partner sites (Airbnb, Awin, Stay22, Travelpayouts, AirHelp, Viator, GetYourGuide, Airalo, ftc.gov and others) were blocked from the research environment. Every rate, cookie window and eligibility rule below came from third-party reports and search summaries. Every rate is "reported, verify" until it is read on the network's own terms page after sign-up. Attach rates and order values are estimates, not data. Month 3 click data replaces them.

## 1. Summary

Affiliate commissions are the income of Hermi's Free tier (no banner ads, see the README). Free users cost up to $0.25 a month in provider spend, so the commission has to cover that cost and, over time, pay for infrastructure. It is a floor, not the growth plan.

Every tier sees the same links in the same places. Paid tiers never lose them and free results are never degraded.

| | Conservative | Base | Optimistic |
|---|---|---|---|
| Revenue per real trip (after attribution loss) | $0.12 | $1.04 | $3.09 |
| Revenue per monthly user per year (modeled) | $0.04 | $0.63 | $2.47 |
| Revenue per monthly user per year (rounded, decision of record) | $0.10 | $0.60 | $1.50 |
| Stacked with the higher-commission lanes of section 13 (per real trip, a range to test) | not modeled | about $4 to $17, versus $1.04 with affiliate links only | not modeled |

The stacked row adds the concierge lane ($2 to $6 a trip), group room blocks ($1.50 to $8) and in-app hotel booking ($0.50 to $3); it depends on founder hours, on attach rates that have not been tested, and on eligibility rules that are unverified (section 13.8). It is not in the scenario totals of [09](09-revenue-expansion.md). The rounded row is what the rest of the plan uses. It lifts the conservative case (the model gives $0.04) and trims the optimistic case (the model gives $2.47, which depends on the unproven sharing loop). The base case is within 5% of the model.

Share of base-case revenue per trip, by category:

| Category | Share |
|---|---|
| Lodging | about 60% |
| Tours and attractions | about 19% |
| Flights | about 10% |
| Insurance | about 4% |
| Transfers and car | about 3% |
| eSIM | about 2% |
| Everything else | under 2% |

What this means for the build:

1. Build the placement map around lodging, tours and the "Before you go" checklist. Flights are a service feature (cached fares pay 1.1% to 1.5%), not a revenue line.
2. The launch needs three integrations: Travelpayouts, Viator's self-service API and Stay22. Direct applications start at month 3, when there is traffic to show.
3. Two new surfaces carry real value: the pre-trip checklist and the after-trip compensation prompt.
4. Higher-commission lanes (section 13) pay 5 to 20 times a link click per booking, but they need a human, a licence or a merchant setup, so they start after the launch integrations and are optional for the user.
5. Compliance is a product feature here, not paperwork. Insurance, visas, disclosure labels and the ranking rule protect both App Review and user trust.

## 2. Direct answers to the owner's questions

### Airbnb

Airbnb has no affiliate program an app can join.

- Airbnb Associates (the open program) closed on 2021-03-31 and has no open replacement.
- Airbnb reportedly runs two Impact-tracked tracks, "Airbnb Creators" (social media influencers) and the "Airbnb Demand Program" (bloggers). Both are invite-only or selective, geo-limited and set per campaign (about 3 to 4% of booking value reported). The publisher program is reported as "not accepting applications". Both are aimed at content creators, not consumer apps. Airbnb also reportedly has invite-only API and brand deals.
- The only public money is host referral ("Refer a host"), which pays an existing user for recruiting a new host (reported $105 to $1,000 for homes, $50 for Experiences, $100 for Services, with regional promotions). It does not pay for guest bookings. Our users are guests, and commercial use of a personal referral link inside an app is likely against the terms.
- Airbnb Experiences has no public affiliate program either.
- Stay22 does not cover Airbnb (reported).

Decision: Airbnb listings get a plain link that the user clicks, unchanged, with no tracking parameters. Airbnb stays a supported link type because users want it. The plan does not count any Airbnb income. A long-shot application to the Demand Program is possible once the app has traffic and content.

### Vrbo

Vrbo is reachable through the Expedia Group Affiliate Program (Expedia, Hotels.com and Vrbo in one program), run on Impact (reported, verify at partner.expediagroup.com).

- Reported Vrbo rates are inconsistent: about 2 to 6%, some sources 5 to 12%, and 1.8% through Travelpayouts. Plan on the low side, roughly $12 to $36 on a $600 stay. Cookie about 7 days.
- It is the best legal source of whole-home rental commission for an app. Impact deep links can wrap any vrbo.com URL the user pasted, built from the URL text without fetching the page.
- Stay22 reportedly holds a strong Vrbo agreement, so it is a second route to the same brand.
- The Rapid API (search and book inside the app) is not realistic: partner-only, certification, PCI or Expedia checkout, reported 6 to 12 months and a six-figure cost. The lighter Travel Redirect API is an option later (verify eligibility).
- Approval for a new app with no traffic is uncertain. Apply at month 3 with a working product and click data.

## 3. Program catalogue

Conventions. "Cookie" is the attribution window in a browser. A native app has no cookies, so links carry a sub-id (section 8) and the window matters only if the user finishes the purchase in the same browser session. "App" says whether the program reportedly allows promotion from a mobile app. "Est." is what one booking would earn, using the stated order value and the reported rate. Status values: launch, month 3+ (apply directly or add once there is data), later, skip. Every rate is reported, verify, and the date checked is 2026-09-30.

### 3.1 Lodging

Estimate basis: $600 stay, 2 guests, 4 nights. Commissions are usually paid after check-out and cancelled stays pay nothing.

| Program | Network | Commission (reported, verify) | Cookie | App | API or links | Est. per booking | Status |
|---|---|---|---|---|---|---|---|
| Booking.com via Travelpayouts | Travelpayouts | 4% | Session to 24h | Verify in-app rules | Link tool, deep links | about $24 | launch |
| Agoda via Travelpayouts | Travelpayouts | 6% (direct 4 to 7% tiered) | 24h | Yes | Links, widgets | $24 to $36 | launch |
| Trip.com via Travelpayouts | Travelpayouts | up to 7% (hotels often 3 to 5%) | 30 days | By approval | Links, widgets | $18 to $42 | launch |
| Hostelworld via Travelpayouts | Travelpayouts | up to 40% of the deposit, about 3 to 4% of stay | 30 days | Yes | Links, widgets | $3 to $6 | launch (hostel items only) |
| Stay22 | Stay22 | 30% of Stay22's commission, negotiable, about 1.5 to 5% effective | Brand cookies, about 30 days (verify) | Website scripts; Direct Travel API contact-based (verify) | Maps widget, Link Swap, Direct Travel API | $9 to $24 | launch (challenger) |
| Expedia Group (Vrbo, Expedia, Hotels.com) | Impact | Vrbo 2 to 6% (some report more), Hotels.com 6 to 16%, Expedia 2 to 12% | 7 days (Hotels.com 30 outside US and CA) | Case by case, no cashback | Deep link generator, Travel Redirect API | Vrbo $11 to $36 | month 3+ |
| Booking.com direct | Network unclear (Awin ending, reported June 2026) | 4%, or a tiered share of Booking's commission | Session to 24h | Yes with mandatory disclosure line | Partner Center deep links | about $24 | month 3+ (confirm current network first) |
| Agoda direct | Agoda Partners | 4 to 7% tiered by monthly bookings | 24h | Yes | Deep links, Affiliate API (approved) | $24 to $36 | later |
| Trip.com direct | Trip.com Affiliate | up to 7% | 30 days | By approval | Links, widgets | $18 to $42 | later |
| HomeToGo | Direct, Awin, TradeTracker | 2.8 to 4% after check-in | 24h to 30 days | Publishers | Search widgets, white label (gated) | $17 to $24 | later (search links when nothing is saved) |
| Plum Guide | Partnerize | 7% | up to 90 days | Publishers | Deep links | $42 (rare) | skip |
| Kayak (hotels) | Kayak network, CJ | Click or revenue share | 30 days | Websites | Widgets | $8 to $20 | skip |
| Marriott, Hilton | CJ, Impact, Partnerize | about 2 to 6% | 7 days | Websites | Deep links | $12 to $36 | skip |
| Airbnb | None open | none | n/a | Not for apps | None | $0 | skip (plain link) |

Notes:

- Booking.com is in flux. The direct program moved to Awin in 2025, and the Awin arrangement is reported to be ending, with partners told to register anew. Check the Affiliate Partner Center before applying. Its Connectivity and Demand APIs are for channel managers and are not an option.
- Travelpayouts is the cheapest way to get Booking.com, Agoda and Trip.com on one contract with no traffic minimum, and it is already the flight provider.
- Stay22 Link Swap converts a Booking, Expedia, Hotels.com, Vrbo, Tripadvisor, Trivago or Kayak URL to a Stay22 link. It may raise conversion by routing to the brand the user is most likely to book, at a lower rate per booking than a direct program. Payout minimum reported $100 (some sources $25).
- Booking.com requires a disclosure line where the tracking link appears ("As a Booking.com Affiliate, I earn from qualifying transactions"), on top of our own sentence.

### 3.2 Flights

Estimate basis: $1,400 total for 2 passengers on one booking.

| Program | Network | Commission (reported, verify) | Cookie | App | API or links | Est. per booking | Status |
|---|---|---|---|---|---|---|---|
| Aviasales | Travelpayouts | 40 to 50% of Aviasales' income, about 1.1 to 1.3% of ticket | 30 days | Yes, app installs credited | Data API (cached fares, open), deep links with marker and sub_id. Search API needs 50,000 MAU | $15 to $18 | launch |
| Kiwi.com | Travelpayouts | about 3% | 30 days typical | Via Travelpayouts | Deep links (Tequila is invitation-only) | about $42 | launch (label self-transfer fares) |
| Trip.com flights | Travelpayouts | 1% to 3% | 30 days web, 7 days app | Travelpayouts signup | Links, widgets | $14 to $42 | launch |
| WayAway | Travelpayouts | about 1.1 to 1.3%, or $10 per WayAway Plus sale | 30 days | Yes | Links, widgets | $15 to $18 | later |
| Skyscanner | Impact | Revenue share, reported GBP 0.07 to 0.30 per flight click | 30 days | Unclear; reported bar of 5,000 monthly uniques | Links, widgets, partner-only API | $0.10 to $0.40 per click | month 3+ (the licensed fare data matters more than the cash) |
| Kayak, Momondo | Kayak network, CJ, Travelpayouts | Pay per click, about $0.30 to $1.20 per click-out | 30 minutes | Publisher application | Links, widgets | per click | later (a hedge against low conversion) |
| Expedia flights | CJ | flat about $1.25 to $2 | n/a | Open | Links | $1.25 to $2 | skip |
| CheapOair | CJ, Rakuten, Impact | flat $8 to $25 | 30 to 90 days | Network application | Deep links | $8 to $10 | skip |
| Google Flights | None | none | n/a | n/a | n/a | $0 | skip (SerpApi results must link through a partner, not Google) |

Flight commissions are thin because OTAs earn small margins on tickets. The Travelpayouts Data API "Book" link opens an Aviasales search with our marker, so the user may see a different price than the cached one. Use "price at last check" wording.

### 3.3 Car rental

Estimate basis: $350 rental.

| Program | Network | Commission (reported, verify) | Cookie | App | API or links | Est. per booking | Status |
|---|---|---|---|---|---|---|---|
| DiscoverCars | Travelpayouts, direct | 60 to 70% of its income, plus 25 to 30% on Full Coverage | 365 days | Travelpayouts signup | Deep links, widgets | $20 to $35 (plus $10 to $15 with coverage) | launch |
| Localrent | Travelpayouts, direct | at least 50% of its income, at least 7.5% of price | 30 days | Direct page | Links, widgets, API | about $26 or more | launch (strong outside the US) |
| QEEQ | Travelpayouts | 5% plus 10% of Diamond sales | 30 days | Yes | Links, widgets | about $17.50 | later |
| Rentalcars.com | Booking.com group | 6% | 30 days | Network | Links, widgets | about $21 | later (verify it is still open) |
| EconomyBookings | Webgains, Travelpayouts | 25% of broker commission, or 60% share | 24h (one source) | Application | Links | $10 to $25 | skip (short cookie) |
| Kayak cars | Kayak network | Click-out pay | 30 minutes | Same as Kayak | Links | $0.30 to $1 per click | skip |

### 3.4 Trains and buses

Estimate basis: $120 ticket.

| Program | Network | Commission (reported, verify) | Cookie | App | API or links | Est. per booking | Status |
|---|---|---|---|---|---|---|---|
| Omio | Travelpayouts, direct | 2 to 8% | 30 days | Application | Deep links, widgets, API | $2.40 to $9.60 | launch (best European coverage) |
| Trainline | Partnerize | 3% new customers, 1% existing | 30 days | Mobile apps named as eligible | Links, feeds | about $3.60 | month 3+ (UK and EU domestic) |
| 12Go | Travelpayouts, direct | 50% of on-site revenue | 30 days, last click | Open signup | Links, widgets, API | $3 to $6 | later (Asia trips) |
| Busbud | Travelpayouts | 5% | 7 days | Yes | Links, widgets, API | $6 | later |
| FlixBus | Direct, regional | 3 to 6% | 30 minutes to 30 days | Regional program | Links, widgets | $3.60 to $7.20 | later |
| Rail Europe | Direct, networks | 1 to 3% | 30 days | Application | Links, widgets | $1.20 to $3.60 | skip |

### 3.5 Airport transfers and rides

Estimate basis: $60 transfer.

| Program | Network | Commission (reported, verify) | Cookie | App | API or links | Est. per booking | Status |
|---|---|---|---|---|---|---|---|
| Welcome Pickups | Travelpayouts, direct | 8 to 9% | 45 days | Application | Links, widgets | $4.80 to $5.40 | launch |
| KiwiTaxi | Travelpayouts, direct | 9 to 11% | 30 days | Application | Links, widgets, API | $5.40 to $6.60 | launch |
| GetTransfer | Travelpayouts | up to 40% of booking fee | 30 days | Yes | Links, widgets, API | $2.40 to $6 | later |
| Intui.Travel | Travelpayouts | up to 40% of booking fee (one source) | 30 days | Yes | Links, widgets | $3 to $5 | skip until verified |
| Uber | Impact | about $5 per new rider | 30 days | Unconfirmed | Links | $5, new riders only | skip |

### 3.6 Tours and attractions

| Program | Network | Commission (reported, verify) | Cookie | App | API or links | Est. per booking | Status |
|---|---|---|---|---|---|---|---|
| Viator | Own Partner Program, Awin | 8%, paid on completed trips | 30 days | Basic Affiliate API is instant and self-service, no minimums | Affiliate API (search, details, photos, reviews), widgets, deep links; weekly payout, $50 minimum | $8 to $9 | launch |
| GetYourGuide via Travelpayouts | Travelpayouts (also Awin, own) | 8% (5 to 8% by network) | 30 to 31 days | Links: reported open. Partner API reportedly needs 50k app downloads | Widgets, deep links | about $8 | launch (widgets); direct month 3+ |
| Tiqets | Travelpayouts, own | 6% own, 8% via Travelpayouts | 30 days | Check app terms | Partner API, widgets | $4 to $6 | launch |
| Go City | Travelpayouts | 6% of gross | 90 days | Verify | Widgets, deep links | $6 to $10 | launch (pass cities only) |
| Klook | Travelpayouts, own | 2 to 5% | 30 days (7 hotels and cars) | Verify | Widgets, deep links | $3 to $6 | month 3+ (Asia trips) |
| Musement | Awin | 5.6 to 8% | 14 to 30 days | Verify | Widgets | about $6 | skip |
| Headout | Own | 1 to 10% by source | 30 days | Verify | Widgets | $4 to $5 | later |
| Civitatis | Own | 6 to 10% | 30 days | Verify | Widgets | about $6 | later (Spain, Latin America) |
| Airbnb Experiences | None | n/a | n/a | Not available | None | $0 | skip |

Showing Viator and GetYourGuide side by side is good UX and a hedge against losing one approval. Overlap between the two must not be double counted. The main engineering task is place-to-product matching (Geoapify place, then a supplier search by name and coordinates). Apply for the GetYourGuide Partner API only after 50k downloads.

### 3.7 Restaurants

Low money, high user value. Build it as a feature, not an income line.

| Program | Network | Commission (reported, verify) | Cookie | App | Est. per booking | Status |
|---|---|---|---|---|---|---|
| OpenTable | Impact-style | $0.25 to $1.00 per seated diner, no-shows pay $0 | Short (verify) | Verify | about $1.50 per party of 3 | later |
| TheFork | Awin, regional | 5 to 10% or fixed per seated booking | 20 days | Verify; EU only | $1 to $2 | later |
| Resy | No public program | n/a | n/a | n/a | $0 | skip |

Restaurant coverage is uneven, and a "Reserve" link that dead-ends hurts trust. Show it only where a real match exists.

### 3.8 eSIM

eSIM plans are digital services delivered to the phone. Link out only, never sell inside the app, never describe as an in-app unlock (section 7).

| Program | Network | Commission (reported, verify) | Cookie | App | Est. per sale | Status |
|---|---|---|---|---|---|---|
| Airalo | Impact | from 10% (up to 12%), new customers, one-off | 30 days; mobile app tracked via Impact and Adjust (reported) | Yes | $2 to $3 | month 3+ (best tracking; Partner API after 50k downloads) |
| Holafly | Own, Awin, Impact | 10%, negotiable to 20% | 30 days | Verify | $3 to $5 | later |
| Saily | Own, Awin, FlexOffers | 15% per new user | 30 days | Verify | $2 to $3 | later |
| Nomad | Impact, FlexOffers | 8 to 12% | 30 days | Verify | about $2 | skip |
| Yesim | Own | 10%, new users | Verify | Verify | $2 to $3 | skip |

A Travelpayouts connectivity program may carry some of these. Check the dashboard. If it does, launch eSIM through it, and add Airalo direct at month 3.

### 3.9 Travel insurance

Insurance is gated by legal review and by the rules in section 7.5. Do not switch it on until both are done.

| Program | Network | Commission (reported, verify) | Cookie | Est. per sale | Status |
|---|---|---|---|---|---|
| EKTA | Travelpayouts | 20% of premium | 30 days | $10 to $25 | launch, gated (non-US focus) |
| VisitorsCoverage | Travelpayouts, own | 3% per order (another source: tiered flat $1 to $100) | 45 days | $5 to $15 | launch, gated (US comparison marketplace) |
| World Nomads | Own | 10% | 60 days | $10 to $20 | month 3+ (strict content rules) |
| Heymondo | Yazing, own | 12% | Verify | $10 to $15 | month 3+ (short trips, EU friendly) |
| SafetyWing | Own | 10% | 364 days | $8 to $15 | later (nomads, monthly plan) |
| Insured Nomads | Own | 15% | Verify | $10 to $20 | skip |
| Squaremouth | Own | Not found | Not found | Verify | skip until a rate is confirmed |

Start with one insurer program plus one comparison marketplace.

### 3.10 Visas and entry authorizations

| Program | Commission (reported, verify) | Cookie | Est. per application | Status |
|---|---|---|---|---|
| iVisa | 10 to 20% (up to 35% on photos) | 30 or 365 days (reports differ) | $8 to $12 | later (after the compliance design) |
| VisaHQ | 10% of service fee | 2 years | $5 to $10 | later |

The official government link always comes first (section 7.6).

### 3.11 Money

| Program | Network | Payout (reported, verify) | Cookie | Status |
|---|---|---|---|---|
| Wise | Partnerize, direct | GBP 10 per personal account, GBP 50 per business account; needs a qualifying first action (verify) | 365 days | later |
| Revolut | Impact | GBP 2 to 20 per personal signup by plan | 30 days | later |
| Travel credit cards | CardRatings, Bankrate, CJ, Impact | $50 to $200 or more per approved application | 7 to 30 days | skip (section 4.3) |

### 3.12 Post-trip compensation

Paid only when a flight was delayed or cancelled and qualifies (mostly EU261 and similar rules, which most US-to-US trips do not meet). Build it as the after-trip prompt in section 6.

| Program | Network | Commission (reported, verify) | Est. per claim | Status |
|---|---|---|---|---|
| Compensair | Travelpayouts | Fixed per confirmed application, EUR 10 base, higher tiers reported (EUR 20 for the United States at 10 confirmed applications, verify) | EUR 10 to 20 | launch (simple, paid per application) |
| AirHelp | Direct affiliate page, networks | 15% of AirHelp's fee on an approved claim, 20% on AirHelp+ | $13 to $30 per approved claim | month 3+ (best-known brand) |
| SkyRefund | Direct, Awin | Not published | Unknown | skip until terms are known |
| ClaimCompass | n/a | Acquired by AirHelp on 2024-11-27 | n/a | skip |

### 3.13 Other trip needs

| Category | Program (network) | Commission (reported, verify) | Est. per sale | Status |
|---|---|---|---|---|
| Luggage storage | Radical Storage (Travelpayouts) | 15% via Travelpayouts, 8% elsewhere | $1 to $2 | launch (via Travelpayouts, on checkout days) |
| Luggage storage | Bounce, which now owns Nannybag (own) | 10% | $1 to $2 | later |
| Lounges | Priority Pass (Travelpayouts) | 10%, or $14 per sale | $15 to $26 | later (a link in the checklist only) |
| Photography | Flytographer (own) | 10% | $15 to $40 | later (honeymoons and couples) |
| Pet sitting | TrustedHousesitters (own) | about $28 per sale | $28 | later |
| Parking | Way.com, SpotHero | 2.4 to 7% | $2 to $4 | skip |
| Cruises | CruiseDirect | 3% | $60 to $100 | skip |
| Travel gear | Amazon Associates | about 1 to 4.5% | $1 to $2 | skip (section 4.3) |
| VPN | NordVPN, Surfshark, ExpressVPN | 30 to 100% | $25 to $40 | skip (section 4.3) |

## 4. Network strategy

### 4.1 Launch: Travelpayouts, Viator and Stay22

| Network | Role at launch | Why |
|---|---|---|
| Travelpayouts | Default for flights (Aviasales, Kiwi.com, Trip.com), stays (Booking.com, Agoda, Trip.com, Hostelworld), cars (DiscoverCars, Localrent), transfers (Welcome Pickups, KiwiTaxi), tours (GetYourGuide, Tiqets, Go City), luggage storage, compensation (Compensair), gated insurance (EKTA, VisitorsCoverage) | One signup, one dashboard, one statistics API, `sub_id` on links, no traffic minimum, already the flight data source. Payout threshold reported $50, monthly. |
| Viator partner API (Basic access) | In-itinerary "Things to do" cards | Instant, self-service, no minimums. Gives search, details, photos and reviews. Weekly payout, $50 minimum (reported). |
| Stay22 | Lodging challenger and map of stays near itinerary points | Covers Booking.com, Expedia, Hotels.com, Vrbo and others through Link Swap. Gives a second route to Vrbo before the Expedia Group approval. |

Rules: never mix two networks on one button. One partner per surface per test cell. Ask Travelpayouts support in writing, before launch, whether a native app using the partner-links API and a server-side redirect is allowed (the public agreement lists mobile apps and White Label as allowed methods, verify).

### 4.2 From month 3: direct applications

Apply in parallel so approvals exist when volume does. Each direct program needs its own reporting adapter, so add one only when its network's revenue justifies it (roughly $1,000 a month from one partner).

| Program | Network | Why apply |
|---|---|---|
| Expedia Group | Impact | The only route to Vrbo, plus Expedia and Hotels.com. Highest rate ceiling for lodging. |
| Booking.com | Confirm the current network | Possible better rate than the Travelpayouts 4%. Confirm the network before applying. |
| Skyscanner | Impact | Licensed live fare source the plan wants. The fare data is worth more than the click income. |
| Airalo | Impact | Explicit mobile app tracking. |
| GetYourGuide | Own program | Direct rate and, later, the Partner API (50k downloads). |
| Trainline, AirHelp, World Nomads, Heymondo | Various | Add after the first paid data shows demand in those categories. |

### 4.3 Avoid or defer

| Item | Decision | Reason |
|---|---|---|
| Travel credit cards | Not at launch. Revisit at about 100k MAU with counsel and a specialist publisher network | Issuers screen publishers. Chase is reported to be reachable only through CardRatings or Bankrate. Every card page needs issuer-approved terms and legal review. AI-written card copy is a hazard, and "best card for Japan" drifts into advice. |
| VPNs | Not at launch | Large payouts but off-brand. Platforms and networks scrutinize privacy claims. At most a single neutral "public wifi" tip later. |
| Amazon product data | Not in the app | Product Advertising API data may not be used inside mobile apps (reported, verify), PA-API is being replaced by the Creators API, and new accounts must make qualifying sales. A static packing list with plain tagged links is the only safe form, and only if a packing list exists anyway. |
| Expedia Rapid API | Skip | Partner-only, certification, PCI or Expedia checkout, 6 to 12 months, six-figure cost. Use affiliate links instead. |
| Partnerize | Avoid for new integrations | Merging into CJ (reported). Contracts migrate to the CJ dashboard after 2026-12-31. Use it only where a brand (Trainline, Wise) forces it. |
| Airbnb | No integration | Section 2. |
| Cruises, parking, gear | Skip | Under $0.10 per trip, each with its own UI and disclosure load. |

## 5. Placement map

Global guardrails, applied to every row:

1. **Label.** "We earn a commission if you book here." beside every partner button, and an "Ad" tag on UK and EU storefronts.
2. **Never rank by commission.** Every list says how it is sorted (price, rating, distance, hearts). Partner prices show the date checked and the provider.
3. **Neutral links stay neutral.** Pasted links stay exactly as pasted (section 5.1).
4. **No ads.** No banners, no sponsored slots, no partner copy in AI answers.
5. **Show the non-affiliate route** where one exists: "Search on the airline's site" beside a flight, "Open your saved link" beside a stay.
6. **Frequency.** At most one affiliate card per screen view, except on lists the user asked for (lodging shortlist, checklist). No pop-ups or interstitials. Never during presentation playback.
7. **Evidence ethos.** Each card says why it is there (the user's dates, a saved item, a sourced AI note) and what the price is based on. No manufactured urgency.
8. **Intent first.** No insurance card until the trip has a chosen flight or a booking. No eSIM card for domestic trips.
9. **Kill switch** per partner through the feature flag config (07).
10. **Paid users** still see the links, never louder than for free users. The disclosure is never hidden.

| Screen or moment | Category | UI treatment | Guardrail | Value |
|---|---|---|---|---|
| Trip created | None | No affiliate UI | Do not monetize the first minute | 0 |
| Destination chosen (overview) | Lodging, activities | One quiet card "Places to stay in <City>" (partner map or search link with the trip dates and party size), collapsed after first view | Only when dates exist. AI destination text never names a partner. | Medium |
| Flight route added, price chart, date grid | Flights | Nothing extra. Cached fares from Travelpayouts, no partner logo in the ranking | Charts stay neutral | 0 |
| Flight chosen | Flights | Chosen-flight card: primary "Book on <provider>" through `/go/`, secondary "Search on the airline's site", and "Next: add stays and a checklist" | Show fare age ("cached 6 h ago") and that the price can change | Low per booking, high intent |
| Price alert (push, email, in-app) | Flights on a tracked route | In-app: "Fare fell $42 since Tuesday. View fare" opens the route, where the Book button lives. Email links to the in-app route, not to the partner | Alerts only for routes the user tracks. No promo-only push (Apple 4.10). Disclose in email. | Medium |
| Lodging shortlist and hearts | Lodging | Stays that came from a partner search get a "Book" button. Pasted links show the user's own URL. A separate "Compare on other sites" link opens a labeled partner search. A "cheaper on <partner>" line appears only with real, dated price data | Never rewrite pasted Airbnb, Vrbo or Booking.com URLs. Never fetch those pages. | High |
| Lodging import (paste, bookmarklet) | None | No affiliate UI. Say "We never change your links." | The trust moment | 0 |
| Search rentals dialog | Lodging | Rows with partner name and sort statement. "Save to shortlist" first, "View" (affiliate) second | Sort by price or rating only | High |
| Itinerary (trip level) | Tours, transfers | "Tickets and tours for this trip" card built from the user's own bookable items, plus Viator "things to do" suggestions (section 6.3) | Only items already in the itinerary, or clearly labeled suggestions | Medium |
| Itinerary day | Tours, transfers, car | "Tickets" button on bookable attractions. Arrival day: airport transfer card. Drive day: car card | Parks and viewpoints get nothing. No reordering of the day. | Medium to high |
| Places (search, detail) | Tours, restaurants | "Tickets" or "Book a table" chip on the detail view, not in the results list | Results ranked by relevance and distance only. Geoapify and Wikipedia attribution stays. | Low to medium |
| Presentation mode, shared pages, PDF | Lodging, tours | Optional last slide "Book the plan" listing every partner link, labeled. Owner can turn it off. Print and PDF keep links live with the sentence printed | Nothing during playback. No partner logos on normal slides. Guests have no accounts. | Medium (viral) |
| "Before you go" checklist | eSIM, insurance, transfers, car, missing bookings | "Get it" buttons on affiliate items (section 6.1) | Section 6.1 and 7 | High |
| During the trip | Tickets for today, transfer home | A "Today" card with a bookable item only if the day has an unbooked eligible activity | No urgency copy. No push to sell. Offline mode shows no partner content. | Medium |
| After the trip | Compensation, next trip | "Was your flight delayed?" prompt (section 6.2) and a "How was the trip?" card | No affiliate button on the review card. Do not monetize goodwill. | Low |
| Agent runs page and AI output | None | Evidence and source links only | Affiliate cards never appear inside AI output. AI never steers to a partner. If output includes a price, show the commission-blind ranking statement. | 0 |
| Settings, "How we earn money" | All | Static page listing partners, the sentence and the ranking rule. A "Hide booking links" switch collapses buttons to a plain "Open on partner site" link | The switch is a trust feature and costs little | 0 |
| Trips home, paywalls | None | No affiliate content. Never an affiliate card beside an upsell | After a booking through an affiliate link, only a soft prompt to plan the days | 0 |

### 5.1 The pasted-link rule and the no-fetch rule

- A pasted listing link stays exactly as pasted. The saved item's "Open" button opens the user's URL unchanged, with no wrapper and no tracking parameters.
- A separate, labeled "Book via partner" button offers a partner link built from the URL text (host, path and the trip's dates), never by fetching the page. It appears only when a program is approved for that host (booking.com, vrbo.com, expedia.com, hotels.com, agoda.com, trip.com, hostelworld.com). It never appears for Airbnb.
- With no saved link, offer "Find on Booking, Vrbo or Agoda" search links prefilled with destination, dates and guests.
- **The hosted server never fetches Airbnb, Vrbo or Booking.com pages, not even for a user-requested preview.** Today's app has a user-triggered preview in `backend/tripplanner/providers/link_preview.py` that fetches one page. The hosted version must disable it for those domains (and for the Expedia Group brands and other partner hosts as a precaution), and show only what the user typed or imported with the bookmarklet. This also fixes a terms risk that grows with scale, since the servers would be the ones breaching site terms (04, 06).

## 6. New features that create affiliate surfaces

### 6.1 "Before you go" checklist

A per-trip card on the trip overview. It appears when the trip has a chosen flight or a saved stay, or 45 days before departure, whichever comes first. It also shows in presentation mode and offline. It is a real product feature, and the partner items are honest slots inside it.

| Group | Item | Trigger | Affiliate |
|---|---|---|---|
| Bookings | Flights booked | Chosen flight not marked booked | Yes (flights) |
| Bookings | Stay booked | Shortlisted stay not marked booked | Yes (lodging) |
| Bookings | Tickets for top itinerary items | Bookable activities exist | Yes (tours) |
| Getting around | Airport transfer or car | Arrival day has a flight | Yes (transfers, car) |
| Connectivity | eSIM for <country> | International trip | Yes (eSIM) |
| Safety | Travel insurance | Booked flight and dates | Yes (insurance, section 7.5) |
| Documents | Passport validity, visa or e-authorization, vaccinations | Country pair | No: official government link |
| Luggage | Storage on checkout day | Checkout day with a late departure | Yes (luggage storage) |
| Money | Tell the bank, get cash, a no-fee card | Always | No |
| Home | Mail hold, pet care, out-of-office | Always | No |
| Packing | Packing list from the weather | Weather known | No |

Rules:

- At least half of the items are unmonetized. That is what makes the checklist believable.
- Each affiliate item shows what it is, why it is here ("You land in Lisbon at 21:40"), the cost range if known, and three actions: "Get it" (affiliate), "I have this", "Not needed". The disclosure sentence sits on the card header and on each button row.
- Done and dismissed states persist per trip. One nudge per item per week at most. The only push is a single opt-in "7 days before departure" reminder.
- Print and PDF show the checklist without affiliate buttons by default (a clean handout).
- Backend sketch: table `trip_checklist_items (id, trip_id, kind, status, dismissed_at, done_at, meta jsonb)` with a fixed enum of kinds, a small rules module that derives the visible list, and `GET` and `PATCH /trips/:id/checklist`. Regenerate `schema.d.ts` after adding routes. Events: `checklist_item_shown`, `checklist_item_clicked` (through `/go`), `checklist_item_done`.

### 6.2 After-trip compensation prompt

On the day after the last trip date, if the trip has a chosen flight, ask "Was your flight delayed or cancelled?" with "No" and "Yes, check what I can claim". Only "Yes" shows a partner link (Compensair at launch, AirHelp from month 3), with the commission sentence and the plain note that eligibility depends on the route and rules (mainly EU261 and similar), and that no result is promised. Never a push. Not shown for trips with no flight. Expected attach is about 1% of trips, so it is a UX feature that occasionally pays.

### 6.3 Itinerary "things to do" from Viator

Use the Viator Basic Affiliate API to suggest bookable activities near a day's plan, matched by name and coordinates from the Geoapify place. Each card carries a source link and the price with its date. It is labeled as a suggestion, sorted by rating and distance, and shows nothing when there is no real match. This is the largest non-lodging revenue line (about $1.50 per trip in the base case).

### 6.4 Car and transfer cards on travel days

The arrival day (from the chosen flight's landing time) gets an airport transfer card (Welcome Pickups, KiwiTaxi). A day with a drive between cities, or a trip with a rental plan, gets a car card (DiscoverCars, Localrent). Both show only for trips where the need is visible in the data, and both offer the non-affiliate route (a note field, "I will arrange this myself").

### 6.5 Compare-and-book on the chosen flight

On the chosen flight, show the cached fare with its age and provider, then one primary "Book on <provider>" button and one equal-weight "Search on the airline's site" link. If a live check is available (a live route), show two or three providers side by side, sorted by price, with a sort statement. Where the price differs from the booking page, say so.

## 7. Compliance

### 7.1 Apple App Review

- **Guideline 3.1.3(e)** (goods and services consumed outside the app): flights, stays, tours, transfers, cars and insurance are sold on the merchant's own checkout, so In-App Purchase does not apply and Apple takes no commission on them. (The research brief cited 3.1.5 for this. In the current guidelines 3.1.5 is cryptocurrencies.)
- **Guideline 3.1.1:** Plus, Trip Pass and credit packs use StoreKit. **Affiliate purchases never unlock app features**, and nothing in the app is worded as if they do.
- **eSIM and VPN** are digital services delivered to the device, so a reviewer could read them as digital goods. Link out only, never sell in the app, never describe them as an in-app unlock.
- **Guideline 5.1.1(vii):** the in-app browser must be visible and never hidden or used to track users without consent.
- **Guideline 4.10:** no promotional pushes whose only purpose is to drive affiliate clicks. User-requested price alerts are fine.
- **Guideline 4.2:** the app must be useful without the links. As a planner it is. Use several partners and a neutral UI so it does not look like a storefront for one.
- Review notes (07, section 6.9) explain that bookings happen on partner sites, that we earn a commission, and that the redirect is first-party with a random per-click id and no IDFA.
- Epic v. Apple (a Supreme Court petition was granted 2026-06-30, reported, verify) concerns web checkout for digital purchases. It bears on Plus and Trip Pass, not on affiliate links.

### 7.2 App Tracking Transparency

Affiliate clicks go through our own server. Design choices that keep this outside ATT (reported, verify in review notes):

- Our server logs the click and redirects. It does not link our user data to other companies' data for advertising.
- The sub-id is a random per-click token, never the user id, email, IDFA, IDFV or a device fingerprint.
- Conversions are pulled by our server from the network API and joined to our click table in our own database.
- No third-party ad, attribution or analytics SDK (AppsFlyer, Adjust, Facebook, Google Ads). No hashed email or phone sent to any partner.
- Privacy label: Usage Data (product interaction: outbound clicks), linked to identity, for Analytics and App Functionality, not used for tracking. The result is no ATT prompt.

### 7.3 In-app browser

Default to SFSafariViewController (the Capacitor Browser plugin), which Apple prefers and which shows the URL and a Done button. It does not share cookies with the Safari app, so a user who clicks in the app and books later in Safari may not be attributed. External Safari keeps attribution for a return visit but leaves the app. Never use an embedded web view with injected JavaScript. Always carry the sub-id in the URL and never rely on cookie state alone. A/B test 1 (section 10) measures the difference.

### 7.4 Disclosure wording

- **United States (FTC, 16 CFR Part 255, revised 2023):** a material connection must be disclosed clearly, next to the recommendation, in plain words. A disclosure only in Settings or an About page is not enough. "Affiliate link" alone is not adequate. The sentence used everywhere is: **"We earn a commission if you book here."**
- **United Kingdom (CMA and ASA):** affiliate links are advertising. Use "Ad" on the card. "Affiliate" alone is not enough. The Digital Markets, Competition and Consumers Act 2024 gives the CMA direct fining powers.
- **European Union:** commercial intent is material information (Unfair Commercial Practices Directive). The Omnibus Directive requires transparency about paid placement and the main ranking parameters. Every "best" or "cheapest" list states its basis (price, rating, hearts) and that commission plays no part.
- **GDPR:** click logs (user id, trip id, hashed IP) are personal data. List them in the privacy policy with purpose "affiliate revenue attribution and fraud detection", legal basis legitimate interest, and retention of 25 months for click rows and 7 years for financial aggregates (suggested).
- **Where the disclosure goes:** next to every partner button, in AI output cards, on shared trip pages, in presentation mode, and in the PDF (links there are live). It is text, not color only, and VoiceOver reads it in the same element as the button. A "How we earn money" page is linked from Settings, the paywall and empty states.
- Booking.com adds its own required line where the tracking link appears.

Legal review of this wording for the US, UK and EU is a pre-launch item.

### 7.5 Insurance

- US insurance is state regulated. Unlicensed parties generally cannot sell, solicit or negotiate, quote rates or advise on coverage. Some states allow flat referral fees to introducers who only refer. Counsel confirms per state. The EU Insurance Distribution Directive can reach comparison and introducer activity depending on the member state. Pure introducer activity is the safe zone.
- **The app refers and never advises.** It shows provider names, a one-line provider-supplied summary, a "Get a quote" link out, and "This is not advice."
- Use insurer-approved copy only, as static text. No "you need this" nudges, no ranking based on the user's trip, no comparison of coverage.
- **AI is blocked from insurance advice.** The research agent and the Haiku assistant may not recommend insurance or judge coverage. If a user asks, they are routed to the static block.
- World Nomads bans affiliates from recommending insurance or comparing insurers. Follow each program's content rules.
- Launch is gated by legal review. Start with one insurer plus one marketplace.

### 7.6 Visas and entry authorizations

Look-alike "government" sites for ESTA, UK ETA and Canada eTA are a known scam category, and stores and payment providers scrutinize them.

- The official government link comes first, with a plain statement that a third-party service is optional.
- A third-party service is labeled "paid assistance service, fee X on top of the government fee".
- Never mimic government branding, never name anything "ESTA" or "eTA", and keep it off by default until the partner terms are reviewed.
- Recheck ETIAS timing. If it is live or close, pre-trip authorization demand rises.

### 7.7 No ranking by commission

No list, badge, AI answer or default sort depends on commission. When two partners offer the same item, pick by an A/B cell or by the user's own criteria, never by payout. Test variants may not hide the disclosure or change ranking by commission. Settings has a "Hide booking links" switch.

## 8. Tracking and reporting

The flow extends section 6 of [06](06-database-and-data-integrations.md).

1. The app calls `POST /api/outbound {entity_type, entity_id, surface, trip_id}`. The server checks trip access, picks the program (feature flags, geography, A/B cell), inserts a `link_clicks` row and returns `https://<host>/go/<click_id>`. The click id is a random 128-bit id, base62, about 22 characters.
2. The app opens the URL in SFSafariViewController.
3. `GET /go/<click_id>` looks up the row, checks it is fresh (under 10 minutes, not used twice), sets `clicked_at`, and returns an **HTTP 302** to the partner URL built from the stored template, with the affiliate id, the sub-id and the deep link. Headers: `Cache-Control: no-store` and `Referrer-Policy: no-referrer`. The response never renders a page, so there is no third-party JavaScript, pixel or cookie from us.

Sub-ids:

- The sub-id sent to the network is the click id (or an 8 to 12 character short code in `link_clicks.short_id` where a network limits length; check each network's limit, reported, verify).
- User id, trip id and email never appear in a URL. The join from conversion to click to user and trip happens in our database.
- A static surface tag (such as `s=lodging-shortlist`) goes in a second field where supported (Stay22 `campaign`, Impact `subId2`), so reports group by surface without our database.

Tables (06 has the base definitions):

- `affiliate_programs`, `link_clicks`, `affiliate_conversions` (unique on `program_id, network_txn_id`) and `affiliate_payouts` as in 06.
- `link_clicks` gains `short_id`, `program_variant` (A/B cell), `opened_in` (`sfsvc` or `safari`), `clicked_at`, `redirect_status`, `country`, `platform`, `app_version` and `checklist_item_kind`. Keep the salted `ip_hash`, rotated monthly. No advertising id.
- `affiliate_conversions` gains `clicks_lag_hours`, `reversal_at` and a status history.

Integrity: rate-limit `/api/outbound` (for example 60 an hour per user), dedupe repeat clicks within 30 seconds, mint click ids only through the authenticated app call, and allow no open redirects (stored templates only, never a `url=` parameter). No self-purchase or cashback schemes that programs prohibit.

Reporting:

- Nightly worker jobs pull each network's API: Travelpayouts booking statistics and payments first, then Impact Actions, and Awin or CJ where used. Each does an idempotent upsert on `(program_id, network_txn_id)` with status changes (pending, approved, rejected, paid).
- Match to clicks by sub-id. Track the unmatched share as a health metric; above 10% means a tracking break.
- Internal admin views: `revenue_by_month`, `revenue_by_surface`, `revenue_by_partner`, `revenue_per_mau` (same MAU definition as the plan), `click_to_booking_by_surface`, days from click to booking, days to payout.
- A cash view splits pending, approved and paid, and projects cash three months out from the real pending-to-approved ratio.
- Alerts: clicks down more than 50% day over day, redirect 4xx or 5xx above 1%, a failed conversion job, a program approval rate under 60%.

## 9. Revenue model

### 9.1 Method

Revenue per monthly user per year = real trips per MAU per year x attribution survival x the sum over categories of (outbound clicks per real trip x click-to-booking rate x net commission per booking).

A real trip has dates within 12 months and at least one of a chosen flight, a shortlisted stay or two itinerary items. Net commission is the booking value times the rate, after cancellations and reversals (10 to 25%) and after the aggregator's share. Attribution survival is the share of true bookings the network credits to us (cookie loss, other devices, app handoffs, in-app browser cookie separation).

### 9.2 Inputs

| Input | Conservative | Base | Optimistic |
|---|---|---|---|
| Real trips per MAU per year | 0.3 | 0.6 | 0.8 |
| Attribution survival | 0.60 | 0.75 | 0.90 |

| Category | Clicks per trip (C / B / O) | Click-to-booking | Net commission per booking |
|---|---|---|---|
| Flights | 0.8 / 1.2 / 1.5 | 1.0% / 2.0% / 3.0% | $3.5 / $6 / $9 |
| Lodging | 0.8 / 1.5 / 2.0 | 1.5% / 3.0% / 3.5% | $11 / $19 / $26 |
| Tours | 0.5 / 1.5 / 2.5 | 2.0% / 4.0% / 5.0% | $2.7 / $4.3 / $6 |
| eSIM | 0.2 / 0.4 / 0.7 | 3% / 5% / 8% | $1.0 / $1.5 / $2.5 |
| Insurance | 0.15 / 0.3 / 0.5 | 1% / 2% / 2.5% | $4.8 / $9.6 / $14 |
| Transfers and car | 0.2 / 0.4 / 0.6 | 1.5% / 3% / 4% | $2 / $4 / $6 |

Worked example, base lodging: 1.5 clicks x 3.0% = 0.045 bookings x $19 = $0.855.

### 9.3 Per trip

| Category | Conservative | Base | Optimistic |
|---|---|---|---|
| Flights | $0.028 | $0.144 | $0.405 |
| Lodging | $0.132 | $0.855 | $1.820 |
| Tours | $0.027 | $0.258 | $0.750 |
| eSIM | $0.006 | $0.030 | $0.140 |
| Insurance | $0.007 | $0.058 | $0.175 |
| Transfers and car | $0.006 | $0.048 | $0.144 |
| **Total before attribution loss** | **$0.206** | **$1.393** | **$3.434** |
| Times attribution survival | x 0.60 = **$0.12** | x 0.75 = **$1.04** | x 0.90 = **$3.09** |

Base shares: lodging 61%, tours 19%, flights 10%, insurance 4%, transfers and car 3%, eSIM 2%. Categories outside this table (restaurants, luggage storage, compensation, money) add cents and are not counted.

### 9.4 Per monthly user

| | Conservative | Base | Optimistic |
|---|---|---|---|
| Per trip after attribution loss | $0.124 | $1.044 | $3.091 |
| Real trips per MAU per year | 0.3 | 0.6 | 0.8 |
| Modeled revenue per MAU per year | **$0.04** | **$0.63** | **$2.47** |
| Outbound clicks per MAU per year | 0.80 | 3.18 | 6.24 |
| Credited bookings per MAU per year | 0.007 | 0.075 | 0.240 |
| Average net commission per credited booking | about $5.3 | about $8.4 | about $10.3 |
| Decision of record (rounded) | $0.10 | $0.60 | $1.50 |

Cross-check against earnings per click (click-to-booking times net commission): base lodging $0.57, flights $0.12, tours $0.17. Reported Booking.com earnings per click run $0.50 to $2.00 (blog, verify), so base lodging sits at the low end, which fits a planner where many clicks are revisits.

### 9.5 Check against the earlier assumption

The earlier plan ([01](01-business-plan.md), "Affiliate reality check") assumed about $3 net per booking and 0.13 to 0.4 bookings per MAU per year, giving $0.40, $0.80 and $1.20.

| | Earlier plan | This model | Comment |
|---|---|---|---|
| Credited bookings per MAU per year | 0.13 / 0.27 / 0.40 | 0.007 / 0.075 / 0.24 | The earlier plan assumed 2 to 4 times more bookings in the base case |
| Net commission per booking | $3 flat | $5.3 / $8.4 / $10.3 | Lodging pulls the average up. The two errors roughly offset in the base case. |
| Revenue per MAU per year | $0.40 / $0.80 / $1.20 | $0.04 / $0.63 / $2.47 | Base is within 22% of the earlier figure. Conservative is about 10 times lower. Optimistic is about 2 times higher. |
| Restated (README) | | $0.10 / $0.60 / $1.50 | Used everywhere from now on |

What has to be true:

- **$0.40 per MAU per year:** about 0.4 real trips per MAU, 75% attribution survival, and base click behavior on lodging (1.5 clicks, 3% conversion).
- **$0.60 to $0.80:** the base case, or about 0.75 real trips per MAU.
- **$1.20 to $1.50:** about 1.0 real trip per MAU and 90% attribution survival. This is the practical ceiling until direct programs and higher-rate partners are in place.

Sensitivity of the base case ($0.63 modeled):

| Lever | Result per MAU per year |
|---|---|
| Lodging click-to-booking falls from 3% to 1.5% | about $0.44 |
| Attribution survival falls from 0.75 to 0.60 | about $0.50 |
| Drop flights entirely | about $0.56 |
| Real trips per MAU rise from 0.6 to 1.0 | about $1.04 |
| Direct Booking.com program (net lodging commission $19 to $24) | about $0.73 |
| No pre-trip checklist | about $0.50 |

Effect on the year 3 affiliate line in 01: conservative (12,000 MAU) about $1.2k at the restated $0.10 (earlier $4.8k), base (60,000 MAU) about $36k at $0.60 (earlier $48k), optimistic (200,000 MAU) about $300k at $1.50 (earlier $240k). The optimistic figure depends on the unproven sharing loop.

Kill rule: at month 9, affiliate income under $0.20 per monthly user per year (annualized) stops investment. The base case ($0.60 a year, about $0.05 a month) clears it. The conservative case ($0.10) does not. Track the annualized figure monthly from launch.

## 10. A/B tests in priority order

Sample size is the constraint. At a 3% lodging click-to-booking rate, detecting a lift from 3.0% to 3.6% needs roughly 20,000 clicks per arm (80% power, alpha 0.05). Early on, test click-through and frequent funnel steps, and treat bookings as a slow aggregated measure.

| # | Test | Variants | Primary metric | Guardrail |
|---|---|---|---|---|
| 1 | Link-out container | SFSafariViewController vs external Safari | Tracked bookings per 100 clicks | Return-to-app rate, complaints |
| 2 | Lodging partner | Travelpayouts (Booking.com) vs Stay22 vs direct once approved | Net commission per click | Cancellation and reversal rate |
| 3 | Disclosure wording | The standard sentence vs "Paid link: we earn a commission." vs the standard sentence plus "Ad" | Click-through rate | Complaints, reviews mentioning ads |
| 4 | Checklist timing | 45, 30 or 14 days before departure | Checklist clicks per trip | Dismiss rate |
| 5 | Button position on lodging cards | Shortlist header, each card, card menu | Clicks per shortlisted stay | Save-to-shortlist rate must not fall |
| 6 | Price alert delivery | Push, email, in-app only | Alert to route-view rate | Notification opt-out rate |
| 7 | "Book the plan" slide | On by default vs off | Guest clicks per shared trip | Owner turn-off rate |
| 8 | "Hide booking links" switch | Visible vs hidden in Settings | Share using it | Revenue per MAU |
| 9 | Paid-tier weighting | Same cards for paid vs collapsed into the checklist | Revenue per Free MAU | Paid churn |

Rules: one test per surface at a time. Pre-register the metric. Randomize per user, stored server-side. Never test a variant that hides the disclosure or ranks by commission. Stop tests that lower satisfaction (thumbs, support tickets). Compliance floor for test 3: every variant discloses.

## 11. Rollout by roadmap phase

| Phase | Affiliate work |
|---|---|
| M0: validate | Create Travelpayouts and Viator accounts. Read the Travelpayouts agreement on mobile apps and email support in writing. Test link generation by hand. Mock the "Before you go" card in interviews and ask which items people would use. No code. |
| 0: foundations | Add `affiliate_programs` seed data (launch programs only) and the feature flag per partner. Design the `/go/<click_id>` redirect and `link_clicks`. Write the AI guardrails: no partner steering, no insurance advice. |
| 1: hosted web beta | Ship `/api/outbound` and `/go`, the nightly Travelpayouts import, the disclosure sentence and the "How we earn money" page. Disable link preview for Airbnb, Vrbo, Booking.com and partner hosts. Ship chosen-flight Book, the lodging "Book via partner" button, Viator things to do and the checklist (without insurance). Add the internal revenue dashboard. Start Stay22 on a share of users. |
| 2: iOS TestFlight | SFSafariViewController through Capacitor, "Ad" label by storefront, privacy label entry, review notes text. Run A/B test 1 (container). Add a legal review for disclosure and insurance. |
| 3: public launch | Confirm no ATT prompt and the review notes with Apple. Turn on gated insurance (EKTA or VisitorsCoverage) after legal sign-off. Submit direct applications at month 3: Expedia Group, Booking.com, Skyscanner, Airalo, GetYourGuide. Ship the after-trip prompt. |
| 4: growth | Add approved direct programs and their reporting adapters. Run the A/B queue. Add Trainline, AirHelp, World Nomads and Heymondo where data supports it. Shareable trip pages carry the "Book the plan" section with labels. Revisit credit cards at about 100k MAU. Set up the concierge lane (host agency, registrations, E&O, request form) as in section 13, then group room-block requests. |

Checklist:

- [ ] Travelpayouts written answer on native app use and sub_id limits
- [ ] Viator Basic access key
- [ ] Stay22 account and app terms confirmed
- [ ] `/go/<click_id>` live with `Cache-Control: no-store` and no open redirects
- [ ] `link_clicks` and `affiliate_conversions` migrated, nightly import running
- [ ] Unmatched conversion share under 10%
- [ ] Disclosure sentence beside every partner button, "Ad" on UK and EU storefronts
- [ ] Sort statement on every list, no commission-based ranking
- [ ] Pasted-link rule and "Book via partner" button working, never for Airbnb
- [ ] Link preview disabled for Airbnb, Vrbo and Booking.com
- [ ] AI blocked from insurance advice and from partner steering
- [ ] Insurance copy approved by the insurer and reviewed by counsel
- [ ] Visa cards show the official link first
- [ ] SFSafariViewController in use, no ad or attribution SDK, no ATT prompt
- [ ] App Review notes describe the redirect and the commission
- [ ] Kill switch per partner tested
- [ ] Direct applications sent at month 3

## 12. Open items to verify

1. Travelpayouts: written confirmation that a native app with the partner-links API and a server-side redirect is allowed; sub_id length and characters; payout threshold; which connectivity and insurance programs it carries in 2026.
2. Booking.com: current network, app terms, deep links to specific properties, and whether an app-only publisher is admitted.
3. Expedia Group (Impact): approval requirements for a new app, real Vrbo rate card, app rules.
4. Skyscanner: approval requirements and eligibility for an app (reported 5,000 monthly uniques).
5. Every rate, cookie window and app-eligibility rule in section 3 (several sources conflict: Klook, Headout, Musement, iVisa cookie, Radical Storage, Vrbo, Saily).
6. Apple: confirm in review notes that a first-party redirect with a random per-click id needs no ATT prompt; confirm the reading of 3.1.3(e) for eSIM.
7. Legal review of disclosure wording (US, UK, EU) and of insurance referral rules by state and by launch country.
8. Real cancellation and reversal rates by program (this plan uses 10 to 25%).
9. Airbnb: any change to creator or demand programs (reported "not accepting applications").
10. ETIAS timing, and the Epic v. Apple outcome (effects on web checkout for Plus and Trip Pass only).
11. Replace every attach rate and order value in this file with real click and conversion data by month 3.

## 13. Higher-commission lanes

Affiliate links pay $8 to $25 per completed booking. The lanes below pay 5 to 20 times that per booking, but each one brings a licence question, human labor or merchant duties, so none is a launch item. Evidence caveat: host-agency, bedbank and block figures come from search summaries (Fora's own site, Forbes and valueaddvc were blocked), so every number is "reported, verify". Per-trip figures are estimates from stated assumptions. The revenue math and scenarios are in [09-revenue-expansion.md](09-revenue-expansion.md) sections 3.1 to 3.3 and 6.4.

| Lane | Net per booking | Attach (share of trips) | Per real trip | Effort | Regulatory burden | Hurts UX? |
|---|---|---|---|---|---|---|
| Concierge via host agency | Hotel $600 stay: $40 to $70. Cruise $3,000: $200 to $380. Package $2,500: $150 to $300 | 2 to 4% opt in | $2 to $6 | Low build, 30 to 60 minutes of founder time per booking | Medium: seller-of-travel registration in some states, host cover, E&O | No, if optional and perks are real |
| Group room blocks and organizer tools | 30-room, 2-night block at $200: about $1,200 at 10%; $1 to $3 per traveler for collection | 0.3 to 1% of trips | $1.50 to $8 | Medium | Medium to high if Hermi holds money; low if the hotel collects | No, free blocks help organizers |
| In-app hotel booking (LiteAPI) | Margin 5 to 15% of $600 = $30 to $90 gross; $15 to $60 after card fees, refunds, support | 3 to 5% | $0.50 to $3 | High | Medium to high: merchant duties, consumer law, probably seller-of-travel | Mixed: smoother checkout, more support, less "we send you to the real site" |
| Expedia TAAP under host credentials | Up to 13% hotels, 11.5% flights and activities, 7.5% cars, 6% packages | Part of the concierge lane | Inside the concierge figure | None beyond the concierge lane | Needs IATA, ARC, CLIA or TRUE, so only through a host | No |

### 13.1 Why these and not the others

Per trip the top three lanes stack to about $4 to $17 against $1.04 today. Skipped in years 1 to 3: flights as merchant (Duffel; net $5 to $25 per ticket, high tail risk), Expedia Rapid and Hotelbeds or WebBeds direct (partner-only, not solo work), credit cards (section 4.3), event tickets (StubHub 4%, SeatGeek 1%, Ticketmaster $0.30; under $0.30 per trip), and airport parking. Travel insurance stays a referral (section 7.5); a limited-lines licence would lift it from $8 to $25 to perhaps $20 to $60 but adds exams and conduct limits.

### 13.2 Concierge via a host agency

How it works (reported): suppliers pay travel agencies 7 to 20% per booking, typically 30 to 90 days after travel, and a host agency passes on a split. The advisor is an independent contractor under the host's IATA, ARC, CLIA or TRUE credentials and E&O cover. The founder joins a host as an advisor; Hermi gets an optional "Have a human book this" button on shortlisted stays, cruises and complex trips. The user fills a brief and the founder books in the host's portal.

| Host | Reported split and fees | Notes |
|---|---|---|
| Fora | 70/30 to start, 80/20 at $300,000 of annual sales, 90/10 at $2M. $299 a year or $99 a quarter. Average 12% per booking reported. 15,000+ advisors, $1B valuation July 2026 (reported) | Fora Reserve has 5,000+ preferred partners (Virtuoso properties, Four Seasons, Rosewood Elite). Portal covers booking, proposals, commission tracking. No partner or API program found; ask by email. |
| Outside Agents | 80% rising to 90 or 95%; about $199 to start, $26 to $46 a month | Large and cheap |
| KHM Travel Group | 80%, 90% after $5,000 of paid commission in a year | |
| Avoya | About 80% on own clients, about 30% on leads it supplies; Elite 100 at $399 a month gives 100% | Lead-gen model |
| Gifted Travel Network, Nexion | 80/20 to 90/10 and 70 to 100%; $0 to $50 and $0 to $200+ a month | Not researched in detail |
| Cruise.com host program | Up to 100% split from $75 a month | Cruise-only option |

Economics under Fora's 70/30: a $600 Virtuoso stay at 10% pays the agency $60 and Hermi $42; a $3,000 cruise at 10 to 16% pays the agency $300 to $480 and Hermi $210 to $340 at 70%. Cruise lines pay 10 to 16% (Royal Caribbean 10% at 0 to 24 passengers up to 16% at 250+), river cruises 15 to 20%, shore excursions 8 to 12%; the affiliate route (CruiseDirect, 3%, $60 to $100) pays less.

Perks (reported): Virtuoso properties give daily breakfast, a property credit (for example $100 at Fairmont), possible upgrade and early check-in or late checkout, at the same or better rate than the hotel's flexible rate, with the hotel paying the advisor. Virtuoso is bookable only through a Virtuoso-affiliated advisor. This is why the lane does not hurt the UX: the user gets more and pays the same.

Credentials and costs (reported): ARC application $2,300 plus $228 a year per location, TRUE $399 the first year, then $240; hosts let advisors ride on their numbers. E&O $400 to $1,200 a year solo at $1M per claim; get separate cover if using an LLC or passing $500,000 a year.

Seller-of-travel registration (reported, verify): California $100 per location, filed 10 days before selling, with the number shown in ads; Florida $50 a year for independent agents (business categories $300 to $2,500); Washington $50 plus a $222 annual licence; Hawaii $146 or $215 and a trust account. Exemptions vary. Counsel confirms whether an app that only forwards a request to a human advisor is outside the rules (inference: referral only usually is; selling is not).

Two hard limits (inference). Host contracts are between the agency and a named advisor, and supplier portals expect a human, so automated or mass booking by the app under host credentials would probably breach terms. The workable model is human in the loop: the app collects a brief and the founder, or a hired advisor, books. Capacity is about 300 bookings a year solo.

Rules that keep it from degrading the planner: it is an opt-in button, never reorders results, discloses that the hotel pays Hermi, shows the perk list beside the price, and is not gated behind a paid tier.

### 13.3 Group room blocks

- Groups360 says it is free to planners, lets planners request commissionable rates on RFP bookings, offers instant booking for 10 to 25 rooms, and connects 200,000+ properties (reported). Group hotel commission is typically up to 10% (reported generally; the Groups360 figure was not confirmed, verify). A 30-room, 2-night wedding block at $200 is $12,000 of room revenue and $600 to $1,200 of commission.
- Whether an app can be the payee is unknown (often only registered planners or agencies are paid). Verify with Groups360 and Hotel Planner before counting it. The concierge host agency may be the route.
- Attrition risk: unsold block rooms can be charged. Hermi never signs a contract for users. Use the hotel's own reservation-link blocks, which carry no liability for the organizer.
- Organizer payment collection: Tern uses per-traveler sub-trips, Lambus has expense splitting, Troupe charges the organizer $3.99 a month or $29.99 once (reported, verify). Hermi uses Stripe Connect with the organizer as the connected account so it never holds funds; a fee of 1.5% of amounts collected (about $1 to $3 a traveler on a typical trip), shown before charging. Interchange income is nil unless Hermi issues cards, which is out of scope. Legal review first.

### 13.4 In-app hotel booking through LiteAPI (year 2 and later)

LiteAPI (Nuitee) is the only bedbank a solo builder can realistically integrate: public REST API, 2M+ hotels, self-serve, no stated minimum, margin set per search, weekly payouts for confirmed bookings, and a choice between Nuitee as merchant of record through its payment SDK or Hermi as merchant of record on net rates (reported, verify). Hermi would use Nuitee as merchant of record to stay out of card-data scope. Margins are constrained by rate parity (inference: bedbank rates are often priced to match public prices), so the usable margin is probably the low end, and net after card fees, chargebacks, cancellations and support is about half of gross. Other providers: RateHawk (business approval needed), Hotelbeds (adds 15 to 22% to hotel net, commercial approval, Hermi as merchant) and WebBeds (no public API) are not solo options. Build only after click data shows strong booking intent, a support process for "I arrived and there is no booking" exists, and counsel has confirmed the registration position.

### 13.5 Expedia TAAP with host credentials

The Expedia Travel Agent Affiliate Program pays up to 13% on hotels, 11.5% on flights and activities, 7.5% on cars and 6% on packages, in tiers by gross bookings (Platinum at $500,000+). It is free with no minimum sales but requires IATA, ARC, CLIA or TRUE credentials (reported, verify). Hermi has none of its own, so the only fit is the founder booking manually as a host-agency advisor, which is part of the concierge lane. It does not replace the Expedia Group affiliate application of section 4.2 and it is not a way to link users straight to a TAAP link. Expedia Rapid stays skipped (section 4.3).

### 13.6 Cashback rules and why Hermi does not share commission as cash

What programs say (reported, verify in each agreement): Booking.com requires its approval before promoting cashback to users; Expedia Group allows loyalty and cashback case by case with rules against unapproved voucher codes; other programs either prohibit cashback partners, allow them at a reduced tier or treat them as a separate segment. Viator, Travelpayouts and Stay22 terms were not found.

Hermi does not pay users a share of commission as cash or cash-like credit, for these reasons:

1. A credit that varies by partner creates a payout-based ranking incentive, which breaks the rule in section 7.7. One flat rate would fix that but not the rest.
2. Stored credit has gift-card, breakage and unclaimed-property rules, and insurance rebating is restricted in many states.
3. Programs can treat self-purchase and incentivized traffic as a violation, and several require approval first.
4. A reward for booking through an outside link connects outside purchases to app value, and section 7.1 says affiliate purchases never unlock app features. Apple guideline 3.1.1 adds risk if credit buys app features; confirm the current text before any test.
5. It halves revenue on the trips where it applies, and adds accounting work.

A compliant variant exists only as a test: a "trip fund" showing "You earned $12 toward your next trip", on one partner that has approved it in writing (email Booking.com or Stay22 first), with one flat rate and insurance excluded. Until a partner approves and Apple's text is confirmed, the answer is no.

### 13.7 Other commission sources considered

| Source | Reported | Verdict |
|---|---|---|
| Viator merchant API | Suppliers pay Viator 20 to 30%; affiliates get about 8% of the sale; the merchant route (markup or commission model) could roughly double or triple the take (inference). Needs certification | Later, after affiliate volume exists; dynamic packaging skipped |
| point.me affiliate | Commission on subscriptions, rate not found (verify) | A small, honest tip inside the flight screen at most ($10 to $30 a subscription) |
| Travel insurance licence | Commission 20 to 40% reported; limited-lines fees NC $100 plus $50, MD $54, MS $200, WA $20, CT $750, CA $4,540 for two years | Stay on referral in years 1 to 3 |
| Vacation rental management referral | Not researched; managers often pay 5 to 10% (verify) | Low volume |
| Sports travel packages | Usually sold by specialist agencies | A possible concierge niche |

### 13.8 What the stacked upside depends on

| | Affiliate links only | With the lanes |
|---|---|---|
| Revenue per real trip, base case | $1.04 (after attribution loss, lodging about 60%) | About $4 to $17 (concierge $2 to $6, groups $1.50 to $8, LiteAPI $0.50 to $3) |

The range depends on:

1. Founder hours. Concierge is capped at about 300 bookings a year solo (30 to 60 minutes each). Above that, contracted advisors keep half of the net. At the base case of 60,000 MAU in year 3 the capped lane earns about $27k, or $0.75 per trip, not $2 to $6.
2. Attach rates that are assumptions: 2 to 4% of trips opt into concierge, 0.3 to 1% are group events with a block, 3 to 5% book in app.
3. Payee and licence rules that are unverified: whether host agencies allow app-routed leads, whether an app can be paid a room-block commission, and whether forwarding a request needs seller-of-travel registration.
4. LiteAPI margin after rate parity. Each in-app booking also replaces an affiliate commission of about $10 on the same stay, so the incremental figure in 09 is $20 a booking, not $30.
5. A support process. Lanes 1 and 3 move blame for hotel problems onto Hermi.

Treat the range as a set of tests, not a forecast. The measure that matters first is the concierge ask rate and commission per booking in months 1 to 12.

### 13.9 Open items to verify for the lanes

1. Whether Fora, Outside Agents and KHM allow app-routed leads or automated booking.
2. Whether Groups360 or Hotel Planner pay non-agency planners, and the percentage.
3. Whether seller-of-travel registration applies when the app only forwards a booking request.
4. LiteAPI margin caps, rate-parity rules, payout currencies and minimums.
5. Viator merchant API certification requirements and timeline.
6. Cashback and incentive clauses in Travelpayouts, Stay22, Viator and Expedia agreements.
7. Travel Planners International, Duffel Stays and Travelfusion terms (not researched).

## Sources

All checked 2026-09-30, mostly through search summaries. Direct fetches of the official partner pages were blocked. Rates and terms are "reported, verify".

Rules and compliance:
- Apple guidelines: https://developer.apple.com/app-store/review/guidelines/ ; ATT and tracking: https://developer.apple.com/app-store/user-privacy-and-data-use/
- FTC endorsement guides: https://www.ftc.gov/business-guidance/resources/ftcs-endorsement-guides-what-people-are-asking ; https://www.federalregister.gov/documents/2023/07/26/2023-14795/guides-concerning-the-use-of-endorsements-and-testimonials-in-advertising
- UK: https://www.asa.org.uk/advice-online/affiliate-marketing.html ; EU Omnibus: https://www.webgains.com/public/en/the-omnibus-directive-affiliate-marketing/
- In-app browser cookies: https://developer.okta.com/blog/2022/01/13/mobile-sso ; https://developer.apple.com/forums/thread/78928
- Epic v. Apple: https://www.scotusblog.com/cases/apple-inc-v-epic-games-inc-2/
- Insurance: https://www.wvinsurance.gov/Portals/0/pdf/webforms-licensing/Travel%20Insurance%20Business%20Entity%20FAQs%2010.2025.pdf ; https://eur-lex.europa.eu/eli/dir/2016/97/oj ; https://www.worldnomads.com/partnerships/affiliates/content-guidelines
- Visas: https://ivisatravel.com/affiliate-terms-and-conditions ; https://www.visahq.com/partnership.php

Lodging:
- Airbnb: https://www.airbnb.com/help/article/4236 ; https://www.airbnb.com/refer ; https://track360.io/blog/airbnb-vacation-rental-affiliate-referral-programs-operator-teardown-2026 ; https://www.makeinfluence.com/en/academy/airbnbs-creator-program-how-it-differs-from-an-open-affiliate-program
- Expedia and Vrbo: https://getlasso.co/affiliate/expedia/ ; https://uppromote.com/affiliate-program-directory/vrbo/ ; https://developers.expediagroup.com/rapid/setup/launch-requirements/b2c-standalone?locale=en_US
- Booking.com: https://www.awin.com/us/advertisers/partner/booking.com ; https://www.netinfluencer.com/booking-com-moves-all-affiliates-to-awin-what-to-know-about-termination-notices/ ; https://mize.tech/blog/all-about-the-booking-com-affiliate-partner-program-for-travel-agents/
- Stay22: https://www.stay22.com/faq ; https://dev.stay22.com/docs/api ; https://thetraveltinker.com/resources/stay22-review/
- Travelpayouts hotels: https://www.travelpayouts.com/blog/best-hotel-affiliate-program/ ; Agoda: https://getlasso.co/affiliate/agoda/ ; HomeToGo: https://www.hometogo.com/legal/

Transport:
- Flights: https://www.travelpayouts.com/en/offers/aviasales-affiliate-program/ ; https://www.travelpayouts.com/en/offers/kiwi-affiliate-program/ ; https://support.travelpayouts.com/hc/en-us/articles/210995808-Requirements-for-Aviasales-Flight-Search-API-access ; https://www.partners.skyscanner.net/product/affiliates ; https://howtojoinaffiliateprograms.com/kayak-affiliate-program/
- Cars: https://www.travelpayouts.com/blog/car-rental-affiliate-programs/ ; https://www.localrent.com/en/partners/rules/ ; https://www.qeeq.com/affiliate-program
- Trains and buses: https://www.travelpayouts.com/blog/train-affiliate-programs/ ; https://www.thetrainline.com/about-us/partnerships/affiliates ; https://agent.12go.asia/
- Transfers: https://aff.travel/welcomepickups.html ; https://kiwitaxi.agency/page3348005.html ; https://www.uber.com/us/en/affiliate-program/
- Compensation: https://www.airhelp.com/en/affiliate/ ; https://aff.travel/compensair.html ; https://skyrefund.com/en/affiliate

Extras:
- Tours: https://getlasso.co/affiliate/viator/ ; https://partnerresources.viator.com/travel-commerce/levels-of-access/ ; https://partner.getyourguide.support/hc/en-us/articles/13981068165917-Our-partner-program ; https://www.travelpayouts.com/en/offers/tiqets-affiliate-program ; https://www.travelpayouts.com/en/offers/go-city-card-affiliate-program ; https://getlasso.co/affiliate/klook/
- Restaurants: https://uppromote.com/affiliate-directory/opentable/ ; https://affi.io/m/thefork
- eSIM: https://developers.partners.airalo.com/introduction-752814m0 ; https://saily.com/affiliate/ ; https://esim.holafly.com/affiliate-program/
- Insurance: https://getlasso.co/affiliate/world-nomads/ ; https://www.travelpayouts.com/blog/the-visitorscoverage-affiliate-program/ ; https://www.travelpayouts.com/blog/earn-money-on-travel-insurance-worldwide-with-ekta/ ; https://yazing.com/affiliate-programs/heymondo-affiliate-program
- Money and cards: https://wecantrack.com/programs/wise-affiliate-program/ ; https://uppromote.com/affiliate-directory/revolut/ ; https://wecantrack.com/insights/credit-card-affiliate-programs/
- Amazon: https://affiliate-program.amazon.com/help/operating/participation/ ; https://www.getchatads.com/blog/amazon-associates-operating-agreement-ai-apps/
- Others: https://www.travelpayouts.com/en/offers/radical-storage-affiliate-program/ ; https://bounce.com/ls/affiliates ; https://www.flytographer.com/partner-with-flytographer/affiliates/

Networks and benchmarks:
- Travelpayouts support: https://support.travelpayouts.com/hc/en-us/articles/203955653-ID-and-SubID-Affiliate-marker-and-additional-marker ; https://support.travelpayouts.com/hc/en-us/articles/360019864079-API-of-affiliate-programs-booking-statistics ; https://support.travelpayouts.com/hc/en-us/articles/203956053-Travelpayouts-Affiliate-Agreement-The-public-offer
- Networks: https://xark.io/resources/affiliate-network-comparison-impact-cj-partnerize-2026 ; https://affiliate-times.com/cj-affiliates-340m-merger-with-partnerize-reshapes-enterprise-cpa-landscape/
- Benchmarks: https://track360.io/blog/best-travel-affiliate-programs-2026-operator-rate-card-benchmark ; https://foundrycro.com/blog/travel-hospitality-marketing-benchmarks-2026/

Higher-commission lanes (section 13; search summaries, reported, verify):
- Host agencies: https://www.foratravel.com/join/resources/travel-agent-commission ; https://www.foratravel.com/join/resources/fora-vs-outside-agents ; https://www.squadtrip.com/guides/what-is-a-host-travel-agency-pros-cons-top-picks/ ; https://travedeus.com/blog/marketing/outside-agents-vs-avoya-travel ; https://www.cruise.com/host-agency/earn-more/ ; https://mainstreetagencytravel.com/news/royal-caribbean-commission-rates-2026-guide
- Credentials, registration and insurance: https://www.altexsoft.com/blog/travel-agency-accreditation/ ; https://www.foratravel.com/join/resources/travel-agent-insurance ; https://startpermit.com/blog/how-to-start-a-travel-agency/ ; https://www.ncdoi.gov/documents/agent-services/referral-fees-faqs/open
- Perks programs and Expedia TAAP: https://onemileatatime.com/guides/virtuoso-hotels-travel-agent/ ; https://travedeus.com/blog/marketing/what-is-expedia-taap
- Bedbanks: https://docs.liteapi.travel/docs/revenue-management-and-commission ; https://docs.liteapi.travel/docs/implementing-payment ; https://www.zentrumhub.com/blog/best-hotel-api-providers/
- Groups: https://groups360.com/blog/event-planner-hotel-commissions-guide/ ; https://help.tern.travel/en/articles/10059452-a-guide-to-group-trip-functionality
- Cashback: https://affiliates.support.booking.com/kb/s/article/Partner-Affiliate-Agreement ; https://getreditus.com/resources/glossary/cashback-affiliate
