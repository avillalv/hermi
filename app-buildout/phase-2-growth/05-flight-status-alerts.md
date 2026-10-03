# Pack 05: Flight status alerts (delay, gate and cancellation)

Part of [Phase 2: growth](README.md). Written 2026-09-30. The full specs have no flight status
feature (Phase 1 has fare price alerts and the booked-fare drop alert only,
[01 F-FLT-6](../reference-full-spec/01-product-spec.md), and the "Leave for the airport" local notification in
[05 section 6.29](../reference-full-spec/05-ui-ux-spec.md)), so the jobs and screens below are new. Phase 1 03 section 14
([Phase 1 03](../phase-1-launch/03-database-schema.md)) reserves the working names used here:
`flight_status_subscriptions`, `flight_status_events`, `chosen_flights.flight_numbers`,
`itinerary_items.flight_number`, the notification kinds `flight_delay` and `gate_change`, and the kill switch
`provider.flight_status`; this pack adds one more table, `tracked_flights`, for per-leg state. Provider facts were gathered from web search results on 2026-09-30 and
are all **reported, verify** until read on each vendor's own terms and pricing page after sign-up
(the vendor sites themselves could not be fetched from the research environment).

| Item | Value |
|---|---|
| Build order | 5 (months 9 to 10); the provider bake-off starts in month 7 |
| Flags | `flight_status` (default off, staged rollout); kill switch `provider.flight_status` (new) |
| Needs from Phase 1 | Chosen flights, booking import, push and email notifications, calendar feed, provider interface pattern and `provider_calls`, admin provider health |
| Soft link | Pack 04 (forwarded confirmations create tracked flights), pack 10 (delay data feeds the compensation prompt) |
| Tickets | P2-043 to P2-054 |
| Tier and products | All tiers with limits by tier (defaults below); no new products, no credits |

## 1. Goal and why now

**Goal.** Tell travelers, in plain facts and on time, when a flight on their trip is delayed, changes
gate or terminal, is cancelled or diverted, and show live status on the trip. The airline remains the
source of truth; Hermi states where the data came from and when it was checked, like every other
fact in the product.

**Why now.**

- Competitive reasons. TripIt users love real-time flight alerts (TripIt Pro, $49 a year, reported,
  verify; [business plan](../context/business-plan/01-business-plan.md)) and email forwarding (pack 04). Flight alerts are
  the main reason frequent travelers keep paying for TripIt, so a planner that wants TripIt switchers
  must match them on alerts. Wanderlog and Trippy are known for group planning rather than flight status (reported, verify), so
  alerts plus groups together is a position neither is known to hold.
- Phase 1 already collects the inputs: chosen flights and pasted bookings. Pack 04 adds flight numbers
  automatically.
- It is a retention feature that works during the trip, the moment when a planner is otherwise idle, and
  it gives the after-trip compensation prompt (pack 10) real data.
- It is cheap per user if polling is disciplined, and the paid tiers get the real-time layer.

## 2. User stories and acceptance criteria

| ID | Story | Acceptance |
|---|---|---|
| FLS-1 | As a traveler, I add my flight number and see its status. | "Add flight number" on a chosen flight, a pasted booking or an itinerary travel item looks the flight up (airline code and number, local departure date). The app shows "TP 1355 Lisbon to New York, 10:05, is this your flight?" before saving. A flight that cannot be found says so and keeps the plain item. |
| FLS-2 | As a traveler, I do not have to do it twice. | Flights confirmed from a pasted booking (Phase 1) or a forwarded email (pack 04) become tracked flights automatically when they have a flight number and date. A fare chosen from cached fares (which may lack a flight number) asks for it once. |
| FLS-3 | As a traveler, I get alerts that matter. | Alerts for: delay of at least my threshold (default 15 minutes; options 15, 30, 60) and again when it changes by 15 minutes or more; cancellation; diversion; gate change within 6 hours of departure; terminal change; optional landed and baggage belt. One push per change, at most 6 pushes per leg, each stating amount and since when. |
| FLS-4 | As a traveler, I see status at a glance. | The flight card and the Today view show a chip (On time, Delayed 45 min, Gate B12, Cancelled, Landed), the times ("now 10:50, was 10:05"), the source and check time ("Status from AeroDataBox, checked 4 minutes ago" or the chosen provider), and a timeline of changes. |
| FLS-5 | As a trip member, everyone who needs alerts gets them. | Every trip member is subscribed by default (owner and editors on, viewers opt in); each person can mute or change the threshold per flight. Quiet hours apply except for changes within 24 hours of departure ("Allow flight alerts during quiet hours", default on). |
| FLS-6 | As a traveler, my calendar stays right. | The live calendar subscription feed updates event times and adds gate and terminal to the description when status changes. |
| FLS-7 | As the business, cost is bounded. | Polling and provider spend follow the schedule below; a per leg spend cap (default $0.10) and a monthly provider budget setting degrade polling before they stop it; kill switch `provider.flight_status` stops calls and the UI shows "Live status is paused. Times shown are the schedule." |
| FLS-8 | As a traveler, I know what this is and is not. | Copy says "Check with your airline for the latest information". There is no rebooking, compensation or insurance advice in alerts; after a cancellation the card shows a plain "Open the airline's site" link and, later, the after-trip prompt (pack 10) handles compensation. No affiliate card appears on or near a disruption alert. |

