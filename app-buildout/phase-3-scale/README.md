# Phase 3: scale (year 2 and later)

Part of the [Hermi build specification](../README.md). Written 2026-09-30.

Phase 1 is the launch app ([phase-1-launch/](../phase-1-launch/README.md)). Phase 2 adds growth features ([phase-2-growth/](../phase-2-growth/README.md)). Phase 3 is seven self-contained feature packs, added one at a time, that aim at the people who plan trips for other people (advisors, group and event organizers, destination boards, agencies) and at higher-value lanes (printed books, hotel booking, card offers). Each pack says exactly what it adds to the Phase 1 database, API, screens, billing and admin, so it can be built without rereading everything.

Scope is final: a feature is in Phase 3 because the "Not in Phase 1" table in the [Phase 1 README](../phase-1-launch/README.md) says so (Stripe group payments, Hermi for Advisors, partner guides, printed trip books, in-app hotel booking, white-label and API, card and loyalty offers). The revenue numbers come from [09-revenue-expansion.md](../context/business-plan/09-revenue-expansion.md) and the affiliate lanes from [08-affiliate-revenue.md](../context/business-plan/08-affiliate-revenue.md).

**Naming.** The Phase 1 spec files call this work "year 2 and later" or "Phase 4" (tickets WF-101 to WF-113 in the full [09-build-roadmap.md](../reference-full-spec/09-build-roadmap.md), listed as moved in [Phase 1 section 7](../phase-1-launch/09-build-roadmap.md)). In this folder it is Phase 3, tickets are `P3-001` onward, and the pack files list which WF ticket each one replaces.

**Links.** Links to `../phase-1-launch/` point at the Phase 1 edition of each spec, which is trimmed to Phase 1 and numbers some sections differently. Section citations that exist only in the full specs (the files in `../`, for example the DDL in full 03 section 5.17 or the payments rules in full 07 section 10) link there and are marked "full spec". Links to `../phase-2-growth/` point at the Phase 2 packs; the Phase 2 README was not yet written when this folder was.

## Packs

| Pack | What | Base Y5 revenue (09) | Build effort | Needs | Tickets |
|---|---|---|---|---|---|
| [01 Stripe group payments](01-stripe-group-payments.md) | Stripe Connect collection for group trips, plus the $79 events workspace | $56.3k ($38.3k events, $18.0k payments) | about 12 weeks | Lawyer first, support contractor | P3-001 to P3-014 |
| [02 Hermi for Advisors](02-hermi-for-advisors.md) | Web SaaS: seats, client workspaces, branded presentations, proposals, commission tracking, Stripe billing | $141.4k (450 seats) | about 16 weeks | 15 interviews, light legal, support contractor at about 100 seats | P3-015 to P3-034 |
| [03 Partner guides](03-partner-guides.md) | Labeled sponsored destination guides, review workflow, sponsor reports | $36.0k (6 deals at $6,000) | about 6 weeks plus sales | Sales time, light legal | P3-035 to P3-044 |
| [04 Printed trip books](04-printed-trip-books.md) | Print-on-demand book and poster from presentation mode | $31.2k contribution | about 10 weeks | Real vendor quotes, accountant | P3-045 to P3-057 |
| [05 In-app hotel booking](05-in-app-hotel-booking.md) | LiteAPI with Nuitee as merchant of record | $72.0k, **upside, not in totals** | about 13 weeks | Lawyer first, support hire, contractor engineer | P3-058 to P3-070 |
| [06 White-label and API](06-white-label-and-api.md) | Branded client pages, custom domains, API keys, account contracts | $36.0k (6 accounts at $6,000) | about 10 weeks | Pack 02 stable, lawyer, onboarding support | P3-071 to P3-081 |
| [07 Card and loyalty offers](07-card-and-loyalty-offers.md) | Labeled card and loyalty offers in one checklist item | Not modeled; $50k to $150k potential at 100k MAU | about 6 weeks | Counsel retainer, network and issuer approval, compliance owner | P3-082 to P3-091 |

