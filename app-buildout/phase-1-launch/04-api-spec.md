# 04. API specification (Phase 1)

Part of the [Phase 1 launch specification](README.md) of the [Hermi build specification](../README.md). The decisions in the [build README](../README.md) (tiers, credit action codes, table names, non-negotiable rules) are final and this file follows them. Table, column, enum and limit-key names come from [03-database-schema.md](03-database-schema.md) (the database), the agents behind the AI endpoints in [06-ai-agents-spec.md](06-ai-agents-spec.md), purchases and paywall logic in [07-monetization-spec.md](07-monetization-spec.md), and the admin console in [08-admin-control-center.md](08-admin-control-center.md).

Written 2026-09-30. This file is complete and self-contained for Phase 1: it defines every HTTP endpoint the web and iOS clients and the partner systems call in the launch app, written so the route modules can be built one per section in FastAPI and the TypeScript client generated from the result. Section numbers match the full-scope specification in [../04-api-spec.md](../reference-full-spec/04-api-spec.md) so cross references agree. Features that belong to Phase 2 or Phase 3 are not specified here; their sections are kept as one-line "Later" pointers so nobody builds them by accident.

## Phase 1 additions at a glance

| Addition | Where |
|---|---|
| Import a trip from a calendar file, a calendar feed URL (with SSRF protection), pasted booking text, a Google Maps export or pasted places, through entries named for TripIt, Tripsy and Wanderlog; preview, then confirm; opt-in "Keep checking this calendar" polling every 6 hours; one free Trip Pass reward per user | 5.26 |
| "Verify this plan": paste an itinerary from ChatGPT, Gemini, Layla or Mindtrip, check each place, hours and price with sources, import the confirmed items | 5.30 |
| Evidence freshness: `stale` after 14 days and a one-tap recheck on notes and verified items | 5.14 |
| Public status summary and "How we earn" data (the Android install guide is a static page and needs no endpoint) | 5.28 |
| Live calendar subscription feed per trip, token URL | 5.29 |
| Booked-fare fields (`paid`, `booked_at`) and the booked-fare drop alert | 5.8 |
| Referral codes and referral rewards | 5.27 |
| Public sample trips and public shared-trip reads (search-friendly pages) | 5.28 and 5.6 |
| Free owners invite 1 collaborator per trip (Plus and Trip Pass up to 6) | 1.3, 2.3, 4 and 5.6 |
| Only Free, Plus, Trip Pass and credit packs are sold, in the iOS app only (no web purchases in Phase 1); RevenueCat is the only billing webhook | 5.19, 5.20 and 6 |

## 1. Conventions

### 1.1 Base URL, format and versioning

| Item | Rule |
|---|---|
| API base | `https://api.hermi.world/v1` in production, `https://api.staging.hermi.world/v1` in staging, `http://localhost:8100/v1` locally (and in CI). All paths below are relative to it unless they start with `/go`, `/health` or `/.well-known` (those are served at the host root). |
| Redirect host | `https://go.hermi.world/go/{click_id}` (same service, separate hostname so cookies and CSP never mix with the API). |
| Format | JSON (`application/json; charset=utf-8`) in and out. Dates are `YYYY-MM-DD`, times `HH:MM:SS`, timestamps RFC 3339 in UTC (`2026-09-30T14:05:00Z`). Only the SSE and redirect endpoints return something else. |
| Names | `snake_case` for fields, `kebab-case` for path segments, plural nouns for collections. |
| Ids | Every public id is a UUIDv7 string. Integer ids from the existing Trip Planner never appear. Ids are opaque: clients never parse them. |
| Money | `{ "amount_minor": 13900, "currency": "USD" }`: integer minor units plus ISO 4217. Fares and lodging prices also carry `observed_at`. Never a float. |
| Nulls | Absent optional fields are returned as `null`, never omitted, so generated types are stable. In PATCH bodies, an omitted field means "leave unchanged" and an explicit `null` clears a nullable field. |
| Versioning | The major version is in the path. Additive changes (new fields, endpoints, enum values) are not breaking: clients must ignore unknown fields and treat unknown enum values as "other". A breaking change ships as `/v2` alongside `/v1` for at least 12 months. Old iOS builds are supported through `X-Client-Version` (1.7) and a minimum-version gate on `GET /me`. |
| Compression and caching | gzip and brotli. Reads that return `ETag` support `If-None-Match` and answer `304`. Responses carry `Cache-Control: private, no-store` unless an endpoint says otherwise. |

### 1.2 Authentication

- Sign-in happens in Supabase Auth (Sign in with Apple, Google, email code). The client sends the Supabase access token on every call: `Authorization: Bearer <jwt>`. Auth is bearer only for web and iOS: there is no session cookie and no `POST /auth/session`.
- `AUTH_MODE=dev` (02 section 7.1): the dev routes `GET /v1/dev/personas` and `POST /v1/dev/session` (body `{ persona }`) exist only when `AUTH_MODE=dev` and `ENVIRONMENT` is `local` or `ci`. They return a bearer token signed by the local key pair that `CurrentUser` verifies against the local JWKS. They are not registered otherwise and are not in the production OpenAPI.
- One FastAPI dependency, `CurrentUser`, verifies signature (JWKS, cached 1 hour and refreshed at most once a minute on an unknown `kid`, 02 section 6), `iss`, `aud`, `exp` and `sub`, resolves `auth_identities(provider, subject)` to a `users` row, and rejects any status other than `active` with `403 account_inactive` (status `pending_deletion` gets `403 account_pending_deletion`, and only `POST /me/deletion/cancel` and `GET /me` work). A first-time valid JWT with no identity row is handled by `POST /me/bootstrap`, the only endpoint that accepts a JWT without a users row.
- Agent workers do not use user tokens. The worker calls internal functions directly, not HTTP. The legacy `/api/agent/v1` bridge is removed.
- Partner callers (webhooks) authenticate with signatures or shared secrets (section 6). Admin callers use the admin API (section 5.25).
- Guest mode is local-first; a guest has no token and calls no endpoint until they tap "Save your trip". `POST /me/claim` merges guest data after sign-in (5.1).

### 1.3 Authorization: roles and 404 for non-members

| Role | Code | Summary |
|---|---|---|
| Owner | `owner` | Everything on the trip, including delete, transfer, invites and share links. Exactly one per trip. |
| Editor | `editor` | Edit itinerary, lodging, flights, notes, checklist; vote; start AI actions from their own credits; invite viewers if the owner allows. |
| Viewer | `viewer` | Read and heart stays and places. No edits, no AI, no invites. |

Trip-scoped routes declare a minimum role through `require_trip(trip_id, min_role)`. A caller who is not a member gets `404 not_found`, never `403`, for every id in the path, so ids cannot be probed. A member whose role is too low gets `403 insufficient_role`. Routes that take a child id (for example `/lodging/{id}`) join up to the trip and apply the same rule. A CI test walks `app.routes` and fails if any route with an id parameter does not use the dependency. Request bodies never accept `owner`, `role` (except on invite and member-role routes), `tier` or `user_id`.

Trip capabilities (what the trip can do) come from the better of the owner's tier and any active `trip_passes` row for that trip. Credits are charged to the acting user. Both are explained to the client through `capabilities` (2.3) and `GET /me/entitlements` (5.19).

### 1.4 Errors: RFC 9457 problem+json

Every non-2xx response has `Content-Type: application/problem+json` and this shape:

```ts
type Problem = {
  type: string              // "https://api.hermi.world/problems/<code>"
  title: string             // short, stable English summary
  status: number
  code: string              // machine code from the catalogue (section 3)
  detail: string            // human sentence, safe to show; no em dashes
  instance: string          // "/v1/trips/0191..."
  request_id: string        // same as X-Request-Id
  errors?: { field: string; code: string; message: string }[]   // validation only
  retry_after_seconds?: number
  current?: unknown         // 409 version_conflict: the latest resource
  paywall?: PaywallHint     // 402 gate errors (`limit_reached`, `entitlement_required`, `insufficient_credits`, `payment_required`): see 5.20
  credits?: { needed: number; balance: number }                  // insufficient_credits
}
```

Clients switch on `code`, never on `title` or `detail`. Stack traces and SQL never appear. FastAPI's default 422 body is replaced by a handler that maps to `validation_failed` with `errors`.

### 1.5 Pagination

Collections that can grow use cursor pagination. Small bounded collections (a trip's days, a trip's members) return a plain array.

```
GET /v1/trips?limit=50&cursor=eyJ0IjoiMDE5MS4uLiJ9
-> 200 { "items": [ ... ], "next_cursor": "eyJ0Ijoi..." | null, "has_more": true }
```

`limit` defaults to 50, maximum 200. Cursors are opaque, signed, expire after 24 hours, and encode the sort key plus id. Default order is newest first by `created_at` unless an endpoint says otherwise. Sync-style lists also accept `updated_since=<timestamp>` and return deleted rows as tombstones (`{ "id": "...", "deleted_at": "..." }`) so polling clients can drop them.

### 1.6 Idempotency keys

`Idempotency-Key: <uuid>` (client generated) is **required** on every POST that reserves credits or writes money, and optional but honored on all other POSTs. The required list: every `/trips/{id}/ai/*` action, `/trips/{id}/agent-runs` and its `cancel` (no cost, but it refunds), `/guest/ai/draft-day`, `/trips/{id}/flights/live-search`, `/trips/{id}/lodging/rental-search`, the verify and recheck routes (`/trips/{id}/verify-plan`, `/plan-verifications/{id}/check`, `/notes/{id}/recheck`, `/items/{id}/recheck`), referral and import rewards (`/imports/paste`, `/imports/ics-feed`, `/imports/{id}/confirm`, `/me/referral/redeem`) and purchase-bound routes (`/credits/packs/claim`, `/purchases/sync`, `/purchases/restore`, `/me/passes/{id}/bind`). The middleware and its tests live in WF-016.

- Keys are stored for 24 hours with the request hash, the status and the response body (`idempotency_keys` holds one row per user and key with the method, path, request hash, state, status and response; credit spends also carry the key, prefixed with the user id, in `ai_usage.idempotency_key` and `credit_ledger.idempotency_key`, so a retry can never charge twice even if the row is gone). The same key with the same body replays the original response and adds `Idempotent-Replay: true`. The same key with a different body gets `422 idempotency_key_reused`. The same key while the first request is still running gets `409 idempotency_in_progress` with `Retry-After: 1`.
- A missing key on a required route gets `400 idempotency_key_required`.
- Credit reservation and ledger writes key off the same value, so a retried agent start can never charge twice.

### 1.7 Optimistic concurrency

Every editable resource has an integer `version` starting at 1, incremented on each successful write by the `bump_version()` trigger (03 convention 11: trips, itinerary days and items, routes, lodging options, checklist items and notes), and returns a strong `ETag: "<version>"`. Two equivalent ways to send it:

- `If-Match: "<version>"` header on `PATCH`, `PUT` and `DELETE` (preferred).
- `version` in the body of a PATCH.

The middleware (`If-Match` parsing, `428`, `409`) and its tests live in WF-016. If both are absent, the write is rejected with `428 precondition_required` for resources marked "versioned" below (trip, days, items, routes, lodging options, notes, checklist items). On mismatch the response is `409 version_conflict` with the latest resource in `current`, and the client shows its conflict sheet ("Sam changed this. Keep yours or use theirs."). Last-writer-wins applies only to the offline queue, per field, where the client re-sends with the new version. Lists return `ETag` over the collection state and support `If-None-Match` for cheap polling (every 15 to 30 seconds on a shared trip, plus on foreground).

### 1.8 Rate limits and headers

Limits are stored in Postgres (`rate_limit_counters`, rows expire after a day) until about 10k MAU. Every response carries the IETF draft headers:

```
RateLimit-Limit: 120
RateLimit-Remaining: 117
RateLimit-Reset: 38          # seconds until the window resets
RateLimit-Policy: 120;w=60
```

A rejected call returns `429 rate_limited` with `Retry-After` (seconds). Starting limits:

| Surface | Limit |
|---|---|
| Write API (POST, PUT, PATCH, DELETE) | 120 per minute per user, 600 per minute per IP |
| Read API | 600 per minute per user |
| Email code and sign-in exchange | handled at Supabase (5 per email per hour, 20 per IP per hour); `POST /me/bootstrap` 30 per IP per 10 minutes |
| Invites | 30 created per user per day, 20 pending per trip |
| AI actions | 30 per hour per user, one agent run at a time per account, plus credits and provider-spend ceilings |
| `POST /outbound` | 60 per hour per user, repeats within 30 seconds deduplicated |
| Share link views | 60 per minute per IP and 600 per hour per token |
| Export and deletion request | 1 per day each |
| Imports | 20 previews a day per user (file, paste and feed together); `POST /imports/ics-feed` 5 a day; feed refresh 4 a day per import |
| Calendar feed `GET /calendar/{token}.ics` | 120 per hour per token, 600 per hour per IP; unknown tokens count against the IP limit |
| Public sample trips | 120 per minute per IP |
| Referral code lookup and redeem | lookup 30 per minute per IP; redeem 10 a day per user |
| Webhooks | not rate limited; signature failures 20 per minute per IP then blocked at Cloudflare |

### 1.9 Other headers and behaviors

| Header | Direction | Meaning |
|---|---|---|
| `X-Request-Id` | both | Client may send one (uuid); server always returns one and logs it with every line. |
| `X-Client-Version` | request | `ios/1.2.0` or `web/2026.10.3`. The server answers `426 client_upgrade_required` only when below `min_client_version` from `GET /me`. |
| `Accept-Language` | request | Locale for error `detail` and AI output. |
| `X-Hermi-Client` | request | `web`, `ios`. Informational (analytics and the web paywall variant); never an auth or CSRF control. |
| `X-Attest-Key-Id`, `X-Attest-Assertion` | request | App Attest key id and assertion; accepted only on `POST /guest/ai/draft-day` (5.1) in place of `Authorization`. |
| `Idempotency-Key`, `If-Match`, `If-None-Match` | request | See 1.6 and 1.7. |
| `Deprecation`, `Sunset` | response | Set on endpoints being retired. |
| `Server-Timing` | response | `db;dur=12, ai;dur=840` for debugging. |

Kill switches (table `kill_switches`) can disable a feature at runtime. A disabled feature returns `503 feature_disabled` with `retry_after_seconds` when known. Cached data endpoints keep working when AI or live providers are switched off.

### 1.10 Async work

Anything longer than about 2 seconds (agent runs, exports, deletions, feed imports, live searches that fan out to providers) returns `202 Accepted` with a resource to poll and, for agent runs, an SSE stream. A `Location` header points to the status resource. Jobs are Procrastinate tasks; workers never call the API over HTTP.

### 1.11 CORS and security headers

Allowed origins: the web app, `capacitor://localhost`, `https://localhost`. Allowed headers include `Authorization`, `Content-Type`, `Idempotency-Key`, `If-Match`, `If-None-Match`, `X-Hermi-Client`, `X-Attest-Key-Id`, `X-Attest-Assertion`, `X-Client-Version`, `X-Request-Id`. Exposed headers: `ETag`, `RateLimit-*`, `Retry-After`, `Idempotent-Replay`, `X-Request-Id`, `Location`. HSTS, `X-Content-Type-Options: nosniff`, and `Referrer-Policy: no-referrer` on all responses.

### 1.12 Tenant isolation and logging

Every request runs in a transaction with `SET LOCAL app.user_id` so row-level security catches a forgotten check. Each request logs one structured line: request id, user id, route template, status, latency, credits charged. No request bodies are logged. Notes, private comments and pasted text never go to Sentry.

## 2. Shared types

Used by the endpoint tables. Written as TypeScript-like blocks; FastAPI models mirror them.

### 2.1 Primitives

```ts
type Uuid = string                          // UUIDv7
type Money = { amount_minor: number; currency: string }
type Iata = string                          // "LIS"
type Role = "owner" | "editor" | "viewer"
type Tier = "free" | "plus"                  // Phase 2 adds "family" and "pro" (additive, see 1.1)
type Product = Tier | "trip_pass"
type CreditAction = "explain" | "live_search" | "draft_day" | "draft_trip" | "research" | "agent_run" | "verify_plan"
type Page<T> = { items: T[]; next_cursor: string | null; has_more: boolean }
type Attribution = { id: Uuid; display_name: string | null }   // null display_name means "Former member"
```

### 2.2 Credit and gate envelopes

Every credit-spending success body includes:

```ts
type CreditReceipt = {
  action: CreditAction
  reserved: number            // credits held at start
  charged: number | null      // null until settled; 1 when served from shared cache
  from_cache: boolean
  balance_after: number       // total spendable credits now
  reservation_id: Uuid        // credit_ledger.reservation_id; one action's reserve, refund and settle rows share it
}
```

```ts
type PaywallTrigger = "third_trip" | "second_route" | "track_live" | "alert_limit" | "invite" | "out_of_credits_draft" | "out_of_credits_research" | "out_of_credits_agent" | "out_of_credits_verify" | "export_footer" | "ninth_stay" | "lifecycle_14d"   // 07 section 6.2
type PaywallHint = {
  trigger?: PaywallTrigger    // the 07 section 6.2 trigger that fired; absent when none applies (traveler_limit, guest sign-up)
  reason: "trip_limit" | "sharing" | "live_routes" | "credits" | "agent_taster_used" | "traveler_limit"
  offer_url: string           // GET /v1/paywall/offer?reason=...&trip_id=...
  free_path: string           // what the user can still do for free, plain sentence
}
```

### 2.3 Trip and capabilities

```ts
type Capabilities = {
  effective_tier: Tier | "trip_pass"
  source: "owner_tier" | "trip_pass"     // a reward pass from an import counts as "trip_pass"
  can_invite: boolean               // a collaborator slot is free: collaborators_used < max_collaborators
  collaborators_used: number        // non-owner members plus pending invites
  max_collaborators: number         // plans.limits.collaborators: Free 1, Plus 6, Trip Pass 6 (Free owners invite 1 collaborator per trip so couples plan free)
  live_routes_max: number           // Free 0 (cached only), Plus 3, Trip Pass 2
  live_routes_used: number
  live_checks_left: number | null   // a pass: live_checks_max (60) minus live_checks_used
  agent_enabled: boolean            // owner setting and consent
  limited: boolean                  // tier lapsed: members downgraded to viewers, banner shown
  pass_expires_at: string | null
}

type Trip = {
  id: Uuid; version: number
  name: string; status: "planning" | "booked" | "done" | "archived"
  start_date: string | null; end_date: string | null
  home_currency: string; notes: string
  destinations: Destination[]
  travelers: Person[]                          // people linked through trip_people
  cover: { image_url: string; destination_name: string; attribution: string | null } | null
  flight_dates: { start: string; end: string | null; flights: ChosenFlightRef[] } | null
  my_role: Role
  capabilities: Capabilities
  ai_enabled: boolean                          // owner toggle
  editors_can_invite: boolean                  // owner setting (trips.editors_can_invite): editors may invite viewers
  member_count: number
  owner: Attribution
  created_at: string; updated_at: string; deleted_at: string | null
}
```

`Trip` keeps the shape of today's `TripOut` (destinations, travelers, cover, flight dates) and adds `version`, `my_role`, `capabilities`, `ai_enabled` and `owner`.

## 3. Error code catalogue

