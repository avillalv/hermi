# Hermi competitive landscape and switching plan

Research date: 2026-09-30. No repo files were edited. Method: WebSearch snippets only. Direct fetches of apps.apple.com, tripit.com, wanderlog.com, jointrippy.com, trippyapp.app and endlesstravelplans.com were blocked by the sandbox proxy, so nearly every competitor fact below is "reported, verify" (R/V). Many of the sources are third-party review and SEO blogs, which are weak evidence; vendor pages should be read before anything is quoted externally. This is strategy, not legal advice.

Hermi facts come from business-plan/app-buildout/README.md, business-plan/02-pricing-tiers.md, business-plan/08-affiliate-revenue.md and app-buildout/01-product-spec.md (as specified, not as built; the app is still a spec).

## 1. Which "Trippy" is it?

There is no single dominant Trippy. Searches (2026-09-30) show at least five unrelated products using the name, none with visible scale. All facts are R/V.

| Product | What it is | Scale signal | Threat to Hermi |
|---|---|---|---|
| Trippy (jointrippy.com) "The Travel Super App" | Group trips, shared itineraries, sync with your crew; iOS and Android | Not found | Medium in concept, low in evidence |
| Trippy (letsgetrippy.com) "Group Travel, Finally Simple" | Group voting, expense splitting, real-time trip chat, "Trippy Spark" AI that turns a group chat into a structured plan | Not found | Closest to Hermi's group pitch; the one to watch |
| Trippy (trippy.global) | AI itinerary generator "inspired by music playlists" | Not found | Low |
| Trippy - Travel App (App Store id1535706273) | Small indie app, reported 2.0 stars on 4 reviews, last update reported 2022-08-18, likely abandoned | Tiny | None |
| Trippy - Travel Manager (Google Play) | Trip organizer, reported 500+ downloads | Tiny | None |
| trippy.com (2011, J.R. Johnson) | Friend-sourced travel recommendations, later road trip planner | Legacy brand, reported | Low; SEO pages (trippy.com/drive) still exist |

Conclusion: the owner's fear is probably about TripIt (brand and scale) or Wanderlog (the real feature overlap), not any Trippy. The competitor that matters most is Wanderlog for planning, TripIt for email import and alerts, Google and Mindtrip for AI, Hopper and Google for fare prediction. Recommend confirming with the owner which product they meant (voice dictation). The letsgetrippy.com product is the only Trippy worth a monthly check, because Trippy Spark (group chat to plan) attacks the same organizer persona as Hermi's Group Trip Pass.

## 2. Feature comparison matrix

Legend: Y yes, N no, P partial, ? unknown or not found, R/V reported, verify. Hermi column = as specified. "Trippy" = letsgetrippy.com / jointrippy.com claims (R/V, no pricing found). Prices are US.

### 2.1 Planning and collaboration

| Feature | Hermi (spec) | Trippy | TripIt / Pro | Wanderlog | Layla | Mindtrip | Hopper | Google Travel / Flights / Maps | Kayak Trips | Splitwise | Troupe | Lambus |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Collaborative planning and voting | Y: shared edits, hearts on stays, polls; polling every 15 to 30 s, no real-time edit | Y: voting, chat (R/V) | P: traveler, planner, viewer roles; no co-planning of itinerary (R/V) | Y: real-time co-edit, edit or view permissions (R/V) | P: share in paid tier (R/V) | Y: shared itineraries, chat, comments (R/V) | N | P: Maps lists can be made collaborative, often buggy (R/V) | N | N | Y: polls, ranked-choice voting, RSVPs (R/V) | Y: shared trip (R/V) |
| Roles | Y: owner, editor, viewer | ? | Y: traveler, planner, viewer (R/V) | Y: edit or view (R/V) | ? | ? | N | P | N | N | ? | ? |
| Group polls | Y: 2 to 12 options, dates, stays, ideas; paid tiers or trips that have them | Y (R/V) | N | P: hearts and votes on places (R/V) | N | P: comments | N | N | N | N | Y: core product, advanced polling in premium (R/V) | ? |
| Day-by-day itinerary with map | Y: drag calendar, MapLibre, ideas list | P (R/V) | P: timeline, not a planner (R/V) | Y: best in class, route optimization in Pro (R/V) | Y: AI drafted (R/V) | Y: chat built (R/V) | N | P: Maps lists, no day plan | P | N | N: "no itinerary building" (R/V) | Y (R/V) |
| Lodging shortlist and comparison | Y: shortlist, hearts, 2 to 4 compare, per night and per person | P: voting | N | P: places list, no side-by-side (R/V) | N | P | P: hotel watch | P: Google Hotels | P | N | P: share Vrbo or Airbnb, vote (R/V) | N |
| Presentation or share mode | Y: full-screen slides, PDF, read-only share link | ? | P: sharing | P: share link, public pages | P: PDF and share in paid tier (R/V) | P | N | P: list links | P | N | N | P |
| Pre-trip checklist | Y: "Before you go", 11 groups, half unmonetized | ? | P: documents storage, Pro 25 docs per trip (R/V) | P: checklists (R/V) | N | N | N | N | N | N | N | P |
| After-trip memories | P: delay prompt, "How was the trip?" card, archive, duplicate; no photos or journal | ? | N | P: journal feature added, weak (R/V) | N | N | N | P: Google Photos | N | N | N | Y: photos and notes (R/V) |