Out of scope for this pack: iOS Live Activities and Dynamic Island, widgets, in-app rebooking, airport
wait times, seat maps, baggage tracking beyond the belt number, and flight status for people who are not
members of a trip.

## 3. Database additions

Migration `0021_flight_status`. New tables and two columns on Phase 1 tables. `iata_code`, `currency_code` and the trigger helpers come
from Phase 1 ([03 section 3](../reference-full-spec/03-database-schema.md)).

```sql
-- Flight numbers as the input: the Phase 1 import and the chosen fare may carry them, cached fares usually do not.
ALTER TABLE chosen_flights  ADD COLUMN flight_numbers text[] NOT NULL DEFAULT '{}';      -- for example {'TP1355'}
ALTER TABLE itinerary_items ADD COLUMN flight_number text;                               -- set for travel items created by import or email

CREATE TYPE flight_leg_status AS ENUM ('scheduled', 'active', 'landed', 'cancelled', 'diverted', 'unknown');
CREATE TYPE flight_event_kind AS ENUM (
  'delay', 'gate_change', 'terminal_change', 'baggage_belt', 'cancelled', 'diverted',
  'departed', 'landed', 'schedule_change', 'restored');

CREATE TABLE tracked_flights (
  id                      uuid PRIMARY KEY DEFAULT uuidv7(),
  trip_id                 uuid NOT NULL REFERENCES trips (id) ON DELETE CASCADE,
  source                  text NOT NULL,                              -- chosen_flight, import, email, manual
  chosen_flight_id        uuid REFERENCES chosen_flights (id) ON DELETE SET NULL,
  itinerary_item_id       uuid,                                       -- the travel item, when one exists
  airline_iata            char(2) NOT NULL,
  flight_number           text NOT NULL CHECK (flight_number ~ '^[0-9]{1,4}[A-Z]?$'),
  flight_date             date NOT NULL,                              -- local departure date
  origin                  iata_code NOT NULL,
  destination             iata_code NOT NULL,
  sched_dep_utc           timestamptz,
  sched_arr_utc           timestamptz,
  est_dep_utc             timestamptz,
  est_arr_utc             timestamptz,
  actual_dep_utc          timestamptz,
  actual_arr_utc          timestamptz,
  dep_terminal            text, dep_gate text,
  arr_terminal            text, arr_gate text, baggage_belt text,
  status                  flight_leg_status NOT NULL DEFAULT 'scheduled',
  dep_delay_min           integer,                                    -- null when unknown
  arr_delay_min           integer,
  provider                text,                                       -- aerodatabox, aeroapi, ...
  provider_flight_ref     text,
  provider_alert_ref      text,                                       -- provider push subscription, when used
  last_polled_at          timestamptz,
  next_poll_at            timestamptz,
  poll_count              integer NOT NULL DEFAULT 0,
  spend_micros            bigint NOT NULL DEFAULT 0,                  -- provider cost so far for this leg (cap in settings)
  tracking_enabled        boolean NOT NULL DEFAULT true,
  created_by              uuid REFERENCES users (id) ON DELETE SET NULL,
  version                 integer NOT NULL DEFAULT 1,
  created_at              timestamptz NOT NULL DEFAULT now(),
  updated_at              timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_tracked_flights_source CHECK (source IN ('chosen_flight', 'import', 'email', 'manual')),
  CONSTRAINT uq_tracked_flights_leg UNIQUE (trip_id, airline_iata, flight_number, flight_date),
  CONSTRAINT uq_tracked_flights_id_trip UNIQUE (id, trip_id)
);
CREATE INDEX ix_tracked_flights_due ON tracked_flights (next_poll_at) WHERE tracking_enabled AND status IN ('scheduled', 'active');
CREATE INDEX ix_tracked_flights_trip ON tracked_flights (trip_id, sched_dep_utc);
SELECT add_version_trigger('tracked_flights');
SELECT add_updated_at_trigger('tracked_flights');

CREATE TABLE flight_status_events (                                   -- append-only change log; the source of alerts and the timeline
  id                  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  tracked_flight_id   uuid NOT NULL,
  trip_id             uuid NOT NULL,
  kind                flight_event_kind NOT NULL,
  old_value           jsonb,
  new_value           jsonb,
  delay_min           integer,
  provider            text NOT NULL,
  observed_at         timestamptz NOT NULL,
  dedupe_key          text NOT NULL,                                   -- kind plus the new value, so a repeated observation does nothing
  created_at          timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY (tracked_flight_id, trip_id) REFERENCES tracked_flights (id, trip_id) ON DELETE CASCADE,
  CONSTRAINT uq_flight_status_events_dedupe UNIQUE (tracked_flight_id, dedupe_key)
);
CREATE INDEX ix_flight_status_events_flight ON flight_status_events (tracked_flight_id, id DESC);

CREATE TABLE flight_status_subscriptions (                             -- who is told, and how
  tracked_flight_id   uuid NOT NULL,
  trip_id             uuid NOT NULL,
  user_id             uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
  min_delay_min       smallint NOT NULL DEFAULT 15 CHECK (min_delay_min IN (15, 30, 60)),
  push                boolean NOT NULL DEFAULT true,
  email               boolean NOT NULL DEFAULT false,
  muted               boolean NOT NULL DEFAULT false,
  last_notified_delay_min integer,
  notify_count        smallint NOT NULL DEFAULT 0,                     -- cap of 6 pushes per leg
  created_at          timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tracked_flight_id, user_id),
  FOREIGN KEY (tracked_flight_id, trip_id) REFERENCES tracked_flights (id, trip_id) ON DELETE CASCADE
);

-- Tier limits (plans.limits keys, merged best-of per trip like every other limit).
-- flight_status_legs: legs tracked at once per trip; flight_status_realtime: 15 minute polling near departure, gate and baggage alerts.
UPDATE plans SET limits = limits || '{"flight_status_legs":2,"flight_status_realtime":false}'::jsonb WHERE code = 'free';
UPDATE plans SET limits = limits || '{"flight_status_legs":12,"flight_status_realtime":true}'::jsonb WHERE code IN ('plus', 'family');
UPDATE plans SET limits = limits || '{"flight_status_legs":20,"flight_status_realtime":true}'::jsonb WHERE code = 'pro';
UPDATE plans SET limits = limits || '{"flight_status_legs":8,"flight_status_realtime":true}'::jsonb WHERE code = 'trip_pass';
UPDATE plans SET limits = limits || '{"flight_status_legs":12,"flight_status_realtime":true}'::jsonb WHERE code = 'group_trip_pass';

INSERT INTO feature_flags (key, description, enabled, rollout_pct, rules, variants) VALUES
('flight_status', 'Flight status tracking and alerts', false, 100, '{}', '{}')
ON CONFLICT (key) DO NOTHING;
INSERT INTO feature_flags (key, kind, description, enabled, rollout_pct, rules, variants) VALUES
('setting_flight_status_monthly_usd', 'setting', 'Monthly flight status provider budget in dollars; 80 and 90 percent raise alerts, 100 percent degrades to the free-tier poll schedule', true, 100, '{"usd":60}', '{}'),
('setting_flight_status_leg_cap_usd', 'setting', 'Provider spend cap per tracked leg in dollars', true, 100, '{"usd":0.10}', '{}')
ON CONFLICT (key) DO NOTHING;
INSERT INTO kill_switches (key, description, auto_rule) VALUES
('provider.flight_status', 'Stop flight status provider calls; stored status stays visible with the schedule', '{"metric":"flight_status_month_pct_of_budget","gte":100}')
ON CONFLICT (key) DO NOTHING;

-- Swap the named check and keep every value other revisions allow (Phase 1 list, plus inbound_email from pack 04 and impact from pack 08).
ALTER TABLE webhook_events DROP CONSTRAINT ck_webhook_events_provider;
ALTER TABLE webhook_events ADD CONSTRAINT ck_webhook_events_provider
  CHECK (provider IN ('revenuecat', 'apple', 'stripe', 'travelpayouts', 'viator', 'stay22', 'inbound_email', 'impact', 'flight_status'));

```