| HTTP | `code` | When | Client behavior |
|---|---|---|---|
| 400 | `bad_request` | Malformed JSON or query | Fix request |
| 400 | `idempotency_key_required` | Missing header on a required route | Generate and retry |
| 401 | `unauthenticated` | No or invalid token | Refresh once, then sign-in |
| 401 | `token_expired` | JWT past `exp` | Refresh and retry |
| 402 | `insufficient_credits` | Balance below action price | Show credit sheet with `credits` and `paywall` |
| 402 | `payment_required` | Feature needs a paid tier or pass | Show paywall from `paywall` |
| 402 | `entitlement_required` | Tier or capability missing (`paywall` hint set) | Paywall moment |
| 402 | `limit_reached` | Plan limit hit (active trips, routes, alerts, collaborators) (`paywall` hint set) | Paywall or explain |
| 403 | `insufficient_role` | Member role too low | Hide control |
| 403 | `account_inactive` | `users.status` is `suspended` (an owner decision in the admin console) or `deleted` | Show support contact |
| 403 | `account_pending_deletion` | In 30 day grace | Offer cancel |
| 403 | `ai_consent_required` | No `ai_processing` consent | Show consent screen |
| 403 | `ai_disabled_for_trip` | Owner turned AI off | Explain |
| 404 | `not_found` | Missing or not a member | Generic not found |
| 405 | `method_not_allowed` | Wrong method | Bug |
| 409 | `version_conflict` | Stale `If-Match` or body version | Show conflict sheet using `current` |
| 409 | `idempotency_in_progress` | Duplicate in flight | Retry after 1 s |
| 409 | `run_already_active` | One agent run at a time | Open the active run |
| 409 | `already_member` | Invite for an existing member | Open trip |
| 409 | `state_conflict` | Invalid transition (cancel a finished run) | Refresh |
| 409 | `referral_already_redeemed` | The account already redeemed a referral code | Explain |
| 410 | `claim_link_expired` | Legacy claim link used or past 7 days | Ask for a new link |
| 410 | `invite_expired` | Invite past expiry, revoked or used up | Ask for a new invite |
| 410 | `share_link_revoked` | Share link revoked or expired | Show gone page |
| 410 | `import_expired` | Import preview older than 24 hours, discarded or already applied | Start the import again |
| 412 | `precondition_failed` | `If-Match` not parseable | Bug |
| 413 | `payload_too_large` | Body over limit (1 MB JSON, 2 MB calendar file, 10 MB other uploads) | Shrink |
| 415 | `unsupported_media_type` | Import file is not a calendar file (`.ics`, `text/calendar`) | Explain, offer paste instead |
| 422 | `validation_failed` | Field errors in `errors` | Show field messages |
| 422 | `idempotency_key_reused` | Key reused with different body | Use a new key |
| 422 | `blocked_domain` | Link to a domain we never fetch (Airbnb, Vrbo, Booking.com), including a calendar feed URL on those hosts | Explain, save link without preview; for a feed, ask for a downloaded file instead |
| 422 | `unsupported_currency` | Currency not in `fx_rates` | Pick another |
| 422 | `feed_url_not_allowed` | Calendar feed URL failed the SSRF rules (5.26) | Ask for a public https calendar link |
| 422 | `attestation_invalid` | App Attest attestation or nonce failed verification | Retry once, then continue without guest AI |
| 422 | `referral_not_eligible` | Code is yours, expired, past the 14 day window or the account is not new | Explain |
| 422 | `list_link_not_readable` | A Google Maps list link was sent where text or a file is needed; Hermi never opens it | Show how to export the list, keep the link as a note |
| 422 | `plan_too_long` | Pasted plan over 8,000 characters | Ask for one trip at a time |
| 409 | `polling_limit` | Already 3 calendars are being kept up to date, or the import cannot be polled | Turn one off first |
| 426 | `client_upgrade_required` | Below minimum client | Show update screen |
| 428 | `precondition_required` | Versioned write without `If-Match` | Bug |
| 429 | `rate_limited` | Limit hit | Back off per `Retry-After` |
| 429 | `provider_budget_exhausted` | Daily or monthly provider-spend ceiling | Explain, show cached data |
| 429 | `quota_exceeded` | Daily place search cap (`places_searches_per_day`) reached; cached results and saved places keep working | Show the 05 6.13 limit copy and "Add by hand" |
| 500 | `internal_error` | Unhandled | Retry, report `request_id` |
| 502 | `provider_error` | Upstream (Anthropic, SerpApi, Travelpayouts) failed; credits released | Retry later |
| 502 | `feed_fetch_failed` | The calendar feed host answered with an error, timed out or returned something that is not a calendar | Retry later or upload the file |
| 503 | `feature_disabled` | Kill switch | Show notice |
| 503 | `provider_unavailable` | Upstream down | Show cached data |
| 504 | `provider_timeout` | Upstream timed out; credits released | Retry |

Webhook endpoints use a smaller set: `401 invalid_signature`, `400 bad_payload`, `200` for duplicates and unhandled event types, `500` only for retryable failures so the sender retries.

## 4. Gates and costs at a glance

Gate codes used in the endpoint tables. A call that fails a gate returns the error shown, with `paywall` set. Plan limits and missing entitlements are always 402 (the one exception is `verify_items`: a 402 `limit_reached` with no `paywall`, because the rest can be checked in another run); 403 is kept for `insufficient_role`, `account_inactive`, `account_pending_deletion`, `ai_consent_required` and `ai_disabled_for_trip`.

| Gate | Passes when | Failure |
|---|---|---|
| none | Any signed-in user | n/a |
| `member(role)` | Caller is a member at or above `role` | 404 or `insufficient_role` |
| `can_invite` | Trip capabilities say a collaborator slot is free (`collaborators_used < max_collaborators`: Free owners 1, Plus and Trip Pass 6) | 402 `limit_reached`, reason `sharing` |
| `active_trips` | Owner is under `plans.limits.active_trips` (Free 2, Plus 25); a trip with an active pass does not count (limit key `active_trips_bonus`, 03 section 7.5) | 402 `limit_reached`, reason `trip_limit` |
| `live_route` | `live_routes_used < live_routes_max` and within 120 days of departure | 402 `limit_reached`, reason `live_routes` |
| `ai` | `ai_processing` consent, trip `ai_enabled`, kill switch open | `ai_consent_required`, `ai_disabled_for_trip`, `feature_disabled` |
| `credits(n)` | Spendable credits at least `n` (`reserve_credits`, which raises SQLSTATE `WF402` when short) and provider ceiling has headroom | 402 `insufficient_credits` or 429 `provider_budget_exhausted` |
| `taster` | Free user has not used the lifetime deep run | 402 `payment_required`, reason `agent_taster_used` |
| `import_reward` | The account has never received an import reward and the confirmed import meets the rules in 5.26 (at least 3 items including a flight or a stay, verified email, no active pass on the trip, no active Plus) | no error; the response carries `reward: null` |
| `verify_items` | The number of items selected for a plan check is at most `plans.limits.verify_items_per_run` (Free 5, Plus and Trip Pass 12) | 402 `limit_reached` with no paywall (the cap is per run, so the rest can be checked in another run); the body says how many can be checked |
| `admin(role)` | Caller is an `admin_users` row with the role | 404 (routes are hidden) |

Credit prices (README, final): `explain` 1, `live_search` 1, `draft_day` 1, `draft_trip` 4, `research` 8 (1 from shared cache), `agent_run` 40 (8 from shared cache), and `verify_plan` 1 per checked item (added from the competitive analysis; reading the pasted plan is 1 credit at the `explain` price; a one-tap evidence recheck is 1 credit at the `explain` price). Hard stops are enforced in the worker, not the API. Credit-spending endpoints reserve before work, settle after, and release on `provider_error`, `provider_timeout` or cancellation before a result.

## 5. Endpoints by module

Table columns: **Endpoint** (method and path), **Auth** (minimum role, all require a bearer token unless stated), **Gate and cost**, **Request and response**, **Errors and side effects**. "Standard errors" means 401, 404 (non-member), 422, 429, 500. Bodies are shown in the schema block under each table. A trailing `?` marks an optional field.

### 5.1 Auth and session bootstrap

| Endpoint | Auth | Gate and cost | Request and response | Errors and side effects |
|---|---|---|---|---|
| `POST /me/bootstrap` | JWT, no users row needed | none | `BootstrapIn` to `Me` (201 new, 200 existing; 409 `email_in_use` when the email belongs to another account) | Calls the `bootstrap_user` function (03), which creates `users`, `auth_identities`, the "Me" `people` row, a `free` `entitlements` row and the user's `referral_codes` row. A `referral_code` in the body is redeemed in the same call (5.27); a bad code is ignored and never fails sign-up. No credit grant is written yet: the 12 Free credits are written on the first credit use of each month (`ensure_free_monthly_grant`, 03 section 5.13) and the taster grant at its first offer. Records Apple relay email flag. Emits `user_signed_up`. |
| `GET /me` | user | none | `Me` | Returns server clock, `min_client_version`, feature flags evaluated for the user, and pending deletion state. Polled on foreground. |
| `POST /me/claim` | user | none | `{ trip: TripJson, claim_id: Uuid, merge?: boolean }` to `ClaimResult` | Imports the guest's local trip (one) and people into new rows owned by the caller. `claim_id` is client generated once per claim, so a double submit returns the first result (`Idempotent-Replay: true`) instead of importing twice. If identity already owns data and `merge` is absent: `409 state_conflict` with counts in `detail`. There is no guest token; a guest holds no server credential. |
| `POST /devices/attest/challenge` | none (rate limited per IP) | none | none to `{ nonce: string, expires_at: string }` | Issues a one-time App Attest challenge nonce (5 minutes). |
| `POST /devices/attest` | none (rate limited per IP) | none | `{ key_id: string, attestation: string, nonce: string }` to 204 | Verifies the attestation (certificate chain, nonce, App ID hash) and stores `key_id`, the public key, the counter (0) and the environment (`development` or `production`) in `device_attestations` (03; the endpoint names are those of 10 section 2.4). `422 attestation_invalid` otherwise. |
| `POST /guest/ai/draft-day` | App Attest assertion, no JWT | `credits(1)` (`draft_day`) from the guest allowance | `{ destination: string, day?: string, preferences?: string }` with `Idempotency-Key` and the assertion headers to `DraftDayResult` | The one guest AI route. Instead of `Authorization`, the request carries `X-Attest-Key-Id` and `X-Attest-Assertion`; the server checks the assertion against the stored public key and advances the counter in one statement (a replayed counter is `401 unauthenticated`). Spend is drawn from `guest_allowances` (one row per key and UTC month, which references `device_attestations`) through its definer function, never from `credit_grants`; an empty allowance is `402 insufficient_credits` with the sign-up prompt as the `paywall` hint. Guest consent to `ai_processing` is given on the device before the call, so there is deliberately no `ai` gate (no users row, no consent row). Nothing is stored for the guest beyond that row. |
| `POST /me/legacy-claim` | JWT, no users row needed (like `POST /me/bootstrap`) | none | `{ token: string }` to `Me` | The claim link for WF-040. The one-time importer (`import-legacy`, 03 section 12) emails each pre-created owner account a link `https://app.hermi.world/claim/<token>` at its verified address. The token is random, stored only as a sha256 hash and expires in 7 days; it works once. The hash lives in the `legacy_claims` table (03 section 5, migration 0023), because `trip_invites` and `trip_share_links` are trip-scoped. With a valid token the call attaches the signed-in identity (`auth_identities`) to the legacy `users` row and creates no second `users` row; `POST /me/bootstrap` must likewise not create a user for an email that a pending legacy row owns, it returns `409 email_in_use` and the client sends the person to the claim link. The owner's imported trips, people and lodging become theirs. `410 claim_link_expired` for a used or expired token (the client shows "Ask for a new link"). |
| `POST /me/sign-out` | user | none | none to 204 | Revokes the current device's refresh token and unregisters its push token. |
| `POST /me/sign-out-everywhere` | user, recent auth | none | none to 204 | Revokes all devices and sessions, marks `devices.revoked_at`. Audit event. |
| `GET /me/devices` | user | none | none to `Device[]` | Lists signed-in devices. |
| `PUT /me/devices/{device_id}` | user | none | `DeviceIn` to `Device` | Registers or updates a device row (`devices.id`). Stores the push token (`push_token`, `push_environment`), `platform`, `app_version` and `os_version`; locale and notification prefs are saved on `users` and `users.prefs`. |
| `DELETE /me/devices/{device_id}` | user | none | 204 | Revokes that device's session. |
| `PUT /me/push-token` | user | none | `{ device_id, push_token, push_environment: "sandbox" \| "production" }` to 204 | Sets the token on the device. Invalid tokens are cleared when APNs answers 410. |
| `GET /health/live` | none | none | `{ status: "ok", version }` | Liveness, served at the host root (not under `/v1`). No auth, no rate limit headers. |
| `GET /health/ready` | none | none | `{ status: "ok" \| "degraded", checks: { database, migrations, queue } }` | Readiness: Postgres reachable, Alembic revision at head, queue reachable; 503 when any check fails (deploys roll back on it). Same rules as `/health/live`. |
| `GET /health/queue` | none | none | `{ status: "ok", lanes: { api, ai, notify, batch: { depth, oldest_age_seconds } } }` | Jobs waiting to run now and the age of the oldest, per lane; scaling reads it. Cached for 5 seconds. 503 `{ status: "fail" }` when the queue cannot be read; it never affects `/health/ready`. Public like `/health/live`. |

```ts
type BootstrapIn = {
  display_name?: string; locale?: string; timezone?: string
  home_airports?: Iata[]; home_currency?: string
  age_confirmed: boolean                     // 13+ (16+ EU and UK locales)
  device?: DeviceIn
  claim?: { trip: TripJson; claim_id: Uuid }  // claim the guest trip in one step (same rules as POST /me/claim)
  referral_code?: string                     // from a hermi.world/r/<code> link, see 5.27
}
type Me = {
  id: Uuid; email: string | null; email_is_relay: boolean
  display_name: string | null; locale: string; timezone: string
  home_currency: string; home_airports: Iata[]
  status: "active" | "pending_deletion"
  tier: Tier; me_person_id: Uuid
  consents: { kind: string; version: string; accepted_at: string }[]
  flags: Record<string, boolean>
  min_client_version: string
  server_time: string
}
type DeviceIn = {
  device_name?: string; platform: "ios" | "web"; app_version: string
  os_version?: string; locale?: string; push_token?: string; push_environment?: "sandbox" | "production"
  notifications?: { price_alerts: boolean; trip_changes: boolean; reminders: boolean }
}
type Device = DeviceIn & { id: Uuid; current: boolean; last_seen_at: string; revoked_at: string | null }
type TripJson = unknown                      // the guest app's local trip document (trip, days, items, saved places, people), validated like TripCreate plus the guest caps (1 trip, 200 items)
type ClaimResult = { trip_id: Uuid | null; people_imported: number; items_imported: number }
```

### 5.2 Account: profile, consents, export, deletion

| Endpoint | Auth | Gate and cost | Request and response | Errors and side effects |
|---|---|---|---|---|
| `PATCH /me/profile` | user | none | `ProfileUpdate` to `Me` | Updates display name, locale, timezone, home currency and airports. Also updates the "Me" person's name and home airports. |
| `GET /me/settings` | user | none | none to `UserSettings` | Per-user settings (replaces the global `AppSetting`). |
| `PUT /me/settings` | user | none | `UserSettings` to `UserSettings` | Full replace. |
| `GET /me/consents` | user | none | none to `Consent[]` | Current accepted versions and withdrawals. |
| `PUT /me/consents/{kind}` | user | none | `{ version: string, granted: boolean }` to `Consent` | Kinds (`consents.kind`): `terms`, `privacy`, `ai_processing`, `marketing_email`, `push_notifications`, `analytics`. Appends a `consents` row (history kept). Withdrawing `ai_processing` makes every AI endpoint return `ai_consent_required`; running agent runs are cancelled. Marketing opt-out also honors one-click unsubscribe. |
| `POST /me/export` | user, re-auth within 10 minutes | 1 per day | none to 202 `DataExport` | Inserts `data_exports`, enqueues the export job. Zip of JSON plus a CSV or PDF per trip, emailed as a signed link valid 7 days. `429 rate_limited` on a second request within a day. |
| `GET /me/export` | user | none | none to `DataExport[]` | Status list (`data_exports.status`): `requested`, `processing`, `ready`, `expired`, `failed`. |
| `GET /me/export/{export_id}/download` | user | none | 302 to a signed R2 URL (5 minutes), or to the local storage route below when `STORAGE_BACKEND=local` | `410` if expired. |
| `GET /storage/{object_key}?expires=&sig=` | signed URL | none | none to the stored bytes | Local only: when `STORAGE_BACKEND=local` the API serves stored objects (exports, uploads) from `.data/storage` through this read route, with a short-lived signed URL (HMAC over key and expiry, 5 minutes), so exports work without R2. The route is not registered when `STORAGE_BACKEND=r2` and is not in the production OpenAPI. The key resolves under `.data/storage`; any path that escapes it (`..`, an absolute path) is `404`, as is a bad or expired signature. |
| `POST /me/deletion` | user, re-auth within 10 minutes | 1 per day | `{ confirm: "DELETE", transfers?: { trip_id: Uuid, new_owner_id: Uuid }[], delete_trip_ids?: Uuid[] }` to 202 `DeletionRequest` | Inserts `deletion_requests`. At once: sessions and refresh tokens revoked, Apple token revoked, push tokens cleared, pending invites cancelled, status `pending_deletion`. Sole-owner trips with other members and no choice: 30 day wait for a member to accept a transfer, then deleted. Hard purge at 30 days (this includes `trip_imports`, stored feed URLs, `referral_codes` and calendar tokens). Does not cancel store subscriptions (response includes `manage_subscription_url`). |
| `POST /me/deletion/cancel` | user | within grace | none to `Me` | Restores `active`. Sessions stay revoked; the user signs in again. |
| `GET /me/deletion` | user | none | none to `DeletionRequest \| null` | Progress checklist and purge date. |
| `DELETE /me/ai-history` | user | none | none to 204 | Deletes the caller's `runs`, `run_events` and AI-created `notes`. Financially required `ai_usage` rows are kept with `user_id` set to null (06 section 12.4). |

```ts
type ProfileUpdate = Partial<{
  display_name: string; locale: string; timezone: string
  home_currency: string; home_airports: Iata[]
}>
type UserSettings = {                          // stored in users.prefs; hide_booking_links is the users.hide_booking_links column
  units: "metric" | "imperial"; time_format: "12h" | "24h"; week_starts_on: 0 | 1 | 6
  hide_booking_links: boolean                 // "Hide booking links" switch
  default_trip_ai_enabled: boolean
  notifications: { price_alerts: boolean; trip_changes: boolean; reminders: boolean }
}
type Consent = { kind: string; version: string; granted: boolean; accepted_at: string }
type DataExport = { id: Uuid; status: string; requested_at: string; ready_at: string | null; expires_at: string | null }
type DeletionRequest = {
  id: Uuid; status: "pending" | "grace" | "purging" | "completed" | "cancelled"
  scheduled_purge_at: string; checklist: { step: string; done: boolean }[]
  manage_subscription_url: string
}
```

### 5.3 Households (Family)

Later: Phase 2 (households, the Family plan and pooled credits).

### 5.4 Trips

| Endpoint | Auth | Gate and cost | Request and response | Errors and side effects |
|---|---|---|---|---|
| `GET /trips` | user | none | `?status=&include=joined,owned&limit&cursor&updated_since` to `Page<TripSummary>` | Trips where the caller is a member, excluding soft-deleted. `ETag` supported. |
| `POST /trips` | user | `active_trips` | `TripCreate` to 201 `Trip` | Creates `trips`, the owner `trip_members` row, `trip_destinations`, and `trip_people` links. Free owner with 2 active trips gets 402 `limit_reached` (reason `trip_limit`, `free_path`: "Archive a trip or join trips other people plan"). Joined trips never count. |
| `GET /trips/{trip_id}` | viewer | none | none to `Trip` | `ETag` is the trip version. |
| `PATCH /trips/{trip_id}` | editor (status, `ai_enabled` and `editors_can_invite`: owner) | versioned | `TripUpdate` to `Trip` | Replaces destinations and travelers when sent. Changing dates re-derives `itinerary_days`; items on removed days become unscheduled, never deleted. Sets cover from the first destination image. |
| `DELETE /trips/{trip_id}` | owner | none | none to 204 | Soft delete (`deleted_at`), 30 days in trash. Cancels active agent runs, revokes invites and share links, and disables the calendar feed token. |
| `POST /trips/{trip_id}/restore` | owner | within 30 days | none to `Trip` | Undeletes. |
| `POST /trips/{trip_id}/transfer` | owner | target is a member | `{ new_owner_id: Uuid }` to `Trip` | New owner becomes `owner`, previous owner becomes `editor`. Capabilities re-evaluated against the new owner's tier; a lapsed tier yields `limited: true`. Notifies both. |
| `POST /trips/{trip_id}/leave` | member (not owner) | none | none to 204 | Removes the caller; contributions stay attributed to "Former member". Owner must transfer first (`409 state_conflict`). |
| `POST /trips/{trip_id}/refresh-info` | editor | none | none to 202 | Re-fetches destination summaries and images (Wikipedia, Geoapify). No credits, counted against a per-trip daily limit. |
| `GET /trips/{trip_id}/activity` | viewer | none | `?limit&cursor` to `Page<ActivityEvent>` | Reverse-chronological change feed ("Sam added Hotel Avenida"). |