### 2.2 Flights, fares and AI

| Feature | Hermi (spec) | Trippy | TripIt / Pro | Wanderlog | Layla | Mindtrip | Hopper | Google Travel / Flights | Kayak Trips | Splitwise | Troupe | Lambus |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Flight price tracking and alerts | Y: cached fares free, 1 alert; live daily checks on paid, 120 day window | N | P: Pro monitors fare on booked flights for refunds and price drops (R/V) | P: Pro price-drop alerts (R/V) | P: PriceLock in premium (R/V) | ? | Y: core; predictions, Watch a Trip, Price Freeze $52 to $57 (R/V) | Y: Flights tracking; AI Mode tracking in 180 plus countries, Aug 2026 (R/V) | Y: price alerts | N | N | N |
| Fare evidence with sources | Y: each AI fare needs source URL, date seen, "Indicative" label; cached fares show age | N | N | N | N | N | N: prediction claims only | P: shows partner list | N | N | N | N |
| AI planner | Y: draft day (1 credit), draft trip (4) | Y: Trippy Spark (R/V) | N: "lacks AI" (R/V) | Y: 5 free AI messages per trip, unlimited in Pro (R/V) | Y: core product, free chat | Y: core, free | P | Y: AI Mode, Gemini in Maps | Y: Ask AI | N | N | N |
| Autonomous AI agents | Y: fare hunt and deep research runs, 40 credits, caps, scheduled routines in Pro later | N | N | N | N | P: chat plus booking | N | P: AI Mode agentic hotel booking (R/V) | P: AI planner (R/V) | N | N | N |
| Email and booking import | P: paste text, 1 credit; no forwarding address, no inbox sync (F-AI-10) | ? | Y: forward to plans@tripit.com free; Inbox Sync Gmail, Outlook, Yahoo (R/V) | Y: forward or Gmail connect, auto scan Pro only (R/V) | N | P: receipts function (R/V) | N | Y: Gmail reservations into Maps "Your trips" (R/V) | ? (unverified) | N | N | P |
| Offline | P: read last 30 days, up to 10 trips, write queue phase 2; no offline maps | ? | Y: offline itinerary (R/V) | P: Pro only, contested (R/V) | N | N | N | P: Maps offline areas | P | N | N | Y: full offline (R/V) |

### 2.3 Money