Notification kinds (swap `ck_notifications_kind` for the current list plus these): `flight_delay`,
`gate_change` (the two names Phase 1 reserves), `flight_cancelled`, `flight_diverted`, `flight_landed`.
Dedupe keys follow the Phase 1 pattern: `flight:<tracked_flight_id>:<event dedupe_key>`.

Numbers in the tier limits and the budget settings are defaults to tune with measured cost per tracked
leg (ticket P2-043); they are `UPDATE`s in the admin console, not migrations. Row-level security: the
three tables follow the trip-child policies (members read; owner and editors write
`tracked_flights`); `flight_status_events` is written by the worker only; `flight_status_subscriptions`
is personal (`user_id = app_user_id()`). `provider_calls.provider` accepts the flight status provider
names. Retention: events and legs are kept with the trip; `poll` detail is in `provider_calls`
(partitioned, rolled up).

## 4. API additions

| Endpoint | Auth | Gate and cost | Request and response | Errors and side effects |
|---|---|---|---|---|
| `POST /trips/{trip_id}/flights/lookup` | editor | flag `flight_status`, 20 an hour per user | `{ airline_iata, flight_number, date }` to `FlightLookup` | One provider call (cached 15 minutes per key). Returns the found leg for confirmation; nothing is saved. `404 not_found` when the provider has no such flight; `503 feature_disabled` with the kill switch. |
| `POST /trips/{trip_id}/tracked-flights` | editor | `flight_status_legs` limit | `{ airline_iata, flight_number, date, chosen_flight_id?, itinerary_item_id? }` with `Idempotency-Key` to 201 `TrackedFlight` | Creates the leg, subscribes the members, schedules the first poll. `403 limit_reached`, reason `flight_status` over the tier limit. |
| `GET /trips/{trip_id}/tracked-flights` | viewer | none | none to `TrackedFlight[]` | With latest status and `checked_at`. `ETag`. |
| `GET /tracked-flights/{id}/events` | viewer | none | `?limit` to `FlightStatusEvent[]` | The timeline. |
| `PATCH /tracked-flights/{id}` | editor | versioned | `{ tracking_enabled? }` to `TrackedFlight` | Stop or resume tracking. |
| `DELETE /tracked-flights/{id}` | editor | none | 204 | Removes tracking, keeps the itinerary item. |
| `PUT /tracked-flights/{id}/subscription/me` | viewer | none | `{ min_delay_min?, push?, email?, muted? }` to `Subscription` | Personal alert settings. |
| `POST /webhooks/flight-status` | provider signature | none | provider payload to 200 | Verifies the signature in constant time, inserts `webhook_events` by provider event id, enqueues `apply_flight_status`. Unknown flights are acknowledged and ignored. |

