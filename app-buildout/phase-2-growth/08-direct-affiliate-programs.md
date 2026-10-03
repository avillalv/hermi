# Pack 08: Direct affiliate programs

Part of [Phase 2: growth](README.md). Written 2026-09-30. Source definitions:
[01 section 4.13](../reference-full-spec/01-product-spec.md), [03 sections 5.15 and 11.4](../reference-full-spec/03-database-schema.md),
[04 section 5.21](../reference-full-spec/04-api-spec.md), [07 section 8](../reference-full-spec/07-monetization-spec.md),
[08 section 6.7](../reference-full-spec/08-admin-control-center.md), WF-099 and WF-101 in [09](../reference-full-spec/09-build-roadmap.md), and
the program research in [08 affiliate revenue](../context/business-plan/08-affiliate-revenue.md). Every commission rate,
cookie window and eligibility rule in this pack is **reported, verify** until read on the network's own
terms page after sign-up (the official partner sites were blocked from the research environment).

| Item | Value |
|---|---|
| Build order | 6, but the applications start in month 7 because approvals take weeks; adapters land as approvals arrive (months 9 to 10) |
| Flags and switches | No feature flag. Each program has a kill switch `affiliate.<code>` and the global `affiliate.all`; program `status` (`planned`, `applied`, `active`, `paused`, `closed`) controls what is shown |
| Needs from Phase 1 | `/v1/outbound` and `/go/{click_id}`, `affiliate_programs`, `affiliate_link_templates`, `link_clicks`, `affiliate_conversions`, nightly conversion import for Travelpayouts, Viator and Stay22, disclosure component, admin affiliate revenue screen, traffic numbers from the overview |
| Feeds | Pack 10 (AirHelp for the compensation prompt) |
| Tickets | P2-075 to P2-083 |
| Tier and products | All tiers see the same links in the same places. No App Store products |

## 1. Goal and why now

**Goal.** Move the biggest affiliate categories from aggregator rates to direct programs where the terms
are better or where the program is the only route: Expedia Group (the only legal route to Vrbo, plus
Expedia and Hotels.com), Booking.com direct, Skyscanner (licensed fare data matters more than the cash),
Airalo (explicit mobile app tracking) and GetYourGuide direct. Keep every rule: one partner per surface
per test cell, no ranking by commission, plain links for pasted listings, never fetch Airbnb, Vrbo or
Booking.com pages.

**Why now.**

- Affiliate income is the free tier's revenue and most of the early business: $0.10, $0.60 and $1.50 per
  monthly user per year in the three scenarios, and the kill rule stops the project if annualized
  affiliate income is under $0.20 per monthly user at month 9 after launch
  ([business plan](../context/business-plan/01-business-plan.md)). Phase 2 is when measured clicks replace the model's
  assumptions, so better rates and better tracking matter.
- Lodging is about 60 percent of affiliate income. Vrbo and Hotels.com exist only through the Expedia
  Group program (Impact); Stay22's Link Swap is a second route at a lower rate. Pasted Vrbo links are
  currently plain links; a separate labeled "Book via partner" button can wrap them, built from the URL
  text and never by fetching the page.
- Approvals need live traffic and screenshots of disclosure and placement, which only exist after
  Phase 1 launches. Applications have lead times, so they start the first week of Phase 2.
- Competitive reasons. TripIt sells subscriptions and Wanderlog is ad supported (reported, verify;
  [business plan](../context/business-plan/01-business-plan.md)); Hermi's public promise is "no ads, honest labels", so
  better direct program rates are the way to earn more per click without adding any placement.
- The Skyscanner relationship is also a hedge: the risk register lists SerpApi terms as a medium
  likelihood risk to live fares, and a licensed fare source would remove it.

## 2. User stories and acceptance criteria

The global affiliate rules from [01 section 4.13](../reference-full-spec/01-product-spec.md) apply unchanged and each is a
testable requirement: a label "We earn a commission if you book here." beside every partner button (UK
and EU storefronts also show an "Ad" tag); lists state how they are sorted and nothing is ranked by
commission; pasted listing links stay exactly as pasted; at most one affiliate card per screen view
except on lists the user asked for; no pop-ups, no interstitials, nothing during presentation playback,
nothing in AI output, no affiliate card beside an upsell; a non-affiliate route appears where one exists;
a per-partner kill switch can hide a partner immediately; paid tiers see the same links; offline mode
shows no partner content; Settings has "How we earn money" and a "Hide booking links" switch.

