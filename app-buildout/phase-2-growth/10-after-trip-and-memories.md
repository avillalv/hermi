# Pack 10: After the trip, memories and "Year in travel"

Part of [Phase 2: growth](README.md). Written 2026-09-30. Source definitions:
[01 section 3.11 and F-AFT-1 and F-AFT-2](../reference-full-spec/01-product-spec.md), [01 F-AFF-5](../reference-full-spec/01-product-spec.md),
the post-trip compensation section of [08 affiliate revenue](../context/business-plan/08-affiliate-revenue.md)
(sections 3.12 and 6). The full specs define the delay prompt and the wrap-up card only; memories and the
"Year in travel" card are new in this pack and follow the same conventions.

| Item | Value |
|---|---|
| Build order | 10 (months 10 to 12): the prompt and wrap-up first, memories next, the Year in travel card in time for December |
| Flags | `trip_memories` (default off, staged), `year_in_travel` (off until November), kill switch `memories.uploads` (new) |
| Needs from Phase 1 | Trips and chosen flights, share links and redaction, checklist and after-trip surface, R2 uploads by signed URL, push and email, archive, affiliate redirect and disclosure, export and deletion |
| Needs from other packs | Pack 05 (delay data, optional but recommended), pack 08 (AirHelp), pack 02 (settlement reminders), pack 04 (forwarded flights) |
| Tickets | P2-095 to P2-104 |
| Tier and products | All tiers. No new products, no credits. Photo limits by tier (defaults) |

## 1. Goal and why now

**Goal.** Close the loop after a trip. The day after the last trip date, help people who had a delayed or
cancelled flight find out what they can claim (a labeled partner link, official information first);
ask how the trip was; turn the finished trip into a keepsake (memories: highlights, photos, a recap);
and at year end offer a shareable "Year in travel" card.

**Why now.**

- The after-trip moment is where Phase 1 goes quiet: once a trip is done the app has no reason to be
  opened until the next one. Memories and the year card give people a reason to come back and a reason to
  show Hermi to friends, which feeds the invite loop without any ad spend.
- The compensation prompt is the most natural post-trip affiliate surface (Compensair pays a fixed amount
  per confirmed application, AirHelp 15 to 20 percent of its fee on an approved claim; reported, verify)
  and it only exists once flight status data (pack 05) and the AirHelp program (pack 08) are available.
- Competitive reasons. TripIt users rely on flight alerts and then on the trip record afterwards; Wanderlog
  and Trippy lean on shareable trip pages and travel stats as part of their social and retention appeal
  (reported, verify). A year-in-review card is the cheapest, most shareable asset a planner can ship, and a
  December release captures the annual sharing moment ("Wrapped" style cards are a proven format).
- Memories keep trips open for a little longer, which matters for retention: people who only visit the
  app before trips churn on the off months, and the model notes that usage concentrates in 2 to 4 active
  months a year.

## 2. User stories and acceptance criteria

### F-AFT-1 Delay prompt (verbatim from the full product spec)

- Acceptance: the day after the last trip date, if a flight was chosen: "Was your flight delayed
  or cancelled?" with "No" and "Yes, check what I can claim"; only "Yes" shows a partner link
  with the commission sentence and a note that eligibility depends on route and rules and no
  result is promised; never a push; not shown without a chosen flight.

### F-AFT-2 Wrap-up (verbatim from the full product spec; Phase 1 builds the card and the archive offer)

- Acceptance: "How was the trip?" card with a 1 to 5 rating and a note, no affiliate button; 14
  days after the end the trip is offered for archive; settlement reminders for unsettled
  expenses once.

(Journey [3.11](../reference-full-spec/01-product-spec.md): the day after the last trip date the delay prompt; a "How was the
trip?" card and archive after 14 days while expenses settle; export, archive or start the next trip from a
past one.) [Phase 1 01 section 4.17](../phase-1-launch/01-product-spec.md) keeps F-AFT-2 without the settlement
reminder and defers the delay prompt, memories and the Year in travel card to this pack. Phase 1 has no table
for the rating, so this pack adds `trip_reviews` to store it (if Phase 1 stored it elsewhere, map to that
instead) and adds the once-only settle-up reminder.

### Stories added by this pack

