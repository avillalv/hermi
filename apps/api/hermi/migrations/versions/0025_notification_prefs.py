# ruff: noqa: E501  (long SQL strings)
"""0025_notification_prefs: notification preferences, per-trip mute, and four more notification kinds (03 section 5.18, WF-047).

The notify lane reads a person's switches, quiet hours and trip mutes, so they live in their own tables and not in users.prefs
(03: prefs is not a place a job must read). Absent row means the defaults (everything on, quiet hours 22:00 to 08:00 local).
The app role reads and writes its own rows; the worker role reads them. New kinds: activity_digest, trial_ending,
account_deleted (the deletion confirmation) and lifecycle (marketing mail, which needs the marketing_email consent).

Revision ID: 0025_notification_prefs
Revises: 0024_trip_pass_spend
"""

from alembic import op

revision = "0025_notification_prefs"
down_revision = "0024_trip_pass_spend"
branch_labels = None
depends_on = None

OLD_KINDS = """'price_drop', 'booked_fare_drop', 'trip_invite', 'invite_accepted', 'run_finished',
    'import_finished', 'pre_trip_reminder', 'referral_reward', 'import_reward',
    'calendar_changes', 'calendar_poll_stopped', 'verify_finished'"""
NEW_KINDS = OLD_KINDS + ", 'activity_digest', 'trial_ending', 'account_deleted', 'lifecycle'"


def _kind_check(kinds: str) -> str:
    return f"""
ALTER TABLE notifications DROP CONSTRAINT ck_notifications_kind;
ALTER TABLE notifications ADD CONSTRAINT ck_notifications_kind CHECK (kind IN ({kinds}));
"""


UP = (
    _kind_check(NEW_KINDS)
    + r"""
CREATE TABLE notification_preferences (
  user_id        uuid PRIMARY KEY REFERENCES users (id) ON DELETE CASCADE,
  email_enabled  boolean NOT NULL DEFAULT true,                 -- false after a one-click "unsubscribe from all"; account mail (deletion confirmation) still goes
  email_off      text[] NOT NULL DEFAULT '{}',                  -- notifications.kind values the person switched off for email
  push_off       text[] NOT NULL DEFAULT '{}',                  -- the same for push (delivery lands in WF-086)
  quiet_enabled  boolean NOT NULL DEFAULT true,
  quiet_start    time NOT NULL DEFAULT '22:00',                 -- local time in users.timezone
  quiet_end      time NOT NULL DEFAULT '08:00',
  updated_at     timestamptz NOT NULL DEFAULT now()
);
SELECT add_updated_at_trigger('notification_preferences');

CREATE TABLE trip_notification_mutes (                            -- a muted trip sends this person no digest, alert or reminder
  trip_id     uuid NOT NULL REFERENCES trips (id) ON DELETE CASCADE,
  user_id     uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
  created_at  timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (trip_id, user_id)
);
CREATE INDEX ix_trip_notification_mutes_user ON trip_notification_mutes (user_id);

ALTER TABLE notification_preferences ENABLE ROW LEVEL SECURITY;  ALTER TABLE notification_preferences FORCE ROW LEVEL SECURITY;
CREATE POLICY notification_preferences_select ON notification_preferences FOR SELECT USING (user_id = (SELECT app_user_id()));
CREATE POLICY notification_preferences_insert ON notification_preferences FOR INSERT WITH CHECK (user_id = (SELECT app_user_id()));
CREATE POLICY notification_preferences_update ON notification_preferences FOR UPDATE USING (user_id = (SELECT app_user_id())) WITH CHECK (user_id = (SELECT app_user_id()));
ALTER TABLE trip_notification_mutes ENABLE ROW LEVEL SECURITY;  ALTER TABLE trip_notification_mutes FORCE ROW LEVEL SECURITY;
CREATE POLICY trip_notification_mutes_select ON trip_notification_mutes FOR SELECT USING (user_id = (SELECT app_user_id()));
CREATE POLICY trip_notification_mutes_insert ON trip_notification_mutes FOR INSERT
  WITH CHECK (user_id = (SELECT app_user_id()) AND trip_id IN (SELECT visible_trip_ids()));
CREATE POLICY trip_notification_mutes_delete ON trip_notification_mutes FOR DELETE USING (user_id = (SELECT app_user_id()));

REVOKE ALL ON notification_preferences, trip_notification_mutes FROM hermi_app, hermi_worker;
GRANT SELECT, INSERT, UPDATE ON notification_preferences TO hermi_app;
GRANT SELECT, INSERT, DELETE ON trip_notification_mutes TO hermi_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON notification_preferences, trip_notification_mutes TO hermi_worker;
"""
)

DOWN = (
    r"""
DROP TABLE trip_notification_mutes;
DROP TABLE notification_preferences;
-- rls-exempt: notifications (0014 owns its policies; this downgrade only lifts and restores FORCE for one delete)
-- FORCE row-level security hides every row from the owner (the policies are the app's), so lift it for the one delete.
ALTER TABLE notifications NO FORCE ROW LEVEL SECURITY;
DELETE FROM notifications WHERE kind IN ('activity_digest', 'trial_ending', 'account_deleted', 'lifecycle');
ALTER TABLE notifications FORCE ROW LEVEL SECURITY;
"""
    + _kind_check(OLD_KINDS)
)


def upgrade() -> None:
    op.execute(UP)


def downgrade() -> None:
    op.execute(DOWN)
