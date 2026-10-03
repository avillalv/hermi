# Pack 03: Comments on items

Part of [Phase 2: growth](README.md). Written 2026-09-30. The full specs only reserve this feature:
[01 F-COL-2](../reference-full-spec/01-product-spec.md) says viewers may "vote, react, comment", [01 section 7](../reference-full-spec/01-product-spec.md)
lists "comments with mentions" as out of the launch scope ("phase 4 of collaboration"),
[03 section 6.4](../reference-full-spec/03-database-schema.md) notes "Viewers may vote and comment", and
[03 section 11.5](../reference-full-spec/03-database-schema.md) seeds the flag `poll_comments` (off). There is no table,
endpoint or screen in the full specs. [Phase 1 03 section 14](../phase-1-launch/03-database-schema.md) reserves
the working names for this pack (a `comments` table, the flag `poll_comments`, and notification kinds for
mentions and replies) and Phase 1 seeds none of them, so the design below is new and follows the same
conventions.

| Item | Value |
|---|---|
| Build order | 3 (month 8, right after group tools) |
| Flag | `comments` (created by this pack; it replaces the working name `poll_comments`, which Phase 1 does not seed, so there is no alias to keep) |
| Needs | Phase 1 collaboration (roles, activity log, hearts), notifications and digests, offline queue, admin moderation queue; soft: pack 02 (comments on polls and expenses) |
| Tickets | P2-025 to P2-031 |
| Tier and products | All tiers, all roles that can view a trip. No new products, no credits |

## 1. Goal and why now

**Goal.** Let trip members discuss a specific thing where it lives: a day plan item, a saved stay, a
poll, a flight route. No chat app, no real-time co-editing, no presence. Short threaded comments with
unread markers and quiet notifications.

**Why now.**

- Phase 1 collaboration stops at hearts, an activity log and poll votes. Groups fall back to a
  separate chat thread to say "is the museum open Monday?", which is where the decision gets lost.