| Feature | Hermi (spec) | Trippy | TripIt / Pro | Wanderlog | Layla | Mindtrip | Hopper | Google | Kayak Trips | Splitwise | Troupe | Lambus |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Budget and cost splitting | Y: expenses, 4 split modes, ECB FX, minimized transfers; manual settle; Stripe collection later (group_trip_pass, pro) | Y (R/V) | N | Y: built in splitter (R/V) | N | N | N | N | N | Y: the category leader, limits free to about 3 to 5 expenses a day (R/V) | N | Y: expenses and splitting (R/V) |
| Pricing | Free; Plus $5.99/mo or $39.99/yr; Family $59.99/yr; Trip Pass $9.99 (90 days); Group Trip Pass $19.99; credit packs | Not found | Pro $49/yr, 30 day trial (R/V, vendor page cited by third party, checked 2026-08-24) | Pro $39.99/yr (was $49.99), $5.99/mo (R/V) | Premium $49.99/yr or $9.99/mo iOS (R/V) | No consumer sub found; earns on bookings (R/V) | Free; fees for Price Freeze and protections | Free | Free | Pro about $39.99 to $49.99/yr, $4.99/mo (R/V) | Free, premium adds advanced polling (R/V) | Monthly $3.99, yearly $24.49, pay per trip $8.99, lifetime $89.99 (R/V) |
| Free tier | Generous: 2 trips, cached fares, itinerary, lodging, checklist, 12 credits, one deep-run taster, joins trips free | ? | Yes: import and itinerary | Yes: planning, budget, collab | Yes: chat and plan | Yes: all core | Yes | Yes | Yes | Yes with daily cap | Yes | Limited |
| Ads | None, never | ? | None reported | Not verified | None | None | Promotions inside app | Yes (Google) | Yes | Ads on free (R/V) | ? | ? |
| Affiliate or booking revenue | Labeled affiliate links on all tiers, never ranks by commission; concierge later | ? | Affiliate via Concur ecosystem; not verified | Affiliate with Expedia, Booking, Viator (R/V) | Booking partners, now Expedia-owned (R/V) | In-app booking via Sabre, Priceline, Viator, Tripadvisor (R/V) | Commission plus add-ons | Partner listings | Metasearch click fees | Subscription | Vrbo integration (R/V) | Subscription |

## 3. Where Hermi wins, ties, or trails

Honest read. "Wins" means a spec-level difference that the evidence suggests no competitor offers. All of it is unbuilt, so each win is a promise until shipped.

### Clearly better (defensible)
1. **Fare evidence.** Source URL, date seen, "Indicative" label, rejected-items view. No competitor found does this. It answers the core complaint about price predictors and AI answers that cannot be checked. This is the one feature that can carry the tagline "Know the fare."
2. **Group decision tools bundled with a real itinerary and fares.** Troupe has polls but no itinerary or expenses (R/V). Wanderlog has itinerary and splitting but weak decisions (hearts, comments). Hermi has polls, lodging votes, compare, expenses, itinerary, and fares in one. Nobody else found ties all of these.
3. **Pricing shape.** Free invitees, $9.99 Trip Pass and $19.99 one-fee Group Trip Pass fit episodic travel better than $40 to $50 annual-only rivals. Only Lambus (pay per trip $8.99) has a comparable pass.
4. **Trust posture.** No ads, no ranking by commission, disclosure on every link, export on every tier, nothing locked on downgrade. Wanderlog gets public backlash for paywalling offline, dark mode, Google Maps export (R/V).
5. **Presentation mode.** Full-screen walkthrough for deciding together. No close equivalent found.
6. **Bounded agents.** Autonomous fare hunting with hard caps and cost shown first is ahead of the market. Google's AI Mode tracking and hotel booking (Aug 2026) is broader but is not evidence-first.

### At parity
Day-by-day itinerary with map (Wanderlog is still the benchmark and ahead on polish), AI drafting (every AI planner does this; nobody pays for it alone), cost splitting (Wanderlog and Lambus have it; Splitwise is deeper), roles and invites, flight alerts on cached fares (Google is free and broader), checklists.

### Behind (be candid)
1. **Email and booking import.** TripIt forwards and syncs Gmail, Outlook and Yahoo automatically; Wanderlog does Gmail; Google does it in Maps. Hermi is paste-and-parse at 1 credit, no forwarding address, no inbox sync. This is the largest functional gap and the biggest blocker to switching.
2. **Real-time alerts during travel.** TripIt Pro's gate, delay, seat and refund alerts. Hermi has none.
3. **Brand, distribution, data.** Wanderlog reports 7.9M web visits in May 2026 (Similarweb via search snippet), 4.9 stars on about 36K ratings, organic SEO as top channel (R/V). TripIt sits inside SAP Concur. Hopper reports 100 million plus downloads (R/V). Google and Expedia (owns Layla since 2026-07-31, R/V) hold supply and first-party data. Hermi has zero users, a cached-fare source (Travelpayouts) and SerpApi with unverified terms and cost.
4. **Offline.** Hermi is read-mostly, no offline maps, write queue is phase 2. Lambus and TripIt have fuller offline.
5. **Live fare tracking depends on SerpApi**, flagged as legal risk in the plan, with cost unverified. Google and Hopper own real fare data.
6. **No memories product.** Polarsteps, Lambus and even Wanderlog journal beat a delay prompt and a review card. The user asked for "after-trip memories"; Hermi's spec does not include photos, journals or recaps.
7. **Android and real-time co-editing.** Android is later; co-editing is 15 to 30 second polling. Wanderlog feels live.
8. **Price.** Plus $39.99 matches Wanderlog but charges for things Wanderlog gives away on free (collaboration invites need a paid owner). Free owners cannot invite, which is the main friction versus Wanderlog, Mindtrip and Troupe. See move 3 below.