Base year 5 revenue for the lines that are in the 09 totals (packs 01, 02, 03, 04, 06) is about $301k, out of $572.5k in total. Pack 05 is the $72.0k of upside that 09 keeps out of its totals, because neither it nor the concierge lane (Phase 2) is tested. Pack 07 is not modeled at all. Build effort is the sum of ticket sizes (below) for one developer working with Claude Code, and includes the non-engineering tickets (legal, interviews, sales).

## Entry criteria

Do not start Phase 3 because the calendar says year 2. Start it when the business can carry it.

### Gate for all of Phase 3

| Area | Criterion |
|---|---|
| Product | Phase 1 live for at least 6 months; the Phase 2 packs that Phase 3 builds on are shipped (Group Trip Pass with polls and cost splitting, room-block request, concierge lane, direct affiliate programs, memories); no open severity-1 bug; crash-free sessions above 99.5% |
| Users | At least 20k MAU sustained for a quarter (base case year 2 average). The affiliate income per MAU and paid conversion are measured, not assumed (09 section 9 items 3 and 4) |
| Revenue | At least $3k a month of net revenue, about a $35k annual run rate (base case year 2 is $34.7k), contribution positive after AI and infrastructure cost |
| Team | The founder plus a support contractor (support is 5 to 10 hours a week from about 5,000 MAU, 09 section 8). Nothing in Phase 3 should be started by a founder who is also the only person answering support |
| Runway | 12 months of personal and business runway without counting on any Phase 3 revenue |
| Legal | A lawyer engaged for the packs marked below, with a retainer or a quote per pack |

These are proposals, not facts from the plan; 09 supplies the ceilings and the MAU and revenue figures, and the thresholds above are chosen to be consistent with them. Tune them in the decision record that opens each pack's ticket list.

### Gate per pack

| Pack | Start when | Source |
|---|---|---|
| 02 Advisors | 15 advisor interviews done, price test run, 5 design partners signed, about 20k MAU so the workspace code is proven by real use | 09 sections 3.4, 9 item 1 |
| 04 Print | About 20k MAU, photo store exists (Phase 2 memories or P3-046), real print quotes in hand | 09 section 3.6 |
| 03 Partner guides | Pilot (one free destination) when destination pages have traffic; first paid deal at about 50k MAU with measured copies and saves | 09 section 3.5 |
| 01 Group payments and events | Counsel memo in writing (P3-001); Group Trip Pass already sells; build time starts after the memo, not before | 09 sections 3.2, 9 item 8 |
| 06 White-label | Advisor product live at least 6 months with 40 paid seats and 3 qualified inbound requests | 09 section 3.7 (pack 06 section 1) |
| 05 LiteAPI | Click data shows booking intent, a support process exists, counsel confirms the registration position, sandbox confirms margin and parity | 09 section 3.3, 08 section 13.4 |
| 07 Card offers | About 100k MAU, low-end economics cover 3 times the first-year cost, a network accepts the app, counsel written advice, trust metrics stable | 09 section 3.8 |

### Team size and revenue (from 09 sections 7 and 8)

A solo founder tops out around $150k to $250k a year, which is roughly 60k to 100k MAU and 100 to 200 advisor seats (60k MAU x $1.71 = $103k, plus 100 seats x $314 = $31k, plus about $15k of partner, print and group income is about $150k). Beyond that the work is support, sales and compliance.

| Annual revenue | Realistic team | What Phase 3 adds to the load |
|---|---|---|
| Up to about $50k | Solo, part time | Nothing from Phase 3 yet |
| $50k to $150k | Solo full time plus a support contractor | Advisor pilot, print, partner guide pilot; about 10 support hours a week per 100 advisor seats |
| $150k to $250k | Solo at the limit | Partner sales and payments compliance now compete with building; stop adding packs here |
| $250k to $500k | 2 to 3 people: engineer, support and advisor success, part-time sales | Packs 01, 03, 05, 06 become feasible; reinvest profit, no funding strictly needed if margins hold |
| $500k to $1M | 4 to 6 people, possibly funded | Payments legal, partner sales, print operations, hotel support, moderation |
| Above $1M | Funded team | Apple's 30% tier may apply above $1M of proceeds (none of the packs sells through Apple except as Phase 1 does) |

## Order of the packs

The pack numbers are identifiers, not a schedule. Two views decide the order.

