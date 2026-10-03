# Pack 07: Concierge lane ("Have a human book this")

Part of [Phase 2: growth](README.md). Written 2026-09-30. Source definitions:
[01 section 4.12](../reference-full-spec/01-product-spec.md), [03 section 5.16](../reference-full-spec/03-database-schema.md),
[04 section 5.18](../reference-full-spec/04-api-spec.md), [05 section 6.22](../reference-full-spec/05-ui-ux-spec.md),
[07 section 9](../reference-full-spec/07-monetization-spec.md), [08 sections 6.8](../reference-full-spec/08-admin-control-center.md),
[10 section 3.8](../reference-full-spec/10-quality-security-launch.md), WF-104 and WF-103 in [09](../reference-full-spec/09-build-roadmap.md),
and the business case in [09 revenue expansion](../context/business-plan/09-revenue-expansion.md) section 3.1.

| Item | Value |
|---|---|
| Build order | 7 (build in month 11); the legal and host agency work starts in month 7 |
| Flags | `concierge_requests` (off; enabled per region only after counsel confirms), settings `setting_concierge_open` and `setting_concierge_host` |
| Needs from Phase 1 | Stays shortlist, trips, consents, Resend, R2, admin console with roles, support inbox, feature flags, notifications |
| Soft link | Pack 02 (room-block requests flow into the same queue) |
| Tickets | P2-065 to P2-074 |
| Tier and products | All tiers. Free for the user, no credits. Hermi earns the host agency commission |

## 1. Goal and why now

**Goal.** An optional, quiet "Have a human book this" action on a shortlisted stay, a cruise idea or a
complex trip. A licensed advisor under a host travel agency books it; the user may get perks (breakfast,
a property credit, an upgrade where available); the price to the user is not higher; Hermi earns a
share of the agency commission. It is always optional, always disclosed and never pushed.

**Why now.**

- It is the highest value revenue stream per trip that does not depend on scale: the model assumes $90
  per completed booking on average (85 percent hotels at $55, 10 percent cruises at $290, 5 percent
  packages at $225), $1.6k in year 1 and $27k in year 3 at a cap of about 300 bookings a year solo
  ([09 revenue expansion](../context/business-plan/09-revenue-expansion.md) section 3.1; reported, verify).
- Competitive reasons. To our knowledge none of TripIt, Wanderlog or Trippy offers a human booking lane
  inside a planner (verify before launch copy); it is a differentiator for couples and families who are planning a honeymoon, a milestone
  trip or a cruise and would otherwise leave to book elsewhere. It also gives the room-block request
  (pack 02) somewhere to go.
- Low build, high founder time: the request form and status screen are small; the constraint is
  compliance and the founder's hours, so the long-lead items must start early even though the build comes
  later.
- The launch mode is the founder as the advisor, which tests demand before hiring anyone. The plan caps
  solo capacity at about 300 bookings a year and says no beyond that.

## 2. User stories and acceptance criteria

### F-CON Concierge request (verbatim from the full product spec)

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

### Rules from the monetization spec ([07 section 9](../reference-full-spec/07-monetization-spec.md)), condensed

- Entry points: a card on a shortlisted stay ("Want a person to book this and handle changes?"), on a
  cruise idea, and on complex trips (more than 2 destinations, more than 8 travelers). Never inside AI
  output, never on a paywall, never as a push.
- The consent screen must be accepted before submit. It lists exactly what goes to the advisor and the
  agency: name, email, phone (if given), the request details, the trip's dates and destination, and
  traveler names and dates of birth only at the time of booking and only when the advisor asks for them
  inside the request thread. It says: "Hermi is paid a commission by the travel agency that books
  this. The price to you is the same as booking direct." Passport numbers are never collected in the app.
- Users can withdraw consent, which closes the request and deletes the advisor-side copy within 30 days
  (except records the agency must keep by law).
- The advisor sends quotes and proposals by email outside the app at launch; proposals are attached to
  the request as files. Booking happens on the agency's and supplier's systems; the client pays the
  supplier or agency directly. Hermi never takes payment for the booking and never stores card data.
- Recommendations include options the client asked for and are never ranked by commission; the advisor
  records conflicts.

### Stories added by this pack

