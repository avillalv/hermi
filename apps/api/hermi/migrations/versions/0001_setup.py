"""0001_setup: extensions, domains and helper functions (03 section 3).

Creates no role. Roles come from infra/db/bootstrap.sql (`npm run db:init`); this migration only
checks that they exist.

Revision ID: 0001_setup
Revises:
"""

from alembic import op

from hermi.db import assert_roles_exist

revision = "0001_setup"
down_revision = None
branch_labels = None
depends_on = None

UP = """
CREATE EXTENSION IF NOT EXISTS citext;

-- Domains keep codes consistent across tables.
CREATE DOMAIN currency_code AS char(3) CHECK (VALUE ~ '^[A-Z]{3}$');
CREATE DOMAIN iata_code     AS char(3) CHECK (VALUE ~ '^[A-Z]{3}$');
CREATE DOMAIN country_code2 AS char(2) CHECK (VALUE ~ '^[A-Z]{2}$');
CREATE DOMAIN hex_color     AS char(7) CHECK (VALUE ~ '^#[0-9A-Fa-f]{6}$');

-- Keeps updated_at current. Attach with add_updated_at_trigger('table') in each migration.
CREATE FUNCTION set_updated_at() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN NEW.updated_at := now(); RETURN NEW; END $$;

CREATE FUNCTION add_updated_at_trigger(p_table regclass) RETURNS void LANGUAGE plpgsql AS $$
BEGIN
  EXECUTE format(
    'CREATE TRIGGER trg_updated_at BEFORE UPDATE ON %s FOR EACH ROW EXECUTE FUNCTION set_updated_at()',
    p_table);
END $$;

-- Optimistic concurrency counter.
CREATE FUNCTION bump_version() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN NEW.version := OLD.version + 1; RETURN NEW; END $$;

CREATE FUNCTION add_version_trigger(p_table regclass) RETURNS void LANGUAGE plpgsql AS $$
BEGIN
  EXECUTE format(
    'CREATE TRIGGER trg_version BEFORE UPDATE ON %s FOR EACH ROW EXECUTE FUNCTION bump_version()',
    p_table);
END $$;

-- Minor-unit exponent for ISO 4217 (2 unless listed).
CREATE FUNCTION currency_exponent(c text) RETURNS smallint LANGUAGE sql IMMUTABLE AS $$
  SELECT CASE
    WHEN c IN ('BIF','CLP','DJF','GNF','ISK','JPY','KMF','KRW','PYG','RWF','UGX','UYI','VND','VUV','XAF','XOF','XPF') THEN 0
    WHEN c IN ('BHD','IQD','JOD','KWD','LYD','OMR','TND') THEN 3
    ELSE 2 END
$$;

-- Session user for row-level security (03 section 6). NULL when unset, so policies fail closed.
CREATE FUNCTION app_user_id() RETURNS uuid LANGUAGE sql STABLE AS $$
  SELECT nullif(current_setting('app.user_id', true), '')::uuid
$$;

"""

DOWN = """
DROP FUNCTION app_user_id();
DROP FUNCTION currency_exponent(text);
DROP FUNCTION add_version_trigger(regclass);
DROP FUNCTION bump_version();
DROP FUNCTION add_updated_at_trigger(regclass);
DROP FUNCTION set_updated_at();
DROP DOMAIN hex_color;
DROP DOMAIN country_code2;
DROP DOMAIN iata_code;
DROP DOMAIN currency_code;
DROP EXTENSION citext;
"""


def upgrade() -> None:
    assert_roles_exist(op.get_bind())
    op.execute(UP)


def downgrade() -> None:
    op.execute(DOWN)
