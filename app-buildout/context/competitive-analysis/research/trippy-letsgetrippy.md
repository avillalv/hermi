# Competitor profile: Trippy (letsgetrippy.com)

Research date: 2026-09-30. No repo edits made.

## Read this first: evidence quality

WebFetch was blocked by the network proxy for letsgetrippy.com, apps.apple.com and google.com (EGRESS_BLOCKED). Everything below comes from WebSearch result snippets, so every fact is "reported, verify" unless stated. Nothing was found for ratings, review counts, downloads, TikTok or Instagram following, pricing, funding, or user reviews. Those cells say "not found" rather than being guessed. Do not cite this file externally before the verification list at the bottom is done.

Disambiguation: several unrelated products are called Trippy. The 2011 social travel planner (founder J.R. Johnson, $1.75M seed from Sequoia and True Ventures, $3.5M Series A in 2014, pivoted to travel Q&A) is a different company. Ignore it for this profile. Other look-alikes on the stores (Trippy Travel App id1535706273, Trippy AI Travel Itinerary by Ilyas Belkheiri, Trippy Travel Manager on Google Play) were not confirmed to be the letsgetrippy product. The right listing must be confirmed by opening the site's own store links.

## 1. Identity

| Item | Finding | Status | Source |
|---|---|---|---|
| Site title and tagline | "Trippy, Group Travel, Finally Simple" | reported, verify | WebSearch result title for letsgetrippy.com, 2026-09-30 |
| Sub-line | "100 messages and zero decisions" turned into an organized trip with voting, splitting and AI that reads the chaos | reported, verify | WebSearch snippet, letsgetrippy.com, 2026-09-30 |
| Founders | Baldwin Cunningham and David Matthews (a LinkedIn result titled "David Matthews - Trippy" appeared) | reported, verify (snippet only, could not open a source page) | WebSearch snippets, 2026-09-30 |
| Launch date | Not found. Site states "Now on Android, free to download", implying an Android launch recently before 2026-09-30 | reported, verify | WebSearch snippet |
| Funding | Not found. No Crunchbase, Dealroom or press hit for this Trippy. (Dealroom and TechCrunch hits are the 2011 company.) | not found | searches 2026-09-30 |
| Platforms | Android confirmed by site copy. iOS and web not confirmed | reported, verify | snippet |
| Store ratings and review counts | Not found | not found | |
| Download estimates | Not found | not found | |
| TikTok and Instagram following | Not found | not found | |

## 2. Product and features (as reported)

| Area | Trippy | Status |
|---|---|---|
| Group chat | Real-time chat inside the app | reported, verify |
| Polls and voting | Group voting on destinations and activities | reported, verify |
| Expense splitting | Yes, bundled with voting and chat | reported, verify |
| AI | "Trippy Spark", an AI organizer that reads the group chat and produces a structured plan: dates, accommodation, restaurants, unresolved items, "in seconds" | reported, verify |
| Bookings and import | Positioned as "plan, book, and experience trips"; auto-imports travel plans and booking confirmations, coordinates the crew, surfaces info before, during and after the trip | reported, verify (founder blurb snippet) |
| Itinerary | Implied (structured plan); depth unknown | not found |
| Maps | Not found | not found |
| Offline | Not found | not found |
| Flights and fare tracking | Not found | not found |
| Lodging search and compare | Not found (accommodation appears only as an extracted item from chat) | not found |
| Affiliate or booking revenue | Not found | not found |

## 3. Pricing, business model, users, positioning

| Item | Finding | Status |
|---|---|---|
| Price | "Free to download". No tier table found. | reported, verify |
| Business model | Unknown. Plausible guesses (subscription, AI credits, booking affiliate) are unsupported. | not found |
| Target users | Friend groups stuck in WhatsApp or iMessage threads, Gen Z and millennial group trips | inferred from copy, verify |
| Positioning | "Group travel, finally simple": replaces the chat plus docs plus booking emails stack with one app; hook is the chat-to-plan AI | reported, verify |
| Marketing channels | Not found (TikTok and Instagram handles not located) | not found |

## 4. User praise and complaints

