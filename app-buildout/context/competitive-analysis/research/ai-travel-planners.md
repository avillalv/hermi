# AI trip planners: competitive survey for Hermi

As of 2026-09-30. Prepared for the Hermi build spec (`business-plan/app-buildout/`).

## Method and confidence (read first)

- Tools: WebSearch only. WebFetch was blocked by the network egress proxy for every domain tried (techcrunch.com, phocuswire.com, apps.apple.com, and two review sites), so no page was read in full. Every fact below comes from search-result snippets or summaries.
- Tag **[RV]** = reported, verify. Because nothing was fetched, treat every number as [RV] unless a primary source (company newsroom, app store page) is checked before it is quoted externally.
- "n/f" = not found in snippets. "?" = unknown.
- Conflicts seen in snippets are listed in Section 7. Do not cite the conflicting figures until resolved.
- Hermi facts come from `app-buildout/README.md` and `phase-1-launch/README.md` (written 2026-09-30). Hermi is unbuilt, so its column shows the plan, not shipped product.
- Vendor "best AI planner" blog rankings (monkeytravel.app, stardrift.ai, travelanywhere.blog, etc.) are marketing from competing products. They were used only for qualitative complaint themes.

---

## 1. Profiles (per app)

Format: owner and launch; platforms; traction; pricing; AI; collab; flight tracking; lodging; sources; offline; monetization; complaints. All [RV].

### Dedicated AI planners

**Layla (layla.ai, formerly Ask Layla)**
- Owner and launch: Expedia Group acquired it (closed 2026-07-31, announced 2026-08-01, terms undisclosed). Berlin, founded 2023, about 25 staff, about 5 million euro raised (First Minute Capital, M13). Co-founders Saad Saeed, Jeremy Jauncey. Earlier it acquired Roam Around (Feb 2024). Expedia says Layla keeps operating; no date for folding it into Expedia products. [RV]
- Platforms: web, iOS, Android, plus an earlier Messenger/WhatsApp-style assistant (n/f in snippets). [RV]
- Traction: homepage counter about 2.1 million trips planned (Aug 2026); Trustpilot 4.0 from 86 reviews. No download figure found. [RV]
- Pricing: core planning free but shallow (overview, map, total price); day-by-day breakdown behind a 3-day trial or premium. Premium reported $49 to $49.99 a year or $9.99 a month; PDF export and sharing in premium. [RV]
- AI: conversational itinerary, live-priced flights and stays, bookable activities, local transport. Agentic booking is partial (hands off to partners). [RV]
- Collaboration: limited; shareable trips are premium. Offline: limited, internet needed for most features. Flight tracking: n/f. Lodging comparison: partner listings, not a shortlist and vote flow. Sources shown: no citations reported.
- Monetization: bookings and affiliate via partners (now Expedia). Subscription on top.
- Complaints: paywall on the useful part, unexpected recurring charges, heavy app, AI opening hours, travel times and visa guidance sometimes wrong.

**Mindtrip**
- Owner and launch: Mindtrip, Inc. (US). Seed $7M (Costanoa), Series A $12M (Sept 2024), about $19M total, plus $2M in Dec 2025; investors named include Capital One Ventures, United Airlines Ventures, Amex Ventures. [RV]
- Platforms: web and iOS. Traction: App Store 4.7 from about 806 ratings; est. 2025 revenue about $3.6M (Latka, low-confidence estimate). [RV]
- Pricing: consumer app free, monetizes via booking partnerships; paid tiers reported for creators ($19 a month) and businesses. [RV]
- AI: chat, itinerary, map, receipts and email import, local events discovery (2026), in-chat flights booking via Sabre inventory with PayPal checkout (announced 2026-05-06). [RV]
- Collaboration: real-time group chat, tag @Mindtrip for suggestions; free tier reported up to 5 people. Offline: no offline mode reported. Flight tracking: n/f. Lodging: suggestions and booking partners. Sources: place cards and reviews; no per-claim citation model reported.
- Monetization: booking commissions and partnerships, B2B tier.
- Complaints: crashes, billing issues, update regressions, slow responses, no cruise or multi-destination start, generic "consensus" picks that ignore saved places.

**Wanderboat**
- Owner and launch: Wanderboat AI, San Francisco, founded 2023 by You Wu (ex Microsoft AI, Bing Chat) and Xiaochuan Ni; Sequoia-backed (reported). [RV]
- Platforms: iOS, Android, web. Traction: 2 million users (Jan 2026) vs "3.5 million" on another page (conflict). Ran a San Francisco BART ad campaign. [RV]
- Pricing: free; "plans" on aggregator sites appear invented. [RV]
- AI: chat, POI discovery, itinerary, drag-and-paste sources. Collaboration and offline: n/f. Flight tracking: no. Lodging: discovery only. Sources: community posts and POI data, no citation model reported.
- Monetization: n/f (likely affiliate). Complaints: n/f in snippets.

