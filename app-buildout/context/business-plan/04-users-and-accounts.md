# 04. Users and accounts

Part of the [business plan](README.md). The decisions of record in the README override anything here.

Written 2026-09-30, updated for Hermi and the Family, Group Trip Pass, concierge and advisor lanes. This file covers who a user is, what they can see, who they can share with, and what we owe them on privacy. Auth vendor prices are approximate and must be re-checked before commit. Pricing and credit numbers live in [02-pricing-tiers.md](02-pricing-tiers.md); the full schema lives in [06-database-and-data-integrations.md](06-database-and-data-integrations.md). This file keeps the data model at the level of entities and rules.

## 1. How auth works today and what must change

### 1.1 Current mechanism

| Piece | File | Behavior |
|---|---|---|
| Access guard | `backend/tripplanner/security.py` (`access_guard`) | Runs on every request. Checks the Host allow-list, requires `X-Trip-Planner: 1` and a same-origin `Origin` on writes, then requires auth on all `/api/*` except `/api/auth/`, `/api/health`, `/api/agent/`. |
| Local trust | `security.py` (`is_local_request`) | A loopback socket without `X-Forwarded-For` is authenticated with no credential. |
| Session token | `security.py` | Cookie `tp_session`, value `v1.<issued>.<sha256(passcode)[:16]>.<hmac>`. No user id. Changing `APP_PASSCODE` signs everyone out. 30 day life. |
| Login | `api/auth.py` | `POST /api/auth/login` compares one shared passcode with `hmac.compare_digest`. |
| Rate limit | `security.py` (`LoginLimiter`) | In-process dict, 5 failures per 5 minutes per IP. Lost on restart, wrong with several workers. |
| DB dependency | `api/deps.py` | Only `DbSession`. No `CurrentUser` anywhere. |
| Agent API | `api/agent.py` | Loopback plus an `AGENT_INGEST_API_KEY` bearer. Agents write into any trip by id. |
| Frontend | `auth-gate.tsx`, `login-screen.tsx`, `settings-page.tsx`, `lib/api/auth.ts` | Passcode screen, 401 interceptor, "each device asks for the passcode once" copy. |

### 1.2 Single-household assumptions

There is no `user_id` or tenant column anywhere. Authorization today means "are you inside the house", never "does this row belong to you".

| Area | Assumption | Change |
|---|---|---|
| Authn (`security.py`, `api/auth.py`) | One passcode, no identity, loopback bypass | Replace with a Supabase-verified JWT (bearer on mobile, cookie on web) that resolves to a `users` row. Loopback trust survives only behind `APP_MODE=local`, as a build flag. |
| Deps (`api/deps.py`) | No current user | Add `CurrentUser` and `require_trip(trip_id, min_role)`. |
| Trips | `list_trips` returns everything; `get_trip(db, id)` loads by sequential integer id | Trip membership table, every query filtered by membership, UUID `public_id`, 404 (not 403) for non-members. |
| People | Global list of travelers, no owner | Keep the table; add `owner_user_id` and `linked_user_id` (section 3.3). |
| Trip children (itinerary, lodging, flights, routines, runs, notes) | Scoped only by `trip_id`; by-id routes load the row directly | Every by-id route joins up to the trip and checks membership through the one dependency. A test fails if a route with an id parameter does not use it. |
| Votes | `LodgingVote` belongs to a Person | Keep, and add a nullable `user_id` so votes attribute to a real account. |
| Settings | `AppSetting` global key/value | Per-user settings table; `AppSetting` stays for server-wide flags only. |
| Worker heartbeat | UI shows "the PC" scheduler health | Ops-only metric, removed from the user UI. |
| Automation (`worker/*`, `claude_cli.py`, `backups.py`) | One machine, the owner's Claude subscription | Owned by [03-ai-features-and-costs.md](03-ai-features-and-costs.md) and [05-infrastructure.md](05-infrastructure.md). For accounts: every `Run` gets a `user_id` (who is charged) and a credit ledger row. |
| Config (`config.py`) | Passcode, Host list, `open_to_network` | Drop from production. Add Supabase JWT settings and Apple/Google client ids; document them in `.env.example`. |
| Files on disk | Shared local folders | Cloudflare R2 with per-trip key prefixes and signed URLs. |
| Frontend | Passcode gate, "this PC" and LAN copy, unkeyed cache | Sign-in and guest flow. Namespace React Query cache and localStorage by user id and clear on sign-out. Run `npm run gen:api`. |
| Tests (`backend/tests`, `e2e_seed.py`) | Unauthenticated fixtures | Two-tenant fixture and a cross-tenant test for every route (section 8). |

## 2. Identity

### 2.1 Decision

**Supabase Auth handles sign-in only. Our own `users` table, in our own Render Postgres, is the source of truth.** We do not use Supabase's database, its client SDK for data, or its row-level security. The backend verifies the Supabase JWT (JWKS, `sub`, `aud`, `exp`) in one dependency, and all authorization stays in our API.