No App Store reviews, Google Play reviews, Reddit threads or TikTok comments about this Trippy were found. Third-party roundups (Tripsil, Weplanify, Jetty) did not list it in the snippets seen. Category-level complaints from the same searches, useful as a proxy for what groups dislike:

| Theme | Evidence | Source |
|---|---|---|
| Wanderlog has no group chat and puts cost splitting behind Pro (about $40 a year) | reported, verify | WebSearch snippet citing tripsil.com / weplanify.com 2026 roundups |
| Splitwise has 50M+ users but no itinerary, polls or packing lists, so groups need a second app | reported, verify | same |

## 5. Weaknesses (inferred, flagged as hypotheses)

| Hypothesis | Basis |
|---|---|
| Very young, tiny footprint: no ratings, reviews or press found | absence of evidence, verify |
| Android first, iOS and web unconfirmed | site copy "Now on Android" |
| No evidence of flight fare tracking, lodging comparison, evidence-linked AI, affiliate layer or offline mode | not found in any snippet |
| AI centered on chat summarization, so value depends on groups actually chatting in app | product design inference |
| Crowded category: Tripeza, TRIPTI.ai, TripLinq, Triplly, TRYPS, Wanderlog all offer vote plus split plus AI | WebSearch 2026-09-30 |
| Name collision with the 2011 Trippy and several store apps hurts search and ASO | confirmed by search results |

## 6. Is this the competitor the Hermi owner means?

The README describes Hermi as a collaborative trip planner for couples, families and friend groups with voting (lodging votes, polls), cost splitting, collaborators, and AI. The user's description of Trippy (group voting, expense splitting, chat, AI turning group chat into a plan) matches letsgetrippy.com's own copy. Likely yes, but the README never names a competitor, so ask the owner to confirm.

## 7. Feature by feature comparison with Hermi

Hermi source: /home/user/trip-planner/business-plan/app-buildout/01-product-spec.md (sections 4.1 to 4.19, tier matrix section 5) and README tier table. Positioning: "Plan together. Know the fare." Platforms: iOS (Capacitor) and web.

| Capability | Trippy (reported) | Hermi (spec) | Edge |
|---|---|---|---|
| Platforms | Android confirmed; iOS and web unknown | iOS and web; no Android | Trippy on Android; Hermi on web |
| Group chat | Yes, core | No chat listed; notes feed (F-NTE-1) and comments only | Trippy |
| Chat to plan AI | Yes, "Trippy Spark", headline feature | No. AI is drafts (F-AI-2), research, agent runs, booking import (F-AI-10) | Trippy |
| Polls and voting | Yes | Polls (F-GRP-1), lodging votes (F-LDG-5), compare | Even; Hermi gates creation to paid or pass for own trip |
| Expense splitting | Yes | Expenses, cost splitting, settlements (F-GRP-2 to 4); Stripe collection in Phase 4 | Even; Hermi deeper later |
| Itinerary and map | Implied | Days, calendar, ideas, place search, MapLibre map (F-ITN) | Hermi (verified by spec) |
| Booking import | Reported auto-import of confirmations | Booking import (F-AI-10, 1 credit), bookmarklet for stays | Even, verify Trippy depth |
| Flights and fare tracking | Not found | Routes, cached and live fares, alerts, agent fare hunts (F-FLT) | Hermi |
| Lodging shortlist and compare | Not found | Shortlist, per-night math, rental search, compare (F-LDG) | Hermi |
| Evidence-linked AI facts | Not found | Source URL on every AI fact (F-AI-5, F-NTE-2) | Hermi |
| Presentation mode | Not found | Full-screen slides (F-PRS) | Hermi |
| Offline | Not found | Offline read (F-TRV-2, 6.2) | Hermi on paper |
| Affiliate and booking revenue | Not found | Labeled affiliate links, concierge, room-block, later LiteAPI | Hermi |
| Checklist and packing list | Not found | F-CHK, F-AI-9 | Hermi |
| Pricing | Free to download; tiers unknown | Free, Plus $5.99 or $39.99, Family $8.99 or $59.99, Pro, passes $9.99 and $19.99, credit packs | Unknown |
| Invitee friction | Unknown | Invitees join free, guest mode (F-ACC-2), share links | Hermi documented |
| Travelers per trip on free | Unknown | Free 2 travelers, invites blocked | Risk for Hermi (see gaps) |