| ID | Story | Acceptance |
|---|---|---|
| CON-1 | As a user, I see who will book and under what registration. | The form, the confirmation email and the terms show "Booked by [host agency name], seller of travel registration [number]" with the state registrations that apply ([10 section 3.8](../reference-full-spec/10-quality-security-launch.md)). |
| CON-2 | As a user, I can only ask where it is lawful. | The form asks where the traveler lives (state or country); regions not in the flag's `regions` list show "Not available in your area yet. Join the waitlist." and create no request. |
| CON-3 | As a user, I talk to a person, not AI. | A request thread (messages and proposal attachments) in the app and by email; the screen says "A person replies, not AI." The thread is never read by any AI feature. |
| CON-4 | As a user, I can cancel or withdraw any time. | Cancel before booked; withdrawing `concierge_sharing` consent closes the request and starts the 30 day advisor-copy deletion. |
| CON-5 | As the founder, I can stop intake when I am at capacity. | Setting `setting_concierge_open` off hides the entry cards and shows "Concierge is not taking new requests right now" on the form; requests in progress continue. A weekly cap alert warns at 80 percent of the solo capacity (about 6 bookings a week). |
| CON-6 | As the founder, I record commission and perks correctly. | Finance role records expected and received commission by agency reference, imports the monthly agency statement (CSV) and matches it; cancelled bookings with nothing received count as lost; perks are recorded; a Hermi reward of 40 credits on a completed booking is granted as an `adjustment` grant (default, configurable). |
| CON-7 | As a user, I get updates I asked for. | In-app message and optional push on status changes (no marketing), an email for each advisor message; SLA alerts internally: first reply within 1 business day; a `quoted` request older than 7 days with no reply triggers a follow-up task. |

## 3. Database additions

Migration `0023_concierge`. Phase 1 has no concierge objects ([Phase 1 03 section 1.1](../phase-1-launch/03-database-schema.md)
lists `concierge_requests`, the `concierge_status` type, the `concierge_sharing` consent kind and the `concierge`
support category as dropped; its section 14 lists what this pack adds). Reused from
[03 section 5.16](../reference-full-spec/03-database-schema.md) with these changes: there is no `advisor_org_id` column (the
[Phase 3 advisors pack](../phase-3-scale/02-hermi-for-advisors.md) adds it with its foreign key), a
`consumer_region` column supports the seller-of-travel gate, and two small tables carry the thread and
commission lines.

