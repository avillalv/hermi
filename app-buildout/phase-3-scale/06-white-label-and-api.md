# Pack 06: White-label and API

Part of [Phase 3: scale](README.md). Tickets P3-071 to P3-081. Written 2026-09-30.

| | |
|---|---|
| Feature flags | `white_label` and `partner_api` (created by this pack, off). Both need `advisor_workspaces` on. |
| Needs | A lawyer (master agreement, data-processing addendum, child-data rules before any school operator). An onboarding and support person: support per account is the real cost. A contractor engineer is sensible for custom domains. No funding. |
| Builds on | **Pack 02 must be stable first** ([02-hermi-for-advisors.md](02-hermi-for-advisors.md)): this is the same code packaged for accounts rather than seats (09 section 3.7). Phase 1: presentation mode, share links, Resend, Cloudflare, Stripe webhook endpoint. |
| Source names | Phase 1 files call this "year 3 and later". Spec of record: [07 section 11.5 (full spec)](../reference-full-spec/07-monetization-spec.md), which specifies only a direction ("a separate tenancy, API keys, annual contracts invoiced by Stripe"). This pack is the detailed contract. |

## 1. Goal and revenue case

**Goal.** License the planner, presentation mode and group workspace to agencies and tour operators with their branding and their domain, and give them an API for the parts they want inside their own systems. A white-label account is a Hermi for Advisors organization with an account-level contract instead of per-seat billing.

**Price.** $500 a month per account ($6,000 a year); the ambitious case uses the same price (09 section 3.7). Assumptions to set in the contract template (P3-071): up to 10 staff seats included, extra seats at the advisor seat price ($29 a month), one custom domain, API included with rate limits. A paid API is the same packaging and adds nothing to the revenue totals.

**Revenue.**

| Accounts | Y2 | Y3 | Y4 | Y5 |
|---|---|---|---|---|
| Conservative | 0 | 0 | 0 | 0 |
| Base | 0 | 1 | 3 | 6 |
| Ambitious | 1 | 4 | 10 | 20 |
| Base revenue at $6,000 | 0 | $6k | $18k | $36k |
| Ambitious revenue | $6k | $24k | $60k | $120k |

Worked: base year 5 is 6 x $6,000 = $36.0k. One account equals about 19 advisor seats ($6,000 / $314.28 net per seat). 09 groups this line with partner guides as "Partner guides and white-label" ($72.0k base year 5).

**Costs and effort.** Medium build (multi-brand theming, custom domain, data-processing agreement, onboarding). Per-account support is the real cost: budget a few hours a week for each new account in its first 90 days (assumption). Do not start before the advisor product is stable.

**What would break the case.** Few buyers (base case needs 6 accounts in year 5), long sales cycles, custom feature requests that turn a license into a consulting business, and a multi-tenant security incident.

**Entry gate (assumptions to tune).** Hermi for Advisors live at least 6 months with at least 40 paid seats and no severity-1 tenancy incident, and at least 3 qualified inbound requests with a stated budget of $6,000 a year or more.

## 2. Design decisions

| # | Decision | Default and reason |
|---|---|---|
| D1 | Same tenancy as advisors | A white-label account is an `advisor_orgs` row with `kind = 'white_label'`. Same RLS, seats, clients, proposals and commission tracker; different billing (account contract) and brand reach. No second data model. |
| D2 | Version 1 scope of branding | Branded client-facing surfaces on the customer's domain: share pages, presentation, proposals, client portal by emailed link, and branded emails. Staff sign in at Hermi's advisor domain as in pack 02. Full sign-in on the customer's domain (auth redirect allow-lists, cookie scope) is deferred until a signed customer needs it, because it multiplies identity risk. |
| D3 | Disclosure cannot be branded away | Required disclosures stay: partner-link commission sentence, AI-source labels, privacy and terms links. The "Made with Hermi" footer can be removed. |
| D4 | Partner links default off | On white-label surfaces affiliate links are off unless the contract turns them on; if on, commissions follow the contract and the disclosure sentence stays. Decide the default in P3-071. |
| D5 | API acts as an org principal | Each API client belongs to one org and acts as an org admin seat (`acts_as_user_id`) with scopes; its keys inherit the same row-level security as that seat. A client is suspended when its admin seat ends. |
| D6 | No school operators until cleared | Child data (COPPA, FERPA) is a gate (P3-080); no account type for schools before counsel signs off. |
| D7 | Minimal service levels | Target 99.5% monthly availability stated as a goal, no credits, response times by plan in the contract (09 section 3.7: service-level promises kept minimal). |

## 3. User stories and acceptance criteria

**W-1. Operator onboarding.**
As an agency owner, I want my brand and domain set up with help, so that clients see my product.
- After contract signature an owner creates the org (kind `white_label`), uploads logo and favicon, picks colors (AA contrast enforced), picks a font from the allow-list, sets contact line, legal links, email sender name and reply-to.
- A preview page shows a sample trip, proposal and share page in the brand before anything is public.

