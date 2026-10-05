import { fireEvent, screen, waitFor, within } from "@testing-library/react"
import { afterEach, beforeEach, expect, test, vi } from "vitest"
import { bodyOf, mockApi, reset, show, type Handler } from "../onboarding/testing"
import { Flights } from "./Flights"

const hoursAgo = (h: number) => new Date(Date.now() - h * 3600_000).toISOString()
const route = (over: Record<string, unknown> = {}) => ({
  id: "r1", trip_id: "t1", label: null, origin_codes: ["JFK"], destination_codes: ["LIS"], trip_type: "round_trip",
  depart_from: "2027-03-12", depart_to: "2027-03-12", return_from: "2027-03-19", return_to: "2027-03-19", min_nights: null,
  max_nights: null, adults: 2, children: 0, cabin: "economy", max_stops: null, mode: "cached", active: true, version: 1,
  chosen_fare_id: null, last_checked_at: hoursAgo(3), ...over,
})
const fare = (over: Record<string, unknown> = {}) => ({
  id: "f1", route_id: "r1", source: "travelpayouts", confidence: "cached", origin: "JFK", destination: "LIS", depart_date: "2027-03-12",
  return_date: "2027-03-19", price: { amount_minor: 41200, currency: "USD" }, passengers: 2, airlines: ["TP"], stops_out: 0, stops_back: 0,
  duration_out_min: 420, duration_back_min: 440, depart_at_local: "2027-03-12T21:10", source_url: null, observed_at: hoursAgo(3),
  age_label: "cached 3 h ago", suspect: false, hidden: false, ...over,
})
const trip = (over: Record<string, unknown> = {}) => ({
  id: "t1", version: 1, name: "Lisbon", status: "planning", start_date: null, end_date: null, home_currency: "USD", my_role: "owner",
  destinations: [], travelers: [], ...over,
})
const history = (points: { day: string; price: number }[]) => ({
  currency: "USD", google: [], points: points.map((p) => ({ day: p.day, source: "travelpayouts", price: { amount_minor: p.price, currency: "USD" } })),
})

type Over = { role?: string; routes?: unknown[]; fares?: unknown[]; hist?: unknown; grid?: unknown[]; more?: Handler }
const api = ({ role = "owner", routes = [route()], fares = [fare()], hist = history([{ day: "2027-01-01", price: 45000 }, { day: "2027-01-02", price: 41200 }]), grid = [], more }: Over = {}): Handler =>
  (u, i) => {
    const m = i?.method ?? "GET"
    const r = more?.(u, i)
    if (r) return r
    if (u.endsWith("/v1/trips/t1") && m === "GET") return Response.json(trip({ my_role: role }))
    if (u.endsWith("/trips/t1/routes") && m === "GET") return Response.json(routes)
    if (u.includes("/flights/summary")) return Response.json((routes as { id: string }[]).map((x) => ({ route_id: x.id, cheapest: fares[0] ?? null, last_checked_at: hoursAgo(3), fare_count: fares.length, chosen: null, chosen_latest: null })))
    if (u.includes("/flights/best")) return Response.json(fares)
    if (u.includes("/price-history")) return Response.json(hist)
    if (u.includes("/date-grid")) return Response.json(grid)
    if (u.endsWith("/price-alerts")) return Response.json([])
    return undefined
  }
const open = () => show(<Flights />, "/trips/:id/flights", "/trips/t1/flights")
const called = (f: ReturnType<typeof mockApi>, method: string, part: string) =>
  f.mock.calls.some(([u, i]) => String(u).includes(part) && ((i as RequestInit | undefined)?.method ?? "GET") === method)

beforeEach(() => reset("free"))
afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

test("loading shows the shared skeleton", async () => {
  mockApi(() => new Promise(() => {}) as never)
  const { container } = open()
  expect(await screen.findByRole("status", { name: "Loading" })).toBeInTheDocument()
  expect(container.querySelector(".state-card--route .state-skel--chart")).toBeInTheDocument()
})

test("empty: no routes says so and offers Add a route", async () => {
  mockApi(api({ routes: [] }))
  open()
  expect(await screen.findByText("No routes yet")).toBeInTheDocument()
  expect(screen.getByText("Add where you fly from and to, and we will track fares for you.")).toBeInTheDocument()
  expect(screen.getByRole("button", { name: "Add a route" })).toBeEnabled()
})

