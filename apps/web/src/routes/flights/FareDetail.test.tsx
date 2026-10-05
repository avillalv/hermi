import { fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import { MemoryRouter, Route, Routes } from "react-router"
import { afterEach, beforeEach, expect, test, vi } from "vitest"
import { bodyOf, mockApi, reset, show, type Handler } from "../onboarding/testing"
import { FareDetail, toMinor } from "./FareDetail"

const hoursAgo = (h: number) => new Date(Date.now() - h * 3600_000).toISOString()
const fare = (over: Record<string, unknown> = {}) => ({
  id: "f1", route_id: "r1", source: "travelpayouts", confidence: "cached", origin: "JFK", destination: "LIS", depart_date: "2027-03-12",
  return_date: "2027-03-19", price: { amount_minor: 41200, currency: "USD" }, passengers: 2, airlines: ["TP"], stops_out: 0, stops_back: 0,
  duration_out_min: 420, duration_back_min: 440, depart_at_local: "2027-03-12T21:10", source_url: null, observed_at: hoursAgo(3),
  age_label: "cached 3 h ago", suspect: false, hidden: false, ...over,
})
const trip = (role: string) => ({ id: "t1", version: 1, name: "Lisbon", status: "planning", start_date: null, end_date: null, home_currency: "USD", my_role: role, destinations: [], travelers: [] })
const point = (day: string, price: number) => ({ day, source: "travelpayouts", price: { amount_minor: price, currency: "USD" } })
type Over = { role?: string; fares?: unknown[]; points?: unknown[]; chosen?: unknown; more?: Handler }
const api = ({ role = "owner", fares = [fare({ id: "f0", price: { amount_minor: 39000, currency: "USD" } }), fare()], points = [point("2027-01-01", 45000), point("2027-01-02", 41200)], chosen = null, more }: Over = {}): Handler =>
  (u, i) => {
    const m = i?.method ?? "GET"
    const r = more?.(u, i)
    if (r) return r
    if (u.endsWith("/v1/trips/t1") && m === "GET") return Response.json(trip(role))
    if (u.includes("/routes/r1/fares")) return Response.json({ items: fares, next_cursor: null, has_more: false })
    if (u.includes("/flights/summary")) return Response.json([{ route_id: "r1", cheapest: null, last_checked_at: null, fare_count: 2, chosen, chosen_latest: null }])
    if (u.includes("/price-history")) return Response.json({ currency: "USD", google: [], points })
    if (u.includes("/choice") && m === "PUT") return Response.json(trip(role))
    return undefined
  }
const open = (id = "f1") => show(<FareDetail />, "/trips/:id/flights/:routeId/fares/:fareId", `/trips/t1/flights/r1/fares/${id}`)
const price = async () => (await screen.findAllByText("$412"))[0]!
const AIRLINE = "Search on the airline's site, opens in a browser"

beforeEach(() => reset("free"))
afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

test("loading shows a skeleton", () => {
  mockApi(() => new Promise(() => {}) as never)
  const { container } = open()
  expect(container.querySelector(".flights__skel")).toBeInTheDocument()
})

test("error says it could not load and offers a retry", async () => {
  mockApi(() => new Response("{}", { status: 500 }))
  open()
  expect(await screen.findByText("We could not load this fare. Try again.", {}, { timeout: 3000 })).toBeInTheDocument()
  expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument()
})

test("shows the price, its age, the trend as text and no Lowest label on a dearer fare", async () => {
  mockApi(api())
  open()
  expect(await screen.findByRole("heading", { level: 1, name: /^JFK to LIS/ })).toBeInTheDocument()
  expect(await price()).toHaveClass("h-figure")
  expect(screen.getByText("for 2 travelers, economy, at last check 3 h ago")).toBeInTheDocument()
  expect(await screen.findByText(/^Down \$38.* since 1 Jan$/)).toBeInTheDocument()
  expect(screen.queryByText("Lowest in this list")).not.toBeInTheDocument()
})

test("the cheapest fare of the list says Lowest in this list", async () => {
  mockApi(api())
  open("f0")
  expect(await screen.findByText("Lowest in this list")).toBeInTheDocument()
})

test("trend says Up and No change", async () => {
  mockApi(api({ points: [point("2027-01-01", 40000), point("2027-01-02", 41200)] }))
  const a = open()
  expect(await screen.findByText(/^Up \$12/)).toBeInTheDocument()
  a.unmount()
  reset("free")
  mockApi(api({ points: [point("2027-01-01", 41200), point("2027-01-02", 41200)] }))
  open()
  expect(await screen.findByText("No change since 1 Jan")).toBeInTheDocument()
})

test("the chart shows for this route", async () => {
  mockApi(api())
  open()
  expect(await screen.findByRole("table", { name: "Price history data" })).toBeInTheDocument()
})

test("Choose saves the choice and a chosen fare shows Chosen", async () => {
  const f = mockApi(api())
  const a = open()
  fireEvent.click(await screen.findByRole("button", { name: "Choose this fare" }))
  await waitFor(() => expect(bodyOf(f, "/routes/r1/choice")).toEqual({ fare_id: "f1" }))
  a.unmount()
  reset("free")
  mockApi(api({ chosen: fare() }))
  open()
  expect(await screen.findByText("Chosen")).toBeInTheDocument()
})

test("Mark as booked asks what you paid, sends it, then shows Booked and Plan your days", async () => {
  const f = mockApi(api())
  open()
  fireEvent.click(await screen.findByRole("button", { name: "Mark as booked" }))
  const dialog = await screen.findByRole("group", { name: "What did you pay?" })
  fireEvent.change(within(dialog).getByLabelText("Total for 2 travelers"), { target: { value: "480.00" } })
  fireEvent.click(within(dialog).getByRole("button", { name: "Save" }))
  expect(await screen.findByText("Booked")).toBeInTheDocument()
  const body = bodyOf(f, "/routes/r1/choice") as { fare_id: string; paid: unknown; booked_at: string }
  expect(body.fare_id).toBe("f1")
  expect(body.paid).toEqual({ amount_minor: 48000, currency: "USD" })
  expect(body.booked_at).toBeTruthy()
  expect(screen.getByRole("link", { name: "Plan your days" })).toHaveAttribute("href", "/trips/t1")
})

test("Skip marks booked without an amount, and a bad amount is refused", async () => {
  const f = mockApi(api())
  open()
  fireEvent.click(await screen.findByRole("button", { name: "Mark as booked" }))
  const dialog = await screen.findByRole("group", { name: "What did you pay?" })
  fireEvent.change(within(dialog).getByLabelText("Total for 2 travelers"), { target: { value: "abc" } })
  fireEvent.click(within(dialog).getByRole("button", { name: "Save" }))
  expect(await within(dialog).findByText("Enter the amount as a number, like 480.00.")).toBeInTheDocument()
  fireEvent.click(within(dialog).getByRole("button", { name: "Skip" }))
  expect(await screen.findByText("Booked")).toBeInTheDocument()
  expect((bodyOf(f, "/routes/r1/choice") as { paid?: unknown }).paid).toBeUndefined()
})

test("a failed save keeps the sheet open with an error", async () => {
  mockApi(api({ more: (u, i) => (u.includes("/choice") && i?.method === "PUT" ? new Response("{}", { status: 500 }) : undefined) }))
  open()
  fireEvent.click(await screen.findByRole("button", { name: "Mark as booked" }))
  fireEvent.click(within(await screen.findByRole("group", { name: "What did you pay?" })).getByRole("button", { name: "Skip" }))
  expect(await screen.findByText("We could not save that. Try again.")).toBeInTheDocument()
  expect(screen.queryByText("Booked")).not.toBeInTheDocument()
})

test("a viewer sees the fare without Choose or Mark as booked", async () => {
  mockApi(api({ role: "viewer" }))
  open()
  await price()
  expect(await screen.findByText("You can view this fare. Ask an editor to choose it.")).toBeInTheDocument()
  expect(screen.queryByRole("button", { name: "Choose this fare" })).not.toBeInTheDocument()
  expect(screen.queryByRole("button", { name: "Mark as booked" })).not.toBeInTheDocument()
})

test("a stale fare (over 24 h) shows the warning line", async () => {
  mockApi(api({ fares: [fare({ observed_at: hoursAgo(50) })] }))
  open()
  expect(await screen.findByText("This price was last seen 2 d ago.")).toBeInTheDocument()
})

test("offline: Book buttons are disabled with the reason, and the saved fare shows", async () => {
  vi.spyOn(navigator, "onLine", "get").mockReturnValue(false)
  mockApi(api())
  open()
  expect(await price()).toBeInTheDocument()
  expect(screen.getByText("Connect to the internet to book.")).toBeInTheDocument()
  expect(screen.getByRole("button", { name: AIRLINE })).toBeDisabled()
  expect(screen.getByRole("button", { name: "Mark as booked" })).toBeDisabled()
})

test("Book this fare lists only the airline when there is no partner price, with the sort line", async () => {
  mockApi(api({ fares: [fare({ airline_search_url: "https://www.google.com/travel/flights?q=x" })] }))
  open()
  expect(await screen.findByText("Sorted by price, lowest first")).toBeInTheDocument()
  expect(screen.getByText("We do not have a partner price for this fare. You can search on the airline's site.")).toBeInTheDocument()
  expect(screen.getByRole("link", { name: AIRLINE })).toHaveAttribute("href", "https://www.google.com/travel/flights?q=x")
})

test("an unknown fare id says it is gone", async () => {
  mockApi(api())
  open("nope")
  expect(await screen.findByRole("alert")).toHaveTextContent("This fare is not on the route any more")
})

test("toMinor parses amounts in the currency's own digits", () => {
  expect(toMinor("480.00", "USD")).toBe(48000)
  expect(toMinor("1,480.5", "USD")).toBe(148050)
  expect(toMinor("5000", "JPY")).toBe(5000)
  expect(toMinor("5000.5", "JPY")).toBeNull()
  expect(toMinor("0", "USD")).toBeNull()
  expect(toMinor("-3", "USD")).toBeNull()
})

test("a booking fires fare_marked_booked with price_entered", async () => {
  const track = vi.spyOn(await import("../../lib/track"), "track")
  mockApi(api())
  open()
  fireEvent.click(await screen.findByRole("button", { name: "Mark as booked" }))
  fireEvent.click(within(await screen.findByRole("group", { name: "What did you pay?" })).getByRole("button", { name: "Skip" }))
  await screen.findByText("Booked")
  expect(track).toHaveBeenCalledWith("fare_marked_booked", { price_entered: false })
})

test("Escape closes the sheet and returns focus to Mark as booked", async () => {
  mockApi(api())
  open()
  const mark = await screen.findByRole("button", { name: "Mark as booked" })
  fireEvent.click(mark)
  await screen.findByRole("group", { name: "What did you pay?" })
  fireEvent.keyDown(document, { key: "Escape" })
  await waitFor(() => expect(screen.queryByRole("group", { name: "What did you pay?" })).not.toBeInTheDocument())
  expect(mark).toHaveFocus()
})

test("a non-economy route says its cabin", async () => {
  mockApi(api({ more: (u) => (u.endsWith("/trips/t1/routes") ? Response.json([{ id: "r1", cabin: "business" }]) : undefined) }))
  open()
  expect(await screen.findByText("for 2 travelers, business, at last check 3 h ago")).toBeInTheDocument()
})

test("a fare past the first page comes from the tapped chip", async () => {
  mockApi(api({ fares: [fare({ id: "f0" })] }))
  const entry = { pathname: "/trips/t1/flights/r1/fares/f9", state: { fare: fare({ id: "f9", price: { amount_minor: 99900, currency: "USD" } }) } }
  render(
    <MemoryRouter initialEntries={[entry]}>
      <Routes>
        <Route path="/trips/:id/flights/:routeId/fares/:fareId" element={<FareDetail />} />
      </Routes>
    </MemoryRouter>,
  )
  expect((await screen.findAllByText("$999"))[0]).toHaveClass("h-figure")
})

test("a hidden cheapest fare does not take the Lowest label", async () => {
  mockApi(api({ fares: [fare({ id: "f0", hidden: true, price: { amount_minor: 100, currency: "USD" } }), fare()] }))
  open()
  expect(await screen.findByText("Lowest in this list")).toBeInTheDocument()
})