```sql
CREATE TYPE concierge_status AS ENUM ('submitted', 'triaged', 'assigned', 'quoted', 'booked', 'completed', 'cancelled', 'declined');

CREATE TABLE concierge_requests (
  id                            uuid PRIMARY KEY DEFAULT uuidv7(),
  trip_id                       uuid REFERENCES trips (id) ON DELETE SET NULL,
  requested_by                  uuid REFERENCES users (id) ON DELETE SET NULL,
  kind                          text NOT NULL,
  status                        concierge_status NOT NULL DEFAULT 'submitted',
  brief                         text NOT NULL CHECK (char_length(brief) BETWEEN 1 AND 4000),
  destination                   text,
  start_date                    date,
  end_date                      date,
  party_size                    smallint CHECK (party_size IS NULL OR party_size BETWEEN 1 AND 40),
  budget_min_minor              bigint,
  budget_max_minor              bigint,
  currency                      currency_code,
  contact_email                 citext NOT NULL,
  consumer_region               text NOT NULL,                             -- where the traveler lives, for example US-CA; checked against the flag's regions list
  share_consent_at              timestamptz NOT NULL,                      -- user agreed to share the brief with the agency
  assigned_to                   uuid REFERENCES users (id) ON DELETE SET NULL,
  agency_reference              text,
  perks                         jsonb NOT NULL DEFAULT '[]'::jsonb,
  quote_minor                   bigint,
  quote_currency                currency_code,
  commission_expected_minor     bigint,
  commission_received_minor     bigint,
  commission_currency           currency_code,
  decline_reason                text,
  first_replied_at              timestamptz,
  booked_at                     timestamptz,
  completed_at                  timestamptz,
  created_at                    timestamptz NOT NULL DEFAULT now(),
  updated_at                    timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_concierge_requests_kind CHECK (kind IN ('stay', 'cruise', 'complex_trip', 'other')),
  CONSTRAINT ck_concierge_requests_dates CHECK (end_date IS NULL OR start_date IS NULL OR end_date >= start_date),
  CONSTRAINT ck_concierge_requests_budget CHECK (budget_max_minor IS NULL OR budget_min_minor IS NULL OR budget_max_minor >= budget_min_minor)
);
CREATE INDEX ix_concierge_requests_status ON concierge_requests (status, created_at);
CREATE INDEX ix_concierge_requests_trip ON concierge_requests (trip_id) WHERE trip_id IS NOT NULL;
CREATE INDEX ix_concierge_requests_user ON concierge_requests (requested_by, created_at DESC);
CREATE UNIQUE INDEX uq_concierge_requests_agency_ref ON concierge_requests (agency_reference) WHERE agency_reference IS NOT NULL;
SELECT add_updated_at_trigger('concierge_requests');

-- Pack 02 created room_block_requests without this foreign key.
ALTER TABLE room_block_requests
  ADD CONSTRAINT fk_room_block_requests_concierge FOREIGN KEY (concierge_request_id)
  REFERENCES concierge_requests (id) ON DELETE SET NULL;

CREATE TABLE concierge_messages (                                      -- the thread the user sees, and the status timeline
  id              uuid PRIMARY KEY DEFAULT uuidv7(),
  request_id      uuid NOT NULL REFERENCES concierge_requests (id) ON DELETE CASCADE,
  kind            text NOT NULL,                                        -- message, status, proposal
  sender          text NOT NULL,                                        -- user, advisor, system
  sender_user_id  uuid REFERENCES users (id) ON DELETE SET NULL,
  body            text NOT NULL DEFAULT '' CHECK (char_length(body) <= 4000),
  status_to       concierge_status,                                     -- set on kind = 'status'
  attachments     jsonb NOT NULL DEFAULT '[]'::jsonb,                   -- [{key, name, size, content_type}] objects in R2
  created_at      timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_concierge_messages_kind CHECK (kind IN ('message', 'status', 'proposal')),
  CONSTRAINT ck_concierge_messages_sender CHECK (sender IN ('user', 'advisor', 'system'))
);
CREATE INDEX ix_concierge_messages_request ON concierge_messages (request_id, created_at);

CREATE TABLE concierge_commission_lines (                              -- rows of the monthly agency statement
  id                   uuid PRIMARY KEY DEFAULT uuidv7(),
  statement_month      date NOT NULL,                                   -- first day of the statement month
  agency_reference     text NOT NULL,
  amount_minor         bigint NOT NULL,
  currency             currency_code NOT NULL,
  matched_request_id   uuid REFERENCES concierge_requests (id) ON DELETE SET NULL,
  status               text NOT NULL DEFAULT 'unmatched',               -- matched, unmatched
  imported_by          uuid REFERENCES users (id) ON DELETE SET NULL,
  created_at           timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_concierge_commission_lines_status CHECK (status IN ('matched', 'unmatched')),
  CONSTRAINT uq_concierge_commission_lines UNIQUE (statement_month, agency_reference)
);

-- Support tickets can be linked to concierge requests, and the concierge consent kind is needed if pack 02 has not added it yet.
ALTER TABLE support_tickets DROP CONSTRAINT ck_support_tickets_category;
ALTER TABLE support_tickets ADD CONSTRAINT ck_support_tickets_category
  CHECK (category IN ('billing', 'credits', 'account', 'bug', 'affiliate', 'privacy', 'other', 'concierge'));
-- consents.kind: append 'concierge_sharing' to the current list (pack 02 adds it first; see there).

-- Flags and settings (from 03 section 11.5; the two settings are new).
INSERT INTO feature_flags (key, description, enabled, rollout_pct, rules, variants) VALUES
('concierge_requests', 'Have a human book this (disclosed, optional)', false, 100, '{"regions":[]}', '{}')
ON CONFLICT (key) DO NOTHING;
INSERT INTO feature_flags (key, kind, description, enabled, rollout_pct, rules, variants) VALUES
('setting_concierge_open', 'setting', 'Intake switch for new concierge requests; off hides the entry cards', true, 100, '{"open":true,"weekly_cap":8}', '{}'),
('setting_concierge_host', 'setting', 'Host agency name and seller of travel registrations shown to users; host split in basis points', true, 100,
 '{"agency_name":"","registrations":{},"terms_url":"","split_bps":7000,"reward_credits":40}', '{}')
ON CONFLICT (key) DO NOTHING;
```