| ID | Story | Acceptance |
|---|---|---|
| AFT-1 | As a traveler, the prompt uses real data when we have it. | If a tracked leg (pack 05) ended with a cancellation or an arrival delay of at least 180 minutes (configurable `delay_hint_minutes`, default 180, reported as the common threshold, verify), the prompt says "Your flight to New York looks about 3 hours late (status from AeroDataBox, checked 2 Oct)." before the question; otherwise the plain question is shown. No claim of eligibility is ever made. |
| AFT-2 | As a traveler, official information comes first. | "Yes, check what I can claim" opens a sheet with official sources first (the European Commission and UK Civil Aviation Authority passenger rights pages and the US Department of Transportation air consumer page, maintained in a content config and covered by the link checker), the plain note that you can also ask the airline directly for free, and then one labeled partner option with the sentence "We earn a commission if you book here." (Compensair now, AirHelp when active, chosen by test cell, never both on one button). |
| AFT-3 | As a traveler, I am not pestered. | Shown once per trip per person, never as a push (an in-app card on Trips home and the trip Overview, optional email only if the person opted into trip emails), dismissible, and not shown without a chosen or tracked flight. No paywall and no affiliate card appears beside the wrap-up card. |
| AFT-4 | As a traveler, I rate the trip privately. | The 1 to 5 rating and note are stored per person, visible only to that person (and the owner sees an aggregate average only when at least 3 members rated); never used for ranking, marketing or AI. |
| AFT-5 | As a trip owner, archiving stays easy. | Unchanged from Phase 1: fourteen days after the end date the trip is offered for archive once; archived trips stay readable and exportable; "Start a new trip from this one" duplicates it. This pack only records the answer in `trip_after_prompts`. |
| AFT-6 | As a member, I get one settle-up reminder. | If expenses are unsettled at the wrap-up, one reminder per person (notify lane, `send_group_settle_reminders`), opt-in respected. |
| MEM-1 | As a member, I add photos and highlights to a finished trip. | A Memories tab appears when the trip has ended. Members add up to the tier limit of photos (Free 20, paid and passes 100, Pro 200; defaults, `plans.limits.memory_photos_per_trip`), captions up to 200 characters and a star on highlights. Uploads go to R2 by signed URL; the server resizes, strips all EXIF data including GPS, keeps only the capture date, and creates thumbnails. |
| MEM-2 | As a member, I see a recap generated from the trip. | A recap card shows days, nights, cities, countries, flights (from chosen and tracked flights), the route on a map, the trip rating average (if shown), and the top highlights. It is computed from data already in the trip; no AI is used. |
| MEM-3 | As an owner, I can share memories as a read-only page. | A memory share link (a share link of kind `memories`, expiry 90 days default) shows highlights, captions, the route map and the recap, with redaction flags on by default (traveler names, prices, notes and exact lodging addresses hidden), `noindex`, revocable, with the "Made with Hermi" line on Free. Photos are served by short-lived signed URLs; no face recognition; photos are never public by default. |
| MEM-4 | As a person, my photos are mine. | The uploader can delete their photos any time; deleting a trip deletes its photos after the 30 day trash window; account deletion removes the user's photos; export includes photos and captions. Children: photos are user content entered by adults; Hermi does not analyze faces, does not use photos for any AI feature and does not collect children's data as data of their own (age gate and travelers-as-names rules unchanged). |
| YIT-1 | As a traveler, I can see my year in travel. | From 1 December to 31 January the Trips home shows a "Your 2026 in travel" card for anyone with at least one finished trip that year. The summary shows trips, countries, cities, nights away, about how far you flew (great-circle distance between the airports of chosen and tracked flights, labeled "about"), your top destination, your longest trip and new countries. |
| YIT-2 | As a traveler, I can share a card, safely. | A generated image (1080 by 1920 story and 1080 by 1080 square, three covers: sky, night and paper) with no names, no photos by default, no dates and no partner links; a small "Made with Hermi" line and the hermi.world address. Shared through the system share sheet or saved as an image; the person can hide countries or cities before sharing. |
| YIT-3 | As a person, I choose whether to be told. | The card is an in-app card; an email "Your year in travel is ready" goes only to people who opted into marketing email (opt-in, one click unsubscribe); never a push (Apple guideline 4.10). Turn-off in Settings, Notifications. |
| YIT-4 | As the business, the card stays honest. | Stats count only trips where the user is a member and that have ended in the year; deleted and trashed trips are excluded; numbers come from stored data only; wrong-looking numbers can be corrected by editing trips, then "Refresh". |

## 3. Database additions

Migration `0026_after_trip`. New tables; conventions as in [03 section 2](../reference-full-spec/03-database-schema.md).

