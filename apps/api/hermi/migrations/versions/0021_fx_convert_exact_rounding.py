"""0021_fx_convert_exact_rounding: fx_convert_minor() rounds exact halves away from zero. Expand only (same signature).

power(10, int) is float8 in PostgreSQL, so the final round() ran on a float and rounded halves to even. power(10::numeric, ...)
keeps the whole expression numeric, where round() goes away from zero, as the web app's convertMinor does. One division
at the end (not divide, multiply, divide) so a non-terminating quotient is not truncated before rounding.

Revision ID: 0021_fx_convert_exact_rounding
Revises: 0020_share_link_book_slide
"""

from alembic import op

revision = "0021_fx_convert_exact_rounding"
down_revision = "0020_share_link_book_slide"
branch_labels = None
depends_on = None

NEW_RETURN = "round((p_minor::numeric * v_to * power(10::numeric, currency_exponent(p_to))) / (v_from * power(10::numeric, currency_exponent(p_from))))::bigint;"
OLD_RETURN = "round(p_minor::numeric / power(10, currency_exponent(p_from)) / v_from * v_to * power(10, currency_exponent(p_to)))::bigint;"
_BODY = f"""
CREATE OR REPLACE FUNCTION fx_convert_minor(p_minor bigint, p_from text, p_to text) RETURNS bigint
LANGUAGE plpgsql STABLE AS $$
DECLARE v_from numeric; v_to numeric;
BEGIN
  IF p_from = p_to THEN RETURN p_minor; END IF;
  v_from := CASE WHEN p_from = 'EUR' THEN 1 ELSE (SELECT per_eur FROM fx_rates WHERE currency = p_from) END;
  v_to   := CASE WHEN p_to   = 'EUR' THEN 1 ELSE (SELECT per_eur FROM fx_rates WHERE currency = p_to) END;
  IF v_from IS NULL OR v_to IS NULL THEN RETURN NULL; END IF;
  RETURN {NEW_RETURN}
END $$;
"""


def upgrade() -> None:
    op.get_bind().exec_driver_sql(_BODY)


def downgrade() -> None:
    op.get_bind().exec_driver_sql(_BODY.replace(NEW_RETURN, OLD_RETURN))