Row-level security (from [03 section 6.3](../reference-full-spec/03-database-schema.md), plus the new tables). A request is
visible to the requester and, while the trip exists, to its members; only the requester inserts; status
changes are written by the admin role.

```sql
ALTER TABLE concierge_requests ENABLE ROW LEVEL SECURITY;
CREATE POLICY concierge_requests_select ON concierge_requests FOR SELECT
  USING (requested_by = (SELECT app_user_id()) OR trip_id IN (SELECT visible_trip_ids()));
CREATE POLICY concierge_requests_insert ON concierge_requests FOR INSERT
  WITH CHECK (requested_by = (SELECT app_user_id()) AND (trip_id IS NULL OR can_edit_trip(trip_id)));

ALTER TABLE concierge_messages ENABLE ROW LEVEL SECURITY;           -- the thread is for the requester only
CREATE POLICY concierge_messages_select ON concierge_messages FOR SELECT
  USING (request_id IN (SELECT id FROM concierge_requests WHERE requested_by = (SELECT app_user_id())));
CREATE POLICY concierge_messages_insert ON concierge_messages FOR INSERT
  WITH CHECK (sender = 'user' AND sender_user_id = (SELECT app_user_id())
              AND request_id IN (SELECT id FROM concierge_requests WHERE requested_by = (SELECT app_user_id())));
-- concierge_commission_lines has no policies for the app role: admin and worker roles only.
```

Notification kinds (swap `ck_notifications_kind` for the current list plus these): `concierge_update`,
`concierge_message`. Dedupe keys: `concierge_update:<request_id>:<status>`.

Retention: requests and messages are kept 24 months after completion for commission and dispute
records (counsel to confirm), then deleted; on consent withdrawal the advisor-side copy is deleted within
30 days and the in-app thread is anonymized; account deletion anonymizes `requested_by` and removes the
thread; commission totals stay without personal data.

## 4. API additions

From [04 section 5.18](../reference-full-spec/04-api-spec.md), verbatim:

| Endpoint | Auth | Gate and cost | Request and response | Errors and side effects |
|---|---|---|---|---|
| `POST /trips/{trip_id}/concierge-requests` | owner or editor | none | `ConciergeIn` with `Idempotency-Key` to 201 `ConciergeRequest` | Writes `concierge_requests` (status `submitted`), emails the advisor desk through Resend, and posts to the admin queue. Needs the `concierge_sharing` consent, recorded as `share_consent_at` on the request. Only the listed fields are shared with the advisor; other travelers' names are sent only if the requester includes them. |
| `GET /trips/{trip_id}/concierge-requests` | viewer | none | none to `ConciergeRequest[]` | |
| `PATCH /concierge-requests/{id}` | requester | status `submitted`, `triaged` or `quoted` | `{ message?: string, cancel?: boolean }` to `ConciergeRequest` | |

```ts
type ConciergeIn = {
  kind: "stay" | "cruise" | "complex_trip" | "other"
  lodging_id?: Uuid; budget?: Money; notes: string; preferred_contact: "email" | "in_app"   // budget becomes budget_max_minor; notes becomes brief (with lodging_id and preferred_contact appended)
  disclosure_accepted: true                    // "A human advisor may book this and Hermi earns a commission from the agency."
}
type ConciergeRequest = Omit<ConciergeIn, "disclosure_accepted"> & {
  id: Uuid; trip_id: Uuid; status: "submitted" | "triaged" | "assigned" | "quoted" | "booked" | "completed" | "cancelled" | "declined"
  advisor_name: string | null; created_at: string; updated_at: string; perks: string[]
}
```

Additions in this pack:

| Endpoint | Auth | Gate and cost | Request and response | Errors and side effects |
|---|---|---|---|---|
| `GET /concierge/availability` | user | none | `?region=` to `{ open: boolean, region_served: boolean, host: { agency_name, registrations, terms_url } }` | Drives the entry cards and the "Not available in your area yet" state from the flag and settings. |
| `ConciergeIn` fields | | | adds `consumer_region: string`, `destination?`, `start_date?`, `end_date?`, `party_size?`, `currency?` | The form fields in the 05 layout. `422 validation_failed` with code `region_not_served` when outside the list. |
| `GET /concierge-requests/{id}/messages` | requester | none | `?after=` to `ConciergeMessage[]` | The thread and status timeline. |
| `POST /concierge-requests/{id}/messages` | requester | status not `cancelled`, `declined` or `completed` | `{ body: string }` with `Idempotency-Key` to 201 | Emails the advisor desk; attachments are sent by email, not uploaded, in this version. |
| `DELETE /concierge-requests/{id}/consent` | requester | none | 204 | Withdraws `concierge_sharing`, closes the request (`cancelled`), schedules advisor-side deletion in 30 days, audited. |
| Admin (see section 7) | | | `GET /concierge`, `PATCH /concierge/{id}`, `POST /concierge/{id}/commission`, `POST /concierge/commission-import` | [08 section 8](../reference-full-spec/08-admin-control-center.md). |

Duplicate requests for the same item (same `lodging_id` or same kind and dates on a trip within 30 days)
return the existing request instead of a new one. Errors: `503 feature_disabled` when the flag or intake
setting is off; `403 insufficient_role` for viewers; `404 not_found` for others' requests.

Webhooks and jobs: `build_concierge_digest` (notify lane, hourly) notifies the advisor desk of new or
stale requests (key `(request_id, state)`); `send_email` templates for request received, advisor
message, status change and declined with reason; SLA scan every 15 minutes (first reply due within 1
business day; `quoted` older than 7 days). Advisor email contains a secure link, never personal data in
the body.

## 5. UI screens and paywall triggers

Screen 6.22 from [05](../reference-full-spec/05-ui-ux-spec.md), verbatim:

**Purpose.** Let a person ask a human advisor to book something, always optional and disclosed.
**Layout.** Entry card on Stays and Overview: "Have a human book this", a two-line explainer and
[Request help]. Request form as a sheet: what to book (Stays, Cruise, Complex trip, Other), dates,
travelers, budget range, preferences, preferred contact. Confirmation screen with expected reply time.
**Content.** A disclosure block in plain words: "A travel advisor at our partner agency will book this
for you and is paid a commission by the suppliers. You pay the same price. You can say no at any time."
Perks, if any, are listed as facts, never as urgency. The advisor relationship is clearly separate from
AI ("A person replies, not AI.").
**Interactions.** Submit creates a request (`concierge_requests`). Status: Received, In progress, Options
ready, Closed. Replies arrive in Activity and by email. Cancel any time.
**States.** Loading: form skeleton. Empty (no requests): entry card only. Error: "We could not send your
request. Your answers are saved. Try again." Offline: the form saves as a draft. No permission: owner
and editors can request; viewers see the card without the button. Limit: none. Not available in the
region: "Concierge is not available where you are yet. Join the waitlist."
**Events.** `concierge_card_shown {surface}`, `concierge_requested {kind, region}`,
`concierge_status_changed {kind, status}` (a cancel by the requester is `status: cancelled`).
**Accessibility.** The disclosure is body text above the submit button and is read before it; the form
uses standard labels and errors.

Additions in this pack:

- **Status mapping** (user labels to `concierge_status`): Received (`submitted`, `triaged`), In progress
  (`assigned`), Options ready (`quoted`), Closed (`booked`, `completed`, `cancelled`, `declined`). The
  timeline shows the detailed step and date; a booked request shows the booking reference and perks as
  facts; a declined one shows the reason and "Book it yourself" with the plain partner options.
- **Request detail** with the thread, proposal attachments (links to files), [Cancel request] and
  "Withdraw my consent and delete my data".
- **Consent sheet** before submit: what goes to the advisor and the agency, the commission sentence, the
  registration line (CON-1), [Agree and send] [Not now]. Consent is separate from the app terms and is
  stored as `consents.kind = 'concierge_sharing'`.
- **Entry points**: shortlisted stay card ("Want a person to book this and handle changes?"), cruise
  ideas, trip overview when the trip has 3 or more destinations or more than 8 travelers; at most one
  card per screen view; never on paywalls, inside AI output, in presentation mode or in push.
