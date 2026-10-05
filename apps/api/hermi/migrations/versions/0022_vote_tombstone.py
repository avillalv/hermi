"""0022_vote_tombstone: hearts survive a removed traveler as "Former traveler", and one stay is Booked per trip.

`lodging_votes` and `saved_place_votes` pointed at `trip_people` with ON DELETE CASCADE, so removing a traveler erased their
hearts (DECISIONS 2026-10-04, WF-024.1). Now the person link is cleared instead (`ON DELETE SET NULL (person_id)`): the vote
stays, attributed to its `user_id`, and the client shows "Former traveler" for a vote whose person is gone.
`person_id` is nullable (a member with no linked traveler can still heart), so the key moves to a surrogate `id`.
A member hearts a stay once (unique on `user_id`), and a traveler once (unique on `person_id`).
Also `uq_lodging_options_one_booked`: at most one booked stay per trip (04 section 5.9, WF-034).

Revision ID: 0022_vote_tombstone
Revises: 0021_fx_convert_exact_rounding
"""

from alembic import op

revision = "0022_vote_tombstone"
down_revision = "0021_fx_convert_exact_rounding"
branch_labels = None
depends_on = None


def _up(table: str, parent: str) -> str:
    return f"""
ALTER TABLE {table} DROP CONSTRAINT {table}_trip_id_person_id_fkey;
ALTER TABLE {table} DROP CONSTRAINT {table}_pkey;
ALTER TABLE {table} ADD COLUMN id uuid NOT NULL DEFAULT uuidv7();
ALTER TABLE {table} ADD CONSTRAINT {table}_pkey PRIMARY KEY (id);
ALTER TABLE {table} ALTER COLUMN person_id DROP NOT NULL;
ALTER TABLE {table} ADD CONSTRAINT uq_{table}_person UNIQUE ({parent}, person_id);
ALTER TABLE {table} ADD CONSTRAINT {table}_trip_id_person_id_fkey
  FOREIGN KEY (trip_id, person_id) REFERENCES trip_people (trip_id, person_id) ON DELETE SET NULL (person_id);
CREATE UNIQUE INDEX uq_{table}_user ON {table} ({parent}, user_id) WHERE user_id IS NOT NULL;
"""


def _down(table: str, parent: str) -> str:
    return f"""
DROP INDEX uq_{table}_user;
ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY;  -- the owner sees every row for this one delete
DELETE FROM {table} WHERE person_id IS NULL;
ALTER TABLE {table} FORCE ROW LEVEL SECURITY;
ALTER TABLE {table} DROP CONSTRAINT {table}_trip_id_person_id_fkey;
ALTER TABLE {table} DROP CONSTRAINT uq_{table}_person;
ALTER TABLE {table} DROP CONSTRAINT {table}_pkey;
ALTER TABLE {table} DROP COLUMN id;
ALTER TABLE {table} ALTER COLUMN person_id SET NOT NULL;
ALTER TABLE {table} ADD CONSTRAINT {table}_pkey PRIMARY KEY ({parent}, person_id);
ALTER TABLE {table} ADD CONSTRAINT {table}_trip_id_person_id_fkey
  FOREIGN KEY (trip_id, person_id) REFERENCES trip_people (trip_id, person_id) ON DELETE CASCADE;
"""


def upgrade() -> None:
    op.execute(_up("lodging_votes", "lodging_id"))
    op.execute(_up("saved_place_votes", "saved_place_id"))
    op.execute("CREATE UNIQUE INDEX uq_lodging_options_one_booked ON lodging_options (trip_id) WHERE status = 'booked'")


def downgrade() -> None:
    op.execute("DROP INDEX uq_lodging_options_one_booked")
    op.execute(_down("saved_place_votes", "saved_place_id"))
    op.execute(_down("lodging_votes", "lodging_id"))
