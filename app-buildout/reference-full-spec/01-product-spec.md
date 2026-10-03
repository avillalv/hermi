# Hermi product specification

Part of the [build specification](../README.md). Written 2026-09-30. The shared decisions in the
folder README (tiers, credit actions, entity names, rules) are final and are used here exactly.
This file says what the product does. Architecture, schema, API, screens and AI internals are in
the other files and are referenced where they matter.

How to read a feature entry: each has a user story, acceptance criteria written as testable
bullets, tier availability, credit cost, and edge cases. Feature ids (for example `F-FLT-3`) are
stable and are reused by the roadmap and test plans. "Owner" means the trip owner, "editor" and
"viewer" are trip roles (see F-COL-2). Tier codes are `free`, `plus`, `family`, `pro`,
`trip_pass`, `group_trip_pass`.

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
10. **Two to twelve people, not thousands.** Collaboration is built for small groups. Polling
    with conditional requests is enough; no real-time editing.

### 1.3 Platforms

iOS app (Capacitor wrapper around the React app, bundled) and the web app. Both ship the same
features except: purchases of subscriptions, Trip Pass and credit packs happen through the App
Store in the iOS app (RevenueCat over StoreKit 2); group payments, advisor billing and printed
books run on the web through Stripe. Android is later.

## 2. Personas

### P1. Couple planners (primary)

Maya and Dev, both 30s, plan two to three trips a year together, often on phones in the evening.
Goals: agree on dates, find a fare that is not a rip-off, pick one stay they both like, and have
one place to look during the trip. Pain: links scattered across messages, one person doing all
the work, fare anxiety ("did it drop?"). Buys: Trip Pass for the big trip, annual `plus` if they
travel often.

### P2. Friend-group organizer

Sam organizes a bachelor weekend or a 10-person ski trip. Goals: get everyone to agree on dates
and a stay, know who owes whom, stop chasing people for money. Pain: decision by attrition,
Splitwise plus Doodle plus WhatsApp. Buys: `group_trip_pass` ($19.99) because it is one fee for
everyone. Most invitees are `free` accounts.

### P3. Family

Priya, two kids, her parents joining for one week. Goals: one household plan, simple daily
schedule with kid-friendly notes, everyone sees the same thing, including grandparents who will
not install anything. Pain: nap times, too many choices, cost. Buys: `family` so four adults in
the household share 150 credits and 5 live routes; uses read-only share links for grandparents.

### P4. Deal hunter

Luis flies 8 to 12 times a year and watches fares obsessively. Goals: know when a fare drops on
the routes he tracks, find budget airline fares the price APIs miss, compare total trip cost.
Pain: alerts that cry wolf, tools that hide how old a price is. Buys: `plus` annual, credit
packs for agent runs, `pro` when it launches.

### P5. Independent travel advisor (year 2)

Nora is a freelance advisor under a host agency. Goals: build client trips quickly, present them
in her brand, track commissions. Pain: Word documents and PDFs, no collaboration with clients.
Buys: `advisor_seat` on the web. Specified at summary level in F-ADV.

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

Success: account exists, trip is saved, no data was lost, no paywall was shown.

### 3.2 Create a trip

1. From trips home, "New trip". User types a destination; autocomplete suggests places.
2. User optionally adds more destinations, optional dates or a flexible month, a trip name, and
   home currency.
3. Trip overview opens with destination summary, photo, local time and money info, and an empty
   state that points to the next step (flights, stays, days). (F-TRP-1 to F-TRP-4)

### 3.3 Invite

1. After three or more items exist, a soft nudge offers "Invite your travel partner".
2. Owner on `plus`, `family`, `pro`, `trip_pass` or `group_trip_pass` enters an email or copies a
   link, picks a role (editor or viewer). Owner on `free` sees the paywall moment (Trip Pass
   first). (F-COL-3)
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
3. Group expenses are logged as they happen. (F-GRP-2)

### 3.11 After the trip

1. The day after the last trip date, if a flight was chosen: "Was your flight delayed or
   cancelled?" (F-AFT-1)
2. "How was the trip?" card; trip moves to archived after 14 days; expenses settle. (F-AFT-2,
   F-GRP-4)