Why:
1. Cost is nearly flat (about $25 a month on the Pro plan, roughly $25 to $60 to 100k MAU). Clerk and Cognito reach $1,350 to $1,800 or more at 100k MAU, and per-MAU prices of $0.02 or more would eat 10 to 40 percent of net revenue per paying user at low conversion. Auth must cost well under a cent per MAU.
2. It provides Sign in with Apple, Google and an email code out of the box, which are the methods we need.
3. One person builds and runs this part-time. Every hand-rolled auth component (token verification, refresh rotation, revocation, abuse controls) is future incident risk. Building it ourselves would take about 3 to 5 weeks plus ongoing security work.
4. Lock-in stays small. Our `users.id` is a UUID we generate, never the vendor id, and an `auth_identities(provider, subject, user_id)` table maps vendor subjects to it. Switching vendors is a remap of that table. Firebase Auth is the fallback; Auth0 is overkill.

Use custom SMTP (Resend or Postmark) to avoid Supabase's built-in email limits.

### 2.2 Sign-in methods

| Method | Phase | Notes |
|---|---|---|
| Sign in with Apple | 2 (iOS), web beta if cheap | Required by guideline 4.8 once Google is offered; ship it regardless. Handle "Hide My Email" relay addresses: store the relay email, do not assume it is real, and register our sending domain with Apple's relay so invites and receipts arrive. Keep Apple's refresh token to call the revoke endpoint on account deletion. |
| Email 6 digit code | 1 | A code, not only a link, so it works without bouncing between mail app and app. Rate limited. |
| Google | 1 | Web and later Android. |
| Passkeys | 4 (growth) | Needs provider support or a small WebAuthn layer. |
| Passwords, phone/SMS | Never | No reset flows, credential stuffing or SMS pumping fraud. |

### 2.3 Sessions

- Mobile: short-lived access JWT (15 to 60 minutes) in memory, refresh token in the iOS Keychain, rotation with reuse detection. Web: HttpOnly, Secure, SameSite=Lax cookie. Keep the existing `X-Trip-Planner` header and Origin check for cookie sessions.
- A devices table lists signed-in devices in settings, with "sign out everywhere". Needed for a lost phone and for account deletion.
- Keep the good ideas from the current code (constant-time compares); discard the passcode fingerprint and loopback bypass.

## 3. Account data model

The full schema is in [06-database-and-data-integrations.md](06-database-and-data-integrations.md). The entities and rules this file depends on:

### 3.1 Sharing belongs to the trip; a household exists only to pool a Family plan

Two people planning one trip is the core case, and friends share only specific trips. Membership is on the trip, with a per-trip role, and that stays true for every tier. A household is a narrow second structure: it exists only so up to 6 people can draw on one Family subscription and one pool of credits (section 3.6). Being in a household never gives anyone access to another member's trips; trips are still shared one at a time through `trip_members`. Advisor organizations (section 3.8) are a third structure with the same rule: they never grant trip access by themselves.

### 3.2 Entities

| Entity | Purpose and rules |
|---|---|
| `users` | Our account row: UUID id, email (may be an Apple relay), display name, locale, timezone, home currency and airports, status (`active`, `pending_deletion`, `deleted`), `is_guest`, timestamps. Tier is read from entitlements (and the household, for Family), with a cached copy for speed. |
| `auth_identities` | Maps a Supabase provider and subject to a user. Unique per provider and subject. |
| `devices` | Push token, platform, refresh-token hash, revocation. |
| `trips` (existing) | Gains an owner, a UUID `public_id`, `deleted_at`. |
| `households` | A Family plan group: payer user, name, status, subscription link. At most 6 active members. Section 3.6. |
| `household_members` | Household, user, role (`payer`, `member`), status (`invited`, `active`, `left`, `removed`), joined and left timestamps. One active household per user. |
| `trip_members` | Trip, user, role (`owner`, `editor`, `viewer`), inviter. Exactly one owner per trip. An advisor is an `editor` whose row carries `advisor_org_id` (section 3.8). |
| `advisor_orgs`, `advisor_seats`, `advisor_clients` | Hermi for Advisors: the organization, its paid seats, and the advisor to client relationship. Section 3.8. |
| `trip_invites` | Hashed token, role fixed at creation, expiry, use cap, revocation. |
| `trip_share_links` | Read-only public link with redaction flags. |
| `people` (existing, kept) | Traveler profiles. Gains `owner_user_id` and `linked_user_id`. Not renamed. |
| `trip_travelers` (existing) | Unchanged. |
| `entitlements`, `trip_passes` | Section 3.5. A Group Trip Pass is a `trip_passes` row with `pass_type='group'`. |
| `credit_ledger`, `credit_grants` | Who was charged (user, plus household when pooled), delta, reason, run id, source (`monthly_grant`, `household_grant`, `pack`, `trip_pass`), expiry. Rules in [02-pricing-tiers.md](02-pricing-tiers.md). |
| `consents`, `audit_events`, `activity_log`, `comments` | Consent versions (including per-request concierge and advisor access consents, section 3.9), security events, the per-trip change feed, and comments (comments can wait until after launch). |
| `concierge_requests`, `room_block_requests` | A request for a human to book, or a group room block; each holds a snapshot of exactly what was shared. Section 3.9. |

Every id exposed to clients is a UUID. Existing integer ids stay internal.

### 3.3 Person versus user

A `Person` is a traveler profile owned by a user (`people.owner_user_id`). It is planning data, not an account. Kids, parents, or a friend who only gets a PDF never install the app.

