# Hermi competitor review mining

Date of research: 2026-09-30. Spec checked: business-plan/app-buildout/01-product-spec.md (all 1614 lines read).

## 0. Method and confidence (read first)

- Tools: WebSearch worked. WebFetch was blocked by the network proxy for almost every review host (apps.apple.com, trustpilot.com, producthunt.com, reddit.com, justuseapp, wandrly, tripstone, marlvel and most blogs). So I could not open a single App Store, Trustpilot, Product Hunt or Reddit page directly.
- Consequence: every fact below is **reported, verify**. It comes from search-result snippets and summaries of secondary review articles, not from pages I read. Quotes are short and are as they appeared in snippets. Nothing is a verified primary review. No Reddit thread was read; "Reddit says" claims are second-hand via review articles.
- Frequency and severity ratings are my estimates from how often a theme appeared across snippets (High = appeared in 3+ independent sources, Medium = 2, Low = 1), not counts of reviews.
- Recommended follow-up: the owner (or a session with open egress) should spot-check the App Store "most critical" sort and Trustpilot 1 to 3 star filters for TripIt, Wanderlog and Layla, and the r/travel, r/solotravel, r/digitalnomad, r/iosapps searches for "TripIt", "Wanderlog", "Trippy".

## 1. Who is "Trippy"?

Voice dictation is ambiguous. Findings (reported, verify):

| Candidate | Evidence | Verdict |
|---|---|---|
| "Trippy - Travel App" (iOS, id1535706273) | App Store rating reported as 2.00 from 4 ratings; last update reported 2022-08-18; one review (April 2023) says "None of the features previewed are available in any kind of menus", only a globe shows, no maps, no Yelp reviews | Tiny, stale, not a real competitor |
| Trippy (2011, J.R. Johnson) | Social "friend-sourcing" travel tool, Pinterest-like want/been boards, tied to Facebook | Defunct or historical |
| Trippy AI travel guide (Firebase + Gemini, 2024 Gemini competition entry) | Games, scavenger hunts, receipt scanning for expenses with auto currency conversion | Hackathon-style; not a market leader |
| Trippy.com / Tripadvisor-style "Trippy" | Nothing found | Unknown |
| **TripIt** | Most likely what the owner means: a well known incumbent whose name sounds like "Trippy" in dictation | Treat as the main competitor |
| Tripsy (also appeared in the "Trippy" search) | Apple-native organizer, about $59 a year, recently added a Claude AI feature (reported) | Sound-alike; include as a watch item |

Recommendation: confirm with the owner. The plan below treats TripIt as the primary competitor and includes Tripsy notes where they surfaced. A literal app named Trippy has no meaningful review base (4 ratings), so there is nothing to mine beyond "features shown in screenshots were not in the app", which is a lesson in honest marketing.

## 2. TripIt and TripIt Pro

Pricing context (reported, verify): Pro about $49 a year. Free tier: email-forward itinerary building, sharing (view only). Pro adds real-time flight alerts, seat tracking, fare-drop refund alerts, points tracker, offline access.

### 2.1 Top praised features

| Feature | Example quote or paraphrase | Source (date) | Strength |
|---|---|---|---|
| Forward-a-confirmation-email builds an itinerary | "forward travel-related emails for automatic organization" | Wandrly review, 2026 (snippet) | High |
| Fare-drop alerts paying for Pro | "That feature alone is worth the pro upgrade even for infrequent travelers"; one user got $43 x 6 vouchers ($258) | Travel blog roundup, CIO, Xevio 2025 (snippets) | High |
| Flight alerts, seat tracking | "Pro gets credit for paying for itself through fare-drop alerts and seat tracking" | Review roundup (snippet) | Medium |
| Southwest refund alerts | Named as a standout benefit | travelsummary.com (snippet) | Low |
| One master itinerary for business travel | Common framing for frequent flyers | Multiple blogs | Medium |

### 2.2 Top complaints by theme

