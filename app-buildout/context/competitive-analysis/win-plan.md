# How Hermi beats every app researched and wins their users

Written 2026-09-30. This is a brainstorm and plan, not a spec. It builds on the six files in [research/](research) and on the Phase 1 scope in [../app-buildout/phase-1-launch/README.md](../../phase-1-launch/README.md). Hermi is unbuilt, so every Hermi "win" below is a promise until it ships.

## How to read this file

- **Reported** means the fact came from a search snippet or third-party review on 2026-09-30 and was not checked on a vendor page. Every competitor number, price and feature in this file is reported unless stated. Verify before any public use (see the verification list at the end of section 5).
- **Adopted** means already in the Phase 1 scope. **Recommend** means it is new and needs the owner's approval (section 9).
- Effort: S is under a week, M is one to three weeks, L is over three weeks, for a solo developer working with Claude Code.
- Phase: 1 fits the six-month launch, 2 is months 7 to 12, 3 is year 2 and later.
- Positioning line for all copy: **Plan together. Know the fare.**

---

## 1. The verdict

### The market in plain terms

1. **There is no big app called Trippy.** The huge app is TripIt (reported: about 22M travelers, Pro $49 a year). It is a post-booking organizer, not a planner. "Trippy" at letsgetrippy.com (reported) is a small, new group-trip app with chat, voting, expense splitting and a chat-to-plan AI called Trippy Spark. Its scale is unknown.
2. **The closest planner is Wanderlog.** Reported: map-first, free live collaboration, Pro at $39.99 a year (one source says $49.99), 4.9 stars, organic search as its main channel. It has the habits Hermi's users already have.
3. **Tripsy is the polish benchmark.** Reported: Apple-only, 4.7 stars from about 5.6K ratings, Editors' Choice, email import, flight alerts, Live Activities, widgets, Watch. It charges for sharing and has no Android editing. In May 2026 it shipped an MCP server, so "bring your own AI" is no longer a unique idea.
4. **AI planners are crowded and alike.** Layla (now Expedia-owned, reported deal closed 2026-07-31), Mindtrip, Wanderboat, Stippl, Airial and a dozen smaller ones all generate a plan in chat. They share the same weaknesses: invented or stale places, no per-fact source, one-shot itineraries, weak group decisions, no price tracking after the plan, paywall before value, offline gated.
5. **The platforms are closing in on the basics.** Google AI Mode (reported: Canvas itinerary, flight price tracking across 300+ airlines, agentic hotel booking, August 2026) and ChatGPT (reported: Expedia and Booking apps, group chats up to 20 people) give away chat planning and booking for free. OTA-owned tools (Expedia, Booking, Kayak, Trip.com) steer toward their own inventory.

### Where Hermi can win

Hermi wins where trust, group decisions and follow-through matter more than inventory or reach.

| Lane | Why Hermi can own it | Who it beats |
|---|---|---|
| Proof, not vibes | Every AI fact says "Found on [site], checked [date]" and links to the page. Fares must be seen on a page during the run. No competitor found does this per fact inside a saved plan. | Layla, Mindtrip, Wanderboat, ChatGPT, Google AI Mode, all small AI planners |
| Check the AI you already use | "Verify this plan": paste a ChatGPT, Layla or Mindtrip itinerary and Hermi checks each place, hours and price. It turns the biggest competitor into a funnel. | ChatGPT, Layla, Mindtrip, Gemini |
| Two people plan free | Free owners invite 1 collaborator per trip. Invitees always join free. | Tripsy, Layla, TripIt (view only), Mindtrip (group caps) |
| The plan watches the price | Fare watch attached to the trip, plus the booked-fare drop alert. | Wanderlog, Tripsy, Layla, Mindtrip, TripIt (partial) |
| Honest commerce | No ranking by commission, labeled links, no ads, no fake urgency, one-tap cancel. | Every OTA-owned planner, Wanderlog (billing complaints) |
| Switching is easy | Import from TripIt, Tripsy, Wanderlog and Google Maps lists, then a free Trip Pass. | TripIt, Tripsy, Wanderlog |
| Works for the whole group | Full web editing from any phone today, native Android later. | Tripsy (Apple only), Trippy (Android first) |

### Fights to avoid

| Fight | Who wins it | Hermi posture |
|---|---|---|
| Live inventory and instant booking | Google, Expedia, Booking, Trip.com, Mindtrip (Sabre) | Hand off through labeled affiliate links. LiteAPI stays Phase 3 and optional. Never call Hermi a booking engine. |
| Generic "plan me a trip" chat | ChatGPT, Gemini, Google AI Mode, Perplexity | Do not compete on one-shot generation. Let people bring drafts in and make Hermi the place to verify and decide. |
| Place database and reviews | Google Maps, Tripadvisor | Use Geoapify, Wikipedia and cited web pages. Do not build a review corpus. |
| Fare prediction and metasearch depth | Google Flights, Kayak, Hopper | Watch the user's specific fare with sources. Never promise predictions. |
| Paid search on "AI trip planner" | Expedia and Booking budgets | Use sample trips, /vs pages, shared-trip pages and referrals. Test competitor keywords only with a hard cap. |
| Being a chat app | Trippy, WhatsApp, iMessage | Do not build a messenger. Ingest the chat instead ("paste your group chat"). |
| Loyalty points and business travel | TripIt Pro, Concur | Out of scope. |

### Honest gaps to close

These are where competitors are ahead today, and the plan must not hide them.

1. **Email import.** TripIt forwards and syncs inboxes; Tripsy claims 700+ providers (reported). Hermi has paste-and-parse at launch, forwarding in Phase 2. This is the biggest switching blocker.
2. **Flight status alerts.** TripIt Pro and Tripsy have them. Hermi is Phase 2.
3. **Native polish.** Tripsy has widgets, Live Activities and Watch. Hermi is a Capacitor shell at launch.
4. **Android.** Web only until Phase 2.
5. **Group chat and chat-to-plan.** Trippy has it. Hermi answers with "paste your group chat" (section 3).
6. **Brand and reviews.** Hermi has zero users and zero ratings. Wanderlog and TripIt have hundreds of thousands.
7. **Live fare source risk.** SerpApi terms and cost are unverified. Do not run comparative fare ads until a licensed source is in place.

### The one-paragraph strategy

Win the people who are already let down. Offer the couple who is tired of paywalled sharing a free shared plan. Offer the person who got a hallucinated restaurant from a chatbot a one-tap check with sources. Offer the TripIt or Tripsy user a five-minute move with a free Trip Pass as thanks. Make every one of those moments fast, calm and correct, because a small app loses on bugs and billing surprises before it loses on features.

---

## 2. Per competitor

Each block has five parts: what they excel at, what Hermi does better, what they lack, the switching hook, and the features Hermi should add to beat them. All competitor facts are reported.

### 2.1 TripIt (SAP Concur)

**What they excel at**
- Scale and trust: reported 22M+ travelers, iOS 4.8 stars from about 311K ratings, founded 2006.
- Forward-a-confirmation email building a master itinerary. Inbox Sync on Gmail, Outlook and Yahoo.
- Pro alerts: flight status often before the airline, seat tracker, fare-drop refund alerts (users report real money back), check-in reminders.
- Corporate bundle: many users get Pro free through their employer.

**What Hermi does better**
- Planning before booking: day-by-day plan, map, stay shortlist with hearts and compare.
- Group work: TripIt sharing is view only (reported). Hermi has roles, hearts, activity log and later polls and cost splitting.
- Fares before you book, not only after.
- Sourced AI research; TripIt has no AI planner (reported).
- A modern interface. Complaints call TripIt dated.

