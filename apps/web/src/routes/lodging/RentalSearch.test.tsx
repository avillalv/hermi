import { TRAVELER_COLORS } from "@hermi/tokens"
import { cleanup, fireEvent, screen } from "@testing-library/react"
import { afterEach, beforeEach, expect, test, vi } from "vitest"
import { queryClient } from "../../lib/queryClient"
import { mockApi, reset, show, type Handler } from "../onboarding/testing"
import { Stays } from "./Stays"

// WF-052.2: live rental search on Stays, behind the same flag as live fares.
const trip = {
  id: "t1", version: 1, name: "La Fortuna", status: "planning", start_date: "2027-11-27", end_date: "2027-12-01", home_currency: "USD", my_role: "owner",
  destinations: [{ id: "d1", position: 0, name: "La Fortuna", region: null, country: null, timezone: null }],
  travelers: [{ id: "p1", name: "Ana", color: TRAVELER_COLORS[0], home_airports: [], linked_user_id: "u1", is_me: true }],
}
const stay = { id: "s1", trip_id: "t1", title: "Casita", url: null, site: null, check_in: null, check_out: null, nights: 4, price_total: null, price_per_night: null, bedrooms: null, rating: null, notes: "", status: "shortlisted", added_via: "paste", version: 1, votes: [], vote_summary: { hearts: 0 } }
const found = (over: Record<string, unknown> = {}) => ({
  offers: [{ title: "Volcano cabin", link: "https://www.airbnb.com/rooms/9", site: "airbnb.com", price_per_night_minor: 12000, price_total_minor: 48000, rating: 4.8 }],
  currency: "USD", sorted_by: "price, lowest first", cached: false, checked_at: new Date().toISOString(), age_seconds: 0, credits_charged: 1, ...over,
})
const api = (flag: boolean, search?: Response): Handler => (u, i) => {
  const m = i?.method ?? "GET"
  if (u.includes("/v1/me/entitlements")) return Response.json({ tier: "plus", limits: {}, flags: { live_search: flag } })
  if (u.endsWith("/lodging/rental-search") && m === "POST") return search?.clone()
  if (u.endsWith("/v1/me")) return Response.json({ id: "u1" })
  if (u.endsWith("/v1/trips/t1") && m === "GET") return Response.json(trip)
  if (u.includes("/trips/t1/lodging?") && m === "GET") return Response.json({ items: [stay], has_more: false, next_cursor: null, sorted_by: "votes" })
  return undefined
}
const open = () => show(<Stays />, "/trips/:id/stays", "/trips/t1/stays")
const control = () => screen.findByRole("button", { name: "Live check: rental search for La Fortuna, 1 credit" })
const confirm = () => fireEvent.click(screen.getByRole("button", { name: "Use 1 credit" }))

beforeEach(() => reset("free"))
afterEach(async () => {
  cleanup()
  await queryClient.cancelQueries() // a late answer of this test must not land in the next one
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

test("rental search is hidden when the flag is off", async () => {
  mockApi(api(false))
  open()
  await screen.findByRole("article", { name: /Casita/ })
  expect(screen.queryByRole("button", { name: /^Live check/ })).not.toBeInTheDocument()
  expect(screen.queryByText("Search rentals")).not.toBeInTheDocument()
})

test("a fresh search shows the price first, then the label and offers that link out", async () => {
  const f = mockApi(api(true, Response.json(found())))
  open()
  fireEvent.click(await control())
  confirm()
  expect(await screen.findByText("Checked just now, 1 credit used")).toBeInTheDocument()
  const call = f.mock.calls.find(([u]) => String(u).endsWith("/lodging/rental-search"))!
  expect(JSON.parse(String((call[1] as RequestInit).body))).toEqual({ check_in: "2027-11-27", check_out: "2027-12-01", adults: 1 })
  expect(new Headers((call[1] as RequestInit).headers).get("Idempotency-Key")).toBeTruthy()
  const link = screen.getByRole("link", { name: /^Open Volcano cabin on airbnb.com/ })
  expect(link).toHaveAttribute("href", "https://www.airbnb.com/rooms/9")
  expect(link).toHaveAttribute("rel", expect.stringContaining("noopener"))
})

test("a shared search under 6 hours old is free and labelled", async () => {
  mockApi(api(true, Response.json(found({ cached: true, credits_charged: 0, age_seconds: 3 * 3600 }))))
  open()
  fireEvent.click(await control())
  confirm()
  expect(await screen.findByText("From a shared check 3 h ago, free")).toBeInTheDocument()
})

test("a provider error says nothing was charged", async () => {
  mockApi(api(true, Response.json({ code: "provider_error" }, { status: 502 })))
  open()
  fireEvent.click(await control())
  confirm()
  expect(await screen.findByRole("alert")).toHaveTextContent("We could not run that check. Nothing was charged.")
})

test("no credits and an empty result have their own states", async () => {
  mockApi(api(true, Response.json({ code: "insufficient_credits" }, { status: 402 })))
  const a = open()
  fireEvent.click(await control())
  confirm()
  expect(await screen.findByRole("alert")).toHaveTextContent("You have no credits left.")
  a.unmount()
  reset("free")
  mockApi(api(true, Response.json(found({ offers: [], credits_charged: 0 }))))
  open()
  fireEvent.click(await control())
  confirm()
  expect(await screen.findByText("No live results came back for these dates. No credit was used.")).toBeInTheDocument()
})

test("a paused search says rentals are paused, not fares", async () => {
  mockApi(api(true, Response.json({ code: "feature_disabled", reason: "provider_paused" }, { status: 503 })))
  open()
  fireEvent.click(await control())
  confirm()
  expect(await screen.findByRole("alert")).toHaveTextContent("Live rental search is paused. Cached results are still here.")
})

test("a 429 says to try again in a few minutes", async () => {
  mockApi(api(true, Response.json({ code: "rate_limited" }, { status: 429 })))
  open()
  fireEvent.click(await control())
  confirm()
  expect(await screen.findByRole("alert")).toHaveTextContent("Too many live checks just now. Try again in a few minutes.")
})