- `people.linked_user_id` is set when a traveler is claimed by a real account. On invite acceptance the app asks "Which traveler are you?" and links the invitee to that Person, so votes and flight origins attribute correctly. A Person links to at most one user per trip.
- Every new user gets one auto-created Person ("Me", airport from settings). This replaces today's hand-made "you two".
- A Person can exist without a user (guest traveler), and a user can be a member without being a traveler (an assistant planner).
- A linked Person's name and airports are visible only to co-members of that trip. Removing a member detaches the link; historic trips keep the Person, and the owner may rename it "Former member".

### 3.4 Roles

| Capability | Owner | Editor | Viewer |
|---|---|---|---|
| View trip, itinerary, lodging, flights | yes | yes | yes |
| Edit itinerary, add lodging, vote, comment | yes | yes | comment and vote only |
| Run AI research (spends credits) | yes | yes, from the editor's own credits | no |
| Invite or remove members, create share links | yes | invite viewers only (owner setting) | no |
| Delete trip, transfer ownership | yes | no | no |
| Leave trip | transfer first | yes | yes |

One dependency, `require_trip(trip_id, min_role)`, enforces this and returns 404 for non-members.

### 3.5 Capabilities and credits on a shared trip

Subscription state lives in `entitlements` (per user: tier `free`, `plus`, `family` or, behind a flag, `pro`; product id; expiry; grace period), populated from RevenueCat and App Store Server Notifications V2, with entitlements stored on our server. For Family, every active household member gets a `family` entitlement derived from the household, not from their own purchase. `trip_passes` records a Trip Pass or Group Trip Pass (trip, purchaser, transaction, `expires_at` 90 days after purchase). Both are non-renewing subscriptions in StoreKit, bound to the trip on the server.

**Rule: a trip's capabilities come from the owner's tier or an active pass on that trip, whichever is better. AI credits are charged to the acting user, from that user's own balance (for a Family member, the household pool).**

| Question | Rule |
|---|---|
| What can this trip do (collaborators, live routes, exports)? | The better of the owner's tier and the trip's Trip Pass. A Trip Pass allows up to 6 collaborators and 2 live routes; a Group Trip Pass allows up to 12 travelers and adds polls, cost splitting and the room-block request; Plus, Family and Free limits are in [02-pricing-tiers.md](02-pricing-tiers.md). |
| Can a Free owner invite editors? | No. Sharing is a Plus, Family or pass feature. The invite button on a Free trip is a paywall moment. One `can_invite(trip)` function makes the decision. |
| Can a Free account join someone else's trip? | Yes, free, always. The invitee gets the owner's tier on that trip only. Joined trips do not count toward the invitee's 2 active trips, and their own trips keep Free limits. |
| Who pays for AI on a shared trip? | The person who starts the action, from their own monthly and purchased credits (a Family member draws on the household pool first). An owner-funded pool is not built at launch, so one collaborator cannot drain the owner. A pass's credits (40 or 80) are spendable by anyone on that trip, but only on that trip, and are charged to the pass, not to a person. |
| Owner's Plus or Family lapses, or a pass expires | The trip becomes limited. Data stays and remains readable and editable by the owner; extra members become viewers (never deleted); a banner tells the owner. Data is never held hostage. |
| Apple Family Sharing | Off for every product. Family plan members are invited in the app (section 3.6), so we control the six-person limit and the pool. |

The client never decides. It reads `GET /me/entitlements` and per-trip `capabilities` in `TripOut`, and the server enforces on every call.

### 3.6 Households and the Family plan

A Family subscription ($8.99 a month or $59.99 a year) is bought by one person, the **payer**. The payer's Apple ID holds the subscription and pays; nobody else needs to buy anything.

| Question | Rule |
|---|---|
| Who is in a household? | The payer plus up to 5 invited members, 6 active in all. Each member has their own Hermi account, trips and sign-in. Invites use the same hashed, expiring tokens as trip invites (section 4). |
| Who is the payer? | The user whose `subscriptions` row holds the Family product. Stored as `households.payer_user_id`. Only the payer can invite, remove members, or see billing. A payer cannot hand a subscription to someone else (Apple does not allow it); "change payer" means the new payer buys Family and the old household moves onto that subscription with no gap in membership. |
| What does a member get? | The `family` tier on their own trips (Plus features, 5 live routes shared across the household) and access to the pool. Members' trips stay private to them until they share a trip the normal way. A household member cannot see another member's trips, people, notes or purchases. |
| How do pooled credits work? | The 150 monthly credits are one `credit_grants` row owned by the household, and the provider-spend ceiling ($3.40 a month) is also one pooled number, so the household as a whole cannot cost more than that. Any active member can spend from the pool. Each spend row records who acted, so the payer sees a per-member usage list. Purchased credit packs stay personal to the buyer and are never pooled. |
| Fairness inside the pool | One member can use at most 60 percent of a month's pool (90 credits) unless the payer raises it in settings. This stops one person draining the others. It is a starting limit to tune. |
| Leaving | A member can leave at any time. They fall back to their own tier (usually Free) immediately, lose pool access, and keep everything they made. Credits they already spent stay spent. Trips they own that exceed Free limits become limited in the same way as a lapsed Plus (section 3.5): data stays, extra members become viewers. The payer can remove a member the same way. |
| Payer cancels, or billing fails | Family stays until the paid period ends (and any Apple grace period), then every member becomes Free. Household and usage history are kept for 90 days so a resubscribe restores it. |
| Payer deletes their account | The app says the household will end at the paid period's end, and offers "change payer" first. Members are told by email. The subscription is not cancelled by deletion (section 7.2). |
| Abuse limits | One active household per user. A person who leaves or is removed cannot join a different household for 30 days. At most 4 membership changes (adds plus removals) per household in any rolling 30 days, so a plan cannot be rotated through dozens of people. At most 10 pending invites. New members must sign in with their own account; App Attest and the disposable-email blocklist apply. There is no address check. The pooled ceiling is the hard backstop: even total abuse costs at most $3.40 a month. Repeated breaches suspend invites, then the household's pool. |