**W-2. Custom domain.**
As an agency owner, I want `trips.myagency.com` to show my client pages, so that Hermi is invisible.
- I enter the hostname; the app shows the exact DNS records to add (CNAME and a verification TXT); status moves pending, verifying, active; TLS is issued automatically; failures show the reason and the fix.
- Only that org's public pages are served on the hostname; staff screens are not. The hostname can be removed at any time and stops serving at once.

**W-3. Branded client experience.**
As a client of the agency, I want a clean branded page, so that I trust it.
- Share pages, presentation mode, proposals and the client portal render with the org's logo, colors, fonts and contact line, on the org's domain, without Hermi branding except required disclosures and legal links.
- Emails (invites, proposal sent, reminders) come from the agency's sender name and a verified sending domain when configured, else from Hermi with the agency name.

**W-4. API keys.**
As a developer at the agency, I want keys with limited scopes, so that my system can read and write trips safely.
- Org admins create a named API client with scopes, then issue keys for it (two active at once to allow rotation); each secret is shown once; only a hash and a short prefix are stored; keys can be revoked; last-used time is visible.

**W-5. Use the API.**
As a developer, I want a documented REST API for clients, trips, items, share links and proposals, so that I can integrate.
- Bearer auth with the key; JSON; pagination, idempotency keys and problem+json errors as in the consumer API; rate limit headers; an OpenAPI document and example requests.
- Writes respect the same validation, limits and audit as the app; a key can never read another org's data.

**W-6. Account billing.**
As an agency owner, I want an annual invoice, so that procurement is simple.
- Contract terms recorded (fee, term, seats included, domains, API limits); Stripe invoice or subscription; renewal notice 60 days before the end; payment by card or bank transfer; usage against included seats and keys visible.

**W-7. Offboarding.**
As an agency owner, I want my data back if I leave, so that I am not locked in.
- Org export at any time (clients, trips, proposals, bookings) in JSON and CSV; on termination the account goes read-only for 30 days, then the custom domain stops and data is deleted on request after export (retention per 03 section 8).

## 4. Database additions

### 4.1 Already defined in 03 (reuse)

`advisor_orgs` and `advisor_seats` (03 section 5.19, pack 02 section 4.1) are the base. Apply the block below only if pack 02 has not created them.

```sql
CREATE TABLE advisor_orgs (
  id                       uuid PRIMARY KEY DEFAULT uuidv7(),
  name                     text NOT NULL CHECK (char_length(name) BETWEEN 1 AND 120),
  slug                     text NOT NULL,
  owner_user_id            uuid REFERENCES users (id) ON DELETE SET NULL,
  host_agency_name         text,
  host_agency_id           text,                                      -- IATAN or CLIA number of the host agency, when supplied
  billing_email            citext,
  stripe_customer_id       text,
  brand                    jsonb NOT NULL DEFAULT '{}'::jsonb,        -- logo key, colors, contact line for branded presentations
  commission_split_bps     integer NOT NULL DEFAULT 0 CHECK (commission_split_bps BETWEEN 0 AND 10000),
  status                   text NOT NULL DEFAULT 'active',
  created_at               timestamptz NOT NULL DEFAULT now(),
  updated_at               timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_advisor_orgs_slug UNIQUE (slug),
  CONSTRAINT ck_advisor_orgs_status CHECK (status IN ('active', 'suspended', 'closed'))
);
CREATE UNIQUE INDEX uq_advisor_orgs_stripe_customer ON advisor_orgs (stripe_customer_id) WHERE stripe_customer_id IS NOT NULL;
SELECT add_updated_at_trigger('advisor_orgs');

ALTER TABLE concierge_requests ADD CONSTRAINT fk_concierge_requests_advisor_org_id_advisor_orgs
  FOREIGN KEY (advisor_org_id) REFERENCES advisor_orgs (id) ON DELETE SET NULL;

CREATE TABLE advisor_seats (
  id                        uuid PRIMARY KEY DEFAULT uuidv7(),
  advisor_org_id            uuid NOT NULL REFERENCES advisor_orgs (id) ON DELETE CASCADE,
  user_id                   uuid REFERENCES users (id) ON DELETE CASCADE,         -- null while an invite is pending
  invited_email             citext,
  role                      text NOT NULL DEFAULT 'advisor',
  billing_period            text NOT NULL DEFAULT 'month',
  stripe_subscription_id    text,
  stripe_subscription_item_id text,
  status                    text NOT NULL DEFAULT 'active',
  started_at                timestamptz NOT NULL DEFAULT now(),
  ended_at                  timestamptz,
  created_at                timestamptz NOT NULL DEFAULT now(),
  updated_at                timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_advisor_seats_role CHECK (role IN ('admin', 'advisor')),
  CONSTRAINT ck_advisor_seats_period CHECK (billing_period IN ('month', 'year')),
  CONSTRAINT ck_advisor_seats_status CHECK (status IN ('invited', 'active', 'past_due', 'ended')),
  CONSTRAINT ck_advisor_seats_user_or_email CHECK (user_id IS NOT NULL OR invited_email IS NOT NULL)
);
CREATE UNIQUE INDEX uq_advisor_seats_org_user ON advisor_seats (advisor_org_id, user_id) WHERE user_id IS NOT NULL AND status <> 'ended';
CREATE INDEX ix_advisor_seats_user ON advisor_seats (user_id) WHERE user_id IS NOT NULL;
SELECT add_updated_at_trigger('advisor_seats');
```