3. Export, archive or start the next trip from a past one (duplicate). (F-TRP-6)

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
- Tier: `free` 2 active trips; `plus`, `family`, `pro` unlimited (fair use 25); `trip_pass` and
  `group_trip_pass` apply to the one passed trip.
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
- Tier: `free` 2 travelers per trip; `plus`, `family`, `trip_pass` 8; `pro` and
  `group_trip_pass` 12.

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
    candidates without votes, and checklist; it never copies members, expenses, notes or agent
    output.
  - Counts toward the active trip limit.
- Tier: all, subject to trip limits.

#### F-TRP-7 Trip overview

- Story: As a member, I want one page that says where the trip stands, so that I know what to do
  next.
- Acceptance:
  - Shows destinations, dates or "Dates not set", chosen flight, booked or shortlisted stay,
    itinerary progress, open polls, "Found by agents" notes, checklist card, and next suggested
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
| Vote, react, comment | yes | yes | yes |
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
  - Collaborator caps: `plus` and `family` and `pro` up to 6 collaborators per trip (`pro` up to
    12); `trip_pass` up to 6; `group_trip_pass` up to 12 travelers in total.
  - A `free` owner tapping Invite sees the paywall moment; the copy says "They join free".
  - Owner can revoke a pending invite or remove a member at any time.
  - The invite email uses the inviter's display name and Hermi's sending domain.
- Tier: `plus`, `family`, `pro`, `trip_pass`, `group_trip_pass` to invite; everyone can accept.
- Edge cases: expired token shows "Ask <name> for a new link"; invite email differing from the
  account email is accepted (the token is the proof); a member already on the trip is told so.

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
- Tier: all on shared trips.

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
- Tier: `plus`, `family`, `pro`, `trip_pass`, `group_trip_pass` create; anyone with the link
  views.

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
  - Routes per trip (`routes_per_trip`): `free` 1; `plus` 5; `family` 5; `pro` 8; `trip_pass` 3;
    `group_trip_pass` 3. Live-tracked routes (`live_routes`): `plus` 3; `family` 5; `pro` 6;
    `trip_pass` 2; `group_trip_pass` 2. Routes beyond the live limit still work on cached fares.
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
  - Live route counts: `plus` 3, `family` 5, `pro` 6, `trip_pass` 2 (max 60 live checks for the
    pass), `group_trip_pass` 2. Account-level routes for `plus`, `family` and `pro` count across
    trips.
  - Checks stop when the month's provider-spend ceiling is hit; the UI says "Live checks resume
    on the 1st" and cached fares continue.
  - A live observation is stored in `fare_observations` with provider, fetched time and cost in
    micro-dollars, and logged in `provider_calls`.
  - Identical searches by different users within 6 hours reuse one result.
- Tier: `plus`, `family`, `pro`, `trip_pass`, `group_trip_pass`. Credits: none for scheduled
  checks.
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
  - The card shows fare age, route, stops and a "Mark as booked" toggle.
  - Itinerary days outside the new dates are kept as ideas, never deleted.
- Tier: all. Credits: none.

#### F-FLT-6 Price alerts

- Story: As a deal hunter, I want to be told when a fare drops, so that I do not watch it.
- Acceptance:
  - An alert (`price_alerts`) sets a target price or "any drop of X percent" on a route.
  - `free` gets 1 alert on cached fares; `plus` 3; `family` 5; `pro` 6; `trip_pass` 2;
    `group_trip_pass` 2; paid tiers alert on live and cached fares.
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
    `trip_pass` 30; `plus`, `family`, `pro` unlimited (fair use 100); `group_trip_pass` 30.
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
  - Ideas can be hearted and commented by any member.
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
  - Soft limits per day: `free` 30 searches, `plus`, `family`, passes 100, `pro` 200; cached
    results always work.
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
  - `pro` users get priority in the queue; others see "Queued, position N".
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

- Story: As a `pro` user, I want a fare hunt or research to run on a schedule, so that I hear
  about new findings without asking.
- Acceptance:
  - A routine (`routines`) has a trip, kind (hunt fares or research), and cadence up to once per
    day with at least 12 hours between runs; up to 3 per trip.
  - Each scheduled run costs 40 credits (`agent_run`) from the routine owner's balance and uses
    the same caps; scheduled work uses the shared cache first.
  - A routine pauses itself when credits run out, the ceiling hits, or the trip is in the past,
    and says why.
  - Notification digest after each run with what changed, never more than one per routine per
    day.
  - Hidden and disabled for all other tiers until `pro` launches; `pro` is built behind a
    feature flag. Non-Pro users who open the Routines screen see a sample result from the
    shared cache and the credit-based manual alternative.