**What they lack**
- Collaborative editing, expense splitting, group decisions.
- Flight price watching for trips not yet booked.
- Free alerts and offline (reported paywall at $49 a year).
- Email parsing that survives unsupported sites (reported failures).

**Switching hook**
"Keep your TripIt emails. Bring the trip over in a minute, plan the next one with your partner for free." Upload the TripIt .ics export or paste the calendar feed URL. First import earns a free Trip Pass. Do not ask for TripIt credentials.

**Features to add to beat them**
- TripIt calendar file and feed import with a clear "what moved" review screen (adopted).
- Booked-fare drop alert, framed as "the TripIt Pro feature people love, in Plus" (adopted).
- Email-forward import, pulled earlier if possible (Phase 2, consider Phase 1 late).
- Flight status alerts, free on the flights you chose (Phase 2).
- Live calendar feed per trip (adopted).

### 2.2 Trippy (letsgetrippy.com)

**What they excel at**
- A sharp group-trip pitch: "100 messages and zero decisions" turned into a plan.
- Trippy Spark: reads the group chat and outputs dates, stays, restaurants and unresolved items in seconds.
- Chat, voting and expense splitting in one free app (reported free to download; pricing not found).
- Android available now.

**What Hermi does better**
- Planning depth: itinerary, map, presentation mode, checklist.
- Fares: history, alerts, booked-fare drop alert. Not found in Trippy.
- Sources on every AI fact. A chat summarizer can invent dates.
- Web access for friends on any device, plus iOS.
- Stay shortlist and compare.

**What they lack (by current evidence; "not found" is not "confirmed absent")**
- Fare tracking, evidence-linked AI, affiliate layer, offline, stay comparison.
- Any visible scale, ratings or press. Name collisions with other Trippy apps hurt its search.

**Switching hook**
"Your group chat is already the plan. Paste it in and get a plan with sources, prices and open decisions." Target groups stuck in WhatsApp and iMessage, not people who want a new chat app.

**Features to add to beat them**
- "Paste your group chat" to draft a plan (4 credits, reuses `draft_trip`). Shows "still undecided" items and sources. Recommend for Phase 1.
- Group polls and cost splitting (Phase 2). Consider a thin slice earlier: one "where to stay" poll type.
- A read-only share link that needs no install (adopted), so the one Android or iPhone holdout is never blocked.
- A "what is still open" list on the trip (M, Phase 2).

### 2.3 Tripsy

**What they excel at**
- Native Apple polish: widgets, Live Activities, Watch, Mac, Setapp, Siri Shortcuts. Editors' Choice, 4.7 stars from about 5.6K ratings.
- Email forwarding across 700+ providers, plus Smart Import from screenshots, Maps lists and social posts (3.10, Pro).
- Flight status alerts, documents, expenses, offline.
- MCP server and CLI (May 2026): users connect Claude or ChatGPT to build trips.

**What Hermi does better**
- Cross-platform editing: Tripsy has no Android editing and a view-only web (reported).
- Free collaboration. Tripsy puts sharing, sync and collaboration behind Pro (reported).
- Fares, price history and the booked-fare drop alert. Tripsy shows flight status only.
- Voting, hearts and (later) polls. Stay shortlist and compare. Presentation mode.
- Cited AI research rather than import plumbing.
- Simpler pricing: Tripsy reports weekly, monthly, yearly and a lifetime price near $299; sources conflict.

**What they lack**
- Android and editable web, free sharing, fare search and tracking, group decisions, stay comparison, presentation mode, cited research.
- Reliability: reported sync problems, flaky email automation, slow saves.

**Switching hook**
"Your friends are on Android. Plan together anyway." Offer a Tripsy switch path (calendar feed or file export; verify what Tripsy can export) and the free Trip Pass. Never offer lifetime; say so as a trust line.

**Features to add to beat them**
- Switching import for Tripsy trips via calendar file or feed (adopted as generic ICS; add a named Tripsy entry after testing).
- Screenshot and pasted-text booking import (extend existing paste import; Phase 1 late or Phase 2).
- Email-forward import (Phase 2).
- Live Activities and widgets for the next flight and next item (Phase 2). Watch only if retention data asks.
- A Hermi MCP server so Claude and ChatGPT users can send plans in (Phase 2). Hermi pays no inference for this path.
- Documents attached to items (Phase 2).
- Publish an "edits are never lost" sync promise backed by tests.

### 2.4 Wanderlog

**What they excel at**
- Best-in-class map plus itinerary with travel time between stops.
- Real-time collaboration like a shared document, free.
- Gmail and forward import, budget with splitting, route optimization (Pro).
- Distribution: reported organic search is the top channel, millions of visits a month, 4.9 stars. Their "Year in Travel" campaign reportedly lifted new users (verify).

**What Hermi does better**
- Evidence and sources on AI facts. Wanderlog's AI is an assistant with no citation model reported, and free AI is capped near 5 messages per trip.
- Fare watch tied to the plan; Wanderlog has no flight tracking (reported; Pro price-drop alerts may exist, verify).
- Offline on every tier. Reported as the number one Wanderlog complaint because it is Pro only.
- Honest billing. Reported complaints: cancellation "nightmare", charged for a full year, a card imported without consent.
- Stay compare, presentation mode.

**What they lack**
- Voting and polls beyond hearts, comments and version history (reported).
- Reliable sync: reported "unable to connect" errors even for paid users.
- Free offline, dark mode and Google Maps export (Pro).
- Fare intelligence.

**Switching hook**
"Nothing you need is locked." Bring a Wanderlog trip over (Google Maps list or pasted places, since no official export was found), keep planning with your partner free, and keep offline free.

**Features to add to beat them**
- Google Maps list and places-paste import (Phase 1, recommend). Covers Wanderlog users who exported to Google Maps.
- A "Synced 12 s ago" indicator and a safe offline edit queue (adopted edit queue; add the indicator, S).
- Free offline plus a public offline guarantee (adopted).
- Comments on items and polls (Phase 2).
- "Year in travel" card (Phase 2).
- A map that is fast and clear with travel times between stops (table stakes; budget for polish).

### 2.5 Layla (Expedia Group)

**What they excel at**
- Conversational planning, live-priced flights and stays, partner bookings. Reported about 2.1M trips planned. Now backed by Expedia inventory.
- Mainstream destinations (reported).

**What Hermi does better**
- Sources on every fact. Reviews report invented restaurant names, hours and prices, and AI that ignored overnight arrivals.
- No paywall before value: Layla's day-by-day and PDF sit behind about $49 a year (reported). Hermi gives a full first draft free.
- Free sharing. Layla shares are premium.
- Honest commerce. An Expedia-owned planner has a reason to steer to Expedia. Hermi never ranks by commission.
- Offline and credit transparency: Layla is reported to have unexpected charges after trial.

**What they lack**
- Per-claim sources, group decisions, fare tracking after the plan, strong offline.
- Stable roadmap. Acquisition raises a risk it is folded into Expedia products (reported: no date given).

**Switching hook**
"Got a Layla itinerary? Paste it. We check every place, hour and price, with sources, and keep watching the fare." Layla users who hit the day-by-day paywall get the whole plan free on Hermi.

**Features to add to beat them**
- "Verify this plan" for pasted Layla itineraries (recommend Phase 1).
- Overnight arrival, time zone and date-logic test suite for AI drafts (S, part of evals).
- Credit cost shown before every AI action and a plain billing page (adopted; add the page).
- Acquisition-watch: monitor Expedia announcements for Layla changes and run a "Layla is changing" switching push if it is folded in.