```ts
type TripCreate = {
  name: string                                   // 1 to 120 chars
  start_date?: string | null; end_date?: string | null     // both or neither
  home_currency?: string                         // defaults to profile
  notes?: string                                 // max 10000
  destinations?: DestinationIn[]                 // max 12
  traveler_ids?: Uuid[]                          // people; defaults to the "Me" person
  template?: "blank" | "city_break" | "road_trip" | "beach_week" | null
}
type TripUpdate = Partial<Omit<TripCreate, "template">> & {
  status?: "planning" | "booked" | "done" | "archived"
  ai_enabled?: boolean
  editors_can_invite?: boolean                   // owner only
  version?: number                               // or If-Match
}
type DestinationIn = {
  id?: Uuid | null; name: string; region?: string | null; country?: string | null
  country_code?: string | null; kind?: string | null
  lat: number; lon: number; timezone?: string | null; bbox?: [number, number, number, number] | null
  geoapify_place_id?: string | null
}
type TripSummary = Pick<Trip, "id" | "version" | "name" | "status" | "start_date" | "end_date"
  | "cover" | "my_role" | "member_count" | "updated_at"> & { destinations_label: string; limited: boolean }
type ActivityEvent = { at: string; actor: Attribution; verb: string; entity_type: string; entity_id: Uuid | null; summary: string }   // from activity_log; its bigint id is never exposed
```

### 5.5 Destinations

Destinations are nested in `Trip` and edited through `PATCH /trips/{id}`; these routes are for single-item edits and for typeahead.

| Endpoint | Auth | Gate and cost | Request and response | Errors and side effects |
|---|---|---|---|---|
| `GET /geo/destinations` | user | none | `?q=&limit=8` to `DestinationSuggestion[]` | Typeahead over Geoapify geocoding (cached in `places_cache`). Per-user quota. |
| `GET /trips/{trip_id}/destinations` | viewer | none | none to `Destination[]` | Ordered. |
| `POST /trips/{trip_id}/destinations` | editor | max 12 | `DestinationIn` to 201 `Destination` | Appends; enqueues summary and image fetch (`info_status: "pending"`). |
| `PATCH /trips/{trip_id}/destinations/{destination_id}` | editor | none | `Partial<DestinationIn>` to `Destination` | |
| `DELETE /trips/{trip_id}/destinations/{destination_id}` | editor | none | 204 | Days pointing at it get `destination_id: null`. |
| `PUT /trips/{trip_id}/destinations/order` | editor | none | `{ ids: Uuid[] }` to `Destination[]` | Must contain every id exactly once. |
| `GET /airports` | user | none | `?q=&limit=10` to `Airport[]` | From `airports`. Cached 24 hours (`Cache-Control: private, max-age=86400`). |
| `GET /airports/nearby` | user | none | `?lat&lon&radius_km=150` to `NearbyAirport[]` | Used only when the user taps "near me"; coordinates are not stored. |

```ts
type Destination = DestinationIn & {
  id: Uuid; position: number; summary: string | null; wiki_url: string | null
  image_url: string | null; info_status: "pending" | "ready" | "not_found" | "failed" | "skipped"
}
type DestinationSuggestion = Omit<DestinationIn, "id"> & { label: string }
type Airport = { iata: Iata; name: string; city: string; country_code: string; lat: number; lon: number }
type NearbyAirport = Airport & { distance_km: number }
```

### 5.6 Members, invites and share links

| Endpoint | Auth | Gate and cost | Request and response | Errors and side effects |
|---|---|---|---|---|
| `GET /trips/{trip_id}/members` | viewer | none | none to `Member[]` | Includes pending invites for owners. |
| `PATCH /trips/{trip_id}/members/{user_id}` | owner | none (the member already holds a collaborator slot) | `{ role: "editor" \| "viewer" }` to `Member` | Cannot set `owner` (use transfer). Limited trips cannot raise a role. Changing editor and viewer does not change `collaborators_used`. |
| `DELETE /trips/{trip_id}/members/{user_id}` | owner | none | none to 204 | Access ends immediately. Linked person detached ("Former member" option). |
| `PUT /trips/{trip_id}/members/me/traveler` | member | none | `{ person_id: Uuid }` to `Member` | Answers "Which traveler are you?"; sets `people.linked_user_id`. A person links to one user per trip. |
| `DELETE /trips/{trip_id}/members/me/traveler` | member | none | none to 204 | Clears the caller's own link (`people.linked_user_id` to null). Idempotent. |
| `POST /trips/{trip_id}/invites` | owner (editors: viewer invites only if `editors_can_invite`) | `can_invite` (free collaborator slot), 30 per day, 20 pending | `InviteCreate` to 201 `Invite` | Random 128 bit token, stored hashed. The raw token appears only in this response and the emailed link. Email sent when `email` set. Invite limit: a pending invite holds a slot until it is used, revoked or expires, and a link invite holds `max_uses` slots. A Free owner has 1 slot per trip, so a second invite gets 402 `limit_reached`, reason `sharing`, with a paywall hint (`free_path`: "Share a read-only link, or remove your collaborator"). Plus and Trip Pass trips have 6 slots. When an owner's paid tier lapses, members beyond the owner's slots stay on the trip as viewers (`limited: true`) and nobody is removed. |
| `GET /trips/{trip_id}/invites` | owner | none | none to `Invite[]` | No tokens. |
| `DELETE /trips/{trip_id}/invites/{invite_id}` | owner | none | 204 | Revokes. |
| `GET /invites/{token}` | none (rate limited) | none | none to `InvitePreview` | Public preview for the landing page: trip name, cover, inviter display name, role. No dates or places. `410 invite_expired` for bad tokens (same response for unknown and expired). |
| `POST /invites/{token}/accept` | user | none | `{ person_id?: Uuid }` to 200 `Trip` | Redeems server side; the email need not match (Apple relay). Adds `trip_members`; single-use invites are consumed; link invites increment `use_count` up to `max_uses`. Free accounts join free and do not count toward their 2 active trips. `409 already_member` returns the trip id. |
| `GET /trips/{trip_id}/share-links` | owner | none | none to `ShareLink[]` | |
| `POST /trips/{trip_id}/share-links` | owner | none (every tier; 5 active links per trip) | `ShareLinkCreate` to 201 `ShareLink` | Read-only public link `https://hermi.world/s/<token>`. Share links never count as collaborators. Default expiry 90 days (maximum 365). Redaction flags hide hotel address, prices, notes and people by default. `indexable: true` lets search engines list the page and is accepted only while `people`, `notes` and `hotel_address` redaction stay on. |
| `PATCH /trips/{trip_id}/share-links/{link_id}` | owner | none | `Partial<ShareLinkCreate>` to `ShareLink` | |
| `DELETE /trips/{trip_id}/share-links/{link_id}` | owner | none | 204 | Revokes; later views return `410 share_link_revoked`. |
| `GET /unsubscribe?t={signed_token}` | none (public, signed token) | none | none to an HTML page | Shows a confirm page with one button that posts the same link. Changes nothing, so a mail scanner that opens the link cannot unsubscribe anyone. `400 invalid_unsubscribe_link` for a bad or tampered token. |
| `POST /unsubscribe?t={signed_token}` | none (public, signed token) | none | none (or form `List-Unsubscribe=One-Click`) to `{ unsubscribed: true }` | One-click unsubscribe from an email link (RFC 8058 `List-Unsubscribe-Post`). The token is signed with `UNSUBSCRIBE_SECRET`, names one user and a scope (`marketing` withdraws the `marketing_email` consent; `all` also switches non-account email off), and never expires. Idempotent. `400 invalid_unsubscribe_link` for a bad token. |
| `GET /shared/{token}` | none (per-IP and per-token limit) | none | none to `SharedTrip` | Public read of the redacted presentation data (5.15). `Cache-Control: public, max-age=60`. Sends `X-Robots-Tag: noindex` unless the link is `indexable`. Pages for search come from the same data (see 5.28). Never includes affiliate click ids; the "Book the plan" slide links come from `POST /shared/{token}/outbound` (5.21). |

```ts
type Member = {
  user_id: Uuid; display_name: string | null; role: Role
  person_id: Uuid | null; joined_at: string; invited_by: Attribution | null
}
type InviteCreate = {
  role: "editor" | "viewer"
  email?: string                      // single use, emailed
  max_uses?: number                   // link invites, 1 to 6, default 1; Free owners: 1
  expires_in_days?: number            // 1 to 14, default 7
}
type Invite = {
  id: Uuid; role: "editor" | "viewer"; email: string | null
  url?: string                        // only in the create response
  uses_left: number /* max_uses minus use_count */; expires_at: string; created_at: string; status: "pending" | "used" | "expired" | "revoked"
}
type InvitePreview = { trip_name: string; cover_url: string | null; inviter_name: string; role: "editor" | "viewer" }
type ShareLinkCreate = {
  expires_in_days?: number            // 1 to 365, default 90; every share link expires
  redact: { hotel_address: boolean; prices: boolean; notes: boolean; people: boolean }   // all true by default; maps to redact_address, redact_prices, redact_notes, redact_people
  show_book_slide: boolean            // "Book the plan" last slide, default true
  indexable?: boolean                 // allow search engines, default false
}
type ShareLink = Required<ShareLinkCreate> & { id: Uuid; url: string; created_at: string; expires_at: string; view_count: number; revoked_at: string | null }
type SharedTrip = { trip_name: string; presentation: Presentation; cta: { label: "Get the app to edit"; url: string }; book_slide: AffiliateOffer[] | null }
```

### 5.7 People

A person is a traveler profile owned by a user. It is planning data, not an account. Names of people who are not members never go to AI providers ("Traveler 1" is used instead).

| Endpoint | Auth | Gate and cost | Request and response | Errors and side effects |
|---|---|---|---|---|
| `GET /people` | user | none | none to `Person[]` | The caller's own people plus linked people visible through shared trips (co-members only). |
| `POST /people` | user | max 30 per user | `PersonIn` to 201 `Person` | `owner_user_id` is the caller. |
| `PUT /people/{person_id}` | owner of the person | none | `PersonIn` to `Person` | Linked people can only be edited by their own user for name and airports. |
| `DELETE /people/{person_id}` | owner of the person | none | 204 | `409 state_conflict` if the person is the only traveler on a trip the caller does not own; otherwise removed from `trip_people`, historic votes keep "Former traveler". |
| `PUT /trips/{trip_id}/travelers` | editor | none | `{ person_ids: Uuid[] }` to `Person[]` | Replaces `trip_people` for the trip (capped by `travelers_per_trip`: Free 2, Plus and Trip Pass 8; over the cap is 402 `limit_reached`, reason `traveler_limit`). |

```ts
type PersonIn = { name: string /* 1..60 */; color: string /* #rrggbb */; home_airports: Iata[] /* max 6 */ }
type Person = PersonIn & { id: Uuid; linked_user_id: Uuid | null; is_me: boolean }
```

### 5.8 Flights

Flight data follows the existing route and quote model. A route is a search definition; fare observations are quotes seen by a source. Cached fares (Travelpayouts Data API) are available to every tier; live fares (SerpApi behind a provider interface, flag `serpapi_live_fares`) need a live route slot and cost 1 credit per user-triggered live check. The scheduled daily live check of a tracked route does not cost credits; it draws on the route slot and the provider-spend ceiling. Sorting is by price only; providers never influence order.

| Endpoint | Auth | Gate and cost | Request and response | Errors and side effects |
|---|---|---|---|---|
| `GET /trips/{trip_id}/routes` | viewer | none | none to `Route[]` | |
| `POST /trips/{trip_id}/routes` | editor | `routes_per_trip` cap (Free 1, Plus 5, Trip Pass 3; `limit_reached`, reason `live_routes` only when `mode: "live"`) | `RouteIn` to 201 `Route` | `mode: "cached"` (default) uses Travelpayouts only. `mode: "live"` needs a free live slot and departure within 120 days, else 402 `limit_reached`. Enqueues a first cached refresh. |
| `PUT /routes/{route_id}` | editor | versioned | `RouteIn` to `Route` | Switching `mode` to `live` re-checks the gate. Changing search fields clears nothing; old observations stay. |
| `DELETE /routes/{route_id}` | editor | none | 204 | Frees the live slot. Observations kept 13 months for history. |
| `POST /trips/{trip_id}/flights/refresh` | editor | none (cached only) | `{ route_ids?: Uuid[] }` to 202 `Job` | Refreshes cached fares for these routes (max 20). Does not call live providers. Per-trip limit 10 an hour. |
| `POST /trips/{trip_id}/flights/live-search` | editor | `live_route` (route in `live` mode), `credits(1)` | `{ route_id: Uuid }` with `Idempotency-Key` to 202 `LiveSearchJob` | Reserves 1 credit (`live_search`), enqueues a SerpApi call, writes `provider_calls` and `fare_observations`. Settles on success; releases on `provider_error`. For trips with a pass, also increments `trip_passes.live_checks_used` (`live_checks_max`, 60). Returns `from_cache: true` and charges 0 when a fresh observation (under 6 hours) already exists in the shared cache. 402, 429 `provider_budget_exhausted`, 402 `limit_reached`. |
| `GET /live-search/{job_id}` | the caller | none | none to `LiveSearchJob` | Poll until `done` or `failed`. |
| `GET /trips/{trip_id}/flights/best` | viewer | none | `?route_id=&limit=20&include_hidden=false&sort=price` to `Fare[]` | Sorted by price ascending then observed time. `sort` accepts `price`, `duration`, `stops` only. |
| `GET /trips/{trip_id}/flights/summary` | viewer | none | none to `RouteSummary[]` | Cheapest fare, last check time, fare count and chosen fare per route. `ETag`. |
| `GET /routes/{route_id}/fares` | viewer | none | `?limit&cursor&source=&since=` to `Page<Fare>` | All observations. |
| `PATCH /fares/{fare_id}` | editor | none | `{ hidden?: boolean, suspect?: boolean }` to `Fare` | Hides or flags a fare for this trip (`trip_fare_links`), never deletes shared data. |
| `GET /routes/{route_id}/price-history` | viewer | none | none to `PriceHistory` | Daily minimum by source, typical low and high, price level. |
| `GET /routes/{route_id}/date-grid` | viewer | none | none to `DateGridCell[]` | Cheapest fare per departure and return pair. |
| `PUT /routes/{route_id}/choice` | editor | none | `{ fare_id: Uuid, paid?: Money, booked_at?: string }` to `Trip` | Writes `chosen_flights`. Trip dates derive from chosen flights when dates are unset. Checklist items "Flights booked", "Airport transfer" and "Travel insurance" become visible (5.16). When `paid` or `booked_at` is sent the flight is also marked booked (see `choice/booked`). Emits `flight_chosen`. |
| `DELETE /routes/{route_id}/choice` | editor | none | none to `Trip` | |
| `POST /routes/{route_id}/choice/booked` | editor | none | `BookedIn` to `Trip` | Marks the chosen flight as booked by the user (used by the checklist): sets `chosen_flights.booked_at` (default now) and, when sent, `paid_amount_minor` and `paid_currency`. `{ booked: false }` clears all three. Emits `flight_booked`. `409 state_conflict` when no flight is chosen. |
| `GET /routes/{route_id}/booked-fare` | viewer | none | none to `BookedFare \| null` | What was paid, the cheapest matching fare now and the drop, for the route's booked flight. `null` until a flight is booked. Private amounts: the paid amount is shown to members only, never in share links or the calendar feed. |
| `PUT /routes/{route_id}/booked-fare` | editor | booked flight | `{ paid: Money \| null, booked_at?: string }` to `BookedFare` | Sets or corrects what was paid. `paid: null` clears the amount and stops the drop alert (the flight stays booked). Currency must be in `fx_rates`. |
| `GET /trips/{trip_id}/price-alerts` | viewer | none | none to `PriceAlert[]` | |
| `POST /routes/{route_id}/price-alerts` | editor | `price_alerts` cap per account (Free 1, cached fares only; Plus 3; a pass gives 2 on its trip). The booked-fare drop alert does not count toward this cap | `PriceAlertIn` to 201 `PriceAlert` | Writes `price_alerts`. Free alerts run on cached fares only and never trigger live calls. `402 limit_reached` with a paywall hint otherwise. |
| `PATCH /price-alerts/{alert_id}` | editor | none | `Partial<PriceAlertIn>` to `PriceAlert` | |
| `DELETE /price-alerts/{alert_id}` | editor | none | 204 | |

```ts
type RouteIn = {
  label?: string | null
  origin_codes: Iata[]; destination_codes: Iata[]          // 1..4 each
  trip_type: "round_trip" | "one_way"
  depart_from: string; depart_to: string
  return_from?: string | null; return_to?: string | null
  min_nights?: number | null; max_nights?: number | null   // 1..60
  adults: number; children: number                           // 1..9, 0..8
  cabin: "economy" | "premium_economy" | "business" | "first"
  max_stops?: 0 | 1 | 2 | null
  mode: "cached" | "live"                                // stored as flight_routes.is_live
  active: boolean
  version?: number
}
type Route = Omit<RouteIn, "version"> & {
  id: Uuid; trip_id: Uuid; version: number
  chosen_fare_id: Uuid | null; booked: BookedFare | null; last_checked_at: string | null
  next_live_check_at: string | null                         // live mode only; derived from last_checked_at and the daily jitter window, not stored
  created_at: string; updated_at: string
}
type Fare = {
  id: Uuid; route_id: Uuid
  source: "travelpayouts" | "serpapi" | "licensed" | "agent" | "manual"      // id is trip_fare_links.id; fare_observations.id (bigint) is never exposed
  confidence: "cached" | "live" | "indicative"             // indicative: an agent saw it on a page during the run
  origin: Iata; destination: Iata; depart_date: string; return_date: string | null
  price: Money; price_home: Money | null; passengers: number
  airlines: string[]; stops_out: number | null; stops_back: number | null
  duration_out_min: number | null; duration_back_min: number | null
  depart_at_local: string | null; flight_numbers: string[] | null
  book_offer: AffiliateOffer | null                          // partner "Book on <provider>" (5.21)
  airline_search_url: string | null                          // non-affiliate route
  source_url: string | null; observed_at: string; age_label: string   // "cached 6 h ago"
  suspect: boolean; hidden: boolean
}
type RouteSummary = {
  route_id: Uuid; cheapest: Fare | null; last_checked_at: string | null
  fare_count: number; chosen: Fare | null; chosen_latest: Fare | null
}
type PriceHistory = {
  currency: string
  points: { day: string; source: string; price: Money }[]
  google: { at: string; price: Money }[]
  typical_low: Money | null; typical_high: Money | null; price_level: "low" | "typical" | "high" | null
}
type DateGridCell = { fare_id: Uuid; depart_date: string; return_date: string | null; price: Money; source: string; observed_at: string }
type PriceAlertIn = { target_price: Money /* threshold_minor + currency */; notify: { push: boolean; email: boolean } /* channel_push, channel_email */; active: boolean }
type PriceAlert = PriceAlertIn & { id: Uuid; route_id: Uuid; last_notified_at: string | null; last_notified_price: Money | null }
type BookedIn = { booked: boolean; paid?: Money | null; booked_at?: string | null }   // paid maps to chosen_flights.paid_amount_minor and paid_currency
type BookedFare = {
  route_id: Uuid; booked_at: string | null
  paid: Money | null                                        // total for the route's party, as the user entered it
  current: { fare_id: Uuid; price: Money; observed_at: string; confidence: "cached" | "live" } | null   // cheapest matching fare now, in the paid currency
  drop: Money | null                                        // paid minus current when positive
  alert_active: boolean                                     // paid is set, the flight is booked and departure is ahead
  last_alert_at: string | null; checked_at: string | null
  airline_search_url: string | null                         // plain link to the airline, never a partner link
  note: string                                              // "Check the airline's change and credit rules before you rebook."
}
type LiveSearchJob = {
  id: Uuid; route_id: Uuid; status: "queued" | "running" | "done" | "failed"
  fares_added: number; credits: CreditReceipt; error_code: string | null
}
type Job = { id: Uuid; status: "queued" | "running" | "done" | "failed"; location: string }
```