### 3.7 Group Trip Pass membership rules

A Group Trip Pass ($19.99) is bought by the trip owner and bound to one trip on the server, like a Trip Pass, for 90 days.

- **Who counts.** Up to 12 travelers. A traveler is either a `trip_members` account or a `people` row on the trip with no account (a friend who only pays their share). Both count toward 12. The owner counts.
- **Joining.** Members join by invite link or email exactly as in section 4, free, on any tier. Their own tier does not matter on this trip.
- **Roles.** Owner, editor and viewer as in section 3.4. Anyone on the trip can vote in a poll and record an expense. Editors and the owner create polls and close them. Only the owner can send a room-block request or remove a member.
- **Expenses and leaving.** A member with an unsettled balance cannot leave, and the owner cannot remove them, until the balance is settled or the owner writes it off (recorded in `settlements`). Expense rows a person created stay when they leave, attributed to "Former member".
- **Access to money data.** Expense shares are visible to everyone on the trip, since splits are shared by nature. Payment details are not stored by us; collection runs through Stripe (see [05-infrastructure.md](05-infrastructure.md)) and only the Stripe customer reference is kept.
- **When the pass expires.** The trip drops to the owner's own tier. Polls and expenses become read-only, the ledger and balances stay visible and exportable, and open balances can still be settled. A banner tells the owner. Nothing is deleted.
- **Invitees' credits.** The pass's 80 credits belong to the trip. Invitees do not get extra personal credits from it.

### 3.8 Advisor organizations and client access

Hermi for Advisors is a web product for independent travel advisors, billed by Stripe on the web ($29 a seat a month or $24 annual). It lives alongside the consumer app and shares the same `users` table.

| Entity | Rules |
|---|---|
| `advisor_orgs` | The business: name, billing owner, Stripe customer reference, branding fields for presentation mode, status. |
| `advisor_seats` | A user's paid seat in an org: role (`owner`, `advisor`), status (`invited`, `active`, `ended`). An advisor is a normal Hermi user with an active seat. Seats add web workspace features only; they do not change the person's own consumer tier. |
| `advisor_clients` | The relationship record: org, advisor seat, client (an existing user, or an email not yet joined), status, the consent version the client accepted, and an optional private note. A client is never created by an advisor without an invitation the client accepts. |

**What an advisor can see.** Only trips where the advisor has a `trip_members` row: either the advisor created the trip in the org workspace and invited the client, or the client (or any owner) invited the advisor from inside their own trip. Access is per trip, never per client and never per org. An advisor sees nothing of a client's other trips, traveler profiles, settings, purchases, credit balance or AI history. Invite links for advisors are labeled in the client's view ("Sam Lee at Harbor Travel can edit this trip").

**Client data separation.**
1. Every query still goes through `require_trip`. The advisor role is an `editor` row marked with `advisor_org_id`, so the same tenant-isolation tests cover it, and the cross-tenant suite adds an advisor case (advisor A cannot read advisor B's client trip, and an org admin cannot read a seat holder's client trips).
2. Advisor-private material (commission figures, internal notes, draft proposals) sits in org-owned tables and fields the client cannot query. Clients see the shared trip and the presentation, not the workspace.
3. The org owner can see the list of clients and trips a seat holds only for reassigning work, not the trip contents, unless the trip is marked "org visible" by the advisor. Reassigning a trip to another seat needs the client's acceptance.
4. The client can remove any advisor from a trip at any time, and access ends at once. If a seat ends or an org is cancelled, its advisors lose access to all client trips immediately; the trips stay with the client.
5. Client accounts are free, always. Their credits, tiers and Family or pass benefits are their own and are never charged to an advisor.
6. If a client deletes their account, their personal data is purged as in section 7.2. Proposals the advisor authored remain in the org workspace with the client's name replaced by "Former client". The advisor is an independent controller of the data they hold about their own clients; our terms say so, and advisor orgs sign a short data processing addendum.

Consumer app rule: the iOS app does not sell advisor seats or link to their purchase. Advisors sign up and pay on the web. See [07-local-to-app-store.md](07-local-to-app-store.md).

### 3.9 Concierge consent

"Have a human book this" is optional and never required to use any feature. A request is fulfilled by the founder acting as an advisor under a host travel agency, and commission is earned from the suppliers through that agency. It needs its own consent, because data leaves our service for a third party.

**Who receives it.** Hermi (acting as the advisor) and the host agency, including its booking platform and the suppliers it books with.

**What is shared.** Only what the request form shows the user before they tap send:

