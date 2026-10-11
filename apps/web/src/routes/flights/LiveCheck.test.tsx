import { cleanup, fireEvent, screen } from "@testing-library/react"
import { afterEach, beforeEach, expect, test, vi } from "vitest"
import { queryClient } from "../../lib/queryClient"
import { mockApi, reset, show, type Handler } from "../onboarding/testing"
import { FareDetail } from "./FareDetail"

// WF-052.2: Live check on the fare detail (1 credit, or free from a shared check under 6 hours old).
const fare = (over: Record<string, unknown> = {}) => ({
  id: "f1", route_id: "r1", source: "travelpayouts", confidence: "cached", origin: "JFK", destination: "LIS", depart_date: "2027-03-12",
  return_date: "2027-03-19", price: { amount_minor: 41200, currency: "USD" }, passengers: 2, airlines: ["TP"], stops_out: 0, stops_back: 0,
  duration_out_min: 420, duration_back_min: 440, depart_at_local: "2027-03-12T21:10", source_url: null,
  observed_at: new Date(Date.now() - 3 * 3600_000).toISOString(), age_label: "cached 3 h ago", suspect: false, hidden: false, ...over,
})
const trip = (role: string) => ({ id: "t1", version: 1, name: "Lisbon", status: "planning", start_date: null, end_date: null, home_currency: "USD", my_role: role, destinations: [], travelers: [] })

type Over = { flag?: boolean; mode?: string; role?: string; search?: Response }
const api = ({ flag = true, mode = "live", role = "owner", search }: Over = {}): Handler => (u, i) => {
  const m = i?.method ?? "GET"
  if (u.includes("/v1/me/entitlements")) return Response.json({ tier: "plus", limits: {}, flags: { live_search: flag } })
  if (u.endsWith("/flights/live-search") && m === "POST") return search?.clone()
  if (u.endsWith("/v1/trips/t1/routes")) return Response.json([{ id: "r1", trip_id: "t1", mode, cabin: "economy" }])
  if (u.endsWith("/v1/trips/t1") && m === "GET") return Response.json(trip(role))
  if (u.includes("/routes/r1/fares")) return Response.json({ items: [fare()], next_cursor: null, has_more: false })
  if (u.includes("/flights/summary")) return Response.json([])
  if (u.includes("/price-history")) return Response.json({ currency: "USD", google: [], points: [] })
  return undefined
}
const body = (over: Record<string, unknown> = {}) => ({
  fares: [fare({ id: "f9", source: "serpapi", confidence: "live", price: { amount_minor: 39800, currency: "USD" } })],
  cached: false, checked_at: new Date().toISOString(), age_seconds: 0, credits_charged: 1, ...over,
})
const open = () => show(<FareDetail />, "/trips/:id/flights/:routeId/fares/:fareId", "/trips/t1/flights/r1/fares/f1")
const control = () => screen.findByRole("button", { name: "Live check: JFK to LIS, 1 credit" })
const settled = () => screen.findByRole("heading", { level: 1, name: /^JFK to LIS/ })
const confirm = () => fireEvent.click(screen.getByRole("button", { name: "Use 1 credit" }))

beforeEach(() => reset("free"))
afterEach(async () => {
  cleanup()
  await queryClient.cancelQueries() // a late answer of this test must not land in the next one
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

test("Live check is hidden when the flag is off", async () => {
  mockApi(api({ flag: false }))
  open()
  await settled()
  expect(screen.queryByRole("button", { name: /^Live check/ })).not.toBeInTheDocument()
})

test("Live check is hidden for a viewer", async () => {
  mockApi(api({ role: "viewer" }))
  open()
  await settled()
  expect(screen.queryByRole("button", { name: /^Live check/ })).not.toBeInTheDocument()
})

test("Live check is hidden on a route that is not live", async () => {
  mockApi(api({ mode: "cached" }))
  open()
  await settled()
  expect(screen.queryByRole("button", { name: /^Live check/ })).not.toBeInTheDocument()
})

test("a fresh check shows the price first, then says 1 credit used and links the live fare", async () => {
  const f = mockApi(api({ search: Response.json(body()) }))
  open()
  fireEvent.click(await control())
  expect(screen.getByText(/This uses 1 credit\./)).toBeInTheDocument()
  expect(f.mock.calls.some(([u]) => String(u).endsWith("/flights/live-search"))).toBe(false)
  confirm()
  expect(await screen.findByText("Checked just now, 1 credit used")).toBeInTheDocument()
  const call = f.mock.calls.find(([u]) => String(u).endsWith("/flights/live-search"))!
  expect(JSON.parse(String((call[1] as RequestInit).body))).toEqual({ route_id: "r1", depart_date: "2027-03-12", return_date: "2027-03-19" })
  expect(new Headers((call[1] as RequestInit).headers).get("Idempotency-Key")).toBeTruthy()
  expect(screen.getByRole("link", { name: /^Live fare for JFK to LIS, \$398/ })).toHaveAttribute("href", "/trips/t1/flights/r1/fares/f9")
})

test("a shared check under 6 hours old is free and says how old it is", async () => {
  mockApi(api({ search: Response.json(body({ cached: true, credits_charged: 0, age_seconds: 2 * 3600 + 60 })) }))
  open()
  fireEvent.click(await control())
  confirm()
  expect(await screen.findByText("From a shared check 2 h ago, free")).toBeInTheDocument()
})

test.each([
  [402, { code: "insufficient_credits" }, "You have no credits left. Cached results are still here."],
  [503, { code: "live_search_busy" }, "The same check is already running. Try again in a moment. Nothing was charged."],
  [503, { code: "feature_disabled", reason: "provider_paused" }, "Live fares are paused. Cached fares are still here."],
  [502, { code: "provider_error" }, "We could not run that check. Nothing was charged."],
])("error %i %j shows its own sentence", async (status, problem, text) => {
  mockApi(api({ search: Response.json(problem, { status }) }))
  open()
  fireEvent.click(await control())
  confirm()
  expect(await screen.findByRole("alert")).toHaveTextContent(text)
})

test("an empty live result says no credit was used", async () => {
  mockApi(api({ search: Response.json(body({ fares: [], credits_charged: 0 })) }))
  open()
  fireEvent.click(await control())
  confirm()
  expect(await screen.findByText("No live results came back for these dates. No credit was used.")).toBeInTheDocument()
})

test("a free fresh result says no credit was used", async () => {
  mockApi(api({ search: Response.json(body({ cached: false, credits_charged: 0 })) }))
  open()
  fireEvent.click(await control())
  confirm()
  expect(await screen.findByText("Checked just now, no credit used")).toBeInTheDocument()
})

test("offline: the button is disabled, the line says a live check needs a connection, nothing is posted", async () => {
  vi.spyOn(navigator, "onLine", "get").mockReturnValue(false)
  const f = mockApi(api({ search: Response.json(body()) }))
  open()
  const b = await control()
  expect(b).toBeDisabled()
  expect(screen.getByText("A live check needs a connection. Cached results are still here.")).toBeInTheDocument()
  fireEvent.click(b)
  expect(f.mock.calls.some(([u, i]) => String(u).endsWith("/flights/live-search") && (i as RequestInit | undefined)?.method === "POST")).toBe(false)
})

test("focus moves to Use 1 credit when the confirm opens and back to the button on Cancel", async () => {
  mockApi(api({ search: Response.json(body()) }))
  open()
  fireEvent.click(await control())
  expect(screen.getByRole("button", { name: "Use 1 credit" })).toHaveFocus()
  fireEvent.click(screen.getByRole("button", { name: "Cancel" }))
  expect(await control()).toHaveFocus()
})