- **Offline and region states** as above; "Join the waitlist" stores the email as a marketing-free
  waitlist entry (consent text shown).

Paywall triggers: none. The concierge is not gated or monetized against the user and never appears beside
an upsell. The plain partner "Book" link stays beside the card.

## 6. Monetization and App Store products

No App Store products, no credits spent. Revenue is the host agency commission on bookings made through
the lane (reported, verify every split):

| Item | Figure |
|---|---|
| Hotel commission to the agency | About 8 to 15 percent, average 12 percent reported for Fora Reserve |
| Cruise commission | 10 to 16 percent, river cruises 15 to 20 percent |
| Host split | Fora 70/30 to start, 80/20 at $300,000 of annual sales, 90/10 at $2M, $299 a year or $99 a quarter; Outside Agents 80 to 90 percent, about $199 to start and $26 to $46 a month; KHM 80 percent, 90 percent after $5,000 paid commission |
| Model average | $90 per completed booking to Hermi; $600 stay at 10 percent and a 70 percent split is $42 |
| Timing | Commission arrives 30 to 90 days after travel; cancelled stays pay nothing; revenue is recognized when received |
| Fixed costs | About $1.4k to $2.2k a year: host fee about $400, E&O insurance $400 to $1,200 for $1M per claim, seller-of-travel registrations about $640 a year for California, Florida, Washington and Hawaii (reported) |

- The user pays nothing extra and Hermi never takes payment for the booking. Apple: a physical travel
  service consumed outside the app, outside In-App Purchase under Guideline 3.1.3(e), never unlocks app
  features, described in the review notes. Google Play (pack 09): check the equivalent policy before
  enabling the lane on Android.
- Perks are recorded in `perks`. A Hermi reward of 40 credits on a completed booking is an
  `adjustment` grant (default, configurable in `setting_concierge_host`). The reward is paid after the
  commission is confirmed, never at request time, and is not advertised as a reason to book.
- Recommendations are never ranked by commission and the advisor records conflicts.
- No insurance sales or advice through the concierge path unless the host agency and counsel approve in
  writing.

### Long-lead checklist (start in month 7; none of it is engineering)

1. Email Fora, Outside Agents and KHM and ask in writing whether app-routed leads are allowed
   ([09 revenue expansion](../context/business-plan/09-revenue-expansion.md) open question 2).
2. Choose the host agency; sign the independent contractor agreement; confirm accreditation (IATA, ARC,
   CLIA or TRUE) through the host.
3. Seller-of-travel: counsel confirms whether forwarding a request to a human advisor needs registration in
   each state where users live (inference: referral only is usually outside, selling is not); register
   where required (California, Florida, Hawaii, Washington, Iowa are the named states); fill
   `setting_concierge_host` and the flag's `regions`.
4. E&O insurance ($1M per claim reported; host cover may apply).
5. Terms of service and privacy policy updates; consent copy; retention periods; Apple and Google review
   notes.
6. Advisor agreement for later advisors: data handling, conduct, commission, audited access.

## 7. Admin additions

From [08 section 6.8](../reference-full-spec/08-admin-control-center.md), verbatim and extended:

- **Purpose:** run the optional "Have a human book this" lane with clear status and commission records
  (hosted under a host travel agency).
- **Data shown** (`concierge_requests`): request id, masked requester, trip, `kind` (`stay`, `cruise`,
  `complex_trip`, `other`; room block requests come from `room_block_requests`), budget range, dates,
  `status`, `assigned_to`, SLA timer, `quote_minor`, `agency_reference` (booking reference), `perks`,
  `commission_expected_minor` and `commission_received_minor`, `booked_at` and `completed_at`.
- **Statuses** (`concierge_status`): `submitted`, `triaged`, `assigned`, `quoted`, `booked`, `completed`,
  `cancelled`, `declined`.
- **Filters:** status, assignee, type, age, overdue SLA, commission outstanding.
- **Actions:** assign, change status (support, engineer, owner), add note, send templated message (via
  support macros), record commission (finance: `commission_expected_minor`, `commission_received_minor`,
  `commission_currency`; the host split is in `setting_concierge_host` in Phase 2 and
  `advisor_orgs.commission_split_bps` after Phase 3), attach perks, decline with reason, convert into a
  support ticket.
