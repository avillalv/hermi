// Credit prices and grant sizes, mirroring apps/api/hermi/modules/credits/prices.py (03 section 11.3, 07 section 5).
// The API reads credit_action_prices at run time; this table is for the client's copy and tests, and an API test keeps it in step.
// [credits, credits when served from the shared cache or null]. verify_plan is per checked item.

export const CREDIT_ACTIONS = ["explain", "live_search", "draft_day", "draft_trip", "research", "agent_run", "verify_plan"] as const;
export type CreditAction = (typeof CREDIT_ACTIONS)[number];

// BEGIN CREDIT_PRICES
export const CREDIT_PRICES = {
  "explain": [1, null],
  "live_search": [1, null],
  "draft_day": [1, null],
  "draft_trip": [4, null],
  "research": [8, 1],
  "agent_run": [40, 8],
  "verify_plan": [1, null]
};
// END CREDIT_PRICES

export const MONTHLY_CREDITS = { free: 12, plus: 60 } as const;
/** The one-time lifetime taster is one agent run, drawn from its own grant. */
export const TASTER_CREDITS = 40;
/** A stopped agent run that called tools is billed pro rata by turns used, never below this. */
export const AGENT_RUN_MINIMUM_CHARGE = 8;
export const PURCHASED_CREDITS_VALID_MONTHS = 12;

export const creditPrice = (action: CreditAction, cached = false): number => {
  const [full, fromCache] = CREDIT_PRICES[action] as [number, number | null];
  return cached && fromCache !== null ? fromCache : full;
};