**Booked-fare drop alert.** When a flight is marked booked with a paid amount, Hermi keeps watching that exact itinerary and tells the traveler if the same trip later costs less. It is a notification, not a refund promise.

- Matching: a `fare_observations` row linked to the route (`trip_fare_links`) with the same origin, destination, departure date, return date, cabin and party size as the chosen flight, not `suspect` or `hidden`, with `confidence` `cached` or `live` (an `indicative` agent fare is shown on the screen but never triggers a push). Different currency: converted to the paid currency with the latest `fx_rates` row.
- Trigger (settled values): the cheapest matching fare is lower than `paid` by at least 5% and by at least the equivalent of 10 USD after conversion. A flight is alerted at most once every 7 days, and a later alert also needs a price below the last alerted one. Alerts are deduplicated by the notification key `booked_drop:{chosen_flight_id}:{price_minor}`. The numbers are the `setting_booked_fare_drop` rules (`min_drop_pct` 5, `min_drop_usd` 10, `min_days_between` 7).
- Delivery: push and email through the normal notification path, honoring `notifications.price_alerts`. Copy: "You paid $412. It is now $368. Check the airline's change and credit rules." The only action links are the trip screen and the airline's own change and credit rules page (`airline_search_url`); never a partner link, and no claim that a refund or credit is available.
- Cost and limits: no credits, no live calls beyond the route's own scheduled checks (cached refresh for Free, live routes on Plus and passes). Runs for every tier until the departure date or until `paid` is cleared. Emits `booked_fare_drop_sent`.

### 5.9 Lodging

Lodging covers options the user saves or pastes, votes, comparison, and rental search. Rule: the server never fetches Airbnb, Vrbo or Booking.com pages, and never rewrites a pasted link. `url` is stored exactly as pasted.

| Endpoint | Auth | Gate and cost | Request and response | Errors and side effects |
|---|---|---|---|---|
| `GET /trips/{trip_id}/lodging` | viewer | none | `?status=&sort=created&limit&cursor&updated_since` to `Page<Lodging>` | `sort` accepts `created`, `price`, `rating`, `votes`. The response states the sort in `sorted_by`. |
| `POST /trips/{trip_id}/lodging` | editor | `saved_lodging_per_trip` (402 `limit_reached`, trigger `ninth_stay`) | `LodgingIn` to 201 `Lodging` | Writes `lodging_options`. Stores `site` from the host of `url`. `added_via`: `paste`, `bookmarklet`, `partner_search`, `agent`, `manual`. Activity feed entry. |
| `GET /lodging/{option_id}` | viewer | none | none to `Lodging` | |
| `PATCH /lodging/{option_id}` | editor | versioned | `Partial<LodgingIn>` to `Lodging` | `status` moving to `booked` also offers to add the stay to the itinerary days (client prompt; no server side effect). |
| `DELETE /lodging/{option_id}` | editor | none | 204 | Removes votes. |
| `PUT /lodging/{option_id}/votes/me` | viewer | none | `{ voted: boolean }` to `Lodging` | Adds or removes the caller's heart in `lodging_votes` (`user_id`, and the linked `person_id`). Viewers may vote. |
| `GET /trips/{trip_id}/lodging/compare` | viewer | none | `?ids=a,b,c` (2 to 4) to `LodgingCompare` | Side by side table: price per night and total in trip home currency, rating, bedrooms, beds, baths, distance to destination center and to chosen itinerary anchors, votes, pros and cons. Sorted by the order of `ids`, never by commission. |
| `POST /lodging/parse-link` | user | none | `{ url: string, check_in?, check_out?, guests? }` to `LinkParse` | Parses only the URL text: host, stay dates and guests in query parameters, listing id. No network request to the host. Blocked-host rule: for `airbnb.*`, `vrbo.*`, `booking.*` and the Expedia Group brands the response has `fetch_allowed: false`; `title`, `photos` and `description` are always empty for them and the client asks the user to type or use the bookmarklet. Any request that sets a `fetch` flag on these hosts gets `422 blocked_domain`. For other hosts it never fetches either in the hosted API; link previews are disabled server side and come only from the user's own clipboard or bookmarklet payload. |
| `POST /trips/{trip_id}/lodging/rental-search` | editor | `credits(1)` (`live_search`), shared cache free for 6 hours | `RentalSearchIn` with `Idempotency-Key` to `RentalSearchResult` | Searches licensed sources only (SerpApi Google Vacation Rentals through the provider interface, Stay22 and partner search). Reserves 1 credit; repeats of the same search within 6 hours return `cached: true` and charge 0. Sorted by `price` or `rating` only, with the sort statement in `sorted_by`. Writes `provider_calls`. |
| `POST /trips/{trip_id}/lodging/from-offer` | editor | none | `{ offer_ref: string }` to 201 `Lodging` | Saves an offer from a search result (`offer_ref` is an opaque server token valid 24 hours). Sets `added_via: "partner_search"` and stores the partner book offer separately from the user's `url`. |
| `GET /lodging/{option_id}/book-offers` | viewer | none | none to `AffiliateOffer[]` | Labeled partner "Book via partner" button and "Compare on other sites" search links built from URL text and trip dates, without fetching. Empty for Airbnb (plain links only) and when `hide_booking_links` is set returns plain "Open on partner site" links. |

```ts
type LodgingIn = {
  title: string; url?: string | null
  check_in?: string | null; check_out?: string | null; guests?: number | null
  price_total?: Money | null; price_per_night?: Money | null
  photos?: string[]                          // max 30, user-supplied or from search results
  location_name?: string | null; lat?: number | null; lon?: number | null
  bedrooms?: number | null; beds?: number | null; baths?: number | null
  rating?: number | null; review_count?: number | null
  notes?: string; pros?: string; cons?: string
  status?: "candidate" | "shortlisted" | "booked" | "rejected"
  favorite?: boolean
  added_via?: "paste" | "bookmarklet" | "partner_search" | "agent" | "manual"
  version?: number
}
type Lodging = Omit<LodgingIn, "version" | "price_total" | "price_per_night"> & {
  id: Uuid; trip_id: Uuid; version: number; site: string | null; nights: number | null
  price_total: Money | null; price_per_night: Money | null; price_home_total: Money | null
  votes: { user_id: Uuid; person_id: Uuid | null }[]                     // hearts (lodging_votes rows)
  vote_summary: { hearts: number }
  added_by: Attribution; created_at: string; updated_at: string
}
type LodgingCompare = { columns: Uuid[]; rows: { key: string; label: string; values: (string | number | null)[] }[]; home_currency: string }
type LinkParse = {
  url: string; site: string | null; fetch_allowed: false
  check_in: string | null; check_out: string | null; guests: number | null
  listing_id: string | null; title: null; photos: []; note: string   // "We never change your links."
}
type RentalSearchIn = { check_in: string; check_out: string; adults: number; children: number; place?: string; max_price?: Money; sort?: "price" | "rating" }
type RentalOffer = {
  offer_ref: string; title: string; site: string | null; kind: string | null; photos: string[]
  price_total: Money | null; price_per_night: Money | null; rating: number | null; review_count: number | null
  lat: number | null; lon: number | null; sleeps: number | null; bedrooms: number | null; beds: number | null; baths: number | null
  details: string[]; observed_at: string
  book_offer: AffiliateOffer | null; save_first: true          // save to shortlist is the first action in the UI
}
type RentalSearchResult = { offers: RentalOffer[]; cached: boolean; sorted_by: string; credits: CreditReceipt }
```

### 5.10 Itinerary

The itinerary is `itinerary_days` (one per trip date, created from the trip dates) and `itinerary_items` (an activity, meal, transport, stay or note entry, scheduled or in the unscheduled pool). This replaces the existing `/activities` routes.

| Endpoint | Auth | Gate and cost | Request and response | Errors and side effects |
|---|---|---|---|---|
| `GET /trips/{trip_id}/days` | viewer | none | `?updated_since` to `Day[]` | Every date in the trip range, with counts and first and last items. Days outside the range that hold items are included with `in_trip: false`. `ETag`. |
| `PUT /trips/{trip_id}/days/{day}` | editor | versioned | `DayUpdate` to `Day` | `day` is `YYYY-MM-DD`. Creates the row if needed. |
| `GET /trips/{trip_id}/items` | viewer | none | `?day=&unscheduled=true&category=&limit&cursor&updated_since` to `Page<Item>` | Ordered by day, then `sort_order`. |
| `POST /trips/{trip_id}/items` | editor | none | `ItemIn` to 201 `Item` | Appends to the end of the day (or the pool) with the next `sort_order`. If `place` is given, saves it to `saved_places` when not present and stores `source: "place_search"`; otherwise `source: "manual"`. Fails `422 validation_failed` if `end_time` precedes `start_time`. |
| `GET /items/{item_id}` | viewer | none | none to `Item` | |
| `PATCH /items/{item_id}` | editor | versioned | `ItemUpdate` to `Item` | Moving `day` is allowed here for a simple change; use `/move` to also set `sort_order`. |
| `DELETE /items/{item_id}` | editor | versioned | 204 | |
| `POST /trips/{trip_id}/days/{day}/reorder` | editor | none | `{ ids: Uuid[], version_map?: Record<Uuid, number> }` to `Item[]` | Sets `sort_order` by order for every item on that day. `ids` must be exactly the current items of the day else `409 version_conflict` with the current order in `current`. |
| `POST /items/{item_id}/move` | editor | versioned | `{ day: string \| null, before_id?: Uuid \| null, start_time?: string \| null }` to `Item[]` | Moves between days or to the pool (`day: null`) and places before `before_id` (end if null). Returns every item whose position changed on both days. |
| `POST /trips/{trip_id}/items/bulk` | editor | max 50 | `{ items: ItemIn[], source?: "ai_draft" \| "import" }` to 201 `Item[]` | Used when accepting an AI draft or a booking import (`source` is stored on each item). One transaction. |
| `GET /trips/{trip_id}/items/{item_id}/book-offers` | viewer | none | none to `AffiliateOffer[]` | "Tickets" offers for bookable items (Viator match by name and coordinates). Empty for parks and viewpoints. |
| `GET /trips/{trip_id}/days/{day}/suggestions` | viewer | none | none to `ThingToDo[]` | Viator "things to do" near the day's plan, sorted by rating then distance, labeled as suggestions. Empty when there is no real match. No credits. |

```ts
type ItemIn = {
  title: string                                          // 1..200
  day?: string | null; start_time?: string | null; end_time?: string | null
  category: "sights" | "museum" | "food" | "nature" | "nightlife" | "shopping" | "travel" | "other"
  status?: "idea" | "planned" | "booked"
  location_name?: string | null; address?: string | null; lat?: number | null; lon?: number | null
  url?: string | null; notes?: string                    // max 4000
  cost?: Money | null                                    // estimated_cost_minor + cost_currency
  place?: { provider: "geoapify"; id: string; data?: Record<string, unknown> } | null
  version?: number
}
type ItemUpdate = Partial<ItemIn> & { version?: number }
type Item = Omit<ItemIn, "place" | "version"> & {
  id: Uuid; trip_id: Uuid; sort_order: number; version: number
  source: "manual" | "place_search" | "ai_draft" | "agent" | "import"     // itinerary_items.source: where the item came from; an accepted AI draft stays flagged
  place_provider: string | null; place_id: string | null; place_data: Record<string, unknown> | null
  bookable: boolean; added_by: Attribution; created_at: string; updated_at: string
}
type DayUpdate = { title?: string; notes?: string; destination_id?: Uuid | null; version?: number }
type Day = {
  day: string; title: string; notes: string; destination_id: Uuid | null; destination_name: string | null
  timezone: string | null; in_trip: boolean; item_count: number; version: number
  first: { title: string; start_time: string | null } | null; last: { title: string; start_time: string | null } | null
}
type ThingToDo = { product_ref: string; title: string; rating: number | null; price_from: Money | null; price_observed_at: string | null; distance_m: number; source: "viator"; book_offer: AffiliateOffer; label: "Suggestion" }
```

### 5.11 Places

Geoapify is the place source; results are cached in `places_cache` per provider terms. Results are ranked by relevance and distance only. Saving a place never calls a paid provider.

| Endpoint | Auth | Gate and cost | Request and response | Errors and side effects |
|---|---|---|---|---|
| `GET /places/search` | user | per-user quota (200 an hour) | `?q=&lat=&lon=&radius_m=&category=&destination_id=&trip_id=&limit=20` to `PlaceSearchResult` | Text or category search around a point or the destination boundary (`geoapify_place_id`). Response includes the required attribution string and `cached`. `429` on quota. |
| `GET /places/{place_id}` | user | none | none to `PlaceDetails` | `place_id` is our id (`geoapify:<id>`). Adds Wikipedia summary when `wikidata` or `wikipedia` tags exist. Cached per terms. |
| `GET /places/{place_id}/book-offers` | user | none | none to `AffiliateOffer[]` | "Tickets" or "Book a table" chips on the detail view only, when a real match exists. |
| `GET /trips/{trip_id}/saved-places` | viewer | none | `?limit&cursor` to `Page<SavedPlace>` | |
| `POST /trips/{trip_id}/saved-places` | editor | none | `{ place_id: string, note?: string }` to 201 `SavedPlace` | Writes `saved_places` (idempotent on trip and place). |
| `DELETE /trips/{trip_id}/saved-places/{saved_id}` | editor | none | 204 | |

```ts
type Place = {
  id: string; provider: "geoapify"; name: string; local_name: string | null
  category: string; kinds: string[]; address: string | null; lat: number; lon: number
  distance_m: number | null; website: string | null; opening_hours: string | null; phone: string | null
  wikidata: string | null; wikipedia: string | null; has_details: boolean
}
type PlaceSearchResult = { places: Place[]; cached: boolean; sorted_by: "relevance" | "distance"; attribution: "Powered by Geoapify, © OpenStreetMap contributors" }
type PlaceDetails = Place & { wiki: { title: string; extract: string; url: string | null; image_url: string | null } | null }
type SavedPlace = { id: Uuid; place: Place; note: string | null; added_by: Attribution; created_at: string }
```

### 5.12 AI: one-shot actions

One-shot actions run inline or as a short job. All need the `ai` gate (consent, trip toggle, kill switch) and reserve credits first. They use Claude Haiku 4.5 for `explain` and Claude Sonnet 5.5 for the rest. Output carries source URLs for every fact found on the web. The AI never gives insurance, visa or legal advice and links to official sources instead, and never mentions a partner.

| Endpoint | Auth | Gate and cost | Request and response | Errors and side effects |
|---|---|---|---|---|
| `POST /trips/{trip_id}/ai/explain` | editor | `ai`, `credits(1)` (`explain`) | `{ question: string, context?: { item_id?: Uuid, lodging_id?: Uuid, place_id?: string } }` with `Idempotency-Key` to `ExplainResult` | Haiku short answer (under 120 words) with optional sources. Reserves 1 credit. Private notes are excluded from context. |
| `POST /trips/{trip_id}/ai/draft-day` | editor | `ai`, `credits(1)` (`draft_day`) | `{ day: string, preferences?: string, replace?: boolean }` with `Idempotency-Key` to `DraftDayResult` | Returns a draft list of `ItemIn`, not saved. Applying it is `POST /trips/{trip_id}/items/bulk`. Hard stop $0.03. |
| `POST /trips/{trip_id}/ai/draft-trip` | editor | `ai`, `credits(4)` (`draft_trip`) | `{ style?: string, pace?: "relaxed" \| "balanced" \| "packed", interests?: string[], budget?: Money }` with `Idempotency-Key` to 202 `DraftJob` | Whole-trip draft (days and items, plus a "why" per day). Runs as a job; poll `GET /ai/jobs/{id}`. Hard stop $0.10. |
| `POST /trips/{trip_id}/ai/research` | editor | `ai`, `credits(8)`, or `credits(1)` if served from `shared_research_cache` (`research`) | `{ topic?: "destination_brief" \| "events_and_closures" \| "reservations_needed" \| "getting_around" \| "seasonal_notes", question?: string, scope?: "destination" \| "dates" \| "lodging" }` (a fixed `topic` can be served from the shared cache; a custom `question` bypasses it) with `Idempotency-Key` to 202 `ResearchJob` | Sonnet with 5 searches and 8 fetches at most, hard stop $0.16. Cache hit returns instantly with `from_cache: true` and charges 1. The shared cache stores only public facts keyed by destination, topic and date bucket, never personal context. |
| `POST /trips/{trip_id}/ai/packing-list` | editor | `ai`, `credits(1)` (`explain` price class) | `{ preferences?: string }` with `Idempotency-Key` to `PackingListResult` | One short Haiku call from destination, dates, weather numbers and activity categories; the run is stored as `runs.kind = 'packing_list'`. Nothing is saved until the user adds lines with `POST /trips/{trip_id}/checklist/packing` (5.16). |
| Booking import (pasted confirmations and calendar descriptions) | | | | Moved to the import flow, 5.26: `POST /imports/paste` and the preview step of the file and feed imports call the `booking_import` feature ([06-ai-agents-spec.md](06-ai-agents-spec.md) section 5.3). |
| `GET /ai/jobs/{job_id}` | the requester | none | none to `AiJob` | Poll a draft-trip or research job until `done`, `failed` or `cancelled`. |
| `POST /ai/jobs/{job_id}/cancel` | the requester | none | none to `AiJob` | Releases unspent reservation if no result was produced. |

```ts
type ExplainResult = { answer: string; sources: Source[]; credits: CreditReceipt }
type Source = { url: string; title: string | null; fetched_at: string }
type PackingListResult = { items: { label: string; group: string }[]; credits: CreditReceipt }
type DraftDayResult = { day: string; items: ItemIn[]; rationale: string; credits: CreditReceipt }
type AiJob<T = unknown> = {
  id: Uuid; kind: "draft_trip" | "research"; status: "queued" | "running" | "done" | "failed" | "cancelled"
  result: T | null; error_code: string | null; credits: CreditReceipt
}
type DraftJob = AiJob<{ days: { day: string; title: string; items: ItemIn[]; rationale: string }[] }>
type ResearchJob = AiJob<{ answer: string; findings: { text: string; source: Source }[]; from_cache: boolean }>
```

### 5.13 AI: agent runs and taster

Agent runs are the fare hunt and deep research agents from the existing app, now metered API calls in our worker. They start only when a person taps the button; scheduled agent routines are Later: Phase 2. A run is a row in `runs`; its events are `run_events`. One run at a time per account, 20 turns, 10 searches, 10 fetches, hard stop $0.80. Admission needs $0.80 of monthly provider headroom even if the daily budget is spent. Every fare an agent saves must have been seen on a page during the run, and every note links its source URL (evidence rules carry over from `agent_ingest`).

| Endpoint | Auth | Gate and cost | Request and response | Errors and side effects |
|---|---|---|---|---|
| `POST /trips/{trip_id}/agent-runs` | editor | `ai`, `credits(40)` (8 from shared cache), or `taster` (free user, once per lifetime), one active run per account | `AgentRunStart` with `Idempotency-Key` to 202 `AgentRun` | Reserves credits, inserts `runs` (status `queued`), enqueues the job, sets `Location` to the run and returns `events_url`. Taster: spends the user's one-time `promo` grant (`restricted_action = 'agent_run'`) when the run starts; the grant is returned only if the run fails before its first tool call. `409 run_already_active` (body has the active run id), 402 `insufficient_credits`, 402 `payment_required` with reason `agent_taster_used`, 429 `provider_budget_exhausted`, 403 `ai_consent_required`. |
| `GET /trips/{trip_id}/agent-runs` | viewer | none | `?status=&kind=&limit&cursor` to `Page<AgentRun>` | All runs on the trip, including others' (members see run summaries; prompts and raw logs only the starter and the owner). |
| `GET /agent-runs/{run_id}` | viewer on the trip | none | none to `AgentRunDetail` | Summary, counts, cost estimate (starter only), credit receipt. |
| `GET /agent-runs/{run_id}/events` | viewer on the trip | none | `?after_seq=0&limit=200` to `RunEvent[]` | Polling fallback for clients that cannot hold SSE. |
| `GET /agent-runs/{run_id}/stream` | viewer on the trip | none | SSE (see below) | `Content-Type: text/event-stream`. Replays from `Last-Event-ID`. Heartbeat comment every 15 seconds. Ends after `run.finished`. Does not count against rate limits once open (one stream per run per user, 3 per user). |
| `GET /agent-runs/{run_id}/outputs` | viewer on the trip | none | none to `RunOutputs` | Saved fares, notes (each with a source URL) and rejections (what was dropped and why). |
| `POST /agent-runs/{run_id}/cancel` | starter or owner | none | `Idempotency-Key` to `AgentRun` | Sets `cancel_requested`; the worker stops at the next checkpoint. Credits are settled for work done through `settle_credits` (charged pro rata by turns used, minimum 8 credits for a run that called tools, 0 if cancelled in the queue). `409 state_conflict` when already finished. |
| `DELETE /agent-runs/{run_id}` | starter or owner | finished runs only | 204 | Deletes stored prompt and log content; the `ai_usage` row stays. |
| `GET /me/agent-taster` | user | none | none to `{ used: boolean, used_at: string | null, run_id: Uuid | null }` | Drives the "Try a deep run free" card. |