### 4.2 New in this pack

```sql
-- Migration p3_white_label. New tables carry their own grants and policies (Phase 1 03 section 10). Pack 02's helpers my_advisor_orgs() and my_writable_advisor_orgs() are reused.

ALTER TABLE advisor_orgs
  ADD COLUMN kind          text NOT NULL DEFAULT 'advisor',
  ADD COLUMN seats_included smallint,                                   -- white_label: seats covered by the account fee
  ADD CONSTRAINT ck_advisor_orgs_kind CHECK (kind IN ('advisor', 'white_label'));
-- brand (existing jsonb) gains: {"logo_key", "favicon_key", "primary", "secondary", "font": "<allow-list key>", "contact_line",
--   "legal_terms_url", "legal_privacy_url", "email_from_name", "reply_to", "hide_hermi_footer": true, "partner_links": false}

CREATE TABLE white_label_contracts (
  id                    uuid PRIMARY KEY DEFAULT uuidv7(),
  advisor_org_id        uuid NOT NULL REFERENCES advisor_orgs (id) ON DELETE CASCADE,
  plan                  text NOT NULL DEFAULT 'annual',
  fee_minor             bigint NOT NULL CHECK (fee_minor >= 0),                 -- per period: 600000 a year or 50000 a month
  currency              currency_code NOT NULL DEFAULT 'USD',
  seats_included        smallint NOT NULL DEFAULT 10,
  domains_included      smallint NOT NULL DEFAULT 1,
  api_rate_limit_per_min integer NOT NULL DEFAULT 120,
  partner_links         boolean NOT NULL DEFAULT false,
  starts_on             date NOT NULL,
  ends_on               date NOT NULL,
  auto_renew            boolean NOT NULL DEFAULT true,
  status                text NOT NULL DEFAULT 'active',
  stripe_subscription_id text,
  stripe_invoice_ref    text,
  msa_version           text NOT NULL,
  dpa_signed_at         timestamptz NOT NULL,
  school_operator       boolean NOT NULL DEFAULT false,                        -- true only after the P3-080 gate
  notes                 text NOT NULL DEFAULT '',
  created_at            timestamptz NOT NULL DEFAULT now(),
  updated_at            timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_white_label_contracts_plan CHECK (plan IN ('annual', 'monthly')),
  CONSTRAINT ck_white_label_contracts_status CHECK (status IN ('draft', 'active', 'past_due', 'ended')),
  CONSTRAINT ck_white_label_contracts_term CHECK (ends_on > starts_on)
);
CREATE INDEX ix_white_label_contracts_org ON white_label_contracts (advisor_org_id, status);
CREATE INDEX ix_white_label_contracts_renewal ON white_label_contracts (ends_on) WHERE status = 'active';
SELECT add_updated_at_trigger('white_label_contracts');
REVOKE ALL ON white_label_contracts FROM hermi_app;                           -- admin and billing only

CREATE TABLE org_domains (
  id                     uuid PRIMARY KEY DEFAULT uuidv7(),
  advisor_org_id         uuid NOT NULL REFERENCES advisor_orgs (id) ON DELETE CASCADE,
  hostname               citext NOT NULL,
  purpose                text NOT NULL DEFAULT 'web',                          -- 'web' (client pages) or 'email' (sending domain)
  status                 text NOT NULL DEFAULT 'pending',
  cloudflare_hostname_id text,
  email_domain_id        text,                                                  -- Resend domain id for purpose 'email'
  dns_records            jsonb NOT NULL DEFAULT '[]'::jsonb,                    -- records the owner must add
  ssl_status             text,
  last_error             text,
  verified_at            timestamptz,
  last_checked_at        timestamptz,
  created_at             timestamptz NOT NULL DEFAULT now(),
  updated_at             timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_org_domains_hostname UNIQUE (hostname),
  CONSTRAINT ck_org_domains_purpose CHECK (purpose IN ('web', 'email')),
  CONSTRAINT ck_org_domains_status CHECK (status IN ('pending', 'verifying', 'active', 'failed', 'removed')),
  CONSTRAINT ck_org_domains_hostname CHECK (hostname ~ '^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$')
);
CREATE INDEX ix_org_domains_org ON org_domains (advisor_org_id, status);
CREATE INDEX ix_org_domains_active ON org_domains (hostname) WHERE status = 'active' AND purpose = 'web';
SELECT add_updated_at_trigger('org_domains');

-- Phase 1 03 section 14 names `api_clients` and `api_keys`: a client is the integration (scopes, rate limit, acting seat); keys are its credentials, so a key can rotate without changing the client.
CREATE TABLE api_clients (
  id                 uuid PRIMARY KEY DEFAULT uuidv7(),
  advisor_org_id     uuid NOT NULL REFERENCES advisor_orgs (id) ON DELETE CASCADE,
  acts_as_user_id    uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,        -- an org admin seat holder (D5)
  name               text NOT NULL CHECK (char_length(name) BETWEEN 1 AND 80),
  scopes             text[] NOT NULL,
  rate_limit_per_min integer NOT NULL DEFAULT 120 CHECK (rate_limit_per_min BETWEEN 1 AND 6000),
  status             text NOT NULL DEFAULT 'active',
  created_by         uuid REFERENCES users (id) ON DELETE SET NULL,
  created_at         timestamptz NOT NULL DEFAULT now(),
  updated_at         timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_api_clients_status CHECK (status IN ('active', 'suspended', 'revoked')),
  CONSTRAINT ck_api_clients_scopes CHECK (scopes <@ ARRAY['clients:read', 'clients:write', 'trips:read', 'trips:write', 'items:write',
                                                          'shares:write', 'proposals:read', 'bookings:read']::text[] AND cardinality(scopes) > 0)
);
CREATE INDEX ix_api_clients_org ON api_clients (advisor_org_id) WHERE status = 'active';
SELECT add_updated_at_trigger('api_clients');
REVOKE ALL ON api_clients FROM hermi_app;

CREATE TABLE api_keys (
  id              uuid PRIMARY KEY DEFAULT uuidv7(),
  api_client_id   uuid NOT NULL REFERENCES api_clients (id) ON DELETE CASCADE,
  prefix          text NOT NULL,                                                   -- first characters, shown in the UI and logs
  key_hash        bytea NOT NULL,                                                  -- SHA-256 of a 32-byte random secret; the secret is shown once
  last_used_at    timestamptz,
  expires_at      timestamptz,
  revoked_at      timestamptz,
  created_at      timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_api_keys_hash UNIQUE (key_hash),
  CONSTRAINT uq_api_keys_prefix UNIQUE (prefix)
);
CREATE INDEX ix_api_keys_client ON api_keys (api_client_id) WHERE revoked_at IS NULL;
REVOKE ALL ON api_keys FROM hermi_app;                                          -- the API process looks keys up through the function below only
CREATE FUNCTION api_key_lookup(p_prefix text)
RETURNS TABLE (key_id uuid, api_client_id uuid, advisor_org_id uuid, acts_as_user_id uuid, key_hash bytea, scopes text[], rate_limit_per_min integer)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT k.id, c.id, c.advisor_org_id, c.acts_as_user_id, k.key_hash, c.scopes, c.rate_limit_per_min
    FROM api_keys k
    JOIN api_clients c ON c.id = k.api_client_id AND c.status = 'active'
    JOIN advisor_orgs o ON o.id = c.advisor_org_id AND o.status = 'active'
   WHERE k.prefix = p_prefix AND k.revoked_at IS NULL AND (k.expires_at IS NULL OR k.expires_at > now())
$$;
REVOKE ALL ON FUNCTION api_key_lookup(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION api_key_lookup(text) TO hermi_app;

-- Request rate limits reuse the Phase 1 Postgres-backed rate_limit_counters with one bucket per key ('api:<key id>').
-- This table is reporting only (usage charts, billing conversations).
CREATE TABLE api_usage_daily (
  api_client_id  uuid NOT NULL REFERENCES api_clients (id) ON DELETE CASCADE,
  day            date NOT NULL,
  requests       integer NOT NULL DEFAULT 0,
  errors         integer NOT NULL DEFAULT 0,
  rate_limited   integer NOT NULL DEFAULT 0,
  PRIMARY KEY (api_client_id, day)
);
REVOKE ALL ON api_usage_daily FROM hermi_app;

-- Row policies for the org-facing reads (org admins list their own domains through the API; key listings and usage are served by the billing service under the org-admin check):
ALTER TABLE org_domains ENABLE ROW LEVEL SECURITY;
CREATE POLICY org_domains_select ON org_domains FOR SELECT USING (advisor_org_id IN (SELECT my_advisor_orgs()));
REVOKE INSERT, UPDATE, DELETE ON org_domains FROM hermi_app;                    -- writes go through the domain service (Cloudflare and DNS checks)

-- Host lookup for public pages: one function, no table access for the public role.
CREATE FUNCTION org_for_hostname(p_host citext) RETURNS TABLE (advisor_org_id uuid, brand jsonb, partner_links boolean)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT o.id, o.brand, COALESCE(c.partner_links, false)
    FROM org_domains d
    JOIN advisor_orgs o ON o.id = d.advisor_org_id AND o.status = 'active' AND o.kind = 'white_label'
    LEFT JOIN white_label_contracts c ON c.advisor_org_id = o.id AND c.status IN ('active', 'past_due')
   WHERE d.hostname = p_host AND d.purpose = 'web' AND d.status = 'active'
   LIMIT 1
$$;
REVOKE ALL ON FUNCTION org_for_hostname(citext) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION org_for_hostname(citext) TO hermi_app;

INSERT INTO feature_flags (key, description, enabled, rollout_pct, rules, variants) VALUES
('white_label', 'White-label accounts: branded client pages, custom domains', false, 100, '{}', '{}'),
('partner_api', 'Partner API with org API keys', false, 100, '{}', '{}')
ON CONFLICT (key) DO NOTHING;
INSERT INTO kill_switches (key, description) VALUES
('white_label.domains', 'Stop serving custom domains (pages fall back to a notice)'),
('provider.api', 'Stop all partner API requests (name from Phase 1 03 section 14)')
ON CONFLICT (key) DO NOTHING;
```