**iplan.ai**
- Owner and launch: small independent developer, launched about 2022 (App Store id 1611716564). [RV]
- Platforms: iOS, Android. Traction: App Store 4.5 from 1.5K ratings; Google Play 3.8 from 6,540+ reviews. [RV]
- Pricing: free trips per month; in-app purchases $3.99 (itinerary builder) and $9.99 (Pro). [RV]
- AI: 30-second day-by-day itinerary generation. No booking, no collaboration reported, offline n/f.
- Complaints: illogical routing, activities at wrong times, limited cities, bugs and crashes.

**Roam Around**
- Owner: acquired by Layla in Feb 2024 (Miami Beach origin, 2023). [RV]
- Traction: 10 million itineraries and about 500K monthly site visits at acquisition; "143,606 users" on a directory page. [RV]
- Pricing: tokens (30 for $5, 80 for $10, 150 for $15; one token per plan) and subscriptions from $2.99 a month. [RV]
- AI: one-shot itinerary plus destination facts. Collaboration, offline, bookings: n/f. Status after the Layla and Expedia deals is unclear.

**Trip Planner AI (tripplanner.ai / trip-planner.ai)**
- Owner: independent (several lookalike products share the name; one iOS "AI Trip Planner" at $3.99 a month or $24.99 a year, rating 4.2). [RV]
- Traction: claims 4.8 stars and 75,000 travelers (vendor claim). [RV]
- Pricing: pay per trip; free plan limited to 3-day itineraries and 2 lifetime itineraries. [RV]
- AI: itinerary with "real traveler insights" and price estimates. Complaint: plan blocked before you can judge value ("clever business, poor value").

**Wonderplan**
- Owner: independent web tool. Free "at least for now", form-driven (destination, dates, budget tier, companion type, interests), PDF export, saved trips. [RV]
- Complaint: template generator; changing profile returns the same base itinerary lightly reshuffled. No booking, collaboration or offline reported.

**Stippl**
- Owner: Stippl (Europe-founded, n/f details); claims 1.5 million travelers (vendor self-report, unaudited); app updated Sept 2026. [RV]
- Pricing: free plus Pro $3.99 a month or $24.99 a year (offline, advanced AI, enhanced collaboration, email forwarding, expense reports). [RV]
- AI: itinerary generator and activity suggestions. Collaboration: yes (enhanced in Pro). Offline: Pro. Bookings: limited partner links. Sources: n/f.

**Airial**
- Owner: Airial Travel, founded by ex-Meta engineers Archit Karandikar and Sanjeev Shenoy; public beta Dec 2024; $3M seed (June 2025; Montage Ventures, Peak XV, South Park Commons). [RV]
- AI: turns creator links (TikTok, Reels, blogs) into itineraries with flights and hotels. Traction, pricing, collaboration: n/f.

**Curiosio**
- Owner: small independent (Ukraine-linked; n/f in snippets). Free road-trip and multi-stop generator across 32 countries with cost and time breakdown, Google Maps handoff; modes: Travel, Geek, Beta. Low commercial push. Traction and complaints: n/f. [RV]

**Vacay**
- Owner: solo developer (Mohamed Nasreldeen Salem on Google Play). Free (3 plans), Premium $9.99 a month, Professional $49 a month (US only). Chatbot, itinerary builder, themed advisors, 150+ languages. Traction n/f. [RV]

**Holiwise**
- Owner: Holiwise, London, founded 2023; about 1.45 to 1.5 million euro pre-seed (Aug 2025; execs from BoA, Google, Barclays, Goldman). Premium-leaning recommendations, hotels and itineraries, group trip planning, "tens of thousands of monthly users" with 80%+ returning (company claim). Free. [RV]

**GuideGeek (Matador Network)**
- Owner: Matador Network (publisher); built on OpenAI. Free, inside WhatsApp, Messenger, Instagram (no app). Reported 1.5 million users, 3.7 million questions, 42 languages, 61 countries (dated figure, likely 2023 to 2024). Chat and flight search; no persistent trip workspace. Monetization: Matador sponsored content and partner deals. [RV]

**Stardrift (found during research)**
- Free AI planner with live prices and calendar awareness (flags meeting conflicts), Starlink wifi flight filter, preference memory across trips, bookable flights and hotels, calendar sync. Traction n/f. [RV]

**Wanderlog (adjacent, found during research)**
- Map-first collaborative planner; about 1M+ users, $1.5M seed 2021 (Y Combinator, General Catalyst). Free tier has live collaboration; Pro $39.99 a year (one source says $49.99): offline, more AI messages (free AI reported capped near 5 messages per trip), route optimization, flight and car deals. Not AI-first but the main collaboration benchmark. [RV]