| ID | Story | Acceptance |
|---|---|---|
| AFF-1 | As a user with a pasted Vrbo, Expedia or Hotels.com link, I see a separate "Book via partner" button. | "Open" still opens my saved URL with no wrapper or tracking parameters. The partner button appears only when the Expedia Group program is `active`, is built from the URL text (host, path, the trip's dates), never by fetching the page, and carries the commission sentence. Never for Airbnb. |
| AFF-2 | As a user, searches prefilled with my dates use the best available program. | The A/B cell (`affiliate_lodging_test`) chooses among Travelpayouts Booking.com, Stay22 and direct programs by experiment, never by payout; every variant shows the same disclosure and the same non-affiliate route. |
| AFF-3 | As a user with a chosen flight, I can "Book on Skyscanner" as an option. | Shown as one of the labeled routes beside "Search on the airline's site"; fare age and "price can change" are shown; Skyscanner is one partner per surface per test cell, never two networks on one button. |
| AFF-4 | As an international traveler, I get a labeled eSIM link in the checklist. | Airalo is a link out only, never sold or described as an in-app unlock; hidden for domestic trips; the checklist keeps at least half its items unmonetized; the official visa link stays first. |
| AFF-5 | As a user looking at things to do, I can buy a ticket for an item in my plan. | GetYourGuide direct joins Viator and the Travelpayouts GetYourGuide program as labeled options; only the booked option counts toward commission (no double counting); day order is never changed. |
| AFF-6 | As the founder, I see whether each program is paying. | Conversions for every new program are imported nightly and matched by sub-id; unmatched share above 10 percent alerts; approval rate under 60 percent alerts; EPC by program and surface is in the dashboard. |
| AFF-7 | As the founder, a program can be switched off at once. | `affiliate.<code>` hides the buttons on the next fetch and makes `/go` return the plain non-affiliate destination; a known expired or used click id also redirects to the plain destination so nobody is stranded. |
| AFF-8 | As a user, partner-mandated wording is shown. | Booking.com's line "As a Booking.com Affiliate, we earn from qualifying transactions." appears next to its links in addition to the standard sentence; other partner lines are stored in `extra_disclosure_text`. |

Programs in scope and their reported terms (all **reported, verify**):

| Program (`code`) | Network | Category | Reported commission | Cookie | Status plan |
|---|---|---|---|---|---|
| Expedia Group: Vrbo, Expedia, Hotels.com (`expedia_group`) | Impact | lodging | Vrbo 2 to 6 percent (some report more), Hotels.com 6 to 16 percent, Expedia 2 to 12 percent; est. Vrbo $11 to $36 per booking | 7 days (Hotels.com 30 outside US and CA) | apply month 7 |
| Booking.com direct (`booking_direct`) | Confirm the current network first (the Awin arrangement is reported to be ending, June 2026) | lodging | 4 percent or a tiered share; est. about $24 per booking | Session to 24 hours | confirm network, then apply |
| Skyscanner (`skyscanner`) | Impact | flights | Revenue share, reported GBP 0.07 to 0.30 per flight click; est. $0.10 to $0.40 per click | 30 days | apply month 7 (reported bar of 5,000 monthly uniques) |
| Airalo (`airalo`) | Impact | esim | From 10 percent (up to 12 percent) on new customers, one-off; est. $2 to $3 per sale | 30 days | apply month 7 |
| GetYourGuide direct (`getyourguide_direct`) | Own program | tours | 8 percent (5 to 8 percent by network) through Travelpayouts today; est. about $8 per booking; the Partner API reportedly needs 50,000 app downloads, so do not apply for the API yet | 30 to 31 days | apply month 7 for links and widgets |
| AirHelp (`airhelp`) | Direct affiliate page, networks | compensation | 15 percent of AirHelp's fee on an approved claim, 20 percent on AirHelp+; est. $13 to $30 per approved claim | verify | apply month 8, used by pack 10 |

Program rules that stay as in Phase 1: one partner per surface per test cell; Airbnb has no program an
app can join, so its listings get plain links that are never converted (a database check blocks it);
insurance programs (`travelpayouts_ekta`, `travelpayouts_visitorscov`) stay `planned` until legal
sign-off; no cashback or incentive that changes a partner's terms; no credit cards, VPNs or Amazon data.

## 3. Database additions

Migration `0024_direct_affiliate`. The Phase 1 tables (`affiliate_programs`, `affiliate_link_templates`,
`link_clicks`, `affiliate_conversions`, `affiliate_payouts`) exist from
[Phase 1 03 section 5.15](../phase-1-launch/03-database-schema.md), but Phase 1 seeds only Travelpayouts,
Stay22 and Viator: its check on `affiliate_programs.network` allows only `travelpayouts`, `stay22` and
`viator`, `webhook_events.provider` has no `impact`, and the direct programs, their link templates and their
kill switches are not seeded ([Phase 1 03 section 1.1](../phase-1-launch/03-database-schema.md) and
section 14). This pack widens the checks, seeds the programs as `planned` (rows from
[03 section 11.4](../reference-full-spec/03-database-schema.md)), adds an application tracker, fills the Impact sub-id fields and
relaxes one template constraint. The Booking.com direct, Expedia Group, Skyscanner, Airalo and GetYourGuide
direct rows are the ones in this pack's scope; `airhelp` is seeded here too because pack 10 needs it.

```sql
-- Widen the network check and the webhook provider check (swap the named constraints; keep every value other revisions allow).
ALTER TABLE affiliate_programs DROP CONSTRAINT ck_affiliate_programs_network;
ALTER TABLE affiliate_programs ADD CONSTRAINT ck_affiliate_programs_network
  CHECK (network IN ('travelpayouts', 'stay22', 'viator', 'impact', 'direct'));
ALTER TABLE webhook_events DROP CONSTRAINT ck_webhook_events_provider;
ALTER TABLE webhook_events ADD CONSTRAINT ck_webhook_events_provider
  CHECK (provider IN ('revenuecat', 'apple', 'stripe', 'travelpayouts', 'viator', 'stay22', 'impact', 'inbound_email', 'flight_status'));

-- Seed the direct programs as planned (from 03 section 11.4). The Impact sub-id fields are filled here (the full 03 leaves them empty,
-- while 07 section 8.2 puts the click id in subId1 and the surface in subId2).
INSERT INTO affiliate_programs (code, network, name, category, status, hosts, cookie_days, subid_param, campaign_param, api_credentials_ref, extra_disclosure_text) VALUES
('expedia_group',       'impact', 'Expedia Group (Vrbo, Expedia, Hotels.com)', 'lodging',      'planned', '{vrbo.com,expedia.com,hotels.com}', 7,  'subId1', 'subId2', 'IMPACT_EXPEDIA_TOKEN', NULL),
('booking_direct',      'direct', 'Booking.com direct',                        'lodging',      'planned', '{booking.com}',                     1,  NULL,     NULL,     'BOOKING_AFFILIATE_ID', 'As a Booking.com Affiliate, we earn from qualifying transactions.'),
('skyscanner',          'impact', 'Skyscanner',                                'flights',      'planned', '{skyscanner.com}',                  30, 'subId1', 'subId2', 'IMPACT_SKYSCANNER_TOKEN', NULL),
('airalo',              'impact', 'Airalo',                                    'esim',         'planned', '{airalo.com}',                      30, 'subId1', 'subId2', 'IMPACT_AIRALO_TOKEN', NULL),
('getyourguide_direct', 'direct', 'GetYourGuide direct',                       'tours',        'planned', '{getyourguide.com}',                30, NULL,     NULL,     'GETYOURGUIDE_PARTNER_ID', NULL),
('airhelp',             'direct', 'AirHelp',                                   'compensation', 'planned', '{airhelp.com}',                     30, NULL,     NULL,     'AIRHELP_PARTNER_ID', NULL)
ON CONFLICT (code) DO NOTHING;

-- One kill switch per program, named affiliate.<code>, for the new programs (Phase 1 created them for its own programs only).
INSERT INTO kill_switches (key, description)
SELECT 'affiliate.' || code, 'Turn ' || name || ' links off (plain links only)' FROM affiliate_programs
ON CONFLICT (key) DO NOTHING;

-- Application tracker: one row per application attempt, with the evidence that was submitted.
CREATE TABLE affiliate_applications (
  id                uuid PRIMARY KEY DEFAULT uuidv7(),
  program_id        uuid NOT NULL REFERENCES affiliate_programs (id) ON DELETE CASCADE,
  status            text NOT NULL DEFAULT 'drafting',
  submitted_at      timestamptz,
  decided_at        timestamptz,
  submitted_by      uuid REFERENCES users (id) ON DELETE SET NULL,
  reference         text,                                      -- the network's application id
  traffic_snapshot  jsonb NOT NULL DEFAULT '{}'::jsonb,        -- MAU, clicks by surface, countries, exported from the admin overview
  evidence_keys     text[] NOT NULL DEFAULT '{}',              -- R2 objects: screenshots of disclosure and placement
  terms_reviewed_at timestamptz,                               -- terms read and filed in docs/affiliate/terms/
  terms_notes       text NOT NULL DEFAULT '',                  -- app use, cashback, link format, sub-id rules, reporting
  decision_note     text NOT NULL DEFAULT '',
  created_at        timestamptz NOT NULL DEFAULT now(),
  updated_at        timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_affiliate_applications_status CHECK (status IN ('drafting', 'submitted', 'more_info', 'approved', 'rejected', 'withdrawn'))
);
CREATE INDEX ix_affiliate_applications_program ON affiliate_applications (program_id, created_at DESC);
SELECT add_updated_at_trigger('affiliate_applications');
-- No policy for the app role: admin and worker roles only.

-- The Phase 1 check blocks "u=" in any template, but Impact and Travelpayouts deep links need it to carry the destination.
-- Keep redirect, url and next blocked, allow u only on deeplink templates, and validate the destination host in code (below).
ALTER TABLE affiliate_link_templates DROP CONSTRAINT ck_affiliate_link_templates_no_url_param;
ALTER TABLE affiliate_link_templates ADD CONSTRAINT ck_affiliate_link_templates_no_url_param
  CHECK (template !~* '[?&](url|redirect|next)=\{dest' AND (kind = 'deeplink' OR template !~* '[?&]u=\{dest'));
```

Destination validation for deep links (code, `modules/affiliate/deeplink.py`): the pasted URL must be
`https`, have no userinfo, normalize punycode and case, match one of the program's `hosts` exactly or as
a subdomain, contain no nested redirect parameter, and be at most 2,000 characters; the path and the
trip's dates are the only parts used; the page is never fetched. A URL that fails validation produces
no partner button (the plain "Open" stays). `/go` still has no `url=` parameter.

Activation data. Each program moves `planned` to `applied` to `active` by an audited admin action; the
statements below show the end state once approved (run as admin changes, not as migrations; templates
need the values the network issues, written literally into the template text as in 07 section 8.2).

```sql
UPDATE affiliate_programs SET status = 'applied' WHERE code IN ('expedia_group', 'skyscanner', 'airalo', 'getyourguide_direct', 'booking_direct');

-- On approval (example for Expedia Group; ids come from the Impact account, never invented):
UPDATE affiliate_programs
   SET status = 'active', marker_or_id = '<impact account id>', commission_model = 'percent_of_booking',
       commission_note = 'Vrbo 2 to 6 percent, Hotels.com 6 to 16 percent, Expedia 2 to 12 percent (reported, verify)',
       terms_url = '<terms url read on approval>'
 WHERE code = 'expedia_group';

INSERT INTO affiliate_link_templates (program_id, kind, surface, variant, template, required_placeholders, active)
SELECT id, 'deeplink', 'lodging_shortlist', 'default',
       'https://<tracker>.sjv.io/c/<account>/<ad>/<program>?subId1={sub_id}&subId2={campaign}&u={dest_enc}',
       '{dest_enc,sub_id,campaign}', false                         -- enable after the link checker passes
  FROM affiliate_programs WHERE code = 'expedia_group'
ON CONFLICT DO NOTHING;

INSERT INTO affiliate_link_templates (program_id, kind, surface, variant, template, required_placeholders, active)
SELECT id, 'search', 'lodging_shortlist', 'default',
       'https://www.booking.com/searchresults.html?ss={dest_enc}&checkin={checkin}&checkout={checkout}&group_adults={guests}&aid={marker}&label={sub_id}',
       '{dest_enc,marker,sub_id}', false
  FROM affiliate_programs WHERE code = 'booking_direct'
ON CONFLICT DO NOTHING;
```

The angle-bracket values are placeholders for ids the network issues; replace them before inserting (the
`^https://[a-z0-9.-]+/` check rejects the placeholders). The Booking.com template is the illustrative row from 03 section 11.4; verify its parameters in the
network's link tool before enabling. Program `hosts` for the Expedia Group row are
`{vrbo.com,expedia.com,hotels.com}` (from the seed), Airalo `{airalo.com}`, Skyscanner `{skyscanner.com}`,
GetYourGuide `{getyourguide.com}`, AirHelp `{airhelp.com}`.

Experiment configuration (`feature_flags`, from the A/B queue in
[07 section 8.9](../reference-full-spec/07-monetization-spec.md)): Phase 1 seeds `affiliate_lodging_test` with variants
`{"travelpayouts":50,"stay22":50}`; once a direct lodging program is active an `UPDATE` makes them
`{"travelpayouts":34,"stay22":33,"direct":33}`; the metric is net
commission per click with cancellation and reversal rate as the guardrail. Sample size note: detecting a
3.0 percent to 3.6 percent lodging conversion needs about 20,000 clicks per arm, so early on test
click-through and treat bookings as a slow aggregate.

Environment variables (documented in `.env.example`, secrets only in the environment, never in the repo;
the `api_credentials_ref` column holds the variable name):

| Variable | Purpose |
|---|---|
| `IMPACT_ACCOUNT_SID`, `IMPACT_AUTH_TOKEN` | Impact Actions API (conversion import) |
| `IMPACT_WEBHOOK_SECRET` | HMAC for Impact postbacks |
| `IMPACT_EXPEDIA_TOKEN`, `IMPACT_SKYSCANNER_TOKEN`, `IMPACT_AIRALO_TOKEN` | Per program references named in the seed |
| `BOOKING_AFFILIATE_ID` | Booking.com direct id |
| `GETYOURGUIDE_PARTNER_ID` | GetYourGuide partner id |
| `AIRHELP_PARTNER_ID` | AirHelp partner id |

## 4. API additions

The outbound API and redirect are Phase 1 and are unchanged ([04 section 5.21](../reference-full-spec/04-api-spec.md)):
`POST /outbound`, `POST /shared/{token}/outbound`, `GET /go/{click_id}`, `GET /trips/{trip_id}/offers`,
`GET /affiliate/disclosure`. The changes are data and adapters, not new public routes.

- **`POST /outbound`**: accepts the new `entity_type` values already defined (`lodging_option`, `fare`,
  `checklist_item`, `thing_to_do`, `after_trip`) and, for a pasted stay link, builds the partner deep link
  from the saved URL text when a program for that host is `active` (AFF-1). Returns `404 not_found` when no
  program applies (the client then shows the plain link). Repeat clicks for the same entity and surface
  within 30 seconds return the same link; rate limit 60 an hour per user.
- **`GET /trips/{trip_id}/offers`**: `AffiliateOffer.partner` and `category` now include the new programs
  ("Book on Skyscanner", "Get an eSIM with Airalo", "Tickets on GetYourGuide"); `sorted_by` is always
  stated and never by commission; `extra_disclosure` carries the Booking.com line; `non_affiliate` carries
  "Search on the airline's site" and "Open your saved link".
- **`GET /affiliate/disclosure`**: the program list (`{name, category}`) and the booking line update
  automatically from `affiliate_programs` where `status = 'active'`.
- **`POST /webhooks/affiliate/impact`** ([04 section 6](../reference-full-spec/04-api-spec.md)): verifies the HMAC signature,
  writes `affiliate_conversions` upserted on `(program_id, network_txn_id)`, matches by sub-id
  (`subId1`), keeps a status history; an unmatched conversion is stored with `click_id = null` and counted
  toward the unmatched-share health metric. Postbacks are a supplement; the nightly pull is the source of
  truth. Unknown slugs return 404.
- **Admin API** ([08 section 8](../reference-full-spec/08-admin-control-center.md)): add `GET /affiliate/applications`,
  `POST /affiliate/applications`, `PATCH /affiliate/applications/{id}` (roles: owner and finance write;
  content read) and `POST /affiliate/programs/{code}/status` (owner only, two-person approval for
  `active`).

**Adapters** (`apps/api/hermi/modules/affiliate/adapters/`), each behind the provider interface and
logged in `provider_calls`:

| Adapter | Job | Source | Sub-id where it returns |
|---|---|---|---|
| Impact (`impact`) | `import_affiliate_conversions` for `expedia_group`, `skyscanner`, `airalo` | Impact Actions API | `subId1` |
| Booking.com direct | same job, only when its network is confirmed | The network's reporting API or Partner Center export (verify) | `label` |
| GetYourGuide direct | same job | Partner reporting or statistics export (verify) | campaign or partner sub-id (verify) |
| AirHelp | same job | Affiliate statistics export or postback (verify) | verify |

The nightly job runs per network, jittered, as an idempotent upsert that appends to `status_history`
(`pending`, `approved`, `rejected`, `paid`); a reversal or cancellation is stored as `rejected` with
`reversal_at`. USD figures are computed at read time with `fx_rates` at the event date. Job alerts: failed
import, zero rows for 3 days on a live program, reversed amounts above 25 percent of the month, redirect
4xx or 5xx above 1 percent, clicks down more than 50 percent day over day, a program approval rate under
60 percent.

## 5. UI screens and paywall triggers

No new screens. The changes are labels and partner names on existing surfaces from
[05 section 4.13](../reference-full-spec/05-ui-ux-spec.md) and [01 section 4.13](../reference-full-spec/01-product-spec.md):

- **Stays** (lodging cards): "Open" (the user's link, unchanged) and a separate "Book via partner" button
  for pasted Vrbo, Expedia, Hotels.com (and Booking.com direct when active) hosts, with the commission
  sentence and, for Booking.com, its mandated line; with no saved link, "Find on Booking, Vrbo or Agoda"
  labeled search links prefilled with destination, dates and guests. A "cheaper on <partner>" line only
  with real, dated price data.
- **Chosen flight card**: "Book on <provider>" options including Skyscanner, "Search on the airline's
  site", fare age and "price can change".
- **Checklist**: Airalo as the eSIM "Get it" button on international trips only.
- **Things to do and Today card**: GetYourGuide beside Viator, sorted by the user's own criteria.
- **Settings, How we earn money**: lists active partners by category and the ranking rule; the list grows
  as programs are approved; "Hide booking links" collapses buttons to "Open on partner site".
- **Offline and presentation**: no partner content offline; nothing during presentation playback; the
  optional "Book the plan" slide follows the same rules and labels.

Disclosure rules are unchanged: text, never color alone; VoiceOver reads the sentence in the same element
as the button; "Ad" tag on UK and EU storefronts. There is no paywall here, and partner cards never sit
beside an upsell or after a purchase moment.

## 6. Monetization and App Store products

No App Store products and no credits. Affiliate income is earned on every tier in the same places;
purchases through a partner never unlock app features and nothing is worded as if they do (Apple
Guideline 3.1.1). No advertising SDKs, no device ids: sub-ids are random per-click tokens, conversions are
pulled by our server, so the app stays outside App Tracking Transparency (note it in the review notes and
verify with Apple; Airalo's reported "tracked via Impact and Adjust" mobile attribution does not apply
because Hermi links out and uses server-side matching).

Expected impact (assumptions; replace with measured numbers when available):

| Lever | Reported rate | Effect |
|---|---|---|
| Vrbo and Hotels.com through Expedia Group (new route) | Vrbo $11 to $36 and Hotels.com 6 to 16 percent per booking | Adds a category Phase 1 could only link plainly |
| Booking.com direct versus Travelpayouts (4 percent, about $24) | 4 percent or a tiered share; net lodging commission $19 to $24 | About $0.73 per monthly user per year against $0.63 modeled in the sensitivity table ([08 affiliate revenue](../context/business-plan/08-affiliate-revenue.md) section 9), if approved |
| Skyscanner | GBP 0.07 to 0.30 per flight click | Small cash; the value is licensed fare data |
| Airalo | 10 to 12 percent, about $2 to $3 per sale | Small, clean tracking |
| GetYourGuide direct | about 8 percent | Replaces the aggregator rate on a share of tours |

Kill rule reminder: annualized affiliate income per monthly user under $0.20 at month 9 after launch
triggers the stop decision; Phase 2's exit review reports the trend ([README](README.md) section 7).

Compliance checklist per program before `active`: terms read and filed, app use and link-out confirmed in
writing where the terms are unclear, sub-id length and character rules confirmed, cashback and incentive
clauses checked (Hermi offers none), disclosure wording agreed, country and category restrictions set in
`countries_allowed` and `countries_blocked`, a test booking recorded, a kill switch tested.

## 7. Admin additions

From [08 section 6.7](../reference-full-spec/08-admin-control-center.md) (existing Phase 1 screen, extended):

- **Applications tab** (new): every program with its status, application history, submitted evidence
  (screenshots, traffic snapshot), terms notes, decision, next action date; buttons "Mark submitted",
  "Mark approved", "Mark rejected", "Pause program". Setting a program to `active` needs a second admin
  approval and writes `audit_log`.
- **Revenue views** include the new networks (Impact, direct) by program and placement, EPC by program
  and surface, click-to-booking days, the cash view (pending, approved, paid), the launch assumption next
  to the measured value, and a direct-versus-aggregator comparison for lodging.
- **Conversion import status** for each new adapter: last import, rows imported and changed, failures,
  unmatched share (alert above 10 percent).
- **Link checker**: new templates are checked against our own redirect (well-formed `Location` for a test
  click id) and a HEAD request to the partner's tracking domain only; Airbnb, Vrbo and Booking.com pages
  are never fetched and Airbnb is listed as "not checked by design". Editing a template needs two-person
  approval and stores the diff in `audit_log`.
- **Disclosure audit**: adds the new partner surfaces, the Booking.com line, the "Ad" label on UK and EU
  storefronts, and the "Hide booking links" behavior.
- **Experiments** (feature flags screen): the lodging partner test, the link-out container test and the
  disclosure wording test, with the existing guardrails (no experiment may hide or weaken a disclosure,
  rank by commission, or change what Free users see of cached fares).
- **Guardrail test**: a test fails the build if any code path that orders a list reads payout or
  commission fields (existing; extended to the new adapters).
- **Finance**: mark payouts received (`affiliate_payouts`), monthly reconciliation of paid rows against
  bank deposits, differences logged as `adjust` notes.

## 8. AI additions

None. Affiliate data stays out of AI: the model never sees clicks, conversions or partner information,
AI answers contain no partner names or links, and no affiliate card appears inside AI output. A test
asserts that no prompt builder imports the affiliate modules.

## 9. Analytics events

Existing events: `partner_card_viewed {program, placement, sponsored}`, `partner_link_tapped {program,
placement}`, `affiliate_conversion_imported {program, status}` (no amounts), `booking_links_hidden`.
The `placement` enum gains `after_trip` (pack 10) and `activity` already exists.

| Event | Properties | When fired |
|---|---|---|
| `book_via_partner_shown` | `program` (code), `host_category` (`vrbo`, `expedia`, `hotels_com`, `booking`) | The separate "Book via partner" button is shown (once per screen visit) |
| `partner_fallback_used` | `program`, `reason` (`kill_switch`, `expired_click`, `no_program`) | `/go` returned the plain destination (server side) |
| `affiliate_experiment_exposed` | `experiment`, `variant` | User assigned to an affiliate experiment cell (server side) |
| `program_status_changed` | `program`, `status` (`program_status`) | Admin changes a program's status (server side, no user id) |

## 10. Tests

- Redirect and templates: every new template renders a well-formed `Location`; `u={dest_enc}` accepted
  only for `deeplink` templates; `url`, `redirect` and `next` rejected; no `url=` parameter on `/go`;
  open-redirect attack tests (userinfo, nested redirects, punycode, other hosts, protocol-relative URLs).
- Destination validation: Vrbo, Expedia and Hotels.com host matching, subdomains, lookalike domains,
  Airbnb never wrapped, pasted links stay exactly as pasted in the "Open" button.
- Kill switches: per program and global; `/go` returns the plain destination; buttons disappear on the
  next fetch; expired or used click ids redirect to the plain destination; unknown ids 404 with an empty
  body.
- Disclosure: sentence beside every button, Booking.com line, "Ad" tag by storefront, VoiceOver same
  element; DOM and snapshot tests per surface; `hide_booking_links` collapses buttons.
- Ranking: list ordering code never reads commission or payout fields (build fails otherwise).
- Adapters: fixture tests for each network, idempotent upsert, status history, reversal, unmatched share
  calculation, HMAC signature and replay.
- Experiments: sticky assignment, one experiment per surface, guardrails reject disclosure changes.
- Offline and presentation: no partner content.
- Privacy: no user id, trip id or email in any outbound URL; `ip_hash` only; no advertising identifiers.
- Overlap: Viator and GetYourGuide on one item count one commission.
- E2E: paste a Vrbo link, see "Open" and "Book via partner", click through `/go`, see the click row,
  import a fixture conversion, see revenue by program.

## 11. Tickets

#### P2-075 Application packets and terms review [S, starts month 7, needs Phase 1 live and admin overview]
- Description: for Expedia Group, Booking.com, Skyscanner, Airalo, GetYourGuide and AirHelp prepare the
  packet: live app link, screenshots of the disclosure and each placement, traffic numbers exported from
  the admin overview, and read and file each program's terms (app use, link format, sub-id rules,
  cashback clauses).
- Accept: six packets ready in `docs/affiliate/applications/`; terms filed in `docs/affiliate/terms/`.

#### P2-076 Applications tracker and submission [S, needs P2-075]
- Description: migration `0024_direct_affiliate`, tracker table and admin tab, submit the applications
  (Booking.com only after confirming its current network), follow up weekly, record decisions.
- Accept: every application has a status and next action date; approvals move programs to `active` with
  two-person approval.
- Touches: `apps/api/hermi/modules/affiliate/`, `apps/web/src/routes/admin/affiliate/`.

#### P2-077 Impact adapter and conversion import [L, needs P2-076, Phase 1 conversion import]
- Description: Impact Actions API adapter, HMAC postback endpoint, sub-id matching (`subId1`), status
  history, unmatched health metric, alerts, `.env.example` entries.
- Accept: fixture tests pass; a test booking on a sandbox or approved account reaches
  `affiliate_conversions` matched to its click.

#### P2-078 Expedia Group, Vrbo and Hotels.com deep links [M, needs P2-077]
- Description: deep link templates with the relaxed constraint, destination validation, "Book via
  partner" for pasted hosts, prefilled search links, lodging experiment wiring, disclosure and "How we
  earn money" updates.
- Accept: pasted links are never rewritten; open-redirect tests pass; link checker green.

#### P2-079 Booking.com direct [M, needs P2-076]
- Description: confirm the current network, build the adapter or template set once approved, the
  mandated disclosure line, add as a variant of `affiliate_lodging_test`.
- Accept: disclosure line shown wherever its links appear; net commission per click reported against
  Travelpayouts and Stay22.

#### P2-080 Skyscanner links and licensed-fare evaluation [M, needs P2-077]
- Description: Skyscanner template for the chosen-flight card; in parallel evaluate the Skyscanner
  Partners licensed fare data as a live-fare provider behind the existing provider interface (terms,
  eligibility, cost) and write the decision memo.
- Accept: link live with one partner per surface per cell; memo records whether to replace or add to
  SerpApi.

#### P2-081 Airalo eSIM [S, needs P2-077, Phase 1 checklist]
- Description: eSIM "Get it" on international trips, hidden for domestic, link-out only, copy review.
- Accept: no in-app unlock wording; at least half of the checklist stays unmonetized.

#### P2-082 GetYourGuide direct and tours dedupe [M, needs P2-076]
- Description: direct templates and adapter, tours surface with Viator and the Travelpayouts program,
  overlap handling so one booking counts once.
- Accept: side-by-side labeled options; sorted by the user's criteria; no double counting.

#### P2-083 Reporting, link checker, experiments and runbook [M, needs P2-077]
- Description: revenue views for new programs, direct versus aggregator comparison, the admin link checker and
  two-person template approval that Phase 1 moved to Phase 2 ([08 section 6.7](../reference-full-spec/08-admin-control-center.md),
  roadmap WF-094 part), experiment setup for the lodging and container tests, alert rules, weekly review
  routine, program pause runbook.
- Accept: dashboards show measured EPC per program; alert rules fire in a drill.

## 12. Risks

| Risk | Mitigation |
|---|---|
| Applications rejected or slow (Skyscanner reported bar of 5,000 monthly uniques; Expedia case by case) | Apply early with real traffic and screenshots; Stay22 Link Swap is a second route to Vrbo; Travelpayouts rates remain the fallback |
| Booking.com network in flux (Awin arrangement reported ending) | Confirm the network in the Partner Center before applying; keep Travelpayouts Booking.com active |
| Disclosure or ranking failure | Tests in section 10, disclosure audit, no ranking test, per-program kill switches, no experiment may touch disclosure keys |
| Open redirect through the relaxed `u=` rule | Constraint only allows `u` on `deeplink` templates, host validation in code, no `url=` on `/go`, attack tests |
| Tracking breaks (unmatched conversions above 10 percent) | Alerts, nightly import plus postbacks, sub-id length rules checked per network |
| Two commissions for one booking | Attribution rule: count only the booked option |
| Policy churn (external links, ATT) | No attribution SDKs, server-side matching, review notes, re-read guidelines before each submission |
| Income below the kill-rule floor | Report trend in the Phase 2 exit; measured EPC replaces assumptions; decide with data at month 9 after launch |