## 4. Growth tactics competitors use

| Tactic | Who, evidence (all R/V) | Copy, counter, or skip |
|---|---|---|
| Programmatic SEO from public trips and guides | Wanderlog: organic is top source, 45.9% of desktop visits, public itineraries form long-tail keyword base. Trippy.com road trip pages. Mindtrip bought Thatch (creator guides), 2025-03-12 | Copy, but smaller. Publish "sample trips" that show fare evidence ("What a Lisbon week cost, with sources") from shared research cache. Do not scrape Google or copy Wanderlog text. |
| App Store optimization | Wanderlog ranks about #59 in Travel, Editors' Choice, 4.9 stars. Keywords: trip planner, itinerary, travel planner, group | Title: "Hermi: Group Trip Planner". Keyword field: trip planner, group travel, itinerary, flight tracker, split costs, vote. Do not put competitor trademarks in name, subtitle or keyword field (App Store Review Guideline 2.3.7). |
| Referral loops | Wanderlog: invite co-planners is the loop; reported 18% repeat referral growth, and a 2024 "Year in Travel" share campaign with a 15% new-user lift (snippet-level, verify). No paid referral program found. | Copy the invite loop (already in spec). Add a shareable "Year in Travel" card (spec has none). The spec's 20 credits both-sides referral is marked "later"; pull it forward only if invite conversion is weak. |
| Creator partnerships | Mindtrip (Thatch creators, Instagram/TikTok/YouTube link saving). Airbnb Creators invite only. | Copy in small form: creators build a public sample trip in Hermi, Trip Pass credits and affiliate share. Needs FTC disclosure by the creator. |
| Import from other apps | Wanderlog: paste any link, Gmail, forward email. Layla and Mindtrip import social saves. TripIt has ICS calendar export and community tools (tripit-exporter, tripit-export to JSON or CSV, Trip Exporter). | Copy. See 4.1. |
| Switching incentives | Lambus and Wanderlog run sales; no clear switching offers found | Copy: import plus a free Trip Pass for the first imported trip (cost about $0.58 to $0.84 of provider spend, plan section 5.3). |
| Pricing undercuts | Wanderlog cut Pro to $39.99 (from $49.99) in 2026 (R/V). TripIt $49. Layla $49.99. Lambus $24.49 and $8.99 per trip. Splitwise about $40. | Do not undercut on annual; Plus annual already sits at the bottom of the band and the plan shows a 13% loss at $29.99. Undercut on shape: Trip Pass $9.99 and Group Trip Pass vs $40 to $50 annual. |
| Free AI as hook | Layla and Mindtrip give AI planning free | Counter with the fare-evidence taster; do not match free unlimited AI (cost structure does not allow it). |

### 4.1 Can Hermi import TripIt or Wanderlog trips?

Verified in snippets, verify on vendor pages before building:
- **TripIt:** one-trip calendar export (ICS file, one time, no sync) and a calendar feed limited to the last 90 days exist (R/V). Third-party tools export all trips to JSON, CSV or ICS (tripit-exporter, tripit-export, Trip Exporter). No official full-account export found. Email forwarding is to TripIt, not from it.
- **Wanderlog:** Pro exports places to Google Maps (R/V). No official JSON or bulk export found. Gmail and email forwarding are import paths, not export paths.
- **No evidence either product offers a public API for partners.** Do not build against a private or unofficial API; terms risk.

