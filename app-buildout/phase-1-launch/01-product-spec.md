# Hermi product specification, Phase 1

Part of the [Phase 1 build specification](README.md) and the [full build specification](../README.md). Written 2026-09-30. This file is the complete product specification for Phase 1 (months 1 to 6): everything the launch app does and nothing it does not. The Phase 1 scope in [README.md](README.md) is final. The shared decisions Phase 1 uses are repeated in section 1.4, so this file can be read on its own; the full tier ladder and the decisions for later phases are in [../README.md](../README.md).

Anything that ships later is replaced by a one-line pointer ("Later: Phase 2, see ...") where a reader would look for it, and is not specified here. Architecture, schema, API, screens and AI internals are in the other Phase 1 files and are referenced where they matter.

How to read a feature entry: each has a user story, acceptance criteria written as testable bullets, tier availability, credit cost, and edge cases. Feature ids (for example `F-FLT-3`) are stable and are reused by the roadmap and test plans; ids of features that ship later are not reused here. "Owner" means the trip owner, "editor" and "viewer" are trip roles (see F-COL-2). Tier codes in Phase 1 are `free`, `plus` and `trip_pass`; credit packs are consumables.

## 1. Product vision and principles

### 1.1 Vision

Hermi is where two or more people turn "we should go somewhere" into a booked, scheduled,
shared plan without a spreadsheet, a group chat full of links, or twelve browser tabs. It keeps
the decisions in one place (dates, flights, stays, days), lets everyone vote, watches fares for
you, and shows the whole plan as a clean full-screen presentation. AI does the tedious hunting
and always shows where each fact came from.

Positioning line: **Plan together. Know the fare.**

### 1.2 Principles

1. **Value before accounts, value before payment.** A visitor can start a trip with no account.
   No paywall appears before the user has built something.
2. **Everything cheap stays free.** Itinerary, lodging shortlist, presentation, checklist and
   export cost us almost nothing and are never gated behind money (only limits on counts, for
   example 8 saved stays on `free`).
3. **Meter only what costs real money.** Live fare checks, rental search and AI use credits or
   route quotas. Editing, saving and presenting never cost credits.
4. **Show sources.** Every AI-found fact carries the URL it came from. Fares must have been seen
   on a page during the run. Agent prices are labeled "indicative".
5. **Show the cost first.** Every credit spend shows its price before it happens; 6 credits or
   more needs a confirm.
6. **No dark patterns.** No banner ads, no fake urgency, no countdowns, the free path is always
   visible, "Not now" is always present, dismissing a paywall mutes it for 7 days, and at most
   one paywall per session.
7. **Commission never ranks anything.** Partner links exist on every tier in the same places,
   are labeled "We earn a commission if you book here.", and lists state how they are sorted.
8. **Your data is yours.** Export on every tier, delete account in the app, nothing locked on
   downgrade.
9. **Plain direct English.** Sentence-case headings, plain verbs, no em dashes or en dashes in
   product copy.

10. **Small groups, not thousands.** Collaboration is built for two to seven people per trip. Polling
    with conditional requests is enough; no real-time editing.

### 1.3 Platforms

iOS app (Capacitor wrapper around the React app, bundled) and the web app. Both ship the same
features except: purchases of subscriptions, Trip Pass and credit packs happen only through the App
Store in the iOS app (RevenueCat over StoreKit 2). There are no web purchases in Phase 1: the web
paywall says "Upgrade in the iOS app" and links to the App Store (see
[07-monetization-spec.md](07-monetization-spec.md)). Android users get the installable web app in
Phase 1, with an install guide (F-WEB-7) and testing on Android Chrome. Native Android and web
billing: Later: Phase 2, see [../phase-2-growth/README.md](../phase-2-growth/README.md).

### 1.4 Phase 1 shared decisions

These decisions are final and are used exactly as written in every Phase 1 file. The full ladder
(Family, Pro, Group Trip Pass, advisor seats) is in [../README.md](../README.md); those tiers are
not sold in Phase 1.

| Code | Name | Price (US) | Store product | Key limits |
|---|---|---|---|---|
| `free` | Free | $0 | none | 2 active trips, 1 cached-fare route per trip, 12 credits a month, one lifetime deep agent run ("taster"), 1 cached-fare alert, invite 1 collaborator per trip (so couples plan free), read-only share links, offline reading, joins others' trips free, checks up to 5 plan items per Verify run |
| `plus` | Plus | $5.99 a month, $39.99 a year | auto-renewing subscription, group `hermi_membership` | unlimited trips (fair use 25), 3 live routes checked daily within 120 days of departure, 60 credits a month, can invite up to 6 collaborators per trip, checks up to 12 plan items per Verify run |
| `trip_pass` | Trip Pass | $9.99 | non-renewing subscription, 90 days | one trip: 2 live routes, max 60 live checks, 40 credits, up to 6 collaborators, 12 plan items per Verify run |
| `credits_50` / `credits_150` / `credits_400` | Credit packs | $2.99 / $6.99 / $14.99 | consumable | purchased credits last 12 months and are spent last |

Rules: a trip's capabilities are the best of its owner's tier and any pass on that trip. Invitees
join free and get the trip's capabilities on that trip. AI credits are charged to the person who
starts the action. Apple Family Sharing is off. A Trip Pass can also be earned free by a first
import (F-IMP-3).

**AI credits.** 1 credit is a budget of up to $0.02 of provider spend.

| Action code | Credits | Hard stop |
|---|---|---|
| `explain` (Haiku short answer) | 1 | $0.01 |
| `live_search` (flight or rental) | 1 | $0.02 |
| `draft_day` | 1 | $0.03 |
| `draft_trip` | 4 | $0.10 |
| `research` | 8 (1 from shared cache) | $0.16; 5 searches, 8 fetches |
| `agent_run` (fare hunt or deep research) | 40 (8 from shared cache) | $0.80; 20 turns, 10 searches, 10 fetches, one at a time |
| `verify_plan` (Verify this plan: one checked item) | 1 per item, at most 5 per run on Free and 12 on Plus and Trip Pass | $0.02 per item; 1 search, 1 page |

The packing list (F-AI-9), booking import (F-AI-10, F-IMP-2), reading a pasted plan (F-AI-11 step 1) and the evidence recheck (F-AI-12) are priced as `explain`. Monthly
provider-spend ceilings: Free $0.25 (plus the one-time taster), Plus $2.25, Trip Pass $1.80; only purchased
credits raise a ceiling, never referral, taster or pass credits. Daily:
Free $0.05, Plus and Trip Pass $0.40. An agent run is admitted if the month has $0.80 of headroom,
even above the daily budget. Cached data always keeps working. Models: Claude Haiku 4.5
(`claude-haiku-4-5`) for short answers and page summaries, Claude Sonnet 5.5 (`claude-sonnet-5-5`)
for drafting, research and agents.

**Money that is not a subscription.**

- **Affiliate links** on every tier, same places, clearly labeled "We earn a commission if you
  book here." All outbound partner links go through `/go/{click_id}`. Phase 1 networks:
  Travelpayouts, Viator partner API, Stay22. Airbnb has no program: plain links only, and pasted
  listing links are never rewritten. The server never fetches Airbnb, Vrbo or Booking.com pages.
  Direct programs: Later: Phase 2, see [../phase-2-growth/README.md](../phase-2-growth/README.md).
- **Never**: banner ads, selling user data, ranking anything by commission, lifetime plans.
- Concierge, group payments and everything else that earns money later: see section 7.

**Non-negotiable rules.**

1. No banner ads, no dark patterns, no fake urgency. The free path is always visible.
2. Never rank search results, lists or suggestions by commission.
3. The server never fetches Airbnb, Vrbo or Booking.com pages, and uses no scrapers.
4. Every AI-found fact carries the source URL it came from and shows "Found on [site], checked
   [date]"; fares must be seen on a page during the run.
5. AI never gives insurance, visa or legal advice; it links to official sources.
6. Account deletion in the app, data export on every tier, and no data held hostage on downgrade.
7. Secrets only in environment variables, never in the repo.
8. No UI copy with em dashes; sentence case; plain verbs (see [05-ui-ux-spec.md](05-ui-ux-spec.md)).

## 2. Personas

### P1. Couple planners (primary)

Maya and Dev, both 30s, plan two to three trips a year together, often on phones in the evening.
Goals: agree on dates, find a fare that is not a rip-off, pick one stay they both like, and have
one place to look during the trip. Pain: links scattered across messages, one person doing all
the work, fare anxiety ("did it drop?"). Buys: Trip Pass for the big trip, annual `plus` if they
travel often.

### P2. Friend-group organizer

Sam organizes a bachelor weekend or a six-person ski trip. Goals: get everyone to agree on dates
and a stay, and keep the plan in one place. Pain: decision by attrition, Doodle plus WhatsApp plus a
spreadsheet. Buys: `trip_pass` ($9.99) because it is one fee and lets Sam invite up to 6 people.
Most invitees are `free` accounts. The Group Trip Pass, polls and cost splitting: Later: Phase 2, see [../phase-2-growth/README.md](../phase-2-growth/README.md).

### P3. Family

Priya, two kids, her parents joining for one week. Goals: one plan, simple daily schedule with
kid-friendly notes, everyone sees the same thing, including grandparents who will not install
anything. Pain: nap times, too many choices, cost. Buys: `plus` so the plan has room for everyone,
and uses read-only share links for grandparents. The Family plan: Later: Phase 2, see [../phase-2-growth/README.md](../phase-2-growth/README.md).

### P4. Deal hunter

Luis flies 8 to 12 times a year and watches fares obsessively. Goals: know when a fare drops on
the routes he tracks, find budget airline fares the price APIs miss, compare total trip cost, and
know if the fare he paid drops after he books. Pain: alerts that cry wolf, tools that hide how old
a price is. Buys: `plus` annual and credit packs for agent runs. Pro: Later: Phase 2, see [../phase-2-growth/README.md](../phase-2-growth/README.md).

### P5. Independent travel advisor (year 2)

Later: Phase 3, see [../phase-3-scale/README.md](../phase-3-scale/README.md).

### P6. Switcher

Jo has two years of trips in TripIt and a calendar full of bookings, and is deciding whether to
move. Goals: bring a current trip over without retyping it, keep it in the calendar app, see
whether the new app is worth paying for. Pain: re-entry, lock-in, subscriptions that overlap.
Buys: nothing at first; the first import includes a Trip Pass for that trip (F-IMP-3).

## 3. Core user journeys

Each journey lists the steps, the screens involved and the feature ids that implement them.

### 3.1 Sign up

1. Visitor opens the app. Splash shows one line of value, "Plan a trip" (no account) and
   "Sign in". (F-ACC-1)
2. Visitor taps "Plan a trip" and builds a guest trip stored on the device. (F-ACC-2)
3. On the first server feature (save, share, AI, second device), "Save your trip" appears.
   Visitor chooses Sign in with Apple, Google, or an email code. (F-ACC-3)
4. Guest data is claimed into the account. A skippable profile asks for display name, home
   airport and currency, creating the "Me" traveler. (F-ACC-4)
5. A card asks "Coming from TripIt, Tripsy or Wanderlog?" with "Bring your trips over" and "Start fresh".
   (F-ACC-7, F-IMP-1)

Success: account exists, trip is saved, no data was lost, no paywall was shown.

### 3.2 Create a trip

1. From trips home, "New trip". User types a destination; autocomplete suggests places.
2. User optionally adds more destinations, optional dates or a flexible month, a trip name, and
   home currency.
3. Trip overview opens with destination summary, photo, local time and money info, and an empty
   state that points to the next step (flights, stays, days). (F-TRP-1 to F-TRP-4)

### 3.3 Invite

1. After three or more items exist, a soft nudge offers "Invite your travel partner".
2. Any owner enters an email or copies a link and picks a role (editor or viewer). A `free` owner
   can invite 1 collaborator per trip, so a couple plans free; asking for a second collaborator
   shows the paywall moment (Trip Pass first). An owner on `plus`, or of a trip with a `trip_pass`,
   invites up to 6. (F-COL-3)
3. Invitee opens the link, installs or opens the web app, signs in, sees "You were added by
   <name>", and answers "Which traveler are you?". They join free. (F-COL-4)

### 3.4 Pick dates and flights

1. On Flights, owner adds a route: up to 4 airports per side, a departure window, and trip
   length in nights or a return window. (F-FLT-1)
2. Cached fares appear at once as a price calendar and a "Cheapest options" list. (F-FLT-2)
3. On a tracked route (paid tiers), live checks run daily within 120 days of departure.
   (F-FLT-3)
4. User taps "Choose" on a fare. Trip dates become the flight's dates. (F-FLT-5)
5. Optional: set a price alert. (F-FLT-6)
6. Chosen-flight card offers "Book on <provider>" (affiliate, labeled) and "Search on the
   airline's site". After booking, user marks it booked. (F-AFF-2)
7. When the user marks the flight booked, the app asks what they paid and watches the route and
   dates; if a comparable fare falls, a booked-fare drop alert says so. (F-FLT-8)

### 3.5 Shortlist and vote on stays

1. On Lodging, members add candidates by pasting a link, using the bookmarklet, typing details,
   or running "Search rentals" (1 credit, `live_search`). (F-LDG-1 to F-LDG-4)
2. Each member hearts favorites. Totals, per-night and per-person prices show in the trip
   currency. (F-LDG-5)
3. Members tick two to four places for side-by-side compare. (F-LDG-6)
4. Owner marks one "Booked". The booked stay feeds the itinerary and the checklist. (F-LDG-7)

### 3.6 Plan days

1. On Itinerary, a card per day shows city and first and last plans.
2. User opens a day, drags on the calendar to add items, drags ideas onto days, uses "Add
   activity" to search places on a map. (F-ITN-1 to F-ITN-5)
3. Optionally "Draft this day" (1 credit, `draft_day`) or "Draft my trip" (4 credits,
   `draft_trip`) gives a proposed plan the user accepts item by item. (F-AI-2)

### 3.7 Run an agent

1. From Agents, user picks "Hunt fares" or "Research a topic" for this trip.
2. Screen shows the credit price (40, or 8 if served from the shared cache) and a confirm.
   (F-AI-4)
3. Run page streams a live log. Saved fares and notes appear with source links; rejected items
   show why. User may stop the run. (F-AI-5, F-NTE-1)
4. Results appear under "Found by agents" on the overview and on the route. `free` users get one
   lifetime deep run as a taster. (F-AI-6)