| Shared | Not shared |
|---|---|
| Names of the travelers as they appear on the booking, typed or confirmed by the user for this request | Other trips, notes, comments, or AI history |
| Trip dates, destination, party size, budget, and the stay or options the user selected | Account id, Apple identifiers, sign-in method |
| The user's contact email (and phone if they add one) so the advisor can reply | Payment details (paid to the supplier or agency, never through Hermi or the app) |
| Preferences the user types into the request | Passport numbers and documents (the agency collects those through its own secure channel when needed; we do not store them) |
| Ages of child travelers, if a booking needs them | Precise device location |

**How consent works.**
1. The form shows a plain summary of the exact payload and the three parties, and discloses that Hermi earns a commission and that the user may get perks (breakfast, credits, upgrades). No pre-ticked boxes.
2. Consent is per request, stored in `consents(kind='concierge_share', version, request_id)` with a hash of the payload snapshot kept on `concierge_requests`. A second request needs a second consent.
3. The user can withdraw before booking. After a booking is confirmed, the agency must keep booking records under its own legal duties; we say so on the form.
4. Travelers other than the requester: the requester confirms they have the others' permission to share their names and ages. The form says so.
5. Status and messages show inside the trip. Only the requester and the trip owner see the request.

**Room-block requests** (Group Trip Pass, owner only) follow the same consent, with one addition: only group size, dates, destination, budget and the owner's contact are sent, never the list of traveler names.

**Retention.** Our copy of the request payload is kept 13 months after the travel date for commission reconciliation and disputes, then deleted. The agency's copy follows its own policy, named on the form. Account deletion removes our copy unless a booking is still pending or a dispute is open (section 7.2). Seller-of-travel registration rules in some US states fall on the agency; confirm that in the host agreement before launch (verify).

## 4. Invites, share links and the growth loop

- **Member invite.** The owner enters an email or taps "Invite" to produce a universal link `https://<domain>/i/<token>`. Tokens are random 128 bit, stored hashed, expire in 7 days, single use for email and capped multi-use for links. The role is fixed at creation. Only owners of Plus, Family or pass trips can create invites (section 3.5). Household and advisor invites are separate kinds (sections 3.6 and 3.8) with the same token rules.
- **Acceptance.** The link opens the app, or the App Store page with an "enter code" fallback. After sign-in the invite is redeemed server side. The invite email need not match the account email (Apple relay); the token is the proof.
- **Invitees get a free account** with the trip in front of them and no paywall before first value. This is the growth loop. Track invites sent, opens, installs, sign-ups, first edit, and second-trip creation.
- **Guest view without install.** A read-only web page for share links (itinerary, map) that ends with "Get the app to edit". Exact hotel address, prices and notes are hidden by default through the `redact` flags.
- **Abuse limits.** 20 pending invites per trip, 30 per user per day, an email domain throttle, and suspension of invite privileges after reports. The invite email uses the inviter's display name with our domain in the from address.
- **Revocation.** The owner can remove any member instantly. Authorization is checked on every request, so access ends immediately. Prior edits show as "Former member".

## 5. Onboarding

Show value before asking for an account. Ask for sign-in only when there is something to save or share, and for permissions only when they matter.

1. **Splash.** One line of value, "Plan a trip" (no account) and "Sign in".
2. **Guest mode.** Local-first: a guest can create one trip, add destinations and itinerary items and view maps, all stored on device. A server row (`is_guest=true`) is created lazily, only when the guest uses a server feature. Guest AI, if offered, is drawn from the Free allowance (12 credits a month) and tied to device attestation (App Attest), not added on top.
3. **"Save your trip" prompt.** Triggered by an invite, sharing, a second device, AI beyond the guest allowance, or export. Sign in with Apple first, then email code. On success, local guest data is claimed into the account (`POST /me/claim` with a signed guest token). Guest work is never lost; if the identity already exists, ask to merge and show counts.
4. **Profile (skippable).** Display name, home airport (typeahead; ask for location only if the user taps "near me"), currency from locale. This creates the "Me" Person.
5. **Trip creation.** Template or blank; dates optional, as today.
6. **Invite nudge** after three or more items, not on first launch.
7. **Push permission** after the first invite or a price alert, with a reason screen.
8. **No ATT prompt.** We do no cross-app tracking.

Invited users skip steps 1 and 2, land on the shared trip after sign-in with a "You were added by <name>" banner, then answer "Which traveler are you?".

**The two existing users.** A one-off script creates both users, assigns owners, creates `trip_members` and sets `people.linked_user_id` (see [06-database-and-data-integrations.md](06-database-and-data-integrations.md) for the data migration). Local mode (`APP_MODE=local`) can stay for development as a build flag, not a runtime bypass.

## 6. Collaboration features

