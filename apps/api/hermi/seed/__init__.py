# ruff: noqa: E501  (SQL copied from 03 section 11, one row per line)
"""Phase 1 seed data (03 section 11): plans, store products, credit prices, affiliate programs, flags, kill switches.

One SQL string shared by migration 0015_seed and `hermi seed`. Every statement is INSERT ... ON CONFLICT DO NOTHING, so a re-run changes nothing.
Run it with exec_driver_sql, not text(): the JSON in it has ":true" and ":false" that text() would read as bind parameters.
The illustrative affiliate_link_templates row of 11.4 is not seeded (inactive example; templates wait for each network's confirmed link format).
Airports, FX rates, sample_trips and admin_users are never seeded (11.6).
"""

SEED_SQL = r"""
INSERT INTO plans (code, kind, name, rank, monthly_credits, credits_granted, credits_valid_days, duration_days, feature_flag_key, is_active, sort_order, limits) VALUES
('free', 'tier', 'Free', 0, 12, 0, NULL, NULL, NULL, true, 0,
 '{"active_trips":2,"active_trips_bonus":0,"routes_per_trip":1,"live_routes":0,"live_window_days":0,"price_alerts":1,"live_alerts":false,
   "collaborators":1,"travelers_per_trip":2,"can_invite":true,"saved_lodging_per_trip":8,"lodging_compare":2,
   "places_searches_per_day":30,"hide_presentation_footer":false,"taster_agent_runs":1,"verify_items_per_run":5,
   "destinations_per_trip":12,"airports_per_side":2,"imports":true,"calendar_feed":true,"calendar_polling":true,"monthly_credits":12,
   "monthly_ceiling_micros":250000,"daily_ceiling_micros":50000}'),
('plus', 'tier', 'Plus', 20, 60, 0, NULL, NULL, NULL, true, 10,
 '{"active_trips":25,"active_trips_bonus":0,"routes_per_trip":5,"live_routes":3,"live_window_days":120,"price_alerts":3,"live_alerts":true,
   "collaborators":6,"travelers_per_trip":8,"can_invite":true,"saved_lodging_per_trip":100,"lodging_compare":4,
   "places_searches_per_day":100,"hide_presentation_footer":true,"taster_agent_runs":0,"verify_items_per_run":12,
   "destinations_per_trip":12,"airports_per_side":4,"imports":true,"calendar_feed":true,"calendar_polling":true,"monthly_credits":60,
   "monthly_ceiling_micros":2250000,"daily_ceiling_micros":400000}'),
('trip_pass', 'pass', 'Trip Pass', 25, 0, 40, 90, 90, NULL, true, 40,
 '{"active_trips_bonus":1,"routes_per_trip":3,"live_routes":2,"live_window_days":120,"live_checks_max":60,"price_alerts":2,"live_alerts":true,
   "collaborators":6,"travelers_per_trip":8,"can_invite":true,"saved_lodging_per_trip":30,"lodging_compare":4,
   "places_searches_per_day":100,"hide_presentation_footer":true,"verify_items_per_run":12,
   "destinations_per_trip":12,"airports_per_side":4,"imports":true,"calendar_feed":true,"calendar_polling":true,"monthly_credits":0,
   "monthly_ceiling_micros":1800000,"daily_ceiling_micros":400000}'),
('credits_50',  'credit_pack', '50 credits',  0, 0,  50, 365, NULL, NULL, true, 60, '{}'),
('credits_150', 'credit_pack', '150 credits', 0, 0, 150, 365, NULL, NULL, true, 61, '{}'),
('credits_400', 'credit_pack', '400 credits', 0, 0, 400, 365, NULL, NULL, true, 62, '{}')
ON CONFLICT (code) DO NOTHING;

INSERT INTO store_products (product_id, store, plan_code, period, price_minor, currency, trial_days, is_active) VALUES
('hermi_plus_monthly',   'apple',  'plus',            'month',  599, 'USD', 0, true),
('hermi_plus_annual',    'apple',  'plus',            'year',  3999, 'USD', 7, true),     -- 7-day trial on annual only
('hermi_trip_pass',      'apple',  'trip_pass',       'once',   999, 'USD', 0, true),     -- non-renewing subscription, 90 days
('hermi_credits_50',     'apple',  'credits_50',      'once',   299, 'USD', 0, true),     -- consumable
('hermi_credits_150',    'apple',  'credits_150',     'once',   699, 'USD', 0, true),
('hermi_credits_400',    'apple',  'credits_400',     'once',  1499, 'USD', 0, true)
ON CONFLICT (product_id) DO NOTHING;

INSERT INTO credit_action_prices (action, credits, credits_cached, hard_stop_micros, max_turns, max_searches, max_fetches, model) VALUES
('explain',     1, NULL,   10000, 1,    0,  0,  'claude-haiku-4-5'),
('live_search', 1, NULL,   20000, NULL, NULL, NULL, NULL),
('draft_day',   1, NULL,   30000, 1,    0,  0,  'claude-sonnet-5-5'),
('draft_trip',  4, NULL,  100000, 1,    0,  0,  'claude-sonnet-5-5'),
('research',    8, 1,     160000, NULL, 5,  8,  'claude-sonnet-5-5'),
('agent_run',  40, 8,     800000, 20,   10, 10, 'claude-sonnet-5-5'),
-- verify_plan is priced per checked item: the credits and the caps below are for ONE item (1 credit, one search, one page). A run reserves
-- credits x items (at most verify_items_per_run, 11.1) and its hard stop is hard_stop_micros x items. Reading the pasted plan is a separate
-- 'explain' action (run kind verify_extract); a one-tap evidence recheck is also 'explain' (run kind recheck).
('verify_plan', 1, NULL,    20000, 1,    1,  1,  'claude-haiku-4-5')
ON CONFLICT (action) DO NOTHING;

INSERT INTO affiliate_programs (code, network, name, category, status, hosts, cookie_days, subid_param, campaign_param, api_credentials_ref, extra_disclosure_text) VALUES
-- Launch: Travelpayouts (one signup, one statistics API)
('travelpayouts_aviasales',   'travelpayouts', 'Aviasales',              'flights',      'active',  '{aviasales.com,tp.media}',     30, 'sub_id', NULL, 'TRAVELPAYOUTS_TOKEN', NULL),
('travelpayouts_kiwi',        'travelpayouts', 'Kiwi.com',               'flights',      'active',  '{kiwi.com,tp.media}',          30, 'sub_id', NULL, 'TRAVELPAYOUTS_TOKEN', NULL),
('travelpayouts_booking',     'travelpayouts', 'Booking.com',            'lodging',      'active',  '{booking.com,tp.media}',        1, 'sub_id', NULL, 'TRAVELPAYOUTS_TOKEN', 'As a Booking.com Affiliate, we earn from qualifying transactions.'),
('travelpayouts_agoda',       'travelpayouts', 'Agoda',                  'lodging',      'active',  '{agoda.com,tp.media}',          1, 'sub_id', NULL, 'TRAVELPAYOUTS_TOKEN', NULL),
('travelpayouts_trip',        'travelpayouts', 'Trip.com',               'lodging',      'active',  '{trip.com,tp.media}',          30, 'sub_id', NULL, 'TRAVELPAYOUTS_TOKEN', NULL),
('travelpayouts_tripcom_flights','travelpayouts','Trip.com flights',      'flights',      'active',  '{trip.com,tp.media}',          30, 'sub_id', NULL, 'TRAVELPAYOUTS_TOKEN', NULL),
('travelpayouts_omio',        'travelpayouts', 'Omio',                   'trains',       'active',  '{omio.com,tp.media}',          30, 'sub_id', NULL, 'TRAVELPAYOUTS_TOKEN', NULL),
('travelpayouts_hostelworld', 'travelpayouts', 'Hostelworld',            'lodging',      'active',  '{hostelworld.com,tp.media}',   30, 'sub_id', NULL, 'TRAVELPAYOUTS_TOKEN', NULL),
('travelpayouts_discovercars','travelpayouts', 'DiscoverCars',           'cars',         'active',  '{discovercars.com,tp.media}', 365, 'sub_id', NULL, 'TRAVELPAYOUTS_TOKEN', NULL),
('travelpayouts_localrent',   'travelpayouts', 'Localrent',              'cars',         'active',  '{localrent.com,tp.media}',     30, 'sub_id', NULL, 'TRAVELPAYOUTS_TOKEN', NULL),
('travelpayouts_welcome',     'travelpayouts', 'Welcome Pickups',        'transfers',    'active',  '{welcomepickups.com,tp.media}',45, 'sub_id', NULL, 'TRAVELPAYOUTS_TOKEN', NULL),
('travelpayouts_kiwitaxi',    'travelpayouts', 'KiwiTaxi',               'transfers',    'active',  '{kiwitaxi.com,tp.media}',      30, 'sub_id', NULL, 'TRAVELPAYOUTS_TOKEN', NULL),
('travelpayouts_gyg',         'travelpayouts', 'GetYourGuide',           'tours',        'active',  '{getyourguide.com,tp.media}',  30, 'sub_id', NULL, 'TRAVELPAYOUTS_TOKEN', NULL),
('travelpayouts_tiqets',      'travelpayouts', 'Tiqets',                 'tours',        'active',  '{tiqets.com,tp.media}',        30, 'sub_id', NULL, 'TRAVELPAYOUTS_TOKEN', NULL),
('travelpayouts_gocity',      'travelpayouts', 'Go City',                'tours',        'active',  '{gocity.com,tp.media}',        90, 'sub_id', NULL, 'TRAVELPAYOUTS_TOKEN', NULL),
('travelpayouts_radical',     'travelpayouts', 'Radical Storage',        'luggage',      'active',  '{radicalstorage.com,tp.media}',30, 'sub_id', NULL, 'TRAVELPAYOUTS_TOKEN', NULL),
('travelpayouts_ekta',        'travelpayouts', 'EKTA',                   'insurance',    'planned', '{ektatraveling.com,tp.media}', 30, 'sub_id', NULL, 'TRAVELPAYOUTS_TOKEN', NULL),
('travelpayouts_visitorscov', 'travelpayouts', 'VisitorsCoverage',       'insurance',    'planned', '{visitorscoverage.com,tp.media}',45,'sub_id', NULL, 'TRAVELPAYOUTS_TOKEN', NULL),
-- Launch: Viator partner API and Stay22
('viator',                    'viator',        'Viator',                 'tours',        'active',  '{viator.com}',                 30, NULL,     NULL, 'VIATOR_API_KEY',      NULL),
('stay22',                    'stay22',        'Stay22',                 'lodging',      'active',  '{stay22.com}',                 30, NULL,  'campaign', 'STAY22_PARTNER_ID', NULL)
ON CONFLICT (code) DO NOTHING;

-- Per-partner kill switches are named affiliate.<code> in kill_switches (seeded from this table in 11.5); feature_flag_key stays null unless a partner needs a staged rollout.

INSERT INTO feature_flags (key, description, enabled, rollout_pct, rules, variants) VALUES
('serpapi_live_fares',       'Live fares from SerpApi (legal risk flagged; stays off until the owner turns it on in the console)', false, 100, '{"tiers":["plus","trip_pass"]}', '{}'),
('guest_mode',               'Local-first guest mode before sign-in',                           true,  100, '{}', '{}'),
('min_app_version',          'Forces an update below the version in rules.min_version',         true,  100, '{"min_version":"1.0.0"}', '{}'),
('insurance_cards',          'Insurance referral cards (legal review first)',                   false, 100, '{}', '{}'),
('visa_assist',              'Third-party visa service links (official link always first)',     false, 100, '{}', '{}'),
('affiliate_lodging_test',   'A/B: Travelpayouts Booking.com versus Stay22 on lodging',         true,  100, '{}', '{"travelpayouts":50,"stay22":50}'),
('link_preview',             'User-initiated link preview (hosts on the denylist are never fetched)', true, 100, '{"denylist":["airbnb.*","vrbo.*","booking.*","expedia.*","hotels.com"]}', '{}'),
('shared_research_cache',    'Serve AI research from the shared cache',                         true,  100, '{}', '{}'),
('trip_import',              'Import a trip from a calendar file, a calendar feed or pasted confirmations', true, 100, '{}', '{}'),
('referrals',                'Referral codes and referral credits',                             true,  100, '{}', '{}'),
('booked_fare_alerts',       'Booked-fare drop alerts (you paid X, it is now Y)',               true,  100, '{}', '{}'),
('verify_plan',              'Verify this plan: check a pasted itinerary place by place',       true,  100, '{}', '{}'),
('evidence_recheck',         'One-tap recheck of evidence older than 14 days',                  true,  100, '{}', '{}'),
('calendar_feed_polling',    'Opt-in "Keep checking this calendar" for feed imports',           true,  100, '{}', '{}')
ON CONFLICT (key) DO NOTHING;

-- Settings are flags with kind 'setting': the value is in rules, and the admin console edits them with a reason and history (08 6.16).
-- Others (admin limits, finance cost entries such as setting_finance_cost_2026_11) are created by the console when first needed.
INSERT INTO feature_flags (key, kind, description, enabled, rollout_pct, rules, variants) VALUES
('setting_ai_warm_daily_usd',      'setting', 'Daily budget for nightly shared-cache warming, in dollars (06 8.6)',  true, 100, '{"usd":5}',  '{}'),
('setting_ai_global_daily_usd',    'setting', 'Global daily Anthropic budget in dollars; 80 and 95 percent of it trip the AI breakers (08 6.5)', true, 100, '{"usd":150}', '{}'),
('setting_serpapi_monthly_quota',  'setting', 'SerpApi searches per month; 90 percent trips provider.serpapi (08 6.5)', true, 100, '{"searches":5000}', '{}'),
('setting_import_reward',          'setting', 'Free Trip Pass for the first qualifying import, once per user; at least min_items_applied items including a flight or a stay, a verified email, no active pass on the trip, no active Plus', true, 100,
   '{"min_items_applied":3,"require_flight_or_stay":true,"require_verified_email":true,"block_if_plus":true}', '{}'),
('setting_referral_credits',       'setting', 'Referral credits for each side (20), expiry in months (12), the referrer caps (5 per rolling 30 days, 10 per calendar year) and the qualifying rule', true, 100,
   '{"referrer":20,"referee":20,"expiry_months":12,"referrer_monthly_cap":5,"referrer_yearly_cap":10,"qualify_event":"first_trip_with_dates"}', '{}'),
('setting_booked_fare_drop',       'setting', 'Booked-fare drop alert thresholds: at least min_drop_pct percent and at least min_drop_usd US dollars (converted) below what was paid, at most once per flight every min_days_between days; never a partner link', true, 100,
   '{"min_drop_pct":5,"min_drop_usd":10,"min_days_between":7,"max_age_hours":48}', '{}'),
('setting_calendar_polling',       'setting', 'Calendar feed polling: hours between polls (6), failures in a row before polling stops (3), polled feeds per person (3)', true, 100,
   '{"interval_hours":6,"max_failures":3,"max_feeds_per_user":3}', '{}')
ON CONFLICT (key) DO NOTHING;

INSERT INTO kill_switches (key, description, auto_rule) VALUES
('ai.all',                 'Stop every AI action and agent run', NULL),
('ai.free_tier',           'Stop AI for Free accounts',          '{"metric":"anthropic_daily_spend_pct_of_limit","gte":80}'),
('ai.all_but_paid',        'Stop AI except for paid tiers',      '{"metric":"anthropic_daily_spend_pct_of_limit","gte":95}'),
('ai.agent_runs',          'Stop agent runs only',               NULL),
('ai.explain',             'Stop explain answers',               NULL),
('ai.draft',               'Stop day and trip drafts',           NULL),
('ai.research',            'Stop research questions',            NULL),
('ai.taster',              'Stop the free taster run',           NULL),
('ai.import',              'Stop booking import (pasted confirmations)', NULL),
('ai.verify',              'Stop Verify this plan (reading and checking pasted plans)', NULL),
('ai.recheck',             'Stop one-tap evidence rechecks', NULL),
('ai.packing',             'Stop packing lists',                 NULL),
('ai.web_search',          'Run AI without server web search; features that need it say unavailable', NULL),
('ai.web_fetch',           'Run AI without server web fetch; features that need it say unavailable', NULL),
('ai.model.sonnet',        'Route Sonnet features to Haiku where the feature allows it, else off', NULL),
('ai.model.haiku',         'Route Haiku features to Sonnet where the feature allows it, else off', NULL),
('ai.force_haiku',         'Use the fast model for every feature that allows it', NULL),
('ai.batch',               'Pause digests and cache warming in the batch lane', NULL),
('ai.shared_cache_write',  'Stop writing to the shared research cache (poisoning incident)', NULL),
('provider.serpapi',       'Stop live SerpApi calls; cached fares keep working', '{"metric":"serpapi_month_pct_of_quota","gte":90}'),
('provider.travelpayouts', 'Stop Travelpayouts data calls',      NULL),
('provider.geoapify',      'Stop Geoapify calls; cache only',    NULL),
('provider.anthropic',     'Stop every Anthropic call',          NULL),
('provider.viator',        'Stop Viator calls; cached results only', NULL),
('provider.stay22',        'Stop Stay22 calls',                  NULL),
('provider.frankfurter',   'Stop FX refresh; the last stored rates stay in use', NULL),
('push.all',               'Stop sending push notifications',    NULL),
('email.all',              'Stop sending email',                 NULL),
('import.all',             'Stop every trip import (files, feeds, pasted text, Google Maps lists) and the import reward', NULL),
('import.polling',         'Stop the 6-hourly calendar feed polling; first-time feed imports keep working', NULL),
('referrals.grant',        'Pause referral credit grants (abuse incident); codes can still be entered', NULL),
('webhooks.process',       'Keep receiving webhooks but pause processing, for a safe replay', NULL),
('maintenance',            'Read-only mode: writes return 503',  NULL),
('affiliate.all',          'Turn every partner link off (plain links only)', NULL),
('affiliate.insurance',    'Turn insurance referral cards off',  NULL),
('signups',                'Pause new account creation',         NULL),
('purchases',              'Hide paywalls and purchase buttons', NULL)
ON CONFLICT (key) DO NOTHING;

-- One switch per affiliate program, named affiliate.<code> (an off switch hides that partner's buttons and makes /go return the plain destination).
INSERT INTO kill_switches (key, description)
SELECT 'affiliate.' || code, 'Turn ' || name || ' links off (plain links only)' FROM affiliate_programs
ON CONFLICT (key) DO NOTHING;
"""