### Big platforms

**Expedia Group: Romie, ChatGPT app, Layla**
- Romie: introduced May 2024 (EG Labs, OpenAI-powered) as a group-chat concierge: invited into SMS group chats, reads emails, disruption help. Skift (via Skift post 2026-08) reports Expedia has deprioritized Romie for a multi-agent approach and bought Layla. [RV]
- Expedia app in ChatGPT: live 2025-10-06; live hotel and flight results, prices, maps; Free, Go, Plus, Pro users outside EU (UK and Switzerland also excluded per one source); hand-off to Expedia to finish booking. [RV]
- Monetization: merchant margin and commissions. Sources: Expedia inventory and reviews. Collaboration: group chat via Romie (alpha). Offline: Expedia app itineraries. Complaint themes: n/f.

**Booking.com AI Trip Planner**
- Beta in US June 2023, OpenAI-powered, expanded 2024 to 2025 (UK, AU, NZ, SG, Europe). Free. Chat for inspiration, itinerary ideas, Smart Filter, property Q&A, review summaries. Also an app in ChatGPT (launched 2025-10-06 with Expedia). Google AI Mode hotel booking lists Booking.com as a launch partner (Aug 2026). [RV]

**Kayak**
- Kayak AI beta Apr 2025; AI Mode launched Oct 2025 (ChatGPT plus Kayak data), renamed "Ask AI" on the homepage as of Apr 2026; voice input Nov 2025; package search Jul 2025. A Kayak app exists in ChatGPT (details n/f). Price Forecast (buy or wait, 30 days) since 2013. Free. Monetization: referral and ad fees. Collaboration n/f. One snippet said "October 2026", which is an error for Oct 2025. [RV]

**Tripadvisor**
- Trips AI builder launched Oct 2023 (OpenAI); day-by-day itinerary from reviews (hundreds of millions to 1B+ reviews), save, edit, share. Tripadvisor app in ChatGPT for logged-in US users on Free, Go, Plus, Pro. Experimental video-to-itinerary demo at NVIDIA GTC 2026. Free. Monetization: hotel meta-search clicks, tours and experiences commissions, ads. Strongest citation-like trust signal (reviews). [RV]

**Google: Search AI Mode, Canvas, Gemini, Maps**
- AI Mode Canvas: side-panel editable itinerary from Search data, Maps photos and reviews, web content; auto-saves; share with friends who can "Customize Canvas". [RV]
- 2026-08-27: flight price tracking across 300+ airlines and sites, agentic hotel booking (chat, compare, cancellation terms, Google Pay; OTA or hotel stays merchant of record; partners Booking.com, Expedia, Hotels.com, Marriott, Hilton, IHG, Choice, Priceline, Trip.com, Wyndham), cost in miles or points. Gemini connects to Google Flights and Maps. Free. Gemini in Maps: conversational, group-dinner style queries. Monetization: ads and partner fees. [RV]

**ChatGPT (OpenAI)**
- General-purpose: itineraries, Agent Mode (paid) researches live and can drive booking apps with user approval (Expedia, Booking.com, Uber, DoorDash; Tripadvisor, Kayak, Omio, IHG, Iberia also reported). Group Chats (Nov 2025 global) up to 20 people, invite link. Free tier exists. Complaints (general chatbots): invented venues reportedly 15 to 20 percent of the time versus 3 to 5 percent for tools grounded in Google Places (one 2025 analysis, low confidence); closed restaurants found on the trip; fake hot springs incident. [RV]

**Perplexity**
- Hotel search and native booking with Selfbook (about 140,000 properties) and Tripadvisor reviews, announced Mar 2025; Pro perks planned; inline citations are a core Perplexity trait. No persistent trip workspace or collaboration reported. [RV]

**Trip.com TripGenie / Trip.Planner**
- Trip.com Group. TripGenie chat plus Trip.Planner hub (ITB Innovator 2026), Canvas editor, invite tripmates to co-edit; about 60% of interactions booking-related; users spend 20+ minutes in app. Free; commission. [RV]

---

## 2. Comparison matrix

Legend: Y yes, P partial, N no, ? unknown or not found. All competitor cells [RV]. "Agent acts" = can complete or drive a booking or long task on the user's behalf.

### 2a. Business facts

