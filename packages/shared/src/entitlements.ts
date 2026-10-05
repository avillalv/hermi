// Plan limits per tier and the paywall triggers, mirroring apps/api (plans seed, billing/paywall.py).
// The API reads plans.limits at run time; this table is for the client's copy and tests, and an API test keeps it in step.

export const TIERS = ["free", "plus", "trip_pass"] as const;
export type TierCode = (typeof TIERS)[number];
export type LimitValue = number | boolean;
export type Limits = Partial<Record<string, LimitValue>>;

export const LIMIT_KEYS = ["active_trips", "active_trips_bonus", "routes_per_trip", "live_routes", "live_window_days", "price_alerts", "live_alerts", "collaborators", "travelers_per_trip", "can_invite", "saved_lodging_per_trip", "lodging_compare", "places_searches_per_day", "hide_presentation_footer", "taster_agent_runs", "verify_items_per_run", "destinations_per_trip", "airports_per_side", "imports", "calendar_feed", "calendar_polling", "monthly_credits", "monthly_ceiling_micros", "daily_ceiling_micros", "live_checks_max"] as const;
export type LimitKey = (typeof LIMIT_KEYS)[number];

// BEGIN TIER_LIMITS
export const TIER_LIMITS = {
  "free": {"active_trips": 2, "active_trips_bonus": 0, "routes_per_trip": 1, "live_routes": 0, "live_window_days": 0, "price_alerts": 1, "live_alerts": false, "collaborators": 1, "travelers_per_trip": 2, "can_invite": true, "saved_lodging_per_trip": 8, "lodging_compare": 2, "places_searches_per_day": 30, "hide_presentation_footer": false, "taster_agent_runs": 1, "verify_items_per_run": 5, "destinations_per_trip": 12, "airports_per_side": 2, "imports": true, "calendar_feed": true, "calendar_polling": true, "monthly_credits": 12, "monthly_ceiling_micros": 250000, "daily_ceiling_micros": 50000},
  "plus": {"active_trips": 25, "active_trips_bonus": 0, "routes_per_trip": 5, "live_routes": 3, "live_window_days": 120, "price_alerts": 3, "live_alerts": true, "collaborators": 6, "travelers_per_trip": 8, "can_invite": true, "saved_lodging_per_trip": 100, "lodging_compare": 4, "places_searches_per_day": 100, "hide_presentation_footer": true, "taster_agent_runs": 0, "verify_items_per_run": 12, "destinations_per_trip": 12, "airports_per_side": 4, "imports": true, "calendar_feed": true, "calendar_polling": true, "monthly_credits": 60, "monthly_ceiling_micros": 2250000, "daily_ceiling_micros": 400000},
  "trip_pass": {"active_trips_bonus": 1, "routes_per_trip": 3, "live_routes": 2, "live_window_days": 120, "live_checks_max": 60, "price_alerts": 2, "live_alerts": true, "collaborators": 6, "travelers_per_trip": 8, "can_invite": true, "saved_lodging_per_trip": 30, "lodging_compare": 4, "places_searches_per_day": 100, "hide_presentation_footer": true, "verify_items_per_run": 12, "destinations_per_trip": 12, "airports_per_side": 4, "imports": true, "calendar_feed": true, "calendar_polling": true, "monthly_credits": 0, "monthly_ceiling_micros": 1800000, "daily_ceiling_micros": 400000}
};
// END TIER_LIMITS

/** A numeric limit; absent means not granted (0). */
export const limitOf = (limits: Limits, key: string): number => Number(limits[key] ?? 0);

/** The higher of an owner tier and a pass, per key (Plus with a Trip Pass takes the higher limit). */
export const bestLimit = (a: Limits, b: Limits, key: string): number => Math.max(limitOf(a, key), limitOf(b, key));

export type PaywallTrigger =
  | "third_trip" | "second_route" | "track_live" | "alert_limit" | "invite"
  | "out_of_credits_draft" | "out_of_credits_research" | "out_of_credits_agent" | "out_of_credits_verify"
  | "export_footer" | "ninth_stay" | "lifecycle_14d";
export type PaywallReason = "trip_limit" | "sharing" | "live_routes" | "credits" | "agent_taster_used" | "traveler_limit";
export type PaywallHint = { trigger?: PaywallTrigger; reason: PaywallReason; offer_url: string; free_path: string };

export type TriggerRule = {
  reason: string;
  freePath: string;
  muteDays: number; // one dismissal
  longMuteDays: number; // after MUTE_AFTER_DISMISSALS dismissals
  countsTowardCap: boolean;
  modal: boolean;
  cooldownDays?: number;
  perTripDays?: number;
};
export const VIEWS_PER_WEEK = 3;
export const MUTE_AFTER_DISMISSALS = 3;

const rule = (reason: string, freePath: string, o: Partial<TriggerRule> = {}): TriggerRule => ({
  reason, freePath, muteDays: 7, longMuteDays: 30, countsTowardCap: true, modal: true, ...o,
});
export const PAYWALL_TRIGGERS: Record<PaywallTrigger, TriggerRule> = {
  third_trip: rule("trip_limit", "Archive a trip or join trips other people plan"),
  second_route: rule("live_routes", "Keep one route"),
  track_live: rule("live_routes", "Use 1 credit or cached fares"),
  alert_limit: rule("live_routes", "Keep the cached-fare alert"),
  invite: rule("sharing", "Keep the one collaborator, or share a read-only link"),
  out_of_credits_draft: rule("credits", "Plan manually, or invite a friend for credits"),
  out_of_credits_research: rule("credits", "Skip, or invite a friend for credits"),
  out_of_credits_agent: rule("credits", "Use a research question"),
  out_of_credits_verify: rule("credits", "Check fewer items, or invite a friend for credits"),
  export_footer: rule("export_footer", "Export with footer", { muteDays: 30, countsTowardCap: false, modal: false }),
  ninth_stay: rule("ninth_stay", "Save it to the later list", { perTripDays: 7 }),
  lifecycle_14d: rule("lifecycle_14d", "Dismiss", { muteDays: 30, countsTowardCap: false, modal: false, cooldownDays: 14 }),
};