| Feature | Phase 1 (web beta) | Phases 2 and 3 | Phase 4 |
|---|---|---|---|
| Shared trips with roles, invite by link or email | yes | | |
| Attribution ("added by Sam") | yes | | |
| Lodging voting, per user | yes | | |
| Optimistic concurrency | yes: extend `Activity.version` to other editable rows, 409 with latest | | |
| Sync freshness | Poll on foreground and every 15 to 30 s on a shared trip (`refetchInterval`, ETag, `updated_since`) | SSE if freshness is a measured complaint | WebSocket presence |
| Push for changes | | Digest style, at most 1 per hour per trip | Per-event settings |
| Activity feed | Simple reverse-chronological log | Filters, unread badge, owner revert within 7 days | |
| Comments | | | Comments, mentions, threads |
| Offline | Offline read | Offline write queue, last-writer-wins per field, 409 conflict UI | CRDT only if needed |
| Ownership transfer | yes | | |
| Web view of a shared itinerary | Read-only share link | | Full web editor |
| Polls and cost splitting (Group Trip Pass) | | Built in phase 2, on sale at launch; Stripe collection follows in phase 4 | Payment reminders |
| Concierge and room-block requests | | Phase 3 if the host agency is signed, otherwise phase 4 | |
| Advisor workspaces and client access | | | Phase 4 (web only) |
| Family households | | Phase 2 with the products | |

Two to five people rarely edit the same row at the same second, so polling with cheap conditional requests is enough and works on any host. Do not adopt CRDTs; row-level optimistic concurrency fits this relational data.

## 7. Privacy and compliance

### 7.1 Data we hold

| Category | Examples | Sensitivity |
|---|---|---|
| Account | Email (may be relay), name, Apple/Google subject | Personal |
| Travel plans | Destinations, dates, itinerary, lodging, notes | Sensitive by inference (when home is empty) |
| Traveler profiles | Names, home airports, possibly kids | Personal, may include minors' names |
| Precise location | Only if the user taps "near me"; not stored by default | Sensitive |
| Purchases | Transaction id, tier, Stripe customer reference (no card data) | Financial-adjacent |
| Group expenses | Who paid what and who owes whom on a trip | Financial-adjacent, shared with trip members |
| Concierge and advisor data | Booking request payloads, client lists | Personal, shared with named third parties only with consent (3.9) |
| Content | Notes, comments, uploads | User content |
| Diagnostics | Crash logs, IP, device model | Analytics |
| AI prompts | Trip context sent to model providers | See 7.5 |

### 7.2 Account deletion (Apple guideline 5.1.1(v), mandatory)

In-app path: Settings > Account > Delete account, confirmed with re-authentication and a plain list of effects. No support email or web-only route.

1. Immediately: revoke all sessions and refresh tokens, revoke the Apple token, unregister push tokens, cancel pending invites, set `status='pending_deletion'`.
2. Owned trips with other members: prompt to transfer or delete. If nobody is chosen, delete after a 30 day grace window unless a member accepts transfer.
3. Owned trips with no other members: deleted.
4. Trips owned by others: the user is removed; their contributions stay, attributed to "Deleted user" (disclosed in the privacy policy).
5. After 30 days (a recovery window for accidents): hard delete the user, identities, devices, personal `people` rows and AI history. Keep only what law requires (purchase records, tax invoices, an abuse audit hash) on a retention timer.
6. Deleted data ages out of backups within 35 days; the privacy policy says so.

Household and advisor effects: a Family payer is offered "change payer" first, a member simply leaves the household, and an advisor seat ends (clients keep their trips). A pending concierge booking or an open expense balance is shown in the confirmation and does not block deletion; open balances are written off with notice to the group. Deleting an account does not cancel the Apple subscription, or a Stripe subscription; the flow says so and deep links to Settings > Subscriptions without blocking deletion. "Delete a trip" and "Delete my AI history" are offered separately. The deletion job is an idempotent worker task with a checklist table so partial failures are visible.

### 7.3 Data export (GDPR Art. 20, CCPA access)

Settings > Account > Export my data: an async job produces a zip with JSON plus a readable PDF or CSV per trip, emailed as a link that expires in 7 days, after re-auth. Target under 24 hours; the legal limits are 30 days (GDPR) and 45 days (CCPA).

### 7.4 Regulations and store labels

| Item | Plan |
|---|---|
| GDPR (EU/UK) | Contract basis for the core service, consent for AI processing and marketing. Processor list with a DPA for each. Breach notice within 72 hours. EU data region only when EU revenue justifies it. |
| CCPA/CPRA | We do not sell data, and say so. No ad SDKs, so no "Do not sell or share" link. |
| Apple privacy label | Declare contact info, user content, identifiers, purchases, diagnostics and usage; location only if collected; tracking none. Vet every SDK before adding it. Ship `PrivacyInfo.xcprivacy`. |
| Google Play Data safety | Same inventory, when Android arrives (phase 4). |
| Privacy policy and Terms | Written by counsel and versioned; `consents` records the accepted version. |
| Children | Age gate 13+ (16+ for EU/UK locales). Not for children, not in the Kids category. Minors on a trip are entered by an adult as a first name and color, with no birthdate or photo. |
| Email marketing | Separate opt-in and one click unsubscribe. Transactional mail is separate. |

### 7.5 What goes to AI providers, and consent

Sent (minimum necessary): destination names, dates, party size, budget, activity preferences and free text the user typed. Not sent: email, name, account id, Apple identifiers, home address, other travelers' names (use "Traveler 1"), payment data. Use an opaque per-request id for provider abuse tracking. Provider choice and costs are in [03-ai-features-and-costs.md](03-ai-features-and-costs.md).

