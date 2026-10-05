"""0020_share_link_book_slide: trip_share_links.show_book_slide for the share-link settings (WF-025.2). Expand only.

04 section 5.6 ShareLinkCreate carries show_book_slide ("Book the plan" last slide, default true); the table had no place for it.

Revision ID: 0020_share_link_book_slide
Revises: 0019_invite_preview
"""

from alembic import op

revision = "0020_share_link_book_slide"
down_revision = "0019_invite_preview"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.get_bind().exec_driver_sql("ALTER TABLE trip_share_links ADD COLUMN show_book_slide boolean NOT NULL DEFAULT true")


def downgrade() -> None:
    op.get_bind().exec_driver_sql("ALTER TABLE trip_share_links DROP COLUMN show_book_slide")