test("error: a failed load shows the message and a retry", async () => {
  mockApi(() => new Response("{}", { status: 500 }))
  open()
  expect(await screen.findByRole("alert", {}, { timeout: 3000 })).toHaveTextContent("We could not load fares. Try again.")
  expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument()
})

test("offline: says fares are the last saved ones and disables writes", async () => {
  vi.spyOn(navigator, "onLine", "get").mockReturnValue(false)
  mockApi(api())
  open()
  expect(await screen.findByRole("status")).toHaveTextContent("You are offline. Showing the last saved fares with their age.")
  await screen.findByRole("article", { name: "JFK to LIS" })
  expect(screen.getByRole("button", { name: "Add route" })).toBeDisabled()
})

test("a route card shows codes, dates, travelers, the lowest fare chip with source and age, and the disclosure", async () => {
  mockApi(api())
  open()
  const card = await screen.findByRole("article", { name: "JFK to LIS" })
  expect(within(card).getByText(/2 travelers/)).toBeInTheDocument()
  expect(within(card).getByText("Lowest in this list")).toBeInTheDocument()
  const chip = within(card).getByRole("button", { name: /LIS.*\$412.*Cached.*3 h ago/ })
  expect(chip).toBeInTheDocument()
  expect(within(card).getByText("Fares at last check. Prices can change on the booking site.")).toBeInTheDocument()
})

test("a stale fare (over 24 h) carries Check again", async () => {
  mockApi(api({ fares: [fare({ observed_at: hoursAgo(30), age_label: "cached 30 h ago" })] }))
  open()
  const card = await screen.findByRole("article", { name: "JFK to LIS" })
  expect(within(card).getAllByText("Check again").length).toBeGreaterThan(0)
})

test("the chart shows a text summary, a hidden data table and the legend", async () => {
  mockApi(api())
  open()
  const card = await screen.findByRole("article", { name: "JFK to LIS" })
  expect(await within(card).findByText(/Lowest \$412 on 2 Jan, now \$412/)).toBeInTheDocument()
  expect(within(card).getByRole("table", { name: "Price history data" })).toBeInTheDocument()
  expect(within(card).getByText("Aviasales, cached")).toBeInTheDocument()
})

test("chart states: empty and one point", async () => {
  mockApi(api({ hist: history([]) }))
  const first = open()
  expect(await screen.findByText("No fares yet. Checks run daily.")).toBeInTheDocument()
  first.unmount()
  reset("free")
  mockApi(api({ hist: history([{ day: "2027-01-01", price: 45000 }]) }))
  open()
  expect(await screen.findByText("We need two checks to draw a line")).toBeInTheDocument()
})

test("chart error says it could not load", async () => {
  mockApi(api({ more: (u) => (u.includes("/price-history") ? new Response("{}", { status: 500 }) : undefined) }))
  open()
  expect(await screen.findByText("We could not load this chart. Try again.", {}, { timeout: 3000 })).toBeInTheDocument()
})

test("Grid is a real table with headers and prices printed as numbers", async () => {
  const grid = [
    { fare_id: "f1", depart_date: "2027-03-12", return_date: "2027-03-19", price: { amount_minor: 41200, currency: "USD" }, source: "travelpayouts", observed_at: hoursAgo(3) },
    { fare_id: "f2", depart_date: "2027-03-13", return_date: "2027-03-19", price: { amount_minor: 52000, currency: "USD" }, source: "travelpayouts", observed_at: hoursAgo(3) },
  ]
  mockApi(api({ grid }))
  open()
  const card = await screen.findByRole("article", { name: "JFK to LIS" })
  fireEvent.click(within(card).getByRole("tab", { name: "Grid" }))
  const table = await within(card).findByRole("table", { name: "Fares by date" })
  expect(within(table).getAllByRole("columnheader").length).toBeGreaterThan(1)
  expect(within(table).getAllByRole("rowheader").length).toBeGreaterThan(0)
  expect(within(table).getByText("Cached, checked 3 h ago")).toBeInTheDocument()
  expect(within(table).getByText("$412")).toBeInTheDocument()
  expect(within(table).getByText("$520")).toBeInTheDocument()
})

