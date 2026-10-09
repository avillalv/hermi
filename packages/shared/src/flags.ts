// Flag and kill switch keys seeded by apps/api (hermi.seed, 03 section 11.5). The API reads the tables at run time;
// this list is for the client's copy and for tests. Per-partner switches are named affiliate.<code> and not listed.

export const FLAG_KEYS = [
  "serpapi_live_fares", "guest_mode", "min_app_version", "insurance_cards", "visa_assist", "affiliate_lodging_test",
  "link_preview", "shared_research_cache", "trip_import", "referrals", "booked_fare_alerts", "verify_plan",
  "evidence_recheck", "calendar_feed_polling",
] as const;
export type FlagKey = (typeof FLAG_KEYS)[number];

export const SETTING_KEYS = [
  "setting_ai_warm_daily_usd", "setting_ai_global_daily_usd", "setting_serpapi_monthly_quota", "setting_import_reward",
  "setting_referral_credits", "setting_booked_fare_drop", "setting_calendar_polling", "setting_rate_limits",
] as const;
export type SettingKey = (typeof SETTING_KEYS)[number];

export const SWITCH_KEYS = [
  "ai.all", "ai.free_tier", "ai.all_but_paid", "ai.agent_runs", "ai.explain", "ai.draft", "ai.research", "ai.taster",
  "ai.import", "ai.verify", "ai.recheck", "ai.packing", "ai.web_search", "ai.web_fetch", "ai.model.sonnet",
  "ai.model.haiku", "ai.force_haiku", "ai.batch", "ai.shared_cache_write",
  "provider.serpapi", "provider.travelpayouts", "provider.geoapify", "provider.anthropic", "provider.viator",
  "provider.stay22", "provider.frankfurter",
  "push.all", "email.all", "import.all", "import.polling", "referrals.grant", "webhooks.process", "maintenance",
  "affiliate.all", "affiliate.insurance", "signups", "purchases",
] as const;
export type SwitchKey = (typeof SWITCH_KEYS)[number];

/** A per-account hold, created on demand and never seeded. */
export type UserHoldKey = `user:${string}`;

/** Defaults the seed ships: serpapi_live_fares is off and the global daily AI budget is 150 US dollars. */
export const FLAG_DEFAULTS = { serpapi_live_fares: false, setting_ai_global_daily_usd: 150 } as const;
