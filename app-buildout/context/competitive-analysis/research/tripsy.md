# Competitor profile: Tripsy (Tripsy: Travel Planner)

Prepared 2026-09-30 for Hermi (specs read: app-buildout/README.md and phase-1-launch/README.md).

## Research limits (read first)

WebFetch was blocked by the network egress proxy for every host tried (tripsy.app, apps.apple.com, wandrly.app, monkeyeatingmango.com, 9to5mac.com). I did not work around the block. Everything below comes from WebSearch result summaries, so **every fact is "reported, verify"** unless a line says otherwise. Sources disagree on price (see the pricing table), so treat those numbers as a range. Reddit threads and full App Store reviews could not be opened; complaint themes come from review aggregators and comparison blogs. Before acting on any number, open the App Store listing and tripsy.help/article/21-whats-the-price-of-premium by hand.

## 1. Snapshot

| Item | Finding | Confidence |
|---|---|---|
| Company | Tripsy, small unfunded company based in Brazil | Reported, verify (Tracxn, BetaList via search) |
| Founders | Rafael K. Streit (iOS developer, co-founder) and Thiago Sanchez. Not "Rafael Conde" | Reported, verify |
| Launch | Founded 2018 (reported); App Store id1429967544 suggests a 2018 listing | Reported, verify |
| Platforms | iPhone, iPad, Mac, Apple Watch; Vision Pro reported by one source. No native Android: Android app on a waitlist as of June 2026. Web is read-only itinerary view | Reported, verify |
| Distribution extras | Also on Setapp (Mac) | Reported, verify |
| App Store rating | 4.7 of 5, about 5.6K ratings (US, iPad listing 5.5K, iPhone listing 4.8K) | Reported, verify (snippet date unknown) |
| Recognition | Apple "Editors' Choice" badge; 2024 App Store Awards iPhone App of the Year finalist. Not a winner (Flighty won the 2023 Apple Design Award for Travel) | Reported, verify |
| Languages | 9 | Reported, verify |
| Latest release | 3.10 on 2026-09-14 (Smart Import, Smart Insights) | Reported, verify |
| Press | MacStories reviews (2.0, 2.10, 2.15), 9to5Mac (2023, 2024), Tools and Toys, YourStory (2022), Sketch blog | Reported, verify |

## 2. Pricing

| Plan | Reported price | Notes |
|---|---|---|
| Free | $0 | Basic trip creation only; most value sits behind Pro |
| Pro weekly | $3.99 | One source only |
| Pro monthly | $9.99 (Adapty and saasgenius style sources); $4.99 (an AI-summary of another source) | Conflict, verify |
| Pro yearly | $59.99 "recommended"; other sources say $39.99 to $59 | Conflict, verify |
| Lifetime | $299 (most sources); $199 and $150 also appear in user complaints | Conflict, likely changed over time, verify |
| Trial | 7 days reported | Verify |
| Free tier limits | Not found in detail. Reviews say trip sharing, cloud sync and collaboration need Pro; Pro adds unlimited trips, documents, expenses, email forwarding, flight alerts, calendar, weather, unlimited guest invites | Reported, verify |

Working assumption for planning: Pro is roughly $40 to $60 a year and $299 lifetime. Hermi Plus at $39.99 a year is at or below that low end.

## 3. Feature list (reported, verify)

| Area | Tripsy |
|---|---|
| Email forwarding import | Yes, Pro. Reported support for 700+ providers including Booking.com and Hotels.com. Automations reported flaky by some users |
| AI: Smart Import (3.10, Pro) | Turns photos, screenshots, documents, saved emails and pasted text into places and reservations; imports Google Maps and Apple Maps lists, travel web pages, public Instagram and TikTok posts. Provider or model not disclosed in anything found |
| AI: Smart Insights (3.10, Pro) | On-device analysis of attached docs and emails (baggage, breakfast, parking, cancellation). Needs Apple Intelligence hardware, so Apple's on-device model, not a cloud model |
| AI: Apple Intelligence, Shortcuts, Intents | Since 3.4 (Tripsy blog) |
| AI: MCP server and CLI (May 2026) | Connect Tripsy to Claude or ChatGPT to create trips, add activities, reorganize by time, location or preference. The AI is the user's own assistant; Tripsy does not pay for inference. Sign in and authorize in about a minute |
| Collaboration and sharing | Pro: unlimited guest invites with edit rights, guests need no Pro. Read-only public web link (hides booking refs and expenses). Reviews conflict; some users say sharing and sync break |
| Maps | Apple Maps points of interest, deep links; map view of activities |
| Offline | Full offline access to itineraries, forwarded emails and documents |
| Flight status | Pro: push alerts for delay, gate, terminal, baggage claim, intensified 48 hours out. Apple Watch and Live Activities for current flight |
| Documents | Yes, Pro, unlimited storage reported |
| Expenses | Yes, Pro |
| Widgets | Interactive Home Screen widgets, Lock Screen complications, watchOS Smart Stack widgets |
| Live Activities | Yes (flight status) |
| Calendar | Calendar integration (Pro) |
| Weather | Forecasts (since 2.15) and time zone support |
| Stats | Not confirmed in anything found; verify |
| Other | Siri Shortcuts, multiwindow iPad, Setapp, customizable overview (2024) |