### 2.6 Mindtrip

**What they excel at**
- Smooth chat, map, collaborative sharing with real-time group chat (reported free up to 5 people), receipts and email import, in-chat flight booking via Sabre (reported May 2026), Stays (July 2026).
- Funding and partners (reported: United, Capital One, Amex ventures).

**What Hermi does better**
- Accuracy: reviews report hotels that do not exist and budget filters not honored.
- Group deciding: reported as solo and couple oriented, not a way for a group to decide.
- Stable plans: reported complaints of itineraries reordering after hours of work. Hermi drafts are preview only; nothing saves until accepted.
- Offline (reported none) and fare watching.

**What they lack**
- Offline, per-claim sources, flight tracking after booking, stable plan edits.
- Reliability: crashes, billing issues, update regressions reported.

**Switching hook**
"AI never changes your plan without asking." Show the preview-then-accept flow and the evidence label in the first 30 seconds. Offer import of saved places via paste.

**Features to add to beat them**
- Preview-then-accept for every AI change (adopted in the spec), advertised.
- Strict filters test: results never exceed a stated price ceiling (S, part of evals).
- "Verify this plan" for Mindtrip itineraries (Phase 1, recommend).
- Repair-a-day so that change is explicit and reversible (M).
- Activity log with undo for AI changes (S, verify it exists in the spec).

### 2.7 Wanderboat

**What they excel at**
- Free, reported 2M to 3.5M users (conflicting figures), iOS, Android and web, broad discovery from community posts, ran a large San Francisco ad campaign.

**What Hermi does better**
- Sources per fact, group planning, fare watch, offline, honest commerce.

**What they lack (not found)**
- Collaboration, offline, flight tracking, booking depth, any visible monetization. Reported complaint data is thin.

**Switching hook**
"Discovery is easy. Deciding together is hard." Target Wanderboat users who have a list of places and a partner who needs to agree. Import by paste.

**Features to add to beat them**
- Places-paste import with a dated source chip per place (Phase 1, recommend).
- Link import for creator posts (Phase 2; see Airial below).
- Free shared plan for two (adopted).

### 2.8 Google AI Mode, Gemini and Maps

**What they excel at**
- Distribution: billions of users, free. Canvas itinerary from Search and Maps data. Reported flight price tracking across 300+ airlines and agentic hotel booking with cancellation terms and Google Pay (August 2026). Gmail reservations feed Maps.

**What Hermi does better**
- Neutral trip workspace: Google is not a place where a couple decides, compares and presents.
- Evidence labels that stay on the saved plan and show the date checked.
- Commerce without ads: Google earns from ads and partner fees.
- Longer memory: fare history tied to your plan, over months.
- Privacy promise: no ads, no data sales, export and deletion.

**What they lack**
- Structure for group decisions (Canvas share is an edit link), persistent watch tied to a plan, explicit "checked on" dates per fact, a presentation walk-through.
- Trust on neutrality.

**Switching hook**
"Start anywhere. Decide here." Do not attack Google. Offer a way to bring a Canvas or AI Mode result into Hermi and verify it. Accept pasted text or a pasted shared link text the user copies (never fetch).

**Features to add to beat them**
- "Verify this plan" accepts any pasted itinerary text (Phase 1, recommend).
- Fare watch that shows the source and date (adopted), positioned as "more honest than a price graph".
- Google Maps saved-list import (Phase 1, recommend).
- Avoid: do not build hotel booking, do not build a place database.

### 2.9 ChatGPT, and its travel apps

**What they excel at**
- Default app for planning: free tier, group chats up to 20 (reported), Expedia and Booking apps with live results, Agent Mode that drives bookings with approval. Flexible: it can answer anything.

**What Hermi does better**
- Structure that survives a chat: a trip with days, stays, votes, a map, offline and a link to share.
- Facts that can be checked: reported invented venues in general chatbots, closed restaurants, a fake hot springs story.
- Follow-through: watching fares, alerting on drops.
- Group decisions, not a long thread.

**What they lack**
- A persistent trip workspace, per-fact dated sources, offline, price watching, presentation mode, calm sharing with non-users.
- Travel apps are merchant-led and steer to Expedia or Booking inventory.

**Switching hook**
"Keep using ChatGPT to brainstorm. Bring the plan to Hermi to check it, share it and watch the price." This is a funnel, not a fight.

**Features to add to beat them**
- "Verify this plan" (hero, Phase 1).
- Hermi MCP server so ChatGPT and Claude users can send a plan into Hermi in one step (Phase 2; consider a thin read-write version earlier if effort is S).
- "Export to ChatGPT" style prompt: a copy button that gives the assistant a trip summary for follow-up questions (S, Phase 2).
- Do not compete on in-chat booking.

### 2.10 Kayak

**What they excel at**
- Metasearch depth, price forecast (buy or wait, 30 days, since 2013), Ask AI, package search, presence inside ChatGPT (reported).

**What Hermi does better**
- Plan context: the fare sits inside a trip with dates, stays and travelers.
- Sources per fare and "Indicative" labels, and a booked-fare drop alert.
- No ad or referral ranking; Kayak earns from referral and ad fees.

**What they lack**
- Collaboration, itinerary, group decisions, persistent plan.

**Switching hook**
"Kayak finds a fare. Hermi watches it for the whole trip, with your partner." Do not bid on Kayak keywords at launch; it is a tool people use alongside Hermi.

**Features to add to beat them**
- Fare watch with price history (adopted).
- "Why this fare" evidence view showing the source page, date and what was rejected (adopted in the spec as a rejected-items view; verify).
- Do not build price prediction. Show "moved since you looked" instead.

### 2.11 Smaller AI planners (grouped)

Includes Stippl, Airial, iplan.ai, Roam Around, Trip Planner AI, Wonderplan, Curiosio, Vacay, Holiwise, GuideGeek, Stardrift, Tripadvisor trip builder, Perplexity, Trip.com TripGenie, Booking.com AI Trip Planner. All reported; many figures are vendor claims.

| App | Excels at | Weakness to exploit | Hook and feature |
|---|---|---|---|
| Stippl | Collaboration, offline and email forwarding in Pro at $3.99 a month or $24.99 a year | Good features sit behind Pro; no sources | Free offline and free couple sharing; "no Pro needed" |
| Airial | Turns creator links (TikTok, Reels, blogs) into itineraries | Sources are the creator, not verified facts | Link and paste import with a verification step (Phase 2) |
| iplan.ai | Fast 30-second itineraries, cheap IAP | Illogical routing, bugs, limited cities | Show routed days with travel times and an honest error state |
| Roam Around | One-shot itinerary, token pricing | Tokens feel like a meter; absorbed by Layla, stale risk | "No tokens before you see value" |
| Trip Planner AI, Wonderplan | Free form-driven plans | Template output; plan blocked before you can judge it | Full first draft free with sources |
| Curiosio | Road-trip and multi-stop generator | Low polish, no collaboration | Road-trip days via Geoapify routing later; not a priority |
| Vacay | Themed advisors, 150+ languages | Solo dev, $49 a month Professional | Out of scope |
| Holiwise | Premium recommendations, group planning | Claims only, small | Compare on proof and price watching |
| GuideGeek | Free inside WhatsApp and Instagram | No persistent trip workspace | "Take the WhatsApp answer into a real plan" via paste import |
| Stardrift | Live prices, calendar awareness, preference memory | Sources unknown | Preference memory is a later idea (Phase 3) |
| Tripadvisor trip builder | Review-based trust, huge base | Ad and click driven, no group tools | Evidence labels with dates; do not copy reviews |
| Perplexity | Inline citations, hotel booking | No trip workspace | Match the citation habit, add the workspace |
| Trip.com TripGenie | Booking-led, co-edit invite | Steers to Trip.com inventory | Honest commerce page |
| Booking.com AI Trip Planner | Stay Q&A and review summaries | Steers to Booking inventory | Honest commerce page; do not fetch Booking pages |

