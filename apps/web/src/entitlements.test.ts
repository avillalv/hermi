import { describe, expect, it } from "vitest";
import {
  LIMIT_KEYS,
  PAYWALL_TRIGGERS,
  TIER_LIMITS,
  TIERS,
  bestLimit,
  limitOf,
} from "../../../packages/shared/src/entitlements";

describe("entitlements table", () => {
  it.each(TIERS)("%s: every limit key is a known key", (tier) => {
    for (const k of Object.keys(TIER_LIMITS[tier]))
      expect(LIMIT_KEYS).toContain(k);
  });
  it("a missing key means not granted", () => {
    expect(limitOf(TIER_LIMITS.trip_pass, "active_trips")).toBe(0);
    expect(limitOf(TIER_LIMITS.free, "collaborators")).toBe(1);
    expect(limitOf(TIER_LIMITS.plus, "live_routes")).toBe(3);
  });
  it("Plus with a Trip Pass takes the higher limit per key", () => {
    for (const k of LIMIT_KEYS) {
      const best = bestLimit(TIER_LIMITS.plus, TIER_LIMITS.trip_pass, k);
      expect(best).toBe(
        Math.max(
          limitOf(TIER_LIMITS.plus, k),
          limitOf(TIER_LIMITS.trip_pass, k),
        ),
      );
    }
    expect(
      bestLimit(TIER_LIMITS.free, TIER_LIMITS.trip_pass, "live_routes"),
    ).toBe(2);
  });
  it("every trigger has a reason and a plain free path", () => {
    expect(Object.keys(PAYWALL_TRIGGERS)).toHaveLength(12);
    for (const t of Object.values(PAYWALL_TRIGGERS))
      expect(t.freePath).not.toMatch(
        new RegExp(`[${String.fromCharCode(0x2013, 0x2014)}]`),
      );
  });
});