| App | Owner | Launch | Platforms | Traction (reported) | Free tier | Paid | Monetization |
|---|---|---|---|---|---|---|---|
| Layla | Expedia Group (closed 2026-07-31) | 2023 | Web, iOS, Android | ~2.1M trips, Trustpilot 4.0 (86) | Shallow | $49 to 49.99 a year, $9.99 a month | Bookings, affiliate, subscription |
| Mindtrip | Mindtrip Inc | 2023 to 2024 | Web, iOS | iOS 4.7 (806); ~$19M raised | Generous | B2B and creator tiers | Booking commissions |
| Wanderboat | Wanderboat AI | 2023 | Web, iOS, Android | 2M to 3.5M users (conflict) | Full | None found | ? |
| iplan.ai | Indie | ~2022 | iOS, Android | iOS 4.5 (1.5K), GP 3.8 (6.5K) | Few trips a month | $3.99, $9.99 | Subscription, IAP |
| Roam Around | Layla (2024) | 2023 | Web, iOS | 10M itineraries at acquisition | Limited | Tokens, from $2.99 a month | Tokens, subscription |
| Tripadvisor AI trip builder | Tripadvisor | Oct 2023 | Web, iOS, Android, ChatGPT | Part of a huge base | Free | None | Hotel clicks, tours, ads |
| Expedia Romie and ChatGPT app | Expedia Group | Romie May 2024, ChatGPT app 2025-10-06 | Expedia app, SMS, ChatGPT | n/f | Free | None | Booking margin |
| Kayak Ask AI and ChatGPT | Booking Holdings | Apr 2025, Oct 2025 | Web, mobile web, ChatGPT | n/f | Free | None | Referral, ads |
| Booking.com AI Trip Planner | Booking Holdings | Jun 2023 | Web, app, ChatGPT | n/f | Free | None | Booking commission |
| Google AI Mode, Gemini, Maps | Google | 2025 to 2026 | Web, Android, iOS | Billions of users (platform) | Free | Google AI plans | Ads, partner fees |
| ChatGPT | OpenAI | 2022 | Web, iOS, Android | Hundreds of millions (platform) | Free | $8+ plans | Subscription |
| Perplexity travel | Perplexity | Mar 2025 | Web, mobile | n/f | Free | Pro | Booking share (?) |
| GuideGeek | Matador Network | 2023 | WhatsApp, Messenger, IG | 1.5M users (dated) | Free | None | Sponsorship, partners |
| Wonderplan | Indie | ~2023 | Web | n/f | Free "for now" | None | ? |
| Trip Planner AI | Indie (several lookalikes) | ~2023 | Web, iOS | 75K (claimed) | 2 lifetime trips | Pay per trip, $3.99 a month | Per-trip fees |
| Stippl | Stippl | ~2022 | Web, iOS, Android | 1.5M (claimed) | Yes | $3.99 a month, $24.99 a year | Subscription, affiliate |
| Airial | Airial Travel | Beta Dec 2024 | Web | $3M seed | Yes | ? | Bookings (?) |
| Curiosio | Indie | ~2020 | Web | n/f | Free | None | Low commercial push |
| Vacay | Indie | ~2023 | iOS, Android | n/f | 3 plans | $9.99, $49 a month | Subscription |
| Holiwise | Holiwise (London) | 2023 | Web, iOS | "tens of thousands monthly" | Free | None | Booking commissions |
| Stardrift | Stardrift | ~2025 | Web | n/f | Free | ? | Bookings |
| Wanderlog | Wanderlog | ~2020 | Web, iOS, Android | 1M+ users | Good | $39.99 a year | Subscription, affiliate |
| Trip.com TripGenie | Trip.com Group | 2023 | App, web | ~1M inquiries (snippet) | Free | None | Commission |
| **Hermi (plan)** | Hermi | Target ~6 months after build start | Web, iOS (Android Phase 2) | 0 | Generous (2 trips, couples free) | $5.99 a month, $39.99 a year, $9.99 Trip Pass, credits | Subscription, passes, credits, affiliate, concierge |

### 2b. Capabilities

