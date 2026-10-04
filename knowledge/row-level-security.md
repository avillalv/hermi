# Row-level security

Second lock behind the app checks in `hermi.deps.require_trip` (03 section 6.5, WF-015). Policies live in migration `0014_rls` and later revisions. The live list is the source of truth: `SELECT tablename, policyname, cmd FROM pg_policies WHERE schemaname = 'public' ORDER BY 1, 2;`

## How it is wired

- `hermi.db.request_transaction` runs `set_config('app.user_id', <user id>, true)` first in every request transaction. It is transaction-local, so it dies on commit or rollback and cannot leak across a pooled connection. `app_user_id()` reads it (null when unset).
- Policies compare against `app_user_id()` and the definer helpers `visible_trip_ids()`, `can_edit_trip(uuid)`, `is_trip_owner(uuid)`. No variable means no rows.
- `hermi.db.open_app_engine` refuses to start when the connected login is a superuser, has `BYPASSRLS`, or owns or is a member of the owner of any public table (`assert_app_login_is_safe`), or when a table lacks ENABLE or FORCE and has a `trip_id` or `user_id` column, a policy, RLS on, or is a named deny-all table (`assert_rls_forced`; exempt: `RLS_EXEMPT_TABLES`, closed by grants instead).
- Roles: `hermi_api_login` (member of `hermi_app`, subject to RLS), `hermi_worker_login` and `hermi_admin_login` (`BYPASSRLS`, reached only through `system_session` and the admin app). Admin writes go through audited `admin_*` functions and column grants, not per-table admin policies.

## Policies by table (live `pg_policies`, 46 tables)

- `activity_log`: `activity_log_insert` (insert), `activity_log_select` (select)
- `ai_usage`: `ai_usage_select` (select)
- `auth_identities`: `auth_identities_select` (select)
- `checklist_items`: `checklist_items_delete` (delete), `checklist_items_insert` (insert), `checklist_items_select` (select), `checklist_items_update` (update)
- `chosen_flights`: `chosen_flights_delete` (delete), `chosen_flights_insert` (insert), `chosen_flights_select` (select), `chosen_flights_update` (update)
- `consents`: `consents_insert` (insert), `consents_select` (select)
- `content_reports`: `content_reports_select` (select)
- `credit_debts`: `credit_debts_select` (select)
- `credit_grants`: `credit_grants_select` (select)
- `credit_ledger`: `credit_ledger_select` (select)
- `data_exports`: `data_exports_insert` (insert), `data_exports_select` (select)
- `devices`: `devices_delete` (delete), `devices_insert` (insert), `devices_select` (select), `devices_update` (update)
- `entitlements`: `entitlements_select` (select)
- `flight_routes`: `flight_routes_delete` (delete), `flight_routes_insert` (insert), `flight_routes_select` (select), `flight_routes_update` (update)
- `idempotency_keys`: `idempotency_keys_delete` (delete), `idempotency_keys_insert` (insert), `idempotency_keys_select` (select), `idempotency_keys_update` (update)
- `itinerary_days`: `itinerary_days_delete` (delete), `itinerary_days_insert` (insert), `itinerary_days_select` (select), `itinerary_days_update` (update)
- `itinerary_items`: `itinerary_items_delete` (delete), `itinerary_items_insert` (insert), `itinerary_items_select` (select), `itinerary_items_update` (update)
- `link_clicks`: `link_clicks_insert` (insert), `link_clicks_select` (select), `link_clicks_update` (update)
- `lodging_options`: `lodging_options_delete` (delete), `lodging_options_insert` (insert), `lodging_options_select` (select), `lodging_options_update` (update)
- `lodging_votes`: `lodging_votes_delete` (delete), `lodging_votes_insert` (insert), `lodging_votes_select` (select)
- `notes`: `notes_delete` (delete), `notes_insert` (insert), `notes_select` (select), `notes_update` (update)
- `notifications`: `notifications_select` (select), `notifications_update` (update)
- `people`: `people_delete` (delete), `people_insert` (insert), `people_select` (select), `people_update` (update)
- `plan_verification_items`: `plan_verification_items_delete` (delete), `plan_verification_items_insert` (insert), `plan_verification_items_select` (select), `plan_verification_items_update` (update)
- `plan_verifications`: `plan_verifications_delete` (delete), `plan_verifications_insert` (insert), `plan_verifications_select` (select), `plan_verifications_update` (update)
- `price_alerts`: `price_alerts_all` (all)
- `referral_codes`: `referral_codes_select` (select)
- `referral_rewards`: `referral_rewards_select` (select)
- `run_events`: `run_events_select` (select)
- `runs`: `runs_insert` (insert), `runs_select` (select), `runs_update` (update)
- `sample_trips`: `sample_trips_published` (select)
- `saved_place_votes`: `saved_place_votes_delete` (delete), `saved_place_votes_insert` (insert), `saved_place_votes_select` (select)
- `saved_places`: `saved_places_delete` (delete), `saved_places_insert` (insert), `saved_places_select` (select), `saved_places_update` (update)
- `store_transactions`: `store_transactions_select` (select)
- `subscriptions`: `subscriptions_select` (select)
- `support_tickets`: `support_tickets_insert` (insert), `support_tickets_select` (select), `support_tickets_update` (update)
- `trip_destinations`: `trip_destinations_delete` (delete), `trip_destinations_insert` (insert), `trip_destinations_select` (select), `trip_destinations_update` (update)
- `trip_fare_links`: `trip_fare_links_delete` (delete), `trip_fare_links_insert` (insert), `trip_fare_links_select` (select), `trip_fare_links_update` (update)
- `trip_imports`: `trip_imports_insert` (insert), `trip_imports_select` (select)
- `trip_invites`: `trip_invites_delete` (delete), `trip_invites_insert` (insert), `trip_invites_select` (select), `trip_invites_update` (update)
- `trip_members`: `trip_members_delete` (delete), `trip_members_insert` (insert), `trip_members_select` (select), `trip_members_update` (update)
- `trip_passes`: `trip_passes_select` (select)
- `trip_people`: `trip_people_delete` (delete), `trip_people_insert` (insert), `trip_people_select` (select), `trip_people_update` (update)
- `trip_share_links`: `trip_share_links_delete` (delete), `trip_share_links_insert` (insert), `trip_share_links_select` (select), `trip_share_links_update` (update)
- `trips`: `trips_delete` (delete), `trips_insert` (insert), `trips_select` (select), `trips_update` (update)
- `users`: `users_self` (select), `users_update` (update)

- RLS on and forced, no policy (deny all to the app, definer functions only): `identity_hashes`, `device_attestations`, `guest_allowances`.
- No RLS, closed by grants: `admin_users`, `deletion_requests`, `affiliate_conversions`, `provider_calls`.

## Tests

`apps/api/tests/test_rls_runtime.py` (no variable, forced-bug query, pooled-connection leak, FORCE refusal incl. `trips`, migrate-login refusal), plus `test_migrations_rls.py` and `test_migrations_rls_isolation.py` (every policy and table, as `hermi_api_login`).