## 4. Business model and positioning

- Freemium iOS-native app; revenue from Pro subscriptions (weekly, monthly, yearly) plus an expensive lifetime purchase, and Setapp distribution. No ads found. Unfunded, so a small team.
- Target users: Apple-device owners who travel often, want one tidy itinerary with bookings, documents and flight alerts. Overlaps with TripIt and Flighty users.
- Positioning (tagline reported): "organize and find all your trip details". Organizer and companion first, not a fare-finder or group decision tool. In 2026 it leans into "bring your own AI" via MCP, plus on-device AI for privacy.

## 5. What users praise and complain about

| Praise | Complaint |
|---|---|
| Polished native Apple design, widgets, Watch, Live Activities (MacStories "favorite travel app") | Paywall: sharing, sync, collaboration and email forwarding behind Pro; "TripIt lets me share free" |
| Email import covering many providers | Lifetime price seen as steep; subscription fatigue |
| Offline access and documents in one place | Sync problems between Mac and iPhone, cross-device sharing issues |
| Web link for non-traveling family that hides sensitive details | Email automation unreliable; reported hangs and very slow saves on some builds |
| Frequent updates, responsive small team | No Android; web is view-only; one source claims only one person can view or add on their phone without Pro |

Sources for this table are aggregator and blog summaries (justuseapp, wandrly, setapp reviews, FlyerTalk snippet). Reddit was not reachable: **no Reddit evidence collected**. Do a manual pass on r/travel, r/iosapps, r/TripIt before quoting.

## 6. Weaknesses (summary)

1. Apple only: no editing on Android or web; group trips break when one friend is on Android.
2. Collaboration is paid and planning is single-author oriented: no voting, polls, hearts or comments reported.
3. No fare search, price history, price alerts or booked-fare drop alert reported.
4. No stays comparison or shortlist voting; no presentation mode.
5. AI is import and assistant plumbing, not research with citations; Smart Insights needs Apple Intelligence hardware.
6. Pricing is confusing (weekly, monthly, yearly, lifetime at about $299) and the free tier is thin.
7. Reliability complaints (sync, email automation, slow saves).

## 7. Feature by feature versus Hermi

Hermi Phase 1 scope from phase-1-launch/README.md; later items from app-buildout/README.md tier table and phase lists.