1. **Consent screen** the first time an AI feature is used, per Apple's guideline 5.1.2(i) on sharing personal data with third-party AI. Name the providers, say what is sent and that it is not used for training. Stored in `consents(kind='ai_processing', version)` and revocable; revoking disables AI, not the app.
2. Contracts with zero-retention or no-training terms and a DPA.
3. In shared trips the requester's consent covers their own prompt, but content by others enters the context. Trip settings say so, and the owner can disable AI for the trip.
4. Notes and comments flagged private are excluded from AI context.
5. Content fetched from the web or written by collaborators is untrusted: it never changes tool permissions or reaches another user's data. `agent_context.build_context` reads only the one trip being planned.
6. Every AI call is logged in `runs` with user id, trip id, provider, tokens and credits.

### 7.6 Retention

| Data | Retention |
|---|---|
| Active account data | While the account exists |
| Soft-deleted trips | 30 days in trash, then hard delete |
| Deleted account | 30 day grace, then purge; backups age out within 35 more days |
| Invite tokens | Expire at 7 days; rows purged at 30 |
| Share links | Until revoked or expiry set by the owner (default 90 days) |
| Auth and audit logs | 12 months; IPs hashed after 30 days |
| AI request logs | Metadata (tokens, cost, model) 13 months for billing. Prompt and response content: only the visible in-app history, and 30 days server side |
| Purchase records | As tax law requires (typically 7 years), stripped of profile data |
| Concierge and room-block payloads | 13 months after the travel date, then deleted |
| Expense and settlement rows | With the trip; anonymized names after a member leaves |
| Place and API caches | Per the provider's cache terms (`expires_at` exists) |
| Crash and analytics | 90 days |

### 7.7 Site terms

The rule of never fetching Airbnb, Vrbo or Booking pages automatically, and using no scrapers, carries over and matters more at scale, since our servers would be the ones breaching terms. User-pasted links and licensed APIs only. `link_preview.py` needs a legal review before scaling.

## 8. Security: tenant isolation, rate limits, abuse

### 8.1 Tenant isolation

1. Every request resolves `CurrentUser` first and rejects any status other than `active`.
2. Every query on a trip child table goes through `require_trip` or a join on `trip_members`. No route takes a bare id and calls `db.get()`.
3. Two layers: app-level scoping plus Postgres row-level security on our own database (`SET LOCAL app.user_id` per transaction). RLS catches the route someone forgets; write policy tests.
4. 404 for unauthorized ids, never 403. UUIDs defeat enumeration.
5. Request schemas never accept `owner`, `role` or `tier` from the client.
6. **Cross-tenant test suite.** Users A and B; a parametrized test walks every route in `app.routes`, calls it with B's token against A's ids and expects 404. CI fails on any route not listed as public. This is the most valuable test in the product.
7. Storage uses signed, expiring URLs with keys prefixed by trip UUID.
8. `api/agent.py` (loopback plus API key) is fine for our own worker, but each run token is scoped to one run, one trip and one user, and expires with the run.
9. Secrets stay in the environment, never the repo. Signing keys rotate with key ids.

### 8.2 Rate limits and abuse controls

The in-process `LoginLimiter` moves to a Postgres-backed store (no Redis until about 10k MAU; see [05-infrastructure.md](05-infrastructure.md)).

| Surface | Starting limit |
|---|---|
| Email code send | 5 per email per hour, 20 per IP per hour, a circuit breaker on email spend |
| Code verify | 5 attempts per code, then invalidate |
| Sign-in token exchange | 30 per IP per 10 minutes |
| Invites | 30 per user per day, 20 pending per trip |
| Write API | 120 per minute per user, 600 per minute per IP |
| AI runs | Credits, one agent run at a time per account, 30 AI actions per hour per user, and the per-account provider-spend ceilings in the README |
| Search and geo proxies | Per-user quotas (make the `serpapi_budget.py` pattern per user) |
| Share-link views | Per-IP and per-token throttles |
| Export and delete | 1 per day each |

Also: App Attest or DeviceCheck for guest AI and new-account fraud, a disposable-email blocklist, report and block on shared trips, limits on text, member count and upload size, malware scan for uploads, an incident runbook and a breach template. Keep the Host allow-list and CSRF header for the web build, with Cloudflare's WAF in front. Pen test before launch.

## 9. Migration checklist by roadmap phase

Phases match the roadmap in the [README](README.md) and [07-local-to-app-store.md](07-local-to-app-store.md). Each step is shippable and backward compatible. Follow `.claude/rules/database-migrations.md` for every model or migration change.

**M0: validate.** No account work. Nothing is rewritten before demand is shown.

**Phase 0: foundations (no user-visible change)**
- [ ] Create the Supabase project (sign-in only), Apple Services ID and key, Google client ids, custom SMTP with SPF, DKIM and DMARC.
- [ ] Alembic migration (run as a pre-deploy step) for `users`, `auth_identities`, `devices`, `trip_members`, `entitlements`, `credit_ledger`, `credit_grants`, plus `owner_user_id`, `linked_user_id` on `people`, and owner, `public_id`, `deleted_at` on `trips`. Backfill to a bootstrap user, then set NOT NULL.
- [ ] Add `user_id` to `runs`, `routines`, `agent_notes`, `lodging_votes`, and creator fields on lodging and activities, so metering can charge the acting user.
- [ ] Add `CurrentUser` and `require_trip` in `api/deps.py`; move per-user `AppSetting` values to per-user settings.