Feasible Hermi import paths, cheapest first:
1. **ICS import.** Accept a TripIt or any calendar .ics (file or URL pasted by the user). Parse flights, hotels, activities into a trip. Zero partner terms risk, works for TripIt single-trip export and feed. Add to spec as F-AI-10b, non-AI, free, no credits.
2. **Forwarding address** (for example plans@hermi.world). Users forward confirmations; Haiku parser already specified in F-AI-10, placeholders for personal data. Reuses the same parser. This mirrors TripIt's habit, so it is the natural "switch" step: "Forward the confirmation emails you already sent to TripIt."
3. **Google Maps saved list link or Takeout CSV.** Covers Wanderlog users who exported to Google Maps, and many planners. Import as saved places.
4. **Share link paste.** A user pastes a public Wanderlog or TripIt share URL. Only if the user's browser extension or bookmarklet reads the open page (same pattern as F-LDG-2). The server must not fetch it, in line with the project's scraping rules. Skip unless legal review passes.
5. **Inbox sync (Gmail and Outlook OAuth).** Matches TripIt and Wanderlog. Heavy: restricted Google scope needs security assessment (CASA), and users call the permission invasive (R/V). Defer to post-launch.

## 5. Plan: win users from the main competitor

Main competitor: the product the owner meant is unconfirmed. Plan assumes TripIt and Wanderlog as the pair (TripIt users want collaboration and AI; Wanderlog users hit paywalls). The same structure works against letsgetrippy.com Trippy. Assumptions are flagged.

### 5.1 Positioning and messaging