test("Options lists fares sorted by price with the neutral statement, and the sort control re-queries", async () => {
  const f = mockApi(api({ fares: [fare(), fare({ id: "f2", price: { amount_minor: 50000, currency: "USD" }, airlines: ["BA"], stops_out: 1 })] }))
  open()
  const card = await screen.findByRole("article", { name: "JFK to LIS" })
  fireEvent.click(within(card).getByRole("tab", { name: "Options" }))
  expect(await within(card).findByText("Sorted by price, lowest first")).toBeInTheDocument()
  expect(await within(card).findByText(/1 stop/)).toBeInTheDocument()
  fireEvent.click(within(card).getByRole("tab", { name: "Stops" }))
  expect(await within(card).findByText("Sorted by stops, fewest first")).toBeInTheDocument()
  await waitFor(() => expect(f.mock.calls.some(([u]) => String(u).includes("sort=stops"))).toBe(true))
})

test("Choose picks a fare with PUT choice", async () => {
  const f = mockApi(api({ more: (u, i) => (u.endsWith("/routes/r1/choice") && i?.method === "PUT" ? Response.json(trip()) : undefined) }))
  open()
  const card = await screen.findByRole("article", { name: "JFK to LIS" })
  fireEvent.click(within(card).getByRole("tab", { name: "Options" }))
  fireEvent.click(await within(card).findByRole("button", { name: "Choose" }))
  await waitFor(() => expect(called(f, "PUT", "/routes/r1/choice")).toBe(true))
  expect(bodyOf(f, "/routes/r1/choice")).toEqual({ fare_id: "f1" })
})

test("Add route sheet posts the airports, dates and travelers", async () => {
  const f = mockApi(api({ routes: [], more: (u, i) => (u.endsWith("/trips/t1/routes") && i?.method === "POST" ? Response.json(route(), { status: 201 }) : undefined) }))
  open()
  fireEvent.click(await screen.findByRole("button", { name: "Add a route" }))
  fireEvent.change(screen.getByLabelText("From"), { target: { value: "jfk, ewr" } })
  fireEvent.change(screen.getByLabelText("To"), { target: { value: "LIS" } })
  fireEvent.change(screen.getByLabelText("Leave on"), { target: { value: "2027-03-12" } })
  fireEvent.change(screen.getByLabelText("Return on"), { target: { value: "2027-03-19" } })
  fireEvent.change(screen.getByLabelText("Travelers"), { target: { value: "2" } })
  fireEvent.click(screen.getByRole("button", { name: "Add route" }))
  await waitFor(() => expect(called(f, "POST", "/trips/t1/routes")).toBe(true))
  const post = f.mock.calls.find(([u, i]) => String(u).endsWith("/trips/t1/routes") && (i as RequestInit).method === "POST")!
  expect(JSON.parse(String((post[1] as RequestInit).body))).toMatchObject({
    origin_codes: ["JFK", "EWR"], destination_codes: ["LIS"], trip_type: "round_trip", depart_from: "2027-03-12", depart_to: "2027-03-12",
    return_from: "2027-03-19", return_to: "2027-03-19", adults: 2, mode: "cached",
  })
})

test("Add route rejects a bad airport code before sending", async () => {
  const f = mockApi(api({ routes: [] }))
  open()
  fireEvent.click(await screen.findByRole("button", { name: "Add a route" }))
  fireEvent.change(screen.getByLabelText("From"), { target: { value: "NEW YORK" } })
  fireEvent.click(screen.getByRole("button", { name: "Add route" }))
  expect((await screen.findAllByText("Use three-letter airport codes, like JFK.")).length).toBeGreaterThan(0)
  expect(called(f, "POST", "/trips/t1/routes")).toBe(false)
})

test("limit: a 402 on add shows the second route message with an upgrade link", async () => {
  mockApi(api({ more: (u, i) => (u.endsWith("/trips/t1/routes") && i?.method === "POST" ? Response.json({ code: "limit_reached" }, { status: 402 }) : undefined) }))
  open()
  fireEvent.click(await screen.findByRole("button", { name: "Add route" }))
  fireEvent.change(screen.getByLabelText("From"), { target: { value: "JFK" } })
  fireEvent.change(screen.getByLabelText("To"), { target: { value: "LIS" } })
  fireEvent.change(screen.getByLabelText("Leave on"), { target: { value: "2027-03-12" } })
  fireEvent.change(screen.getByLabelText("Return on"), { target: { value: "2027-03-19" } })
  fireEvent.click(screen.getByRole("button", { name: "Add route" }))
  expect(await screen.findByRole("alert")).toHaveTextContent("Your plan has reached its route or airport limit for this trip.")
  expect(screen.getByRole("link", { name: "See plans" })).toHaveAttribute("href", "/account")
})