**Phase 1: hosted web beta (accounts, sharing, entitlements, ledger)**
- [ ] Rewrite the services and every router to take a scope; by-id child routes join through the trip.
- [ ] Postgres RLS on trip-owned tables; cross-tenant test suite in CI; `e2e_seed.py` for two users.
- [ ] Replace the passcode: token exchange endpoint (verify the Supabase JWT), `GET /me`, `POST /me/claim`, logout, devices endpoints. Remove loopback trust and passcode fingerprint from production; keep Host allow-list and CSRF checks behind `APP_MODE`.
- [ ] Update `schemas/auth.py`, run `npm run gen:api`, commit `frontend/src/lib/api/schema.d.ts`.
- [ ] Replace `auth-gate.tsx` and `login-screen.tsx` with sign-in and guest flow; rewrite settings copy per `.claude/rules/frontend.md`; namespace cache and localStorage by user.
- [ ] Remove `APP_PASSCODE` and `ALLOWED_HOSTS` from production config; add new variables to `.env.example`.
- [ ] Shared-store rate limiting in place of `LoginLimiter`.
- [ ] Invites, share-link page, "Which traveler are you?", attribution, `updated_since` polling, 409 conflict UI.
- [ ] Entitlement service: `can_invite`, `trip_capabilities`, credit checks against the ledger.
- [ ] Migrate the two existing users' data.
- [ ] Gate: 4-week retention measured.

**Phase 2: iOS TestFlight**
- [ ] Sign in with Apple, with relay-email handling and token revoke.
- [ ] RevenueCat and App Store Server Notifications V2 webhook (signed JWS verification); Trip Pass and Group Trip Pass bound to a trip.
- [ ] Households: invite flow, pooled grant, payer rules, leave and cooldown limits (section 3.6). Polls, expenses and settlements for Group Trip Pass (section 3.7).
- [ ] In-app account deletion and the purge worker with checklist; data export job.
- [ ] Universal links (`apple-app-site-association`), push tokens, App Attest for guests.
- [ ] AI consent screen and per-trip AI toggle; `PrivacyInfo.xcprivacy`.

**Phase 3: public launch**
- [ ] Privacy policy, terms, nutrition label, age gate, provider DPAs.
- [ ] Retention jobs (trash purge, invite purge, IP hashing, log expiry).
- [ ] Concierge and room-block consent (section 3.9), if the host agency agreement is signed.
- [ ] Review against guidelines 4.8, 5.1.1(v), 5.1.2(i) and 3.1.1, and a reviewer demo account with a pre-filled trip in App Store Connect notes.
- [ ] Pen test, load test at 10x expected, backup and restore drill including per-user deletion.
- [ ] Incident and breach runbook, abuse inbox, audited admin tooling (view user, revoke sessions, refund credits, suspend).

**Phase 4: growth.** Passkeys, comments, Play Data safety, Android sign-in, Pro entitlement live.
- [ ] Advisor orgs, seats and clients tables, the advisor role marker on `trip_members`, advisor cases in the cross-tenant suite, advisor data processing addendum, and web-only sign-up with Stripe billing.
- [ ] Concierge consent screen, payload snapshot and retention job (if not already live in phase 3).
- [ ] Stripe-collected group payments with the expense and settlement rules in section 3.7.

## 10. Where this plan changed the initial idea

1. **Trip membership first; households only for Family.** The first idea framed sharing as a Plus feature between partners. Membership on the trip with a per-trip role covers that and fits the growth loop, where a friend joins one trip. Households were left out until the Family plan needed a pool of credits and a six-person limit; they now exist for that purpose only and grant no access to anyone's trips. Advisor organizations follow the same rule.
2. **Owner's tier sets capabilities; the acting user pays for AI.** Making credits follow the owner lets one collaborator drain them and hides metering from invitees. Final rule: capabilities come from the owner's tier or the trip's Trip Pass, and credits are charged to whoever starts the action. No owner-funded pool at launch.
3. **Free accounts join free, but Free owners cannot invite editors.** An earlier draft allowed one free collaborator as a taste. The final decision is cleaner: sharing is a Plus or Trip Pass feature, and joining is always free. Invitee accounts start on the standard Free tier (12 credits a month, no bonus), and device attestation limits credit farming.
4. **Guest mode is local-first.** A server user per install inflates MAU and invites abuse. The server row appears on first use of a server feature.
5. **The passcode and loopback trust are replaced, not extended.** Only the CSRF header and rate-limit ideas are kept.
6. **Supabase Auth for sign-in only.** Self-hosting and Firebase were weighed. Supabase is cheap, portable through our own `users` table, and keeps product data in our Render Postgres. Clerk and Auth0 cost too much per MAU.
7. **Polling first, realtime later.** Two to five collaborators do not need WebSockets at launch.
8. **The local Claude Code CLI agent is not a user feature.** It runs on the owner's own subscription. It becomes metered API calls in our worker ([03-ai-features-and-costs.md](03-ai-features-and-costs.md)). The Sonnet rule for subagents is a build-time rule for this repo, not a runtime one.
9. **Personal data stays in our database.** The `people` table is kept (not renamed to travelers) and extended, so existing trips and votes keep working.