```sql
-- Which after-trip prompts were shown or answered, once per trip and person.
CREATE TABLE trip_after_prompts (
  trip_id       uuid NOT NULL REFERENCES trips (id) ON DELETE CASCADE,
  user_id       uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
  kind          text NOT NULL,                                   -- delay, wrapup, archive, settle
  shown_at      timestamptz NOT NULL DEFAULT now(),
  answer        text,                                            -- delay: yes or no; archive: archived or later
  answered_at   timestamptz,
  dismissed_at  timestamptz,
  PRIMARY KEY (trip_id, user_id, kind),
  CONSTRAINT ck_trip_after_prompts_kind CHECK (kind IN ('delay', 'wrapup', 'archive', 'settle'))
);

CREATE TABLE trip_reviews (                                        -- private rating and note, one per person per trip
  trip_id      uuid NOT NULL REFERENCES trips (id) ON DELETE CASCADE,
  user_id      uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
  rating       smallint NOT NULL CHECK (rating BETWEEN 1 AND 5),
  note         text NOT NULL DEFAULT '' CHECK (char_length(note) <= 1000),
  created_at   timestamptz NOT NULL DEFAULT now(),
  updated_at   timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (trip_id, user_id)
);
SELECT add_updated_at_trigger('trip_reviews');

CREATE TABLE trip_memories (                                        -- the memory store: photos now, other kinds later (the photo store that Phase 3 printed books can map to)
  id              uuid PRIMARY KEY DEFAULT uuidv7(),
  kind            text NOT NULL DEFAULT 'photo' CHECK (kind IN ('photo')),
  trip_id         uuid NOT NULL REFERENCES trips (id) ON DELETE CASCADE,
  uploader_id     uuid REFERENCES users (id) ON DELETE SET NULL,       -- null after account deletion, photo removed by the deletion job
  object_key      text NOT NULL,                                       -- R2 key of the processed image (EXIF stripped)
  thumb_key       text NOT NULL,
  width           integer NOT NULL,
  height          integer NOT NULL,
  bytes           integer NOT NULL,
  taken_on        date,                                                -- from EXIF date only; the rest of the metadata is discarded
  caption         text NOT NULL DEFAULT '' CHECK (char_length(caption) <= 200),
  is_highlight    boolean NOT NULL DEFAULT false,
  itinerary_item_id uuid,                                              -- optional link to a place in the plan
  sort_order      double precision NOT NULL DEFAULT 0,
  status          text NOT NULL DEFAULT 'processing',                  -- processing, ready, failed, removed
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_trip_memories_status CHECK (status IN ('processing', 'ready', 'failed', 'removed')),
  CONSTRAINT uq_trip_memories_id_trip UNIQUE (id, trip_id)
);
CREATE INDEX ix_trip_memories_trip ON trip_memories (trip_id, sort_order) WHERE status = 'ready';
CREATE INDEX ix_trip_memories_uploader ON trip_memories (uploader_id) WHERE uploader_id IS NOT NULL;
SELECT add_updated_at_trigger('trip_memories');

-- A memory share is a share link of a different kind (03 section 5.3): same token, expiry and redaction flags.
ALTER TABLE trip_share_links ADD COLUMN IF NOT EXISTS kind text NOT NULL DEFAULT 'plan';
ALTER TABLE trip_share_links ADD CONSTRAINT ck_trip_share_links_kind CHECK (kind IN ('plan', 'memories'));

CREATE TABLE share_cards (                                         -- generated share cards; Phase 2 has one kind, year_in_travel (working name from Phase 1 03 section 14)
  id             uuid PRIMARY KEY DEFAULT uuidv7(),
  user_id        uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
  kind           text NOT NULL DEFAULT 'year_in_travel',
  year           smallint NOT NULL CHECK (year BETWEEN 2026 AND 2100),
  stats          jsonb NOT NULL,                                      -- trips, countries[], cities[], nights, km_flown, top_destination, longest_trip_nights, new_countries[]
  theme          text NOT NULL DEFAULT 'sky',                         -- sky, night, paper
  hidden         text[] NOT NULL DEFAULT '{}',                        -- fields the person chose to hide on the card (countries, cities)
  image_key      text,                                                -- R2 key of the last rendered card (private)
  computed_at    timestamptz NOT NULL DEFAULT now(),
  shared_count   integer NOT NULL DEFAULT 0,
  CONSTRAINT uq_share_cards_user_kind_year UNIQUE (user_id, kind, year),
  CONSTRAINT ck_share_cards_kind CHECK (kind IN ('year_in_travel')),
  CONSTRAINT ck_share_cards_theme CHECK (theme IN ('sky', 'night', 'paper'))
);

-- Tier limits (plans.limits), defaults tuned with measured storage cost.
UPDATE plans SET limits = limits || '{"memory_photos_per_trip":20}'::jsonb  WHERE code = 'free';
UPDATE plans SET limits = limits || '{"memory_photos_per_trip":100}'::jsonb WHERE code IN ('plus', 'family', 'trip_pass', 'group_trip_pass');
UPDATE plans SET limits = limits || '{"memory_photos_per_trip":200}'::jsonb WHERE code = 'pro';

-- Phase 1 03 section 14 names trips.completed_at: set by build_after_trip_prompts the day after the last trip date (null while the trip is planned or running).
ALTER TABLE trips ADD COLUMN completed_at timestamptz;

-- The Travelpayouts compensation program is used only by this pack, so Phase 1 does not seed it (03 section 11.4 row).
INSERT INTO affiliate_programs (code, network, name, category, status, hosts, cookie_days, subid_param, campaign_param, api_credentials_ref, extra_disclosure_text) VALUES
('travelpayouts_compensair', 'travelpayouts', 'Compensair', 'compensation', 'active', '{compensair.com,tp.media}', 30, 'sub_id', NULL, 'TRAVELPAYOUTS_TOKEN', NULL)
ON CONFLICT (code) DO NOTHING;
INSERT INTO kill_switches (key, description)
SELECT 'affiliate.' || code, 'Turn ' || name || ' links off (plain links only)' FROM affiliate_programs WHERE code = 'travelpayouts_compensair'
ON CONFLICT (key) DO NOTHING;
-- AirHelp (code airhelp) is seeded by pack 08. A link template for each is added when the network's link format is confirmed.

-- Notification kinds (swap ck_notifications_kind for the current list plus these): compensation_prompt (the in-app card and the opt-in email), year_in_travel_ready (opt-in email only, never push).

-- Compensation delay hint (used by the prompt; see section 2, AFT-1).
INSERT INTO feature_flags (key, kind, description, enabled, rollout_pct, rules, variants) VALUES
('setting_delay_hint_minutes', 'setting', 'Arrival delay in minutes at which the after-trip prompt mentions the delay', true, 100, '{"minutes":180}', '{}')
ON CONFLICT (key) DO NOTHING;
INSERT INTO feature_flags (key, description, enabled, rollout_pct, rules, variants) VALUES
('trip_memories', 'Memories tab, photos and memory share pages', false, 100, '{}', '{}'),
('year_in_travel', 'Year in travel card', false, 100, '{}', '{}')
ON CONFLICT (key) DO NOTHING;
INSERT INTO kill_switches (key, description) VALUES
('memories.uploads', 'Stop new photo uploads; existing photos stay visible')
ON CONFLICT (key) DO NOTHING;
```

