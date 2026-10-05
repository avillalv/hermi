import { afterEach, beforeEach, expect, test, vi } from "vitest"
import { __resetAnalytics, __sink, analytics, setAnalyticsOptOut, setAnalyticsUser } from "./analytics"
import { track } from "./track"

const seen: unknown[] = []
const on = (e: Event) => seen.push((e as CustomEvent).detail)
beforeEach(() => {
  localStorage.clear()
  sessionStorage.clear()
  __resetAnalytics()
  seen.length = 0
  window.addEventListener("hermi:event", on)
})
afterEach(() => {
  window.removeEventListener("hermi:event", on)
  delete (navigator as { globalPrivacyControl?: boolean }).globalPrivacyControl
  vi.restoreAllMocks()
})

test("an event reaches the sink once with the common properties", () => {
  expect(analytics.capture("trip_created", { source: "blank", destination_count: 1, has_dates: true })).toBe(true)
  expect(__sink).toHaveLength(1)
  expect(seen).toHaveLength(1)
  const p = __sink[0].properties
  expect(__sink[0].event).toBe("trip_created")
  expect(p).toMatchObject({ platform: "web", source: "blank", destination_count: 1, has_dates: true })
  expect(p.app_version).toBeTruthy()
  expect(p.env).toBeTruthy()
  expect(p.session_id).toBe(sessionStorage.getItem("hermi.analytics.session"))
})

test("opt-out by GPC, by the setting and by setAnalyticsOptOut each stop events and no request is made", () => {
  const f = vi.spyOn(globalThis, "fetch")
  const beacon = vi.fn(() => true)
  Object.defineProperty(navigator, "sendBeacon", { value: beacon, configurable: true })
  ;(navigator as { globalPrivacyControl?: boolean }).globalPrivacyControl = true
  expect(track("trip_archived")).toBe(false)
  delete (navigator as { globalPrivacyControl?: boolean }).globalPrivacyControl
  setAnalyticsOptOut(true)
  expect(localStorage.getItem("hermi.analytics.optout")).toBe("1")
  expect(track("trip_archived")).toBe(false)
  setAnalyticsOptOut(false)
  expect(track("trip_archived")).toBe(true)
  setAnalyticsOptOut(true)
  expect(track("map_opened")).toBe(false)
  expect(__sink).toHaveLength(1) // only the one sent while opted in
  expect(seen).toHaveLength(1)
  expect(f).not.toHaveBeenCalled()
  expect(beacon).not.toHaveBeenCalled()
})

test("an unknown name, an unknown property and a bad value throw and never send", () => {
  // @ts-expect-error not in the catalogue
  expect(() => analytics.capture("made_up_event")).toThrow(/unknown event/)
  // @ts-expect-error property not in the catalogue
  expect(() => analytics.capture("trip_created", { email: "a" })).toThrow(/no property/)
  // @ts-expect-error not an allowed value
  expect(() => analytics.capture("trip_created", { source: "carrier_pigeon" })).toThrow(/not allowed/)
  expect(() => analytics.capture("trip_created", { destination_count: 1.5 })).toThrow(/not allowed/)
  expect(__sink).toHaveLength(0)
  expect(seen).toHaveLength(0)
})

test("a string value that looks like an email or free text is rejected", () => {
  expect(() => analytics.capture("error_shown", { code: "me@example.com" })).toThrow(/not allowed/)
  expect(() => analytics.capture("error_shown", { code: "x".repeat(65) })).toThrow(/not allowed/)
  expect(() => analytics.capture("error_shown", { code: "not_found", screen: "plan" })).not.toThrow()
})

test("captureOnce fires once even when called again (StrictMode double effects)", () => {
  const go = () => analytics.captureOnce("first", "first_itinerary_item_added", { minutes_since_signup_bucket: "unknown" })
  expect([go(), go(), go()]).toEqual([true, false, false])
  expect(__sink).toHaveLength(1)
})

test("an opted-out call does not burn the once flag", () => {
  setAnalyticsOptOut(true)
  expect(analytics.captureOnce("k", "map_opened")).toBe(false)
  setAnalyticsOptOut(false)
  expect(analytics.captureOnce("k", "map_opened")).toBe(true)
})

test("distinct_id is the user id once set, the once flag is scoped by it, and sign-out clears it", () => {
  const id = "0190a1b2-0000-7000-8000-000000000001"
  analytics.capture("map_opened")
  expect(__sink[0].distinct_id).toBe(sessionStorage.getItem("hermi.analytics.session"))
  setAnalyticsUser(id)
  analytics.capture("map_opened")
  expect(__sink[1].distinct_id).toBe(id)
  expect(analytics.captureOnce("k", "map_opened")).toBe(true)
  expect(localStorage.getItem(`hermi.analytics.once.k.${id}`)).toBe("1")
  setAnalyticsUser("0190a1b2-0000-7000-8000-000000000002")
  expect(analytics.captureOnce("k", "map_opened")).toBe(true)
  setAnalyticsUser(null)
  analytics.capture("map_opened")
  expect(__sink[__sink.length - 1].distinct_id).toBe(sessionStorage.getItem("hermi.analytics.session"))
})