| Theme | What users say | Source (date) | Frequency | Severity |
|---|---|---|---|---|
| Paywall on essentials | "flight alerts and offline access that modern alternatives now include for free" at $49 a year; occasional travelers "mostly don't justify the cost" | monkeyeatingmango, Wandrly 2026 (snippets) | High | High |
| Stale, dated UI | "appearing as if it hasn't been updated since 2015" | Review roundup 2026 (snippet) | High | Medium |
| Email parsing failures | breaks "if emails are not formatted as expected or if plans are booked through unsupported platforms, requiring manual adjustments" | Wandrly 2026 (snippet) | High | Medium |
| Sync and data-loss bugs | "within the last month it's suddenly gotten all glitchy. The app seems to keep resetting because it won't keep my trips" | Review listing, 2026 (snippet) | Medium | High |
| Wrong or confusing alerts | Gate-change text for a different airline's gate; user went through security repeatedly | Review listing (snippet) | Low to Medium | High |
| Billing and renewal | Daily renewal reminders after paying for another year; "fees already paid are nonrefundable"; support did not help | Trustpilot, PissedConsumer (snippets) | Medium | Medium |
| Collaboration limits | "TripIt only offers view-only collaboration" | Comparison blogs 2026 (snippets) | High | High for groups |
| No expense or budget splitting | "TripIt has no expense tracking or splitting feature of any kind" | Comparison blogs 2026 (snippets) | High | High for groups |
| No group decisions | "won't help a group choose a destination, vote on activities, or split a bill" | Group-app roundups 2026 (snippets) | High | High for groups |
| Not a planner | Organizes bookings, does not help discover or plan days, no map-first planning | Wanderlog-vs-TripIt posts (snippets) | High | Medium |
| Customer support | Unhelpful on billing | Trustpilot (snippet) | Low to Medium | Medium |
| Data privacy | Nothing substantive found | none | Not found | n/a |

### 2.3 Unmet requests (reported, verify)

- Free flight alerts and free offline (most repeated).
- Real group planning: edit rights for travelers, voting, shared expenses.
- Planning side: map, day-by-day plan, places discovery.
- Better import that handles unsupported booking sites.
- Modern design.

## 3. Wanderlog (reference)

Pricing (reported, verify): free core planning and collaboration; Pro about $39.99 to $49.99 a year ($4.99 monthly) for offline, Google Maps export, Gmail sync, dark mode, ad removal. App Store rating reported 4.9 with 5,000 to 33,000+ reviews (figures differ by source).

### 3.1 Praise

| Feature | Quote or paraphrase | Source (date) | Strength |
|---|---|---|---|
| Map plus itinerary with travel time between stops | "the map of the trip and time/miles between spots" | review roundups (snippet) | High |
| Live collaboration by link or email | "real-time collaboration like Google Docs" | Tripstone/Reddit summary 2026 (snippet) | High |
| Email and Gmail import | "Forward email" or "Sync with Gmail" populates flights and stays | reviews (snippet) | High |
| Budget tool with splitting | tracks expenses and splits between tripmates | comparison blogs (snippet) | Medium |
| Overall delight | "Love love love!" | App Store (snippet) | High |

### 3.2 Complaints

| Theme | Detail | Source (date) | Frequency | Severity |
|---|---|---|---|---|
| Paywall on offline | "#1 complaint on the App Store"; users call it "ridiculous"; Pro "really is not worth the $40 a yr" | App Store, review blogs 2026 (snippets) | High | High |
| Subscription and cancellation friction | "cancellation of free trial is described as a nightmare"; slow cancel handling; messages to founder ignored; "charged for the whole year" | Trustpilot (snippets) | High | High |
| Card imported without consent | "immediately imported credit card from Google wallet without permission" on trial signup | Trustpilot (snippet) | Low | High (trust) |
| Sync and server errors | "unable to connect, restart the app" even for paid users; occasional downtime; tip: export a backup before travel | App Store, Reddit via Tripstone (snippets) | Medium | High |
| Group chaos, no commenting or history | "no commenting system or version history"; no structured voting ("decisions still happen in chat") | Tripstone, group roundups (snippets) | High | High for groups |
| Solo-planner centre of gravity | group features exist but it is built for one planner | comparison blogs (snippet) | Medium | Medium |
| No flight price tracking | not reported as a feature | n/a | Gap | n/a |

### 3.3 Unmet requests: free offline, voting and polls, comments, version history, better reliability, honest trial.

## 4. Layla and Mindtrip (reference)

Layla (owned by Expedia, reported): Trustpilot about 4.0 from 71 to 86 reviews; day-by-day detail and PDF behind about $49 a year (reported, verify). Mindtrip: launched Flights (May 2026, Sabre and PayPal) and Stays (July 2026) (reported, verify).