### By expected revenue and effort

| Rank by base Y5 revenue | Pack | Y5 base | Effort (weeks) | Y5 revenue per week of effort | Confidence (09 section 6.5) |
|---|---|---|---|---|---|
| 1 | 02 Advisors | $141.4k | 16 | $9.1k | Low to medium |
| 2 | 05 LiteAPI (upside) | $72.0k | 13 | $5.7k | Untested, left out of totals |
| 3 | 01 Payments and events | $56.3k | 12 | $4.9k | Low |
| 4 (tie) | 03 Partner guides | $36.0k | 6 | $5.6k | Low |
| 4 (tie) | 06 White-label | $36.0k | 10 | $3.7k | Low |
| 6 | 04 Print | $31.2k | 10 | $3.1k | Medium |
| n/a | 07 Cards | $50k low end at 100k MAU (not modeled) | 6 | about $8.9k at the low end | Not modeled |

### Recommended build sequence

1. **Start the long-lead non-engineering work at once, in parallel:** the advisor interviews (P3-015), the vendor quotes for print (P3-045), the counsel memo for payments (P3-001), the partner-guide rate card and contract (P3-035). None needs code and each has a lead time.
2. **02 Advisors.** Largest line and the foundation for pack 06. Build once the interviews and design partners exist.
3. **04 Print.** Small, self-contained, no legal gate, and a good change of pace from the advisor work. Interleave it while the advisor pilot runs, or build it first if the interviews are not finished.
4. **03 Partner guides.** The engineering is light; run the free pilot as soon as destination pages have traffic so the case study exists when the audience reaches about 50k MAU.
5. **01 Group payments and events.** Only after the counsel memo. The events workspace can ship without collection if the memo says collection is not allowed.
6. **06 White-label.** Only after pack 02 has run for 6 months.
7. **05 LiteAPI.** Only after the go or no-go memo; the highest support burden per dollar.
8. **07 Card offers.** Last, at about 100k MAU, when the decision record says it is worth it.

This matches the start years in 09 section 1: print, advisor build and the partner pilot in year 2; payments and events, white-label and the LiteAPI build in year 3; cards at about 100k MAU.

## Who needs a hire, a lawyer or funding