- Competitive reasons. Wanderlog and Trippy have group tools for collaborating inside the plan
  (reported, verify), and TripIt users' complaint about group coordination is the
  same gap ([business plan](../context/business-plan/01-business-plan.md): group coordination "is still clumsy in TripIt
  and Google Docs"). Comments are table stakes for the friend-group persona and the cheapest feature in
  Phase 2 (about a week).
- It is free for everyone, including viewers and Free invitees, which makes the invite loop more
  valuable without touching any paywall.

## 2. User stories and acceptance criteria

| ID | Story | Acceptance |
|---|---|---|
| CMT-1 | As a member, I comment on an itinerary item, a stay, a poll, a flight route or an expense. | A thread button with a count sits on the card. Comments are plain text up to 2,000 characters, shown newest last, with author name, time and "edited" when changed. Links are shown as text and never fetched (no link previews). |
| CMT-2 | As a member, I reply to a comment. | One level of replies (a reply to a reply attaches to the same parent). Replying notifies the parent's author. |
| CMT-3 | As a viewer, I can comment. | Role matrix (F-COL-2): "Vote, react, comment": owner yes, editor yes, viewer yes. Read-only share links and presentation mode never show comments. |
| CMT-4 | As an author, I edit or delete my comment. | Editing is allowed any time and marks "edited". Deleting removes the body; if replies exist the row shows "Comment removed" so the thread stays readable. The trip owner can delete any comment. |
| CMT-5 | As a member, I see what is new. | Unread dots on the trip's section tabs and cards, from `comment_reads`; opening a thread marks it read. The Activity feed lists "Sam commented on Belem Tower" (verb `commented`). |
| CMT-6 | As a member, I can mention someone. | Typing `@` offers trip members only (display names); a mention notifies that person. Mentions never resolve to people outside the trip. Mentions ship as the last ticket and can be cut without harming the rest. |
| CMT-7 | As a member, I control notifications. | Change-digest push for shared trips stays at most one per hour per trip and now includes comments. Replies to me and mentions can be pushed (default on); other comments are digest only (default off for push). Per trip mute and quiet hours apply. No promotional push. |
| CMT-8 | As a person, I can report abuse. | "Report" on a comment creates a `content_reports` row (target type `comment`); three reports from different members hide it pending review; reporter identity is never revealed to the reported user. |
| CMT-9 | As a person leaving, my history remains sensible. | Leaving keeps comments attributed as "Former member"; account deletion shows "Deleted user"; both keep the text (same rule as other contributions in F-SET-3). |
| CMT-10 | As an owner, I can turn comments off for my trip. | Trip setting "Allow comments" (default on) hides the thread buttons and rejects new comments with `422 validation_failed` and code `comments_disabled`; existing comments stay visible to members. |

Rules: comments are never sent to AI (no feature reads them; 06 section 12.1 already excludes
"names, notes, other members"); never included in share links, presentation mode, PDF or calendar
feeds; included in the per-trip export (JSON and PDF appendix) and in the account data export.
Rate limit: 30 comments per hour per user per trip and 10 per minute overall (defaults, configurable).

## 3. Database additions

Migration `0019_comments`. New table definitions, following the conventions in
[03 section 2](../reference-full-spec/03-database-schema.md) (UUIDv7 ids, `timestamptz`, versioned rows,
`add_updated_at_trigger`, RLS in the same migration).

```sql
CREATE TYPE comment_entity AS ENUM ('itinerary_item', 'lodging_option', 'poll', 'flight_route', 'expense');

CREATE TABLE comments (
  id               uuid PRIMARY KEY DEFAULT uuidv7(),
  trip_id          uuid NOT NULL REFERENCES trips (id) ON DELETE CASCADE,
  entity_type      comment_entity NOT NULL,
  entity_id        uuid NOT NULL,                                  -- validated by the API against the trip; cleaned up by triggers below
  parent_id        uuid,                                           -- one level of replies
  author_user_id   uuid REFERENCES users (id) ON DELETE SET NULL, -- null after account deletion (shown as "Deleted user")
  body             text NOT NULL CHECK (char_length(body) BETWEEN 0 AND 2000),
  edited_at        timestamptz,
  deleted_at       timestamptz,                                    -- soft delete when replies exist; body is blanked
  hidden_at        timestamptz,                                    -- set by moderation or three reports
  version          integer NOT NULL DEFAULT 1,
  created_at       timestamptz NOT NULL DEFAULT now(),
  updated_at       timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_comments_id_trip UNIQUE (id, trip_id),
  FOREIGN KEY (parent_id, trip_id) REFERENCES comments (id, trip_id) ON DELETE CASCADE,
  CONSTRAINT ck_comments_deleted_body CHECK ((deleted_at IS NULL AND char_length(body) >= 1) OR (deleted_at IS NOT NULL AND body = ''))
);
CREATE INDEX ix_comments_entity ON comments (trip_id, entity_type, entity_id, created_at);
CREATE INDEX ix_comments_trip_recent ON comments (trip_id, created_at DESC);
CREATE INDEX ix_comments_author ON comments (author_user_id) WHERE author_user_id IS NOT NULL;
SELECT add_version_trigger('comments');
SELECT add_updated_at_trigger('comments');

-- A reply must attach to a top-level comment on the same entity.
CREATE FUNCTION comments_validate() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE v_parent comments%ROWTYPE;
BEGIN
  IF NEW.parent_id IS NOT NULL THEN
    SELECT * INTO v_parent FROM comments WHERE id = NEW.parent_id AND trip_id = NEW.trip_id;
    IF NOT FOUND OR v_parent.parent_id IS NOT NULL
       OR v_parent.entity_type <> NEW.entity_type OR v_parent.entity_id <> NEW.entity_id THEN
      RAISE EXCEPTION 'invalid_parent' USING ERRCODE = 'WF422';
    END IF;
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER trg_comments_validate BEFORE INSERT ON comments
  FOR EACH ROW EXECUTE FUNCTION comments_validate();

-- Entities are polymorphic, so each parent table removes its comments when a row goes.
CREATE FUNCTION comments_cascade() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  DELETE FROM comments WHERE entity_type = TG_ARGV[0]::comment_entity AND entity_id = OLD.id;
  RETURN OLD;
END $$;
CREATE TRIGGER trg_itinerary_items_comments AFTER DELETE ON itinerary_items FOR EACH ROW EXECUTE FUNCTION comments_cascade('itinerary_item');
CREATE TRIGGER trg_lodging_options_comments  AFTER DELETE ON lodging_options  FOR EACH ROW EXECUTE FUNCTION comments_cascade('lodging_option');
CREATE TRIGGER trg_polls_comments            AFTER DELETE ON polls            FOR EACH ROW EXECUTE FUNCTION comments_cascade('poll');
CREATE TRIGGER trg_flight_routes_comments    AFTER DELETE ON flight_routes    FOR EACH ROW EXECUTE FUNCTION comments_cascade('flight_route');
CREATE TRIGGER trg_expenses_comments         AFTER DELETE ON expenses         FOR EACH ROW EXECUTE FUNCTION comments_cascade('expense');

CREATE TABLE comment_reads (                                       -- unread markers, one row per person and thread
  user_id        uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
  trip_id        uuid NOT NULL REFERENCES trips (id) ON DELETE CASCADE,
  entity_type    comment_entity NOT NULL,
  entity_id      uuid NOT NULL,
  last_read_at   timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, trip_id, entity_type, entity_id)
);

CREATE TABLE comment_mentions (                                    -- mentions ticket (P2-031)
  comment_id          uuid NOT NULL,
  trip_id             uuid NOT NULL,
  mentioned_user_id   uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
  notified_at         timestamptz,
  PRIMARY KEY (comment_id, mentioned_user_id),
  FOREIGN KEY (comment_id, trip_id) REFERENCES comments (id, trip_id) ON DELETE CASCADE
);

ALTER TABLE trips ADD COLUMN IF NOT EXISTS comments_enabled boolean NOT NULL DEFAULT true;   -- owner setting "Allow comments"

-- Moderation: extend content_reports (03 section 5.21) to comments.
ALTER TABLE content_reports ADD COLUMN IF NOT EXISTS comment_id uuid REFERENCES comments (id) ON DELETE SET NULL;
ALTER TABLE content_reports DROP CONSTRAINT ck_content_reports_target;
ALTER TABLE content_reports ADD CONSTRAINT ck_content_reports_target CHECK (target_type IN ('shared_trip', 'agent_note', 'ai_answer', 'research_cache', 'comment'));
ALTER TABLE content_reports DROP CONSTRAINT ck_content_reports_target_ref;
ALTER TABLE content_reports ADD CONSTRAINT ck_content_reports_target_ref CHECK (
  (target_type = 'shared_trip' AND share_link_id IS NOT NULL) OR
  (target_type = 'agent_note' AND note_id IS NOT NULL) OR
  (target_type = 'ai_answer' AND run_id IS NOT NULL) OR
  (target_type = 'research_cache' AND cache_key IS NOT NULL) OR
  (target_type = 'comment' AND comment_id IS NOT NULL));

INSERT INTO feature_flags (key, description, enabled, rollout_pct, rules, variants) VALUES
('comments', 'Comments on itinerary items, stays, polls, routes and expenses', false, 100, '{}', '{}')
ON CONFLICT (key) DO NOTHING;
INSERT INTO kill_switches (key, description) VALUES
('comments.write', 'Stop new comments and edits; reads keep working')
ON CONFLICT (key) DO NOTHING;
```

Notification kinds (Phase 1 has a `notifications` outbox with a named check on `kind`; swap
`ck_notifications_kind` for the current list plus these): `comment_reply`, `comment_mention`. Comment digests
reuse the existing change-digest path and need no kind. Dedupe keys: `comment_reply:<comment_id>`,
`comment_mention:<comment_id>:<user_id>`.

Row-level security (viewers may comment; a comment row must be the caller's own; the author edits, the
owner can delete or hide):

```sql
ALTER TABLE comments ENABLE ROW LEVEL SECURITY;
CREATE POLICY comments_select ON comments FOR SELECT
  USING (trip_id IN (SELECT visible_trip_ids()) AND (hidden_at IS NULL OR author_user_id = (SELECT app_user_id()) OR is_trip_owner(trip_id)));
CREATE POLICY comments_insert ON comments FOR INSERT
  WITH CHECK (author_user_id = (SELECT app_user_id()) AND trip_id IN (SELECT visible_trip_ids()));
CREATE POLICY comments_update ON comments FOR UPDATE
  USING (author_user_id = (SELECT app_user_id()) OR is_trip_owner(trip_id))
  WITH CHECK (trip_id IN (SELECT visible_trip_ids()));
CREATE POLICY comments_delete ON comments FOR DELETE
  USING (author_user_id = (SELECT app_user_id()) OR is_trip_owner(trip_id));

ALTER TABLE comment_reads ENABLE ROW LEVEL SECURITY;
CREATE POLICY comment_reads_all ON comment_reads FOR ALL
  USING (user_id = (SELECT app_user_id())) WITH CHECK (user_id = (SELECT app_user_id()) AND trip_id IN (SELECT visible_trip_ids()));
ALTER TABLE comment_mentions ENABLE ROW LEVEL SECURITY;
CREATE POLICY comment_mentions_select ON comment_mentions FOR SELECT USING (trip_id IN (SELECT visible_trip_ids()));
```

Retention: comments live with the trip (purged with it after the 30 day trash window); hidden comments
keep their text for moderation for 90 days, then the body is blanked. The account deletion job sets
`author_user_id` to null on the user's comments (they show as "Deleted user").

## 4. API additions

| Endpoint | Auth | Gate and cost | Request and response | Errors and side effects |
|---|---|---|---|---|
| `GET /trips/{trip_id}/comments` | viewer | none | `?entity_type=&entity_id=&after=&limit=` to `Page<Comment>` | Threads for one entity, oldest first; or the trip's recent comments without filters. |
| `GET /trips/{trip_id}/comment-counts` | viewer | none | none to `{ entity_type, entity_id, count, unread }[]` | One call fills every badge on a screen. `ETag`. |
| `POST /trips/{trip_id}/comments` | viewer | flag `comments`, trip `comments_enabled`, 30 an hour per user per trip | `CommentIn` with `Idempotency-Key` to 201 `Comment` | Validates the entity belongs to the trip (404 otherwise). Writes an `activity_log` row (verb `commented`). Enqueues notification jobs. |
| `PATCH /comments/{comment_id}` | author | versioned | `{ body: string, version: number }` to `Comment` | Sets `edited_at`. Others get 404 or `insufficient_role`. |
| `DELETE /comments/{comment_id}` | author or owner | none | 204 | Soft delete when replies exist, hard delete otherwise. |
| `POST /comments/{comment_id}/report` | viewer | one per person per comment | `{ reason: "spam" \| "harmful" \| "privacy", detail?: string }` to 204 | Creates `content_reports` (`target_type = 'comment'`); three distinct reporters set `hidden_at`. |
| `PUT /trips/{trip_id}/comment-reads` | viewer | none | `{ entity_type, entity_id }` to 204 | Upserts `comment_reads`. |
| `PATCH /trips/{trip_id}` | owner | versioned | `{ comments_enabled?: boolean }` | Existing route gets the new field. |

```ts
type CommentIn = {
  entity_type: "itinerary_item" | "lodging_option" | "poll" | "flight_route" | "expense"
  entity_id: Uuid; body: string                         // 1 to 2000 characters
  parent_id?: Uuid; mention_user_ids?: Uuid[]            // mentions ticket; members of the trip only
}
type Comment = {
  id: Uuid; trip_id: Uuid; entity_type: CommentIn["entity_type"]; entity_id: Uuid
  parent_id: Uuid | null; body: string | null            // null when removed or hidden for the viewer
  author: Attribution | null                              // null renders "Deleted user"
  created_at: string; edited_at: string | null; removed: boolean; mine: boolean; version: number
}
```

Errors: `404 not_found` for non members (never 403), `422 validation_failed` with code
`comments_disabled`, `body_too_long` or `invalid_parent`, `429 rate_limited`, `503 feature_disabled`
when the flag is off. Polling: comment lists refresh on foreground and every 15 to 30 seconds with
conditional requests, the same as other shared data (F-COL-5). Notifications: job `send_comment_push`
(notify lane, key `(user_id, comment_id, channel)`) for replies and mentions; the change digest builds
from `activity_log`.

## 5. UI screens and paywall triggers

- **Thread sheet** (bottom sheet on phones, side panel on web; 4.19): header with the item title, list of
  comments with avatar, name, relative time, "edited"; composer with "Add a comment"; Send disabled when
  empty; reply and report in a row menu; offline comments are queued with "Waiting to sync".
- **Comment affordance** on Day card items, Lodging cards (beside the heart), Poll cards, Flight route
  rows and Expense rows: a count chip that reads "3 comments" for screen readers, an unread dot when
  `unread > 0`.
- **Trip settings**: "Allow comments" switch.
- **Notifications settings**: rows "Replies and mentions" (push and email) and "New comments" (digest).
- **Activity feed**: "Sam commented on Belem Tower. View" with a link to the thread.

States. Loading: three skeleton rows. Empty: "No comments yet", "Ask a question or leave a note for the
group.", [Add a comment]. Error: "We could not send your comment. It is saved. Try again." Offline:
queued. No permission: nobody is blocked by role (viewers comment); when the owner turned comments off
the chips are hidden and the sheet says "The owner turned comments off for this trip." Limit: "You are
commenting quickly. Try again in a few minutes." No paywall anywhere in this pack.

Copy follows the microcopy rules (sentence case, plain verbs, no em dashes, no exclamation marks).
Accessibility: the thread is a list with one item per comment; the composer has a visible label; the
unread state is text for screen readers ("2 new comments").

## 6. Monetization and App Store products

None. Comments are free on every tier and for every role; there are no credits and no products. This
is deliberate: it makes invitees more active, which feeds the invite loop and the `invite` paywall.
No new `plans.limits` keys.

## 7. Admin additions

- **Content moderation (08 section 6.12).** New queue "Reported comments": the comment text (visible
  to content and owner roles only, audited like other reveals), trip id, author id masked, report
  reasons and count. Actions: dismiss, hide (`hidden_at`), warn the author (macro), suspend sharing
  and invites for repeat offenders (`users.sharing_suspended_at`, existing), escalate. Reports are
  answered within 24 hours (alert at 12), as for other reports.
- **Trip lookup.** Support can see comment counts per trip, never the text without the moderation path.
- **Kill switch.** `comments.write` (new, in `kill_switches`) stops new comments and edits while reads
  keep working; pairs with the `comments` flag.
- **Alert rules.** More than 5 reports in an hour (notify), comments per minute above 3 times the
  trailing 7 day p95 (notify, abuse watch).

## 8. AI additions

None, by design. Comments contain names and opinions and are excluded from every prompt, from the
weekly digest and from `research` context. A test asserts no code path that builds a prompt queries the
`comments` table.

## 9. Analytics events

No PII and no comment text; enums and buckets only.

| Event | Properties | When fired |
|---|---|---|
| `comment_added` | `entity_type` (`comment_entity`), `is_reply` (bool), `role` (`owner`, `editor`, `viewer`), `length_bucket` | Comment created (server side) |
| `comment_thread_opened` | `entity_type`, `unread_bucket` | Thread sheet opened |
| `comment_edited` | none | Edit saved |
| `comment_deleted` | `by` (`author`, `owner`) | Delete |
| `comment_reported` | `reason` | Report sent |
| `comments_setting_changed` | `enabled` (bool) | Owner switches comments |
| `comment_mention_sent` | none | Mention notification queued (after P2-031) |

Funnel: invite loop extension (`invite_accepted` to `comment_added` within 7 days) as an engagement
signal for invitees.

## 10. Tests

- RLS and roles: a viewer can comment, edit only their own, cannot delete others; the owner can delete
  and hide any; non members get 404; tenant isolation suite covers `comments`, `comment_reads`,
  `comment_mentions`.
- Entity integrity: comment on an entity from another trip is rejected; deleting the entity removes its
  comments (each cascade trigger); reply depth limited to one.
- Soft delete: parent with replies shows "Comment removed", replies stay.
- Rate limit and idempotency: a retried POST with the same key creates one comment.
- Notifications: reply notifies the parent author once; mentions only notify trip members; digest
  includes comment summaries without text; quiet hours and per-trip mute respected; no more than one
  digest push per hour per trip.
- Privacy: comments absent from share link pages, presentation data, PDF and calendar feed; present in
  the export; absent from every AI prompt builder; account deletion nulls authorship.
- Moderation: three distinct reports hide the comment; reporter identity never returned.
- Offline: queued comment sends once, ordering preserved.
- Accessibility: axe on the thread sheet, keyboard send, focus return to the chip.
- E2E: two accounts, one viewer, comment and reply on a stay and on a poll, unread dot clears.

## 11. Tickets

#### P2-025 Comments schema, RLS and flag [M, needs Phase 1 collaboration schema]
- Description: migration `0019_comments` with tables, triggers, policies, content_reports extension,
  `trips.comments_enabled`, flag and kill switch rows.
- Accept: empty to head and previous to head pass; cascade triggers remove comments with their entity.
- Tests: migration, RLS and cascade tests.

#### P2-026 Comments API [M, needs P2-025]
- Description: list, counts, create, edit, delete, report, reads; rate limits; activity log rows.
- Accept: viewers can comment; non members get 404; soft delete rules.
- Touches: `apps/api/hermi/modules/collaboration/comments.py`.

#### P2-027 Thread UI and badges [L, needs P2-026]
- Description: thread sheet, composer, count chips and unread dots on Day card, Lodging card, Poll card,
  route rows and expense rows, trip setting, states and copy.
- Accept: axe clean; keyboard and VoiceOver verified; no link previews.
- Touches: `apps/web/src/components/comments/`.

#### P2-028 Notifications and digest integration [M, needs P2-026, Phase 1 notifications]
- Description: replies push, digest inclusion, settings rows, quiet hours, per-trip mute, Activity
  feed items.
- Accept: at most one digest push per hour per trip; no promotional content.
- Tests: notification handler tests.

#### P2-029 Moderation and admin [S, needs P2-026, Phase 1 moderation queue]
- Description: reported comments queue, hide and warn actions, three-report auto hide, kill switch,
  alert rules.
- Accept: actions audited; reporter identity never revealed.

#### P2-030 Offline, export, deletion and privacy checks [M, needs P2-027]
- Description: offline comment queue, per-trip and account export inclusion, deletion job nulls
  authorship, share and PDF exclusions, test that no prompt builder reads comments.
- Accept: tests in section 10 pass; privacy policy text updated (comments are visible to trip members).

#### P2-031 Mentions (optional, cut first) [M, needs P2-027]
- Description: `@` picker limited to trip members, `comment_mentions`, mention push and email, settings.
- Accept: mentions never resolve outside the trip; notification is sent once per mention.

## 12. Risks

| Risk | Mitigation |
|---|---|
| Scope creep into chat (typing indicators, reactions, real-time) | Out of scope list in section 1; polling only; one level of replies |
| Harassment or spam in group trips | Reports, three-report auto hide, owner delete and disable, rate limits, sharing suspension for repeat offenders |
| Notification fatigue | Digest first, push only for replies and mentions, quiet hours, per-trip mute |
| Private information leaks through shares or exports | Excluded from share pages, presentation, PDF and feeds; tests |
| Polymorphic entity rows go stale | Cascade triggers and a nightly orphan check in the retention sweep |
