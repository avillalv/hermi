"""0011_checklist_notes: checklist items and notes (03 section 5.15).

The SQL is the DDL of 5.15, verbatim.
Grants, row-level security and policies land in 0014_rls. No grant is given here.

Revision ID: 0011_checklist_notes
Revises: 0010_itinerary_lodging
"""

from alembic import op

revision = "0011_checklist_notes"
# 03 section 10 lists the parents of this revision; the chain is linear, so the parent is 0010_itinerary_lodging (one head).
down_revision = "0010_itinerary_lodging"
branch_labels = None
depends_on = None

UP = r"""
CREATE TABLE checklist_items (
  id             uuid PRIMARY KEY DEFAULT uuidv7(),
  trip_id        uuid NOT NULL REFERENCES trips (id) ON DELETE CASCADE,
  kind           text NOT NULL,
  title          text,                                          -- custom items and AI packing lines; null for rules rows
  status         text NOT NULL DEFAULT 'todo',
  due_on         date,
  done_at        timestamptz,
  done_by        uuid REFERENCES users (id) ON DELETE SET NULL,
  dismissed_at   timestamptz,
  assignee_user_id uuid REFERENCES users (id) ON DELETE SET NULL,
  program_id     uuid REFERENCES affiliate_programs (id) ON DELETE SET NULL,   -- partner offered on this item, if any
  source         text NOT NULL DEFAULT 'rules',                 -- rules: one row per kind from the checklist rules; user: a custom item; ai: one line of an accepted packing list (06 5.2)
  meta           jsonb NOT NULL DEFAULT '{}'::jsonb,            -- ai packing lines keep {"group": "clothing", "qty": 2} here
  version        integer NOT NULL DEFAULT 1,
  created_at     timestamptz NOT NULL DEFAULT now(),
  updated_at     timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_checklist_items_kind CHECK (kind IN (
    'flights_booked', 'stay_booked', 'tickets', 'transfer_or_car', 'esim', 'insurance',
    'documents', 'luggage_storage', 'money', 'home', 'packing', 'custom')),
  CONSTRAINT ck_checklist_items_status CHECK (status IN ('todo', 'done', 'skipped', 'not_needed')),
  CONSTRAINT ck_checklist_items_source CHECK (source IN ('rules', 'user', 'ai')),
  CONSTRAINT ck_checklist_items_source_kind CHECK ((source = 'user') = (kind = 'custom') AND (source <> 'ai' OR kind = 'packing')),
  CONSTRAINT ck_checklist_items_title CHECK (source = 'rules' OR title IS NOT NULL)
);
-- One row per kind from the rules; custom items and AI packing lines are many per trip.
CREATE UNIQUE INDEX uq_checklist_items_trip_kind ON checklist_items (trip_id, kind) WHERE source = 'rules';
CREATE INDEX ix_checklist_items_trip ON checklist_items (trip_id, status);
SELECT add_version_trigger('checklist_items');
SELECT add_updated_at_trigger('checklist_items');

CREATE TYPE note_kind AS ENUM ('user', 'agent');

CREATE TABLE notes (
  id              uuid PRIMARY KEY DEFAULT uuidv7(),
  trip_id         uuid NOT NULL REFERENCES trips (id) ON DELETE CASCADE,
  kind            note_kind NOT NULL DEFAULT 'user',
  author_user_id  uuid REFERENCES users (id) ON DELETE SET NULL,
  title           text NOT NULL DEFAULT '' CHECK (char_length(title) <= 160),
  topic           text NOT NULL DEFAULT '' CHECK (char_length(topic) <= 80),   -- agent notes: the add_note topic (06 2.5)
  body            text NOT NULL DEFAULT '',
  urls            text[] NOT NULL DEFAULT '{}',                  -- sources; required for agent notes
  day             date,                                          -- the note is attached to this day (04 NoteIn.day)
  itinerary_item_id uuid,                                        -- or to this item (04 NoteIn.item_id)
  is_private      boolean NOT NULL DEFAULT false,                -- visible only to the author; never sent to AI
  pinned          boolean NOT NULL DEFAULT false,
  run_id          uuid REFERENCES runs (id) ON DELETE SET NULL,
  checked_at      timestamptz NOT NULL DEFAULT now(),            -- when the sources were last seen on their pages (evidence label date); a recheck moves it. Older than 14 days shows "May be out of date"
  version         integer NOT NULL DEFAULT 1,
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY (itinerary_item_id, trip_id) REFERENCES itinerary_items (id, trip_id) ON DELETE SET NULL (itinerary_item_id),
  CONSTRAINT ck_notes_agent_sources CHECK (kind <> 'agent' OR cardinality(urls) >= 1),
  CONSTRAINT ck_notes_agent_not_private CHECK (kind <> 'agent' OR NOT is_private)
);
CREATE INDEX ix_notes_trip ON notes (trip_id, pinned DESC, created_at DESC);
CREATE INDEX ix_notes_run ON notes (run_id) WHERE run_id IS NOT NULL;
CREATE INDEX ix_notes_item ON notes (itinerary_item_id) WHERE itinerary_item_id IS NOT NULL;
CREATE INDEX ix_notes_day ON notes (trip_id, day) WHERE day IS NOT NULL;
SELECT add_version_trigger('notes');
SELECT add_updated_at_trigger('notes');
"""

DOWN = r"""
DROP TABLE notes;
DROP TYPE note_kind;
DROP TABLE checklist_items;
"""


def upgrade() -> None:
    op.execute(UP)


def downgrade() -> None:
    op.execute(DOWN)