Row-level security: `trip_after_prompts` and `trip_reviews` are personal (`user_id = app_user_id()`);
`trip_memories` follow the trip-child policies (members read; owner and editors write; a member may
delete their own photos), and images are never served directly: the API returns short-lived signed R2
URLs only to members (or through a valid memory share token); `share_cards` is personal. Retention:
photos live with the trip (purged 30 days after the trip is deleted); the account deletion job removes the
user's photos, reviews, prompts and year rows and the rendered card objects.

Year in travel statistics (computed by the worker, `modules/memories/year_stats.py`):

```sql
-- Trips that count: the user is a member, the trip ended in the year, not deleted.
WITH my_trips AS (
  SELECT t.* FROM trips t JOIN trip_members m ON m.trip_id = t.id
   WHERE m.user_id = :user_id AND t.deleted_at IS NULL
     AND t.end_date IS NOT NULL AND t.end_date < current_date
     AND extract(year FROM t.end_date) = :year
), legs AS (
  SELECT o.lat AS lat1, o.lon AS lon1, d.lat AS lat2, d.lon AS lon2
    FROM chosen_flights c JOIN my_trips t ON t.id = c.trip_id
    JOIN airports o ON o.iata = c.origin JOIN airports d ON d.iata = c.destination
)
SELECT (SELECT count(*) FROM my_trips)                                              AS trips,
       (SELECT coalesce(sum(end_date - start_date + 1), 0) FROM my_trips)           AS days_away,
       (SELECT round(sum(6371 * 2 * asin(sqrt(
                 power(sin(radians(lat2 - lat1) / 2), 2) +
                 cos(radians(lat1)) * cos(radians(lat2)) * power(sin(radians(lon2 - lon1) / 2), 2)))))
          FROM legs)                                                                AS km_flown_about;
```

Countries and cities come from `trip_destinations` (`country_code`, `name`) of the counted trips;
"new countries" are those not present in any counted trip of earlier years; the round-trip distance counts
each chosen route once per leg (outbound and return when a return date exists). Tracked legs (pack 05) may
refine the list when a leg was changed; the figure is always labeled "about".

## 4. API additions