- **Guardrails:** first reply due within 1 business day (overdue shows red); a request is created only by
  a user's explicit tap, never automatically; the requester sees the disclosure ("Hermi earns a
  commission from the travel agency on bookings made this way"); commission fields are finance and owner
  writable only; the console never stores payment card data; a declined request says why to the user
  through a macro.

Added in this pack:

- **Room blocks** appear in the same queue as kind "room block" (from pack 02); a room-block request can
  be converted into a concierge request (`room_block_requests.concierge_request_id`).
- **Commission import**: upload the monthly agency statement as CSV (`agency_reference`, amount,
  currency); matched lines set `commission_received_minor` and `concierge_commission_lines`; unmatched
  lines are listed for manual matching; a cancelled booking with expected commission and nothing
  received shows as lost. Mismatches are logged as `adjust` notes in `audit_log`.
- **Capacity panel**: requests this week against `weekly_cap`, bookings completed per year against the
  300 solo limit, founder hours per booking (manual entry), intake switch.
- **Permissions**: concierge queue W for support, engineer, owner and finance (support updates status,
  finance records commission; everyone else read), per the matrix in 08 section 3.
- **Support macros**: concierge follow-up (existing), "declined request", "withdraw consent", "commission
  explained".
- **Alert rules (08 section 10)**: concierge request past 1 business day (notify), `quoted` older than 7
  days (notify), weekly cap at 80 percent (notify).
- **Revenue**: the overview and finance reports add "concierge commission" as a stream (expected,
  received, lost).

## 8. AI additions

None, deliberately. No AI feature reads requests, threads or attachments, and the user-facing copy says
"A person replies, not AI." The trip summary attached to a request is built by a deterministic template,
not by Anthropic. The only AI-adjacent rule is the existing one: AI never gives insurance, visa or legal
advice and never appears beside the concierge card.

## 9. Analytics events

Existing events: `concierge_card_shown {surface}`, `concierge_requested {kind, region}`,
`concierge_status_changed {kind, status}`, `trip_created {source: concierge}`.

| Event | Properties | When fired |
|---|---|---|
| `concierge_consent_shown` | none | Consent sheet displayed |
| `concierge_consent_declined` | none | "Not now" on the consent sheet |
| `concierge_consent_withdrawn` | `status_at_withdrawal` | Consent withdrawn |
| `concierge_region_blocked` | `region` | A request blocked by region (server side) |
| `concierge_message_sent` | `sender` (`user`, `advisor`) | Thread message (no text) |
| `concierge_booking_completed` | `kind` | Status reaches `completed` (no amounts in analytics) |
| `concierge_intake_paused` | none | Intake setting switched off (server side) |

Funnel: `concierge_card_shown` to `concierge_requested` to `concierge_status_changed {status: booked}`;
ask rate per trip is the headline metric (assumption: 2 percent opt in, 50 percent completed).

## 10. Tests

- Consent: no request without `concierge_sharing` consent; consent text version stored; withdrawal closes
  the request, schedules advisor-copy deletion and is audited.
- Region gate: flag `regions` list enforced server side; blocked region creates nothing and shows the
  right copy; the registration line renders in the form, email and terms for each configured state.
- Entry points: a card never appears inside AI output, paywalls, presentation mode or push; at most one
  per screen view; viewers see no button; duplicate requests merge.
- Status lifecycle and timeline mapping; declined shows the reason and the DIY path; cancel allowed only
  in `submitted`, `triaged`, `quoted`.
- Privacy: only the listed fields are shared; other travelers' names only if the requester includes
  them; no personal data in advisor email bodies; RLS and tenant isolation for requests and messages.
- Finance: commission roles, CSV import matching, lost commission, reward grant once on completed
  booking (idempotent), no credits before commission confirmed.
- Capacity: intake switch hides cards and blocks new requests, in-progress requests continue.
- SLA jobs: overdue first reply and stale quote alerts.
- Disclosure snapshot tests for the card, sheet, confirmation and emails.
- E2E: request from a shortlisted stay, advisor reply in the admin console, user sees the status and
  message, cancel.

## 11. Tickets