## 8. What Trippy does that Hermi lacks

1. In-app group chat.
2. Chat-to-plan AI that ingests the conversation and lists unresolved decisions.
3. Android app (Hermi is iOS plus web only).
4. Group tools ungated on a free product (as reported; verify). Hermi limits free trips to 2 travelers and hides own-trip polls and expenses behind a preview.

## 9. What Hermi does that Trippy lacks (by current evidence)

1. Flight routes, fare history, live tracking, price alerts, agent fare hunts.
2. Lodging shortlist, per-night math, compare, rental search.
3. Source-cited AI research with evidence rules.
4. Full itinerary, calendar, map, presentation mode, checklist, packing list.
5. Monetization layers: affiliate, concierge, group payments, advisor seats.
6. Data export (JSON, ICS, PDF), in-app account deletion, privacy stance (no ads, no data sales).
All "lacks" for Trippy mean "not found in snippets", not confirmed absent.

## 10. Gaps to exploit and risks

| # | Move | Why |
|---|---|---|
| 1 | Lead with money: "Know the fare". Trippy shows no fare tracking or price intelligence | Hermi's core differentiator |
| 2 | Source-cited AI versus a chat summarizer | Trust story; summaries can hallucinate dates |
| 3 | Win the couple and family personas (P1, P3), not only friend groups | Trippy copy targets chat-heavy friend groups |
| 4 | Web and share-link invitees with no install | Android-first rival; Hermi's read-only links and guest mode help |
| 5 | Planning depth: itinerary, map, presentation, offline | Trippy reads as coordination first, planning second |
| 6 | Privacy and no-ads promise | Unknown for Trippy; cheap to claim |
| Risk A | Hermi has no chat and no chat-to-plan import. Consider a "paste your group chat" AI action (draft_trip from pasted text, 4 credits) as a low-cost answer. Do not build a full messenger | Closes the headline gap |
| Risk B | Free tier caps travelers at 2 and gates collaborators. A free group app would beat Hermi on virality. Consider letting free trip owners invite to polls and splitting | Adoption risk in group use case |
| Risk C | No Android. Friend groups are mixed-device, so one Android member blocks chat-first rivals, but iOS-only hurts Hermi in mixed groups; the web app mitigates | Platform reach |

## 11. Verification checklist (do this from a machine with open internet)

1. Open letsgetrippy.com, capture pricing, FAQ, privacy policy (names the legal entity), footer social links.
2. Follow the store links to the exact listings; record rating, count, version history, in-app purchases, developer name.
3. Check TikTok and Instagram handles for followers and top comments.
4. Search Reddit (r/travel, r/solotravel, r/iOSApps, r/androidapps) and Product Hunt for "Trippy group travel".
5. Check LinkedIn for founders, Crunchbase or YC for funding.
6. Get download estimates from Sensor Tower or AppMagic.

## Sources (all accessed 2026-09-30, via WebSearch snippets; none opened directly)

- https://letsgetrippy.com/ (search result title and snippets only; fetch blocked)
- https://www.linkedin.com/in/j-david-matthews/ (result title "David Matthews - Trippy")
- https://en.wikipedia.org/wiki/Trippy, https://techcrunch.com/2014/04/29/social-travel-planner-trippy-relaunches-as-qa-service-raises-3-5-million-more/ (2011 company, used only to exclude it)
- https://apps.apple.com/us/app/trippy-travel-app/id1535706273, https://apps.apple.com/in/app/trippy-ai-travel-itinerary/id6757307612 (unconfirmed look-alikes)
- https://tripsil.com/5-best-apps-for-group-travel-in-2026-honest-review-no-sponsored-rankings/ and https://www.weplanify.com/en/alternatives/best-group-trip-planner-apps (category context)
- https://tripeza.in/, https://tripti.ai/, https://trip-linq.com/use-cases/friends (other group planners)
- Hermi: /home/user/trip-planner/business-plan/app-buildout/README.md and 01-product-spec.md