| Capability | Tripsy | Hermi | Edge |
|---|---|---|---|
| Platforms | iPhone, iPad, Mac, Watch; web view-only | iOS (Capacitor) and full web app P1; native Android P2; no Mac or Watch app | Tripsy on Apple breadth; Hermi on cross-platform editing |
| Native feel, widgets, Live Activities, Watch | Strong | Not in P1 (Capacitor shell) | Tripsy |
| Email forwarding import | Yes, 700+ providers, Pro | Pasted-confirmation import (Haiku) and calendar feed import P1; plans@hermi.world forward P2 | Tripsy until P2 |
| Switching from TripIt or Wanderlog | Not a focus | TripIt and iCal import, free Trip Pass for first import | Hermi |
| AI import | Smart Import (photos, Maps lists, Instagram, TikTok) | Booking paste import; no screenshot or social import in P1 | Tripsy |
| AI research and drafting | MCP only (user's own Claude or ChatGPT); on-device insights | explain, draft_day, draft_trip, research, agent fare hunts, every fact cited with source and date (Claude Haiku 4.5, Sonnet 5.5) | Hermi |
| Flights: fares, history, alerts | Status alerts only | Cached and live fares, price history, alerts, booked-fare drop alert P1; status alerts P2 | Hermi on fares; Tripsy on status until P2 |
| Stays | Reservation storage | Shortlist, paste links, hearts, compare, rental search, partner booking | Hermi |
| Collaboration | Pro only, guest edit, read-only web link | Free owners invite 1 collaborator; Plus and pass up to 6; roles; hearts; activity log; polls, cost split, comments P2 | Hermi, especially free couples |
| Expenses | Yes (Pro) | Manual cost splitting P2, Stripe group payments P3 | Tripsy until P2 |
| Documents | Yes (Pro) | Not listed as P1 feature; verify | Tripsy |
| Maps and itinerary | Apple Maps, day agenda | Day-by-day drag and drop, MapLibre map, places search | Even |
| Presentation and PDF | Itinerary web link | Full-screen presentation, read-only link, PDF export | Hermi |
| Offline | Full | Readable offline on every tier, edits queue | Even |
| Calendar | Calendar sync (Pro) | Live calendar subscription feed per trip | Even |
| Before you go | Weather | Visa links first, partner items, checklist | Hermi |
| Stats | Unconfirmed | "Year in travel" card P2 | Unknown |
| Pricing | About $40 to $60 a year, $299 lifetime | Plus $5.99 a month or $39.99 a year; Trip Pass $9.99; no lifetime | Hermi on entry price and pass option |
| Free tier | Thin | 2 trips, 12 credits, offline, joins free | Hermi |

## 8. Summary lists

**What Tripsy does better**
- Native Apple polish: widgets, Live Activities, Watch, Mac, Setapp, Siri Shortcuts.
- Email forwarding with 700+ providers today, and screenshot, Maps-list and social import.
- Flight status alerts and documents and expenses already shipped.
- Brand trust: Editors' Choice, MacStories coverage, about 5.6K ratings at 4.7.
- MCP and CLI make it the easy target for power users who live in Claude or ChatGPT.

**What Hermi does better**
- Fare hunting with price history, alerts and booked-fare drop alert; AI research with visible sources.
- Real group planning: hearts now, polls and cost split later, collaboration free for couples.
- Cross-platform: full web editing now, Android in P2.
- Lower and simpler pricing, Trip Pass for one-off trips, honest free tier, no subscription lock on exports.
- Presentation mode, PDF export, TripIt and Wanderlog switching path.

**What Tripsy lacks**
- Android and editable web; free collaboration; voting; fare search and price tracking; stay comparison; presentation mode; cited AI research; any shared-credit AI model of its own (it relies on the user's chatbot and Apple on-device AI).

**Ideas to beat it and win its users**
1. Build a "Switching from Tripsy" import (Tripsy has a CLI and MCP, so a CLI or export script route is plausible; verify export format) and add it to onboarding next to TripIt and Wanderlog, with the free Trip Pass reward. Publish a `/vs/tripsy` page stating facts only.
2. Pull email-forward import earlier than P2, or at least ship a share-sheet and "paste or drop a screenshot" flow in P1 to close the Smart Import gap.
3. Pitch the gap Tripsy cannot fill: "Your friends are on Android, plan together anyway." Lead marketing and App Store copy with cross-platform free collaboration.
4. Publish a Hermi MCP server (or Claude connector) in Phase 2 so the Claude-native crowd is not exclusive to Tripsy, and because it costs no inference.
5. Price comparison content: Plus $39.99 a year with fares and AI versus Tripsy Pro at about $40 to $60 without fares; Trip Pass $9.99 beats a year of Pro for one trip. Never offer lifetime (consistent with Hermi rules), and use that as a trust message against the $299 lifetime.
6. Close the native gaps cheaply: Live Activity and widget for flights and next item in Phase 2, then Apple Watch only if retention data asks for it.
7. Cover reliability as a feature: sync test suite and a public "edits never lost" promise, because sync and slow-save complaints are Tripsy's most repeated pain.
8. Add documents (attach PDFs and confirmations per item) to Phase 1 or early Phase 2 if not already specified; it is a Pro anchor for Tripsy.

## 9. Sources (all via WebSearch snippets, retrieved 2026-09-30; none opened directly)

- App Store listing: https://apps.apple.com/us/app/tripsy-travel-planner/id1429967544 (rating 4.7, 5.6K, Editors' Choice)
- Tripsy site, updates and blog: https://tripsy.app/ , https://tripsy.app/updates , https://tripsy.blog/ , https://tripsy.blog/tripsy-3-10-set-your-travel-inspiration-free/ , https://tripsy.blog/plan-smarter-trips-with-tripsy-and-claude-or-chatgpt/
- Tripsy support price article: https://tripsy.help/article/21-whats-the-price-of-premium ; Android/web help: https://tripsy.help/article/43-how-to-open-the-itinerary-on-android-or-web-without-having-the-app-installed
- Tripsy 3.10 (2026-09): https://alternativeto.net/news/2026/9/tripsy-3-10-brings-ai-powered-travel-planning-features-smart-import-and-smart-insights/
- MCP and CLI (2026-05): https://alternativeto.net/news/2026/5/tripsy-adds-mcp-integration-and-cli-support-for-ai-powered-travel-planning-and-organization/ , https://dev.to/kahwee/tripsy-now-has-a-cli-and-an-mcp-1ne4
- Android waitlist (June 2026): https://tripsy.app/android
- Apple 2024 finalists: https://www.apple.com/newsroom/2024/11/apple-reveals-45-app-and-game-finalists-for-the-2024-app-store-awards/
- MacStories: https://www.macstories.net/reviews/tripsy-review-the-ultimate-trip-planner-for-iphone-and-ipad/
- 9to5Mac: https://9to5mac.com/2024/10/02/tripsy-travel-planner/ , https://9to5mac.com/2023/09/22/tripsy-travel-planner-app-update/
- Company: https://tracxn.com/d/companies/tripsy/__nk5ScB2m3bIuLbcUqfqa5pwIdmvot5jSlcvIfC1107w , https://rafaelks.com/ , https://www.sketch.com/blog/tripsy/
- Reviews and comparisons (third party, treat with care, some look AI-generated): https://www.wandrly.app/reviews/tripsy , https://justuseapp.com/en/app/1429967544/tripsy/reviews , https://setapp.com/apps/tripsy/customer-reviews , https://adapty.io/paywall-library/tripsy/ , https://tripstone.app/blog/tripsy-alternatives , https://monkeyeatingmango.com/blog/monkeyeatingmango-vs-tripsy/