### 4.1 Praise

| App | Feature | Quote or paraphrase | Source | Strength |
|---|---|---|---|---|
| Layla | Chat planning and one-chat booking | "plan and book vacations easily, saving time on research" | Trustpilot summary (snippet) | High |
| Layla | Good for mainstream destinations | "excels with mainstream destinations" | AI planner reviews 2026 (snippet) | Medium |
| Mindtrip | Conversational search, maps, collaborative sharing | "supports collaborative planning" | reviews 2026 (snippet) | Medium |

### 4.2 Complaints

| Theme | App | Detail | Frequency | Severity |
|---|---|---|---|---|
| AI accuracy and hallucinations | Both | Layla: "restaurant names, opening hours, and pricing can be hallucinated"; "forgets instructions"; Mindtrip suggested hotels that do not exist (a Holiday Inn Express in Tokyo, an Intercontinental in Nagasaki) | High | High |
| Generic for less-visited places | Layla | "becomes generic and unreliable for less-visited places" | Medium | Medium |
| Date and logic bugs | Layla | AI ignoring overnight flights arriving next calendar day | Low | High |
| Billing and trial | Layla | charged right after trial; refund refused in one review; "billing and cancellation headaches" | Medium | Medium |
| Paywalled detail | Layla | day-by-day and PDF at $49 a year; free tier limits chats | Medium | Medium |
| Itinerary randomly reorders | Mindtrip | "randomly refreshing and messing up the order of places" after hours of organizing | Low to Medium | High |
| Filters not honored | Mindtrip | budget filter shows results above ceiling | Low | Medium |
| No real group deciding | Mindtrip | "built around solo and couple planning rather than providing a way for a group to actually decide" | Medium | Medium |
| Trust, no benchmark | All AI | "no independent benchmark... any AI-surfaced venue is a lead rather than a fact" | High | High |

### 4.3 Unmet requests: verified facts with citations, group voting, transparent credits, reliable dates.

## 5. "Trippy" itself

Reported, verify: 2.0 stars from 4 ratings; "None of the features previewed are available in any kind of menus" (App Store review, April 2023); no maps; no Yelp reviews; last update 2022-08-18. No Trustpilot, Product Hunt or Reddit threads found for an app by this name. (Trustpilot "trippytourguide.com" is an unrelated tour company.) Nothing further to mine.

## 6. Cross-cutting themes (ranked by breadth and severity)

1. Paywalled basics (offline, alerts): TripIt, Wanderlog, Layla. Universal and angriest.
2. Subscription and cancellation distrust: all three.
3. AI fabricated venues and dates: Layla, Mindtrip.
4. Groups cannot decide or split money in one place: TripIt, Wanderlog, Mindtrip.
5. Reliability, sync and data loss: TripIt, Wanderlog, Mindtrip.
6. Confirmation import fragile or absent: TripIt (fragile), Wanderlog (works, Pro), Layla (none).
7. Dated UI: TripIt.
8. Flight price tracking exists only as post-booking refund alerts (TripIt Pro), not pre-booking watching tied to a plan.

## 7. Gap list against the Hermi spec

Coverage key: Yes (specified), Partial, No (missing or out of scope).

