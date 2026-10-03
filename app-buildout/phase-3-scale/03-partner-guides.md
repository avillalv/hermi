# Pack 03: Partner guides

Part of [Phase 3: scale](README.md). Tickets P3-035 to P3-044. Written 2026-09-30.

| | |
|---|---|
| Feature flag | `partner_guides` (created by this pack, off) |
| Needs | Sales time (the real cost). A lawyer for a one-page sponsorship contract and disclosure terms (light review). An audience of about 50k MAU before the first paid deal. No funding, no engineering hire. |
| Builds on | Phase 1: admin console and audit log, affiliate system (`/go`), disclosure component, itinerary items, first-party analytics. |
| Source names | Phase 1 files call this "year 2 and later" and "Phase 4", ticket WF-106. Spec of record: [07 section 11.2 (full spec)](../reference-full-spec/07-monetization-spec.md), [08 section 6.10 (full spec)](../reference-full-spec/08-admin-control-center.md), [03 section 5.17 (full spec)](../reference-full-spec/03-database-schema.md), [04 section 5.22 (full spec)](../reference-full-spec/04-api-spec.md). |

## 1. Goal and revenue case

**Goal.** A clearly labeled "Partner guide" shelf: an official destination guide funded by a tourism board or hotel brand, with itinerary entries a traveler can copy into a trip. Every card says who sponsors it. Sponsors never appear in fare, stay or ranked results, cannot buy rank, cannot see user-level data, and users can hide the shelf. The product sells trust, so the rules matter more than the revenue (09 section 3.5).

**Price.** $5,000 to $8,000 per destination per quarter; the model uses $6,000 (base) and $8,000 (ambitious). Benchmarks (reported, verify): tourism-board creator campaigns run from EUR 1,000 to EUR 50,000; micro creator posts $250 to $2,500. Proof to sell with: measured copies into itineraries and saved trips.

**Revenue (from 09 sections 3.5 and 6.2).** A deal is one destination for one quarter; a renewal counts as a new deal.

| | Y2 | Y3 | Y4 | Y5 |
|---|---|---|---|---|
| Base deals | 0 (pilot) | 1 | 3 | 6 |
| Base revenue at $6,000 | 0 | $6k | $18k | $36k |
| Ambitious deals at $8,000 | 1 | 4 | 10 | 20 |
| Ambitious revenue | $8k | $32k | $80k | $160k |
| Conservative | 0 | 0 | 0 | 0 |

Worked: base year 5 is 6 x $6,000 = $36.0k. Ambitious year 5 is 20 x $8,000 = $160k (09 sums this with white-label in its "Partner guides and white-label" line).

**Costs.** About 1 paid deal per 15 to 25 pitches (assumption), so 6 deals a year needs 90 to 150 pitches. Design, editing and the monthly sponsor report add a few hours per deal. There is no engineering run cost beyond hosting. Card fees on invoices are about 3% if paid by card; invoicing by bank transfer avoids them.

**Constraint.** Sales cycles are the limit, and a paid deal needs an audience of about 50k MAU (09 section 3.5, "Starts"). Year 2 is a pilot: one free or discounted destination to prove copies and saves.

**User-experience impact.** Contained only if the shelf is separate, labeled and hideable. It is the easiest place in the product to lose the trust the product sells, so a rule is written into every contract: no paid placement in search or ranking.

## 2. Design decisions

| # | Decision | Default and reason |
|---|---|---|
| D1 | Where guides appear | A "Partner guides" section on destination pages (below the neutral destination content) and a Guides screen. Never in search, autosuggest, Discover cards, fare or stay lists, ranked lists, AI answers, push notifications, emails or share pages. Discover itself keeps "No partner cards" (05 section 6.23); it may link to Guides with one plain text row "Partner guides (sponsored)". |
| D2 | Label | "Partner guide" plus "Sponsored by {partner}" on every card and guide page, text not color only; "Ad" prefix on UK and EU storefronts. |
| D3 | AI never uses them | Agents never cite a guide, and guide text is never sent to a model. Copying an entry creates a normal item with attribution "From {guide}". |
| D4 | Data firewall | Sponsors get a monthly aggregate report (views, taps, copies, outbound clicks by country). No user-level data, ever. The app role cannot read sponsorship terms (03 section 6.1 column grants). |
| D5 | Two-person rule | The author cannot approve their own guide (constraint `ck_partner_guides_reviewer`); only the owner publishes. |
| D6 | Hideable | A setting "Hide partner guides" (`users.prefs.hide_partner_guides`) removes every guide surface for that user. Default on for nobody, off for everybody. |
| D7 | Sold outside the app | Flat-fee sponsorships invoiced through Stripe invoices or bank transfer; the invoice reference is stored on the guide (`sponsor_invoice_ref`). No in-app purchase. |