```ts
type TrackedFlight = {
  id: Uuid; trip_id: Uuid; airline_iata: string; flight_number: string; flight_date: string
  origin: string; destination: string
  status: "scheduled" | "active" | "landed" | "cancelled" | "diverted" | "unknown"
  sched_dep: string | null; est_dep: string | null; actual_dep: string | null
  sched_arr: string | null; est_arr: string | null; actual_arr: string | null
  dep_terminal: string | null; dep_gate: string | null; arr_terminal: string | null; arr_gate: string | null; baggage_belt: string | null
  dep_delay_min: number | null; arr_delay_min: number | null
  source_label: string                       // "AeroDataBox" or the chosen provider's name, for the evidence line
  checked_at: string | null; tracking_enabled: boolean; realtime: boolean
}
type FlightStatusEvent = { id: number; kind: string; delay_min: number | null; old: unknown; new: unknown; observed_at: string }
type FlightLookup = { found: boolean; leg: Omit<TrackedFlight, "id" | "trip_id"> | null }
```

**Provider interface** (`apps/api/hermi/providers/flightstatus/`): `lookup(airline, number, date)`,
`subscribe(leg)` and `unsubscribe(leg)` where the vendor supports push alerts, `poll(leg)`, and
`parse_webhook(body)`; every call writes `provider_calls` (cost in micro-dollars, cached flag) and
honors the kill switch; the vendor is chosen by config and a second vendor can be added behind the same
interface (the same pattern as SerpApi behind a flag).

**Jobs (worker).**

| Job | Lane | Trigger | Schedule | Idempotency key | Retries |
|---|---|---|---|---|---|
| `poll_flight_status` | batch | scheduler | scans `next_poll_at <= now()` every 60 seconds (leader only); polls per the schedule below | `(tracked_flight_id, time_bucket)` | transient x5 |
| `apply_flight_status` | api | poll result or webhook | event | `(tracked_flight_id, dedupe_key)` on `flight_status_events` | transient x5 |
| `send_flight_alert` | notify | new `flight_status_events` row | event | `(user_id, event_id, channel)` | transient x5 |
| `auto_track_flights` | api | trip booking confirmed, email import confirmed | event | `(trip_id, airline, number, date)` | transient x3 |

