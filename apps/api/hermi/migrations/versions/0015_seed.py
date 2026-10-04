"""0015_seed: Phase 1 seed data (03 sections 10 and 11), idempotent.

The SQL lives in hermi.seed so `hermi seed` runs the same statements. The seed tables (plans, store_products,
credit_action_prices, affiliate_programs, feature_flags, kill_switches) have no user_id or trip_id, so 0014 did not
force RLS on them and the owner can insert. Downgrade is a no-op (see downgrade()).

Revision ID: 0015_seed
Revises: 0014_rls
"""

from alembic import op

from hermi.seed import SEED_SQL

revision = "0015_seed"
down_revision = "0014_rls"
branch_labels = None
depends_on = None

def upgrade() -> None:
    # exec_driver_sql: op.execute would read ":true" inside the JSON as a bind parameter.
    op.get_bind().exec_driver_sql(SEED_SQL)


def downgrade() -> None:
    # shortcut: no-op. Seed rows may already be referenced (entitlements.tier_code, ledger rows) and an admin may have edited them, so a
    # delete could fail or destroy edits; the 0003 and 0008 downgrades drop the tables with their rows. Upgrade is idempotent, so
    # a down-then-up round trip is safe. Revisit only if a revision must remove a seeded key.
    pass