```ts
type AgentRunStart = {
  kind: "fare_hunt" | "deep_research"
  route_ids?: Uuid[]                          // fare_hunt: 1 to 3, each route must be in the trip (06 maps them to R1 to R3)
  topic?: string                              // deep_research, max 300 chars
  instructions?: string                       // max 2000 chars, treated as untrusted user text
}
type AgentRun = {
  id: Uuid; trip_id: Uuid; kind: "fare_hunt" | "deep_research"
  status: "queued" | "running" | "succeeded" | "partial" | "failed" | "timed_out" | "cancelled" | "interrupted"
  started_by: Attribution; params: Record<string, unknown>
  queued_at: string; started_at: string | null; finished_at: string | null
  summary: string | null; error_code: string | null
  accepted_count: number; rejected_count: number
  turns_used: number | null; searches_used: number | null; fetches_used: number | null
  from_cache: boolean; is_taster: boolean
  credits: CreditReceipt
  cancel_requested: boolean
  events_url: string                          // /v1/agent-runs/{id}/stream
}
type AgentRunDetail = AgentRun & { cost_usd_micros?: number /* starter and admins only */ }
type RunEvent = {                               // type is the SSE event name, derived from run_events.type (info, warning, error, tool_use, tool_result, text, result, rejection) plus tool_name and payload.kind
  seq: number; ts: string
  type: "run.started" | "turn" | "tool.search" | "tool.fetch" | "fare.saved" | "note.saved"
      | "fare.rejected" | "budget" | "warning" | "run.finished"
  tool_name: string | null; summary: string; payload: Record<string, unknown> | null
}
type RunOutputs = { fares: Fare[]; notes: Note[]; rejections: { kind: string; reason: string; detail: string }[] }
```

**SSE stream format.** Each event is one SSE message with an id equal to `seq`:

```
id: 14
event: fare.saved
data: {"seq":14,"ts":"2026-09-30T14:07:11Z","type":"fare.saved","tool_name":"submit_flight_quotes","summary":"Saved LIS round trip $412 on TAP, seen on tap.example","payload":{"fare_id":"0191..."}}

: heartbeat

id: 27
event: run.finished
data: {"seq":27,"type":"run.finished","summary":"2 fares and 1 note saved","payload":{"status":"succeeded","credits":{"reserved":40,"charged":31,"balance_after":29}}}
```

Clients reconnect with `Last-Event-ID`. `run.finished` is always the last event and carries the settled credit receipt. The stream authenticates with the normal bearer header (the iOS client uses a fetch-based reader, not `EventSource`); a short-lived `?stream_token=` (60 seconds, from `POST /agent-runs/{id}/stream-token`) is accepted for browsers that cannot set headers.

### 5.14 Notes and evidence

Notes are either user notes or agent findings. An agent note must carry at least one `source_url`; fares seen by an agent are evidence on the `Fare`.

| Endpoint | Auth | Gate and cost | Request and response | Errors and side effects |
|---|---|---|---|---|
| `GET /trips/{trip_id}/notes` | viewer | none | `?kind=&pinned=&limit&cursor&updated_since` to `Page<Note>` | Private notes of other users are omitted. |
| `POST /trips/{trip_id}/notes` | editor | none | `NoteIn` to 201 `Note` | `kind: "user"` only; agent notes are written by the worker. |
| `PATCH /notes/{note_id}` | author or owner | versioned | `Partial<NoteIn>` to `Note` | Agent notes can be pinned or hidden, not edited. |
| `DELETE /notes/{note_id}` | author or owner | none | 204 | |
| `GET /notes/{note_id}/evidence` | viewer | none | none to `Evidence` | Source URLs, titles, fetched times, `checked_at`, `stale` and the run that found them. |
| `POST /notes/{note_id}/recheck` | editor | `ai`, `credits(1)` (`explain`, run kind `recheck`; kill switch `ai.recheck`) | `Idempotency-Key` to 200 `RecheckResult` | One tap on "May be out of date". Fetches the stored source once and reports `confirmed` (moves `checked_at` to today), `changed` or `not_shown` (shows the new value, changes nothing), or `unreachable` (credit refunded). Agent notes only. 06 section 5.12. |
| `POST /items/{item_id}/recheck` | editor | as above | `Idempotency-Key` to 200 `RecheckResult` | The same for an itinerary item that carries `check_url` (created by plan verification). `422 validation_failed` when the item has no evidence to recheck. |
| `POST /reports` | user (viewer on the trip) | 20 per day per user | `ReportIn` to 201 `{ id: Uuid }` | "Report a problem" on an agent note or an AI answer. Writes `content_reports` (`target_type` `agent_note` or `ai_answer`; when the run used the shared cache the `cache_key` is added server side). The report immediately expires that cache entry so it is no longer served; the third report from different users also flags it (03 section 5.11). The reporter is never shown to anyone but moderators. |
| `POST /shared/{token}/report` | none (share token) | 5 an hour per IP | `{ reason: ReportReason, detail?: string }` to 201 | Report a shared trip page (`target_type` `shared_trip`, `reporter_user_id` null). Reviewed in the admin moderation queue (08 6.12). |

```ts
type ReportReason = "spam" | "harmful" | "wrong_info" | "copyright" | "privacy"   // content_reports.reason
type ReportIn = { note_id?: Uuid; run_id?: Uuid; reason: ReportReason; detail?: string /* max 1000 */ }   // exactly one of note_id and run_id
type NoteIn = { title?: string; body: string /* max 10000 */; pinned?: boolean; is_private?: boolean; day?: string | null; item_id?: Uuid | null; version?: number }
type Note = NoteIn & {
  id: Uuid; trip_id: Uuid; version: number; kind: "user" | "agent"; author: Attribution | null
  run_id: Uuid | null; sources: Source[]; checked_at: string; stale: boolean   // stale: checked_at older than 14 days (agent notes only)
  created_at: string; updated_at: string
}
type Evidence = {
  note_id: Uuid; run_id: Uuid | null; sources: Source[]; excerpt: string | null
  checked_at: string                         // the day the sources were last seen on their pages (notes.checked_at); the date on the evidence label
  stale: boolean                             // true when checked_at is more than 14 days ago: the UI shows "May be out of date" and a Recheck button
  stale_after_days: 14
}
type RecheckResult = {
  result: "confirmed" | "changed" | "not_shown" | "unreachable"
  current_value: string | null               // what the page shows now, copied exactly; null for confirmed and unreachable
  source: Source; checked_at: string         // moved to today only when result is confirmed
  credits: CreditReceipt                     // charged 1, or 0 when unreachable
}
```

### 5.15 Presentation data

| Endpoint | Auth | Gate and cost | Request and response | Errors and side effects |
|---|---|---|---|---|
| `GET /trips/{trip_id}/presentation` | viewer | none | `?redact=` to `Presentation` | Everything the full-screen walkthrough needs in one payload: cover, destinations, days with items, chosen flights, booked stays, weather, and the pre-trip checklist summary. `ETag`. |
| `GET /trips/{trip_id}/presentation/pdf` | viewer | none | none to 202 `Job` then 302 to a signed file | PDF export. Free owners get a small "Made with Hermi" footer (`plans.limits.hide_presentation_footer` false); paid trips have none. Partner buttons are omitted by default (`?links=true` keeps them live with the commission sentence printed). |
| `GET /calendar/{token}.ics` | none (the token) | none | none to `text/calendar` | Live calendar subscription for the trip; token URL, rotation and content rules are in 5.29. |

```ts
type Presentation = {
  trip: Pick<Trip, "id" | "name" | "start_date" | "end_date" | "cover" | "destinations">
  days: { day: string; title: string; notes: string; destination_name: string | null; items: Item[] }[]
  flights: Fare[]; stays: Lodging[]
  weather: { day: string; high_c: number; low_c: number; summary: string }[] | null
  checklist: { done: number; total: number }
  book_slide_enabled: boolean                 // owner setting; never shown during playback
  generated_at: string
}
```

### 5.16 Checklist ("Before you go")

The checklist is derived from trip data by a rules module and stored as `checklist_items` only for state (done, dismissed, meta). At least half the items are unmonetized.

| Endpoint | Auth | Gate and cost | Request and response | Errors and side effects |
|---|---|---|---|---|
| `GET /trips/{trip_id}/checklist` | viewer | none | none to `ChecklistItem[]` | Appears when the trip has a chosen flight or a saved stay, or 45 days before departure. Each item says why it is shown. Affiliate items carry `offer` with the disclosure line. The "Flights booked" item asks for what was paid and feeds the booked-fare alert (5.8). Emits `checklist_item_shown` once per item per session. |
| `PATCH /trips/{trip_id}/checklist/{kind}` | editor | versioned | `{ status: "todo" \| "done" \| "skipped" \| "not_needed", version?: number }` to `ChecklistItem` | Persists per trip. One nudge per item per week at most. |
| `PATCH /trips/{trip_id}/checklist/items/{item_id}` | editor | versioned | `{ status?: "todo" \| "done" \| "skipped" \| "not_needed", title?: string, version?: number }` to `ChecklistItem` | For custom items and AI packing lines, which have many rows per trip and so are addressed by id (rules items are addressed by `{kind}` above). |
| `POST /trips/{trip_id}/checklist/custom` | editor | none | `{ title: string }` to 201 `ChecklistItem` | User items (`kind: "custom"`, `source: "user"`). |
| `POST /trips/{trip_id}/checklist/packing` | editor | none | `{ items: { label: string, group: string }[] /* max 40 */ }` to 201 `ChecklistItem[]` | Saves the lines the user kept from a packing-list result as `kind: "packing"`, `source: "ai"`, `meta.group` set. Free; the credit was spent on the AI call. |
| `DELETE /trips/{trip_id}/checklist/{item_id}` | editor | custom items and AI packing lines only | 204 | |

```ts
type ChecklistKind = "flights_booked" | "stay_booked" | "tickets" | "transfer_or_car" | "esim" | "insurance"
  | "documents" | "luggage_storage" | "money" | "home" | "packing" | "custom"
type ChecklistItem = {
  id: Uuid; kind: ChecklistKind; title: string; why: string       // "You land in Lisbon at 21:40"
  status: "todo" | "done" | "skipped" | "not_needed"; group: string; version: number
  source: "rules" | "user" | "ai"                                 // checklist_items.source: rules rows are one per kind; user and ai rows are many
  cost_hint: string | null; official_link: string | null          // documents links to the government source first
  offer: AffiliateOffer | null                                    // null for unmonetized items and when insurance is not enabled
  done_at: string | null; dismissed_at: string | null
}
```

### 5.17 Group tools: polls, votes, expenses, shares, settlements

Later: Phase 2 (polls, manual cost splitting and settlements; the Group Trip Pass). Stripe collection: Phase 3.

### 5.18 Concierge and room-block requests

Later: Phase 2 (concierge lane and room-block requests).

### 5.19 Entitlements and credits

| Endpoint | Auth | Gate and cost | Request and response | Errors and side effects |
|---|---|---|---|---|
| `GET /me/entitlements` | user | none | none to `Entitlements` | The one source the client reads for what the account can do. Derived from `entitlements`, `subscriptions` and `trip_passes`. Never calls Apple. `ETag`. |
| `POST /purchases/sync` | user | none | `{ trip_id?: Uuid, product_id?: string }` with `Idempotency-Key` to `Entitlements` | Called after a purchase for instant unlock before the webhook lands. The server asks RevenueCat's REST API for the subscriber and applies the same code as the webhook. For a Trip Pass, `trip_id` binds the pass (it can move once, see `/me/passes/{pass_id}/move`). |
| `POST /purchases/restore` | user | none | none to `Entitlements` | Re-pulls the subscriber after "Restore purchases". |
| `GET /me/credits` | user | none | none to `CreditBalance` | Balance split by source, expiry dates and next monthly grant. |
| `GET /me/credits/ledger` | user | none | `?limit&cursor&kind=` to `Page<LedgerEntry>` | From `credit_ledger`, newest first; `kind` filters `entry_type`. |
| `GET /credits/packs` | user | none | none to `CreditPack[]` | `credits_50`, `credits_150`, `credits_400` (plan codes) with their store product ids (`hermi_credits_50` and so on). The price is shown by StoreKit, not by us. |
| `POST /credits/packs/claim` | user | none | `{ product_id: string, transaction_id: string }` with `Idempotency-Key` to `CreditBalance` | Verifies the transaction through RevenueCat, grants credits keyed by `transaction_id` (never twice). Usually already granted by the webhook; this returns the balance. `409 state_conflict` if the transaction belongs to another user. |
| `GET /trips/{trip_id}/pass` | viewer | none | none to `TripPass \| null` | Pass status and expiry for the trip settings screen. A reward pass shows `source: "import_reward"` and is not refundable. |
| `GET /me/passes` | user | none | none to `TripPass[]` | Includes an unapplied pass waiting to be bound to a trip (a `store_transactions` row with `kind = 'pass'` and no `trip_passes` row yet). |
| `POST /me/passes/{pass_id}/bind` | user (trip owner) | none | `{ trip_id: Uuid }` with `Idempotency-Key` to `BindResult` | Binds an unapplied pass to a trip the caller owns: inserts `trip_passes` (`starts_at` now, `expires_at` plus 90 days, limits copied from `plans.limits`), writes the `trip_pass` credit grant, recomputes capabilities, and returns `{ bound: true, pass, credits_granted: 0, support_ticket_id: null }`. The caller must be the trip's owner: otherwise `403 insufficient_role`. When a paid second pass cannot bind because the trip already has an active pass: returns `200 { bound: false, pass: null, credits_granted: 40, support_ticket_id, message }`, grants the pass's credits to the buyer (`trip_pass` grant, keyed by the store transaction, so a retry grants once), opens a `support_tickets` row for the refund, and the `message` tells the buyer that support sends the refund request ("This trip already has a Trip Pass. We added the 40 credits to your account and support will send you the refund request."). The purchase flow and the RevenueCat handler apply the same rule when `trip_id` names a trip the buyer does not own or that already has a pass. A reward pass from an import (5.26) is bound to its trip when it is granted and needs no bind call. |
| `POST /me/passes/{pass_id}/move` | user (trip owner) | none | `{ trip_id: Uuid }` to `TripPass` | Moves an active pass to another trip the caller owns, once (`move_count`). Keeps `expires_at`, moves unspent pass credits and the live-check counter. `409 state_conflict` on a second move. |

```ts
type BindResult = { bound: boolean; pass: TripPass | null; credits_granted: number; support_ticket_id: Uuid | null; message?: string }
type Entitlements = {
  tier: Tier; source: "none" | "subscription" | "comp"
  product_id: string | null; status: "none" | "active" | "in_trial" | "in_grace" | "billing_retry" | "paused" | "expired" | "refunded" | "revoked"
  valid_until: string | null; auto_renew: boolean | null; store: "apple" | null        // Phase 1 sells only through the App Store; there are no web purchases
  manage_subscription_url: string | null
  cancel_url: string | null                  // the store's own subscription page, opened by the one-tap "Cancel subscription" row (07 section 7.11); null when there is no subscription
  limits: { active_trips: number | null; live_routes: number; monthly_credits: number; price_alerts: number; collaborators: number }   // plans.limits keys
  usage: { active_trips: number }
  trip_passes: TripPass[]
  flags: { agent_runs: boolean; taster_available: boolean; import_reward_available: boolean }
  credits: CreditBalance
}
type CreditBalance = {
  total: number; monthly: number; trip_pass: number; purchased: number
  spend_order: ["monthly", "promo", "trip_pass", "adjustment", "purchase"]   // same order as reserve_credits; referral rewards are promo grants
  grants: { kind: "monthly" | "promo" | "trip_pass" | "purchase" | "adjustment"; remaining: number; expires_at: string | null; trip_id: Uuid | null }[]
  next_monthly_grant_at: string | null; blocked: boolean   // blocked when a refund pushed the balance negative
}
type LedgerEntry = {
  reservation_id: Uuid | null; at: string; kind: "grant" | "reserve" | "settle" | "refund" | "expire" | "clawback" | "adjust"   // credit_ledger.entry_type; its bigint id is never exposed
  delta: number; charged: number | null; action: CreditAction | null
  trip_id: Uuid | null; run_id: Uuid | null; note: string
}
type CreditPack = { plan_code: "credits_50" | "credits_150" | "credits_400"; product_id: "hermi_credits_50" | "hermi_credits_150" | "hermi_credits_400"; credits: number; valid_months: 12 }
type TripPass = {
  id: Uuid; product: "trip_pass" /* plan_code */; source: "purchase" | "import_reward"; trip_id: Uuid | null   // id is trip_passes.id, or store_transactions.id while unapplied
  starts_at: string | null; expires_at: string | null; status: "unapplied" | "active" | "expired" | "refunded"
  live_checks_left: number | null; collaborators_max: number
}
```

### 5.20 Paywall offers

The server decides which offer to show and why, so the client never hard codes paywall logic. A paywall is shown only at a moment of value, always with the free path visible, and never with fake urgency.

| Endpoint | Auth | Gate and cost | Request and response | Errors and side effects |
|---|---|---|---|---|
| `GET /paywall/offer` | user | none | `?trigger=&reason=&trip_id=&surface=` to `PaywallOffer` | Logs `paywall_viewed` (no experiment cell is shown twice in one session). Returns 200 with `offer: null` when nothing should be shown (for example when the user already has the capability). |
| `POST /paywall/events` | user | none | `{ offer_id: Uuid, event: "viewed" \| "dismissed" \| "cta_tapped" \| "purchase_started" \| "purchased" \| "purchase_failed" \| "restore_tapped" }` to 204 | Analytics and experiment accounting only. |

```ts
type PaywallOffer = {
  offer_id: Uuid; reason: PaywallHint["reason"] | null; trigger?: PaywallTrigger   // reason is null for the three client-initiated triggers
  purchasable: boolean                                       // false on the web app: there are no web purchases in Phase 1 and "lead" and "alternatives" are empty
  headline: string; body: string; why: string              // why this is shown now, plain words
  lead: { product_id: string; label: string; trial_days: number | null }
  alternatives: { product_id: string; label: string }[]     // at most 2
  free_path: { label: string; action: string }              // always present: "Keep planning for free"
  disclosure: string | null                                 // subscription terms line
  experiment_cell: string | null
} | null
```

**Web app.** The web app cannot buy anything in Phase 1. When the request comes from the web client (`X-Hermi-Client: web`) the offer has `purchasable: false`, `lead.product_id` is omitted, and the headline is "Upgrade in the iOS app" with the same `why` and `free_path`; `cta` is an App Store link, never a purchase page or a price comparison. Web billing arrives with Android in Phase 2.