---

## 3. Master list of features to implement

Each entry: what beats whom, the user problem, how it works in Hermi, effort, phase, and how it makes money or drives growth. "Adopted" means in the Phase 1 scope already.

### 3.1 Trust and proof

**F1. Evidence labels as the hero**
- Beats: Layla, Mindtrip, Wanderboat, ChatGPT, Google AI Mode, all small AI planners.
- Problem: AI invents places, hours and prices, and nobody can tell.
- How: every AI-found fact shows "Found on [site], checked [date]", tappable to the source page. Facts older than a set age show "Stale, recheck" and a one-tap recheck (1 credit, S). Places the AI could not ground are dropped, not shown.
- Effort: M. Phase: 1 (adopted; stale flag and recheck are recommended additions).
- Money or growth: the headline in onboarding, the App Store listing and every /vs page. Recheck spends credits, which funds itself.

**F2. "Verify this plan"**
- Beats: ChatGPT, Layla, Mindtrip, Gemini, Google AI Mode, Wanderboat.
- Problem: people plan in a chatbot and do not trust the output, then spend hours checking it by hand.
- How: paste text from any assistant (or upload a screenshot later). Haiku extracts places, days, hours and prices. Each place is checked against place data and cited pages. Result shows green (matches), amber (differs, here is the source) and red (could not be found). One tap imports the verified days as a draft trip.
- Effort: M. Phase: 1 (recommend; it extends the paste-import and research paths already in scope).
- Money or growth: entry point for ChatGPT, Layla and Mindtrip users. Costs credits (suggest a cheap batch price, for example 4 for a trip under 8 places), so free users hit the credit limit naturally and buy a Trip Pass.

**F3. Honest affiliate page ("How we earn")**
- Beats: Layla (Expedia), Mindtrip, Booking and Trip.com planners, Kayak.
- Problem: users suspect AI picks are paid placement.
- How: public page listing the rules (never ranked by commission, labeled links, no ads, no data sales, Airbnb and Booking pages never fetched), with live counts of links and a disclosure next to each button.
- Effort: S. Phase: 1 (recommend). Money or growth: trust asset, PR angle, links from /vs pages.

**F4. Public accuracy note and eval results**
- Beats: all AI planners.
- Problem: nobody publishes how often their AI is wrong.
- How: a page that states the test method (for example, 100 random itineraries checked for place existence, hours, travel time and date logic) and the latest pass rate. Update monthly. Claim only what was measured.
- Effort: S after evals exist. Phase: 1 (recommend, tied to the zero-hallucination policy in section 4). Growth: press and Reddit credibility.

**F5. Reliability bar and public status page**
- Beats: Wanderlog, Tripsy, TripIt, Mindtrip (all with reported sync or crash complaints).
- Problem: sync errors and data loss before or during a trip.
- How: crash-free sessions above 99.5% at TestFlight, latency budgets per action, a public status page, a visible "Synced 12 s ago" indicator, a tested offline queue, and an "edits are never lost" promise.
- Effort: S for the page and indicator, ongoing for testing. Phase: 1. Growth: reviews and retention.

### 3.2 Planning and group work

**F6. "Paste your group chat" to draft a plan**
- Beats: Trippy (answers Trippy Spark), ChatGPT group chats, WhatsApp threads.
- Problem: 100 messages and no decisions.
- How: paste or share-sheet the exported chat text. A draft_trip-style action lists dates mentioned, candidate places, stays with links, who said what about each, and "still undecided". The owner accepts items into the trip. Names are stripped to first names and raw chat text is not stored after extraction (verify privacy copy).
- Effort: M. Phase: 1 (recommend, light) with a richer version in 2. Money or growth: 4 credits, strong TikTok demo, organic invites because the plan is shared back to the group.

**F7. Free couple collaboration**
- Beats: Tripsy, Layla, TripIt (view only), Mindtrip (caps).
- Problem: the partner has to pay or join a paywalled trip.
- How: free owners invite 1 collaborator per trip; Plus and Trip Pass up to 6; invitees always join free; a partner's heart and edits appear within seconds (polling every 15 to 30 s).
- Effort: S. Phase: 1 (adopted). Growth: every invite is an acquisition. Track invite to join rate.

**F8. Repair-a-day**
- Beats: one-shot planners (Layla, Mindtrip, Wonderplan, iplan.ai).
- Problem: a place is closed, it rains, a flight moves, and the plan is now wrong.
- How: on any day, "Repair this day" shows the reason (for example "closed Mondays, source, checked date"), proposes 2 swaps with travel times, and applies only after the user accepts. Undo is one tap. Phase 1 version: user-triggered, single day. Phase 2: proactive prompts when a chosen flight changes.
- Effort: M. Phase: 1 light (recommend) then 2. Money or growth: 1 credit each; shows "adaptive, not one-shot" in demos.

**F9. Group polls**
- Beats: Wanderlog (hearts only), TripIt, Mindtrip, ChatGPT group chat.
- Problem: decisions happen by attrition.
- How: polls on dates, stays and ideas with 2 to 12 options, closing time, and a result that feeds the plan.
- Effort: M. Phase: 2 (Group Trip Pass). Recommend a thin slice (one "where to stay" poll type) if interviews confirm. Money: Group Trip Pass $19.99; invitees join free.

**F10. Cost splitting**
- Beats: TripIt, Trippy parity, Wanderlog Pro.
- How: expenses, four split modes, FX, minimized transfers, manual settle.
- Effort: M. Phase: 2. Money: part of Group Trip Pass and paid plans.

**F11. "What is still open" list**
- Beats: Trippy Spark (unresolved items), Wanderlog.
- Problem: nobody knows what is undecided.
- How: a trip-level list built from empty days, stays without a vote, unbooked flights and open polls, with a nudge to the people who have not voted.
- Effort: M. Phase: 2. Growth: re-engagement pushes.

**F12. Presentation mode as a differentiator**
- Beats: every competitor (none found with a full-screen walkthrough).
- Problem: deciding together on a phone is cramped; sharing with non-members is messy.
- How: full-screen slides of days, stays and fares; read-only link; PDF (free adds a small footer). Add a "Plan review with your partner" mode with a swipe and a heart on each slide.
- Effort: M (adopted core). Phase: 1 (adopted). Growth: shared links carry the brand; the PDF footer drives installs.

### 3.3 Fares and money

**F13. Fare watch attached to the plan**
- Beats: Wanderlog, Tripsy, Layla, Mindtrip, Trippy.
- Problem: fares change after the plan is made and nobody tells you.
- How: a route on the trip, price history, alerts, sources and dates on every fare, "Indicative" label, and a clear "moved since you looked".
- Effort: M. Phase: 1 (adopted). Money: Plus (3 live routes), Trip Pass (2), affiliate hand-off.

**F14. Booked-fare drop alert**
- Beats: TripIt Pro (closest), Tripsy, Kayak, Google.
- Problem: you booked, the price fell, and you did not know you could ask for a credit or refund.
- How: enter what you paid; Hermi watches the route; on a drop it says "you paid $X, it is now $Y; check the airline's change and credit rules" with a link to the rules. No claim of a refund.
- Effort: M. Phase: 1 (adopted). Money: a main reason for Plus.