| App | Itinerary gen | Chat | Bookings in app | Real-time prices | Agent acts | Collab | Flight tracking | Lodging compare | Sources shown | Offline |
|---|---|---|---|---|---|---|---|---|---|---|
| Layla | Y | Y | P (partners) | Y | P | P | N | P | N | P |
| Mindtrip | Y | Y | Y (flights via Sabre, PayPal) | Y | P | Y (chat) | N | P | N | N |
| Wanderboat | Y | Y | N | ? | N | ? | N | N | P | ? |
| iplan.ai | Y | N | N | N | N | N | N | N | N | ? |
| Roam Around | Y | P | N | N | N | N | N | N | N | ? |
| Tripadvisor trip builder | Y | P | P (links) | P | N | P (share) | N | P | Y (reviews) | P |
| Expedia Romie and ChatGPT app | Y | Y | P (finish on Expedia) | Y | P | P (Romie group chat) | P | Y | P | P |
| Kayak Ask AI | P | Y | P (links) | Y | N | N | P (price forecast) | Y | N | N |
| Booking.com AI Trip Planner | Y | Y | Y | Y | P | N | N | Y (own stays) | P (reviews) | P |
| Google AI Mode, Gemini | Y | Y | Y (agentic hotels) | Y | Y | P (share Canvas) | Y (price tracking) | Y | P (links) | P |
| ChatGPT | Y | Y | P (apps) | P | P (Agent Mode) | P (20-person group chat) | N | P | P | N |
| Perplexity | P | Y | P (hotels) | Y | P | N | N | P | Y (inline) | N |
| GuideGeek | P | Y | N | P | N | N | N | N | N | N |
| Wonderplan | Y | N | N | N | N | N | N | N | N | N |
| Trip Planner AI | Y | N | N | P (estimates) | N | N | N | N | P | N |
| Stippl | Y | P | N | N | N | Y | N | N | N | Y (Pro) |
| Airial | Y | Y | P | Y | P | ? | N | P | P (creator links) | ? |
| Curiosio | Y | N | N | P (cost est.) | N | N | N | N | N | ? |
| Vacay | Y | Y | N | N | N | N | N | N | N | ? |
| Holiwise | Y | Y | P | P | N | Y | N | P | P (ratings) | ? |
| Stardrift | Y | Y | Y | Y | P | ? | N | P | ? | ? |
| Wanderlog | Y (AI assistant) | P | N | P (Pro deals) | N | Y (live) | N | P | P (place data) | Y (Pro) |
| Trip.com TripGenie | Y | Y | Y | Y | P | Y (invite tripmates) | P | Y | ? | P |
| **Hermi (plan)** | Y (draft_day, draft_trip) | Y (explain) | P (affiliate hand-off; LiteAPI Phase 3) | Y (cached plus live fares, SerpApi behind a flag) | Y (manual fare hunt and research runs; scheduled Pro, Phase 2) | Y (roles, hearts, activity log; polls and cost splitting Phase 2) | Y for fares (price history, alerts, booked-fare drop alert); flight status Phase 2 | Y (shortlist, hearts, compare) | **Y (every fact carries "Found on [site], checked [date]")** | **Y (all tiers)** |

---

## 3. Recurring weaknesses of AI planners as a category

Each is backed by the complaint themes above. Strength is how widely it appears in snippets.

| # | Weakness | Evidence (all [RV]) | Strength |
|---|---|---|---|
| 1 | Invented or stale places, wrong hours and travel times | Closed restaurants found on trips; fake hot springs incident; general chatbots hallucinating venues 15 to 20% of the time (2025 analysis, weak source); Layla AI hours, travel times, visa notes flagged as unreliable | Very high |
| 2 | No per-fact sources | Most dedicated planners show place cards, not "where this came from and when". Perplexity and Tripadvisor are exceptions (inline links, reviews) | High |
| 3 | One-shot itineraries that do not adapt | Wonderplan template reshuffles; iplan.ai illogical routing; Mindtrip "consensus" picks ignoring saved places | High |
| 4 | Weak group support | Collaboration is an add-on (chat tag, share link) rather than shortlist, vote and decide; Mindtrip capped at 5 on free; Layla shares are premium; ChatGPT group chat has no trip structure | High |
| 5 | No price tracking after the plan | Only Google (new), Kayak (forecast) and travel-hack tools track; planners show a price once | High |
| 6 | Paywall before value | Layla day-by-day locked; Trip Planner AI blocks the plan before you judge it; Roam Around tokens; Wanderlog caps free AI | High |
| 7 | Pushy or opaque booking | Planners owned by OTAs (Layla under Expedia, Booking, Trip.com) steer toward their own inventory; disclosure weak | Medium |
| 8 | Weak or missing offline | Mindtrip none; Layla limited; Stippl and Wanderlog gate it in Pro | Medium to high |
| 9 | Unexpected recurring charges and billing bugs | Layla, Mindtrip billing complaints | Medium |
| 10 | Bugs and crashes in small apps | iplan.ai, Mindtrip update regressions | Medium |
| 11 | Stale product after acquisition | Roam Around (absorbed by Layla), Romie deprioritized, Layla now Expedia-owned: roadmap risk | Medium |
| 12 | Privacy and data portability | Chat logs held inside platforms; none of the snippets mention export | Low evidence, high opportunity |

---

## 4. Where Hermi can be clearly best-in-class

Only claims tied to spec rules that are hard for big players to copy.