Mapping (decision table the endpoint implements, detail in 07): `sharing` (a Free owner wants a second collaborator) leads with Trip Pass for a one-trip group or Plus annual for repeat planners; `live_routes` and `agent_taster_used` lead with Plus annual; `credits` shows credit packs first for Plus members and Plus for Free; `traveler_limit` shows Plus; `trip_limit` shows Plus and the option to archive. Credit packs are never shown beside an upsell on a trips home screen. `GET /paywall/offer` takes `?trigger=` (any `PaywallTrigger`, exactly the 07 section 6.2 codes). The trigger sets the reason: `third_trip` gives `trip_limit`; `second_route`, `track_live` and `alert_limit` give `live_routes`; `invite` gives `sharing`; `out_of_credits_draft`, `out_of_credits_research`, `out_of_credits_verify` and `out_of_credits_agent` give `credits`; `out_of_credits_agent` for a Free user whose lifetime deep run is spent gives `agent_taster_used`. `export_footer`, `ninth_stay` and `lifecycle_14d` are client-initiated and have `reason: null`. A gate error maps the other way: `limit_reached` with reason `trip_limit`, `sharing` or `live_routes` sets the matching trigger; `traveler_limit` sets no trigger. `?reason=` alone is accepted and picks the default trigger for it. Product ids in `lead` and `alternatives` are `store_products.product_id` values such as `hermi_plus_annual` and `hermi_trip_pass`.

### 5.21 Affiliate: outbound links, redirect and offers

All outbound partner links go through `/go/{click_id}`. The server mints a click id only through an authenticated call, builds the destination only from a stored `affiliate_link_templates` row plus a validated destination for that program's own hosts, and never ranks anything by commission. The server never fetches Airbnb, Vrbo or Booking.com pages; pasted listing links open unchanged and are never rewritten.

| Endpoint | Auth | Gate and cost | Request and response | Errors and side effects |
|---|---|---|---|---|
| `POST /outbound` | user (viewer on the trip) | 60 an hour per user | `OutboundIn` to 201 `OutboundLink` | Checks trip access, picks the program (feature flags, geography, A/B cell, kill switch per partner), inserts `link_clicks` with a random 128 bit base62 `click_id` (and `short_id` of 8 to 12 characters where a network limits sub-id length), returns `https://go.hermi.world/go/<click_id>`. Repeat clicks for the same entity and surface within 30 seconds return the same link. `404 not_found` when no program applies (the client then shows the plain link). User id, trip id and email never appear in the URL. |
| `POST /shared/{token}/outbound` | none (share token) | 30 an hour per IP | `{ offer_ref: string }` to 201 `OutboundLink` | For the "Book the plan" slide on share pages. No user is attached; the click row has `user_id` null, `entity_type = 'share_link'` and the share link id as `entity_id`. |
| `GET /go/{click_id}` | none | known id; the affiliate redirect needs it fresh (under 10 minutes) and unused | none to `302 Location: <partner url>` | Sets `clicked_at`, `redirect_status` (the HTTP status sent: 302 for a partner redirect and for the plain fallback; an unknown id has no row), `opened_in`, `country` and `platform` on `link_clicks`; marks the id used. Headers: `Cache-Control: no-store`, `Referrer-Policy: no-referrer`. Never renders a page, sets a cookie or runs a script. There is no `url=` parameter; an id that never existed gets `404` with an empty body and `X-Robots-Tag: noindex`, while a known id that is expired or already used gets a 302 to the plain non-affiliate destination so nobody is stranded. Partner kill switch on: the same 302 to the plain destination. |
| `GET /trips/{trip_id}/offers` | viewer | none | `?context=&entity_id=` to `AffiliateOffer[]` | Offers per context: `destination`, `flight_chosen`, `lodging_shortlist`, `itinerary_day`, `place`, `checklist`, `presentation`. At most one card per screen view except user-requested lists. Sorting is always stated and is never by commission. Returns `[]` when the user set `hide_booking_links` (the client then renders plain links), for domestic trips on eSIM items, and before a chosen flight or booking on insurance. |
| `GET /affiliate/disclosure` | none | none | none to `{ sentence, eu_uk_label: "Ad", booking_line: string, programs: {name: string, category: string}[], ranking_rule: string }` | Static content for the "How we earn money" page. `Cache-Control: public, max-age=3600`. |

```ts
type OutboundIn = {
  entity_type: "fare" | "lodging_option" | "itinerary_item" | "saved_place" | "checklist_item" | "offer" | "thing_to_do"   // link_clicks.entity_type
  entity_id: Uuid | string; surface: string           // "lodging-shortlist", "flight-chosen", "checklist-esim" ...
  trip_id?: Uuid
  opened_in?: "sfsvc" | "safari" | "web" | "android_tab"
}
type OutboundLink = { click_id: string; url: string; expires_at: string }
type AffiliateOffer = {
  offer_ref: string                           // opaque, valid 24 hours, used with /outbound
  category: "lodging" | "flight" | "tour" | "transfer" | "car" | "esim" | "insurance" | "train" | "luggage"
  partner: string; label: string              // "Book on Agoda"
  why: string                                 // "Your dates, 4 nights, 2 guests"
  price: Money | null; price_observed_at: string | null; price_note: string | null   // "price at last check"
  disclosure: "We earn a commission if you book here."
  extra_disclosure: string | null             // "Ad" label on UK and EU storefronts
  non_affiliate: { label: string; url: string } | null     // "Search on the airline's site", "Open your saved link"
  sorted_by: string | null
}
```

### 5.22 Partner guides

Later: Phase 3 (labeled partner guides and `POST /trips/{id}/items/from-guide`).

### 5.23 Print orders (web)

Later: Phase 3 (printed trip books, Stripe checkout).

### 5.24 Advisors

Later: Phase 3 (Hermi for Advisors workspaces, seats and proposals).

### 5.25 Admin API (outline)

Base path `/v1/admin`, hidden from the public OpenAPI schema, reachable only from the admin console origin behind Cloudflare Access, with a separate admin Supabase project claim and `admin_users.role` (`admin_role`: `owner`, `support`, `finance`, `engineer`, `content`). `ADMIN_AUTH_MODE=dev` (local and ci only) uses the fake-Access signer of 08: the same admin routes accept a token it signs, and nothing else changes. Every mutating call needs a `reason` string and writes `audit_log` (actor, route, target, before and after). Routes return `404` to non-admins. The route list above is a summary; the full table, limits and permissions are in [08-admin-control-center.md](08-admin-control-center.md) section 8, which is authoritative.

| Area | Endpoints (all under `/v1/admin`) | Minimum role |
|---|---|---|
| Users | `GET /users`, `GET /users/{id}`, `POST /users/{id}/sign-out`, `POST /users/{id}/ai-hold` | support |
| Billing | `GET /subscriptions`, `GET /store-transactions`, `POST /users/{id}/comp` | finance |
| Credits | `GET /users/{id}/credits`, `POST /users/{id}/credits/grant`, `POST /runs/{id}/cancel` | support |
| AI spend | `GET /ai-spend/summary`, `GET /runs` | engineer |
| Kill switches and flags | `GET/PUT /kill-switches/{key}`, `GET /flags`, `PATCH /flags/{key}` | engineer |
| Affiliate | `GET /affiliate/programs`, `PUT /affiliate/templates/{id}`, `GET /affiliate/summary`, `GET /affiliate/imports` | finance |
| Support | `GET /tickets`, `PATCH /tickets/{id}` | support |
| Content reports | `GET /reports`, `PATCH /reports/{id}` | support |
| Audit | `GET /audit` | support (own actions) or owner |

### 5.26 Imports (switching from TripIt, Tripsy, Wanderlog, Google Maps and calendars)

An import brings an existing plan into Hermi in two steps: create a **preview** (nothing is written to any trip), review it, then **confirm**. There are five sources, stored as `trip_imports.source`: `ics_file` (an uploaded calendar file, for example a TripIt, Tripsy or Google Calendar export), `ics_feed` (a calendar feed URL the user pastes), `pasted_text` (booking confirmations pasted as text), `maps_file` (a Google Maps saved-list export: Takeout CSV, GeoJSON or KML) and `places_text` (pasted place names, one per line, or a list copied out of Wanderlog or Google Maps). The import screen has entries named for TripIt, Tripsy, Wanderlog and Google Maps; every create call takes an optional `origin` (`tripit`, `tripsy`, `wanderlog`, `google_calendar`, `google_maps`, `other`) that only changes the instructions shown and feeds the "switch imports per week" metric, never the parsing. An import targets a new trip (the default, used by the onboarding card "Coming from TripIt or Wanderlog?") or an existing trip the caller can edit. Email-forward import (plans@hermi.world) is Later: Phase 2.

Rules that hold for every source:

1. The server never fetches Airbnb, Vrbo or Booking.com pages. A feed URL on those hosts (or any host in `BLOCKED_HOSTS`, 06 section 2.4) is refused with `422 blocked_domain` and the client suggests downloading the file and uploading it. URLs found inside calendar events or pasted text are kept as plain text in notes; they are never followed, rewritten or given an affiliate link.
2. A preview belongs to the importing user, expires after 24 hours and stores only normalized candidates (`trip_imports.preview`). The raw file or pasted text is never stored (no file storage, no object key); it is parsed in memory and dropped. Raw content and feed URLs never go to logs or Sentry.
3. Claude Haiku (06 section 5.3) is used only where text must be interpreted: pasted text, and calendar event descriptions that look like bookings. Dates, times, places and titles read straight from a calendar file are parsed without AI and cost nothing.
4. Nothing is saved until confirm. Every row an import creates has `source: "import"` and appears in the trip's activity feed ("Maya imported 9 items").
5. Google Maps is never scraped. A Google Maps list link (`maps.app.goo.gl`, `google.com/maps/placelists/...`) is never opened, resolved or fetched; sent where a file or text is needed it returns `422 list_link_not_readable`, and the screen explains how to export the list and offers to keep the link as a note on the trip. Places from a file or pasted text are matched by name through place search (Geoapify), with no AI and no credits; any Google Maps URL in the file stays as plain text in the item's notes.

**Limits (one table; 01, 02 section 5.4 and 10 mirror it).**

| Source | Maximum size | Maximum items | Rate limit |
|---|---|---|---|
| ICS file | 2 MB | 500 events; description extraction at most 3 AI calls (18 events) | 20 previews a day |
| ICS feed body | 2 MB | 500 events; description extraction at most 3 AI calls (18 events) | 5 registrations a day, 4 refreshes a day per import; counts toward the 20 previews a day |
| Pasted booking text | 12,000 characters | 1 AI call | 20 previews a day (file, paste and feed together) |
| Google Maps file | 5 MB | 200 places | 20 previews a day |
| Pasted places | 20,000 characters | 200 places | 20 previews a day |