The API key format is `hm_live_<prefix>_<secret>` (prefix 8 characters, secret 32 random bytes, URL-safe). Lookup is by prefix, then constant-time compare of the hash; the key is never logged (logs carry only the prefix). Client-facing data served on a custom domain comes only from the existing share, proposal and presentation reads plus the `brand` and the contract's `partner_links` flag. Retention: `api_usage_daily` 25 months; `org_domains` with the org; contracts 7 years.

## 5. API additions

Two surfaces, both behind their flags and kill switches.

**Org administration (web app, Supabase session).** Base `/v1`, org admin required.

| Endpoint | Auth | Gate and cost | Request and response | Errors and side effects |
|---|---|---|---|---|
| `PATCH /advisor-orgs/{org_id}/brand` | org admin | `white_label` | `BrandIn` to `AdvisorOrg` | Validates contrast (AA), font allow-list, logo and favicon type and size; preview token returned. |
| `GET/POST /advisor-orgs/{org_id}/domains` | org admin | `white_label`, domains within the contract | `{ hostname, purpose }` to `OrgDomain` | Creates the Cloudflare custom hostname or the Resend domain, returns `dns_records`. `409` if the hostname is used by another org; `422` for blocked names (see section 9). |
| `POST /advisor-orgs/{org_id}/domains/{id}/check` | org admin | 10 an hour | to `OrgDomain` | Re-checks DNS and certificate state. |
| `DELETE /advisor-orgs/{org_id}/domains/{id}` | org admin | none | 204 | Stops serving immediately and deletes the Cloudflare hostname. |
| `GET/POST /advisor-orgs/{org_id}/api-clients` | org admin | `partner_api`, at most 10 active clients | `{ name, scopes, rate_limit_per_min? }` to `ApiClient` | Creates the integration; the acting seat is the caller. |
| `PATCH /api-clients/{id}` | org admin | none | `{ name?, scopes?, rate_limit_per_min?, status? }` | Scope or status changes apply at once. |
| `POST /api-clients/{id}/keys` | org admin | at most 2 active keys per client (rotation) | `{ expires_at? }` to `ApiKey` with `secret` once | |
| `DELETE /api-keys/{id}` | org admin | none | 204 | Revokes at once; cache invalidated. |
| `GET /advisor-orgs/{org_id}/api-usage` | org admin | none | `?days=` to `{ day, requests, errors, rate_limited }[]` | |
| `GET /advisor-orgs/{org_id}/contract` | org admin | none | to `{ plan, fee, seats_included, domains_included, ends_on, auto_renew, status }` | Read only; changes go through the admin console. |