| Endpoint | Auth | Gate and cost | Request and response | Errors and side effects |
|---|---|---|---|---|
| `GET /trips/{trip_id}/after-trip` | member | none | none to `AfterTrip` | The prompts due for the caller (delay, wrapup, archive, settle) with the delay hint data; empty unless the trip ended. |
| `POST /trips/{trip_id}/after-trip/delay` | member | none | `{ answer: "yes" \| "no" }` to `DelaySheet \| null` | Records the answer once; "yes" returns the official sources and at most one partner offer through the existing `/outbound` contract (`entity_type: "after_trip"`, `surface: "after-trip"`). |
| `PUT /trips/{trip_id}/review/me` | member | none | `{ rating: 1..5, note?: string }` to 204 | Upsert. `GET` returns the caller's own review only. |
| `POST /trips/{trip_id}/after-trip/archive` | owner | none | `{ archive: boolean }` to `Trip` | Offers archive once; `later` dismisses. |
| `GET /trips/{trip_id}/memories` | member | flag `trip_memories` | none to `Memories` | Recap, highlights, photos (signed URLs, 15 minutes). |
| `POST /trips/{trip_id}/memories/photos` | member | flag, `memory_photos_per_trip`, 60 an hour | `{ content_type, bytes }` to 201 `{ photo_id, upload_url }` | Creates a `processing` row and a signed R2 upload URL (JPEG, PNG, WebP, HEIC up to 10 MB). `403 limit_reached` (reason `trip_memories`). |
| `POST /memories/photos/{photo_id}/complete` | uploader | none | none to `MemoryPhoto` | Enqueues processing: decode, resize to at most 2,048 px on the long side, strip metadata, thumbnail, content-type sniffing; status `ready` or `failed`. |
| `PATCH /memories/photos/{photo_id}` | uploader or owner | versioned | `{ caption?, is_highlight?, sort_order? }` | |
| `DELETE /memories/photos/{photo_id}` | uploader or owner | none | 204 | Removes the R2 objects. |
| `POST /trips/{trip_id}/share-links` | owner | existing | `{ kind: "memories", ... }` | The existing share link route gains `kind`; the public page `GET /shared/{token}/memories` serves the memory view. `410 share_link_revoked` as usual. |
| `GET /me/year-in-travel/{year}` | user | flag `year_in_travel`, 1 December to 31 January | none to `YearInTravel \| null` | Stats, theme and hidden fields; `null` when no finished trip. |
| `PATCH /me/year-in-travel/{year}` | user | none | `{ theme?, hidden? }` to `YearInTravel` | |
| `POST /me/year-in-travel/{year}/card` | user | 10 an hour | `{ format: "story" \| "square" }` to `{ url, expires_at }` | Renders the image (see below) and returns a signed URL valid 7 days; increments `shared_count` when the client reports a share. |

```ts
type AfterTrip = {
  delay: { due: boolean; hint: { leg: string; minutes_late: number | null; cancelled: boolean; source_label: string; checked_at: string } | null } | null
  wrapup: { due: boolean } | null; archive: { due: boolean } | null; settle: { due: boolean; unsettled_count: number } | null
}
type DelaySheet = {
  official: { label: string; url: string }[]; ask_airline_note: string
  partner: { offer_ref: string; partner: string; label: string; disclosure: "We earn a commission if you book here."; extra_disclosure: string | null } | null
  note: "Eligibility depends on the route and the rules. No result is promised."
}
type YearInTravel = {
  year: number; trips: number; countries: { code: string; name: string }[]; cities: string[]; nights_away: number
  km_flown_about: number; top_destination: string | null; longest_trip_nights: number; new_countries: string[]
  theme: "sky" | "night" | "paper"; hidden: ("countries" | "cities")[]
}
```

Jobs (worker): `build_after_trip_prompts` (api lane, daily per time zone at 09:00 local the day after the
last trip date; also creates the wrap-up, archive at 14 days and settle prompts, idempotent on
`(trip_id, user_id, kind)`), `process_memory_photo` (batch lane, key `photo_id`, transient x3),
`compute_year_in_travel` (batch lane, nightly from 1 November to 31 January and on demand; key
`(user_id, year)`), `render_year_card` (api lane, on demand; Satori and resvg or an equivalent image
renderer in the worker, no headless browser), `purge_memory_objects` (daily, removes objects of deleted
trips, photos and accounts). Errors: `403 limit_reached` with reason `memory_photos`, `422
validation_failed` (unsupported image, too large), `503 feature_disabled` with the kill switch,
`404 not_found` for other users' items.

## 5. UI screens and paywall triggers

1. **After-trip card** (Trips home and trip Overview; one card at a time). Delay prompt: "Was your flight
   delayed or cancelled?" with [No] and [Yes, check what I can claim] (and the data line from AFT-1 when
   present). "Yes" opens the **Claim sheet**: official sources first, the "you can also ask the airline
   directly for free" note, then one labeled partner button with "We earn a commission if you book here.",
   the plain note "Eligibility depends on the route and the rules. No result is promised." and [Not now].