| Pack | Hire | Lawyer | Funding | Other |
|---|---|---|---|---|
| 01 Payments and events | Support contractor for refunds and disputes | Yes, **before any build**: money transmission, charge type and liability, terms, tax, sanctions | No | Accountant for reconciliation; a platform reserve for disputes (size with counsel) |
| 02 Advisors | Support and advisor-success contractor at about 100 seats (about $20.8k a year at an assumed $40 an hour, paid from seat revenue) | Light: terms, data-processing addendum, SaaS tax | No | Accountant for sales tax on SaaS |
| 03 Partner guides | Part-time sales help becomes useful after about 6 deals a year (90 to 150 pitches) | Light: one-page sponsorship contract and disclosure terms | No | Founder sales time is the real cost |
| 04 Print | No | No | No | Accountant for sales tax on physical goods; Stripe Tax does the calculation |
| 05 LiteAPI | Yes: a support person before opening to everyone; contractor engineer advised | Yes, before launch: seller-of-travel and consumer law, supplier terms | No while Nuitee is merchant of record; yes (working capital and licences) if Hermi ever becomes merchant | Emergency contact path for stays within 24 hours |
| 06 White-label | Onboarding and support person (per-account support is the real cost) | Yes: master agreement, DPA, child-data rules before any school operator | No | External security review before the first customer |
| 07 Cards | Compliance owner (part of the founder's time at first) | Yes, on retainer; per-offer copy review | No | Specialist publisher network and issuer approvals |

Nothing in Phase 3 strictly needs outside funding if the gates above are respected. The plan's $500k to $1M band (09 section 8) is where a funded team becomes likely, because each $100k of advisor revenue brings about 300 seats to support.

## Dependencies between packs

- **Pack 06 needs pack 02** (same tenancy and code). **Pack 01's events workspace** reuses the pass machinery from Phase 2's Group Trip Pass. **Pack 05** is unrelated code but reuses the stay comparison and the affiliate disclosure from Phase 1 and the direct programs from Phase 2. **Pack 03** and **pack 07** reuse the affiliate redirect, disclosure component and admin console. **Pack 04** needs photos (Phase 2 memories or P3-046).
- **Shared rule for selling:** advisors, white-label, the events workspace and print are sold on the web through Stripe. The iOS app never sells them and never links to their purchase pages (Apple 3.1.1; 3.1.3(e) covers the physical and real-world goods: print, payments, hotels). Re-read the current Apple text on each submission ([09 risk 7](../context/business-plan/09-revenue-expansion.md)).
- **Migration order.** Each pack's DDL is a separate Alembic revision added after the last Phase 2 revision, following [03 section 10](../phase-1-launch/03-database-schema.md): a table added after the RLS revision carries its own grants and policies in the same migration. Phase 1 dropped the tables that belong to these packs (Phase 1 03 section 1.1), and Phase 2 creates only `polls`, `expenses`, `settlements`, `room_block_requests`, `concierge_requests` and their neighbors. Each pack's section 4.1 states what exists after Phase 2 and gives the definitions from the full 03, which it creates; the table names match Phase 1 03 section 14.

### Flags and kill switches

| Flag | Where it is created | Pack |
|---|---|---|
| `group_payments` | created off by Phase 2 | 01 |
| `event_workspaces` | created by the pack | 01 |
| `advisor_workspaces` | created by the pack | 02 (also gates 06) |
| `partner_guides` | created by the pack | 03 |
| `print_orders` | created by the pack | 04 |
| `inapp_hotel_booking` | created by the pack | 05 |
| `white_label`, `partner_api` | created by the pack | 06 |
| `card_offers`, `loyalty_offers` | created by the pack | 07 |

New kill switches: `group_payments.collect` (01), `advisors.billing` (02), `provider.printer` (04), `provider.liteapi` (05), `white_label.domains` and `provider.api` (06), `card_offers` (07). Existing or assumed: `provider.stripe` (create it in pack 01 if Phase 1 did not seed it), `affiliate.<code>` (one per program).

### New or extended tables

| Pack | Tables |
|---|---|
| 01 | `payment_collections`, `payment_disputes`; columns on `settlements` and `users`; plan `event_workspace` |
| 02 | `advisor_orgs`, `advisor_seats`, `advisor_clients` (from full 03), `advisor_subscriptions`, `advisor_notes`, `advisor_proposals`, `advisor_bookings`, `advisor_templates`; `concierge_requests.advisor_org_id`; plan `advisor_seat`; seat status `read_only` |
| 03 | `partner_guides` (from full 03), `partner_guide_versions`, `guide_metrics_daily`, `sponsor_reports`; `itinerary_items.source` value `guide` |
| 04 | `print_orders` (from full 03), `print_products`, `print_order_events`, `trip_photos` (if Phase 2 memories did not add one) |
| 05 | `hotel_bookings`, `hotel_booking_events`; `lodging_options.hotel_booking_id`; `lodging_options.added_via` value `liteapi` |
| 06 | `white_label_contracts`, `org_domains`, `api_clients`, `api_keys`, `api_usage_daily`; `advisor_orgs.kind` |
| 07 | `card_offers`, `card_offer_reviews`, `loyalty_accounts`; `affiliate_programs.category` value `cards`; `consents.kind` value `offers` |

### Environment variables (document each in `.env.example`; values only in `.env`)

Expected names, added by each pack's infrastructure ticket: `STRIPE_CONNECT_WEBHOOK_SECRET` (01), `STRIPE_ADVISOR_PRICE_ID` and an annual equivalent (02, already in 02-architecture.md for the monthly price), `PRINTER_API_KEY` and `PRINTER_WEBHOOK_SECRET` (04), `LITEAPI_KEY` (05, already listed empty in 02-architecture.md) and `LITEAPI_WEBHOOK_SECRET`, `CLOUDFLARE_SAAS_API_TOKEN` and the zone id (06), `CARDS_NETWORK_TOKEN` (07).

## How each pack is laid out

Every pack file has the same sections: goal and revenue case (with the 09 numbers and the worked arithmetic), design decisions, user stories with acceptance criteria, database additions (first the definitions reused verbatim from [03 (full spec)](../reference-full-spec/03-database-schema.md), then the new DDL), API additions, UI screens, billing, admin additions, legal and compliance, analytics, tests, tickets and risks.

### Ticket conventions

- IDs run `P3-001` to `P3-091` across the packs in file order; each pack states its range. Pack files say which Phase 1 roadmap ticket (WF-102 to WF-110) they replace.
- Sizes are larger than the Phase 1 roadmap's (there S is 2 hours, L a day). Here S is about 1 day, M about 3 days and L about 1 week for one developer working with Claude Code, including review and tests. These are work packages: when one is scheduled, split it into Phase 1 style one-day tickets. The calibration is that pack 02 adds up to about 16 weeks, which matches 09's "3 to 4 months for one person" for the advisor product.
- Each ticket names what it needs, and "Who" marks the ones that are not engineering (lawyer, founder, bookkeeper, support).
- The Definition of Done from [09-build-roadmap.md section 6](../phase-1-launch/09-build-roadmap.md) applies to every ticket: pull request per ticket, `npm run lint` and `npm test` pass, `npm run gen:api` after any route or schema change, migrations follow the project's database rules, new variables in `.env.example`, UI copy rules (sentence case, no em dashes), and the non-negotiable rules.

## Not in Phase 3

- **Phase 2 items:** Family plan, Group Trip Pass, polls, the concierge lane, direct affiliate programs, Pro, Android, email-forward import, flight alerts, memories (see the Phase 1 README table).
- **Creator paid guides** ($2.7k in year 5): an acquisition tool, not a revenue line (09 section 3.6).
- **Deferred or poor fits in years 1 to 3** (09 section 3.9): flights as merchant (Duffel), Expedia Rapid, Hotelbeds and WebBeds direct, the Viator merchant API, and an insurance licence. Revisit only after the packs above have data.
- **Rejected** (09 section 4): selling user data, banner ads, cashback or commission-driven rankings, lifetime plans, hard paywall.

## Source notes: discrepancies found while writing the packs

Resolve these before the affected pack starts; each is also marked in the pack.

1. **Payments revenue per MAU** (pack 01): 09 says the stated inputs give $0.09; they multiply to $0.18. The model's $0.08 and $0.12 are below both, so totals stand, but use measured volume before planning on it.
2. **Destination charges and liability** (pack 01): 07 section 10.2 says Hermi never holds traveler money and the organizer handles disputes, but under Stripe's documented model destination charges leave refunds and chargebacks with the platform. Counsel and Stripe decide between destination and direct charges.
3. **Advisor seat allowance** (pack 02): 03 seeds 150 credits and a $3.40 ceiling per seat (86% worst-case margin); 09 assumes 60 credits and $2.25 (91%). The 03 seed is the default and the pilot decides.
4. **Print margin** (pack 04): 07 targets 35 to 45% after vendor, shipping and Stripe fees; 09's $26.39 contribution is 59% of the book price with shipping passed through at cost. A price guard and real quotes settle it. 09's poster contribution of $16.47 also differs by one cent from its own inputs ($16.46).
5. **Discover and partner cards** (pack 03): 05 section 6.23 says "No partner cards" while the sitemap lists guides under Discover. Pack 03 keeps Discover free of cards and adds a labeled section on destination pages and a Guides screen.
6. **Phase naming and section numbers:** the full specs call this work Phase 4 and "year 2", and the Phase 1 editions renumber some sections (for example the Phase 1 roadmap Definition of Done is in section 6, not 5). The packs cite the full specs for DDL and rules and the Phase 1 editions for conventions.
7. **Names:** table and column names follow Phase 1 03 section 14 ("working names that the pack may refine"). The refinements are listed in each pack: pack 06 splits API credentials into `api_clients` and `api_keys` and adds domains and contracts; pack 07 adds the approval trail `card_offer_reviews` and makes offers opt-in through the `offers` consent.
8. **Section 14 of Phase 1 03 lists `payment_collections` as a Phase 3 table**, while the full 03 creates it in the first migrations; the packs follow Phase 1 03 (created in pack 01).