**Partner API.** Base `/v1/partner`, `Authorization: Bearer hm_live_...`, JSON, problem+json errors, `Idempotency-Key` on writes, cursor pagination, headers `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `Retry-After` (same conventions as [04 section 1](../phase-1-launch/04-api-spec.md)). The key acts as its admin seat (D5), so all limits, validation and row-level security apply. Every call writes `audit_log` with the key prefix as actor.

| Endpoint | Scope | Notes |
|---|---|---|
| `GET /clients`, `POST /clients`, `GET/PATCH /clients/{id}` | `clients:read`, `clients:write` | `advisor_clients` fields; no private notes are exposed. |
| `GET /trips`, `POST /trips`, `GET/PATCH /trips/{id}` | `trips:read`, `trips:write` | Create a client trip (owner is the acting seat; client invited by email if given). |
| `GET /trips/{id}/items`, `POST /trips/{id}/items`, `PATCH/DELETE /items/{id}` | `trips:read`, `items:write` | Itinerary items with the Phase 1 validation; versioned with `If-Match`. |
| `GET /trips/{id}/presentation` | `trips:read` | The presentation data (JSON) with brand; partner links only when allowed. |
| `POST /trips/{id}/share-links` | `shares:write` | Returns `share_url` on the org's custom domain when active. |
| `GET /proposals`, `GET /proposals/{id}` | `proposals:read` | Status and the client's response. |
| `GET /bookings` | `bookings:read` | Commission tracker lines (read only in version 1). |
| `GET /openapi.json` | none | The published partner API schema (generated from a separate FastAPI sub-application so the consumer API stays private). |

Errors: `401 unauthenticated` (bad or revoked key), `403 insufficient_scope`, `404 not_found`, `429 rate_limited`, `503 feature_disabled` (kill switch). Out of scope for version 1: AI endpoints, credit-spending actions, billing, user accounts. Outbound webhooks (`proposal.responded`, `trip.updated`) are added only when a signed customer needs them (stretch in P3-077).

```ts
type BrandIn = { logo_key?: string; favicon_key?: string; primary: string; secondary: string; font: "system" | "serif" | "humanist" | "geometric"
  contact_line?: string; legal_terms_url?: string; legal_privacy_url?: string; email_from_name?: string; reply_to?: string
  hide_hermi_footer?: boolean }