2. **Wrap-up card.** "How was the trip?" with 5 stars, an optional note, [Save]; no affiliate button;
   then the archive offer (14 days after the end) and the single settle-up reminder entry.
3. **Memories tab** (trip). Recap header (days, cities, countries, flights, route map), highlights
   carousel, photo grid with captions, [Add photos] (photo picker; uploads queue offline and retry), limit
   text "20 of 20 photos used" with the soft offer "Keep more photos with Plus or a Trip Pass", [Share
   memories] (creates a memory link with redaction options, same sheet as plan share links).
4. **Memory share page** (public, read-only, `noindex`): recap, highlights, captions, route map; no
   traveler names, prices, notes or addresses unless the owner turned redaction off; "Made with Hermi"
   on Free; "Report" link (existing moderation path).
5. **Year in travel** (Trips home card, then a full screen): stats with big numbers in the mono face,
   cover theme chooser offering three covers (sky, night, paper) with the trip's route pattern and a
   ticket-stub tag per country, "Hide countries" and "Hide cities" switches, [Share] (system share sheet)
   and [Save image]. Preview shows exactly what will be shared; the card carries no names, no photos and
   no dates.
6. **Settings.** Notifications rows: "Year in travel email" (marketing opt-in) and "Trip reminders" (existing).

States. Loading skeletons. Empty Memories: "No memories yet", "Add a few photos from the trip. Only people
on this trip can see them.", [Add photos]. Upload error: "We could not add this photo. Try a smaller
one." Processing: "Preparing your photo". Offline: photos queue with "Waiting to sync". No permission:
viewers see memories, members add. Limit: the photo limit card (soft, no modal). Year card before
December: hidden; no finished trip: "Finish a trip to see your year" appears only in Settings, never as a
nag. Partner content is never shown offline.

Paywall triggers: none new and no hard paywall. A single soft, client-initiated line
`memory_photo_limit` (added to the reason list of `GET /paywall/offer`) appears when a Free owner hits the
20 photo limit; leading offer Trip Pass, then annual Plus; free path "Keep 20 photos"; one paywall per
session, dismiss mutes it for 7 days, never on the wrap-up or delay cards, never beside an affiliate
card, never on a trip where the user is an invitee. Trip pass expiry never removes photos: the trip keeps
them readable and exportable, and only adding beyond the owner's tier limit is blocked.

## 6. Monetization and App Store products

- No new products and no credits. Memories and the Year in travel card are free on every tier; the soft
  photo limit is the only upgrade reason and it is deliberately mild.
- Affiliate: the compensation partner link is the only monetized element, through the existing
  `/go/{click_id}` redirect with `surface = after_trip` and `entity_type = after_trip`: Compensair via
  Travelpayouts (fixed EUR 10 base per confirmed application, higher tiers reported, e.g. EUR 20 for the
  United States at 10 confirmed applications; est. EUR 10 to 20) and AirHelp direct from pack 08 (15
  percent of AirHelp's fee on an approved claim, 20 percent on AirHelp+; est. $13 to $30 per approved
  claim), all reported, verify. Compensation only pays when a flight was delayed or cancelled and
  qualifies (mostly EU261-style rules, which most US-to-US trips do not meet), so expected value is
  small; the prompt exists because it is helpful and trustworthy, not as a revenue pillar.
- Rules: one partner option per cell (A/B between Compensair and AirHelp by experiment, never by payout);
  the global affiliate rules apply (label, non-affiliate route first, kill switch `affiliate.all` and
  `affiliate.<code>`, hide booking links setting, "Ad" tag in the UK and EU, nothing offline); the wrap-up
  and memory screens carry no affiliate button; the year card carries no partner link.
- Storage cost: photos are the only new variable cost. At 2,048 px JPEG (about 0.4 to 1.0 MB processed) and
  the default limits, a Free trip is at most about 20 MB and a Pro trip about 200 MB; R2 storage and
  operations are cheap but tracked (provider health: bytes stored, growth per month); reprice limits by
  `UPDATE` if needed.
- Apple and Google: no purchase involved; the share card is ordinary user content.

## 7. Admin additions

- **Affiliate revenue (08 section 6.7).** New surface `after_trip` in revenue by placement; Compensair and
  AirHelp in program views; disclosure audit includes the claim sheet; experiment setup for the partner
  cell.
- **Moderation (08 section 6.12).** Reported memory pages and photos join the existing queue (target type
  `shared_trip` via the share link, kind `memories`); actions unchanged (hide, disable link, warn,
  suspend sharing); the admin can open a reported photo through a signed URL with an audit entry; photo
  content is never browsed without a report; reports are answered within 24 hours.