| # | Recurring complaint or request | Seen in | Hermi spec coverage | Idea to beat the competitor |
|---|---|---|---|---|
| 1 | Offline is paywalled | Wanderlog, TripIt | Yes: F-TRV-2 and 6.2 offline read on every tier, per-trip download | Market it: "Offline is free." Put a guarantee in onboarding. Ship offline write (spec defers to phase 2) earlier as a differentiator. |
| 2 | Flight alerts paywalled or flight status unreliable | TripIt | Partial: F-FLT-6 fare alerts (1 free, cached). Flight status, gate and delay alerts are not specified | Add free delay and gate-change push for chosen flights, fed by a status API; state the data source and time in the alert. |
| 3 | Fare tracking: only post-booking refund alerts exist | TripIt Pro | Partial: F-FLT-5 shows movement against the chosen fare; F-AFT-1 delay claim prompt | Add "price dropped after you booked" alert with the refund or credit rule per airline; this is TripIt's best loved feature, match it in Plus. |
| 4 | Expensive, unclear value | TripIt, Wanderlog, Layla | Yes: Trip Pass $9.99, no forced subscription, free path always visible | Lead with "No subscription needed" for one-trip users; show price per trip versus $49 a year. |
| 5 | Trial and cancellation traps, unexpected charges, auto-imported card | Wanderlog, Layla, TripIt | Yes: F-SUB-1 trial only on annual, price and date stated, reminder before conversion; F-SUB-6 pause and cancel; no dark patterns | Publish a one-tap cancel inside the app and a plain-language "how billing works" page; use it in App Store copy. |
| 6 | Hallucinated venues, hotels, hours, dates | Layla, Mindtrip | Yes: F-AI-2 places grounded via place search, ungrounded dropped; F-AI-5 source URLs; fares seen on page | Show a "Verified on <date>" chip per item; publish an accuracy note. Sell "AI that cites sources". Add date-logic tests (overnight arrivals, time zones) to evals. |
| 7 | AI is opaque about cost or limits | Layla | Yes: credit price shown before every action, refunds on failure | Keep. Show remaining credits inline; never a silent cap. |
| 8 | Group cannot decide (no polls, no voting) | Wanderlog, TripIt, Mindtrip | Yes: F-GRP-1 polls, F-LDG-5 hearts, date polls. Risk: polls for free owner are preview only | Consider free polls on any trip to win group virality; invitees already use them free. Add "find dates everyone is free" scheduler. |
| 9 | Expense splitting lives in Splitwise | TripIt, Wanderlog (partial) | Yes: F-GRP-2 and 3 multi-currency, minimized transfers; Stripe collection Phase 4 | Emphasize cost plus plan in one app; add receipt photo capture later (Trippy AI demo did OCR). |
| 10 | No comments or version history; editing chaos | Wanderlog | Partial: activity feed and 409 conflict UI (F-COL-5); comments on ideas (F-ITN-3); general comments Phase 4 | Pull comments earlier; "Keep mine or use theirs" merge is already better than silent overwrite, so advertise it. |
| 11 | Real-time collaboration sync bugs and outages | Wanderlog, TripIt | Partial: 15 to 30 s polling, versions, offline queue; no real-time by design | Fine for 2 to 12 people. Show a visible "Synced 12 s ago" indicator and a safe offline queue; publish a status page. |
| 12 | Email or Gmail import fails or needs Pro | TripIt, Wanderlog | Partial: F-AI-10 paste-a-booking (1 credit); email and calendar inbox parsing is explicitly out of scope | Add a forwarding address later (zero-credit, deterministic parser for top airlines plus Haiku fallback). At minimum keep paste free or cheap; do not make it a paid-only feature. |
| 13 | Dated UI | TripIt | Yes: Hermi design system, presentation mode | Screenshot-led marketing; accessibility as a quality signal (WCAG AA is specified). |
| 14 | Planner versus organizer: no one does both | TripIt (organizer), Wanderlog (planner) | Yes: itinerary, map, stays, flights, checklist in one | Position "Plan together. Know the fare." as planning plus fare intelligence in one. |
| 15 | Invite gating: collaboration behind paywall | TripIt (view only), Wanderlog (free collab) | **Conflict**: F-COL-3 a free owner cannot invite; Wanderlog collaboration is free | Real risk. Wanderlog's free collaboration sets expectation. Mitigate with Trip Pass framing ("They join free") or allow one free invitee (partner) on free trips, since the target persona is a couple. |
| 16 | Free tier too thin (2 travelers, 2 trips, 8 stays) | Wanderlog comparison | Partial: limits are explicit | Test a couples-friendly free tier (2 travelers already included); keep the paywall moments non-blocking. |
| 17 | Support unresponsive | TripIt, Wanderlog | Partial: admin support tickets (08 file); no response-time promise in this spec | Publish a support response SLA and put Help in Settings; reply in-app. |
| 18 | Data privacy and AI consent | Not a top complaint | Yes: consent screen, PII stripping, export, delete, no ad SDKs, no ATT prompt | Use as quiet trust marketing: "No ads, no data sales". |
| 19 | Android missing | Every alternative ships Android | No: Android is later; web works | Ship a good PWA install path; web covers Android users meanwhile. Note many "Trippy/TripIt" users are cross-platform. |
| 20 | Points, loyalty tracking (TripIt Pro) | TripIt | No: explicitly out of scope | Skip; appeals to the business flyer, not the target persona. |
| 21 | Calendar sync (live subscription feed) | TripIt | Partial: ICS export only | Add a live ICS subscription URL; cheap and expected. |
| 22 | Email-forward auto-import at launch | TripIt strength | No | See row 12. TripIt owns this; do not compete head-on at launch, win on group and AI honesty. |
| 23 | Hotel filters not honored | Mindtrip | Yes: rental search states sort; F-LDG-4 price and rating only | Keep filters strict; add a test that results never exceed a stated ceiling. |
| 24 | Itinerary reorders or loses user work | Mindtrip, TripIt | Yes: version checks, drafts are preview-only; nothing saved until accepted | Advertise "AI never changes your plan without asking". |