#### P2-065 Legal and host agency setup [M, starts month 7, no code]
- Description: the long-lead checklist in section 6: written answers from host agencies, counsel review of
  seller-of-travel and forwarding-a-request, registrations, E&O, contract, consent and terms copy.
- Accept: host chosen; regions list agreed with counsel; documents stored in `docs/legal/`.
- Gate: no production request before this is done.

#### P2-066 Schema, RLS, flags and settings [M, needs Phase 1 schema]
- Description: migration `0023_concierge`, policies, flag and settings seeds, foreign key from pack 02.
- Accept: empty to head and previous to head pass; cross-tenant suite covers the new tables.

#### P2-067 Concierge API, availability and messages [M, needs P2-066]
- Description: create (with consent and region check), list, patch, thread, consent withdrawal, duplicate
  merge, Resend emails to the advisor desk, idempotency.
- Accept: no request without an explicit tap and consent; disclosure returned with every response.
- Touches: `apps/api/hermi/modules/concierge/`.

#### P2-068 Request form, consent sheet and entry cards [L, needs P2-067]
- Description: entry cards on stays, cruise ideas and complex trips, the sheet, consent, confirmation,
  states, region and intake states.
- Accept: axe clean; disclosure is body text above Submit; one card per screen view.
- Touches: `apps/web/src/routes/concierge/`.

#### P2-069 Status timeline, thread and notifications [M, needs P2-067, Phase 1 notifications]
- Description: request detail, thread, status mapping, in-app and email updates, optional push, Activity
  items.
- Accept: replies arrive by email and in-app; declined shows reason and DIY path.

#### P2-070 Admin concierge queue [L, needs P2-067, Phase 1 admin console]
- Description: queue screen, assignment, statuses, notes, macros, SLA timers, room-block conversion,
  permissions, audit.
- Accept: commission fields writable by finance and owner only; first reply due timers visible.
- Touches: `apps/api/hermi/modules/admin/concierge.py`, `apps/web/src/routes/admin/concierge/`.

#### P2-071 Commission tracking and import [M, needs P2-070]
- Description: expected and received commission, CSV statement import and matching, lost commission,
  completed-booking credit reward through `adjustment` grant, revenue stream in finance reports.
- Accept: import is idempotent; reward granted once; reports reconcile with received totals.

#### P2-072 Capacity, SLA and alerts [S, needs P2-070]
- Description: intake switch, weekly cap panel, SLA jobs, alert rules, `build_concierge_digest`.
- Accept: alerts fire in a drill; intake off hides cards.

#### P2-073 Privacy, deletion and retention [S, needs P2-067]
- Description: consent withdrawal and advisor-copy deletion job, retention sweep, account deletion and
  export steps, privacy policy and App Privacy label updates.
- Accept: deletion checklist covers requests and messages; export includes the user's requests.

#### P2-074 Review notes, staged launch and first bookings [S, needs P2-068, P2-065]
- Description: Apple and Google review notes text (service consumed outside the app, no feature
  unlock), enable the flag for one region, then more; founder runs the first 10 bookings end to end and
  records hours per booking and commission timing.
- Accept: first completed booking recorded; measured founder time per booking replaces the 30 to 60
  minute assumption.

## 12. Risks

| Risk | Mitigation |
|---|---|
| Seller-of-travel regulation (California, Florida, Hawaii, Washington, Iowa and others) | Region-gated flag, registration line shown, counsel sign-off before any request, Hermi never takes booking payment or calls itself a travel seller |
| Host agency terms forbid app-routed leads | Written confirmation first (P2-065); switch hosts (Fora, Outside Agents, KHM) if needed |
| Founder time and burnout (about 300 bookings a year solo) | Intake switch, weekly cap, say no beyond capacity, hire advisors later at a 50 percent split |
| Commission arrives late or not at all (30 to 90 days after travel, cancellations pay nothing) | Recognize when received, track expected versus received versus lost, reward credits only after commission |
| Trust and conflict of interest | Disclosure on the card, form, confirmation and proposal; options the client asked for; never ranked by commission; always optional with the plain Book link beside it |
| Data sharing with a third party | Explicit separate consent, only the listed fields, advisor access audited, withdrawal deletes within 30 days |
| Apple and Google policy | Physical service outside the app, never unlocks features, review notes; re-read the guidelines on submission day |
