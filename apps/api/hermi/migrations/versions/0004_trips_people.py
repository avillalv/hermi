"""0004_trips_people: trips and collaboration, people (03 sections 5.4 and 5.5).

Includes the owner-member trigger and the definer functions redeem_trip_invite and transfer_trip_owner.
Grants, row-level security and policies land in 0014_rls (the EXECUTE grants on the two functions are in 5.4 and are kept here).

Revision ID: 0004_trips_people
Revises: 0003_reference_catalog
"""

from alembic import op

revision = "0004_trips_people"
# 03 section 10 lists 0002 as the parent; the chain is linear, so the parent is 0003 (one head).
down_revision = "0003_reference_catalog"
branch_labels = None
depends_on = None

UP = """
CREATE TYPE trip_status AS ENUM ('planning', 'booked', 'done', 'archived');
CREATE TYPE trip_role   AS ENUM ('owner', 'editor', 'viewer');

CREATE TABLE trips (
  id                uuid PRIMARY KEY DEFAULT uuidv7(),
  owner_user_id     uuid NOT NULL REFERENCES users (id) ON DELETE RESTRICT,
  name              text NOT NULL CHECK (char_length(name) BETWEEN 1 AND 120),
  start_date        date,                                 -- optional: a trip can be an idea before it has dates
  end_date          date,
  status            trip_status NOT NULL DEFAULT 'planning',
  home_currency     currency_code NOT NULL,
  notes             text NOT NULL DEFAULT '',
  cover_image_url   text,
  ai_enabled        boolean NOT NULL DEFAULT true,        -- owner can turn AI off for the trip
  show_book_slide   boolean NOT NULL DEFAULT true,        -- presentation "Book the plan" slide
  editors_can_invite boolean NOT NULL DEFAULT false,      -- owner setting: editors may invite viewers (04 5.6)
  calendar_token_hash bytea,                              -- sha256 of the calendar feed token (04 5.15); the token is shown once and rotated by POST /trips/{id}/calendar-token
  version           integer NOT NULL DEFAULT 1,
  archived_at       timestamptz,
  deleted_at        timestamptz,                          -- trash; hard purge after 30 days
  created_at        timestamptz NOT NULL DEFAULT now(),
  updated_at        timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_trips_valid_dates CHECK ((start_date IS NULL) = (end_date IS NULL) AND (end_date IS NULL OR end_date >= start_date))
);
CREATE INDEX ix_trips_owner_status ON trips (owner_user_id, status) WHERE deleted_at IS NULL;
CREATE INDEX ix_trips_start_date ON trips (start_date) WHERE deleted_at IS NULL AND start_date IS NOT NULL;
CREATE INDEX ix_trips_trash ON trips (deleted_at) WHERE deleted_at IS NOT NULL;
CREATE UNIQUE INDEX uq_trips_calendar_token ON trips (calendar_token_hash) WHERE calendar_token_hash IS NOT NULL;
SELECT add_version_trigger('trips');
SELECT add_updated_at_trigger('trips');

CREATE TABLE trip_members (
  trip_id     uuid NOT NULL REFERENCES trips (id) ON DELETE CASCADE,
  user_id     uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
  role        trip_role NOT NULL,
  invited_by  uuid REFERENCES users (id) ON DELETE SET NULL,
  joined_at   timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (trip_id, user_id)
);
CREATE UNIQUE INDEX uq_trip_members_one_owner ON trip_members (trip_id) WHERE role = 'owner';
CREATE INDEX ix_trip_members_user_trip ON trip_members (user_id, trip_id);      -- the "my trips" query and RLS helper

-- The owner is always a member.
CREATE FUNCTION trips_add_owner_member() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
BEGIN
  INSERT INTO trip_members (trip_id, user_id, role) VALUES (NEW.id, NEW.owner_user_id, 'owner');
  RETURN NEW;
END $$;
CREATE TRIGGER trg_trips_owner_member AFTER INSERT ON trips
  FOR EACH ROW EXECUTE FUNCTION trips_add_owner_member();

CREATE TABLE trip_invites (
  id            uuid PRIMARY KEY DEFAULT uuidv7(),
  trip_id       uuid NOT NULL REFERENCES trips (id) ON DELETE CASCADE,
  invited_by    uuid REFERENCES users (id) ON DELETE SET NULL,
  token_hash    bytea NOT NULL,                              -- sha256 of a random 128-bit token; the token is never stored
  role          trip_role NOT NULL DEFAULT 'editor',
  email         citext,                                      -- null for a shareable link
  max_uses      smallint NOT NULL DEFAULT 1 CHECK (max_uses BETWEEN 1 AND 50),
  use_count     smallint NOT NULL DEFAULT 0,
  expires_at    timestamptz NOT NULL DEFAULT now() + interval '7 days',
  revoked_at    timestamptz,
  accepted_by   uuid REFERENCES users (id) ON DELETE SET NULL,   -- last redeemer
  accepted_at   timestamptz,
  created_at    timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_trip_invites_role CHECK (role <> 'owner'),
  CONSTRAINT ck_trip_invites_uses CHECK (use_count <= max_uses),
  CONSTRAINT uq_trip_invites_token UNIQUE (token_hash)
);
CREATE INDEX ix_trip_invites_trip ON trip_invites (trip_id) WHERE revoked_at IS NULL;
CREATE INDEX ix_trip_invites_expiry ON trip_invites (expires_at);

CREATE TABLE trip_share_links (
  id                uuid PRIMARY KEY DEFAULT uuidv7(),
  trip_id           uuid NOT NULL REFERENCES trips (id) ON DELETE CASCADE,
  created_by        uuid REFERENCES users (id) ON DELETE SET NULL,
  token_hash        bytea NOT NULL,
  redact_address    boolean NOT NULL DEFAULT true,           -- hide exact lodging address
  redact_prices     boolean NOT NULL DEFAULT true,
  redact_notes      boolean NOT NULL DEFAULT true,
  redact_people     boolean NOT NULL DEFAULT true,           -- show travelers as "Traveler 1" instead of names
  indexable         boolean NOT NULL DEFAULT false,          -- public pages carry noindex unless the owner sets this
  expires_at        timestamptz NOT NULL DEFAULT now() + interval '90 days',   -- every share link expires (04: 1 to 365 days)
  revoked_at        timestamptz,
  view_count        integer NOT NULL DEFAULT 0,
  last_viewed_at    timestamptz,
  created_at        timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_trip_share_links_token UNIQUE (token_hash)
);
CREATE INDEX ix_trip_share_links_trip ON trip_share_links (trip_id) WHERE revoked_at IS NULL;

CREATE TABLE trip_destinations (
  id                  uuid PRIMARY KEY DEFAULT uuidv7(),
  trip_id             uuid NOT NULL REFERENCES trips (id) ON DELETE CASCADE,
  position            smallint NOT NULL,
  name                text NOT NULL CHECK (char_length(name) BETWEEN 1 AND 120),
  region              text,
  country             text,
  country_code        country_code2,
  kind                text,                                  -- city, region, country, poi
  lat                 double precision NOT NULL CHECK (lat BETWEEN -90 AND 90),
  lon                 double precision NOT NULL CHECK (lon BETWEEN -180 AND 180),
  timezone            text,
  bbox                double precision[],                    -- [west, south, east, north]
  geoapify_place_id   text,
  wikidata_id         text,
  summary             text,                                  -- Wikipedia extract (CC BY-SA)
  wiki_url            text,
  image_url           text,
  image_attribution   text,
  image_license       text,
  info_status         text NOT NULL DEFAULT 'pending',
  info_updated_at     timestamptz,
  created_at          timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_trip_destinations_info_status CHECK (info_status IN ('pending', 'ready', 'not_found', 'failed', 'skipped')),
  CONSTRAINT uq_trip_destinations_position UNIQUE (trip_id, position) DEFERRABLE INITIALLY DEFERRED
);

CREATE TABLE activity_log (                                  -- per-trip change feed
  id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  trip_id         uuid NOT NULL REFERENCES trips (id) ON DELETE CASCADE,
  actor_user_id   uuid REFERENCES users (id) ON DELETE SET NULL,
  verb            text NOT NULL,                              -- added, updated, removed, voted, joined, ...
  entity_type     text NOT NULL,
  entity_id       uuid,
  summary         text NOT NULL DEFAULT '',
  created_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_activity_log_trip ON activity_log (trip_id, id DESC);
-- Redeem an invite for the caller. Returns the trip id. Raises invite_expired (P0001) for an unknown, revoked, expired or used-up invite, or one for a trashed trip
-- (one error for all four, so a caller cannot tell them apart) and already_member (23505) when the caller is already on the trip.
CREATE FUNCTION redeem_trip_invite(p_token_hash bytea) RETURNS uuid
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE
  v_me  uuid := app_user_id();
  v_inv trip_invites%ROWTYPE;
BEGIN
  IF v_me IS NULL THEN RAISE EXCEPTION 'not_authenticated' USING ERRCODE = '42501'; END IF;
  SELECT * INTO v_inv FROM trip_invites WHERE token_hash = p_token_hash FOR UPDATE;
  IF NOT FOUND OR v_inv.revoked_at IS NOT NULL OR v_inv.expires_at <= now() OR v_inv.use_count >= v_inv.max_uses
     OR EXISTS (SELECT 1 FROM trips WHERE id = v_inv.trip_id AND deleted_at IS NOT NULL) THEN      -- a trashed trip cannot be joined
    RAISE EXCEPTION 'invite_expired' USING ERRCODE = 'P0001';
  END IF;
  IF EXISTS (SELECT 1 FROM trip_members WHERE trip_id = v_inv.trip_id AND user_id = v_me) THEN
    RAISE EXCEPTION 'already_member' USING ERRCODE = '23505', DETAIL = v_inv.trip_id::text;
  END IF;
  INSERT INTO trip_members (trip_id, user_id, role, invited_by) VALUES (v_inv.trip_id, v_me, v_inv.role, v_inv.invited_by);
  UPDATE trip_invites SET use_count = use_count + 1, accepted_by = v_me, accepted_at = now() WHERE id = v_inv.id;
  RETURN v_inv.trip_id;
END $$;
ALTER FUNCTION redeem_trip_invite(bytea) OWNER TO hermi_definer;
REVOKE EXECUTE ON FUNCTION redeem_trip_invite(bytea) FROM PUBLIC;
GRANT  EXECUTE ON FUNCTION redeem_trip_invite(bytea) TO hermi_app;

-- Hand a trip to another member. Only the current owner may call it. The old owner becomes an editor. Returns the new owner id.
CREATE FUNCTION transfer_trip_owner(p_trip uuid, p_new_owner uuid) RETURNS uuid
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE
  v_me uuid := app_user_id();
BEGIN
  IF v_me IS NULL OR NOT EXISTS (SELECT 1 FROM trips WHERE id = p_trip AND owner_user_id = v_me AND deleted_at IS NULL) THEN
    RAISE EXCEPTION 'insufficient_role' USING ERRCODE = '42501';
  END IF;
  IF p_new_owner = v_me OR NOT EXISTS (SELECT 1 FROM trip_members WHERE trip_id = p_trip AND user_id = p_new_owner) THEN
    RAISE EXCEPTION 'target_not_member' USING ERRCODE = '22023';
  END IF;
  -- uq_trip_members_one_owner is not deferrable: demote first, then promote.
  UPDATE trip_members SET role = 'editor' WHERE trip_id = p_trip AND user_id = v_me;
  UPDATE trip_members SET role = 'owner'  WHERE trip_id = p_trip AND user_id = p_new_owner;
  UPDATE trips SET owner_user_id = p_new_owner WHERE id = p_trip;
  RETURN p_new_owner;
END $$;
ALTER FUNCTION transfer_trip_owner(uuid, uuid) OWNER TO hermi_definer;
REVOKE EXECUTE ON FUNCTION transfer_trip_owner(uuid, uuid) FROM PUBLIC;
GRANT  EXECUTE ON FUNCTION transfer_trip_owner(uuid, uuid) TO hermi_app;
CREATE TABLE people (
  id               uuid PRIMARY KEY DEFAULT uuidv7(),
  owner_user_id    uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
  linked_user_id   uuid REFERENCES users (id) ON DELETE SET NULL,
  name             text NOT NULL CHECK (char_length(name) BETWEEN 1 AND 60),
  color            hex_color NOT NULL DEFAULT '#FF5E7E',
  home_airports    iata_code[] NOT NULL DEFAULT '{}',
  is_self          boolean NOT NULL DEFAULT false,          -- the auto-created "Me" person
  created_at       timestamptz NOT NULL DEFAULT now(),
  updated_at       timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX uq_people_owner_linked ON people (owner_user_id, linked_user_id) WHERE linked_user_id IS NOT NULL;
CREATE UNIQUE INDEX uq_people_one_self ON people (owner_user_id) WHERE is_self;
CREATE INDEX ix_people_linked_user ON people (linked_user_id) WHERE linked_user_id IS NOT NULL;
SELECT add_updated_at_trigger('people');

CREATE TABLE trip_people (
  trip_id     uuid NOT NULL REFERENCES trips (id) ON DELETE CASCADE,
  person_id   uuid NOT NULL REFERENCES people (id) ON DELETE CASCADE,
  added_by    uuid REFERENCES users (id) ON DELETE SET NULL,
  created_at  timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (trip_id, person_id)
);
CREATE INDEX ix_trip_people_person ON trip_people (person_id);
"""

DOWN = """
DROP TABLE trip_people;
DROP TABLE people;
DROP FUNCTION transfer_trip_owner(uuid, uuid);
DROP FUNCTION redeem_trip_invite(bytea);
DROP TABLE activity_log;
DROP TABLE trip_destinations;
DROP TABLE trip_share_links;
DROP TABLE trip_invites;
DROP TRIGGER trg_trips_owner_member ON trips;
DROP FUNCTION trips_add_owner_member();
DROP TABLE trip_members;
DROP TABLE trips;
DROP TYPE trip_role;
DROP TYPE trip_status;
"""


def upgrade() -> None:
    op.execute(UP)


def downgrade() -> None:
    op.execute(DOWN)