**Polling schedule (defaults; `flight_status_realtime` decides the near-departure cadence).**

| Time to scheduled departure | Free (2 legs) | Paid and passes |
|---|---|---|
| more than 7 days | once a day (schedule change check) | once a day |
| 7 days to 48 hours | once a day | every 12 hours |
| 48 to 12 hours | every 6 hours | every 3 hours |
| 12 to 3 hours | every 2 hours | every hour |
| 3 hours to departure | every 30 minutes | every 15 minutes |
| departed to 45 minutes before arrival | no polling (webhook if available) | no polling (webhook if available) |
| 45 minutes before arrival to 30 minutes after | once at landing | every 10 minutes (landed, arrival gate, belt) |

When the provider offers push (webhook alerts), the vendor pushes changes and the poll becomes a safety
net every 6 hours. The per leg spend cap moves a leg to the Free cadence; the monthly budget at 100
percent moves all legs to the Free cadence; the kill switch stops everything. A leg stops polling 2
hours after landing or cancellation.

**Alert rules** (`apply_flight_status`):

- `delay`: notify when the departure delay first reaches the subscriber's threshold and again when it
  changes by 15 minutes or more from the last notified value; "restored" when it returns under the
  threshold after a notification.
- `cancelled` and `diverted`: always notify (all channels the user enabled).
- `gate_change` and `terminal_change`: notify within 6 hours of departure, realtime tiers; Free sees the
  change on the card without a push.
- `landed` and `baggage_belt`: off by default, opt in, realtime tiers.
- At most 6 pushes per leg per person (`notify_count`); quiet hours apply except within 24 hours of
  departure when the person allowed it.
- Push copy states the fact: "TP 1355 Lisbon to New York: delayed 45 minutes, now departs 10:50." No
  emoji, no exclamation marks, no sales. Tapping opens the flight card. Emails link to the in-app card,
  never to a partner.

## 5. UI screens and paywall triggers

1. **Flight card (Flights section and trip overview).** A status chip and the times beside the chosen or
   imported flight; "Add flight number" when missing; the evidence line "Status from <provider>, checked
   4 minutes ago"; an "Alerts" row showing the threshold; "Open the airline's site" link (non affiliate).
2. **Flight detail sheet.** Timeline of changes (scheduled, delayed, gate, departed, landed) with times
   and sources; alert settings (threshold 15, 30, 60; push, email; mute); "Stop tracking".