type OrgDomain = { id: Uuid; hostname: string; purpose: "web" | "email"; status: "pending" | "verifying" | "active" | "failed" | "removed"
  dns_records: { type: "CNAME" | "TXT" | "MX"; name: string; value: string }[]; ssl_status: string | null; last_error: string | null }
type ApiClient = { id: Uuid; name: string; scopes: string[]; rate_limit_per_min: number; status: "active" | "suspended" | "revoked"; keys: ApiKey[] }
type ApiKey = { id: Uuid; prefix: string; expires_at: string | null; last_used_at: string | null; secret?: string }
```

Request pipeline for a custom hostname: Cloudflare terminates TLS for the hostname and forwards to the public page service; the service resolves `Host` through `org_for_hostname()`, rejects unknown hosts with a generic 404, applies the org theme, and generates every absolute link from the matched host. CORS and CSP allow-lists are built from active `org_domains` only.

## 6. UI screens

**Brand settings (org admin, web).** Logo and favicon upload, two colors with live contrast checks, font choice from four options, contact line, terms and privacy links, email sender name and reply-to, toggles for the Hermi footer and partner links (the latter locked by the contract), a live preview of a share page, presentation slide and proposal. Empty: a sample trip is used for preview.

**Domains.** List with status chips, an add form, a records table with copy buttons ("Add these two records at your DNS provider"), a "Check now" action and the last error in plain words ("The CNAME points somewhere else. It should point to {target}."). Domain removal has a typed confirmation.

**API clients and keys.** List of clients (name, scopes, status) with their keys (prefix, last used, expiry), create sheet with scope checkboxes, one-time secret display with a copy button and the warning "You will not see this again", revoke with confirmation, usage chart (requests, errors, rate limited), link to the API docs.

**Contract and billing.** Plan, term, seats used of included, domains used of included, renewal date, invoices link, and "Contact us to change your plan".

**Client-facing pages on the custom domain.** The consumer share page, presentation and proposal, re-skinned: org logo in the header, brand colors and fonts from tokens, contact line, required disclosures (partner-link sentence when enabled, AI-source labels), links to the org's legal pages, and no Hermi footer when hidden. Errors and expired links show a branded, plain-language message. Accessibility: the contrast check is enforced at save, focus states and skip links are kept, and font choices are limited to tested stacks.

**Public API docs.** A static documentation site (generated from the OpenAPI document) with authentication, errors, pagination, idempotency, examples in curl and Python, and the terms of use.

**Admin console.** See section 8.

Design-system note: theming is token driven ([05 section 2](../phase-1-launch/05-ui-ux-spec.md) tokens become CSS variables set per request from `brand`); no per-customer CSS is ever accepted.

## 7. Billing

- **Account contract.** $500 a month or $6,000 a year, recorded in `white_label_contracts`; billed through Stripe Invoicing or a Stripe subscription for the account (monthly card payment or annual invoice by bank transfer or card). Invoices are net 14 or net 30 as the contract says; dunning follows pack 02 (Stripe retries, then read-only after the contract grace period).
- **Included usage.** Up to 10 seats, 1 domain, API at 120 requests a minute per key (assumptions, set per contract). Extra seats are billed at the advisor seat price through pack 02's seat subscription on the same customer.
- **Net revenue.** Card payments net about 97%; bank transfer nets more. 09 counts $6,000 per account.
- **Tax.** Stripe Tax on invoices; business VAT ids captured.
- **Web only.** Never sold or linked in the iOS app (Guideline 3.1.1).
- **Renewal.** Reminder email 60 days before the end; one-click cancel in the contract view (auto-renew rules, [10 section 3.10 (full spec)](../reference-full-spec/10-quality-security-launch.md)).
- **Cost control.** Custom hostnames, email domains and storage have small per-account costs (Cloudflare for SaaS hostname pricing and Resend domains: verify); they are included in the fee.

## 8. Admin additions

New admin screen "White-label accounts" (Money group); extends [08](../phase-1-launch/08-admin-control-center.md) and pack 02's Advisors screens.

- **Account detail:** contract terms, status, seats used, domains and their states, API keys (prefix only) with last used and 30-day usage, brand preview, recent support tickets, export status.
- **Actions.** Create or edit a contract (owner and finance; typed confirmation), suspend the account (owner: pages fall back to a notice), revoke any API key, force a domain re-check, remove a domain (engineer), start an org export (support), rotate a customer's DPA version, set `school_operator` (owner only, after P3-080).
- **Permissions.** `whitelabel.read` for support, engineer, finance and owner; `whitelabel.contract.write` for finance and owner; `whitelabel.suspend` and `whitelabel.domain.remove` for owner and engineer; the route-permission test covers them.
- **Alerts.** Domain stuck verifying over 48 hours, certificate failure, API error rate above 5% for a key for 15 minutes, rate-limit hits above 20% of requests, a hostname resolving to an unknown origin (possible takeover, page), a contract ending in 60 days (renewal task), seats above the included number.
- **Runbook: onboarding a white-label account.** Contract signed, DPA accepted, org created, brand configured and reviewed, email domain verified, web domain verified, test share link opened from outside, API key issued if requested, 30 and 90 day check-ins.
- **Runbook: domain incident.** Kill switch `white_label.domains`, identify the hostname, remove or suspend, check for dangling records, notify the customer.

## 9. Legal and compliance

1. **Master agreement and DPA.** Hermi is a processor for the operator's client data; the operator is the controller. The contract covers processing instructions, sub-processors (the current list), security measures, breach notice times, deletion and return of data, audit rights limited to reasonable requests, liability caps, and termination. Counsel drafts the templates once (P3-071).
2. **Service levels.** Availability target and support response times stated by plan, no service credits, maintenance windows; nothing promised that Render and Cloudflare do not support (D7).
3. **Acceptable use and branding.** The operator owns its brand; Hermi may refuse domains that impersonate other organizations; blocked hostnames include anything containing other travel brands or Hermi lookalikes; impersonation and phishing complaints disable a domain at once (kill switch). Hermi's name may be removed from client pages but legal notices, disclosures and the privacy and terms links remain.
4. **Disclosure.** Partner-link commission sentence, "Ad" labels where applicable, and AI-source labels are not removable (D3); FTC, UK and EU rules in [08-affiliate-revenue.md section 7.4](../context/business-plan/08-affiliate-revenue.md).
5. **Child data (school operators).** COPPA (under 13) and FERPA (education records) apply to school trips. The design before any school operator: adult accounts only (teachers and parents), no accounts for children, minimal student data (first names and initials, no photos by default), no AI on student data, contract terms for school officials, and parental consent handled by the school. The gate ticket P3-080 must finish with counsel's written approval; until then the contract template prohibits school use.
6. **Data residency and transfers.** Operators outside the US: standard contractual clauses and a statement of where data is processed.
7. **Security.** Multi-tenant isolation is the headline risk: host-header handling, CORS and CSP built from active domains only, no cookies on custom domains, no sign-in on custom domains in version 1, API keys hashed and scoped, rate limits, audit on every API call, external review before the first customer.
8. **API terms.** No resale of access, no scraping of other users' data, no storage of passport or card numbers, acceptable rate use, right to suspend keys.
9. **Apple.** White-label is a web business product; no sale or link in the iOS app.
10. **Customer-specific requests.** A written scope rule: anything outside the contract's features is a paid project or a no, to keep a license from becoming consulting.

## 10. Analytics

Events: `wl_org_created`, `wl_brand_saved`, `wl_domain_added`, `wl_domain_active`, `wl_api_key_created {scope_count}`, `wl_client_page_viewed` (aggregate, by org, no client identity), `wl_proposal_responded`. Metrics: accounts, ARR, time from contract to first live client page (target 14 days), domain onboarding success rate, API requests and errors per key, pages served per account, seats used versus included, support hours per account in the first 90 days, renewals and churn. Base case needs 1 account in year 3 and 6 in year 5; track pipeline (qualified inbound, demos, proposals) as the leading indicator.

## 11. Tests

- **Isolation.** A key for org A never reads or writes org B (all partner routes, including list filters); a client page on org A's hostname never serves org B's share token; unknown and removed hosts return a generic 404; `Host` header tampering and `X-Forwarded-Host` are ignored unless set by Cloudflare; absolute links always use the matched host.
- **Keys.** Constant-time hash compare, scope enforcement (`403 insufficient_scope`), expiry and revoke effective immediately (cache invalidation test), rate limiting per key with headers, secret shown once and never logged.
- **Theming.** Contrast validation rejects failing colors; the font allow-list is enforced; arbitrary CSS is impossible; required disclosures render and cannot be hidden (snapshot tests for share page, presentation and proposal).
- **Domains.** Fake Cloudflare API: pending to active, failure with reason, removal stops serving at once; blocked hostnames rejected; periodic check detects a dangling record.
- **Email.** SPF and DKIM state from the fake Resend API; fallback sender used until verified.
- **Billing and contract.** Seat and domain limits enforced; renewal reminder; past-due behavior.
- **API conformance.** The OpenAPI document matches routes (generated schema test); idempotency replay; versioned writes with `If-Match`; pagination stability.
- **Security.** Dependency and ZAP scans on the public host handler; penetration test of host routing and key handling before the first customer; load test of a custom hostname at the public page targets.
- **E2E.** Create a white-label org, set brand, add a domain (staging test domain), issue an API key, create a trip through the API, share link opens branded on the test domain, proposal accepted, export works.

## 12. Tickets

| ID | Title | Size | Needs | Who |
|---|---|---|---|---|
| P3-071 | Gate check and contract pack: entry criteria, pricing and included usage, partner-link default, master agreement, DPA, SLA-lite, acceptable use, API terms; lawyer review | M | Pack 02 live | Founder, lawyer |
| P3-072 | Schema, flags and row policies (4.2): `kind`, contracts, domains, API clients, keys, usage, `org_for_hostname()`, kill switches, leak tests | M | P3-071 | Engineer |
| P3-073 | Theming engine: token-driven per-org theme, logo and favicon, font allow-list, contrast validation, disclosures preserved, branded presentation, share page and proposal | L | P3-072 | Engineer |
| P3-074 | Custom domains: Cloudflare for SaaS integration, DNS record guidance, verification and certificate polling, host routing, dynamic CORS and CSP allow-lists, takeover checks, blocked names | L | P3-072 | Engineer |
| P3-075 | Branded email: Resend sending domains, SPF and DKIM status, branded templates, reply-to, fallback | M | P3-073 | Engineer |
| P3-076 | API clients and keys: issuance, hashing, scopes, prefix lookup, rotation, revoke, expiry, per-key limits in `rate_limit_counters`, usage counters, org admin UI | M | P3-072 | Engineer |
| P3-077 | Partner API v1: clients, trips, items, presentation, share links, proposals and bookings reads, OpenAPI document, docs site and examples; stretch: outbound webhooks | L | P3-076 | Engineer |
| P3-078 | Contracts and billing: contract records, Stripe invoice or subscription, seat and domain limits, renewal reminders, dunning and read-only | M | P3-072 | Engineer |
| P3-079 | Admin screens, alerts, onboarding and domain-incident runbooks, support macros | M | P3-074, P3-076, P3-078 | Engineer, founder |
| P3-080 | School-operator gate: COPPA and FERPA design review, restrictions, contract addendum; written counsel approval before any school account | M | P3-071 | Lawyer, founder |
| P3-081 | Tests, external security review, first-customer onboarding at a pilot discount, 30 and 90 day reviews; launch checklist | L | P3-073 to P3-079 | Engineer, reviewer, founder |

## 13. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Few buyers and long sales cycles | High | Medium | Base case needs only 6 accounts by year 5; gate on inbound demand; do not build ahead of a signed pilot |
| Per-account support exceeds the fee | Medium | Medium | Onboarding runbook, included-usage limits, paid projects for custom work |
| Multi-tenant security incident (host routing, keys) | Low | Severe | Isolation tests, external review, no sign-in on custom domains in v1, kill switches |
| Domain abuse or impersonation | Low | High | Blocked names, review of first hostnames, immediate disable, takeover checks |
| License turns into consulting | Medium | Medium | Written scope rule, feature requests go to the roadmap or a paid project |
| Child-data obligations for school operators | Medium | High | Gate P3-080; contract forbids school use until cleared |
| Custom domain costs and Cloudflare changes | Low | Low | Verify pricing, cost included in the fee, domains limit per contract |
| Divergence from the advisor product | Medium | Medium | Same code and tenancy (D1), theming by tokens, no per-customer forks |