**F15. One-tap cancel and no paywall before value**
- Beats: Wanderlog and Layla (reported billing complaints), Trip Planner AI, Roam Around.
- How: a full first draft is free (taster). Price and date stated before any trial, reminder before conversion, cancel inside the app in one tap, a plain "how billing works" page, no card imported from a wallet. The free path is always visible.
- Effort: S to M. Phase: 1 (mostly adopted; recommend the billing page and the in-app cancel shortcut). Growth: App Store review tone and word of mouth.

### 3.4 Switching and import

**F16. Switching imports**
- Beats: TripIt, Tripsy, Wanderlog, Google Maps users.
- Problem: moving apps feels like losing work.
- How: onboarding asks "Coming from TripIt, Tripsy or Wanderlog?" with three paths: upload a calendar file (.ics) or paste a feed URL (TripIt, Tripsy, Google Calendar; adopted), paste booking confirmations (adopted), and import a Google Maps list or pasted places (recommend). A review screen shows what was found; nothing saves until accepted. Never ask for another app's password. Say what moves (dates, flights, stays, places), not "everything".
- Effort: M. Phase: 1 (ICS and paste adopted; Maps list and named Tripsy and Wanderlog entries recommended).
- Money or growth: first import earns a free Trip Pass (adopted), about $0.58 to $0.84 of provider spend (from the plan). Track switch imports per week.

**F17. Email-forward import (plans@hermi.world)**
- Beats: TripIt, Tripsy, Wanderlog (Pro).
- Problem: pasting is slower than forwarding.
- How: a personal forwarding address per user; a deterministic parser for top airlines and hotels with a Haiku fallback; results land in a review inbox, never auto-merged.
- Effort: L (security, parsing, abuse). Phase: 2; consider pulling to month 5 or 6 if the paste flow proves slow in beta. Money: free for all, because gating it is a reported TripIt and Wanderlog complaint.

**F18. Screenshot and link import**
- Beats: Tripsy Smart Import, Airial.
- How: paste or share a screenshot, Maps link text, or a post the user copied; extract candidate places and bookings, then verify (F2).
- Effort: M. Phase: 2. Growth: creator hook; respects site terms by using only text the user provides.

**F19. Flight status alerts**
- Beats: TripIt Pro, Tripsy.
- How: delay, gate and cancellation push for chosen flights, with the data source and time in each alert.
- Effort: L (a status data provider and cost). Phase: 2. Money: free for chosen flights on Plus and Trip Pass; free tier gets the first alert only (decide after cost is known).

### 3.5 Offline and platforms

**F20. Offline everywhere**
- Beats: Wanderlog, TripIt, Layla, Mindtrip, Stippl (all gate or lack it).
- How: trips readable offline on every tier; edits queue and sync (adopted). Add downloaded map tiles for the trip area (Phase 2) and a clear "Offline ready" badge per trip.
- Effort: M, L for maps. Phase: 1 for read and queue; 2 for maps. Growth: headline on the store listing.

**F21. Android via web, then native**
- Beats: Tripsy (no Android editing), Trippy parity.
- How: Phase 1 ships a fast installable web app (PWA-style add to home screen) with full editing. Native Android arrives in Phase 2.
- Effort: S in Phase 1 (install guide, manifest, tests on Android Chrome), L in Phase 2. Growth: mixed-device groups work on day one.

**F22. Live Activities and widgets on iOS**
- Beats: Tripsy (polish benchmark), Flighty-style expectations.
- How: a Live Activity for the next flight and departure countdown, home and lock screen widgets for the next item and price moves.
- Effort: L. Phase: 2. Growth: visible polish in screenshots; retention during travel.

### 3.6 Growth features

**F23. Hermi MCP server**
- Beats: ChatGPT and Claude users who build plans in chat; narrows Tripsy's edge.
- How: a hosted MCP connector that lets an assistant create a trip, add days and places, and ask Hermi to verify. The user's own assistant pays for inference; Hermi adds evidence labels and storage. Scoped token, read and write per trip, revocable.
- Effort: M. Phase: 2. Growth: a channel inside AI assistants. Keep the product useful without any one assistant.

**F24. "Year in travel" share card**
- Beats: Wanderlog (reported campaign), Tripsy (stats unconfirmed).
- How: a designed card of trips, places, miles and money saved by fare drops, shareable as an image with a link.
- Effort: S to M. Phase: 2. Growth: seasonal campaign in December.

**F25. Referral credits and Trip Pass gifting**
- Beats: all (none found with a paid referral program).
- How: invitee gets a credit on signup; inviter gets credits when the invitee creates a trip (adopted).
- Effort: S to M. Phase: 1 (adopted). Growth: each trip brings 2 to 6 people.

**F26. Sample trips, /vs pages, calendar feed**
- Adopted in Phase 1. Sample trips show evidence labels and real costs. /vs pages follow section 5.3. The live calendar feed answers a TripIt expectation.

**F27. Documents on items**
- Beats: Tripsy (Pro anchor), TripIt Pro (25 documents per trip, reported).
- How: attach a PDF or image of a confirmation to an item, available offline.
- Effort: M. Phase: 2 (recommend to start early Phase 2).

**F28. Dates everyone is free**
- Beats: Troupe and Doodle-style tools, Trippy.
- How: a simple availability poll for trip dates with overlap shown.
- Effort: M. Phase: 2 (part of the poll pack).

### 3.7 Summary table

| # | Feature | Effort | Phase | Status |
|---|---|---|---|---|
| F1 | Evidence labels (plus stale flag, recheck) | M | 1 | Adopted; additions recommended |
| F2 | Verify this plan | M | 1 | Recommend |
| F3 | Honest affiliate page | S | 1 | Recommend |
| F4 | Public accuracy note | S | 1 | Recommend |
| F5 | Reliability bar and status page | S | 1 | Recommend (status page, sync indicator) |
| F6 | Paste your group chat | M | 1 light, 2 full | Recommend |
| F7 | Free couple collaboration | S | 1 | Adopted |
| F8 | Repair-a-day | M | 1 light, 2 full | Recommend |
| F9 | Group polls | M | 2 | Phase 2 (thin slice optional) |
| F10 | Cost splitting | M | 2 | Phase 2 |
| F11 | What is still open list | M | 2 | Phase 2 |
| F12 | Presentation mode | M | 1 | Adopted |
| F13 | Fare watch on the plan | M | 1 | Adopted |
| F14 | Booked-fare drop alert | M | 1 | Adopted |
| F15 | One-tap cancel, no paywall before value | S to M | 1 | Mostly adopted; billing page recommended |
| F16 | Switching imports | M | 1 | ICS and paste adopted; Maps list recommended |
| F17 | Email-forward import | L | 2 (consider earlier) | Phase 2 |
| F18 | Screenshot and link import | M | 2 | Phase 2 |
| F19 | Flight status alerts | L | 2 | Phase 2 |
| F20 | Offline everywhere | M to L | 1 read and queue, 2 maps | Adopted; maps Phase 2 |
| F21 | Android via web, then native | S then L | 1 web, 2 native | Web is adopted |
| F22 | Live Activities and widgets | L | 2 | Phase 2 |
| F23 | Hermi MCP server | M | 2 | Phase 2 |
| F24 | Year in travel card | S to M | 2 | Phase 2 |
| F25 | Referral credits | S to M | 1 | Adopted |
| F26 | Sample trips, /vs pages, calendar feed | M | 1 | Adopted |
| F27 | Documents on items | M | 2 | Phase 2 |
| F28 | Dates everyone is free | M | 2 | Phase 2 |