- **Provider health and system health.** R2 storage bytes and growth, processing queue depth and failures,
  render time for year cards, job health for the nightly stats job.
- **Kill switches.** `memories.uploads` added; `affiliate.all` and per-program switches cover the claim
  partner.
- **Feature flags.** `trip_memories`, `year_in_travel` (date window rule in `rules`), the delay-hint
  setting.
- **Users.** Storage used per account and per trip; action "remove photo" after a report (audited).
- **Alert rules (08 section 10).** Photo processing failures above 10 percent (notify), R2 growth above 2
  times forecast (notify), share card render errors above 2 percent (notify).
- **Support macros.** "I do not see my year in travel", "Delete my photos", "Is my delayed flight
  eligible" (answer: we cannot say; here are the official sources).

## 8. AI additions

None. The recap, stats and cards are deterministic. No photo, caption, rating or note is sent to an AI
service, no face recognition or image classification is used, and no AI feature reads memories. Affiliate
data stays out of AI. A possible later idea (an optional trip summary sentence) would be an `explain`-class
action with its own consent and is not in this pack.

## 9. Analytics events

No PII, no captions, no place names, no numbers that identify a trip; buckets and enums only.

| Event | Properties | When fired |
|---|---|---|
| `delay_prompt_shown` | `has_status_data` (bool) | Card shown |
| `delay_prompt_answered` | `answer` (`yes`, `no`) | Answer saved |
| `claim_sheet_opened` | `partner_shown` (bool) | Claim sheet displayed |
| `partner_link_tapped` (existing) | `program`, `placement: after_trip` | `/go` click created |
| `trip_rating_submitted` | `rating`, `has_note` (bool) | Review saved |
| `trip_archive_offered` | `action` (`archived`, `later`) | Answer to the archive offer |
| `memories_opened` | `photo_count_bucket` | Memories tab opened |
| `memory_photo_added` | `count_bucket` | Photo processed successfully |
| `memory_photo_limit_reached` | `tier` | Limit hit |
| `memory_page_shared` | `redaction_level` | Memory link created |
| `year_card_viewed` | `year`, `trip_count_bucket` | Year in travel opened |
| `year_card_shared` | `format` (`story`, `square`), `channel` (`share_sheet`, `save_image`) | Share or save completed |

Funnels: after-trip card viewed to rating submitted; memories opened to photo added to page shared; year
card viewed to shared (the viral proxy); `year_card_shared` to new signups from `share_link_viewed` and
the hermi.world landing is measured with a referrer-free first-party visit count, never with tracking
parameters on the card link.

## 10. Tests

- Prompt timing: delay prompt the day after the last trip date in the trip's time zone, once per person,
  never without a chosen or tracked flight, never as a push, dismiss and answered states persist; wrap-up,
  archive at 14 days and one settle reminder fire once each.
- Delay hint: threshold logic from tracked legs (cancelled, 180 minutes, below threshold, missing data),
  the wording never claims eligibility, source and check time shown.
- Claim sheet: official links first, partner option only after "Yes", disclosure sentence and Booking-style
  extra lines where applicable, one partner per cell, kill switches replace the button with nothing or a
  plain link, no partner offline, no affiliate UI on the wrap-up card.
- Reviews: private to the author, owner sees only an aggregate with at least 3 ratings, never used in AI.
- Photo pipeline: content-type sniffing (reject non-images and polyglots), size limits, HEIC conversion,
  EXIF and GPS fully stripped (assert no metadata in the stored file), thumbnail generation, processing
  failure path, limits by tier, offline queue and retry, deletion removes objects, signed URL expiry,
  members only, non members get 404.
- Memory share page: redaction defaults, `noindex`, revocation and expiry, signed photo URLs tied to the
  token, no traveler names or prices by default, report path.
- Year stats: golden fixtures for trips across years and time zones, member versus non-member trips,
  deleted and trashed trips excluded, great-circle distance correctness (for example a known airport
  pair), new countries logic, hidden fields, refresh after edits.
- Card rendering: visual snapshot tests for each theme and format, long city lists truncate cleanly, right
  to left and non-Latin names, no names or dates or photos on the image, image alt text provided for
  sharing, rendering under 2 seconds.
- Privacy: export includes photos and captions, account deletion removes photos, reviews, prompts and year
  rows and objects, tenant isolation tests for the new tables, no analytics payload contains captions or
  place names.
- Accessibility: star rating is a radio group with labels, the year card preview has a text alternative
  with the same numbers, focus order, reduced motion.
- E2E: finish a trip, answer the delay prompt, rate the trip, add three photos, share a memory link,
  open it logged out, then compute and share a year card.

## 11. Tickets