| Endpoint | Auth | Gate and cost | Request and response | Errors and side effects |
|---|---|---|---|---|
| `POST /imports/ics-file` | user | none; 20 previews a day | multipart form: `file` (max 2 MB, `.ics` or `text/calendar`), `trip_id?` (caller must be editor) to 201 `ImportPreview` | Parses in the worker sandbox and returns a `review` import (files are parsed locally, so no async step). `415 unsupported_media_type`, `413 payload_too_large`, `422 validation_failed` (`no_events`, `too_many_events`). Description extraction may spend credits (see parsing rules). |
| `POST /imports/ics-feed` | user | none; 5 a day; SSRF rules below | `{ url: string, trip_id?: Uuid }` with `Idempotency-Key` to 202 `ImportPreview` (status `received`) | Validates the URL, holds it encrypted (only until the preview is confirmed or discarded, unless "Keep checking this calendar" is switched on later), enqueues the fetch job, sets `Location: /v1/imports/{id}`. Poll `GET /imports/{id}` until `review` or `failed`. `422 feed_url_not_allowed`, `422 blocked_domain`, `502 feed_fetch_failed` (as the failed import's `error_code`). |
| `POST /imports/paste` | user | `ai`, `credits(1)` (`booking_import`, action code `explain`) | `{ text: string /* max 12000 */, trip_id?: Uuid }` with `Idempotency-Key` to 201 `ImportPreview` | Reserves 1 credit, redacts personal data, calls Haiku once with a strict JSON schema, builds candidates. Nothing recognized: the credit is refunded and the import has `warnings: [{ code: "unrecognized" }]`. `402 insufficient_credits`, `403 ai_consent_required`, `503 feature_disabled` (kill switch `ai.import`). The server never fetches a URL in the text. |
| `POST /imports/maps-file` | user | none; 20 previews a day | multipart form: `file` (max 5 MB, `.csv`, `.json`, `.geojson` or `.kml`), `trip_id?`, `origin?` to 201 `ImportPreview` | Reads the Takeout list locally (title, note, comment; coordinates when present) and matches each title by place search. Up to 200 places, more is `422 too_many_events`. Candidates are `kind: "place"`. No AI, no credits. `415`, `413`. |
| `POST /imports/places` | user | none; 20 previews a day | `{ text: string /* max 20000 */, trip_id?: Uuid, origin?: ImportOrigin }` to 201 `ImportPreview` | Pasted place names, one per line or a copied list. A single Google Maps list link returns `422 list_link_not_readable`. Matching by place search, no AI, no credits; up to 200 places. |
| `GET /imports` | user | none | `?status=&limit&cursor` to `Page<ImportSummary>` | The caller's imports from the last 30 days and registered feeds. |
| `GET /imports/{import_id}` | the importer | none | none to `ImportPreview` | Poll and review. `410 import_expired` for a preview older than 24 hours (its status is then `discarded`), discarded or already `applied`. |
| `POST /imports/{import_id}/refresh` | the importer | `ics_feed` only; 4 a day | none to 202 `ImportPreview` | Re-fetches the stored feed now and builds a change preview containing only events that are new or changed since the last confirm. Never applies anything by itself. |
| `PUT /imports/{import_id}/polling` | the importer | `ics_feed` only, after confirm; at most 3 polled feeds per account | `{ enabled: boolean }` to 200 `ImportSummary` | "Keep checking this calendar": opt-in, off by default, never switched on for the person. On: the encrypted feed URL is kept and the worker polls every 6 hours (`trip_imports.poll_enabled`, `next_poll_at`). Off: the stored URL and any pending changes are deleted. Calls `set_import_polling()` (03 5.9). `409 polling_limit`, `503 feature_disabled` (kill switch `import.polling`). |
| `GET /imports/{import_id}/changes` | the importer | none | none to `ImportChanges \| null` | The change preview found by polling or refresh: events added, changed and removed since the last confirm. `null` when there is nothing to review. |
| `POST /imports/{import_id}/changes/confirm` | the importer (editor on the trip) | none | `{ include_keys: string[] }` with `Idempotency-Key` to 200 `ImportResult` | Applies only the ticked changes, matched by `import_uid`; removed events are never deleted silently (the item is shown as "Removed from your calendar" for the person to delete). Polling changes never count toward the reward. |
| `DELETE /imports/{import_id}/changes` | the importer | none | none to 204 | Dismisses the change preview. |
| `POST /imports/{import_id}/confirm` | the importer (editor on an existing target trip) | `active_trips` when a new trip is created; `routes_per_trip` for tracked fares | `ImportConfirm` with `Idempotency-Key` to 201 `ImportResult` | One transaction (rules below). Sets `trip_imports.status = 'applied'`, deletes the candidate payload and, unless polling is switched on, the stored feed address, and applies the reward when the account is eligible. `402 limit_reached` (reason `trip_limit`) when a Free owner has 2 active trips; the client then offers "Add to an existing trip". |
| `DELETE /imports/{import_id}` | the importer | none | none to 204 | Discards the preview, deletes the stored feed URL and candidates. Rows an earlier confirm created stay. Also turns polling off. |
| `GET /me/import-reward` | user | none | none to `ImportReward` | Drives the onboarding card and the copy on the import screen. |

**Parsing rules (file and feed).** RFC 5545 is parsed with a maintained library inside a size-limited sandbox. `TZID` and `VTIMEZONE` are honored and local times are kept with their zone; all-day events become all-day items; `STATUS:CANCELLED` events and `VTODO` are ignored; recurring events are expanded up to 60 occurrences inside the trip window (the rest dropped with warning `recurrence_trimmed`); more than 500 events is `422 too_many_events`. Classification is deterministic first: a flight number plus two IATA codes in the summary, or a TripIt flight marker, gives `flight`; "Check-in", "Hotel" or "Stay" plus a location gives `lodging`; everything else is `item` with a category guessed from keywords and `other` by default.

**Description extraction (AI, only when needed).** An event whose description is longer than 40 characters and contains booking-like text (confirmation, reservation, booking reference, flight or check-in words) is sent to the `booking_import` feature. Personal data is redacted first (06 section 12.3). One call covers up to 6 events and costs 1 credit; an import makes at most 3 calls, so 18 events. If the balance covers fewer calls, the importer runs as many as it can and adds warning `ai_partial_no_credits`; with no credits the structured fields still import and the warning is `ai_skipped_no_credits`. A calendar preview never returns `402`. Extracted values fill gaps and never overwrite what the file stated, and every extracted value must appear in the event text (06 section 5.3).

**Trip target.** A new trip takes its name from `X-WR-CALNAME` (or the first destination), its dates from the earliest and latest event, and its destinations from flight destination airports through the `airports` table; nothing is geocoded by AI and the user edits all of it in the preview. For an existing trip, events outside the trip dates carry warning `outside_trip_dates` and `extend_trip_dates` on confirm widens the dates. A candidate that matches an existing row (same flight number and date, same lodging name and check-in, or same title, day and start time) gets `duplicate_of` set and `include: false`.

**Feed fetch and SSRF protection.** The feed fetcher is the only place Hermi fetches a URL a user supplied, so it is locked down:

- Scheme `https` only (`webcal://` is rewritten to `https://`; `http:`, `file:`, `ftp:`, `gopher:` and anything else is rejected). Port 443 only. No user info in the URL. The host must be a DNS name, not an IP literal. URL length at most 2,048 characters.
- The fetcher resolves the host itself and rejects the request if any answer is not a public address: loopback, private (RFC 1918), link-local including 169.254.0.0/16 and the cloud metadata addresses, carrier-grade NAT 100.64.0.0/10, multicast, reserved and unspecified ranges, IPv6 loopback, unique local fc00::/7, link-local fe80::/10, and IPv4-mapped or NAT64 forms of any of these. It then connects to the validated address (pinned, with the original name for SNI and the Host header) so DNS cannot change between the check and the connection.
- Redirects: at most 3. Every hop is validated from scratch (scheme, port, address, blocked hosts) and a redirect to an Airbnb, Vrbo or Booking.com host is refused.
- Limits: 5 second connect timeout, 15 second total, response body at most 2 MB (streamed and aborted at the limit, also after decompression). The body must start with `BEGIN:VCALENDAR`; anything else is `502 feed_fetch_failed`. No cookies and no authorization headers are sent. `User-Agent: HermiCalendarImport/1.0`, `Accept: text/calendar`.
- Egress: the fetch job runs in a worker whose outbound traffic goes only through an egress proxy that enforces the same address rules at the network layer and has no route to the private network, the database or metadata services.
- Privacy: feed URLs often carry a secret token. The URL is stored encrypted (`trip_imports.feed_url_enc`), shown back only as the host plus a masked path, and deleted on discard, on expiry of an import that was never confirmed, when polling is switched off, and on account deletion. It is kept only while "Keep checking this calendar" is on.
- Polling (opt-in): every 6 hours, through the same guard, with a conditional request and a content hash. A change produces a preview the person confirms (`GET /imports/{id}/changes`) and one push or in-app notice; nothing is applied automatically. Polling stops 7 days after the trip ends, after three consecutive failures (the person is told, `calendar_poll_stopped`), or when the person turns it off.
- Abuse: 5 registrations a day per user, 4 manual refreshes a day per import, at most 3 polled feeds per account, 60 fetches an hour per destination host across the platform; three consecutive failures mark the import `failed` and stop polling.

**Confirm.** `include_keys` selects candidates and `edits` corrects them. In one transaction the server creates the trip when the target is new (`status` `booked` when a booked flight or stay is included, else `planning`) with its destinations, then the rows: a flight becomes an itinerary item (`category: "travel"`, `status: "booked"`, `source: "import"`); a stay becomes a `lodging_options` row (`status: "booked"`, `added_via: "manual"`, `url` exactly as given in the source); a place (Google Maps or pasted) becomes an idea item with no day (`category` from the place, `source: "import"`, the list note in its notes); anything else becomes an itinerary item (`source: "import"`). Confirmation numbers go into the item's notes. For each flight listed in `track_fares` that has origin, destination, departure date and a paid amount, the server also creates a cached-mode `flight_routes` row and a `chosen_flights` row with `booked_at`, `paid_amount_minor`, `paid_currency` and `source: "import"`, so the booked-fare drop alert (5.8) starts watching it. Tracked flights count toward `routes_per_trip`; flights over the cap are created as plain items with warning `route_limit`, so nothing is lost.

**Reward (free Trip Pass, once).** The first qualifying confirmed import for an account grants a Trip Pass for the trip it filled, once per account for life (gate `import_reward`). It is granted only when all of these hold (settled values):

- the confirm created or added at least 3 items, at least one of them a flight or a stay (place-only imports and change confirmations never qualify);
- the trip is owned by the caller and has no active pass;
- the account has a verified email (an Apple relay address counts) and no active Plus;
- no earlier import reward went to this user, this normalized email or this Apple or Google subject (`trip_imports.reward_granted_at`).

The grant is a `trip_passes` row bound to the trip: `plan_code = 'trip_pass'`, no `store_transaction_id`, `starts_at` now, `expires_at` 90 days later, the same limits as a purchased Trip Pass (2 live routes, 60 live checks, 6 collaborators, 8 travelers) and its one-time 40 credit `trip_pass` grant, with `trip_imports.reward_pass_id` pointing at it. It is a gift: no card is asked, it is not refundable, and it can move to another trip once like any pass. The response carries `reward: TripPass`. Refreshes and later imports never grant again. Emits `import_reward_granted`.

```ts
type ImportSource = "ics_file" | "ics_feed" | "pasted_text" | "maps_file" | "places_text"
type ImportOrigin = "tripit" | "tripsy" | "wanderlog" | "google_calendar" | "google_maps" | "other"
type ImportStatus = "received" | "parsing" | "review" | "applied" | "failed" | "discarded"   // = 03 ck_trip_imports_status; a preview past 24 hours is `discarded`
type ImportFlightDraft = {
  airline: string | null; flight_number: string | null
  origin: Iata | null; destination: Iata | null
  depart_local: string | null; arrive_local: string | null        // YYYY-MM-DDTHH:MM, local time of the airport
  confirmation: string | null; paid: Money | null
}
type ImportLodgingDraft = {
  name: string | null; address: string | null
  check_in: string | null; check_out: string | null
  confirmation: string | null; price_total: Money | null; url: string | null   // url exactly as found, never fetched
}
type ImportCandidate = {
  key: string                                   // stable within the preview, used by confirm
  kind: "flight" | "lodging" | "item" | "place"      // place: a Google Maps or pasted place, imported as an idea with no day
  include: boolean                              // false for duplicates and low-confidence rows
  confidence: "high" | "medium" | "low"
  origin: "calendar" | "ai_extraction" | "calendar_and_ai" | "place_match"
  draft: ImportFlightDraft | ImportLodgingDraft | ItemIn
  duplicate_of: Uuid | null
  warnings: string[]                            // codes: outside_trip_dates, recurrence_trimmed, missing_dates, not_in_text
}
type ImportPreview = {
  id: Uuid; source: ImportSource; origin: ImportOrigin; status: ImportStatus
  trip: { mode: "new_trip" | "existing_trip"; trip_id: Uuid | null
          draft: { name: string; start_date: string | null; end_date: string | null; destinations: DestinationIn[] } | null }
  candidates: ImportCandidate[]
  counts: { flights: number; stays: number; items: number; places: number; duplicates: number }
  warnings: { code: string; message: string }[]   // unrecognized, ai_partial_no_credits, ai_skipped_no_credits, too_many_events
  feed: { host: string; last_fetched_at: string | null; polling: boolean; next_poll_at: string | null; pending_changes: number } | null
  credits: CreditReceipt | null                   // null when no AI ran
  reward_available: boolean                       // true when confirming now would grant the free Trip Pass (3 or more items including a flight or stay, verified email, no active Plus)
  error_code: string | null; expires_at: string; created_at: string
}
type ImportSummary = Pick<ImportPreview, "id" | "source" | "origin" | "status" | "counts" | "expires_at" | "created_at"> & { trip_id: Uuid | null; feed_host: string | null; polling: boolean }
type ImportChanges = {
  import_id: Uuid; found_at: string; expires_at: string
  added: ImportCandidate[]; changed: (ImportCandidate & { item_id: Uuid; was: Partial<ItemIn> })[]
  removed: { item_id: Uuid; title: string }[]      // events that left the calendar; shown, never deleted for the person
}
type ImportConfirm = {
  include_keys: string[]
  edits?: Record<string, Partial<ImportFlightDraft> | Partial<ImportLodgingDraft> | Partial<ItemIn>>   // by candidate key
  trip?: { name?: string; start_date?: string | null; end_date?: string | null; home_currency?: string; destinations?: DestinationIn[] }   // new trip only
  trip_id?: Uuid | null                         // attach to an existing trip instead (caller must be editor)
  extend_trip_dates?: boolean
  track_fares?: string[]                        // flight candidate keys to watch for the booked-fare drop alert
}
type ImportResult = {
  trip: Trip
  created: { itinerary_items: number; lodging_options: number; places: number; routes: number; chosen_flights: number }
  skipped: number; warnings: { code: string; message: string }[]
  reward: TripPass | null                       // the free Trip Pass, first confirmed import only
}
type ImportReward = {
  available: boolean                            // false once granted
  granted_at: string | null; trip_id: Uuid | null; pass: TripPass | null
  rules: string                                 // plain sentence for the UI: "Your first import earns a free Trip Pass for that trip when it adds 3 or more items including a flight or a stay." Empty for accounts with an active Plus (available: false)
}
```

### 5.27 Referrals

Every account has one referral code (`referral_codes`, created at bootstrap), shown on the profile screen as the link `https://hermi.world/r/<code>`. Rewards (`referral_rewards`) are AI credits for both people, never cash, never a discount on a purchase and never tied to a review or rating. Amounts below are the settled values, kept in the `setting_referral_credits` flag (03 section 11.5); [07-monetization-spec.md](07-monetization-spec.md) section 9 restates them.

| Endpoint | Auth | Gate and cost | Request and response | Errors and side effects |
|---|---|---|---|---|
| `GET /me/referral` | user | none | none to `Referral` | Code, share link, redeemed code (if any), stats and reward terms. |
| `GET /referrals/{code}` | none (30 a minute per IP) | none | none to `ReferralPreview` | Landing page data: the inviter's first name and the reward sentence. Unknown, disabled and capped codes all return the same `404 not_found`. `Cache-Control: no-store`. |
| `POST /me/referral/redeem` | user | once per account; within 14 days of sign-up | `{ code: string }` to `Referral` | Links the account to the code's owner. `409 referral_already_redeemed`, `422 referral_not_eligible` (own code, account older than 14 days, code disabled), `404 not_found`. The client also passes the code in `POST /me/bootstrap`, which calls the same logic and ignores a bad code. Creates `referral_rewards` rows with status `pending` for both people. |
| `GET /me/referral/rewards` | user | none | `?limit&cursor` to `Page<ReferralReward>` | History as referrer and as referee. |

**When a reward is granted.** A pending reward becomes `granted` when the referred person creates their first trip with dates, within 30 days of redeeming. They also need a verified email. Each person then receives 20 credits as a `promo` grant in `credit_grants` (`period_key = 'referral:<reward id>'`, which makes the grant idempotent, expiring after 12 months) and a notification. A referrer is paid for at most 5 rewards in a rolling 30 days and 10 in a calendar year; past a cap the referred person still gets their 20 credits and the referrer gets nothing more (`referrer_capped`). The caps are not raised for anyone. Promo credits are spent inside the normal provider-spend ceilings and do not raise them. Guards: a code cannot be redeemed by its owner, by an account on the same device (App Attest or device id) or by the same normalized email; admins can void a reward (status `void`, credits clawed back through the ledger). Emits `referral_redeemed` and `referral_reward_granted`.

```ts
type Referral = {
  code: string; share_url: string                  // https://hermi.world/r/<code>
  redeemed_code: string | null                     // the code this account used, if any
  stats: { signups: number; qualified: number; credits_earned: number }
  reward: { credits_each: 20; expires_after_months: 12; cap_per_30_days: 5; cap_per_year: 10; qualifying_action: string }   // plain sentence for the UI: "after your friend's first trip with dates"
}
type ReferralPreview = { inviter_first_name: string | null; reward_sentence: string }
type ReferralReward = {
  id: Uuid; role: "referrer" | "referee"; status: "pending" | "granted" | "void"
  credits: number; other_first_name: string | null
  created_at: string; granted_at: string | null
}
```

### 5.28 Public pages: sample trips and shared trips

These routes need no sign-in. They feed the pages search engines see: public sample trips and opted-in shared trips. All are read-only, cacheable at Cloudflare and rate limited per IP (1.8).

| Endpoint | Auth | Gate and cost | Request and response | Errors and side effects |
|---|---|---|---|---|
| `GET /public/sample-trips` | none | none | `?destination=&tag=&limit&cursor` to `Page<SampleTripSummary>` | Staff-curated sample trips. `tag` filters on `sample_trips.tags` (the Beach, City, Mountains and Food chips). A sample trip is an ordinary trip owned by a Hermi content account and published from the admin console; nothing else from that account is ever exposed. `Cache-Control: public, max-age=3600`. |
| `GET /public/sample-trips/{slug}` | none | none | none to `SampleTrip` | The presentation payload (5.15) with the same redaction as a share link (no people, no notes), labeled "Sample trip". Prices are shown as example prices with their observed date. `book_slide` is always `null`: sample pages carry no partner links. `404` for unpublished slugs. |
| `POST /public/sample-trips/{slug}/copy` | user | `active_trips` | `{ start_date?: string }` with `Idempotency-Key` to 201 `Trip` | "Use this plan" (the one button label; event `sample_trip_copied`): copies days, items and saved places (never flights or prices) into a new trip owned by the caller, shifting dates to start at `start_date`. Items get `source: "manual"`. Emits `sample_trip_copied`. WF-133 builds the 5.28 sample routes and WF-107 reuses them. |
| `GET /shared/{token}/meta` | none (per-IP and per-token limit) | none | none to `SharedMeta` | Title, description and cover for the page head and social cards, so the web app can render them at the edge. Returns `indexable` so the page sets `noindex` when it is false. `410 share_link_revoked` for revoked or expired links. |
| `GET /public/sitemap` | none | none | `?cursor` to `Page<{ url: string; updated_at: string }>` | Sample trips and shared links with `indexable: true`, for the sitemap generator. `Cache-Control: public, max-age=3600`. |
| `GET /public/status` | none (60 a minute per IP) | none | none to `PublicStatus` | The same component summary the public status page shows (web app, API, AI features, fare data, push), so the app can show a banner when something is degraded. `Cache-Control: public, max-age=30`. The hosted status page is separate and keeps working when the API is down (02 section 8.1). |
| `GET /public/how-we-earn` | none | none | none to `HowWeEarn` | Data for the public "How we earn" page: the rules, every active partner with its category and disclosure line, and live counts. Built from `affiliate_programs` and `GET /affiliate/disclosure` content. `Cache-Control: public, max-age=3600`. |

The shared-trip read itself is `GET /shared/{token}` in 5.6 (redacted presentation, `X-Robots-Tag: noindex` unless the link is `indexable`), with `POST /shared/{token}/outbound` and `POST /shared/{token}/report` beside it. A shared trip opts in to search only when the owner sets `indexable: true` on the link, and then the server keeps `people`, `notes` and `hotel_address` redaction on.

```ts
type SampleTripSummary = { slug: string; title: string; destination_name: string; days: number; summary: string; cover: Trip["cover"]; tags: string[]; suits: string }   // tags and suits are sample_trips.tags and sample_trips.suits (03 5.19)
type SampleTrip = {
  slug: string; label: "Sample trip"; title: string; summary: string
  presentation: Presentation; book_slide: null
  cta: { label: "Plan your own"; url: string }; updated_at: string
}
type SharedMeta = { title: string; description: string; cover_url: string | null; indexable: boolean; canonical_url: string }
type PublicStatus = {
  overall: "operational" | "degraded" | "outage"
  components: { key: "web" | "api" | "ai" | "fares" | "push"; label: string; state: "operational" | "degraded" | "outage" }[]
  incident: { title: string; started_at: string; url: string } | null   // the current incident on the hosted status page
  updated_at: string
}
type HowWeEarn = {
  rules: string[]                                   // never ranked by commission, labeled links, no ads, no data sales, Airbnb, Vrbo and Booking.com pages are never fetched
  partners: { name: string; category: string; disclosure: string | null }[]   // affiliate_programs with status active
  counts: { partners: number; categories: number; link_labels: number }       // link_labels: surfaces that carry the commission line
  updated_at: string
}
```

### 5.29 Calendar feed

Each trip can publish a live calendar subscription that phones and desktop calendars refresh on their own. It is a read-only token URL: anyone who holds the URL can read the feed, like a "secret address" in other calendar apps, so the URL is shown once and can be rotated or turned off. Available on every tier; it does not count as a collaborator or a share link.

| Endpoint | Auth | Gate and cost | Request and response | Errors and side effects |
|---|---|---|---|---|
| `POST /trips/{trip_id}/calendar-token` | editor | none | none to 201 `CalendarFeed` | Creates the feed or rotates its token (256-bit random, stored only as `trips.calendar_token_hash`). The URL is returned only in this response. Rotating stops the old URL at once. Emits `calendar_feed_created`. |
| `GET /trips/{trip_id}/calendar-feed` | viewer | none | none to `CalendarFeedStatus` | Whether the feed is on, when it was created or rotated and when it was last fetched. Never returns the URL. |
| `DELETE /trips/{trip_id}/calendar-token` | editor | none | none to 204 | Turns the feed off. |
| `GET /calendar/{token}.ics` | none (the token) | 120 an hour per token, 600 an hour per IP | `If-None-Match` to `text/calendar; charset=utf-8` | Served at `https://api.hermi.world/v1/calendar/{token}.ics`. Unknown, rotated or disabled tokens, and deleted trips, return an empty `404`. Updates `last_fetched_at` at most once a minute. |

Feed content rules:

- Calendar header: `PRODID:-//Hermi//Trip//EN`, `X-WR-CALNAME` the trip name, `X-WR-TIMEZONE` the first destination's zone, `REFRESH-INTERVAL;VALUE=DURATION:PT1H` and `X-PUBLISHED-TTL:PT1H`.
- Events: an itinerary item with a start time becomes a timed event in the destination's `TZID` (end time, or one hour if none); an item with a day and no time becomes an all-day event; pool items with no day are left out. A booked stay becomes an all-day event from check-in to check-out (exclusive end). A chosen flight becomes an event on its departure date, timed when `depart_at_local` is known.
- Stable identity: `UID` is `item-<id>@hermi.world` (or `stay-<id>@...`, `flight-<id>@...`), `SEQUENCE` is the row's `version`, `LAST-MODIFIED` is `updated_at`. An item removed from the trip is dropped from the feed and calendar apps remove it on the next refresh.
- Privacy: `LOCATION` carries the place name and address. `DESCRIPTION` carries the item's notes only when they are not private, plus the link `https://hermi.world/trips/<id>` (which asks for sign-in). The feed never includes prices, paid amounts, confirmation numbers, private notes, people, partner links or affiliate click ids.
- Caching: `ETag` over the feed content with `If-None-Match` answered `304`, `Cache-Control: private, max-age=300`, `Referrer-Policy: no-referrer`. The token is in the path (not a query string) because some calendar apps drop query strings, and request logs record only the route template `/v1/calendar/{token}.ics`. At most 2,000 events per feed.
- A `limited` trip (owner's paid tier lapsed) keeps its feed; a soft-deleted trip serves `404` until restored.

```ts
type CalendarFeed = { url: string; webcal_url: string; created_at: string }      // url: https://api.hermi.world/v1/calendar/<token>.ics; webcal_url: the same with the webcal scheme for one-tap subscribe on iOS
type CalendarFeedStatus = { enabled: boolean; created_at: string | null; rotated_at: string | null; last_fetched_at: string | null }
```

### 5.30 Plan verification ("Verify this plan")

A person pastes an itinerary from ChatGPT, Gemini, Layla, Mindtrip or any other source. Hermi reads it into items (step 1), the person chooses which items to check (step 2) and Hermi checks each place, its opening hours and its price against place data and cited pages, then the person can import the confirmed items. The pasted text is redacted before the model sees it and is never stored; Hermi never opens a link in the text and never opens Airbnb, Vrbo or Booking.com pages. The AI details, prompts and limits are in [06-ai-agents-spec.md](06-ai-agents-spec.md) section 5.11 and the tables in 03 section 5.20. The feature works on every tier (the `ai` gate, consent and credits apply) and is off when the `verify_plan` flag or the `ai.verify` kill switch says so.

| Endpoint | Auth | Gate and cost | Request and response | Errors and side effects |
|---|---|---|---|---|
| `POST /trips/{trip_id}/verify-plan` | editor | `ai`, `credits(1)` (`explain`, run kind `verify_extract`; kill switch `ai.verify`) | `VerifyPlanIn` with `Idempotency-Key` to 201 `PlanVerification` (status `review`) | Redacts personal data, reads the text with Haiku (strict schema, no tools) and returns up to 25 items. Nothing recognized: the credit is refunded and `warnings` has `unrecognized`. `422 plan_too_long`, `402 insufficient_credits`, `403 ai_consent_required`, `503 feature_disabled`. The pasted text is not stored. |
| `GET /trips/{trip_id}/plan-verifications` | viewer | none | `?limit&cursor` to `Page<PlanVerificationSummary>` | Verifications of the last 30 days on the trip. |
| `GET /plan-verifications/{id}` | viewer on the trip | none | none to `PlanVerification` | Items, verdicts and evidence. Poll while `status` is `checking`. `410 import_expired` after 30 days. |
| `PUT /plan-verifications/{id}/selection` | editor | `verify_items` | `{ item_ids: Uuid[] }` to `PlanVerification` | Chooses which items to check (at most `plans.limits.verify_items_per_run`: Free 5, Plus and Trip Pass 12). The default selection is the first items in plan order. `402 limit_reached` (no paywall) over the cap. |
| `POST /plan-verifications/{id}/check` | editor | `ai`, `credits(n)` where n is the number of selected items (`verify_plan`, 1 each; 6 or more needs the usual confirm), `verify_items`; one check at a time per verification | `Idempotency-Key` to 202 `PlanVerification` (status `checking`, `Location` the same resource, `events_url` the run stream) | Reserves n credits, creates the `verify_plan` run and enqueues the worker. Progress streams on `GET /agent-runs/{run_id}/stream` (5.13, events `item.checked`). Settles to the items that ended green, amber or red and refunds the rest. `409 state_conflict` when already checking, `402`, `429 provider_budget_exhausted`. |
| `POST /plan-verifications/{id}/import` | editor | none | `{ include_item_ids: Uuid[] }` with `Idempotency-Key` to 201 `{ created: number, skipped: number }` | Writes the ticked items as itinerary items (`source: "verify_plan"`, with `check_url` and `checked_at` from the evidence, so the freshness flag and recheck apply). Free, no credits. Red items can be ticked but are never ticked by default. |
| `DELETE /plan-verifications/{id}` | editor | none | 204 | Discards the result and its evidence. Items already imported stay. |

```ts
type VerifyPlanIn = { text: string /* max 8000 */; source_label?: "chatgpt" | "gemini" | "layla" | "mindtrip" | "other" }
type Verdict = "green" | "amber" | "red" | "unchecked"      // green: confirmed; amber: differs or partly confirmed; red: could not be found
type PlanVerificationItem = {
  id: Uuid; position: number; day_label: string | null; planned_day: string | null; planned_start: string | null
  name: string; category: ItemCategory
  claimed: { hours: string | null; price: Money | null }                       // what the plan says
  selected: boolean; verdict: Verdict
  reason_code: "not_found" | "hours_differ" | "price_differ" | "closed_at_planned_time" | "partly_confirmed" | "blocked_source" | "over_cap" | "budget_stop" | "provider_error" | null
  reason: string | null                                                       // one plain sentence: "Closed on Mondays. Your plan has Monday at 10:00."
  checks: { exists: "confirmed" | "differs" | "unconfirmed"; hours: "confirmed" | "differs" | "unconfirmed" | "not_claimed"; price: "confirmed" | "differs" | "unconfirmed" | "not_claimed" } | null
  found: { place_name: string | null; hours: string | null; price: Money | null; lat: number | null; lon: number | null } | null
  evidence: { source_url: string; source_domain: string; seen_at: string; from_cache: boolean } | null   // the evidence label: "Found on [site], checked [date]"; always set for green and amber
  include_in_import: boolean; imported_item_id: Uuid | null
}
type PlanVerification = {
  id: Uuid; trip_id: Uuid; source_label: string; status: "extracting" | "review" | "checking" | "done" | "failed" | "discarded"
  items: PlanVerificationItem[]
  counts: { found: number; selected: number; green: number; amber: number; red: number; unchecked: number }
  price: { per_item_credits: 1; max_items: number; selected_credits: number }   // the price shown before the second step
  warnings: { code: string; message: string }[]                                  // unrecognized, over_cap
  credits: CreditReceipt | null; events_url: string | null
  error_code: string | null; created_at: string; expires_at: string
}
type PlanVerificationSummary = Pick<PlanVerification, "id" | "source_label" | "status" | "counts" | "created_at" | "expires_at">
```

## 6. Webhooks

All webhook endpoints are public routes (no bearer token), excluded from the cross-tenant test by an explicit allow-list, and served under `/v1/webhooks`. Shared processing rules:

1. Read the raw body, verify the signature with a constant-time compare before parsing. Invalid: `401 invalid_signature`, log, never process.
2. Insert into `webhook_events (provider, event_id, event_type, payload, received_at)` where `event_id` is the provider event id (RevenueCat `event.id`, network `txn` key, Resend `svix-id`, Supabase hook id); the primary key is `(provider, event_id)`. `INSERT ... ON CONFLICT DO NOTHING`. If the row already existed and `processed_at` is set (`status = 'processed'`), return `200` and stop. This is the idempotency guarantee.
3. Process in one transaction, set `status = 'processed'` and `processed_at`, return `200`. Unknown event types are stored (`status = 'ignored'`) and acknowledged with `200`. A transient failure returns `500` so the sender retries (`attempts` is incremented); a permanent failure stores `error` with `status = 'failed'` and returns `200` and alerts (payment webhook failures page the on-call).
4. Handlers are order independent: each applies the state carried in the event (and, for billing, re-reads the subscriber from RevenueCat) rather than assuming the previous event arrived.
5. Payloads are untrusted data. Amounts come from our own `store_transactions`, never from a webhook field alone.

| Endpoint | Sender | Verification | Events handled and effects |
|---|---|---|---|
| `POST /webhooks/revenuecat` | RevenueCat | `Authorization: Bearer <REVENUECAT_WEBHOOK_SECRET>` compared in constant time; `environment` field must match the deployment (sandbox events are accepted only in staging) | `INITIAL_PURCHASE`, `RENEWAL`, `PRODUCT_CHANGE`, `CANCELLATION`, `UNCANCELLATION`, `BILLING_ISSUE`, `EXPIRATION`, `REFUND` (as `CANCELLATION` with reason), `NON_RENEWING_PURCHASE`, `TRANSFER`, `SUBSCRIBER_ALIAS`. Upserts `subscriptions` (unique on `store` and `original_transaction_id`) and `store_transactions` (unique on `store` and `store_transaction_id`), recomputes `entitlements`, grants the monthly credit allowance on renewal (`credit_grants.period_key` keeps it idempotent), binds a Trip Pass to the trip by inserting `trip_passes` (the purchase flow sent `trip_id` as a subscriber attribute; a pass with no trip stays `unapplied`, meaning a `store_transactions` row with no `trip_passes` row), grants credit packs keyed by the store transaction (`credit_grants.store_transaction_id` is unique), and claws back unspent credits on refund (`clawback` ledger rows; a shortfall blocks AI until later grants cover it). `app_user_id` is our user UUID. Emits `subscription_started`, `subscription_renewed`, `subscription_canceled`. |
| `POST /webhooks/affiliate/{network}` | Travelpayouts, Stay22, Viator (where a network offers postbacks); `{network}` is an `affiliate_programs.network` value and the `webhook_events.provider` | Per network: Travelpayouts shared token in a header or query parameter plus IP allow-list; Stay22 and Viator by token. Reject unknown slugs with `404`. | Writes `affiliate_conversions` upserted on `(program_id, network_txn_id)`, matched to `link_clicks` by sub-id, status history (`pending`, `approved`, `rejected`, `paid`). An unmatched conversion is stored with `click_id = null` and counted toward the unmatched-share health metric. Postbacks are a supplement: the nightly network pull job is the source of truth. Conversions never change any user-visible feature. |
| `POST /webhooks/resend` | Resend | Svix signature (`svix-id`, `svix-timestamp`, `svix-signature`) verified with `RESEND_WEBHOOK_SECRET` in constant time; a timestamp more than 5 minutes old is refused | `email.bounced` and `email.complained`. Marks the address undeliverable (hard bounce) or stops marketing mail (complaint) and writes the delivery row; never changes an account's data. Other event types are stored as `ignored`. |
| `POST /webhooks/supabase` | Supabase Auth hook | Shared secret in `Authorization: Bearer <SUPABASE_AUTH_HOOK_SECRET>` compared in constant time | The auth hook (for example after sign-in or an email change): keeps `auth_identities` and the verified-email flag in step with Supabase. Idempotent on the hook id. Never creates a `users` row (that stays `POST /me/bootstrap`). |

RevenueCat is the only store feed: there is no Apple webhook, and every purchase event arrives on `POST /webhooks/revenuecat`. The providers (`webhook_events.provider`) are exactly `revenuecat`, `travelpayouts`, `viator`, `stay22`, `resend` and `supabase` (03 `ck_webhook_events_provider`; `/webhooks/affiliate/{network}` accepts `travelpayouts`, `viator` and `stay22`).

Later: Phase 3 adds `POST /webhooks/stripe` (group payments, print orders, advisor seats). Phase 1 has no web purchases (the web paywall says "Upgrade in the iOS app") and no Stripe webhook: every purchase is an App Store purchase whose events arrive on the RevenueCat endpoint above. Web billing arrives with Android in Phase 2.

Replay protection: a webhook older than 7 days is stored and ignored unless it is a refund or revocation. `webhook_events` rows are kept 12 months (03 section 8).

## 7. Mapping from the existing Trip Planner API

For the team reusing the current code. Phase 1 covers every row; new Phase 1 routes (imports, plan verification, referrals, sample trips, calendar feed, booked fare, public status) have no existing equivalent.

| Existing route (under `/api/v1`) | Hermi route (under `/v1`) | Change |
|---|---|---|
| `/trips`, `/trips/{id}` | same | UUIDv7 ids, membership scoping, `version`, `capabilities` |
| `/trips/{id}/activities`, `/activities/{id}` | `/trips/{id}/items`, `/items/{id}` | Renamed; adds `sort_order`, reorder, move, `cost` |
| `/trips/{id}/days/{day}` | same | `version` added |
| `/trips/{id}/routes`, `/routes/{id}`, `/routes/{id}/choice`, `/routes/{id}/history`, `/routes/{id}/date-grid` | same, plus `mode`, `/price-history`, alerts | `history` renamed `price-history` |
| `/trips/{id}/flights/refresh`, `/flights/best`, `/flights/summary`, `/flight-quotes/{id}` | same, `/fares/{id}` | "quote" becomes "fare"; `live-search` added |
| `/trips/{id}/lodging`, `/lodging/{id}`, `/lodging/{id}/hearts/{person_id}` | same, `/votes/me` | Hearts stay hearts (`lodging_votes`), now per user; `/lodging/preview` becomes `/lodging/parse-link` (no fetching) |
| `/trips/{id}/lodging/search-rentals` | `/trips/{id}/lodging/rental-search` | Metered, cached |
| `/people` | same | Owner scoped |
| `/places/search`, `/places/geoapify/{id}`, `/places/wiki` | `/places/search`, `/places/{id}` | Wiki folded into details |
| `/runs`, `/runs/{id}`, `/runs/{id}/events`, `/runs/{id}/outputs`, `/runs/{id}/cancel` | `/agent-runs/...` plus `/stream` | SSE added; start endpoint is new |
| `/settings` | `/me/settings` | Per user |
| `/api/auth/login`, `/session`, `/logout` | `/me/bootstrap`, `/me`, `/me/sign-out` | Passcode removed |
| `/api/agent/v1/*` | removed | The worker calls services in process |
| `/system/status`, `/system/backup`, `/usage/serpapi` | admin API | Ops only |

## 8. OpenAPI generation

FastAPI generates the OpenAPI 3.1 schema from the Pydantic 2 models and route declarations. The schema is the contract.

- `GET /v1/openapi.json` is served in development and staging only; production disables `/docs` and `/openapi.json`. The admin and webhook routers are created with `include_in_schema=False` so they never enter the public schema (the admin console has its own generated client from a second schema, `/v1/admin/openapi.json`).
- Give every route an explicit `operation_id` of the form `module_action` (`trips_create`, `flights_live_search`, `agent_runs_start`) so generated function names are stable, and a `tags` entry per module in section 5. Declare `responses={...}` with `Problem` for every documented error code so the client types include them. Mark credit-spending routes with the `x-credits: <action>` and `x-idempotency-required: true` extensions.
- `npm run gen:api` runs `uv run python -m hermi.tools.dump_openapi > frontend/src/lib/api/openapi.json` and then `openapi-typescript openapi.json -o src/lib/api/schema.d.ts`. Commit both files. CI fails if regenerating changes the committed `schema.d.ts` (drift check), and a contract test fails if a route is missing `operation_id` or a 4xx response model.
- The web and iOS (Capacitor) clients use `openapi-fetch` on top of the generated `paths` type. `client.ts` sets `baseUrl` from `VITE_API_BASE_URL`, middleware adds `Authorization`, `X-Hermi-Client`, `X-Client-Version` and `X-Request-Id`, adds an `Idempotency-Key` for routes marked `x-idempotency-required`, refreshes once on 401, maps `application/problem+json` to a typed `ApiError` keyed by `code`, and sends `If-Match` from the cached `ETag`.
- SSE is not described by OpenAPI. The stream route is documented with a `text/event-stream` response and the event payloads in section 5.13; the client has a small hand-written reader (`lib/api/sse.ts`) that uses the generated `RunEvent` type.
- Enums in this file are closed in the schema but clients treat unknown values as "other" (1.1).
- Backend layout: one router module per section (`api/me.py`, `api/trips.py`, `api/flights.py`, `api/lodging.py`, `api/itinerary.py`, `api/places.py`, `api/ai.py`, `api/agent_runs.py`, `api/imports.py`, `api/plan_verification.py`, `api/calendar_feed.py`, `api/referrals.py`, `api/public.py`, `api/billing.py`, `api/affiliate.py`, `api/webhooks.py`, `api/admin/`), all using the shared dependencies `CurrentUser`, `require_trip(trip_id, min_role)`, `require_gate(...)` and `idempotent(...)`.
- Tests: the cross-tenant suite (user B against user A's ids expects 404 for every route not on the public allow-list), a gate test per row of section 4, an idempotency replay test for every required route, webhook fixtures with recorded signatures, an SSRF test suite for the feed importer (private, loopback, link-local and metadata addresses, DNS rebinding, redirects to private hosts, oversize bodies) a calendar-feed test that secrets (paid amounts, notes, confirmation numbers) never appear in the output, a polling test (unchanged feed makes no preview, a changed feed makes a preview that is never applied without confirm, the third failure stops polling and deletes the stored URL), and plan verification tests (the credits reserved equal the items selected, unchecked items are refunded, a green or amber item always carries evidence, a verdict cannot be edited by a member).

## 9. Example flow: trip, invite, agent run, events, credits settled

Maya (Plus, 60 credits left) plans Lisbon with Sam (Free). Headers `Authorization`, `X-Request-Id` omitted for brevity.

**1. Create the trip.**

```
POST /v1/trips
{ "name": "Lisbon in May", "start_date": "2026-05-12", "end_date": "2026-05-19", "home_currency": "USD",
  "destinations": [{ "name": "Lisbon", "country_code": "PT", "lat": 38.72, "lon": -9.14 }] }
-> 201 { "id": "0192a1f0-...-7c1", "version": 1, "my_role": "owner",
         "capabilities": { "effective_tier": "plus", "can_invite": true, "live_routes_max": 3, "max_collaborators": 6, ... } }
```

**2. Invite Sam and let him join.**

```
POST /v1/trips/0192a1f0-...-7c1/invites
{ "role": "editor", "email": "sam@example.com" }
-> 201 { "id": "0192a1f1-...", "url": "https://hermi.world/i/Qx7...", "uses_left": 1, "expires_at": "2026-10-07T..." }

# Sam opens the link, signs in, and POST /v1/me/bootstrap creates his Free account.
GET  /v1/invites/Qx7...          -> 200 { "trip_name": "Lisbon in May", "inviter_name": "Maya", "role": "editor" }
POST /v1/invites/Qx7.../accept   { "person_id": "0192a1f2-..." }
-> 200 Trip { "my_role": "editor", "capabilities": { "effective_tier": "plus", ... } }   # trip capabilities come from Maya's tier
```

**3. Maya starts a fare hunt.**

```
POST /v1/trips/0192a1f0-...-7c1/agent-runs
Idempotency-Key: 6f1c2b7e-5d7a-4e0e-9f7a-1f7f0a8f2a11
{ "kind": "fare_hunt", "route_ids": ["0192a1f3-..."] }
-> 202 Location: /v1/agent-runs/0192a2aa-...
{ "id": "0192a2aa-...", "status": "queued", "is_taster": false,
  "credits": { "action": "agent_run", "reserved": 40, "charged": null, "from_cache": false, "balance_after": 20, "reservation_id": "0192a2a9-..." },
  "events_url": "/v1/agent-runs/0192a2aa-.../stream" }
```

A retry with the same key replays this response with `Idempotent-Replay: true`. If Sam taps "Start agent run" while Maya's runs, Sam's call succeeds only if Sam has no active run and enough of his own credits (Free: the taster, once).

**4. Receive events.**

```
GET /v1/agent-runs/0192a2aa-.../stream
Accept: text/event-stream
id: 1  event: run.started   data: {"seq":1,"summary":"Fare hunt started for LIS"}
id: 4  event: tool.search   data: {"seq":4,"tool_name":"web_search","summary":"Searching fares JFK to LIS, May 12"}
id: 9  event: fare.saved    data: {"seq":9,"summary":"Saved $489 round trip on TAP, seen on the airline page","payload":{"fare_id":"0192a2b1-..."}}
id: 17 event: run.finished  data: {"seq":17,"summary":"2 fares saved","payload":{"status":"succeeded","credits":{"reserved":40,"charged":40,"balance_after":20}}}
```

**5. Credits settled.** The worker called `settle_credits`, which marked the `ai_usage` row `settled` (provider cost $0.61, under the $0.80 hard stop) and wrote the `settle` ledger row; the run shows its receipt.

```
GET /v1/me/credits        -> 200 { "total": 20, "monthly": 20, "trip_pass": 0, "purchased": 0, "next_monthly_grant_at": "2026-10-31T..." }
GET /v1/me/credits/ledger -> 200 { "items": [{ "kind": "settle", "delta": 0, "charged": 40, "action": "agent_run", "run_id": "0192a2aa-..." },
                                               { "kind": "reserve", "delta": -40, "charged": null, "action": "agent_run", "run_id": "0192a2aa-..." }, ...] }
GET /v1/agent-runs/0192a2aa-.../outputs -> 200 { "fares": [ { "price": { "amount_minor": 48900, "currency": "USD" }, "confidence": "indicative", "source_url": "..." } ], "notes": [...] }
```

If the provider had failed before any result, the run would end `failed`, `settle_credits(reservation, 0)` would write a `refund` of +40 and a `settle` row with `charged` 0, and `run.finished` would carry `"charged": 0`. If the same run had been a shared cache hit, the receipt would show `"from_cache": true, "charged": 8`.

**6. Maya picks the fare.**

```
PUT /v1/routes/0192a1f3-.../choice   { "fare_id": "0192a2b1-..." }   -> 200 Trip (flight_dates set)
GET /v1/trips/0192a1f0-...-7c1/offers?context=flight_chosen
-> 200 [{ "category": "flight", "label": "Book on Aviasales", "price_note": "price at last check, cached 2 h ago",
          "disclosure": "We earn a commission if you book here.",
          "non_affiliate": { "label": "Search on the airline's site", "url": "https://..." } }]
POST /v1/outbound { "entity_type": "fare", "entity_id": "0192a2b1-...", "surface": "flight-chosen", "trip_id": "0192a1f0-...-7c1" }
-> 201 { "click_id": "3vQ9kT2mX0bE7nLw1ZpCya", "url": "https://go.hermi.world/go/3vQ9kT2mX0bE7nLw1ZpCya" }
GET  /go/3vQ9kT2mX0bE7nLw1ZpCya   -> 302 Location: https://www.aviasales.com/...?marker=...&sub_id=8Kq2xPv1Lm
```

Later the nightly Travelpayouts pull (or a postback to `/v1/webhooks/affiliate/travelpayouts`) writes an `affiliate_conversions` row matched to the click by sub-id. Nothing in the app changes for the user.



## 10. Example flow: switch from TripIt, import, track a booked fare

Jo (Free, new account, signed in with Apple) exports a TripIt trip as `lisbon.ics` and uploads it from onboarding.

**1. Preview.**

```
POST /v1/imports/ics-file      (multipart: file=lisbon.ics)
-> 201 { "id": "0192b000-...", "source": "ics_file", "status": "review",
         "trip": { "mode": "new_trip", "draft": { "name": "Lisbon", "start_date": "2027-04-10", "end_date": "2027-04-17", "destinations": [{ "name": "Lisbon", "country_code": "PT", ... }] } },
         "candidates": [ { "key": "e1", "kind": "flight", "include": true, "confidence": "high", "origin": "calendar_and_ai",
                           "draft": { "flight_number": "TP204", "origin": "JFK", "destination": "LIS", "depart_local": "2027-04-10T21:05",
                                      "confirmation": "K7XQ2M", "paid": { "amount_minor": 48900, "currency": "USD" } }, "warnings": [] },
                         { "key": "e2", "kind": "lodging", ... }, { "key": "e3", "kind": "item", ... } ],
         "counts": { "flights": 2, "stays": 1, "items": 6, "duplicates": 0 },
         "credits": { "action": "explain", "reserved": 1, "charged": 1, "from_cache": false, "balance_after": 11, "reservation_id": "0192b001-..." },
         "reward_available": true, "expires_at": "2026-10-01T14:05:00Z" }
```

**2. Confirm, tracking the outbound flight.**

```
POST /v1/imports/0192b000-.../confirm        Idempotency-Key: 3a8d0f52-...
{ "include_keys": ["e1", "e2", "e3", "e4", "e5", "e6", "e7", "e8", "e9"], "track_fares": ["e1"] }
-> 201 { "trip": { "id": "0192b010-...", "status": "booked", "my_role": "owner", "capabilities": { "effective_tier": "trip_pass", "max_collaborators": 6, "collaborators_used": 0 } },
         "created": { "itinerary_items": 8, "lodging_options": 1, "routes": 1, "chosen_flights": 1 }, "skipped": 0, "warnings": [],
         "reward": { "id": "0192b011-...", "product": "trip_pass", "source": "import_reward", "status": "active", "expires_at": "2027-01-01T14:06:00Z" } }
```

**3. The price falls.** Days later the cached refresh for the route sees a matching fare for the same dates. The worker compares it with `paid_amount_minor` (48900) and, because the fall is over 5% and over the equivalent of 10 USD, sends a push: "You paid $489. It is now $431. Check the airline's change and credit rules." `GET /v1/routes/0192b020-.../booked-fare` shows `paid`, `current`, `drop: { amount_minor: 5800, currency: "USD" }` and `alert_active: true`.

**4. Subscribe and invite.** Jo turns on the calendar feed (`POST /v1/trips/0192b010-.../calendar-token` returns the URL once) and invites a partner (`POST /v1/trips/0192b010-.../invites`). The reward pass gives the trip 6 collaborator slots. Without a pass, a Free trip has 1 slot and a second invite returns `402 limit_reached` with reason `sharing`.