---

## 4. The polish bar

"Most polished AI travel app" is a claim that can be tested. These are the targets. Measure them monthly and publish the ones that are favorable.

### 4.1 Speed

| Measure | Target | Why |
|---|---|---|
| App launch to trip visible (warm) | under 1.0 s on a mid-range phone | Tripsy feels native; Hermi is a Capacitor shell and must not feel like a website |
| Open a trip offline | under 1.0 s, no spinner | Offline is a headline claim |
| Tap to screen change | under 100 ms response, under 300 ms content | Feels instant |
| Explain (Haiku) | first words in under 2 s | Chat feels alive |
| draft_day | under 15 s, with progress shown | Mindtrip is reported slow |
| draft_trip | under 45 s, with streaming days | Users wait if they see work |
| Verify this plan (8 places) | under 30 s | The hero demo |
| Agent run | progress events every few seconds; result notification when done | Long runs need trust |
| Sync after an edit | other person sees it within 30 s, indicator always shown | Wanderlog sync complaints |
| Map pan and zoom | 60 frames per second on a mid-range phone | Wanderlog sets the bar |

### 4.2 Accuracy and the zero-hallucination policy

1. No AI-found place, hour, price or fare appears without a source URL and a checked date (spec rule 4).
2. Places that cannot be grounded by place search are dropped from drafts, never shown as real.
3. Fares must be seen on a page during the run and show "Indicative" plus age.
4. When Hermi does not know, it says "could not confirm" and shows what it tried. A blank is better than a guess.
5. AI never gives visa, insurance or legal advice; it links to official sources.
6. Date and time zone logic is tested (overnight arrivals, date line, daylight saving).
7. A monthly eval set reports: place exists, hours match, travel time within tolerance, date logic correct. Target: 98% or better on place existence and 95% or better on hours, measured on Hermi's own test set. Publish the method and result (F4). Do not claim "zero errors"; claim "every fact has a source you can check".
8. Strict filters: price ceilings and dates are never exceeded in results (test in CI).
9. AI changes never save without an accept tap. Undo is one tap.

### 4.3 Accessibility

- WCAG 2.2 AA on all Phase 1 screens, including contrast of the Hermi palette (sky, ink, pink and yellow; app-buildout 05 section 2.3).
- Dynamic Type and text zoom to 200% with no clipped controls.
- VoiceOver and TalkBack labels for every control; evidence chips read as "Found on [site], checked [date]".
- Reduce Motion respected; no information carried by color alone (green, amber, red in Verify also use icons and words).
- Touch targets at least 44 by 44 points.
- Test with a screen reader before each release; track issues like crashes.

### 4.4 Native feel

- Native share sheet, Sign in with Apple, haptics on accept and undo, swipe back, pull to refresh where expected.
- Safe areas, keyboard handling and scroll position done right on every screen; no rubber-banding of fixed headers.
- Dark mode that matches the Hermi palette (verify the brand file supports it).
- Skeleton screens instead of spinners; no layout jump on load.
- Widgets and Live Activities in Phase 2 to close the gap with Tripsy.

### 4.5 Error states and empty states

- Every error says what happened, what is safe, and what to do next. No raw codes.
- Offline is a normal state with a calm banner, never an error.
- If a provider is down (fares, places), show the last cached data with its age and keep everything else working.
- A failed AI run refunds credits automatically and says so.
- Empty states teach one action ("Paste a confirmation", "Invite your partner").
- Conflicts show "Keep mine or use theirs" (spec F-COL-5) instead of silent overwrite.

### 4.6 Support and trust

| Measure | Target |
|---|---|
| First reply to a support message | under 4 hours on weekdays, under 24 hours otherwise; published |
| Billing issue resolved | within 1 business day; refund policy in plain language |
| Crash-free sessions | above 99.5% at TestFlight, above 99.8% at launch |
| Uptime | 99.9% monthly, public status page |
| App Store rating | 4.7 or higher after the first 200 ratings (Tripsy 4.7, Wanderlog 4.9, TripIt 4.8, all reported) |
| Cancel a subscription | one tap in the app, confirmation email |
| Data export and delete | in the app on every tier, completes within 24 hours |
| Time to first value | under 3 minutes from install to a plan with sources |

---

## 5. Customer acquisition plan to take their users

Principle: honest, useful, and specific. Every channel should show a real moment where a competitor user hit a problem Hermi solves.

### 5.1 Positioning lines per competitor

| Competitor users | Pain (reported) | Line | Proof to show |
|---|---|---|---|
| TripIt | view-only sharing, $49 for alerts, dated UI | "Keep your confirmations. Plan the next trip together." | Import screen, free couple invite |
| Trippy | 100 messages, no decisions | "Paste the group chat. Get a plan with sources." | Chat-to-plan demo |
| Tripsy | Apple only, sharing behind Pro | "Your friends are on Android. Plan together anyway." | Android web editing, free invite |
| Wanderlog | offline paywall, billing friction | "Nothing you need is locked. Cancel in one tap." | Offline badge, cancel screen |
| Layla | paywalled day-by-day, wrong details | "See the whole plan free. Every fact has a source." | Evidence labels |
| Mindtrip | fake hotels, plan reorders | "AI never changes your plan without asking." | Preview and accept flow |
| Wanderboat | discovery without deciding | "From a list of places to a plan you both agree on." | Hearts and polls |
| Google AI Mode | neutral and free but no workspace | "Start anywhere. Decide here." | Verify this plan |
| ChatGPT | invented venues, long threads | "Check your ChatGPT itinerary in 30 seconds." | Verify demo, sourced result |
| Kayak, Google Flights | one price at a time | "Hermi watches the fare for your whole trip." | Fare history inside a trip |

Tone rules: plain sentence case, no fake urgency, no em dashes, never disparage. Say "reported" internally; publicly say only what has been checked and dated.

### 5.2 App Store optimization

- Metadata holds no competitor names (Apple Review Guideline 2.3.7, reported). No "TripIt alternative" in the name, subtitle, keywords or screenshots.
- Name: "Hermi: Group Trip Planner". Subtitle idea: "Plan together. Know the fare." Keyword field: trip planner, group travel, itinerary, flight tracker, split costs, vote, fare alert, offline.
- Screenshots in order: (1) evidence label on a place, (2) plan together free, (3) fare watch and drop alert, (4) offline ready, (5) presentation mode, (6) Verify this plan.
- Custom product pages per audience (couples, groups, switchers). Custom pages must also follow 2.3.7.
- Ratings prompt after a positive moment (accepted plan, fare drop alert), never after an error. Reply to every review in 48 hours.
- Localize later after English proves out.
- Do a short verification of current Apple rules before submission.

### 5.3 The /vs pages (honest, with evidence)

Pages at hermi.world/vs/tripit, /vs/tripsy, /vs/wanderlog, /vs/layla, /vs/mindtrip, /vs/chatgpt, /vs/trippy. Use the same template for each.

Template:
1. One-line summary and "as of [date]".
2. Table of facts with a source link and a checked date per row.
3. **Where they win** (required section; for example, TripIt for flight alerts and email sync today, Tripsy for Apple polish, Wanderlog for map feel, ChatGPT for open-ended brainstorming).
4. **Where Hermi wins**, each with a screenshot.
5. Price comparison with the plan names used by the vendor.
6. "Switch" steps with the import path.
7. Correction email and last review date.