1. **Provenance on every AI fact.** Rule 4 ("Found on [site], checked [date]", fares must be seen on a page during the run). Answers weaknesses 1 and 2 directly. Google and ChatGPT cite loosely; none offers a per-fact dated evidence label inside a saved plan.
2. **Group decision workflow, not group chat.** Hearts, shortlist, compare, roles, then polls and cost splitting (Phase 2). ChatGPT group chats and Canvas share links lack structure; Wanderlog lacks AI with evidence.
3. **Free collaboration for couples.** Free owners invite 1 collaborator; invitees always join free. Competitors gate sharing (Layla) or group size (Mindtrip 5).
4. **Fare watching that follows the plan.** Price history, alerts, and the booked-fare drop alert ("you paid $X, now $Y; check change and credit rules"). Google now tracks prices but is not a trip workspace and is neutral to your plan.
5. **Honest commerce.** No ranking by commission, labeled affiliate links, no ads, no fake urgency, never fetching Airbnb, Vrbo or Booking pages. A trust position an OTA-owned planner cannot take.
6. **Offline on every tier** and an export and deletion promise (rule 6). Competitors gate offline or omit it.
7. **Switching path.** TripIt and Wanderlog import, pasted-confirmation import, first import earns a free Trip Pass.
8. **Predictable AI cost to the user.** Credit ledger and ceilings avoid surprise bills and "paywall before value": free gives 12 credits a month plus a deep-run taster.
9. **Presentation mode and print-quality PDFs** for sharing a plan with non-members.

Caveat: items 1, 3, 4 are design intent until built. Execution quality and latency decide whether they register.

---

## 5. Where big players will out-muscle Hermi, and how to avoid the fight

| Arena | Who wins | Why | Hermi posture |
|---|---|---|---|
| Live inventory and instant booking | Google (agentic hotels), Expedia, Booking, Trip.com | Direct supply, payments, merchant of record | Do not try to be the booking engine. Hand off via affiliate; LiteAPI stays Phase 3 and optional |
| Generic "plan me a trip" chat | ChatGPT, Gemini, Google AI Mode, Perplexity | Default app, free, billions of users, apps inside chat | Do not compete on one-shot generation. Let users bring AI drafts in (paste, import) and make Hermi the place to verify and decide |
| Discovery on search and maps | Google Search, Maps, Tripadvisor | Reviews, photos, query volume | Use Geoapify, Wikipedia and web fetch for facts; do not build a place database or review corpus |
| Price forecasting and metasearch depth | Kayak, Google Flights | Years of data, all-airline coverage | Track the user's specific fare; partner feeds only; never claim predictions as guarantees |
| Paid acquisition and brand | Expedia and Booking marketing | Budgets | Avoid paid search on "AI trip planner". Use SEO pages (`/vs/...`), shared-trip pages, referral credits |
| Ecosystem distribution (in-chat apps) | OpenAI and Google platform control | They can change terms, ranking, or ship your feature | Keep the product useful without any one assistant; consider an MCP or app surface later as a channel, not a dependency |
| Loyalty and card points | Amex, Capital One, airlines (Mindtrip investors) | Data and partnerships | Out of scope until Phase 3 |

Structural rule: stay where trust, collaboration and follow-through matter more than inventory or reach. Expect Google Canvas and ChatGPT group chats to keep narrowing the gap on basic group planning, so the defensible gap is evidence, decisions, and watching prices over months.

---

## 6. The 15 most important moves to win users from AI planners

Ordered by expected impact per cost, tied to the Phase 1 scope.