### 3.8 Present

1. "Present" opens the trip as full-screen slides built from what is saved now. (F-PRS-1)
2. Keyboard, swipe, grid view, and PDF print work. A `free` trip shows a small "Made with
   Hermi" footer and PDF watermark. (F-PRS-2)
3. Owner can share the presentation as a read-only link. (F-COL-6)

### 3.9 Before you go

1. From 45 days before departure, or once a flight or stay is chosen, the checklist appears on
   the overview. (F-CHK-1)
2. User works through documents, bookings, eSIM, insurance, transfers, money, home and packing,
   marking each done or not needed. (F-CHK-2)
3. One opt-in push arrives 7 days before departure. (F-NOT-2)

### 3.10 Travel

1. A "Today" view shows the current day's plan, local time, and next item. (F-TRV-1)
2. The trip is readable offline (see section 6.2). (F-TRV-2)
3. The trip's live calendar feed keeps the plan in the user's own calendar app. (F-CAL-1)

### 3.11 After the trip

1. The day after the last trip date, a "How was the trip?" card appears, and after 14 days the
   trip is offered for archive. (F-AFT-2)
2. Export, archive or start the next trip from a past one (duplicate). (F-TRP-6)

The flight delay prompt, memories and the "Year in travel" card: Later: Phase 2, see [../phase-2-growth/README.md](../phase-2-growth/README.md).

### 3.12 Switch from TripIt, Tripsy or Wanderlog

1. On first run the onboarding card "Coming from TripIt, Tripsy or Wanderlog?" (or "Import a trip"
   on Trips home or in Settings) opens Import. (F-ACC-7)
2. The import screen lists entries named for TripIt, Tripsy and Wanderlog, plus Google Calendar and
   Google Maps. Each shows how to get the data out of that app and opens the matching method: a
   calendar file, a calendar feed link, pasted booking confirmations, a Google Maps list export or
   pasted places. (F-IMP-1, F-IMP-2, F-IMP-4, F-IMP-5)
3. A preview lists everything found. The user unticks anything wrong and taps "Import"; nothing is
   saved before that.
4. A new trip opens with flights, stays, reservations and saved places in place. When the import
   added at least 3 items including a flight or a stay, it shows "Your first import includes a
   Trip Pass for <trip>". (F-IMP-3)
5. Optional: for a calendar feed, turn on "Keep checking this calendar" so later changes arrive as
   a preview to confirm (F-IMP-6), and turn on the calendar feed so the trip shows in the user's
   own calendar app (F-CAL-1).

Success: the trip exists without retyping, and no TripIt, Tripsy, Google or Wanderlog password was
shared.

### 3.14 Check a plan from another AI