3. **Add flight number sheet.** Airline code or name, number, date (defaults to the trip's date);
   "Is this your flight?" confirmation card with route and times.
4. **Today view (trip in progress).** The next flight is first, with gate, terminal and boarding
   countdown facts; offline shows the last known status with its age ("Last checked 2 hours ago").
5. **Notification settings.** New rows: "Flight delays and cancellations", "Gate and terminal changes",
   "Landed and baggage belt"; quiet hours override "Allow flight alerts during quiet hours".
6. **Activity.** Items such as "TP 1355 is delayed 45 minutes".

States. Loading: skeleton chip. Empty (no flight number): "Get alerts for this flight", "Add the flight
number and we will tell you if it changes.", [Add flight number]. Error: "We could not check this
flight. The schedule is shown." Offline: last known status with age. Provider paused: "Live status is
paused. Times shown are the schedule." No permission: viewers see status and set their own alerts.
Limit: "You are tracking 2 flights on this trip. Live alerts for more flights are in Plus or a Trip Pass."
(a card, not a modal).

Paywall triggers: one soft, client-initiated moment `flight_status_limit` (reason added to
`GET /paywall/offer`): a Free owner adds a third leg or opens gate and baggage alerts. It follows the
paywall rules (one per session, "Not now" always visible, dismiss mutes 7 days, no countdowns, no
paywall before first value, none beside an affiliate card, none during an active disruption so a person
in trouble is never upsold). Leading offer: Trip Pass (more legs and realtime alerts for this trip),
then annual Plus. Free path: "Keep 2 flights".

## 6. Monetization and App Store products

No new App Store products and no credits. Flight status is a service cost, not an AI cost, so it sits
outside the AI credit ceilings and is limited by legs and cadence per tier (defaults in section 3):

| Plan | Legs tracked per trip | Near-departure cadence | Gate, terminal, landed and belt alerts |
|---|---|---|---|
| Free | 2 | 30 minutes | card only, no push |
| Plus, Family | 12 | 15 minutes | yes |
| Pro | 20 | 15 minutes | yes |
| Trip Pass | 8 | 15 minutes | yes |
| Group Trip Pass | 12 | 15 minutes | yes |

The competitive win plan ([win-plan.md](../context/competitive-analysis/win-plan.md), F19) suggests "free for chosen
flights on Plus and Trip Pass; free tier gets the first alert only (decide after cost is known)". This pack
starts more generously for Free (2 legs, delay and cancellation only, slower cadence) because the alerts are
the trust moment for TripIt switchers; if the bake-off shows a leg costs more than about $0.10, fall back to
the win plan's version by changing `flight_status_legs` for Free to 1 and removing push for delays under 60
minutes. Free gets delay and cancellation alerts on purpose: they are the feature TripIt users love and the
trust moment that makes Hermi the place they keep trips. The upgrade reason is coverage (more legs,
faster cadence, gate and belt), not the basic safety alert. Revisit after 60 days of measured cost.

### Candidate providers (reported, verify)

Figures come from search result summaries dated 2026-09-30; none could be confirmed on the vendors' own
pages. Every number is **reported, verify** and ticket P2-043 replaces this table with measured data
and the vendors' actual terms.

| Provider | What it offers (reported) | Reported price | Reported fit and caveats |
|---|---|---|---|
| FlightAware AeroAPI | Flight status, tracking, alerts, historical and, on higher tiers, Foresight and Aireon data | Personal: free, up to $5 of queries a month, for personal and academic use, about 10 result sets a minute. Standard: $100 a month minimum, includes historical data, alerting and B2C commercial use, about 5 result sets a second. Premium: $1,000 a month minimum, B2B use, advanced data, about 100 result sets a second, phone support and a 99.5 percent uptime guarantee. Per query fees about $0.001 to $0.05 per result set depending on endpoint | Strong data and alerts. The Personal tier is not allowed for a commercial consumer app, so the realistic entry is Standard at a $100 fixed monthly minimum. Verify how alert (push) subscriptions are billed and what attribution is required. |
| AeroDataBox | Flight status, schedules, airport data, statistics; a separate Flight Alert API that calls your webhook when a flight changes | Via RapidAPI: a free plan with about 600 units a month, Pro about $5.35 a month for 6,000 units, Mega about $160 a month for 600,000 units. Via API.Market: Pro about $5, Ultra about $30, Mega about $150 a month, with a 7 day free trial. Webhook subscription management reported as free tier; refilling webhook credit uses quota | Cheapest by far and webhook friendly, which cuts polling. Verify commercial use rights, data accuracy and gate coverage, the unit cost of each call tier, and the terms for redistributing status to end users. A strong first choice to bake off. |
| OAG Flight Info API | Schedules and real-time flight status for travel technology | Via RapidAPI reported about $249 a month for 500 calls up to about $449 a month for 1,000 calls; direct subscriptions on request and aimed at larger enterprises; a limited free tier reported | Premium schedule data, expensive per call at small scale. Not a fit for launch volume; revisit at scale or for the schedule-change feed. |
| Cirium (FlightStats Flex APIs) | Flight status, delays, alerts; industry standard in airlines and OTAs | Free 30 day evaluation plan, up to 20,000 requests; Commercial plan is pay-as-you-go with volume pricing; Contract plan needed for premium APIs. No public self-serve prices; quote based, reported into four figures a month at high volume | Best coverage and event quality, priced for scale. Use the free evaluation in the bake-off for accuracy comparison; adopt only if volume or accuracy demands it. |

Recommendation (to be confirmed by the bake-off): start with AeroDataBox behind the provider interface
(low fixed cost, webhook alerts), keep FlightAware AeroAPI Standard as the challenger and fallback
(reported $100 monthly minimum is acceptable once 1,000 legs a month are tracked), treat Cirium and OAG
as scale options. The default budget of $60 a month is an assumption (about 1,000 legs a month at about $0.06 a leg)
until the bake-off replaces it with a measured cost per leg.

Cost model to fill in during the bake-off: queries per leg = sum of polls in the schedule (about 18 on
the Free cadence and about 40 on the realtime cadence for a leg tracked from 48 hours out) minus polls
replaced by webhooks; cost per leg = queries per leg x unit price; monthly cost = legs per month x cost
per leg plus fixed plan minimum. The per leg cap and the monthly budget settings enforce the result.

Sources (search results, reported, verify):
[FlightAware AeroAPI](https://www.flightaware.com/commercial/aeroapi/),
[AeroAPI pricing summary, apis.io](https://apis.io/plans/flightaware/flightaware-plans-pricing/),
[AeroDataBox pricing on RapidAPI](https://rapidapi.com/aedbx-aedbx/api/aerodatabox/pricing),
[AeroDataBox pricing](https://aerodatabox.com/pricing),
[AeroDataBox on API.Market](https://api.market/store/aedbx/aerodatabox),
[OAG developer portal](https://developers.oag.com/),
[OAG Flight Info API listing](https://marketplace.microsoft.com/en-us/product/saas/oag1597930402040.fiapi?tab=overview),
[Cirium FlightStats evaluation account](https://developer.cirium.com/apis/flightstats-apis/get-evaluation-account),
[Cirium query pricing help](https://helpdesk.cirium.com/hc/en-us/articles/217614968-How-does-a-query-count-toward-pricing-),
[Best flight data APIs in 2026, Geekflare](https://geekflare.com/guides/flight-data-api/).

## 7. Admin additions

- **Provider health (08 section 6.13).** New panel "Flight status": calls today and this month, cost
  against the monthly budget and per leg cap, cache hit rate, webhook lag, error and empty-result rate,
  legs tracked and polled, alerts sent, and a provider accuracy sample (alerts later contradicted by an
  observation).
- **Kill switches (08 section 6.5).** `provider.flight_status` with its auto rule at 100 percent of the
  monthly budget; per tier degrade is automatic (Free cadence), not a switch.
- **Feature flags.** `flight_status`, plus the two settings flags, editable with a reason.
- **Users and trips.** Trip detail lists tracked legs, status and event log for support (status data,
  no message content); action "stop tracking" (audited).
- **Alert rules (08 section 10).** Monthly flight status spend at 80 percent (notify) and 90 percent
  (page); webhook backlog older than 10 minutes (page); provider empty-result rate above 20 percent
  (notify); alerts sent per minute above 5 times the trailing p95 (possible duplicate storm, notify).
- **Support macros.** "Why did I not get an alert", "My flight status is wrong", "Stop flight alerts".

## 8. AI additions

None. Status, alert text and thresholds are deterministic. No flight status data, trip or traveler name
is sent to an AI service. A future optional idea (a plain-language summary of a disruption) would be an
`explain` action with its own consent and is not in this pack. Affiliate and partner data stay out of
alerts.

## 9. Analytics events

No PII; airline codes and airports are not sent (route is a country pair bucket at most).

| Event | Properties | When fired |
|---|---|---|
| `flight_number_added` | `source` (`manual`, `chosen_flight`, `import`, `email`), `found` (bool) | Lookup then confirm |
| `flight_tracking_started` | `tier_legs_bucket`, `days_to_departure_bucket` | Leg created |
| `flight_status_viewed` | `status`, `age_minutes_bucket` | Flight card or sheet opened |
| `flight_alert_delivered` | `kind` (`flight_event_kind`), `channel` (`push`, `email`, `in_app`) | Alert sent (server side) |
| `flight_alert_opened` | `kind`, `channel` | Opened from an alert |
| `flight_alert_setting_changed` | `key` (`threshold`, `push`, `email`, `mute`) | Personal settings change |
| `flight_status_limit_shown` | none | Limit card shown |
| `flight_status_provider_degraded` | `reason` (`leg_cap`, `budget`, `kill_switch`, `provider_error`) | Server side |

Funnel: `flight_number_added` to `flight_alert_delivered` to `flight_alert_opened`; retention guard:
D30 of users with at least one tracked leg versus without.

## 10. Tests

- Provider contract tests with recorded fixtures per vendor (found, not found, cancelled, diverted, gate
  and terminal changes, time zone edges, codeshare numbers, overnight flights, date line).
- Polling schedule table tests with a fake clock for both cadences, leg cap and budget degradation,
  kill switch, stop 2 hours after landing.
- Alert rules: threshold and re-notify at 15 minute changes, dedupe by `dedupe_key`, cap of 6 per leg,
  quiet hours and the 24 hour override, viewer opt in, muted members, cancelled always notifies.
- Webhook: signature, replay, unknown flight, out-of-order events (apply by `observed_at`).
- Auto tracking from import and email confirms; duplicate legs collapse on the unique key.
- Calendar feed updates times and description without breaking Phase 1 feed tests.
- Offline: last known status with age; local notification behavior unchanged.
- Entitlements: leg limits per tier and pass, best-of merge, Free third leg shows the limit card.
- Privacy and isolation: tenant tests for the three tables; no PII in analytics.
- Chaos: provider 500s and timeouts (breaker opens, UI shows schedule, no alert spam on recovery).
- Bake-off script: replay 30 real upcoming flights against two vendors and compare delay, gate and
  cancellation accuracy and cost per leg.

## 11. Tickets

#### P2-043 Provider bake-off and interface [M, starts month 7, needs Phase 1 provider pattern]
- Description: create accounts and read the real terms for AeroDataBox, FlightAware AeroAPI Standard
  and Cirium's evaluation; implement the `flightstatus` provider interface and two adapters; run the
  bake-off script on 30 flights over 2 weeks; record accuracy, latency to alert, cost per leg,
  webhook support, commercial use, attribution and redistribution terms.
- Accept: decision memo in `docs/`; the price table in section 6 replaced with measured numbers and the
  vendors' own terms; budget and leg cap settings updated.
- Touches: `apps/api/hermi/providers/flightstatus/`, `docs/`.

#### P2-044 Schema, RLS, settings and flags [M, needs P2-043]
- Description: migration `0021_flight_status`, policies, limits, flags, kill switch, settings.
- Accept: empty to head and previous to head pass; cross-tenant suite covers the tables.

#### P2-045 Lookup and tracked flights API [M, needs P2-044]
- Description: lookup, create, list, patch, delete, personal subscription, tier limit, entitlement
  errors, `ETag`.
- Accept: leg limits by tier; lookup cached 15 minutes; nothing saved before confirmation.

#### P2-046 Auto tracking from chosen flights, imports and emails [M, needs P2-045, pack 04 optional]
- Description: `auto_track_flights` on booking confirm and email confirm; "Add flight number" prompt on
  chosen cached fares.
- Accept: a pasted booking with a flight number starts tracking; duplicates collapse.

#### P2-047 Poll scheduler and cost controls [L, needs P2-045]
- Description: `poll_flight_status` with the schedule table, per leg cap, monthly budget degrade,
  kill switch, provider push subscribe and unsubscribe, `provider_calls` logging.
- Accept: schedule tests pass; spend never exceeds the cap in simulation.

#### P2-048 Webhook receiver and event detection [M, needs P2-045]
- Description: `POST /webhooks/flight-status`, `apply_flight_status`, `flight_status_events` with dedupe
  and ordering, status transitions.
- Accept: webhook and poll paths produce the same events; out-of-order handled.

#### P2-049 Alert delivery and preferences [M, needs P2-048, Phase 1 notifications]
- Description: `send_flight_alert`, copy, thresholds, caps, quiet hours override, email template,
  notification settings rows, Activity items.
- Accept: alert rules in section 4 pass; copy follows the microcopy rules.

#### P2-050 Flight status UI [L, needs P2-045]
- Description: chips, detail sheet with timeline, add flight number sheet, Today view integration,
  states, offline age.
- Accept: axe clean; status read by VoiceOver as text; no affiliate UI near disruptions.
- Touches: `apps/web/src/routes/flights/`, `routes/today/`.

#### P2-051 Calendar feed and presentation updates [S, needs P2-048]
- Description: update ICS event times and description on change; present mode shows the schedule only.
- Accept: feed tests pass; no live status on public share pages.

#### P2-052 Limits and soft paywall [S, needs P2-045, Phase 1 paywall engine]
- Description: `flight_status_limit` reason, limit card, Trip Pass lead, suppression during active
  disruptions.
- Accept: decision tests; free path present.

#### P2-053 Admin panel, alerts and macros [S, needs P2-047]
- Description: provider health panel, cost against budget, alert rules, support tools.
- Accept: alerts fire in a drill; every admin action audited.

#### P2-054 Attribution, privacy and launch checks [S, needs P2-050]
- Description: provider attribution text where required, privacy policy note (flight numbers are sent to
  the provider, no names), terms review for redistribution, staged rollout plan (staff, 10 percent,
  100 percent) with the cost watch.
- Accept: legal checklist complete; first 1,000 legs within budget.

## 12. Risks

| Risk | Mitigation |
|---|---|
| Provider cost grows faster than revenue | Per leg cap, monthly budget, cadence by tier, webhooks, kill switch, measured cost before broad rollout |
| Wrong or late alerts erode trust | Source and check time on every status, airline-is-source-of-truth copy, bake-off accuracy gate, dedupe and re-notify rules |
| Licensing limits the use of status data in a consumer app | Read terms during the bake-off; AeroAPI Personal is not for this use; keep a second adapter ready |
| Alert fatigue | Thresholds, cap of 6 pushes per leg, mute, quiet hours |
| Disruption upsell looks predatory | No paywall or affiliate card during an active disruption |
| Free-tier abuse (many legs across trips) | Legs limited per trip and by active trips; cap on Free cadence; budget degrade |
| Vendor concentration | Provider interface with two adapters; cached stored status stays visible on outage |