1. **Ship the evidence label as the hero.** Make "Found on [site], checked [date]" visible on every AI item, tappable to the source, with a "stale after N days" flag. Demo it in the first 30 seconds of onboarding and on the store listing.
2. **Free collaboration for two on day one.** Couple invites with no paywall, and show the partner's heart and vote live. Lead marketing with "plan together free".
3. **Import competitors' trips.** Polish TripIt and iCal import, and add a Wanderlog and Layla export-paste path (public pages are user-provided text, not scraped). Free Trip Pass for the first import.
4. **"Verify this plan" on AI drafts pasted from ChatGPT or Gemini.** Users already plan in chatbots; let them paste an itinerary and have Hermi check each place exists, hours, and travel time, with sources. Converts the biggest competitor into a funnel.
5. **Fare watch on the plan, not a separate tool.** Attach routes to trips, show price history, and push the booked-fare drop alert. Message it as "know the fare".
6. **No paywall before value.** Give a full first draft_trip free (the taster) with evidence and let the paywall hit only at save limits or live checks. Answer the Layla and Trip Planner AI complaint directly in copy.
7. **Adaptive plans.** When a place is closed, a flight changes, or a vote flips, offer a one-tap "repair day" with the reason shown. Counter "one-shot itinerary".
8. **Offline and export as headline features** on the listing: offline on free, PDF and data export always, in-app account deletion.
9. **Honest comparison pages.** `/vs/layla`, `/vs/mindtrip`, `/vs/wanderlog`, `/vs/chatgpt` with factual tables and dated sources, including where competitors win. Build them with the same evidence rule.
10. **Group poll and split flow (Phase 2) pulled forward as a thin slice** if user interviews confirm: one poll type (where to stay) plus a simple who-owes-whom. This is the clearest gap versus chatbots and Canvas.
11. **Transparent affiliate copy and a public "how we earn" page.** Screenshot-ready; contrast with OTA-owned planners. Publish the no-commission-ranking rule.
12. **Creator and link import.** Paste TikTok, Reels or blog links and turn places into saved candidates with sources (Airial's hook), but keep the fact-check step. Only use links the user provides; respect site terms.
13. **Referral credits and Trip Pass gifting.** Invitees join free and get a credit on signup; inviter gets credits when the invitee creates a trip. Organic growth through group trips, since every trip brings 2 to 6 people.
14. **Reliability bar.** Crash-free above 99.5% at TestFlight, latency budgets on AI actions, clear credit cost before a run. Mindtrip and iplan.ai reviews show small apps lose on bugs and billing surprises.
15. **Distribution beyond the app store.** Public sample trips and shared-trip pages for SEO, plus an MCP or assistant-side integration later so Hermi can be invoked from ChatGPT or Claude as a channel, without depending on it.

---

## 7. Open items and conflicts to verify before publishing any number

| Item | Conflict or gap |
|---|---|
| Layla price | $49 a year (layla.ai, Aug 2026 per one review) vs $49.99 a year and $9.99 a month (official articles per another) |
| Layla users | No download count; only "2,115,252 trips planned" counter |
| Wanderboat users | 2M (Jan 2026) vs 3.5M; "series B" label unverified; pricing on aggregator sites looks fabricated |
| Wanderlog Pro | $39.99 vs $49.99 a year; 1M+ users figure dated (2023) |
| Mindtrip pricing | Free app "monetizing through booking partnerships" vs paid tiers for creators and businesses |
| Kayak timeline | One snippet says AI Mode integrated "October 2026"; other sources say October 2025; rename to Ask AI reported Apr 2026 |
| Expedia Romie status | Skift reports deprioritized for multi-agent approach; Expedia newsroom not read |
| Expedia ChatGPT app regions | Outside EU (one source adds UK and Switzerland) |
| Hallucination rates | 15 to 20% vs 3 to 5% comes from a single low-authority blog; do not quote externally |
| Google AI Mode features | Rollout staged; availability by country and account not confirmed |
| Stippl, Airial, Curiosio, Vacay, Holiwise | Owner details and traction mostly vendor claims |

Suggested first verification pass (needs a network that permits fetches): Skift and PhocusWire Layla articles, Expedia newsroom (Romie, ChatGPT app), blog.google AI Mode Canvas, App Store and Google Play pages for Layla, Mindtrip, Stippl, Wanderlog, Wanderboat, iplan.ai, and Trustpilot pages for complaint sampling.

---

## Sources (all via search results; dates are publication or event dates as reported; none fetched in full)

- Skift, "Expedia Acquired AI Trip-Planner Layla: Exclusive", 2026-07-31. https://skift.com/2026/07/31/expedia-acquired-ai-trip-planner-layla-exclusive/
- Skift on X summary of the Layla deal, 2026-08. https://x.com/skift/status/2083260024252416436
- PhocusWire, "Expedia calls on Layla to speed up its AI strategy", 2026-08. https://www.phocuswire.com/news/technology/expedia-group-acquires-ai-travel-planning-app-layla
- Hospitality Net, HN Brief on Layla deal, 2026-08. https://www.hospitalitynet.org/editorial/4133797/
- Travelers Today, "Expedia Buys Layla", 2026-08-01. https://www.travelerstoday.com/articles/60678/20260801/expedia-buys-layla-what-ai-trip-planner-deal-changes-travelers.htm
- Endless Travel Plans, "Layla AI Review 2026", 2026. https://www.endlesstravelplans.com/guides/planning-tools/layla-ai-review
- Trustpilot, Layla reviews. https://de.trustpilot.com/review/layla.ai
- TechCrunch, Layla acquires Roam Around, 2024-02-12. https://techcrunch.com/2024/02/12/travel-startup-layla-acquires-flyr-backed-ai-itinerary-building-bot
- PhocusWire, Mindtrip funding and receipts; Latka, Mindtrip revenue estimate; Tracxn and PitchBook profiles, 2025 to 2026. https://www.phocuswire.com/ai-travel-planner-mindtrip-receipts-funding ; https://getlatka.com/companies/mindtrip.ai
- Sabre and Morningstar, "Mindtrip launches agentic AI flight booking", 2026-05-06. https://www.morningstar.com/news/pr-newswire/20260506ph51568/
- AltexSoft, "Mindtrip adds in-chat flights", 2026. https://www.altexsoft.com/travel-industry-news/mindtrip-adds-in-chat-flights-as-ai-moves-to-action/
- Apple App Store, Mindtrip listing (via search snippet). https://apps.apple.com/us/app/mindtrip-ai-travel-companion/id6503107567
- Wanderboat: Google Play listing, PhocusWire Startup Stage, PR Newswire launch, Crunchbase, Tracxn. https://play.google.com/store/apps/details?id=com.wanderboat.app
- iplan.ai App Store and Google Play listings, Cybernews, 2026. https://apps.apple.com/us/app/iplan-ai-ai-travel-planner/id1611716564
- Roam Around App Store listing and directory pages, 2026. https://apps.apple.com/us/app/roam-around-plan-trips-ai/id6446047996
- Trip Planner AI listings and reviews (App Store, Futurepedia, serp.ai), 2026. https://www.trip-planner.ai/
- Wonderplan reviews (The Rundown, aitravel.tools, monkeytravel.app), 2026. https://www.therundown.ai/tools/wonderplan
- Stippl reviews and pricing (itechguides, wandrly, mwm.ai), Sept 2026. https://www.stippl.io/
- Airial: Startup Ecosystem Canada, NetInfluencer, Business Wire (2024-12-05). https://www.businesswire.com/news/home/20241205056478/en/
- Curiosio: Travel AI Hub, bestaitools, MakeUseOf. https://www.travelaihub.com/curiosio-review/
- Vacay: Google Play, Futurepedia, tooldirectory. https://play.google.com/store/apps/details?id=com.nasr.vacay
- Holiwise: PhocusWire, EU-Startups (2025-08), Tech Funding News. https://www.eu-startups.com/2025/08/london-based-holiwise-raises-e1-45-million-and-partners-with-industry-leaders-to-reinvent-premium-travel/
- GuideGeek: PR Newswire, Wikipedia, AiThority. https://en.wikipedia.org/wiki/GuideGeek
- Wanderlog pricing and funding (monkeyeatingmango.com July 2026, Tracxn, Latka). https://monkeyeatingmango.com/blog/wanderlog-pricing-2026/
- Stardrift resources pages, 2026. https://stardrift.ai/resources/best-ai-travel-planners
- Trip.com Group newsroom and PhocusWire AI check-in; ITB Berlin coverage (2026-03). https://www.trip.com/newsroom
- Expedia Romie: Hotel Dive, Travel Weekly, PhocusWire, Matador, 2024-05. https://www.hoteldive.com/news/expedia-ai-assistant-romie/716315/
- Expedia newsroom, app in ChatGPT; Skift "ChatGPT Travel Apps Are Now a Thing", 2025-10-06. https://skift.com/2025/10/06/expedia-booking-chatgpt-apps-openai/
- eMarketer, Expedia and Booking.com integrations push ChatGPT deeper into commerce, 2025-10. https://www.emarketer.com/content/expedia-booking-com-integrations-push-chatgpt-deeper-commerce
- Kayak: kayak.com AI Mode news, PR Newswire 2025-10, Globetrender 2025-10-17, AltexSoft, Kayak AI updates page (Ask AI, Apr 2026). https://www.kayak.com/c/kayak-ai-updates/
- Booking.com newsroom AI Trip Planner; OpenAI case study; Booking product blog. https://news.booking.com/bookingcom-launches-new-ai-trip-planner-to-enhance-travel-planning-experience/
- Tripadvisor: media room AI travel planning launch (2023-10), Hotel Dive, tripadvisor.com/ChatGPT, Travel Weekly. https://tripadvisor.mediaroom.com/Tripadvisor-launches-AI-powered-travel-planning-product
- Google: Skift 2026-08-27 and TechCrunch 2026-08-27 on AI Mode flight tracking and agentic hotel booking; Google blog on Canvas travel planning; engine.com and techbuzz.ai summaries. https://skift.com/2026/08/27/googles-agentic-hotel-booking-tool-comes-to-ai-mode/ ; https://blog.google/products-and-platforms/products/search/tips-prompts-ai-mode-canvas-travel-planning/
- OpenAI ChatGPT Group Chats global rollout, 2025-11-20 (TechCrunch, PYMNTS). https://www.techcrunch.com/2025/11/20/chatgpt-launches-group-chats-globally/
- Perplexity, Selfbook and Tripadvisor hotel booking, PhocusWire, 2025-03. https://www.phocuswire.com/perplexity-selfbook-agentic-ai-travel-booking-tripadvisor
- Hallucination coverage: DEV Community, monkeytravel.app "Can you trust an AI travel itinerary", Euronews 2025-03-22, Fox News, AOL "Tourists duped by AI into visiting fake hot springs". https://www.euronews.com/travel/2025/03/22/how-good-is-chatgpt-at-planning-holidays-i-put-it-to-the-test-on-a-weekend-trip-to-tallinn
- Hermi spec: `/home/user/trip-planner/business-plan/app-buildout/README.md`, `.../phase-1-launch/README.md`, 2026-09-30.