test("a viewer sees fares with no add, choose or check controls", async () => {
  mockApi(api({ role: "viewer" }))
  open()
  const card = await screen.findByRole("article", { name: "JFK to LIS" })
  fireEvent.click(within(card).getByRole("tab", { name: "Options" }))
  await within(card).findByText("Sorted by price, lowest first")
  expect(screen.queryByRole("button", { name: /Add route|Add a route|Choose|Check now/ })).not.toBeInTheDocument()
})

test("the section strip links to Flights as current", async () => {
  mockApi(api())
  open()
  await screen.findByRole("article", { name: "JFK to LIS" })
  expect(screen.getByRole("link", { name: "Flights" })).toHaveAttribute("aria-current", "page")
})

const checkNow = async (more: Over["more"]) => {
  mockApi(api({ more }))
  open()
  const card = await screen.findByRole("article", { name: "JFK to LIS" })
  fireEvent.click(within(card).getByRole("button", { name: "Check now" }))
  return card
}
const refresh = (res: () => Response): Over["more"] => (u, i) => (u.endsWith("/flights/refresh") && i?.method === "POST" ? res() : undefined)

test("Check now: a 503 says it could not check and cached fares remain", async () => {
  const card = await checkNow(refresh(() => Response.json({}, { status: 503 })))
  expect(await within(card).findByRole("alert")).toHaveTextContent("We could not check fares right now. Cached fares are still here.")
})

test("Check now: a 429 says to try again in a minute", async () => {
  const card = await checkNow(refresh(() => Response.json({}, { status: 429 })))
  expect(await within(card).findByRole("alert")).toHaveTextContent("You checked a moment ago. Try again in a minute.")
})

test("Check now: a 202 with a failed job shows the failure", async () => {
  const card = await checkNow(refresh(() => Response.json({ id: "j", status: "failed", location: "/x" }, { status: 202 })))
  expect(await within(card).findByRole("alert")).toHaveTextContent("We could not check fares right now.")
})

test("Add route records flight_route_added with the real route type", async () => {
  const seen: { event: string; props: Record<string, unknown> }[] = []
  const on = (e: Event) => seen.push((e as CustomEvent).detail)
  window.addEventListener("hermi:event", on)
  mockApi(api({ routes: [], more: (u, i) => (u.endsWith("/trips/t1/routes") && i?.method === "POST" ? Response.json(route(), { status: 201 }) : undefined) }))
  open()
  fireEvent.click(await screen.findByRole("button", { name: "Add a route" }))
  fireEvent.change(screen.getByLabelText("From"), { target: { value: "JFK" } })
  fireEvent.change(screen.getByLabelText("To"), { target: { value: "LIS" } })
  fireEvent.change(screen.getByLabelText("Leave on"), { target: { value: "2027-03-12" } })
  fireEvent.click(screen.getByRole("button", { name: "Add route" }))
  await waitFor(() => expect(seen.some((s) => s.event === "flight_route_added")).toBe(true))
  window.removeEventListener("hermi:event", on)
  expect(seen.find((s) => s.event === "flight_route_added")?.props.route_type).toBe("one_way")
})

test("a Free user entering 3 airports is told the plan cap and nothing is posted", async () => {
  const f = mockApi(api({ routes: [], more: (u) => (u.endsWith("/v1/me/entitlements") ? Response.json({ limits: { airports_per_side: 2 }, trip_passes: [] }) : undefined) }))
  open()
  fireEvent.click(await screen.findByRole("button", { name: "Add a route" }))
  fireEvent.change(screen.getByLabelText("From"), { target: { value: "JFK, EWR, LGA" } })
  fireEvent.change(screen.getByLabelText("To"), { target: { value: "LIS" } })
  fireEvent.change(screen.getByLabelText("Leave on"), { target: { value: "2027-03-12" } })
  await waitFor(() => expect(f.mock.calls.some(([u]) => String(u).endsWith("/v1/me/entitlements"))).toBe(true))
  fireEvent.click(screen.getByRole("button", { name: "Add route" }))
  expect(await screen.findByText("Use at most 2 airports on each side.")).toBeInTheDocument()
  expect(called(f, "POST", "/trips/t1/routes")).toBe(false)
})