- Tier: `pro` only. Credits: `agent_run` 40 per run.

#### F-AI-8 AI metering and limits

- Story: As the business, I want no account to cost more than it pays, so that the product
  survives.
- Acceptance:
  - Monthly provider-spend ceilings and daily budgets are enforced on the server as in the
    README; the ledger fails closed if it cannot be read.
  - AI endpoints are limited to 10 per minute per account and 30 AI actions per hour.
  - Family draws from the household pool; Trip Pass and Group Trip Pass credits are spent
    before purchased credits.
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

#### F-NTE-2 Evidence view

- Story: As a skeptical user, I want to see where a fact came from, so that I can verify it.
- Acceptance:
  - Every AI-found item has a "Source" chip that opens the original URL and shows the date seen.
  - The run page lists rejected items and why.
  - An item whose source later fails is not removed but shows "Source not checked since <date>".
- Tier: all.

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

Real-world money handling is through Stripe, never Apple In-App Purchase, and never for digital
features.

Gating rule for the whole section: polls and manual cost splitting (expenses, balances, "mark as
paid") are included in `plus`, `family`, `pro`, `trip_pass` and `group_trip_pass`. A `free` user
uses them on any trip whose capabilities include them (for example a trip they joined, or a trip
with a pass); a `free` owner's own trip shows a preview and the paywall moment. The Group Trip Pass
adds up to 12 travelers and the room-block request. Collecting money through Stripe (F-GRP-4,
Phase 4) is for `group_trip_pass` and `pro` only.

#### F-GRP-1 Polls

- Story: As an organizer, I want a quick vote on dates, stays or activities, so that the group
  decides without a chat thread.
- Acceptance:
  - A poll (`polls`) has a question, 2 to 12 options, single or multiple choice, optional
    deadline, and anonymous or named; votes in `poll_votes`.
  - Poll types: free text, date ranges, or pick from the trip's lodging candidates or ideas.
  - Members vote from the app or the link; results update live on refresh; owner closes the poll
    and can apply the winner (for example, marks the winning stay "Shortlisted").
  - Viewers can vote.
  - Reminder notification to members who have not voted, at most once per poll per day.
- Tier: `plus`, `family`, `pro`, `trip_pass`, `group_trip_pass`, and `free` users on trips that
  have them. A `free` owner sees polls as a preview with the `trip_pass` paywall moment. Credits:
  none.

#### F-GRP-2 Expenses

- Story: As a traveler, I want to log who paid for what, so that costs stay fair.
- Acceptance:
  - An expense (`expenses`) has amount in minor units plus currency, payer, date, category,
    description, and shares (`expense_shares`) by equal split, by exact amounts, by percentages,
    or by shares; the description can name the item or stay it is for.
  - Foreign currency amounts convert to the trip currency with the ECB rate of the expense date
    and store both.
  - Editors and owners can add; every member can view their own balance.
  - Deleting an expense keeps an audit line.
- Tier: `plus`, `family`, `pro`, `trip_pass`, `group_trip_pass`, and `free` users on trips that
  have them; the traveler cap is the trip's own limit (8, or 12 on a Group Trip Pass or `pro`).
  A `free` owner sees a preview with the `trip_pass` paywall moment. Credits: none.

#### F-GRP-3 Cost splitting

- Story: As a member, I want to see who owes whom in the fewest payments, so that settling is
  easy.
- Acceptance:
  - The balance screen shows each traveler's net position and a minimized set of transfers.
  - Rounding: amounts are integer minor units; leftover cents are assigned deterministically
    (by traveler order) so totals always match.
  - Travelers without accounts (`people` with no linked user) are included and shown by name.
- Tier: same as F-GRP-2.

#### F-GRP-4 Settlements

- Story: As a debtor, I want to pay or record a payment, so that the trip is squared away.
- Acceptance:
  - A settlement (`settlements`) is "Pay with card or bank through Stripe" (web, funds go to the
    organizer's connected account as a destination charge inside a `payment_collections` row;
    Hermi takes no cut in year 1) or "Mark as paid" (manual, both sides confirm).
  - Status (`settlements.status`): pending (waiting for the payee to confirm, or for Stripe),
    recorded (confirmed manual payment), succeeded (Stripe paid), failed, refunded, disputed.
    Recorded and succeeded settlements reduce balances.
  - Payment is only for real-world trip costs; nothing digital is sold through it.
  - The organizer must complete Stripe Connect onboarding to collect (`users.stripe_connect_account_id`);
    manual marking works without it.
- Tier: Stripe collection is `group_trip_pass` and `pro` only and ships in Phase 4 (flag
  `group_payments`); manual marking is in every F-GRP-2 tier from launch.
- Edge cases: a member leaves with a balance: the balance stays and the owner can write it off
  with an audit line; currency mismatch settles in the trip currency.

#### F-GRP-5 Room-block request

- Story: As an organizer of a wedding or event, I want to ask for a hotel room block, so that
  guests get a group rate.
- Acceptance:
  - A form (`room_block_requests`) takes hotel (from the shortlist or typed), dates, rooms, guest
    count, budget and notes.
  - Submission is routed to the concierge team (host agency), who reply by email within 2
    business days; status is visible (submitted, in review, quoted, accepted, declined, expired, cancelled).
  - The form shows a plain disclosure: "Hermi may earn a commission from the hotel or our host
    agency. It does not change what you pay."
  - Request creates no charge and no obligation.
- Tier: `group_trip_pass` only (a trip with a Group Trip Pass, including for its invited members).
  Credits: none.

### 4.12 Concierge request (F-CON)

- Story: As a user planning a stay, cruise or complex trip, I want an option to have a human
  book it, so that I can skip the work and get perks.
- Acceptance:
  - A quiet "Have a human book this" action on a booked-intent stay, a cruise idea, or a trip
    with 3 or more destinations opens a short form (`concierge_requests`): what to book, dates,
    budget, preferences, contact preference.
  - The screen explains: a licensed advisor under a host travel agency fulfills it, you may get
    perks such as breakfast or credits, Hermi earns commission from the supplier, price to you
    is not higher.
  - It is never pushed, never pop-up, and appears at most once per screen view.
  - Status timeline: submitted, assigned, quoted, booked, declined; replies arrive by email and
    in-app.
  - A declined request says why and offers the DIY path.
  - Booking payments are handled by the agency, outside the app.
- Tier: all. Credits: none.
- Edge cases: region not served shows "Not available in your area yet"; duplicate requests for
  the same item are merged.

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
10. Settings has "How we earn money" listing partners and the ranking rule, with a "Hide booking
    links" switch that collapses buttons to a plain "Open on partner site" link.

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
    (booking.com, vrbo.com, expedia.com, hotels.com, agoda.com, trip.com, hostelworld.com), built
    from the URL text and trip dates, never by fetching the page; never for Airbnb.
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

- Checklist "Get it" buttons (F-CHK-1), optional "Book the plan" slide (F-PRS-1), the after-trip
  compensation link (F-AFT-1), and a "Today" card during the trip (F-TRV-1) follow the same
  global rules. Trip created, flight charts, lodging import, agent pages, trips home and
  paywalls carry no affiliate UI.

#### F-AFF-6 Launch partners

- Travelpayouts (flights, stays, cars, transfers, tours, eSIM, insurance), Viator partner API,
  Stay22 at launch; Expedia Group (Vrbo), Booking.com, Skyscanner, Airalo, GetYourGuide from
  month 3. Airbnb is plain links only.

### 4.14 Notifications and email (F-NOT)

#### F-NOT-1 Channels and preferences

- Story: As a user, I want to choose what I am told and where, so that I am never spammed.
- Acceptance:
  - Channels: push (APNs), in-app inbox, email (Resend). Settings has a matrix of event types by
    channel.
  - Event types: price alert, invite accepted, member joined, poll opened or closed, expense
    added, settlement requested, agent run finished, checklist reminder, concierge update,
    export ready, deletion steps.
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

- Acceptance: invite, sign-in code, receipts for Stripe payments, export ready, deletion
  confirmation, concierge and room-block updates; sender name shows the inviter for invites;
  every email renders in plain text too.

### 4.15 Settings, export and delete account (F-SET)

#### F-SET-1 Settings

- Acceptance: sections for Account (name, email, sign-in methods, devices with "sign out
  everywhere"), Preferences (home airports, currency, units, locale, time zone, theme),
  Notifications (F-NOT-1), AI (consent, per-trip toggles, credit history), Subscription
  (F-SUB), How we earn money, Privacy, Help and Legal. Changes save immediately.

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
  - Plans screen shows `free`, `plus`, `family`, `trip_pass`, `group_trip_pass`, and credit
    packs; `pro` is hidden until its flag is on.
  - `plus` $5.99 a month or $39.99 a year (annual pre-selected, 7-day trial on annual only),
    `family` $8.99 or $59.99, `pro` $11.99 or $99, `trip_pass` $9.99, `group_trip_pass` $19.99,
    `credits_50` $2.99, `credits_150` $6.99, `credits_400` $14.99.
  - Subscriptions share the `hermi_membership` group; upgrade, downgrade and cross-grade follow
    StoreKit rules.
  - The trial screen states the price and renewal date; a reminder is sent before conversion.
  - Restore purchases is always present.
  - Web purchases of advisor seats, group payments and print are through Stripe.
  - Entitlements are stored server side from RevenueCat and App Store Server Notifications v2;
    the client reads `GET /me/entitlements` and never decides.
- Tier: all. Credits: none.

#### F-SUB-2 Passes

- Story: As a trip-focused user, I want to upgrade one trip, so that I do not subscribe.
- Acceptance:
  - A Trip Pass or Group Trip Pass is bound to one trip on the server (`trip_passes`) and lasts
    90 days from binding. Purchase comes first, binding second: the purchase is a
    `store_transactions` row (`kind = 'pass'`) and the pass has no trip until the owner picks one.
  - Binding flow: before the purchase the app asks "Which trip is this for?" (pre-selected when
    the purchase started from a trip) and sends the trip with `POST /v1/purchases/sync`. A pass
    bought with no trip waits as "unapplied" in Settings, Purchases (listed by `GET /v1/me/passes`,
    kept 12 months) until the owner binds it with `POST /v1/me/passes/{pass_id}/bind`. Only the
    trip's owner can bind, and the purchaser must be that owner. A trip holds one active pass;
    a second apply of the same plan is refused.
  - One move: an active pass can move to another trip the same owner owns, once
    (`POST /v1/me/passes/{pass_id}/move`). The move keeps the original expiry, carries the
    unspent pass credits and the live-check counter, and pauses live routes on the old trip. A
    second move is refused.
  - Upgrade: buying a Group Trip Pass for a trip that has an active Trip Pass replaces it (the
    Trip Pass becomes `upgraded`, the new pass gets a full 90 days, the live-check counter carries
    over and unspent Trip Pass credits stay spendable until their own expiry).
  - Trip Pass: 2 live routes, at most 60 live checks, 40 credits, up to 6 collaborators, polls and
    manual cost splitting. Group Trip Pass: the same plus up to 12 travelers, 80 credits and the
    room-block request. The passed trip does not count toward the owner's active-trip limit.
  - A trip's capabilities are the best of its owner's tier and any pass on it.
  - Pass credits are a pool tied to the trip (a `trip_pass` grant with the trip id), expire with
    the pass after 90 days, are spendable by any member acting on that trip, and are spent after
    the actor's monthly allowance and before purchased credits.
  - The trip settings screen shows the pass status and expiry, a notice 7 days before expiry, and
    a renewal offer (a new pass starts a new 90 days).
  - Default paywall order: Trip Pass first when a trip has dates within 120 days; annual `plus`
    first when the user has 2 or more active trips.
- Tier: purchasable by any user. Credits: pass credits as above.
- Edge cases: a pass bought while on `plus` still applies its extra group features; an expired
  pass returns the trip to the owner's tier (F-SUB-6); a refunded pass stops granting
  capabilities and its unspent credits are removed.

#### F-SUB-3 Family

- Story: As a household, I want to share one plan, so that everyone uses the same pool.
- Acceptance:
  - The `family` payer creates a household (`households`) and invites up to 6 members
    (`household_members`) in the app; Apple Family Sharing stays off.
  - Members get `plus` capabilities on their own trips, 5 live routes and 150 credits pooled,
    drawn by whoever acts.
  - A person can be in one household at a time; leaving takes effect immediately and the person
    returns to their own tier.
  - When the payer cancels, the household reverts to `free` at period end.
- Tier: `family`.

#### F-SUB-4 Credits

- Story: As a user, I want to see and top up credits, so that I am never surprised.
- Acceptance:
  - Monthly grants: `free` 12, `plus` 60, `family` 150 pooled, `pro` 240 (one month rolls over,
    capped at 240), `trip_pass` 40 once, `group_trip_pass` 80 once; monthly grants do not roll
    over (except `pro`).
  - Purchased packs last 12 months and are spent last; expiry dates are shown.
  - Spend order: monthly allowance (or the household pool), then promo (the taster), then pass
    credits for that trip, then adjustments, then purchased credits (oldest expiry first).
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
| Invite a collaborator | `free` owner | `trip_pass` ("They join free") |
| Draft or research out of credits | 0 credits | Credit pack or `plus` |
| Scheduled routine | Not `pro` | Sample result, credit-based manual run |
| Polls or cost splitting on a `free` owner's trip | `free` owner | `trip_pass` or `plus` |
| More than 8 travelers, or room-block request | Not group pass | `group_trip_pass` |
| Collect payments through Stripe (Phase 4) | Not group pass or `pro` | `group_trip_pass` |
| Presentation footer and PDF watermark | `free` share | `trip_pass` (soft, at export) |
| Saving the 9th stay | `free` limit | Keep in "Later", `trip_pass` |
| 14 days before departure on a `free` trip | Lifecycle | `trip_pass` (email or push, opt-in) |

- Acceptance: the "After booking through an affiliate link" moment shows no paywall; no
  countdown timers, no invented scarcity, no "unlimited" claims in copy.

#### F-SUB-6 Downgrade and lapse

- Acceptance:
  - Data is never deleted or hidden on downgrade; archived and over-limit trips stay readable
    and exportable.
  - A lapsed owner's trip becomes limited: extra members become viewers, live tracking pauses,
    polls close, extras are kept and come back if the owner renews.
  - A banner tells the owner what changed and how to restore.
  - Cancellation and a 3 month pause are offered before cancelling (where the store allows).

### 4.17 Travel and after-trip (F-TRV, F-AFT)

#### F-TRV-1 Today view

- Story: As a traveler, I want today's plan front and center, so that I can just follow it.
- Acceptance: during trip dates the trip opens on "Today" with local time, next item, map, stay
  address and confirmation numbers; an optional "Today" partner card appears only if an
  unbooked eligible activity exists and never with urgency copy; no partner content offline.
- Tier: all.

#### F-TRV-2 Offline read

- Acceptance: itinerary, stay details, checklist, notes and maps tiles for the trip area are
  cached for reading; the offline state is shown; edits queue per section 6.2.
- Tier: all.

#### F-AFT-1 Delay prompt

- Acceptance: the day after the last trip date, if a flight was chosen: "Was your flight delayed
  or cancelled?" with "No" and "Yes, check what I can claim"; only "Yes" shows a partner link
  with the commission sentence and a note that eligibility depends on route and rules and no
  result is promised; never a push; not shown without a chosen flight.

#### F-AFT-2 Wrap-up

- Acceptance: "How was the trip?" card with a 1 to 5 rating and a note, no affiliate button; 14
  days after the end the trip is offered for archive; settlement reminders for unsettled
  expenses once.

### 4.18 Advisor workspace (F-ADV, year 2, summary level)

Sold as `advisor_seat` on the web through Stripe ($29 a seat a month, $24 annual).

- Story: As an independent advisor, I want to build and present client trips under my brand, so
  that I look professional and track what I earn.
- Scope (summary, to be specified in detail before year 2):
  - Advisor organization (`advisor_orgs`) with seats (`advisor_seats`) and clients
    (`advisor_clients`).
  - Client workspaces: a trip the advisor owns with the client as viewer or editor, with
    private advisor notes the client cannot see.
  - Branded presentation mode (logo, colors, contact, custom domain later).
  - Proposals: a shareable, read-only package of options with a client approval action.
  - Commission tracking: manual entries and, where available, imported supplier statements;
    totals per client and per month.
  - Templates: reusable trip skeletons.
  - Client data stays the client's: the client can export and leave.
- Acceptance (summary): seat billing works in Stripe; an advisor can create a client trip,
  invite the client, present it branded, and record a commission line; clients need no paid plan.
- Out of this file: detailed screens, compliance with advisor agency rules.

### 4.19 Printed trip book (F-PRT, year 2, summary level)

- Story: As a traveler, I want a printed book of the trip, so that I keep a keepsake.
- Scope (summary):
  - Ordered on the web (Stripe) from presentation mode; print-on-demand vendor (`print_orders`).
  - Layout follows the presentation slides with photos, maps and day pages; preview and proof
    before payment; price shown before checkout; shipping to supported countries.
  - Partner links are omitted from print by default.
- Acceptance (summary): order created, paid, sent to the vendor, tracked, and refunded on
  vendor failure.

## 5. Tier and entitlement matrix

Legend: yes, no, number (limit), or note. `free` $0; `plus` $5.99 or $39.99 a year; `family`
$8.99 or $59.99 a year; `pro` $11.99 or $99 a year (launches later); `trip_pass` $9.99 for one
trip for 90 days; `group_trip_pass` $19.99 for one trip for 90 days. For passes, every value
applies to the passed trip only.

| Capability | free | plus | family | pro | trip_pass | group_trip_pass |
|---|---|---|---|---|---|---|
| Active trips | 2 | unlimited (fair use 25) | unlimited (fair use 25) | unlimited (fair use 50) | the trip | the trip |
| Join others' trips | yes | yes | yes | yes | yes | yes |
| Archived trips: read and export | yes | yes | yes | yes | yes | yes |
| Travelers per trip | 2 | 8 | 8 | 12 | 8 | 12 |
| Destinations per trip | 12 | 12 | 12 | 12 | 12 | 12 |
| Invite collaborators | no | yes, 6 per trip | yes, 6 per trip | yes, 12 per trip | yes, 6 | yes, up to 12 travelers |
| Read-only share link | no | yes | yes | yes | yes | yes |
| Routes per trip (cached fares; live where allowed) | 1 | 5 | 5 | 8 | 3 | 3 |
| Airports per side of a route | 2 | 4 | 4 | 4 | 4 | 4 |
| Live-tracked routes (daily, within 120 days) | 0 | 3 | 5 | 6 | 2 (max 60 checks) | 2 |
| Refresh now (live peek) | 1 credit | 1 credit | 1 credit | 1 credit | 1 credit | 1 credit |
| Price alerts | 1 cached | 3 live and cached | 3 live and cached | 6 live and cached | 2 | 2 |
| Saved stays per trip | 8 | unlimited (fair use 100) | unlimited (fair use 100) | unlimited | 30 | 30 |
| Lodging compare | 2 | 4 | 4 | 4 | 4 | 4 |
| Rental search | 1 credit | 1 credit | 1 credit | 1 credit | 1 credit | 1 credit |
| Place searches per day (soft) | 30 | 100 | 100 | 200 | 100 | 100 |
| Itinerary, ideas, map | yes | yes | yes | yes | yes | yes |
| Presentation mode | yes, footer and watermark | yes | yes | yes | yes | yes |
| Before-you-go checklist | yes | yes | yes | yes | yes | yes |
| After-trip prompt | yes | yes | yes | yes | yes | yes |
| Affiliate booking links | yes | yes | yes | yes | yes | yes |
| Monthly credits | 12 | 60 | 150 pooled (6 members) | 240 (one month rolls over) | 40 once | 80 once |
| `explain` (1), `packing_list` (1), `booking_import` (1) | credits | credits | credits | credits | credits | credits |
| `draft_day` (1), `draft_trip` (4) | credits | credits | credits | credits | credits | credits |
| `research` (8, 1 cached) | credits | credits | credits | credits | credits | credits |
| `agent_run` manual (40, 8 cached) | credits | credits | credits | credits | credits | credits |
| Deep agent run taster | one, lifetime | no | no | no | no | no |
| Scheduled agent routines | no | no | no | yes, 3 per trip | no | no |
| Priority queue | no | no | no | yes | no | no |
| Polls | on trips that have them (own trip: preview) | yes | yes | yes | yes | yes |
| Expenses and manual cost splitting | on trips that have them (own trip: preview) | yes, 8 travelers | yes, 8 travelers | yes, 12 travelers | yes, 8 travelers | yes, up to 12 |
| Stripe settlements (Phase 4) | no | no | no | yes | no | yes |
| Room-block request | no | no | no | no | no | yes |
| Concierge request | yes | yes | yes | yes | yes | yes |
| Data export (JSON, ICS, PDF) | yes | yes | yes | yes | yes | yes |
| Delete account in app | yes | yes | yes | yes | yes | yes |
| Monthly provider-spend ceiling | $0.25 (plus taster) | $2.25 | $3.40 pooled | $5.50 | $1.80 | $3.60 |
| Daily provider-spend budget | $0.05 | $0.40 | $0.40 | $1.25 | $0.40 | $0.40 |
| Advisor workspace | no (separate `advisor_seat`) | no | no | no | no | no |

Notes:

- Credit packs (`credits_50`, `credits_150`, `credits_400`) can be bought on any tier and add to
  purchased credits valid 12 months.
- Rules that override any cell: a trip's capabilities are the best of its owner's tier and any
  pass on that trip; AI credits are charged to the person who starts the action; cached data
  always keeps working when a ceiling hits.
- `pro` features are built behind a feature flag and appear only when the flag is on.
- Group tools: polls and manual cost splitting are in every paid plan and both passes, and a
  `free` user has them on any trip that has them. The Group Trip Pass adds up to 12 travelers and
  the room-block request. Stripe collection is `group_trip_pass` and `pro` only and arrives in
  Phase 4.
- Launch scope: `free`, `plus`, `family`, `trip_pass`, `group_trip_pass` and credit packs are sold
  at launch; `pro` stays behind its flag until its launch gate; Stripe group payments, advisors,
  print and LiteAPI are Phase 4.

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
| Sync on shared trip | A change is visible to another member within 30 s |
| Presentation | Slide change under 100 ms; 60 fps drag on calendar |
| Availability | 99.9% monthly for API; planned migrations without downtime |
| Web bundle | Initial JS under 250 KB gzipped, routes code-split |
| Scale target for launch | 10,000 monthly active users, 50 requests per second peak, tested at 10x |

### 6.2 Offline behavior

- Read offline: trips the user opened in the last 30 days (up to 10 trips) cache their
  itinerary, stays, checklist, notes, travelers and expenses, plus map tiles for the destination
  area (user can "Download for offline" per trip).
- A visible "Offline" bar shows when there is no connection; data age is shown ("Updated 3 h
  ago").
- Write offline (phase 2 of the collaboration plan): edits to itinerary items, notes, checklist
  ticks and expenses queue locally, send on reconnect, last writer wins per field, and a 409
  shows the conflict UI.
- Not available offline: search, fares, AI, purchases, invites, settlements. Buttons explain why.
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
- The design system colors (the Hermi theme) are checked in light and dark themes for contrast (the measured pairs are in 05 section 2.3).
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
- Site terms: no scrapers, no fetching of Airbnb, Vrbo or Booking.com pages by the server, ever.

### 6.6 Reliability and data

- Point-in-time recovery on the database; a restore drill is run before launch.
- Jobs are idempotent and retry with backoff; a failed agent run refunds credits automatically.
- Provider outages degrade gracefully: cached data shows with its age, live actions show a clear
  message and are not charged.
- Every money, credit and entitlement change writes an immutable ledger row.

## 7. Out of scope

Not part of this specification or the launch build:

- Android app (later), native iOS rewrite, Apple Watch, iPad-specific layouts beyond responsive
  web.
- Banner ads, sponsored slots, paid placement in search or lists, ranking by commission, selling
  user data, cashback, lifetime plans.
- Real-time co-editing, cursors, presence, CRDTs, and comments with mentions (comments are
  phase 4 of collaboration).
- In-app flight or hotel booking, payment for flights or stays inside the app (year 2 or later
  through a merchant-of-record partner), ticketing, and airline check-in.
- Scraping, automatic fetching of Airbnb, Vrbo or Booking.com pages, and any converted or
  rewritten Airbnb link.
- Insurance, visa, immigration or legal advice from AI; selling insurance in the app other than
  labeled partner links with approved copy.
- Expense and payment features for digital goods; any payment flow through Apple In-App Purchase
  for real-world costs.
- Credit cards, VPNs and Amazon product data.
- Apple Family Sharing, passwords, SMS sign-in, passkeys at launch (phase 4).
- Owner-funded shared credit pools on group trips (credits follow the acting user, except the
  `family` household pool).
- Email or calendar inbox parsing (auto-import of confirmations), loyalty program tracking, and
  visa application filing.
- Social feed, public trip discovery, user reviews of places, and user-generated public guides.
- White-label and API licensing (year 3 or later), partner guides and sponsored content (year 2
  or later), and any detailed advisor or print-on-demand behavior beyond the summaries in F-ADV
  and F-PRT.
- Languages other than English at launch, and right-to-left languages.