1. A user who planned in ChatGPT, Gemini, Layla or Mindtrip taps "Verify a plan" (Trips home "+"
   menu, a trip's menu, or the import screen) and pastes the text. (F-AI-11)
2. Hermi reads the places out of it (1 credit) and shows the list with the price of checking
   them ("Check 7 places for 7 credits"). The user picks the items to check, up to 5 on Free and 12
   on Plus and Trip Pass.
3. Each place comes back green (confirmed), amber (differs or only partly confirmed, with the
   source) or red (could not be found), with "Found on [site], checked [date]". Items that were not
   checked say so.
4. The user imports the confirmed items into the trip as a draft. Older findings later show "May
   be out of date" with a one-tap recheck. (F-AI-12, F-NTE-2)

Success: the user knows which parts of the AI plan hold up, sees the source for each claim, and
starts the trip from checked facts. No paywall appears before the first list of places.

### 3.13 Arrive from the web

1. A visitor lands from search on a sample trip, a shared-trip page or a comparison page
   (`/vs/...`). (F-WEB-1 to F-WEB-3)
2. They read it with no account and no app.
3. "Copy this trip", "Import your trips" or "Plan a trip" opens the app or guest mode. No account
   wall, no paywall. A friend's referral code can be applied at sign-in. (F-REF-1)

## 4. Feature catalogue

Conventions: "Tier" lists who gets the feature and any numeric limits. "Credits" lists the
action code and price, or "none". Acceptance bullets are testable at API or UI level.

### 4.1 Accounts and onboarding (F-ACC)

#### F-ACC-1 Sign in

- Story: As a new or returning user, I want to sign in with Apple, Google or an email code, so
  that I never manage a password.
- Acceptance:
  - Sign in with Apple, Google and a 6 digit email code are offered; Apple is listed first on iOS.
  - No password or SMS sign-in exists.
  - The email code expires in 10 minutes, allows 5 attempts, then is invalidated.
  - Email code sends are limited to 5 per email per hour and 20 per IP per hour.
  - A verified Supabase JWT resolves to a row in `users` through `auth_identities`; the client
    never sends role, tier or owner.
  - Apple "Hide My Email" relay addresses are stored as the account email and invites still
    arrive.
  - Users under the age gate (13, or 16 in EU and UK locales) are refused with a plain message.
- Tier: all. Credits: none.
- Edge cases: same email through Apple and Google creates one account only after the user
  confirms a link step; a disposable email domain is refused; sign-in with a deleted account
  inside its 30 day grace offers recovery.

#### F-ACC-2 Guest mode

- Story: As a curious visitor, I want to start a trip before signing up, so that I see value
  first.
- Acceptance:
  - A guest can create one trip with destinations, itinerary items and map, stored on device.
  - No `users` row exists until the guest uses a server feature; it is created with
    `is_guest=true`.
  - Guest AI, if used, draws from the `free` monthly allowance and requires device attestation.
  - Guest cannot invite, present shared links, or buy.
- Tier: pre-account. Credits: from the `free` allowance only.
- Edge cases: clearing site data loses a guest trip (the Save prompt warns once after the third
  item); a guest on a second device sees nothing until sign-in.

#### F-ACC-3 Save your trip (claim)

- Story: As a guest, I want to sign in and keep what I built, so that nothing is lost.
- Acceptance:
  - The prompt appears on invite, share, second device, AI beyond the guest allowance, or
    export.
  - On sign-in the guest trip is claimed into the account with one request; result shows counts.
  - If the identity already exists with trips, user chooses "Merge" or "Keep separate" with
    counts shown.
  - Claim is idempotent (double submit creates no duplicates).
  - If the claim would exceed the tier's active trip limit, the extra trip is kept as archived,
    not dropped.
- Tier: all. Credits: none.

#### F-ACC-4 Profile and "Me" traveler

- Story: As a new user, I want to set my name and home airport, so that flights default to my
  city.
- Acceptance:
  - Fields: display name, home airport (typeahead; location only if the user taps "near me"),
    currency (defaulted from locale), locale, time zone.
  - Saving creates one `people` row named "Me" linked to the user (`linked_user_id`).
  - The profile step can be skipped and finished later from Settings.
- Tier: all. Credits: none.

#### F-ACC-5 Onboarding for invitees

- Story: As an invitee, I want to land on the trip I was invited to, so that I can help right
  away.
- Acceptance:
  - An invite link opens the trip after sign-in with a banner "You were added by <name>".
  - No paywall, splash or profile step blocks first view.
  - "Which traveler are you?" lists the trip's travelers plus "I am new here"; choice links
    `people.linked_user_id`.
  - Invitee accounts start as `free` with the standard 12 credits and no bonus.
- Tier: `free` and up. Credits: none.

#### F-ACC-6 Consents

- Story: As a user, I want to control what is processed by AI and what marketing I get, so that
  I stay in charge of my data.
- Acceptance:
  - First use of any AI feature shows a consent screen naming the providers, what is sent, and
    that it is not used for training; acceptance is stored in `consents` with a version.
  - Revoking AI consent disables AI features only.
  - Marketing email is a separate opt-in, off by default, one click unsubscribe.
  - Owner can disable AI per trip; it then shows "AI is off for this trip" to all members.
- Tier: all.

#### F-ACC-7 "Coming from TripIt, Tripsy or Wanderlog?" onboarding

- Story: As someone switching from another planner, I want to be offered an import when I start,
  so that I do not retype my trips.
- Acceptance:
  - After sign-in and the skippable profile step, onboarding shows one card titled "Coming from
    TripIt, Tripsy or Wanderlog?" with "Bring your trips over" (opens the import screen, F-IMP-4)
    and "Start fresh". The card is shown once in onboarding and can be skipped.
  - The same entry stays available as "Import a trip" on Trips home (prominent when the user has no
    trips, otherwise in the "+" menu), in a trip's menu ("Import into this trip"), and in Settings.
  - Guests do not see the card before sign-up; a guest who taps Import gets the "Save your trip"
    prompt first (F-ACC-3).
  - No paywall and no credit charge appear in the card or the import choice screen.
  - Copy names the products as plain text; no third-party logos are used.
- Tier: all. Credits: none.

### 4.2 Trips and destinations (F-TRP)

#### F-TRP-1 Create and edit a trip

- Story: As a planner, I want to create a trip with a name, destinations and optional dates, so
  that I have a home for the plan.
- Acceptance:
  - Required: one destination. Optional: name, dates (or flexible month), party size, currency.
  - Dates can be empty; with a chosen flight, dates are locked to the flight (F-FLT-5).
  - Trip ids exposed to clients are UUIDs (`trips.id`).
  - Editing is optimistic with version checks; a stale edit returns 409 with the latest row and
    the UI shows a merge prompt.
- Tier: `free` 2 active trips; `plus` unlimited (fair use 25); `trip_pass` applies to the one
  passed trip.
- Edge cases: creating a third active trip on `free` shows the paywall moment with "Archive one"
  as the first option; trips joined from others do not count against the limit.

#### F-TRP-2 Destinations with lookup

- Story: As a planner, I want to add several destinations in order, so that multi-city trips
  work.
- Acceptance:
  - Autocomplete returns city, region, country with coordinates; results are cached.
  - Destinations can be reordered and each has optional arrival and departure dates.
  - Each destination stores a time zone used for every time shown for that place.
  - Removing a destination asks what to do with its itinerary items (move, keep as ideas,
    delete).
- Tier: all; up to 12 destinations per trip. Credits: none.

#### F-TRP-3 Destination info

- Story: As a planner, I want a summary, photo, local time and money info per destination, so
  that I get oriented fast.
- Acceptance:
  - Shows a short Wikipedia summary with attribution, a photo with credit, current local time,
    currency and exchange rate (ECB via FX).
  - Info refreshes in the background; failure shows the last good data with its age.
  - Text is labeled as sourced from Wikipedia; AI text is never mixed in.
- Tier: all. Credits: none.

#### F-TRP-4 Travelers

- Story: As a planner, I want traveler profiles (including kids and people without accounts), so
  that costs, flights and votes attribute correctly.
- Acceptance:
  - A traveler (`people`, attached to the trip through `trip_people`) has first name, color, home
    airport, and optional type (adult, child).
  - No birthdate or photo is stored for minors.
  - A traveler can be linked to at most one user per trip.
  - Removing a member detaches the link; the traveler stays and may be renamed "Former member".
- Tier: `free` 2 travelers per trip (the owner and the 1 collaborator a `free` owner may invite);
  `plus` and `trip_pass` 8.

#### F-TRP-5 Trip archive and trash

- Story: As a user, I want to archive finished trips and recover deleted ones, so that I free a
  slot without losing anything.
- Acceptance:
  - Archive frees an active slot; archived trips stay readable and exportable forever on every
    tier.
  - Delete moves the trip to trash for 30 days, then hard deletes; restore works in that window.
  - Only the owner can delete or archive.
- Tier: all.

#### F-TRP-6 Duplicate a trip

- Story: As a repeat traveler, I want to copy a past trip's structure, so that I reuse a good
  plan.
- Acceptance:
  - Duplicate copies destinations, itinerary items (dates shifted to a new start date), lodging
    candidates without votes, and checklist; it never copies members, notes or agent
    output.
  - Counts toward the active trip limit.
- Tier: all, subject to trip limits.

#### F-TRP-7 Trip overview

- Story: As a member, I want one page that says where the trip stands, so that I know what to do
  next.
- Acceptance:
  - Shows destinations, dates or "Dates not set", chosen flight, booked or shortlisted stay,
    itinerary progress, "Found by agents" notes, checklist card, and next suggested
    step.
  - Suggested next step follows a fixed order (destinations, dates or flight, stay, days,
    checklist) and never shows an upsell.
  - A limited-trip banner appears for the owner when a pass or plan has lapsed (F-SUB-6).
- Tier: all.

### 4.3 Collaboration, roles and invites (F-COL)

#### F-COL-1 Trip membership

- Story: As an owner, I want my partner or friends to see and edit the trip, so that we plan
  together.
- Acceptance:
  - `trip_members` holds trip, user, role, inviter; exactly one owner per trip.
  - Non-members get 404 (never 403) for any trip resource id.
  - Authorization is checked on every request, so removal takes effect immediately.
  - Activity items show "added by <name>".
- Tier: see F-COL-3 limits.

#### F-COL-2 Roles

| Capability | Owner | Editor | Viewer |
|---|---|---|---|
| View everything | yes | yes | yes |
| Edit itinerary, lodging, routes, notes | yes | yes | no |
| Vote, react | yes | yes | yes |
| Run AI (spends the actor's credits) | yes | yes | no |
| Invite editors | yes | no | no |
| Invite viewers, create share links | yes | owner setting | no |
| Delete trip, transfer ownership | yes | no | no |
| Leave trip | after transfer | yes | yes |

- Acceptance: each cell is enforced server side with one dependency; role and tier are never
  accepted from the client; a test walks every route with a viewer token and expects 404 or 403
  as defined above.

#### F-COL-3 Invite by email or link

- Story: As an owner, I want to invite people by email or link with a fixed role, so that I
  control access.
- Acceptance:
  - Token is random 128 bit, stored hashed in `trip_invites`, expires in 7 days, role fixed at
    creation; email invites are single use, link invites have a use cap (default 10).
  - Limits: 20 pending invites per trip, 30 invites per user per day.
  - Collaborator caps (members other than the owner, pending invites included): `free` owner 1 per
    trip; `plus` up to 6 per trip; `trip_pass` up to 6 for the passed trip.
  - A `free` owner's first invite is never gated, so a couple plans free. Asking for a second
    collaborator shows the paywall moment (Trip Pass first); the copy says "They join free". The
    owner's free alternatives are to keep the one collaborator or to share a read-only link
    (F-COL-6).
  - Owner can revoke a pending invite or remove a member at any time; a revoked or removed
    collaborator frees the slot immediately.
  - The invite email uses the inviter's display name and Hermi's sending domain.
- Tier: all owners invite, within the caps above; everyone can accept. Credits: none.
- Edge cases: expired token shows "Ask <name> for a new link"; invite email differing from the
  account email is accepted (the token is the proof); a member already on the trip is told so; if
  an owner's plan lapses and the trip exceeds the `free` cap, F-SUB-6 applies.

#### F-COL-4 Accept an invite

- Story: As an invitee, I want a link that just works, so that joining takes under a minute.
- Acceptance:
  - Universal link opens the app, or the web app, or an App Store page with an "enter code"
    fallback.
  - After sign-in the invite is redeemed server side and the user lands on the trip.
  - The invitee gets the trip's capabilities on that trip only; their own trips keep their own
    tier.
  - Joined trips do not count toward the invitee's active trip limit.
- Tier: all.

#### F-COL-5 Sync and conflicts

- Story: As a collaborator, I want to see my partner's changes quickly and never silently lose
  mine, so that we trust the plan.
- Acceptance:
  - Shared trips refresh on foreground and every 15 to 30 seconds with conditional requests
    (ETag or `updated_since`).
  - Every editable row has a version; a stale write returns 409 with the current row and the UI
    shows both versions with "Keep mine" and "Use theirs".
  - A simple activity feed lists changes newest first ("Maya added Lisbon food tour").
  - The trip header shows a sync indicator: "Synced 12 s ago" (seconds under a minute, then
    minutes, then the time), counted from the last successful sync response or accepted queued
    edit, refreshed every 5 seconds. Other states are "Syncing", "Offline, 3 edits waiting" and
    "Could not sync, retrying" (after three failed polls). Tapping it syncs now. It never shows a
    time for a sync that did not happen, is text as well as an icon, and screen readers are told of
    state changes only, not the ticking seconds.
- Tier: all on shared trips; the indicator is on every trip.

#### F-COL-6 Share links

- Story: As an owner, I want a read-only link for someone who will not install anything, so that
  grandparents and friends can look.
- Acceptance:
  - `trip_share_links` creates a public read-only web page of itinerary and map, with redaction
    flags on by default: hide exact lodging address, prices, notes and traveler names.
  - Default expiry 90 days (owner can choose 1 to 365); owner can revoke at any time; views are throttled per IP and token.
  - Page ends with "Get the app to edit" and shows the "Made with Hermi" footer on `free`
    trips.
  - Partner links on the page follow F-AFF rules and can be turned off by the owner.
  - Page layout, search indexing and evidence labels on shared pages are specified in F-WEB-1.
- Tier: all tiers create (a `free` owner's page carries the footer); anyone with the link views.

#### F-COL-7 Ownership transfer and leaving

- Story: As an owner, I want to hand a trip to someone else, so that it survives me leaving.
- Acceptance:
  - Owner selects an editor; the target must accept; the old owner becomes editor.
  - Capabilities follow the new owner's tier (or an existing pass on that trip).
  - A user who leaves keeps their attributed edits as "Former member".
- Tier: all.

### 4.4 Flights (F-FLT)

Reuse note: route, fare and choice logic carry over from the existing Trip Planner
(`backend/tripplanner/api/flights.py` and services).

#### F-FLT-1 Routes

- Story: As a planner, I want to describe where and when I might fly, so that Hermi looks at
  the right fares.
- Acceptance:
  - A route (`flight_routes`) has up to 4 origin and 4 destination airports, a departure window,
    and either trip length in nights or a return window; traveler count defaults to the trip's.
  - Airport search supports city names, codes and "nearby airports" with distances.
  - Validation: window must be in the future and at most 330 days out; nights 1 to 60.
  - Routes per trip (`routes_per_trip`): `free` 1; `plus` 5; `trip_pass` 3. Live-tracked routes
    (`live_routes`): `plus` 3; `trip_pass` 2. Routes beyond the live limit still work on cached
    fares.
  - `free` airports per side: 2; paid: 4.
- Tier: all, limits above. Credits: none.
- Edge cases: adding a second route on `free` shows a preview of its cached fares and the
  paywall; editing a route keeps its fare history.

#### F-FLT-2 Cached fares

- Story: As any user, I want to see recent fares for my route at no cost, so that I can judge
  prices.
- Acceptance:
  - Cached fares come from the Travelpayouts data API, refreshed daily server side, per adult,
    economy.
  - Every fare shows its age ("cached 6 h ago"), the source and "price can change".
  - Views: price calendar (date grid), history chart of the lowest price over time
    (`fare_observations`), "Cheapest options" table sortable by any column with filters for
    nights, dates, stops, airline, and "Cheapest by trip length".
  - Columns include Nights and Per night so a cheap fare on a short trip is visible.
  - Sort and filter state is shown; lists are never ranked by commission.
- Tier: all. Credits: none.

#### F-FLT-3 Live fares and tracking

- Story: As a deal hunter, I want live fares checked daily, so that I see real movement.
- Acceptance:
  - Live tracking runs one check per day per live route, only within 120 days of departure,
    through the flight provider interface (SerpApi behind a feature flag at launch).
  - Live route counts: `plus` 3, `trip_pass` 2 (max 60 live checks for the pass). Account-level
    routes for `plus` count across trips.
  - Checks stop when the month's provider-spend ceiling is hit; the UI says "Live checks resume
    on the 1st" and cached fares continue.
  - A live observation is stored in `fare_observations` with provider, fetched time and cost in
    micro-dollars, and logged in `provider_calls`.
  - Identical searches by different users within 6 hours reuse one result.
- Tier: `plus`, `trip_pass`. Credits: none for scheduled checks.
- Edge cases: a route beyond 120 days shows "Live checks start on <date>"; if the provider flag
  is off, the UI shows cached fares only with no error.

#### F-FLT-4 Refresh now (live peek)

- Story: As any user, I want a live price right now, so that I can decide today.
- Acceptance:
  - "Refresh now" runs one live search for the route and costs 1 credit (`live_search`), shown
    before the tap.
  - A result under 6 hours old is returned free and says so.
  - Failure or an empty result is refunded automatically.
  - Available to every tier; `free` pays credits from its 12 monthly.
- Tier: all. Credits: `live_search` 1.

#### F-FLT-5 Choose a flight

- Story: As a planner, I want to lock a fare, so that the trip's dates follow it.
- Acceptance:
  - "Choose" on a fare row or date grid cell sets `chosen_flights` and the trip's start and end
    dates to the flight's departure and return.
  - While a flight is chosen, trip dates change only by choosing another flight or clearing
    ("Clear" under "Your flight").
  - Later checks look at the chosen dates first and show price movement against the chosen
    fare.
  - The card shows fare age, route, stops and a "Mark as booked" toggle; marking it booked asks
    what the person paid (F-FLT-8).
  - Itinerary days outside the new dates are kept as ideas, never deleted.
- Tier: all. Credits: none.

#### F-FLT-6 Price alerts

- Story: As a deal hunter, I want to be told when a fare drops, so that I do not watch it.
- Acceptance:
  - An alert (`price_alerts`) sets a target price or "any drop of X percent" on a route.
  - `free` gets 1 alert on cached fares; `plus` 3; `trip_pass` 2; paid tiers alert on live and
    cached fares. The booked-fare drop alert (F-FLT-8) is separate and does not use these counts.
  - Notification: push and in-app, at most one per route per day; text states amount and since
    when ("Fare fell $42 since Tuesday"); tapping opens the route. Emails link to the in-app
    route, not to a partner.
  - Alerts exist only for routes the user tracks; there are no promotional alerts.
  - Alert setup asks for push permission with a reason screen if not yet granted.
- Tier: all, with counts above. Credits: none.

#### F-FLT-7 Agent-found fares

- Story: As a deal hunter, I want fares from budget airlines and sales that APIs miss, so that I
  see the full market.
- Acceptance:
  - Agent fares appear on the route labeled "Indicative", with the source URL, date seen, and
    currency; they are never mixed into cached or live charts without the label.
  - The rules in F-AI-5 apply.
- Tier: via agent runs (F-AI-4).

#### F-FLT-8 Booked-fare drop alert

- Story: As a traveler who has booked, I want to know if the fare I paid drops later, so that I can
  check whether the airline would change or credit my ticket.
- Acceptance:
  - When the user marks a chosen flight as booked (F-FLT-5), or accepts an imported booked flight
    (F-IMP-1, F-IMP-2), the app asks "What did you pay?" with the fare price prefilled (total for
    all travelers, with currency) and a switch "Tell me if this fare drops", on by default and
    changeable later on the flight card. Skipping stores no watch.
  - The watch compares the amount paid with the lowest fare found for the same origin and
    destination airports, dates, cabin (economy) and traveler count, from cached fares on every
    tier and from live checks where the trip already has a live route. It never starts a provider
    call of its own, and it stops at departure.
  - An alert fires when the comparable fare is lower than the amount paid by at least 5 percent and
    by at least $10 (the equivalent after conversion to US dollars), and lower than the last price
    alerted. At most one alert per flight every 7 days.
  - Alert text states both numbers, the source and the age, and points to the airline's own rules:
    "You paid $480. It is now $431 (cached, checked 3 h ago). Check the airline's change and
    credit rules." Push and in-app (F-NOT-1 type price alert); email links to the flight card. The
    alert never carries a partner link.
  - The flight card shows "Your booked fare": amount paid, the current comparable fare with source
    and age, the difference, and a link "Airline change and credit rules" that opens the airline's
    own site (non-affiliate). No Book button, partner card or paywall appears on it.
  - Copy never promises a refund or credit and never gives legal advice. The card says "This is the
    lowest fare we found for those dates. It may be a different flight."
  - A watch is a `price_alerts` row with `kind = 'booked_drop'`; one watch per booked flight; it
    does not count against the alert limits of F-FLT-6.
- Tier: all. Credits: none.
- Edge cases: an amount paid in another currency converts with the ECB rate for the comparison and
  shows the conversion date; a removed booked flight or changed dates retires the watch; comparable
  data older than 48 hours pauses alerts and the card says "Fares are stale" rather than alerting
  from old data.

### 4.5 Lodging (F-LDG)

Hard rules: the server never fetches Airbnb, Vrbo or Booking.com pages; pasted links are never
rewritten; no ranking by commission.

#### F-LDG-1 Shortlist a stay manually

- Story: As a member, I want to add a place I found anywhere, so that all candidates live in one
  list.
- Acceptance:
  - Fields: name, URL (optional), dates, guests, total price, currency, bedrooms, rating,
    photos, notes, status.
  - Pasting a URL extracts dates and guest counts from the URL text only, never by fetching.
  - "Get title and photo" is disabled for Airbnb, Vrbo, Booking.com, Expedia Group and other
    partner hosts on the hosted server; for other hosts a one-page fetch is allowed only if legal
    review passes (feature flag off by default).
  - Saved limit: `free` 8 per trip (9th goes to a locked "Later" list that stays visible);
    `trip_pass` 30; `plus` unlimited (fair use 100).
- Tier: all, limits above. Credits: none.

#### F-LDG-2 Bookmarklet import (web)

- Story: As a desktop user, I want to save a listing with one click from any site, so that I skip
  copy and paste.
- Acceptance:
  - A draggable "Save to Hermi" bookmarklet opens the app with name, photos, price and rating
    that the page in front of the user exposes, ready to review and save.
  - The bookmarklet reads only the open page in the user's own browser; the server never visits
    the site.
  - A Safari share-sheet equivalent on iOS (share extension) is a later item.
- Tier: all.

#### F-LDG-3 Status and per-night math

- Story: As a planner, I want totals per night and per person, so that stays are comparable.
- Acceptance:
  - Each card shows total, per night, and per person in the trip currency; other currencies
    convert with the latest ECB rate and show "converted on <date>".
  - Status: Considering, Shortlisted, Booked, Not for us. Only one stay per date range can be
    Booked; a second Booked asks for confirmation.
  - Changing dates recomputes per-night values.
- Tier: all.

#### F-LDG-4 Rental search

- Story: As a planner, I want to search priced rentals for my dates, so that I find options
  without leaving Hermi.
- Acceptance:
  - "Search rentals" takes destination, dates and guests, and lists priced results from licensed
    hotel and rental partners.
  - Each search costs 1 credit (`live_search`), shown before the tap; repeating the same search
    within 12 hours is free.
  - Rows show provider name and the sort statement ("Sorted by price, lowest first"); sort
    options are price and rating only.
  - "Save to shortlist" is the first action on each row; "View" (affiliate, labeled) is second.
  - Airbnb listings may not appear and the UI says so.
- Tier: all. Credits: `live_search` 1.

#### F-LDG-5 Votes

- Story: As a member, I want to heart stays I like, so that we see what the group prefers.
- Acceptance:
  - Each member hearts a stay once (`lodging_votes`), attributed to the user and their traveler.
  - Viewers can vote; vote counts and names are visible to all members.
  - Sort by hearts, price, rating or date added; the sort in use is always shown.
  - Removing a member keeps their votes attributed to "Former member".
- Tier: all.

#### F-LDG-6 Compare

- Story: As a member, I want to put stays side by side, so that I can choose.
- Acceptance:
  - Tick 2 to 4 stays (`free`: 2) to compare price, per night, per person, rating, bedrooms,
    hearts, distance to planned activities, with lowest price and best rating marked.
  - A map shows the stays and the planned activities.
- Tier: `free` 2, all others 4.

#### F-LDG-7 Partner links on stays

- Story: As a user, I want my own link to stay mine, so that I trust the app.
- Acceptance: follows F-AFF-3 (Open shows the user's link unchanged; separate labeled "Book via
  partner" only where a program is approved; never for Airbnb).

### 4.6 Itinerary, places and map (F-ITN)

#### F-ITN-1 Days

- Story: As a planner, I want a card per day, so that I see the shape of the trip.
- Acceptance:
  - Days (`itinerary_days`) are generated from trip dates; each shows city and first and last
    plan. With no dates, days are "Day 1, Day 2" and convert when dates are set.
  - Each day has an optional title and notes; destination per day defaults from destination
    dates.
- Tier: all.

#### F-ITN-2 Day calendar

- Story: As a planner, I want to drag plans on a calendar, so that scheduling is quick.
- Acceptance:
  - Dragging on empty time creates an item; dragging a block moves it; dragging its bottom edge
    changes duration; clicking edits, moves to another day, or deletes.
  - Times are in the destination's local time regardless of device time zone; an evening can end
    after midnight.
  - Each item has one category (`itinerary_items.category`: sights, museum, food, nature,
    nightlife, shopping, travel, other) and a status (idea, planned, booked); a lodging check-in
    or check-out is an item in `travel` or `other`, and free time is a day with no items.
  - Order within a day is start time, then `sort_order`.
  - Keyboard alternative exists for every drag action (see section 6.3).
- Tier: all.

#### F-ITN-3 Ideas

- Story: As a planner, I want to park ideas without a day, so that I capture everything.
- Acceptance:
  - An "Ideas" list holds `itinerary_items` with no day; "+" or drag assigns a day and time.
  - Ideas can be hearted by any member.
- Tier: all.

#### F-ITN-4 Place search

- Story: As a planner, I want to find restaurants and sights on a map, so that I can add them
  fast.
- Acceptance:
  - Category chips: restaurants, cafes, museums, landmarks, viewpoints, parks, beaches,
    nightlife, shopping; or type a name.
  - A country or region is searched fully ("All of Costa Rica"); a city is searched within a
    chosen radius in miles or km by locale; "Search this area" searches the map view.
  - Results (from `places_cache`, 1 week) show opening hours, website, Wikipedia summary when one
    exists, and a Google Maps link; order is relevance and distance only.
  - "Add your own" creates a free-text item with optional address.
  - Geoapify and OpenStreetMap attribution is visible.
  - Soft limits per day: `free` 30 searches, `plus` and `trip_pass` 100; cached results always
    work.
  - "Save place" puts it in the trip's `saved_places` shortlist.
- Tier: all. Credits: none.

#### F-ITN-5 Map

- Story: As a traveler, I want a map of the day, so that I see how far things are.
- Acceptance:
  - MapLibre map shows day stops numbered in order; tapping a pin opens the item.
  - If WebGL is unavailable, a simple list plot replaces the map with a notice; all other
    features still work.
  - Print view draws stops as a static plot.
- Tier: all.

#### F-ITN-6 Booked items and tickets

- Story: As a traveler, I want to attach confirmations to items, so that I find them on the go.
- Acceptance:
  - An item can store a booking link (user's own, unchanged) and notes, where the person can
    also keep a confirmation number.
  - Bookable items show a "Tickets" action per F-AFF-4 where a program applies.
- Tier: all.

### 4.7 AI features (F-AI)

Full technical detail is in [06-ai-agents-spec.md](06-ai-agents-spec.md). User-facing rules:

- Every AI action shows its credit price first; 6 credits or more needs a confirm.
- Failed, timed out or empty actions are refunded automatically.
- The requester's balance is charged. A trip owner cannot be drained by collaborators.
- AI never gives insurance, visa or legal advice; it links to official sources.
- Affiliate content never appears inside AI output and AI never steers to a partner.
- When a monthly or daily spend ceiling is reached, AI and live actions pause with a plain
  message; cached data keeps working.
- AI consent is required before first use (F-ACC-6).

#### F-AI-1 Explain

- Story: As a user, I want a quick answer about a fare, place or plan, so that I decide faster.
- Acceptance:
  - An "Explain" button on a fare, place or item returns a short answer (under 400 tokens) from
    Claude Haiku 4.5 using only that item's data and trip dates.
  - Costs 1 credit (`explain`); a repeat of the same question within 6 hours is free.
  - Answers never claim "best price" or "lowest"; they cite the data they used.
- Tier: all, from the user's credits. Credits: `explain` 1.

#### F-AI-2 Drafts

- Story: As a planner, I want a proposed day or whole plan, so that I start from something.
- Acceptance:
  - "Draft this day" (`draft_day`, 1 credit) proposes 4 to 8 timed items for one day in the
    destination; "Draft my trip" (`draft_trip`, 4 credits) does up to 14 days; longer trips bill
    per 14 days.
  - Output is a preview. Nothing is saved until the user accepts items; "Accept all" and
    per-item accept exist.
  - Places named come from place search, so each has coordinates and hours; ungrounded names are
    dropped.
  - Private notes are not sent to the model; other travelers' names are replaced with
    "Traveler 1" and so on.
  - Input text limit 2,000 characters; identical request within 6 hours returns the earlier
    result free.
  - At zero credits the UI shows a blurred preview of day one and the credit-pack or Plus offer.
- Tier: all. Credits: `draft_day` 1, `draft_trip` 4. Model: Claude Sonnet 5.5.

#### F-AI-3 Research question

- Story: As a planner, I want a sourced answer to "what events are on during our dates?", so
  that I do not search myself.
- Acceptance:
  - Costs 8 credits (`research`), or 1 when served from the shared research cache (same
    destination, same topic, under 7 days old); the price shown before the tap says which.
  - Caps: 5 searches, 8 fetches, $0.16 hard stop.
  - Result is a note with bullet findings, each with a source URL and "seen on <date>".
  - Airbnb, Vrbo and Booking.com are never opened.
  - User can save findings to the notes feed and convert one to an idea or itinerary item.
- Tier: all. Credits: `research` 8 (1 cached).

#### F-AI-4 Agent runs

- Story: As a deal hunter, I want an agent to hunt fares or research a topic in depth, so that I
  get more than the APIs show.
- Acceptance:
  - Two kinds: "Hunt fares" (for a route) and "Deep research" (a topic). Both cost 40 credits
    (`agent_run`), or 8 if served from the shared cache, with the confirm screen stating which.
  - Caps: 20 turns, 10 web searches, 10 page fetches, $0.80 hard stop, one run at a time per
    account; a run is admitted if the month has $0.80 of provider-spend headroom, even above the
    daily budget.
  - User stop bills pro rata by turns used with a minimum of 8 credits; failed runs with nothing
    saved are refunded.
  - Runs wait in a queue and show "Queued, position N".
  - Each run is a row in `runs` with events in `run_events`, charged through `credit_ledger`.
  - A run page streams the log, shows saved fares and notes with sources, rejected items with
    reasons, tokens used, and credits charged.
- Tier: all tiers for manual runs (credits only). Credits: `agent_run` 40 (8 cached).
- Edge cases: starting a run with a run in progress is refused with a link to it; ceiling hit
  mid-run ends the run with results so far and a pro rata charge.

#### F-AI-5 Evidence rules

- Story: As a user, I want every AI fact to be checkable, so that I can trust it.
- Acceptance:
  - A saved fare must include route, airports, dates, a public source URL, price, currency, and
    must have been seen on a page during the run.
  - Items failing validation are stored as rejected with a reason and are never shown as facts.
  - Blocked domains (Airbnb, Vrbo, Booking.com) are refused as sources.
  - Agent prices are labeled "Indicative: seen on the linked page, not live-checked".
  - Agents write only through the ingest tools scoped to one run, one trip and one user, and
    cannot read other trips.
- Tier: all.

#### F-AI-6 Taster

- Story: As a free user, I want to try a deep agent run once, so that I can see if it is worth
  paying for.
- Acceptance:
  - Each `free` account gets one lifetime deep run (`agent_run`) at no credit cost, on top of
    12 monthly credits; it is served from the shared cache when possible.
  - The taster has a separate allowance (one-time $0.80 spend) and never reduces credits.
  - The taster button says "Try a deep run free (once)" and disappears after use; state is
    server side and tied to the account and device attestation.
  - After the run, the paywall moment shows a credit pack and the Trip Pass, with "Not now".
- Tier: `free` only. Credits: none for the taster.
- Edge cases: a failed taster run that saved nothing does not consume the taster.

#### F-AI-7 Scheduled routines (Pro)

Later: Phase 2, see [../phase-2-growth/README.md](../phase-2-growth/README.md).

#### F-AI-8 AI metering and limits

- Story: As the business, I want no account to cost more than it pays, so that the product
  survives.
- Acceptance:
  - Monthly provider-spend ceilings and daily budgets are enforced on the server as in section
    1.4; the ledger fails closed if it cannot be read.
  - AI endpoints are limited to 10 per minute per account and 30 AI actions per hour.
  - Trip Pass credits are spent before purchased credits.
  - The balance and history are visible in Settings; the client never decides balance.
- Tier: all.

#### F-AI-9 Packing list

- Story: As a traveler, I want a packing list that fits the weather and my plans, so that I
  pack once.
- Acceptance:
  - "Suggest a packing list" in the Before you go checklist (packing group) returns 18 to 35 short
    lines grouped as clothing, toiletries, documents, electronics, health and other, from the
    destination, dates, daily weather numbers, activity categories and party size (adults and
    children). No names, notes or product links are sent or returned.
  - Costs 1 credit (`explain` price class, Haiku 4.5, hard stop $0.01); the same inputs within 7
    days return the earlier list free. The result is a preview: the lines the person keeps are
    saved as tick-off checklist rows (`checklist_items` with `kind = 'packing'`, `source = 'ai'`).
  - Documents lines never state a visa, vaccine or insurance requirement; they point to official
    sources.
  - Kill switch `ai.packing`; needs AI consent and `trips.ai_enabled`.
- Tier: all, from the user's credits. Credits: `explain` 1. Model: Claude Haiku 4.5.

#### F-AI-10 Booking import

- Story: As a planner, I want to paste a confirmation email and have it become a flight, stay or
  activity entry, so that I do not retype it.
- Acceptance:
  - "Paste a booking" (Flights, Stays, Add item) takes pasted text up to 12,000 characters and
    returns a draft flight, stay or activity with dates, places, amounts and references only as
    the text states them; missing fields stay empty.
  - Personal data in the text (names, emails, phone numbers, booking references, frequent flyer
    numbers) is replaced with placeholders before the model call and restored into the draft
    locally. The server never fetches a link in the text.
  - Costs 1 credit (`explain` price class, Haiku 4.5, hard stop $0.01); text with no booking in it
    is refunded and says so. Nothing is saved until the person accepts: a flight or activity
    becomes an itinerary item (`source = 'import'`, flights as `travel`, `booked`), a stay becomes
    a lodging option (`status = 'booked'`).
  - Kill switch `ai.import`; needs AI consent and `trips.ai_enabled`.
- Tier: all, from the user's credits. Credits: `explain` 1. Model: Claude Haiku 4.5.
- The switching import (F-IMP-2) uses this same pipeline for several pasted confirmations in one
  session.

#### F-AI-11 Verify this plan

- Story: As someone who planned a trip in ChatGPT, Gemini, Layla or Mindtrip, I want to paste the
  plan and see which places, opening hours and prices hold up, so that I do not check each one by
  hand.
- Story: As a planner who found some problems, I want to import only what checked out, so that my
  trip starts from facts and I can see where each one came from.
- Acceptance:
  - Entry points: "Verify a plan" in the "+" menu on Trips home, in a trip's menu, and on the
    import screen. It runs inside a trip (a Free owner at the 2 active trip limit is offered "Check
    it inside one of your trips"); a person starting from Trips home can create the trip from the
    plan's first destination.
  - Step 1, read the plan: the person pastes text of up to 8,000 characters and optionally says
    which assistant wrote it (ChatGPT, Gemini, Layla, Mindtrip or other, shown but never trusted).
    Personal data is replaced with placeholders before the model call (F-AI-10 rules). Hermi
    lists up to 25 items (place, day, time, stated hours, stated price). Costs 1 credit (`explain`
    price class), shown before the tap; text with no places is refunded and says so. The text is
    never stored and no link in it is opened.
  - The list shows the price of step 2 before anything is checked: "Check 7 places for 7
    credits" (1 credit per checked item). A check of 6 or more items asks for the usual confirm.
    The person ticks the items to check; the cap per run is 5 on Free and 12 on Plus and Trip Pass.
    Items over the cap stay "Not checked" and can be checked in another run, each run priced on its
    own.
  - Step 2, check: for each selected item Hermi looks the place up in place data, uses the
    shared cache when it has a fresh answer, and otherwise reads at most one page, to confirm that
    the place exists, that the stated opening hours fit the planned day and time, and that a stated
    price is within 15 percent of the page. The result is one of:
    - Green "Confirmed": the place exists and everything the plan stated was confirmed.
    - Amber "Differs" or "Partly confirmed": the place exists but a stated hour or price differs
      or could not be confirmed. The row says which field and shows what the source says ("Closed
      Mondays. Your plan has Monday at 10:00").
    - Red "Could not find it": no place data and no page names it.
    - "Not checked" with a reason: over the cap, the cost limit was reached, the source is an
      Airbnb, Vrbo or Booking.com page (never opened), or a provider error (the credit is
      refunded).
  - Every green and amber item shows the evidence label "Found on [site], checked [date]" linking
    to the page. Colors always come with a word and an icon. A red item is never shown as a fact
    and never appears on a trip until the person chooses to add it.
  - The header states what was done, not a score: "Checked 7 of 9. 5 confirmed, 1 differs, 1 not
    found. 2 not checked." Hermi never calls a whole plan "verified".
  - The worker saves verdicts only with their evidence; a person cannot edit a verdict or a date.
    Only the tick marks for checking and importing are editable.
  - Credits are reserved for the selected items and settled to the items that ended green, amber
    or red; unchecked items, provider errors and a run that finds nothing are refunded.
  - "Add to trip" imports the ticked items as itinerary items (`source = 'verify_plan'`, status
    `idea`, or `planned` when the plan gave a day) with their evidence. Green items are ticked by
    default, amber items after the person has opened them, red items never. Importing costs nothing
    and nothing is saved before the tap.
  - Results stay available for 30 days on the trip ("Plan checks") and are then deleted with their
    evidence; items already imported stay.
  - Needs AI consent and `trips.ai_enabled`; kill switch `ai.verify` and flag `verify_plan`. No
    partner link, affiliate card or paywall appears on the screens. At zero credits the normal
    credit paywall appears only when the person taps "Check".
- Tier: all. Credits: `explain` 1 to read the plan, then `verify_plan` 1 per checked item (at most
  5 on Free and 12 on Plus and Trip Pass per run). Model: Claude Haiku 4.5.
- Edge cases: a plan with more than 25 places reads the first 25 and says so; a plan longer than
  8,000 characters asks for one trip at a time; two items that match the same place are merged into
  one row; an item that duplicates something already on the trip is marked "Already on your trip"
  and left unticked; a place whose stated price is in another currency is converted with the ECB
  rate for the comparison only; a closed-for-renovation or renamed place is amber with the page
  that says so.

#### F-AI-12 Evidence recheck

- Story: As a planner with an older finding, I want to ask again whether the page still says the
  same thing, so that I do not plan around stale facts.
- Acceptance:
  - An AI-found finding (a note from an agent run) or a checked plan item whose evidence is more
    than 14 days old shows "May be out of date" next to its evidence label (F-NTE-2) and a
    "Recheck" button. The flag is computed from the date on the label; nothing is sent or changed
    in the background.
  - "Recheck" costs 1 credit (`explain` price class), shown first. It opens the stored source page
    once and tells the person one of four things: still the same (the label date moves to today),
    changed (what the page says now, with the source, and "Save as a note"; the old text is not
    overwritten), no longer shown, or unreachable (nothing is charged).
  - Rechecking never searches the web, never opens Airbnb, Vrbo or Booking.com, and never changes
    a trip item by itself.
  - Editors and owners can recheck at any time, not only after 14 days; viewers see the flag only.
  - Kill switch `ai.recheck`; needs AI consent and `trips.ai_enabled`.
- Tier: all, from the user's credits. Credits: `explain` 1. Model: Claude Haiku 4.5.
- Edge cases: fares are not rechecked here (they show their own age and "Refresh now", F-FLT-4); a
  finding with several sources rechecks the first and offers the others in turn.

### 4.8 Notes and evidence (F-NTE)

#### F-NTE-1 Notes feed

- Story: As a member, I want one feed of findings and notes with sources, so that nothing gets
  lost.
- Acceptance:
  - `notes` hold human notes, AI findings and saved research, each with author or "Found by
    agents", timestamp and (for AI) source URLs.
  - A finding can be converted into an idea, an itinerary item, or a lodging candidate in one
    tap.
  - Notes can be marked private to the author; private notes are never sent to AI and never
    shown in share links or presentations.
  - Owners can delete any note; authors can delete their own; deleting an AI finding does not
    refund credits.
- Tier: all.

#### F-NTE-2 Evidence view and evidence labels

- Story: As a skeptical user, I want to see where a fact came from and when it was checked, so
  that I can verify it.
- Acceptance:
  - Every AI-found item (a fare, a finding, a research bullet, a saved note) shows the evidence
    label "Found on [site], checked [date]", for example "Found on theflightsite.com, checked 12
    Sep". [site] is the domain of the source; [date] is the day the agent saw the fact on that
    page (`seen_at`), in the user's date format. The label is a link that opens the original URL.
  - The label appears wherever the item appears: route cards and fare rows, the Found by AI list,
    the run page, presentation slides, share pages and PDF export.
  - With more than one source the label shows the first and "and 2 more", which opens the list.
  - Freshness: an AI-found finding or checked plan item whose label date is more than 14 days old
    shows "May be out of date" beside the label and a one-tap "Recheck" (F-AI-12). It is not removed
    or hidden. An item whose source later fails to load is also not removed: it shows "Source not
    checked since <date>" in place of "checked <date>".
  - The run page lists rejected items and why (F-AI-5). Rejected items never wear the label
    because they are never shown as facts.
  - Fares add "Indicative: seen on the linked page, not live-checked" (F-AI-5) next to the label.
  - Non-AI content keeps its own attribution (Wikipedia, Geoapify, notes people wrote) and never
    wears the label.
- Tier: all. Credits: none.

### 4.9 Presentation mode (F-PRS)

Reuse note: extends the existing `presentation` page.

#### F-PRS-1 Slides

- Story: As a planner, I want to walk my partner or group through the plan, so that we decide
  together.
- Acceptance:
  - Built from current data: title slide; one slide per destination (summary, local time,
    money, map); one per flight route (cheapest fares and price trend); the stay shortlist; one
    per day with plans (timeline and map); a closing summary; empty sections are skipped.
  - Optional last slide "Book the plan" lists every partner link with the disclosure sentence;
    the owner can turn it off; no partner content appears during normal slides.
  - Notes marked private are excluded.
- Tier: all. Credits: none.

#### F-PRS-2 Controls and print

- Story: As a presenter, I want simple controls and a PDF, so that I can present or hand it out.
- Acceptance:
  - Right arrow or Space next, left arrow back, Home and End, F for full screen, G for grid, Esc
    exits; swipe on touch.
  - The URL ends with the slide number (`/present#5`) and a reload keeps the place.
  - Print or Save as PDF gives one 16:9 page per slide; maps print as a static stop plot;
    partner links stay live in PDF with the disclosure sentence printed, except the checklist,
    which prints without affiliate buttons.
  - `free` trips show a small "Made with Hermi" footer and PDF watermark; paid and passed trips
    do not.
  - No affiliate card or paywall appears during playback.
- Tier: all (footer and watermark on `free` only).

### 4.10 Before-you-go checklist (F-CHK)

#### F-CHK-1 Checklist

- Story: As a traveler, I want a list of what I still need, so that I arrive prepared.
- Acceptance:
  - Appears on the overview when the trip has a chosen flight or a saved stay, or 45 days before
    departure, whichever is first; also in presentation mode and offline.
  - Items (`checklist_items`, fixed enum of kinds): flights booked, stay booked, tickets for top
    items, airport transfer or car, eSIM (international only), travel insurance (only after a
    chosen flight or booking), documents (passport validity, visa or e-authorization,
    vaccinations, linking to official government sites first), luggage storage (late departure),
    money (tell the bank, cash, no-fee card), home (mail, pets, out-of-office), packing list
    (from weather; the optional AI packing list is F-AI-9).
  - At least half of the items carry no affiliate link.
  - Each partner item shows what it is, why it is here ("You land in Lisbon at 21:40"), cost
    range if known, and three actions: "Get it" (affiliate), "I have this", "Not needed".
  - Done and dismissed states persist per trip and per item; one nudge per item per week at
    most.
  - AI never gives insurance, visa or legal advice; insurance copy uses insurer-approved text
    only.
- Tier: all. Credits: none.

#### F-CHK-2 Custom items

- Story: As a traveler, I want to add my own to-dos, so that the list covers my life.
- Acceptance: custom items have text, optional due date and assignee; shared with members; never
  monetized.
- Tier: all.

### 4.11 Group tools (F-GRP)

Later: Phase 2, see [../phase-2-growth/README.md](../phase-2-growth/README.md). Covers polls, manual cost splitting and settle up, and the room-block request. Stripe collection of group payments: Later: Phase 3, see [../phase-3-scale/README.md](../phase-3-scale/README.md).

### 4.12 Concierge request (F-CON)

Later: Phase 2, see [../phase-2-growth/README.md](../phase-2-growth/README.md).

### 4.13 Affiliate booking surfaces (F-AFF)

All outbound partner links go through `/go/{click_id}` with a random per-click sub-id
(`link_clicks`; conversions in `affiliate_conversions`, program config in `affiliate_programs`
and `affiliate_link_templates`). No ad or attribution SDKs, no device ids, so no App Tracking
Transparency prompt.

Global rules (each is a testable requirement):

1. A label "We earn a commission if you book here." sits beside every partner button; UK and EU
   storefronts also show an "Ad" tag.
2. Lists state how they are sorted; nothing is ranked by commission.
3. Pasted listing links stay exactly as pasted.
4. At most one affiliate card per screen view, except on lists the user asked for (lodging
   shortlist, checklist).
5. No pop-ups, no interstitials, nothing during presentation playback, nothing in AI output, no
   affiliate card beside an upsell.
6. A non-affiliate route appears where one exists ("Search on the airline's site", "Open your
   saved link").
7. A per-partner kill switch can hide a partner immediately.
8. Paid tiers see the same links in the same places, never hidden.
9. Offline mode shows no partner content.
10. Settings has "How we earn" (the public page, F-WEB-4) listing every partner and the ranking
    rule, with a "Hide booking links" switch that collapses buttons to a plain "Open on partner
    site" link.

#### F-AFF-1 Destination card

- Story: As a planner with dates, I want a helpful "Places to stay" shortcut, so that I can
  start browsing.
- Acceptance: one quiet card on the overview, only when dates exist, collapsed after first view,
  linking to a partner search with dates and party size; no partner name in AI text.
- Tier: all.

#### F-AFF-2 Chosen flight booking

- Story: As a user who chose a flight, I want to go book it, so that I finish the job.
- Acceptance: card shows "Book on <provider>" (affiliate), "Search on the airline's site",
  fare age and "price can change", and a soft "Next: add stays and a checklist"; after a click,
  the trip shows "Did you book it?" with a yes toggle.
- Tier: all.

#### F-AFF-3 Stays

- Story: As a user, I want my links untouched and partner links clearly separate.
- Acceptance:
  - "Open" always opens the user's saved URL with no wrapper or tracking parameters.
  - A separate "Book via partner" button appears only when a program is approved for that host
    through a Phase 1 network (Travelpayouts, Stay22 or Viator), built from the URL text and trip
    dates, never by fetching the page; never for Airbnb.
  - With no saved link, "Find on Booking, Vrbo or Agoda" offers labeled search links prefilled
    with destination, dates and guests.
  - A "cheaper on <partner>" line appears only with real, dated price data.
- Tier: all.

#### F-AFF-4 Tickets, transfers, cars

- Story: As a traveler, I want to buy tickets or a transfer for things already in my plan.
- Acceptance: "Tickets" on bookable attractions; airport transfer card on arrival day; car card
  on drive days; parks and viewpoints get nothing; day order is never changed.
- Tier: all.

#### F-AFF-5 Other surfaces

- Checklist "Get it" buttons (F-CHK-1), optional "Book the plan" slide (F-PRS-1), and a "Today"
  card during the trip (F-TRV-1) follow the same global rules. Trip created, flight charts,
  lodging import, the switching import, Verify this plan, evidence rechecks, the booked-fare alert,
  the calendar feed, comparison and sample pages, the trust pages, the status page, agent pages,
  trips home and paywalls carry no affiliate UI.

#### F-AFF-6 Launch partners

- Travelpayouts (flights, stays, cars, transfers, tours, eSIM, insurance), Viator partner API and
  Stay22. Airbnb is plain links only. Direct programs (Expedia Group for Vrbo, Booking.com,
  Skyscanner, Airalo, GetYourGuide): Later: Phase 2, see [../phase-2-growth/README.md](../phase-2-growth/README.md).

### 4.14 Notifications and email (F-NOT)

#### F-NOT-1 Channels and preferences

- Story: As a user, I want to choose what I am told and where, so that I am never spammed.
- Acceptance:
  - Channels: push (APNs), in-app inbox, email (Resend). Settings has a matrix of event types by
    channel.
  - Event types: price alert (including the booked-fare drop), invite accepted, member joined,
    agent run finished, plan check finished, calendar changes found, checklist reminder, referral
    reward, export ready, deletion steps.
  - Change-digest push for shared trips is at most one per hour per trip.
  - No promotional push (Apple guideline 4.10). Marketing email is separate and opt-in.
  - Every email has a one click unsubscribe for non-transactional types.
  - Push permission is requested after the first invite or alert, with a reason screen.
- Tier: all.

#### F-NOT-2 Reminders

- Story: As a traveler, I want one reminder before departure, so that I do not forget the
  checklist.
- Acceptance: one opt-in push 7 days before departure summarizing open checklist items; a second
  message is never sent for the same trip.
- Tier: all.

#### F-NOT-3 Transactional email

- Acceptance: invite, sign-in code, export ready, deletion confirmation, referral reward; sender
  name shows the inviter for invites; every email renders in plain text too.

### 4.15 Settings, export and delete account (F-SET)

#### F-SET-1 Settings

- Acceptance: sections for Account (name, email, sign-in methods, devices with "sign out
  everywhere"), Preferences (home airports, currency, units, locale, time zone, theme),
  Notifications (F-NOT-1), AI (consent, per-trip toggles, credit history), Subscription
  (F-SUB, with "Cancel subscription" and "How billing works", F-SUB-7), Invite friends (F-REF),
  Import a trip (F-IMP), How we earn (F-WEB-4), Privacy, Help (including "Install on Android",
  F-WEB-7, and "Service status", F-WEB-6) and Legal. Changes save immediately.

#### F-SET-2 Export

- Story: As a user, I want all my data, so that I am never locked in.
- Acceptance:
  - "Export my data" (re-auth required) creates a `data_exports` job producing a zip: JSON of
    everything plus a readable PDF and CSV per trip, ICS of itineraries, emailed as a link that
    expires in 7 days.
  - Target under 24 hours; limit 1 export per day.
  - Per-trip export (JSON, ICS, PDF) is available on every tier from the trip menu and works on
    archived trips.
- Tier: all.

#### F-SET-3 Delete account

- Story: As a user, I want to delete my account in the app, so that my data goes away.
- Acceptance:
  - Path: Settings > Account > Delete account, with re-authentication and a plain list of
    effects; no email or web-only route.
  - Immediately: sessions and tokens revoked, Apple token revoked, push tokens removed, pending
    invites cancelled, `deletion_requests` row created, account `pending_deletion`.
  - Owned trips with other members: prompt to transfer or delete; if no choice, deleted after 30
    days unless a member accepts transfer. Owned trips without members are deleted.
  - Trips owned by others: user removed; contributions remain as "Deleted user".
  - After 30 days: hard delete of the user, identities, devices, personal travelers and AI
    history; purchase records kept for legal retention only; backups age out within 35 days.
  - The flow says deleting does not cancel an App Store subscription and deep links to
    subscription settings without blocking.
  - The account can be restored by signing in within the 30 days.
  - Deletion is an idempotent job with a visible checklist for partial failures.
- Tier: all.

### 4.16 Subscriptions, passes, credits and paywalls (F-SUB)

#### F-SUB-1 Plans and purchase

- Story: As a user, I want clear plans and a simple purchase, so that I pay only for what I use.
- Acceptance:
  - Plans screen shows `free`, `plus`, `trip_pass` and credit packs.
  - `plus` $5.99 a month or $39.99 a year (annual pre-selected, 7-day trial on annual only),
    `trip_pass` $9.99, `credits_50` $2.99, `credits_150` $6.99, `credits_400` $14.99.
  - Plus monthly and annual share the `hermi_membership` group; switching between them follows
    StoreKit rules.
  - The trial screen states the price and renewal date; a reminder (local notification and email)
    is sent 2 days before conversion and carries the one-tap cancel link (F-SUB-7).
  - On the web app no plan can be bought: the paywall shows what the upgrade unlocks, the free
    path and "Upgrade in the iOS app" with a link to the App Store. It shows no price list, no
    purchase button and no "cheaper on the web" text.
  - Restore purchases is always present.
  - Entitlements are stored server side from RevenueCat and App Store Server Notifications v2;
    the client reads `GET /me/entitlements` and never decides.
- Tier: all. Credits: none.
- Later: Family, Group Trip Pass and Pro, see the full ladder in [../README.md](../README.md) and Later: Phase 2, see [../phase-2-growth/README.md](../phase-2-growth/README.md).

#### F-SUB-2 Trip Pass

- Story: As a trip-focused user, I want to upgrade one trip, so that I do not subscribe.
- Acceptance:
  - A Trip Pass is bound to one trip on the server (`trip_passes`) and lasts 90 days from binding.
    Purchase comes first, binding second: the purchase is a `store_transactions` row
    (`kind = 'pass'`) and the pass has no trip until the owner picks one.
  - Binding flow: before the purchase the app asks "Which trip is this for?" (pre-selected when
    the purchase started from a trip) and sends the trip with `POST /v1/purchases/sync`. A pass
    bought with no trip waits as "unapplied" in Settings, Purchases (listed by `GET /v1/me/passes`,
    kept 12 months) until the owner binds it with `POST /v1/me/passes/{pass_id}/bind`. Only the
    trip's owner can bind, and the purchaser must be that owner. A trip holds one active pass; a
    second pass for the same trip is refused.
  - One move: an active pass can move to another trip the same owner owns, once
    (`POST /v1/me/passes/{pass_id}/move`). The move keeps the original expiry, carries the
    unspent pass credits and the live-check counter, and pauses live routes on the old trip. A
    second move is refused.
  - Trip Pass: 2 live routes, at most 60 live checks, 40 credits, up to 6 collaborators. The
    passed trip does not count toward the owner's active-trip limit.
  - A trip's capabilities are the best of its owner's tier and any pass on it.
  - Pass credits are a pool tied to the trip (a `trip_pass` grant with the trip id), expire with
    the pass after 90 days, are spendable by any member acting on that trip, and are spent after
    the actor's monthly allowance and before purchased credits.
  - The trip settings screen shows the pass status and expiry, a notice 7 days before expiry, and
    a renewal offer (a new pass starts a new 90 days).
  - A Trip Pass is also granted free by a first qualifying import (F-IMP-3). It behaves exactly like a
    purchased pass except that it has no store transaction (`trip_passes.source = 'import_reward'`).
  - Default paywall order: Trip Pass first when a trip has dates within 120 days; annual `plus`
    first when the user has 2 or more active trips.
- Tier: purchasable by any user. Credits: pass credits as above.
- Edge cases: a pass bought while on `plus` takes the better of each limit and adds its 40 credits;
  an expired pass returns the trip to the owner's tier (F-SUB-6); a refunded pass stops granting
  capabilities and its unspent credits are removed.

#### F-SUB-3 Family

Later: Phase 2, see [../phase-2-growth/README.md](../phase-2-growth/README.md).

#### F-SUB-4 Credits

- Story: As a user, I want to see and top up credits, so that I am never surprised.
- Acceptance:
  - Monthly grants: `free` 12, `plus` 60, `trip_pass` 40 once; monthly grants do not roll over.
  - Purchased packs last 12 months and are spent last; expiry dates are shown.
  - Promo credits (the taster, referral credits from F-REF-1) carry their own expiry and are
    shown separately from purchased credits. Only purchased credits raise the provider-spend
    ceiling; promo, taster, referral and pass credits never do.
  - Spend order: monthly allowance, then promo (the taster, then referral credits, oldest expiry
    first), then pass credits for that trip, then adjustments, then purchased credits (oldest
    expiry first).
  - Balance, history and expiry are visible (`credit_ledger`, `credit_grants`).
  - Refunds through Apple remove unspent credits from that purchase; if some were already spent
    the shortfall is recorded as a debt (`credit_debts`) that blocks paid AI until later credits
    cover it, and repeated refunds block pack purchases for 180 days.
  - On lapse, purchased credits stay usable on `free`; allowance credits vanish.
- Tier: all.

#### F-SUB-5 Paywall moments

The table lists every moment. Rules: one paywall per session at most, "Not now" always visible,
dismiss mutes the same prompt for 7 days, the prompt says what the user gets on this trip, no
paywall before first value, none beside an affiliate card.

| Moment | Trigger | Best offer |
|---|---|---|
| Third active trip | `free` limit of 2 | Archive one, or annual `plus` |
| Second route | `free` 1 route per trip | `trip_pass` |
| Live tracking or alert beyond limit | No live access | `trip_pass` or 1 credit |
| Invite a second collaborator | `free` owner with 1 collaborator already on the trip | `trip_pass` ("They join free") |
| Draft, research or plan check out of credits | Fewer credits than the action costs | Credit pack or `plus` |
| Presentation footer and PDF watermark | `free` share | `trip_pass` (soft, at export) |
| Saving the 9th stay | `free` limit | Keep in "Later", `trip_pass` |
| 14 days before departure on a `free` trip | Lifecycle | `trip_pass` (email or push, opt-in) |

- Acceptance: the "After booking through an affiliate link" moment shows no paywall; no
  countdown timers, no invented scarcity, no "unlimited" claims in copy. The import flow, the
  calendar feed, the booked-fare alert, the list of places in Verify this plan, the taster result and
  the public web pages never show a paywall.
- Paywall moments for scheduled routines, group tools and group passes: Later: Phase 2, see [../phase-2-growth/README.md](../phase-2-growth/README.md).

#### F-SUB-6 Downgrade and lapse

- Acceptance:
  - Data is never deleted or hidden on downgrade; archived and over-limit trips stay readable
    and exportable.
  - A lapsed owner's trip becomes limited: collaborators beyond the `free` cap of 1 become viewers
    (the earliest to join stays an editor), live tracking pauses, extras are kept and come back if
    the owner renews.
  - A banner tells the owner what changed and how to restore.
  - Cancelling is never blocked, delayed or put behind an offer: "Cancel subscription" is always
    one tap away (F-SUB-7).

#### F-SUB-7 Plain billing and one-tap cancel

- Story: As a subscriber, I want to understand what I pay and cancel without hunting, so that I
  never feel trapped.
- Acceptance:
  - On the Account screen the plan card has a first-level row "Cancel subscription" next to
    "Change plan". One tap opens the App Store's own subscription sheet for that plan, where Apple
    asks for the final confirm. No question, survey or retention offer comes before it. When the
    plan already ends, the row reads "Your plan ends on <date>".
  - On the web app the row reads "Cancel in the iOS app" and opens the App Store's subscription
    page.
  - The trial reminder, receipt and billing problem emails carry the same cancel link.
  - "How we bill" is a plain page (F-WEB-5), linked from Settings, every paywall and the App Store
    listing, that says what each plan costs and when it renews, what the trial does on day 8, that
    a Trip Pass never renews, how credits expire, that refunds go through Apple, what stays when
    you cancel, and that purchases are in the iOS app only.
  - Cancelling keeps the data: trips stay readable and exportable, purchased credits stay (F-SUB-6).
  - No countdowns, no pre-checked upsells, no renamed or hidden cancel.
- Tier: all subscribers. Credits: none.

### 4.17 Travel and after-trip (F-TRV, F-AFT)

#### F-TRV-1 Today view

- Story: As a traveler, I want today's plan front and center, so that I can just follow it.
- Acceptance: during trip dates the trip opens on "Today" with local time, next item, map, stay
  address and confirmation numbers; an optional "Today" partner card appears only if an
  unbooked eligible activity exists and never with urgency copy; no partner content offline.
- Tier: all.

#### F-TRV-2 Offline reading (every tier)

- Story: As a traveler, I want my trip on my phone with no signal, so that I can read the plan
  anywhere.
- Acceptance:
  - Offline reading is on every tier, for trips the user owns and trips they joined, in the iOS
    app and, for trips opened on that browser, the web app.
  - Itinerary, flights and fares (with their age), stay details, checklist, notes, evidence labels,
    travelers and map tiles for the trip area are cached for reading; the offline state and the
    data age are shown.
  - Trips opened in the last 30 days (up to 10) stay cached automatically; "Download for offline"
    on a trip fetches its map tiles on demand.
  - Edits queue and sync when the connection returns (section 6.2). The sync indicator (F-COL-5)
    reads "Offline, N edits waiting" while they wait.
  - No partner content is shown offline.
- Tier: all. Credits: none.

#### F-AFT-1 Delay prompt

Later: Phase 2, see [../phase-2-growth/README.md](../phase-2-growth/README.md).

#### F-AFT-2 Wrap-up

- Acceptance: "How was the trip?" card with a 1 to 5 rating and a note, no affiliate button; 14
  days after the end the trip is offered for archive.

### 4.18 Switching import (F-IMP)

People arrive with trips already in TripIt, a calendar app or their email. Import brings them in
without retyping and without giving Hermi a password. Hermi never asks for a TripIt, Google or
Wanderlog login, uses no sign-in tokens from those services, and has no access to anyone's inbox.
The import screen has an entry for each app (F-IMP-4), a Google Maps list import (F-IMP-5) and an
opt-in way to keep a calendar feed up to date (F-IMP-6).

#### F-IMP-1 Import from a calendar file or feed

- Story: As a TripIt or Google Calendar user, I want to import a trip from a calendar file or
  link, so that my bookings are in Hermi without retyping.
- Acceptance:
  - Import accepts an iCalendar (.ics) file chosen from the device (a TripIt single-trip export, a
    Tripsy or Google Calendar export, or any iCalendar file), or a calendar feed link pasted into a
    field (a TripIt or Tripsy iCal feed or a Google Calendar secret iCal address, `webcal://` or
    `https://`). A feed is read once, at import time, and the link is not stored, unless the person
    turns on "Keep checking this calendar" after the first import (F-IMP-6).
  - Limits: file or feed up to 2 MB and 500 events. A link is fetched over https only, with a 15
    second timeout, at most 3 redirects, and private and internal addresses refused; Airbnb, Vrbo
    and Booking.com hosts are refused and ask the person to upload a file. The server never follows
    links found inside events.
  - A TripIt trip export is treated as one trip. A larger calendar shows a date range and type
    filters (Flights, Stays, Activities, Other) with "Select all in range".
  - Reading is deterministic, with no AI and no credits: events that look like flights (flight
    numbers or airport codes) become flights (itinerary items in the `travel` category, status
    `booked`, `source = 'import'`); hotel or lodging events and multi-day events with an address
    become booked stays (lodging options, status `booked`); reservations, tours and meals become
    activity items; anything unsure becomes a plain item in the `other` category. The person can
    change the type of any row.
  - Times keep their time zone. Floating times are read in the destination's time zone; all-day
    events become untimed items on that day.
  - Preview before saving: every event found is listed by day with type, title, time and place,
    each with a tick, an edit and "Change type", and a count ("18 found, 16 will be imported").
    Nothing is saved until "Import".
  - Destination: a new trip (name, destinations and dates prefilled from the items) or "Import
    into this trip". Importing never changes trip dates while a flight is chosen (F-FLT-5); items
    outside those dates are kept as ideas.
  - Re-importing the same file skips items already imported (each item keeps the event's UID) and
    says how many were skipped.
  - Confirmation numbers found in an event stay in the item's notes, visible to trip members.
  - Imported booked flights offer the booked-fare watch (F-FLT-8).
- Tier: all. Credits: none.
- Edge cases: an empty or unreadable file says so and offers "Paste a booking email"; an event
  with no date is listed as unparsed and left unticked; two events with the same flight number and
  date merge into one row.

#### F-IMP-2 Import from pasted confirmations

- Story: As someone with bookings in email, I want to paste confirmations and get entries, so that
  I do not retype them.
- Acceptance:
  - The import screen takes up to 10 pasted texts in one session, each up to 12,000 characters.
    Each text goes through F-AI-10 (personal data replaced with placeholders before the model
    call, Haiku 4.5, no link ever fetched); one text can yield several items (for example a
    round-trip flight and a hotel).
  - Each text costs 1 credit (`explain` price class), shown before the tap; a text with no booking
    in it is refunded and says so. Credits come from the normal allowance, or from the trip's
    pass credits once F-IMP-3 has granted the pass.
  - Results join the same preview list as F-IMP-1, so a file and pasted confirmations can be
    imported together; nothing is saved until "Import".
  - Kill switch `ai.import`; needs AI consent and `trips.ai_enabled`.
- Tier: all, from the user's credits. Credits: `explain` 1 per text. Model: Claude Haiku 4.5.

#### F-IMP-3 First import earns a Trip Pass

- Story: As a new user who brings a trip over, I want that trip to get full features, so that I
  can judge Hermi with my own data.
- Acceptance:
  - The first time an account completes an import (F-IMP-1 or F-IMP-2) that adds at least 3
    items including a flight or a stay, the trip that received them gets a Trip Pass for 90 days at
    no charge: a `trip_passes` row with `source = 'import_reward'`, no `store_transactions` row,
    bound to that trip, with the same capabilities and 40 pass credits as a purchased Trip Pass
    (F-SUB-2).
  - All of these must hold: at least 3 items added, at least one of them a flight or a stay; a
    verified email; the trip has no active pass; the account has no active Plus. A Google Maps or
    pasted-places import (F-IMP-5) and a calendar change confirmation (F-IMP-6) never qualify.
  - Once per account, ever. The import screens promise the pass only while it is still available
    and the person has no Plus ("Your first import includes a Trip Pass for Lisbon").
  - Requires a signed-in account past the age gate, checked server side with device attestation. An
    import that does not qualify, or a trip that already has an active pass, does not consume the
    reward, and it stays available for the next import.
  - The result screen says plainly what was granted: "Your first import includes a Trip Pass for
    Lisbon: live fare checks, up to 6 collaborators and 40 credits until 4 Dec."
  - The pass shows in Settings, Purchases as "Included with your first import", can move once
    (F-SUB-2), expires after 90 days like any pass, and at expiry the trip returns to the owner's
    tier (F-SUB-6) with the 7 day notice.
  - No card, no trial, nothing renews.
- Tier: all. Credits: 40 pass credits.
- Edge cases: deleting the imported trip does not restore the reward; a pass granted to a trip the
  owner later transfers follows F-COL-7.

#### F-IMP-4 Import entries named for TripIt, Tripsy and Wanderlog

- Story: As someone using another planner, I want an entry with my app's name that tells me how to
  get my trips out, so that I know it will work before I try.
- Acceptance:
  - The import screen lists TripIt, Tripsy, Wanderlog, Google Calendar and Google Maps as plain
    text entries (no logos). Each entry opens the matching method and shows two or three steps for
    getting the data out of that app: TripIt and Tripsy: a calendar file or calendar feed link;
    Wanderlog: pasted places from a list or pasted booking confirmations; Google Calendar: an
    exported file or a secret iCal address; Google Maps: F-IMP-5. The steps are checked against the
    app's own help pages at build time and before launch; where an app offers no export we say so
    instead of guessing.
  - Each entry says what moves ("dates, flights, stays and places", never "everything") and that
    nothing is saved until the person taps "Import".
  - The entry used is recorded (`origin`) for the "switch imports per week" metric and nothing else.
  - No entry asks for another app's password, sign-in or email access.
- Tier: all. Credits: none for the entries themselves (pasted confirmations cost 1 credit each,
  F-IMP-2).

#### F-IMP-5 Google Maps list and pasted places

- Story: As someone who saved places in a Google Maps list or another planner, I want to bring
  those places into a trip, so that I do not search for each one again.
- Acceptance:
  - Import accepts an exported Google Maps saved-list file (a Google Takeout "Saved" CSV, GeoJSON
    or KML file, up to 5 MB and 200 places) or pasted place names, one per line or copied from a
    list, up to 20,000 characters.
  - Hermi never opens, resolves or scrapes a Google Maps list link. If the person pastes a list
    link, the screen explains that the list has to be exported first (two steps, with the Takeout
    path), offers "Keep this link as a note on the trip", and does not contact the address.
  - Each place is matched by name through place search (Geoapify); the preview shows the match
    (name, address, a small map) with "Not the right place" to pick another or drop it. Unmatched
    rows stay in the list as plain text for the person to fix or untick.
  - Places become ideas with no day (F-ITN-3). The list's own notes and any Google Maps URLs in the
    file are kept as plain text in the item's notes and are never followed.
  - Reading uses no AI and no credits. Nothing is saved until "Import".
  - A places-only import never earns the first-import Trip Pass (F-IMP-3).
- Tier: all. Credits: none.
- Edge cases: a file with no recognizable places says so and offers the paste field; more than
  200 places imports the first 200 and says so; a duplicate of an existing saved place is marked
  "Already on your trip" and left unticked.

#### F-IMP-6 Keep checking this calendar

- Story: As someone whose trip lives in a TripIt or Tripsy calendar feed, I want Hermi to notice
  changes, so that my plan stays current without re-importing.
- Acceptance:
  - After a feed import is applied, the result screen offers a switch "Keep checking this
    calendar", off by default and never turned on for the person. It says how often ("every 6
    hours") and that changes arrive as a preview to confirm.
  - When on, Hermi reads the feed every 6 hours. If events were added, changed or removed, the
    trip shows "Your calendar changed: 3 updates" with a notification, and a preview listing each
    change (new, changed with before and after, removed). The person ticks what to apply and taps
    "Apply"; nothing is applied automatically, ever. Removed events are listed and never deleted
    for the person.
  - The feed link is stored encrypted only while the switch is on, is never shown in full, and is
    deleted when the switch goes off, the import is discarded, the trip is deleted or the account
    is deleted.
  - Polling turns off by itself after 3 failed reads in a row (the person is told), 7 days after
    the trip ends, or when the person turns it off. At most 3 calendars can be kept up to date per
    account.
  - Polling is one way: Hermi never writes to the person's calendar. It is free, uses no AI and
    no credits, works on every tier, and does not count as an import for the reward (F-IMP-3).
  - Kill switches `import.polling` and `import.all`; flag `calendar_feed_polling`.
- Tier: all. Credits: none.

### 4.19 Live calendar subscription feed (F-CAL)

#### F-CAL-1 Calendar feed per trip

- Story: As a traveler, I want the trip in my own calendar app and kept up to date, so that I see
  the plan beside the rest of my life.
- Acceptance:
  - The owner turns on "Calendar feed" in trip settings (off by default). It creates one feed per
    trip at `https://hermi.world/cal/<token>.ics` with a random 128 bit token, stored encrypted so
    the owner can copy it again. "Add to Apple Calendar" opens the `webcal://` form, "Copy link"
    serves Google Calendar, Outlook and others with a one-line how-to for each, and "Make a new
    link" revokes the old link at once.
  - The feed is read-only iCalendar. Each itinerary item with a time is one event in the
    destination's time zone; untimed items are all-day events on their day; the chosen flight is
    an event with airports and times; a booked stay is an all-day span from check-in to
    check-out. Ideas without a day are not included.
  - Event text is the item title, place name and the item's public note. Stay addresses are
    included only if the owner turns on "Include addresses" (off by default, same redaction rule as
    share links). Prices, private notes, confirmation numbers, traveler names and partner links
    are never included.
  - Live: events keep stable UIDs with `SEQUENCE` and `LAST-MODIFIED`, so edits update and
    deleted items disappear; the feed declares a one hour refresh hint (`REFRESH-INTERVAL`,
    `X-PUBLISHED-TTL`), supports ETag and If-None-Match, and is cached for 15 minutes. How fast a
    change shows depends on the calendar app, and the sheet says so ("often within an hour, and
    Google Calendar can take up to a day").
  - Anyone with the link can read the schedule, and the sheet says so. The feed answers 404 for an
    unknown token and 410 after it is revoked or the trip is deleted; requests are limited to 60
    an hour per token; it is unlisted and not indexable.
  - The feed is separate from the one-time ICS export in F-SET-2.
- Tier: all, including `free`. Credits: none.
- Edge cases: a trip with no dated items returns an empty calendar; the owner losing a paid plan
  does not turn the feed off; archived trips keep serving.

### 4.20 Public web pages (F-WEB)

Public pages need no account and no app. They use the Hermi design and the same components as
the app, follow the affiliate rules, and are screens 6.34 to 6.36 and 6.40 to 6.42 in [05-ui-ux-spec.md](05-ui-ux-spec.md).
Only the page behavior is specified here; hosting and SEO plumbing are in
[02-architecture.md](02-architecture.md) and the launch tasks in [09-build-roadmap.md](09-build-roadmap.md).

#### F-WEB-1 Shared-trip pages

- Story: As someone with a link, I want to read the trip in a clean page, so that I do not need
  the app.
- Acceptance:
  - The page at `/s/<shareId>` (created by F-COL-6) shows trip title, destinations, dates and the
    day by day plan with a map, with the redaction of F-COL-6 applied, evidence labels (F-NTE-2) on
    AI-found items, the "Made with Hermi" footer on `free` trips, and "Get the app to edit".
  - Search listing is opt-in: the owner's switch "Let search engines list this page" is off by
    default. Off, the page is `noindex`. On, the page has a title, a description, a canonical URL
    and a preview image built from the trip's route pattern and destination. Listing needs an expiry,
    and an expired or revoked page returns 410 and drops out.
  - A "Report this page" link sends the page to the admin content reports queue.
  - No account wall, no paywall, no comments.
- Tier: all tiers create; anyone views.

#### F-WEB-2 Public sample trips

- Story: As a visitor, I want to see a finished plan, so that I understand what Hermi makes.
- Acceptance:
  - A gallery at `/samples` lists 4 to 6 sample trips written by Hermi (for example a long
    weekend in Lisbon, a week in Japan, a family road trip); each is at `/samples/<slug>` and uses
    the shared-trip page with overview, itinerary, map, stay shortlist with hearts, checklist and a
    fare chart labeled "Sample data, dated <date>".
  - Samples are owned by a Hermi system account, cannot be edited by visitors, contain no real
    people, and show every price and fact with a date and, for AI-found facts, the evidence label.
    A sample never presents a cached or stale price as current.
  - "Copy this trip" duplicates the structure into the visitor's account or guest trip using the
    F-TRP-6 rules (no fares, votes or notes); it works in guest mode.
  - Sample pages are indexable, with title, description, canonical URL and preview image. Partner
    links, if any, follow F-AFF.
  - The gallery is a fixed, editorial list; there is no browsing of user trips (section 7).
- Tier: public.

#### F-WEB-3 Comparison pages

- Story: As someone comparing trip planners, I want an honest side by side, so that I can choose.
- Acceptance:
  - Launch pages: `/vs/tripit`, `/vs/wanderlog` and `/vs/tripsy`. Each has a short summary, who
    each app suits best (including when the other app is the better choice), a table of features
    and prices, "Switching from <name>" with a link to the import (F-IMP-1), and "Plan a trip".
  - Every statement about another product has a source link and a "Checked <date>" label, like an
    evidence label, and is re-checked at least every 90 days; the page shows "Last checked
    <date>". A claim that cannot be sourced is not made. Prices show currency and date.
  - Hermi's own limits are stated (for example, no Android app until Phase 2).
  - No affiliate links or partner cards, no competitor logos (names as plain text), no
    disparaging words and no "best" claims.
  - Content is reviewed text in the repository, written by people from
    [../context/competitive-analysis/README.md](../context/competitive-analysis/README.md); nothing is scraped
    or fetched from competitor sites by the server.
  - Pages are indexable, with a plain title ("Hermi and TripIt"), a description and a canonical
    URL. The comparison basis statement shows on UK and EU storefronts (section 6.4).
- Tier: public.

#### F-WEB-4 How we earn

- Story: As a visitor or user, I want to see exactly how Hermi makes money, so that I can trust
  its suggestions.
- Acceptance:
  - A public page at `/how-we-earn`, needing no account, linked from Settings, every paywall,
    empty states and every `/vs` page, states in plain words: Hermi earns from subscriptions,
    Trip Passes, credits and commissions when someone books through a partner link; nothing is
    ranked by commission; every partner link is labeled; there are no ads; user data is never
    sold; Airbnb, Vrbo and Booking.com pages are never fetched.
  - It lists every active partner by category with its disclosure line, and shows live counts
    (partners and categories) built from the same partner list the app uses, so a partner cannot
    be added without appearing on it.
  - It shows how a partner button and its label look, and explains the "Hide booking links"
    setting.
  - It has no affiliate links, no cards and no paywall.
- Tier: public.

#### F-WEB-5 How billing works

- Story: As a subscriber or a person about to subscribe, I want a plain explanation of billing, so
  that nothing surprises me.
- Acceptance:
  - A public page at `/billing` (also in Settings and on every paywall) says, in short sentences:
    each plan's price and renewal; the 7-day trial on the annual plan, the reminder 2 days before
    it converts and what happens on day 8; that Trip Pass is one time and never renews; how credits
    expire; how to cancel (the one-tap link, F-SUB-7); what stays after cancelling; that refunds go
    through Apple and what Hermi can do; that no card details are stored; that purchases are in
    the iOS app only for now; and what stays free.
  - Prices on the page come from the same configuration as the paywall, so they cannot disagree.
  - It is reviewed with every price change and included in the App Review notes.
- Tier: public.

#### F-WEB-6 Public status page and service status

- Story: As a user who sees something wrong, I want to check whether Hermi has a problem, so that
  I know it is not me.
- Acceptance:
  - A public status page at `status.hermi.world` (also linked as `/status`) is hosted outside
    Hermi's own infrastructure, so it works during an outage. It shows five components (web app,
    API, AI features, fare data, push), each operational, degraded or down, with 90 days of uptime
    and posted incidents in plain words with times.
  - The app shows a quiet banner when a component is degraded ("Fares are delayed right now. Saved
    trips still work") with a link to the page. Settings has "Service status".
  - The banner never appears for a single user's failed request; it reflects the same state as the
    page.
  - The trip header shows how fresh its data is ("Synced 12 s ago", F-COL-5).
- Tier: public.

#### F-WEB-7 Android install guide

- Story: As an Android user, I want to use Hermi like an app, so that I can plan with friends who
  have iPhones.
- Acceptance:
  - The web app is installable: a web app manifest (name, icons, sky theme color `#2AA5FF`, standalone display) and a
    service worker that keeps opened trips readable offline, so Chrome on Android offers "Install
    app" and "Add to Home screen".
  - A page at `/install/android` explains in 3 short steps with screenshots how to install from
    Chrome (and notes Samsung Internet), what works (full planning, editing, sharing, reading
    offline) and what does not yet (push notifications for price drops arrive by email; native
    Android app is planned), and links to Settings, Help, "Install on Android".
  - On Android Chrome a dismissible card "Add Hermi to your home screen" appears after the person
    has created a trip (never on the first screen, never a modal), once every 30 days at most, and
    uses the browser's own install prompt.
  - Hermi is tested on Android Chrome (phone and tablet sizes) before each release: sign-in,
    creating and editing a trip, sharing, offline reading and the install flow.
  - Copy never claims a Play Store app or push that does not exist.
- Tier: all. Credits: none.

### 4.21 Referral credits (F-REF)

#### F-REF-1 Invite a friend, both get credits

- Story: As a user, I want to tell a friend about Hermi and be thanked with credits, so that
  sharing is worth it.
- Acceptance:
  - Every signed-in account has a referral link `https://hermi.world/r/<code>` and a code, in
    Account, "Invite friends", with the native share sheet. A friend can also type the code
    ("Have a friend's code?") at sign-in or in onboarding. There is no attribution SDK, so the code
    arrives through the link on the web, the universal link when the app is installed, or typing.
  - The reward is 20 credits to the referrer and 20 credits to the friend when the friend signs in
    with a verified identity, passes the age gate, and, within 30 days of applying the code,
    creates their first trip with dates.
  - Credits are promo grants (`credit_grants`, kind `promo`), expire after 12 months, and are
    spent as in F-SUB-4. They are never cash and cannot be sold or transferred. They never raise
    the provider-spend ceiling.
  - A referrer is paid for at most 5 rewards in a rolling 30 days and 10 in a calendar year; past a
    cap friends still get theirs and the screen says so.
  - Refused: your own code, a second code on one account, an account sharing the referrer's
    device attestation, and disposable email domains.
  - Joining a trip through a trip invite (F-COL-4) earns no referral reward for anyone.
  - Screen shows the plain rule ("You and a friend each get 20 credits after their first trip with
    dates. Credits last 12 months."), friends joined and credits earned (no friend names), with no
    countdowns and no nags; there is at most one push per reward earned.
- Tier: all. Credits: earned as above.
- Edge cases: a friend who already has an account cannot apply a code; if the friend deletes the
  account before the reward is paid, no reward is paid.

### 4.22 Advisor workspace (F-ADV) and printed trip book (F-PRT)

Later: Phase 3, see [../phase-3-scale/README.md](../phase-3-scale/README.md).

## 5. Tier and entitlement matrix

Legend: yes, no, number (limit), or note. `free` $0; `plus` $5.99 or $39.99 a year; `trip_pass`
$9.99 for one trip for 90 days (also granted once, free, by a first import, F-IMP-3). For passes,
every value applies to the passed trip only. Phase 1 sells these tiers and the credit packs only;
the full ladder, including Family, Pro and Group Trip Pass, is in [../README.md](../README.md).

| Capability | free | plus | trip_pass |
|---|---|---|---|
| Active trips | 2 | unlimited (fair use 25) | the trip |
| Join others' trips | yes | yes | yes |
| Archived trips: read and export | yes | yes | yes |
| Travelers per trip | 2 | 8 | 8 |
| Destinations per trip | 12 | 12 | 12 |
| Invite collaborators | 1 per trip | 6 per trip | 6 |
| Read-only share link and shared-trip page | yes, with footer | yes | yes |
| Offline reading | yes | yes | yes |
| Live calendar feed | yes | yes | yes |
| Switching import (calendar file or feed, TripIt, Tripsy and Wanderlog entries) | yes | yes | yes |
| Google Maps list and pasted places import | yes | yes | yes |
| Keep checking this calendar (feed polling every 6 hours, opt-in) | yes | yes | yes |
| Import from pasted confirmations | 1 credit each | 1 credit each | 1 credit each |
| Free Trip Pass after first qualifying import (3 or more items including a flight or a stay, verified email, no active Plus) | once per account | not applicable (has Plus) | not applicable |
| Routes per trip (cached fares; live where allowed) | 1 | 5 | 3 |
| Airports per side of a route | 2 | 4 | 4 |
| Live-tracked routes (daily, within 120 days) | 0 | 3 | 2 (max 60 checks) |
| Refresh now (live peek) | 1 credit | 1 credit | 1 credit |
| Price alerts | 1 cached | 3 live and cached | 2 |
| Booked-fare drop alert | yes | yes | yes |
| Saved stays per trip | 8 | unlimited (fair use 100) | 30 |
| Lodging compare | 2 | 4 | 4 |
| Rental search | 1 credit | 1 credit | 1 credit |
| Place searches per day (soft) | 30 | 100 | 100 |
| Itinerary, ideas, map | yes | yes | yes |
| Presentation mode | yes, footer and watermark | yes | yes |
| Before-you-go checklist | yes | yes | yes |
| After-trip wrap-up | yes | yes | yes |
| Evidence labels on AI-found facts, "May be out of date" after 14 days | yes | yes | yes |
| Evidence recheck (`explain`, 1) | credits | credits | credits |
| Verify this plan: read the plan (1), check items (`verify_plan`, 1 per item) | credits; 5 items per run | credits; 12 items per run | credits; 12 items per run |
| How we earn, How billing works, status page, Android install guide | public | public | public |
| Cancel subscription link (one tap) | not applicable | yes | not applicable (a pass never renews) |
| Affiliate booking links | yes | yes | yes |
| Monthly credits | 12 | 60 | 40 once |
| `explain` (1), `packing_list` (1), `booking_import` (1) | credits | credits | credits |
| `draft_day` (1), `draft_trip` (4) | credits | credits | credits |
| `research` (8, 1 cached) | credits | credits | credits |
| `agent_run` manual (40, 8 cached) | credits | credits | credits |
| Deep agent run taster | one, lifetime | no | no |
| Referral credits (F-REF-1): 20 each, 12 month expiry, 5 paid per 30 days and 10 per year for the referrer | yes | yes | yes |
| Data export (JSON, ICS, PDF) | yes | yes | yes |
| Delete account in app | yes | yes | yes |
| Monthly provider-spend ceiling | $0.25 (plus taster) | $2.25 | $1.80 |
| Daily provider-spend budget | $0.05 | $0.40 | $0.40 |

Notes:

- Credit packs (`credits_50`, `credits_150`, `credits_400`) can be bought on any tier and add to
  purchased credits valid 12 months.
- Rules that override any cell: a trip's capabilities are the best of its owner's tier and any
  pass on that trip; AI credits are charged to the person who starts the action; cached data
  always keeps working when a ceiling hits.
- Tiers that arrive later (Family, Pro, Group Trip Pass, advisor seats) are in the full ladder in
  [../README.md](../README.md). Later: Phase 2, see [../phase-2-growth/README.md](../phase-2-growth/README.md).

## 6. Non-functional requirements

### 6.1 Performance targets

| Area | Target |
|---|---|
| App start (warm, iOS, mid-range phone) | Interactive in under 2.0 s at p75; web first contentful paint under 1.5 s on 4G |
| Trip overview and itinerary load | p95 API response under 400 ms; screen usable under 1.5 s |
| Standard read endpoints | p95 under 300 ms; writes p95 under 500 ms |
| Cached fare calendar | Under 600 ms p95 for a route with 12 months of data |
| Place search (cache hit) | Under 300 ms; uncached under 1.5 s |
| Live fare refresh | Result in under 15 s p90, with progress state and cancel |
| `explain` | First text in under 2 s p90 |
| `draft_day`, `draft_trip` | Under 15 s and 45 s p90; streaming preview |
| `research` | Under 90 s p90 |
| `agent_run` | Usually 3 to 10 minutes; live log updates every 2 s; hard cap 20 minutes |
| Sync on shared trip | A change is visible to another member within 30 s; the sync indicator is accurate to 5 s |
| `verify_extract` and each `verify_plan` item | Plan read under 10 s p90; each item under 25 s, 12 items under 90 s p90 |
| Presentation | Slide change under 100 ms; 60 fps drag on calendar |
| Availability | 99.9% monthly for API; planned migrations without downtime |
| Web bundle | Initial JS under 250 KB gzipped, routes code-split |
| Scale target for launch | 10,000 monthly active users, 50 requests per second peak, tested at 10x |

### 6.2 Offline behavior

- Read offline, on every tier: trips the user opened in the last 30 days (up to 10 trips) cache
  their itinerary, flights and fares (with their age), stays, checklist, notes, evidence labels
  and travelers, plus map tiles for the destination area (user can "Download for offline" per
  trip).
- A visible "Offline" bar shows when there is no connection; data age is shown ("Updated 3 h
  ago"); the trip header's sync indicator shows "Offline, N edits waiting" (F-COL-5).
- Write offline: edits to itinerary items, notes and checklist ticks queue locally, send on
  reconnect, last writer wins per field, and a 409 shows the conflict UI.
- Not available offline: search, fares, AI (including Verify this plan and rechecks), imports, purchases, invites, calendar feed setup.
  Buttons explain why.
- No partner content is shown offline.
- Sign-in state survives offline; tokens refresh on reconnect.

### 6.3 Accessibility (WCAG 2.2 AA)

- Meets WCAG 2.2 level AA on web and iOS (VoiceOver, Dynamic Type to XXXL, Reduce Motion, Bold
  Text).
- Text contrast 4.5:1 (3:1 for large text and UI components); never color alone for status
  (votes, prices, statuses also have text or icons).
- Every interactive element is keyboard reachable with visible focus (minimum 2 px ring), logical
  tab order, no traps, and targets at least 24 by 24 CSS pixels (44 pt on iOS).
- Every drag action has a non-drag equivalent (move with buttons or a form), satisfying the
  dragging-movements criterion.
- Calendar, map and charts have text alternatives: list views for the map, a table for the
  price chart, and readable summaries.
- Presentation mode supports keyboard, screen readers (slide titles announced) and respects
  Reduce Motion.
- Forms have visible labels, inline errors, and no time limits without warning (the pass and
  trial screens state dates).
- Consistent help location and no cognitive-test-only steps (email code is paste-friendly,
  autofill works).
- The design system colors (Hermi theme, 05 section 2.3) are checked in light and dark themes for contrast.
- Accessibility checks are in CI (axe on key screens) and a manual screen reader pass runs
  before each release.

### 6.4 Localization

- Launch language: English (US, UK, Canada, Australia spellings via locale). All strings live in
  resource files from day one; no concatenated sentences; plural rules through ICU messages.
- Dates, times, numbers and currencies format by locale; time shown for a place uses that
  place's time zone with the zone label when it differs from the device.
- Units: miles or kilometers by locale with a setting; 12 or 24 hour clock by locale.
- Currencies: trip currency plus conversion with ECB (Frankfurter) rates and the conversion date;
  store prices are in the store currency.
- Right-to-left layout is supported in the component library (logical CSS properties) but no RTL
  language ships at launch.
- Next languages (year 2): Spanish, French, German, Portuguese; AI output follows the user's
  language setting.
- UK and EU storefronts show the "Ad" tag on partner buttons and the comparison basis statement.

### 6.5 Privacy and security

- Tenant isolation: every trip resource is reached through trip membership; non-members get 404;
  Postgres row-level security as a second layer; a cross-tenant test hits every route with
  another user's ids and must pass in CI.
- Data sent to AI providers: destinations, dates, party size, budget, preferences and text the
  user typed; never email, name, account id, other travelers' names, payment data or private
  notes. Zero-retention or no-training terms with providers.
- No ad SDKs, no cross-app tracking, no ATT prompt; analytics through PostHog with no device ids
  and opt-out in Settings; Apple privacy label and `PrivacyInfo.xcprivacy` match the real data
  use.
- Retention: soft-deleted trips 30 days; deleted accounts 30 days then purge, backups age out
  within 35 days; invite tokens purged at 30 days; the audit log 13 months (money, security and control actions
  7 years) with IPs hashed from the start; AI prompt content 30 days server side; crash and analytics data 90 days.
- GDPR and CCPA: export and delete in the app, consent records, breach notice within 72 hours,
  no sale of data (stated in the policy).
- Transport and storage: TLS everywhere, encryption at rest, files in R2 behind signed expiring
  URLs with keys prefixed by trip id, secrets only in environment variables.
- Abuse limits: rate limits as in the architecture file; App Attest for guest AI and new-account
  fraud; disposable email blocklist; report and block on shared trips.
- Children: not for children; age gate 13+ (16+ in EU and UK); minors on a trip are first names
  only.
- Site terms: no scrapers, no fetching of Airbnb, Vrbo or Booking.com pages by the server, ever, and no reading of Google Maps list links.

### 6.6 Reliability and data

- Point-in-time recovery on the database; a restore drill is run before launch.
- Jobs are idempotent and retry with backoff; a failed agent run refunds credits automatically.
- Provider outages degrade gracefully: cached data shows with its age, live actions show a clear
  message and are not charged.
- Every money, credit and entitlement change writes an immutable ledger row.

## 7. Out of scope

### 7.1 Later phases

Each line is a pointer only. These features are not specified, built or sold in Phase 1.

- Family plan and households: Later: Phase 2, see [../phase-2-growth/README.md](../phase-2-growth/README.md).
- Group Trip Pass, polls, manual cost splitting, room-block requests: Later: Phase 2, see [../phase-2-growth/README.md](../phase-2-growth/README.md).
- Comments on items (comments with mentions included): Later: Phase 2, see [../phase-2-growth/README.md](../phase-2-growth/README.md).
- Email-forward import (plans@hermi.world): Later: Phase 2, see [../phase-2-growth/README.md](../phase-2-growth/README.md).
- Flight status, delay and gate alerts: Later: Phase 2, see [../phase-2-growth/README.md](../phase-2-growth/README.md).
- Pro tier and scheduled agent routines: Later: Phase 2, see [../phase-2-growth/README.md](../phase-2-growth/README.md).
- Concierge lane (host agency): Later: Phase 2, see [../phase-2-growth/README.md](../phase-2-growth/README.md).
- Direct affiliate programs (Expedia Group and Vrbo, Booking.com, Skyscanner, Airalo, GetYourGuide): Later: Phase 2, see [../phase-2-growth/README.md](../phase-2-growth/README.md).
- Native Android app and web billing: Later: Phase 2, see [../phase-2-growth/README.md](../phase-2-growth/README.md).
- "Paste your group chat" to draft a plan, and repair-a-day when plans change: Later: Phase 2, see [../phase-2-growth/README.md](../phase-2-growth/README.md).
- After-trip flight compensation prompt, memories and "Year in travel" card: Later: Phase 2, see [../phase-2-growth/README.md](../phase-2-growth/README.md).
- Stripe group payments: Later: Phase 3, see [../phase-3-scale/README.md](../phase-3-scale/README.md).
- Hermi for Advisors: Later: Phase 3, see [../phase-3-scale/README.md](../phase-3-scale/README.md).
- Partner guides, printed trip books, in-app hotel booking (LiteAPI), white-label and API, card and loyalty offers: Later: Phase 3, see [../phase-3-scale/README.md](../phase-3-scale/README.md).

### 7.2 Not planned

- Apple Watch, native iOS rewrite, iPad-specific layouts beyond responsive web.
- Banner ads, sponsored slots, paid placement in search or lists, ranking by commission, selling
  user data, cashback, lifetime plans.
- Real-time co-editing, cursors, presence and CRDTs.
- In-app flight or hotel booking and payment for flights or stays inside the app, ticketing, and
  airline check-in (a merchant-of-record partner is a year 2 or later question).
- Scraping, automatic fetching of Airbnb, Vrbo or Booking.com pages, and any converted or
  rewritten Airbnb link.
- Insurance, visa, immigration or legal advice from AI; selling insurance in the app other than
  labeled partner links with approved copy.
- Expense and payment features for digital goods; any payment flow through Apple In-App Purchase
  for real-world costs.
- Credit cards, VPNs and Amazon product data.
- Apple Family Sharing, passwords, SMS sign-in, passkeys at launch.
- Owner-funded shared credit pools on group trips (credits follow the acting user).
- Reading anyone's email or calendar account (no Gmail or Google Calendar sign-in, no OAuth to
  TripIt, Tripsy or Wanderlog, and no scraping of Google Maps lists). Phase 1 imports only files,
  feed links the user pastes, and text the user pastes. Also out: loyalty program tracking and visa application filing.
- Social feed, browsing of other people's trips, user reviews of places, and user-generated public
  guides. The public sample trips are a fixed list written by Hermi.
- Languages other than English at launch, and right-to-left languages.