| Audience | Pain (R/V) | Message |
|---|---|---|
| TripIt users, couples and families | View-only sharing, no planning, no AI, $49 for alerts, feels dated | "Keep your TripIt emails. Plan the trip together. Hermi reads what you forward and adds the fare check TripIt does not show." |
| Wanderlog users | Paywalls on offline, dark mode, export; Gmail permission feels invasive; sync duplicates notes | "Nothing you need to plan is locked. Invite your group, vote, and see where every fare came from." (only true if the spec's free owner invite gap is closed; see move 3) |
| Group organizers (Trippy, Troupe) | Decision by attrition, Splitwise plus WhatsApp plus Doodle | "Poll, vote, split costs and plan the days in one place. One $19.99 pass covers up to 12 travelers." |
| Fare watchers (Hopper, Google) | Predictions with no proof | "Know the fare. Every price shows its source and age." |

Tone rules from the spec apply: no fake urgency, plain sentence case, no em dashes.

### 5.2 "Switch in one tap" import (product)

- Onboarding screen: "Coming from TripIt or Wanderlog?" with three buttons: Upload .ics, Forward your emails, Import a Google Maps list.
- Result screen lists what was found and lets the user accept item by item (matches F-AI-10 accept-before-save).
- After a successful import: no paywall. Offer a free Trip Pass on that trip (cost to Hermi low; decide after A/B).
- Do not promise "all your data moves over". TripIt and Wanderlog expose limited export; say what moves (dates, flights, stays, places).
- Do not use login credentials of another app (terms and security risk). Never ask for a TripIt or Wanderlog password.

### 5.3 Comparison landing pages: legal limits

United States, from FTC policy and trademark doctrine (snippets, not legal advice; have counsel review before launch):
- **Truthful and substantiated.** FTC encourages naming competitors but requires every claim be accurate and substantiated before publication. Keep a dated evidence file for each row (screenshot of vendor page, plan, price).
- **Nominative fair use.** Use the competitor's name in plain text only to refer to it. No logos, no mimicry of their trade dress, no implied endorsement or affiliation.
- **Avoid unverifiable superlatives** ("better than", "the best") without proof. Prefer factual table rows with "as of <date>".
- **Date and source every claim.** Prices change weekly (Wanderlog moved from $49.99 to $39.99 this year, R/V). Add an update process and a correction email.
- **Do not claim competitor defects from Reddit anecdotes** unless verified.
- **Disparagement and false statements** expose Hermi to Lanham Act false advertising claims. Word carefully: "TripIt shares trips view-only per its help pages" not "TripIt cannot collaborate".
- **UK, EU:** comparative advertising is allowed if objective, verifiable, compares like with like and does not take unfair advantage of a mark (Misleading and Comparative Advertising rules; ASA and CMA for UK). Recheck before launching there.
- **Domain and page names:** do not register domains containing a competitor mark (tripit-alternative style domains are a cybersquatting and confusion risk). Use hermi.world/vs/tripit style paths.
- **SEO pages:** keep one page per competitor with the same template, a neutral verdict, and a "where they are better" section. That honesty is also a conversion and trust asset.

### 5.4 App Store search ads on competitor names: rules

- **Apple Ads (Apple Search Ads) allows bidding on competitor brand keywords** (R/V from ASO and ads agency sources; confirm against Apple Ads policies before launch).
- **App Store Review Guideline 2.3.7** prohibits trademarked terms and competitor names in your app name, subtitle, keyword field and metadata. Bid on names; never list them in metadata.
- **Ad creative:** do not use the competitor's name or logo in your creative. Use a Custom Product Page framed as "Group trip planner with fare sources".
- **Expect trademark complaints occasionally;** a competitor can file a claim with Apple (R/V). Keep creative clean to win any dispute.
- **Structure:** exact-match ad group per competitor, separate campaign, cap daily budget. Reported industry finding: most competitor keyword campaigns lose money (RocketShip HQ, R/V), so treat as a test with a hard stop: pause if cost per install exceeds the trial or Trip Pass payback.
- **Privacy:** the plan uses no ad or attribution SDK. Apple Ads attribution via AdServices is first party, but check it against the plan's "no ATT prompt" rule before enabling.
- **Do not** bid on competitor names for Google web ads without checking each competitor's trademark policy; Google's policy on third-party trademarks in ad text is stricter than keyword use.

### 5.5 Reddit and TikTok

| Channel | Approach | Rules and risks |
|---|---|---|
| Reddit (r/travel, r/solotravel, r/TravelHacks, r/digitalnomad, r/tripit) | Answer real planning questions with help first; share a free sample trip or a fare-evidence walkthrough. Founder account, disclosed. | Each subreddit sets its own rule; many ban product links or confine them to weekly threads. The "90/10" guideline is widely cited (R/V). Read rules of each sub and message moderators for permission. Never astroturf or use undisclosed accounts. |
| TikTok and Reels | Short demos: "I forwarded 6 emails and my trip built itself", "Who owes who after a 10-person ski trip", "How I checked a fare's source". UGC creators on Collabstr-type marketplaces. | Creators must disclose paid partnerships (FTC). No competitor logos in video; do not show a competitor UI in a way that implies endorsement. Budget test before scale. |
| Group-chat virality | The invite link is the channel: invitees join free, see the trip, vote. | Already in spec. Track invite to join to create-own-trip rates. |
| Comparison and "alternative" SEO | "TripIt alternative for groups", "Wanderlog free alternative" as honest pages (5.3). Both query families already have many small competitors writing them (Tineo, Tripstone, WePlanify, Plot a Trip, Tripsil, TripProf and others, R/V). | Crowded. Win with real data (fare evidence, real costs), not keywords alone. |

### 5.6 Sequencing

1. Before launch: ICS import, forwarding address, free-owner invite decision, three comparison pages with evidence files, counsel review.
2. Launch month: Reddit helpful posting, 5 to 10 creators, Apple Ads test with cap.
3. Month 3: measure invite conversion, import completion, Trip Pass redemption, cost per paying user; drop what fails.

## 6. Open items and risks

- **Confirm which "Trippy".** If the owner means letsgetrippy.com, revisit group features (Trippy Spark chat-to-plan, real-time chat) which Hermi lacks; if TripIt, email import and alerts dominate.
- **Free owner cannot invite** (F-COL-3) is the single biggest spec conflict with switching from Wanderlog, Mindtrip or Troupe, where free collaboration is normal. Options: free owners may invite 1 person per trip, or make Trip Pass a one-tap purchase inside the invite moment as specced but test both.
- **Offline is thin** for a product positioned as a travel companion.
- **No memories feature.** Either cut it from the marketing claims or add a minimal photo recap (phase 3).
- **SerpApi legal and cost risk** underpins the "Know the fare" claim. Do not make live-fare comparison ads until a licensed source is in place.
- **All competitor facts are snippet-level.** Re-verify every price and feature on vendor pages (especially TripIt pricing, Wanderlog Pro price, Trippy identity) before any public comparison.

## 7. Sources (accessed 2026-09-30, via WebSearch snippets unless noted)

- Trippy: https://www.jointrippy.com/ , https://letsgetrippy.com/ , https://www.trippy.global/ , https://apps.apple.com/us/app/trippy-travel-app/id1535706273 , https://en.wikipedia.org/wiki/Trippy , https://www.trippy.com/drive/
- TripIt pricing and features: https://www.tripit.com/web/pro/pricing (third-party citation, checked 2026-08-24), https://monkeyeatingmango.com/blog/tripit-pricing-2026/ , https://www.going.com/guides/tripit-review , https://www.tripit.com/web/blog/news-culture/automate-your-tripit-itineraries-inbox-sync , https://www.tripit.com/web/blog/news-culture/5-easy-ways-share-travel-plans , https://help.tripit.com/en/support/solutions/articles/103000063293-export-an-individual-trip-to-your-calendar , https://github.com/aaronspruit/tripit-exporter , https://github.com/jschnurr/tripit-export , https://www.tripexporter.com/
- TripIt complaints and alternatives: https://www.usecarly.com/blog/tripit-alternative/ , https://tripstone.app/blog/tripit-alternatives
- Wanderlog: https://tripstone.app/blog/wanderlog-pro-cost , https://tripstone.app/blog/wanderlog-review , https://stardrift.ai/resources/wanderlog , https://monkeyeatingmango.com/blog/wanderlog-pricing-2026/ , https://www.similarweb.com/website/wanderlog.com/ , https://businessmodelcanvastemplate.com/blogs/growth-strategy/wanderlog-growth-strategy , https://apps.apple.com/us/app/wanderlog-travel-planner/id1476732439
- Layla: https://layla.ai/ , https://monkeyeatingmango.com/blog/layla-review-2026/ , https://skift.com/2026/07/31/expedia-acquired-ai-trip-planner-layla-exclusive/ , https://thepaypers.com/mergers-aquisitions-and-investments/news/expedia-group-acquires-ai-trip-planner-layla
- Mindtrip: https://www.lindy.ai/blog/trip-planner-app , https://www.phocuswire.com/mindtrip-thatch-merge-ai-travel-planning-creators , https://pitchbook.com/profiles/company/535220-74
- Hopper: https://www.travelaiagent.com/products/hopper-travel , https://www.pilotplans.com/blog/hopper-review , https://gizmodo.com/download/hopper-hotels-flights-cars
- Google: https://9to5google.com/2026/08/27/google-ai-mode-flights/ , https://skift.com/2026/08/27/googles-agentic-hotel-booking-tool-comes-to-ai-mode/ , https://blog.google/products-and-platforms/products/search/book-travel-ai-mode/ , https://tineo.ai/blog/google-trips-shutdown-best-alternatives/
- Kayak: https://www.kayak.com/news/ask-ai/ , https://www.travelpulse.com/news/technology/kayak-launches-ai-trip-planner-that-works-like-a-conversation
- Splitwise: https://split-circle.com/en/blog/splitwise-free-vs-pro , https://tripplanhelper.com/blog/splitwise-free-plan-limits/
- Troupe and Lambus: https://www.phocuswire.com/jetblue-travel-products-launches-troupe-app-simplify-group-travel-planning , https://www.wandrly.app/tools/troupe , https://adapty.io/paywall-library/lambus/ , https://travelhighlights.io/travel-apps/lambus-vs-wanderspend/
- Legal and ads: https://www.ftc.gov/legal-library/browse/statement-policy-regarding-comparative-advertising , https://www.wilsonlegalgroup.com/blogs/trademark-law/use-of-third-party-trademarks-in-advertising , https://www.gummicube.com/blog/targeting-competitor-ios-app-brands-with-keyword-optimization/ , https://www.rocketshiphq.com/bid-competitor-keywords-apple-search-ads/ , https://www.apptweak.com/en/aso-blog/guide-to-apple-search-ads
- Reddit and TikTok: https://redship.io/blog/reddit-self-promotion-rules , https://getupvotes.com/reddit-self-promotion/ , https://collabstr.com/top-influencers/user-generated-content/travel
- Memories: https://apps.apple.com/us/app/polarsteps/id947925763 , https://www.wandrly.app/comparisons/wanderlog-vs-polarsteps