## 8. Biggest opportunities, ranked

1. Free offline plus honest pricing (rows 1, 4, 5): highest-volume, angriest complaint.
2. Sourced AI that does not invent venues (rows 6, 7, 24): a measurable, demo-able edge over Layla and Mindtrip.
3. Group deciding in one app: polls, hearts, date polling, expenses (rows 8, 9, 10): no competitor covers all; partially undercut by the invite paywall (row 15).
4. Fix the invite paywall risk (row 15): the spec's biggest self-inflicted gap versus free Wanderlog collaboration.
5. Flight status and post-booking fare-drop alerts (rows 2, 3): TripIt's loved and paid features; the spec has fare alerts but not delay and gate alerts.
6. Cancellation and trial transparency (row 5).
7. Email forwarding or cheaper booking import (row 12).
8. Live calendar feed, comments earlier, support SLA, PWA for Android (rows 10, 17, 19, 21).

## 9. Sources (all reported via search snippets; pages not opened)

- Trippy App Store listing: https://apps.apple.com/us/app/trippy-travel-app/id1535706273
- Trippy Firebase and Gemini write-up: https://firebase.blog/posts/2024/11/gemini-competition-best-firebase-app/
- Tripsy App Store reviews: https://apps.apple.com/us/app/tripsy-travel-planner/id1429967544?see-all=reviews
- TripIt Trustpilot: https://www.trustpilot.com/review/www.tripit.com
- TripIt PissedConsumer: https://www.pissedconsumer.com/tripit/RT-F.html
- TripIt Wandrly review: https://www.wandrly.app/reviews/tripit
- TripIt pricing, monkeyeatingmango: https://monkeyeatingmango.com/blog/tripit-pricing-2026/
- TripIt Pro refund alerts and fare tracking: https://www.cio.com/article/244687/why-the-tripit-pro-plan-is-worth-49-a-year.html ; https://xevio.us/2025/03/tripit/ ; http://www.travelsummary.com/another-benefit-tripit-pro-southwest-refund-alerts/
- Pilot TripIt review: https://www.pilotplans.com/blog/review-of-tripit
- Wanderlog Trustpilot: https://www.trustpilot.com/review/wanderlog.com
- Wanderlog Reddit summary: https://tripstone.app/blog/wanderlog-review
- Wanderlog App Store: https://apps.apple.com/us/app/wanderlog-travel-planner/id1476732439?see-all=reviews
- Wanderlog marlvel report: https://marlvel.ai/intel-report/travel/wanderlog-travel-planner
- Layla Trustpilot: https://www.trustpilot.com/review/layla.ai
- Layla reviews: https://aitravel.tools/layla-ai-review/ ; https://www.endlesstravelplans.com/guides/planning-tools/layla-ai-review
- Layla vs Mindtrip: https://aitravel.tools/layla-vs-mindtrip-vs-wonderplan/
- Mindtrip Product Hunt: https://www.producthunt.com/products/mindtrip/reviews
- Mindtrip reviews: https://monkeytravel.app/blog/mindtrip-review-2026
- AI planner hallucination roundup: https://www.travelanywhere.blog/blog/best-agentic-ai-travel-apps-2026-mindtrip-layla-stippl-stardrift-wanderlog-tested
- Group trip app roundups: https://tripstogether.co.uk/blogs/best-group-trip-planning-apps-2026 ; https://www.jettova.com/blog/best-app-group-trip-voting-2026