Rules (not legal advice; have counsel review before launch):
- Truthful and substantiated; keep a dated evidence file per row (screenshot of the vendor page).
- Use competitor names in plain text only. No logos, no trade dress, no implied affiliation.
- Word claims exactly: "TripIt shares trips view-only per its help pages (checked [date])", not "TripIt cannot collaborate".
- No claims drawn from Reddit anecdotes.
- No domains containing a competitor mark; use paths on hermi.world.
- Recheck prices weekly during launch month (Wanderlog reportedly changed Pro price in 2026).
- UK and EU: comparative advertising rules require objective, verifiable, like-for-like claims; recheck before launching there.

### 5.4 Apple Search Ads tests on competitor keywords

- Apple Ads allows bidding on competitor brand keywords (reported; verify current policy and any trademark complaint process before spending).
- Never use competitor names or logos in ad creative. Use a custom product page framed as "Group trip planner with fare sources".
- Structure: one campaign, exact-match ad groups per competitor (TripIt, Tripsy, Wanderlog, Layla, Mindtrip), daily cap, 4-week test.
- Stop rule: pause any group whose cost per install is above the payback of a Trip Pass sale or the plan's budget line. Reported industry finding: most competitor keyword campaigns lose money (verify).
- Check that Apple's first-party attribution is consistent with the plan's rule of no ad SDK and no ATT prompt before enabling.
- Do not bid on competitor names in Google web ads until each brand's trademark policy is checked.

### 5.5 Reddit playbook

- Be useful first. Answer planning questions in r/travel, r/solotravel, r/TravelHacks, r/digitalnomad, r/iosapps, r/tripit and r/Shoestring with real help. Disclose the founder relationship.
- Read each subreddit's rules and ask moderators before posting links. Many ban product links or confine them to a weekly thread.
- Good posts: "I checked 50 ChatGPT itineraries and here is how many places were closed" (with method), "How to get money back when the fare drops after you book", "How I move a TripIt trip to a new app".
- Never astroturf, never use undisclosed accounts, never attack a named competitor.
- Track referral traffic by UTM and ask "where did you hear about us" at onboarding.

### 5.6 TikTok and Reels playbook

Short formats (15 to 40 seconds):
1. "I pasted my group chat and got a plan" (Trippy audience).
2. "I asked ChatGPT for a Lisbon itinerary. Here is what was closed." (Verify demo).
3. "Who owes who after a 10 person trip" (Phase 2).
4. "My fare dropped after I booked. Here is what I did." (Booked-fare drop alert).
5. "I moved my TripIt trips in a minute."
6. "Plan a trip with your partner with no paywall."

Rules: disclose paid partnerships, no competitor logos or UI in a way that implies endorsement, one clear call to action, pinned comment with the link.

### 5.7 Creator program

- 10 to 20 travel creators at launch, mixed sizes. Each builds a public sample trip in Hermi showing evidence labels and real costs.
- Offer: Trip Pass credits, an affiliate share on links in their public trip (only where compliant), early access, and a say in the roadmap.
- Require FTC-style disclosure. Give a short brief, never a script.
- Measure by installs and trips created per creator, not views.
- Creator trips become SEO sample trips (adopted).

### 5.8 Switching offers

- Free Trip Pass after the first import (adopted). Show it on the import success screen, not before.
- For TripIt, Tripsy and Wanderlog users: a short landing page per source app with the exact import steps and a screenshot of each export screen.
- Annual trial of 7 days, price and date shown (adopted). No lifetime. No "switch and save 50%" discount that breaks the price floor.
- Win-back: if a user imports but does not plan, send one email with the next step, then stop.

### 5.9 Referral loop

- Every shared trip is an ad: the read-only link shows evidence labels, the invite page says "join free", and PDFs carry a small footer on Free.
- Invitee gets a credit on signup; inviter gets credits when the invitee creates a trip (adopted).
- Couples loop: the second person is a new user every time. Track invite to join to create-own-trip.
- Group loop: every group trip brings 2 to 6 people.

### 5.10 PR angle

- "We checked the AI trip planners" study: a transparent test of places and hours across ChatGPT, Layla, Mindtrip and Gemini using a fixed prompt set. Publish the method and raw results. Only publish after verifying with dated screenshots and giving each company a right of reply.
- "Why we show where every fact came from" founder story.
- "How we earn" page as a transparency story for travel media.
- Timing hooks: Layla's Expedia deal, Google AI Mode launches, holiday travel peaks, December "Year in travel".
- Target: travel and consumer tech press, Product Hunt, Hacker News (a real technical write-up on evidence labels), travel bloggers.

### 5.11 Verification list before any public claim

1. Check each competitor's current price and features on its own site and store listing.
2. Confirm TripIt and Tripsy export formats before naming them as import sources.
3. Verify Apple rules: metadata 2.3.7, competitor keyword bidding, custom product pages.
4. Confirm the letsgetrippy.com store listings, ratings, pricing and privacy policy.
5. Confirm Layla's status inside Expedia.
6. Confirm Wanderlog Pro price, offline policy and whether price-drop alerts exist.
7. Re-run the place accuracy study before publishing any number.
8. Legal review of /vs pages and any ad creative.

---

## 6. Pricing position

The plan's floor is Plus at $39.99 a year. The plan shows a 13% loss at $29.99, so do not cut below it. Compete on shape (Trip Pass, free collaboration, no lifetime, no tokens) and on value (fares, sources, offline), not on a lower annual price.

| Competitor | Reported price | Hermi position | Message |
|---|---|---|---|
| TripIt Pro | $49 a year, 30-day trial | Plus $39.99 a year is $9 lower and includes fare watch and planning | "Less than TripIt Pro, and you can plan with it." |
| Tripsy Pro | about $39.99 to $59.99 a year, monthly $4.99 to $9.99, weekly $3.99, lifetime about $299 (sources conflict) | Plus at or below the low end; Trip Pass $9.99 for one trip; no lifetime | "One trip? $9.99. No weekly or lifetime traps." |
| Wanderlog Pro | $39.99 a year (one source $49.99), $5.99 a month | Same annual price; Hermi gives offline and couple invites on Free | "Same price. Offline is free." |
| Layla Premium | about $49 to $49.99 a year, $9.99 a month | $10 lower, whole plan visible free | "No paywall before you see the plan." |
| Mindtrip | free consumer app, revenue from bookings | Free tier comparable; Hermi adds watching and sources | "Free to plan, honest about how we earn." |
| Stippl Pro | $24.99 a year, $3.99 a month | Not matched on price; Hermi Free includes offline and couple sharing | "The features behind Stippl's Pro are free here." |
| Trippy (letsgetrippy) | free to download; tiers not found | Free tier for groups via invitees joining free; Group Trip Pass in Phase 2 | Verify their pricing first |
| Google, ChatGPT, Kayak | free | Do not match free; sell follow-through and trust | "Free to start; pay when you want fare watching or more AI." |