## 3. User stories and acceptance criteria

**G-1. Traveler reads a guide.**
As a traveler planning a trip to Lisbon, I want an official guide I can trust to be labeled, so that I know who paid for it.
- The destination page shows the shelf only when at least one published guide matches the destination and the user has not hidden guides.
- Card: cover, title, "Partner guide", "Sponsored by {partner}", and a disclosure line ("Sponsored guide. We earn a commission if you book here." only where the guide contains partner links; otherwise the guide's own `disclosure_text`).
- The guide page shows the label at the top, author, updated date, sections, sources and entries; "Hide partner guides" is one tap away.
- Order among guides is by recency, never by fee.

**G-2. Traveler copies an entry.**
As a traveler, I want to add a place from the guide to my trip, so that I do not retype it.
- "Add to my trip" on an entry opens the trip picker and creates an idea or item with `source = 'guide'`, attribution "From {guide}", coordinates and URL. No partner link is added to the item by the copy.
- Works offline only for already cached guides; queued otherwise.

**G-3. Traveler hides guides.**
As a traveler, I want to switch them off, so that I see none.
- Settings toggle; takes effect immediately on every surface; stored in `users.prefs`.

**G-4. Editor writes a guide.**
As a content editor, I want a structured editor and preview, so that guides look consistent and compliant.
- Blocks: overview, neighborhoods, sample days, practical notes, sources, entries (places with coordinates and URLs), images with alt text and credit, sponsor block, mandatory label field.
- Side-by-side preview in the app's guide layout; diff between versions.
- Cannot save a published guide without the label and a sponsor record.

**G-5. Reviewer approves.**
As the owner, I want a checklist before anything goes live, so that no guide breaks the rules.
- Checklist: label present, sources cited, no claim that AI wrote it, no insurance, visa or legal advice beyond official links, affiliate links labeled, no paid placement in search results, images licensed, copy matches the contract.
- Statuses: draft, in review, changes requested, approved, published, paused, archived. Publish schedules an end date from the sponsorship; pause hides immediately.

**G-6. Sponsor sees results.**
As a sponsor, I want a monthly report, so that I can see what I paid for.
- PDF and CSV with views, taps, entries copied into itineraries, saved trips containing a guide entry, outbound clicks through `/go` and top origin countries; the period and the method are stated; counts are aggregated with small-count suppression below 10.
- No user ids, emails or trip contents. The report says "Sponsorship does not affect ranking anywhere in Hermi."

**G-7. Founder runs the pilot.**
As the founder, I want a free pilot for one destination, so that I have numbers to sell with.
- One guide published for 90 days; the metrics above are visible in the admin console weekly; results are written up as a one-page case study before the first paid pitch.

## 4. Database additions

### 4.1 Defined in the full 03 (reuse verbatim)

03 section 5.17 defines `partner_guides`, with the review workflow and the sponsorship columns the app role cannot read. Phase 1 dropped the table (Phase 1 03 section 1.1) and Phase 2 does not create it, so this pack creates it. Apply 4.1 and 4.2 in one Alembic revision.

```sql
CREATE TABLE partner_guides (
  id                 uuid PRIMARY KEY DEFAULT uuidv7(),
  slug               text NOT NULL,
  title              text NOT NULL CHECK (char_length(title) BETWEEN 1 AND 160),
  summary            text NOT NULL DEFAULT '',
  destination_name   text NOT NULL,
  country_code       country_code2,
  lat                double precision,
  lon                double precision,
  partner_name       text NOT NULL,
  partner_url        text,
  program_id         uuid REFERENCES affiliate_programs (id) ON DELETE SET NULL,
  author_name        text NOT NULL,
  language           text NOT NULL DEFAULT 'en',
  body_md            text NOT NULL,
  entries            jsonb NOT NULL DEFAULT '[]'::jsonb,           -- places a reader can copy into an itinerary: [{"id", "title", "lat", "lon", "url"}] (04 5.22)
  cover_image_url    text,
  cover_attribution  text,
  is_sponsored       boolean NOT NULL DEFAULT true,
  disclosure_text    text NOT NULL DEFAULT 'Sponsored guide. We earn a commission if you book here.',
  status             text NOT NULL DEFAULT 'draft',                -- pausing a published guide sets it back to draft (review_state stays approved)
  review_state       text NOT NULL DEFAULT 'none',                 -- console workflow (08 6.10): none, in_review, changes_requested, approved
  reviewed_by        uuid REFERENCES users (id) ON DELETE SET NULL,   -- never the author
  reviewed_at        timestamptz,
  sponsor_starts_on  date,                                         -- sponsorship terms: finance only, never served to the app (column grants in 6.1)
  sponsor_ends_on    date,
  sponsor_fee_minor  bigint CHECK (sponsor_fee_minor IS NULL OR sponsor_fee_minor >= 0),
  sponsor_fee_currency currency_code,
  sponsor_invoice_ref text,                                        -- Stripe invoice id or bank reference; the invoice itself lives outside the app
  published_at       timestamptz,
  created_by         uuid REFERENCES users (id) ON DELETE SET NULL,
  version            integer NOT NULL DEFAULT 1,
  created_at         timestamptz NOT NULL DEFAULT now(),
  updated_at         timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_partner_guides_slug UNIQUE (slug),
  CONSTRAINT ck_partner_guides_status CHECK (status IN ('draft', 'published', 'archived')),
  CONSTRAINT ck_partner_guides_review CHECK (review_state IN ('none', 'in_review', 'changes_requested', 'approved')),
  CONSTRAINT ck_partner_guides_reviewed CHECK (status <> 'published' OR (review_state = 'approved' AND reviewed_by IS NOT NULL)),
  CONSTRAINT ck_partner_guides_reviewer CHECK (reviewed_by IS NULL OR reviewed_by IS DISTINCT FROM created_by),
  CONSTRAINT ck_partner_guides_sponsor_dates CHECK (sponsor_ends_on IS NULL OR sponsor_starts_on IS NULL OR sponsor_ends_on >= sponsor_starts_on),
  CONSTRAINT ck_partner_guides_sponsor_fee CHECK ((sponsor_fee_minor IS NULL) = (sponsor_fee_currency IS NULL)),
  CONSTRAINT ck_partner_guides_lat_lon CHECK ((lat IS NULL) = (lon IS NULL)),
  CONSTRAINT ck_partner_guides_published CHECK (status <> 'published' OR published_at IS NOT NULL),
  CONSTRAINT ck_partner_guides_disclosure CHECK (NOT is_sponsored OR char_length(disclosure_text) > 0)
);
CREATE INDEX ix_partner_guides_published ON partner_guides (country_code, published_at DESC) WHERE status = 'published';
SELECT add_version_trigger('partner_guides');
SELECT add_updated_at_trigger('partner_guides');
```

Grants and policy already in 03 sections 6.1 and 6.4 (the app sees published rows and only the non-sponsorship columns; the admin role writes):

```sql
-- Partner guides: the API reads published guides and never the sponsorship terms (finance data); the row policy in 6.4 limits it to status = 'published'.
REVOKE SELECT ON partner_guides FROM hermi_app;
GRANT SELECT (id, slug, title, summary, destination_name, country_code, lat, lon, partner_name, partner_url, program_id,
              author_name, language, body_md, entries, cover_image_url, cover_attribution, is_sponsored, disclosure_text,
              status, published_at, updated_at) ON partner_guides TO hermi_app;

-- Guides: the app sees published rows only (columns are limited by the grants above).
ALTER TABLE partner_guides ENABLE ROW LEVEL SECURITY;
CREATE POLICY partner_guides_published ON partner_guides FOR SELECT USING (status = 'published');
```

Flag and enum changes (Phase 1 seeds no later-phase flags; `itinerary_items.source` and `link_clicks.entity_type` gain the value `guide`, Phase 1 03 section 14):

```sql
INSERT INTO feature_flags (key, description, enabled, rollout_pct, rules, variants) VALUES
('partner_guides', 'Labeled partner guides', false, 100, '{}', '{}')
ON CONFLICT (key) DO NOTHING;
ALTER TABLE itinerary_items DROP CONSTRAINT ck_itinerary_items_source;
ALTER TABLE itinerary_items ADD CONSTRAINT ck_itinerary_items_source
  CHECK (source IN ('manual', 'place_search', 'ai_draft', 'agent', 'import', 'guide'));
-- link_clicks.entity_type is free text (Phase 1 03 section 5.15); add 'guide' to its comment and to OutboundIn.entity_type in the API schema.
```

### 4.2 New in this pack

```sql
-- Same Alembic revision as 4.1 (p3_partner_guides). New tables carry their own grants.

-- Version history for the admin diff view and the audit requirement (08 section 6.10: every publish writes before and after).
CREATE TABLE partner_guide_versions (
  id              uuid PRIMARY KEY DEFAULT uuidv7(),
  guide_id        uuid NOT NULL REFERENCES partner_guides (id) ON DELETE CASCADE,
  version         integer NOT NULL,
  title           text NOT NULL,
  summary         text NOT NULL DEFAULT '',
  body_md         text NOT NULL,
  entries         jsonb NOT NULL DEFAULT '[]'::jsonb,
  sources         jsonb NOT NULL DEFAULT '[]'::jsonb,        -- [{"label","url"}], required before review
  changed_by      uuid REFERENCES users (id) ON DELETE SET NULL,
  change_note     text NOT NULL DEFAULT '',
  created_at      timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_partner_guide_versions UNIQUE (guide_id, version)
);
REVOKE ALL ON partner_guide_versions FROM hermi_app;                         -- admin console only

ALTER TABLE partner_guides
  ADD COLUMN sources jsonb NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN review_checklist jsonb NOT NULL DEFAULT '{}'::jsonb,            -- the reviewer's ticked items, kept for the audit
  ADD CONSTRAINT ck_partner_guides_sources CHECK (jsonb_typeof(sources) = 'array');
-- Re-issue the app column grant to include sources (published rows only):
GRANT SELECT (sources) ON partner_guides TO hermi_app;

-- Aggregated, anonymous counters. No user id, no trip id, no device id: the sponsor report is built from this table only.
CREATE TABLE guide_metrics_daily (
  guide_id        uuid NOT NULL REFERENCES partner_guides (id) ON DELETE CASCADE,
  day             date NOT NULL,
  country_code    country_code2 NOT NULL DEFAULT 'ZZ',        -- from the request, 'ZZ' when unknown; suppressed below 10 in reports
  surface         text NOT NULL,                              -- 'destination_shelf', 'guides_screen', 'guide_page'
  impressions     integer NOT NULL DEFAULT 0,
  taps            integer NOT NULL DEFAULT 0,
  opens           integer NOT NULL DEFAULT 0,
  entries_copied  integer NOT NULL DEFAULT 0,
  outbound_clicks integer NOT NULL DEFAULT 0,
  PRIMARY KEY (guide_id, day, surface, country_code),
  CONSTRAINT ck_guide_metrics_surface CHECK (surface IN ('destination_shelf', 'guides_screen', 'guide_page'))
);
REVOKE ALL ON guide_metrics_daily FROM hermi_app;
-- The API bumps counters through one SECURITY DEFINER function, so the app role can neither read nor edit the table.
CREATE FUNCTION bump_guide_metric(p_guide uuid, p_surface text, p_country country_code2, p_field text) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
BEGIN
  IF p_field NOT IN ('impressions', 'taps', 'opens', 'entries_copied', 'outbound_clicks') THEN RAISE EXCEPTION 'bad_field'; END IF;
  IF NOT EXISTS (SELECT 1 FROM partner_guides WHERE id = p_guide AND status = 'published') THEN RETURN; END IF;
  EXECUTE format('INSERT INTO guide_metrics_daily (guide_id, day, surface, country_code, %1$I) VALUES ($1, CURRENT_DATE, $2, $3, 1)
                  ON CONFLICT (guide_id, day, surface, country_code) DO UPDATE SET %1$I = guide_metrics_daily.%1$I + 1', p_field)
    USING p_guide, p_surface, COALESCE(p_country, 'ZZ');
END $$;
REVOKE ALL ON FUNCTION bump_guide_metric(uuid, text, country_code2, text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION bump_guide_metric(uuid, text, country_code2, text) TO hermi_app;

CREATE TABLE sponsor_reports (
  id              uuid PRIMARY KEY DEFAULT uuidv7(),
  guide_id        uuid NOT NULL REFERENCES partner_guides (id) ON DELETE CASCADE,
  period_start    date NOT NULL,
  period_end      date NOT NULL,
  summary         jsonb NOT NULL,                              -- the numbers shown in the report
  pdf_key         text,                                        -- R2 object key
  sent_at         timestamptz,
  sent_to         text,
  created_at      timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_sponsor_reports_period UNIQUE (guide_id, period_start, period_end),
  CONSTRAINT ck_sponsor_reports_period CHECK (period_end >= period_start)
);
REVOKE ALL ON sponsor_reports FROM hermi_app;
```

User preference `hide_partner_guides` lives in `users.prefs` (no column). Retention: `guide_metrics_daily` 25 months (same as `link_clicks`); `sponsor_reports` 7 years with the contract; versions kept with the guide.

## 5. API additions

Base `/v1`, behind the `partner_guides` flag. Reads extend [04 section 5.22 (full spec)](../reference-full-spec/04-api-spec.md); authoring is admin-only.

| Endpoint | Auth | Gate and cost | Request and response | Errors and side effects |
|---|---|---|---|---|
| `GET /partner-guides` | user | flag; empty when the user hides guides | `?destination=&country=&limit&cursor` to `Page<GuideSummary>` | Sorted by recency, never by fee. Never included in any search or suggest route (test). |
| `GET /partner-guides/{slug}` | user | flag | to `Guide` | `Cache-Control: private, max-age=300`. Sanitized markdown. |
| `POST /trips/{trip_id}/items/from-guide` | editor | none | `{ guide_slug, entry_id }` to 201 `Item` | Copies the entry (source `guide`, attribution). Increments `entries_copied`. |
| `POST /partner-guides/{slug}/events` | user | 120 an hour per user | `{ event: "impression" \| "tap" \| "open" \| "outbound", surface }` to 204 | Calls `bump_guide_metric()` (no user id kept). Ignored when the guide is not published. |
| `PATCH /me/settings` | user | none | `{ hide_partner_guides?: boolean }` | Writes `users.prefs`. |

```ts
type GuideSummary = { slug: string; title: string; destination_name: string; partner_name: string; cover_image_url: string | null
  label: "Partner guide"; sponsored_by: string; disclosure: string }
type Guide = GuideSummary & { body_md: string; sources: { label: string; url: string }[]
  entries: { id: string; title: string; lat: number | null; lon: number | null; url: string | null }[]; updated_at: string }
```

Admin API ([08 section 8](../phase-1-launch/08-admin-control-center.md), under `/v1/admin`): `GET /guides`, `POST /guides`, `PUT /guides/{id}`, `POST /guides/{id}/submit`, `POST /guides/{id}/review` (owner or a second admin, never the author), `POST /guides/{id}/publish` (owner, step-up 2FA, schedules the end date, publish or pause), plus new `GET /guides/{id}/versions`, `GET /guides/{id}/diff?from=&to=`, `GET /guides/{id}/metrics`, `POST /guides/{id}/sponsor-report` (generate and send), `PUT /guides/{id}/sponsorship` (finance only). Every mutating call needs a reason and writes `audit_log` with before and after content.

Jobs (02 section 5.1 pattern, scheduler-enqueued): `expire_guides` (daily: archive guides whose `sponsor_ends_on` has passed, alert 14 days before), `build_sponsor_reports` (monthly, first business day), `purge_guide_metrics` (nightly, 25 months).

## 6. UI screens

**Destination page: Partner guides section.** Purpose: show labeled guides where the traveler is already reading about a place. Layout: below the neutral content, a section titled "Partner guides" with a one-line explainer ("Sponsored guides from tourism boards and hotel brands. They never change how we rank anything.") and up to 3 cards in a horizontal list. Card: cover (with attribution), title, destination, "Sponsored by {partner}" as text, and "Hide partner guides" in an overflow menu. States: no guide, no section; loading skeleton; offline cached cards only; hidden by the user, no section. Accessibility: the label and sponsor are read as part of the card name before the title.

**Guides screen.** Reached from the destination section and from the Discover text row. List of published guides by recency with a country filter; every row labeled; a footer link "How we earn money". Empty: "No partner guides right now." Events: `guide_shelf_viewed {surface}`, `guide_opened`, `guide_entry_copied`, `guides_hidden`.

**Guide page.** Sticky label bar "Partner guide, sponsored by {partner}", title, cover, author and date, sections, entries with "Add to my trip", sources list, disclosure text, report link, "Hide partner guides". Partner links inside the guide go through `/go/{click_id}` with the standard disclosure sentence beside each button and `entity_type = 'guide'`.

**Add to my trip.** The normal trip picker sheet with the entry prefilled and the attribution line "From {guide}".

**Settings row.** "Hide partner guides" toggle under Settings, next to "Hide booking links".

**Admin editor** (08 section 6.10): blocks editor, sources list, image alt text and credit fields, sponsor block, mandatory label field rendering "Sponsored guide from {sponsor}", side-by-side preview, version diff, review checklist with ticks stored in `review_checklist`, workflow buttons, expiry indicator, metrics tab (views, taps, copies, clicks, countries). Finance tab (finance and owner only) shows sponsorship terms and invoice reference.

States, tokens and copy follow [05](../phase-1-launch/05-ui-ux-spec.md): sentence case, no em dashes, no urgency, label as text.

## 7. Billing

- **No in-app billing.** Sponsorships are flat fees per destination per quarter, agreed by contract and invoiced outside the app (Stripe invoices or bank transfer). Invoice reference in `partner_guides.sponsor_invoice_ref`; fee and dates in the finance-only sponsorship columns.
- **Payment terms.** Pay in advance for the quarter; publish when the invoice is marked paid (finance action) and the reviewer has approved. No refunds once published; a pause with pro-rata credit if the guide is removed for a policy reason the sponsor caused is decided by contract.
- **Revenue reporting.** Finance reports list sponsorship revenue by guide and quarter and deferred revenue across the period; the owner sees renewals due in 30 days.
- **Affiliate links inside guides** earn like any other partner link and are reported under the guide's `program_id` and `entity_type = 'guide'`; they never change order or content.
- **Tax.** Invoices for a business customer; VAT or sales tax handled through Stripe Tax or the accountant (verify).

## 8. Admin additions

Extends [08 section 6.10 (full spec)](../reference-full-spec/08-admin-control-center.md) (source ticket WF-106). Screens: Guides list (status, sponsor, destination, expiry, review state), editor, versions and diff, metrics, sponsor reports, finance tab. Roles: `content` edits and submits, a different admin reviews, the owner approves and publishes (08 section 3), finance edits sponsorship terms. Permissions: `guides.edit`, `guides.review`, `guides.publish`, `guides.sponsorship.write`, `guides.report.send`; the route-permission test covers them. Alerts: a guide expires in 14 days (notify), a published guide lacks a label or sources (page), any guide appears in a search or ranked response in the nightly audit (page), sponsor report unsent after the 5th (notify). Kill switch: `partner_guides` flag off hides every surface at once.

## 9. Legal and compliance

1. **Advertising disclosure.** US: FTC endorsement rules (16 CFR Part 255) require a clear, adjacent disclosure; the label sits in the card and the page. UK: "Ad" on the card (ASA and CMA). EU: commercial intent and paid placement are material information; every list states its ordering basis (here: recency) and that payment plays no part. The rules are already collected in [08-affiliate-revenue.md section 7.4](../context/business-plan/08-affiliate-revenue.md).
2. **Contract terms (one page, counsel reviews once).** No ranking influence anywhere; Hermi's editorial control over what publishes; sponsor supplies or approves facts but cannot edit the label; no user-level data; aggregate reporting only; term and end date; fees and invoicing; removal for policy breach; sponsor warrants licences for images and claims.
3. **Accuracy and claims.** The reviewer checks claims against sources; no health, safety, visa or insurance advice beyond official links; no claim that AI wrote a guide.
4. **Images.** Licensed or supplied with written permission; credit shown; alt text required.
5. **Privacy.** Guide views are not tied to a user; the metrics table has no user id; the privacy policy says guide engagement is counted in aggregate. No sponsor pixels or third-party scripts on guide pages (CSP already blocks them).
6. **App Review.** Guides are content, not digital goods; labeled, hideable and outside search. Mention in reviewer notes.
7. **Security.** Markdown is sanitized through the single DOMPurify component ([10 section 2.1 V5](../phase-1-launch/10-quality-security-launch.md)); image URLs are served from our storage, not hotlinked; editor links are checked with the existing outbound validation.
8. **No ranking by commission.** Non-negotiable rule 2 in the README; this pack adds tests (section 11) so it cannot regress.

## 10. Analytics

Events: `guide_shelf_viewed {surface}`, `guide_card_tapped`, `guide_opened`, `guide_entry_copied {category}`, `guide_outbound_clicked`, `guides_hidden`, `guides_unhidden`. They feed `guide_metrics_daily` (no user id) and PostHog (no guide-specific user profile beyond the normal event user).

Metrics for selling and for trust: entries copied per 1,000 views, taps per impression, saved trips containing a guide entry, outbound click rate, hide rate (alert above 5% of viewers in a week: the shelf is annoying), complaint count. Pilot targets to write into the case study are set after the first 30 days; the pitch uses measured figures only.

## 11. Tests

- **Never in search or ranks (the key test).** A crawl of every list, search, suggest, offers, Discover and AI endpoint with published guides present asserts no guide id, slug or sponsor appears; a snapshot test of Discover asserts no partner card; AI tool outputs never include guide text.
- **Label.** Component test: no card or page renders without label and sponsor text; the publish guard rejects a guide with an empty label; UK and EU variant shows "Ad".
- **Workflow.** Author cannot approve (constraint plus API test); publish needs approved state, reviewer and `published_at`; pause hides at once; expiry job archives after `sponsor_ends_on`.
- **Grants.** The app role cannot select sponsorship columns or the new tables, and can change metrics only through `bump_guide_metric()` (direct attempts fail); published-only row policy holds; drafts are invisible.
- **Metrics.** Counters are anonymous (no user id columns), suppressed below 10 in reports, and a sponsor report never contains user-level data.
- **Sanitization.** Script, iframe, event handler and `javascript:` payloads in `body_md` are stripped.
- **Hide setting.** With `hide_partner_guides` true every surface and `GET /partner-guides` return empty.
- **Copy.** From-guide creates an item with attribution and no partner link; idempotency on repeated taps.

## 12. Tickets

| ID | Title | Size | Needs | Who |
|---|---|---|---|---|
| P3-035 | Sales kit and contract: one-page rate card, pilot offer, sponsorship contract and disclosure terms (lawyer review), target list of 100 destinations and boards | M | none | Founder, lawyer |
| P3-036 | Schema additions (4.2): versions, sources, review checklist, daily metrics, sponsor reports, grants | S | none | Engineer |
| P3-037 | Admin guide editor: blocks, sources, images with alt text, label field, preview, versions and diff | L | P3-036 | Engineer |
| P3-038 | Review and publish workflow: checklist, two-person rule, scheduled end date, pause, audit before and after, alerts | M | P3-037 | Engineer |
| P3-039 | App surfaces: destination shelf, Guides screen, guide page, hide setting, label component, `/go` links with disclosure | L | P3-036 | Engineer |
| P3-040 | Copy entry into a trip with attribution; offline cache of opened guides | S | P3-039 | Engineer |
| P3-041 | Never-in-search enforcement: route audit, nightly audit job, snapshot and AI-output tests | M | P3-039 | Engineer |
| P3-042 | Metrics and sponsor reports: event endpoint, daily counters, monthly report job, PDF and CSV, small-count suppression | M | P3-039 | Engineer |
| P3-043 | Sponsorship billing flow: invoice reference, finance tab, expiry job and 14-day alert, revenue report lines | S | P3-038 | Engineer, bookkeeper |
| P3-044 | Pilot and first sale: one free destination for 90 days, one-page case study, 90 to 150 pitches for the first 6 deals, flag on | M | P3-035, P3-041, P3-042 | Founder |

## 13. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Sales cycles too slow (1 deal per 15 to 25 pitches) | High | Medium | Start the pilot in year 2, write the case study, treat revenue as upside until 50k MAU |
| A sponsor asks for placement or data | Medium | High | Contract clause, firewall by design (no user data in the table), walk away |
| Trust loss from perceived ads | Medium | High | Separate labeled shelf, hide setting, hide-rate alert, never in search or AI, never pushed |
| Legal exposure for false claims in a guide | Low | Medium | Source-checked review, sponsor warranties, removal right |
| Low audience makes the numbers weak | Medium | Medium | Gate on about 50k MAU for paid deals; pilot for learning only |
| Regression lets a guide reach search or an AI answer | Low | High | Tests in section 11 run in CI; nightly audit pages the owner |
| Editorial workload (a few hours per deal) | Medium | Low | Templates, sponsor supplies facts, reports are generated |