#### P2-095 After-trip prompts engine and delay prompt [M, needs Phase 1 chosen flights and notifications]
- Description: `trip_after_prompts`, the daily `build_after_trip_prompts` job, the delay card and claim
  sheet (official sources first, one labeled partner option), copy and disclosure, content config for the
  official links with link checker coverage.
- Accept: prompt once per trip per person, never a push, not shown without a flight; eligibility never
  claimed; disclosure beside the button.
- Touches: `apps/api/hermi/modules/aftertrip/`, `apps/web/src/routes/after-trip/`.

#### P2-096 Flight status link and partner wiring [S, needs P2-095, pack 05 and pack 08 optional]
- Description: use tracked leg data for the delay hint and its source line, add Compensair now and AirHelp
  when active as cells of one experiment, `placement` value `after_trip`.
- Accept: hint appears only with data; one partner per cell; revenue by surface shows `after_trip`.

#### P2-097 Trip reviews storage and settle reminder [M, needs P2-095]
- Description: `trip_reviews` behind the Phase 1 rating card (store and read the rating and note), record the
  archive offer answer, single settle-up reminder using the `send_group_settle_reminders` job from pack 02.
- Accept: reviews private; archive prompt and reminder once; no affiliate or paywall on the card.

#### P2-098 Memories schema, storage and photo pipeline [L, needs Phase 1 R2 uploads]
- Description: migration `0026_after_trip` photo tables and limits, signed upload flow, `process_memory_photo`
  (decode, resize, strip all metadata, thumbnails, content sniffing), purge job, kill switch.
- Accept: no metadata survives; limits by tier enforced; deletion removes objects.

#### P2-099 Memories UI and recap [L, needs P2-098]
- Description: Memories tab, recap computation, highlights, captions, grid, picker, offline queue, states,
  limit card and soft line.
- Accept: axe clean; alt text from captions; uploads resume after offline.

#### P2-100 Memory share pages [M, needs P2-099, Phase 1 share links]
- Description: `kind = 'memories'` share links with redaction, public page, signed photo URLs, `noindex`,
  report link, moderation queue integration.
- Accept: redaction defaults hold; revoked links return 410; admin can review reported photos with audit.

#### P2-101 Year in travel statistics [M, needs Phase 1 chosen flights, airports]
- Description: `share_cards` (kind `year_in_travel`), `compute_year_in_travel` with the query above, new-countries logic,
  refresh, date window rule, settings and email opt-in wiring.
- Accept: golden fixtures pass; numbers labeled "about" where estimated.

#### P2-102 Year card renderer and sharing [L, needs P2-101]
- Description: image renderer with three themes (sky, night, paper) and two formats, preview screen, hide switches,
  share sheet and save image (iOS and web; Android in pack 09), card alt text, signed URLs.
- Accept: no names, photos, dates or partner links on the image; snapshots pass; render under 2 seconds.

#### P2-103 Privacy, export, deletion and admin [M, needs P2-098, P2-101]
- Description: export and deletion steps for photos, reviews, prompts and year rows, privacy policy and App
  Privacy label update (Photos or Videos, linked to the user, app functionality, not tracking), admin
  storage views, moderation actions, alert rules, support macros.
- Accept: deletion checklist covers all new data; export includes photos and captions.

#### P2-104 Launch checks and December rollout [S, needs P2-102, P2-100]
- Description: staged rollout of `trip_memories` (staff, 10 percent, 100 percent), enable `year_in_travel`
  on 1 December, storage cost watch against the forecast, accessibility pass, share card review on real
  devices.
- Accept: rollout without P0; storage within forecast; share rate of the card recorded.

## 12. Risks

| Risk | Mitigation |
|---|---|
| Compensation looks like a sales pitch after a bad trip | Official sources first, free option stated, one quiet card, never a push, no promises, partner label, kill switch |
| Wrong delay data produces a misleading hint | Hint only with a sourced tracked leg, source and check time shown, wording never claims eligibility |
| Photos leak private data (EXIF, faces, children) | Metadata stripped, members-only signed URLs, no face or image analysis, redaction defaults, report path, children rules unchanged |
| Storage cost grows | Tier limits, client-side downscale, processed size cap, cost watch, limits are an `UPDATE` |
| Year card exposes personal travel patterns | No names, dates or photos, hide switches, private image keys, optional sharing only, no tracking parameters |
| Promotional push rules (Apple 4.10) | In-app card and opt-in email only |
| Numbers look wrong to users (distance, countries) | Labeled "about", derived from trips they can edit, Refresh action, golden tests |
| Low uptake of memories | Measure funnel; the compensation prompt and wrap-up are valuable even without memories; memories are the first cut if capacity is short |