Pricing rules:
1. Never go below $39.99 a year for Plus or below $9.99 for a Trip Pass without a margin check.
2. No lifetime plan (trust message against Tripsy's reported price).
3. No weekly plan.
4. Keep the annual trial at 7 days with price and date shown.
5. A/B test only the order and copy of paywalls, not hidden price differences.
6. The Trip Pass is the main tool against annual-only competitors: for a two-trip-a-year user it costs less than a year of any rival.
7. Switching reward is the free Trip Pass, not a discount on Plus.

---

## 7. Risks and how competitors might respond

| Risk | Likelihood | Effect | Response |
|---|---|---|---|
| Google adds source links and groups to Canvas | High | Narrows the evidence and group story | Keep depth: dated labels, stale flags, recheck, fare history over months. Emphasize neutrality and export |
| OpenAI or Google ships travel planning with better verification | Medium | Verify this plan becomes less unique | Make Hermi the place where the verified plan lives, with group and price watching. Keep the MCP server as a channel |
| Expedia folds Layla into its app and bundles it free | Medium | Layla's paywall complaint disappears | Lean on neutrality and "How we earn". Run a switching message if Layla changes |
| TripIt adds collaboration or AI with SAP backing | Low to medium | Their 22M base is large | Do not claim to replace TripIt; speed on planning and fares. Keep import so TripIt users can use both |
| Tripsy ships free sharing or Android editing | Medium | Removes a hook | Keep fares, stays, polls and group decisions; Tripsy is an organizer |
| Wanderlog adds sources or fare tracking | Medium | Closest overlap | Stay ahead on accuracy and billing trust; publish the accuracy note |
| Trippy (letsgetrippy) grows fast | Low to medium | Attacks the same organizer | Ship paste-your-group-chat early; watch monthly |
| Competitors copy evidence labels | Medium | Hero feature loses uniqueness | Depth: labels plus recheck plus stale flags plus published accuracy; be visibly first and best |
| Trademark or false advertising complaint about /vs pages or ads | Low to medium | Takedown, reputation | Evidence files, nominative use, counsel review, correction email |
| Apple rejects metadata or rules change | Low | Delay | Keep metadata free of competitor names; have a fallback listing |
| Price war (Wanderlog cut to $39.99 in 2026, reported) | Medium | Margin squeeze | Do not match; use passes and free features; watch unit cost |
| Live fare source (SerpApi) legal or cost failure | Medium | "Know the fare" weakens | Keep cached fares as baseline; apply for a licensed source; no comparative fare ads until licensed |
| AI errors despite the policy | Medium | Trust damage | Show "could not confirm", refund credits, publish measured accuracy, fast fix loop |
| Small team cannot keep up with a polish bar | High | Bad reviews | Cut scope before cutting polish; keep the recommended Phase 1 additions small |
| Reliance on competitor import paths (TripIt, Wanderlog changing exports) | Medium | Switching breaks | Use open formats (ICS, CSV, text); never use private APIs or credentials |

---

## 8. A 90-day post-launch competitive plan

Assumes launch at the end of month 6. All targets are starting hypotheses to tune against real data.

### Days 1 to 30: land and listen

- Week 1: launch on web and App Store. Publish the /vs pages, "How we earn", and the accuracy note. Post founder story on Product Hunt and Hacker News. Start Reddit helpfulness routine (3 real answers a day, no links unless allowed).
- Week 1: turn on Apple Search Ads test on TripIt, Tripsy, Wanderlog, Layla and Mindtrip (exact match, daily cap).
- Week 2: first creator cohort (5 to 10) posts. Start the TikTok series (2 videos a week).
- Week 2 to 4: read every review and support message. Tag each by competitor mentioned. Fix the top 3 issues.
- Week 4: first weekly competitor check (prices, releases, reviews). Record in a dated file.

### Days 31 to 60: sharpen

- Review switch import funnel: started, completed, Trip Pass redeemed, first plan, first invite. Fix the worst step.
- Publish the first "We checked the AI planners" study if the method and screenshots are verified.
- Ship the top recommended follow-ups: email-forward beta if pulled earlier, poll thin slice, Maps list import improvements.
- A/B test the paywall order and onboarding copy ("Coming from TripIt or Wanderlog?").
- Decide on continuing or stopping each Apple Ads group against the stop rule.
- Second creator cohort; drop creators who do not convert.

### Days 61 to 90: compound

- Start Phase 2 packs in priority order: email-forward, flight status, polls, Android.
- Publish a Hermi MCP server preview to a small group of Claude and ChatGPT users.
- Run the referral credit test (double credits weekend) if invite conversion is weak.
- Prepare the "Year in travel" card for December.
- Review the kill rule inputs early: paying share and affiliate income per monthly user.
- Write a retro: what competitor users said, which hook worked, which did not.

### Metrics that prove Hermi is winning

| Metric | Why it matters | Day 90 hypothesis |
|---|---|---|
| Switch imports per week (by source: TripIt, Tripsy, Wanderlog, Maps) | Direct evidence of taking users | 50 a week by week 12 |
| Import completion rate | Friction check | above 70% of started imports |
| Share of sign-ups from competitor terms (Search Ads, /vs pages, "alternative" search) | Are competitor users finding us | 15% of sign-ups |
| Verify this plan runs per week, and share that convert to a trip | Funnel from ChatGPT users | 200 a week, 40% convert |
| Paste group chat runs per week | Trippy answer works | 100 a week |
| Invite to join rate (couples and groups) | Viral loop | above 50% of invites joined |
| Free Trip Pass redeemed to paid conversion on the next trip | Payback of the switching offer | above 15% buy Plus or another pass within 6 months |
| Fare alerts sent and booked-fare drops flagged | Follow-through value | track count and user-reported savings |
| Crash-free sessions | Polish | above 99.8% |
| App Store rating and count | Trust and ranking | 4.7 or higher, 200 or more ratings |
| Reviews that mention a competitor | Are we winning their users | track, read each |
| First support reply time | Polish | under 4 hours weekdays |
| Paying share of monthly users (kill rule input) | Business health | above 1% by month 9 after launch, per plan |
| Cost per install on competitor keywords vs payback | Ad discipline | below Trip Pass payback or stop |
| Accuracy eval pass rate | Hero claim is real | above targets in section 4.2 |

---

## 9. Recommended changes to the Phase 1 build (for the owner to approve)

These are new, small and separate from what is already adopted. Adopted items (free invite of 1 collaborator, offline reading, switching import by ICS and paste with a free Trip Pass, booked-fare drop alert, calendar feed, evidence labels, sample trips, /vs pages, referral credits) are not repeated here.

1. **Verify this plan** (M): paste an itinerary from ChatGPT, Layla, Mindtrip or Gemini and check each place, hours and price with sources. Reuses paste import and research paths. The best funnel from the largest competitor.
2. **Paste your group chat** (M, light version): a `draft_trip` variant that reads pasted chat text and lists places, dates and "still undecided". Closes the Trippy Spark gap without building chat.
3. **Google Maps list and places-paste import, plus named Tripsy and Wanderlog entries on the import screen** (S to M): covers switching users who have no email or calendar export.
4. **Stale flag and one-tap recheck on evidence labels** (S): makes the hero feature hold up over time.
5. **Public "How we earn" page, plain billing page, and in-app one-tap cancel link** (S): trust features that answer the most repeated billing complaints.
6. **Public status page, "Synced N seconds ago" indicator, and a published accuracy note with a monthly eval** (S): the measurable polish bar.
7. **Repair-a-day, user-triggered, single day** (M): shows adaptive plans in demos. Proactive version stays Phase 2.
8. **Android web install guide and testing on Android Chrome** (S): makes "Android via web" real for mixed groups.
9. **Decision to consider, not assume:** pull email-forward import earlier (L). Recommend deciding at the month 4 review based on how the paste import performs in beta. If it is slow or fails often, pull it into month 5 or 6. Otherwise keep it Phase 2.

Cost note: items 1 to 6 and 8 are small and mostly reuse existing paths. Items 2 and 7 are the largest. If the month plan is tight, cut in this order: 7, then 2 (keep 1), then 3. Do not cut 4, 5 or 6; they are cheap and carry the trust message.
