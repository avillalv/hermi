import { fireEvent, screen, waitFor, within } from "@testing-library/react"
import { afterEach, beforeEach, expect, test, vi } from "vitest"
import { bodyOf, mockApi, reset, show, type Handler } from "../onboarding/testing"
import { FareDetail } from "./FareDetail"
import { Flights } from "./Flights"

const now = new Date(Date.now() - 3 * 3600_000).toISOString()
const route = { id: "r1", trip_id: "t1", label: null, origin_codes: ["JFK"], destination_codes: ["LIS"], trip_type: "round_trip", depart_from: "2027-03-12", depart_to: "2027-03-12", return_from: "2027-03-19", return_to: "2027-03-19", adults: 1, children: 0, cabin: "economy", mode: "cached", version: 1, last_checked_at: now }
const fare = { id: "f1", route_id: "r1", source: "travelpayouts", confidence: "cached", origin: "JFK", destination: "LIS", depart_date: "2027-03-12", return_date: "2027-03-19", price: { amount_minor: 41200, currency: "USD" }, passengers: 1, airlines: ["TP"], stops_out: 0, stops_back: 0, duration_out_min: 420, depart_at_local: "2027-03-12T21:10", source_url: null, observed_at: now, age_label: "cached 3 h ago", suspect: false, hidden: false }
const alert = (over: Record<string, unknown> = {}) => ({ id: "a1", route_id: "r1", target_price: { amount_minor: 40000, currency: "USD" }, notify: { push: true, email: false }, active: true, last_notified_at: null, last_notified_price: null, ...over })
const trip = (role: string) => ({ id: "t1", version: 1, name: "Lisbon", status: "planning", start_date: null, end_date: null, home_currency: "USD", my_role: role, destinations: [], travelers: [] })

type Over = { role?: string; tier?: string; alerts?: unknown[] | "error" | "slow"; more?: Handler }
const api = ({ role = "owner", tier = "free", alerts = [], more }: Over = {}): Handler => (u, i) => {
  const m = i?.method ?? "GET"
  const r = more?.(u, i)
  if (r) return r
  if (u.endsWith("/me/entitlements")) return Response.json({ tier, limits: { airports_per_side: 2 } })
  if (u.endsWith("/v1/trips/t1") && m === "GET") return Response.json(trip(role))
  if (u.endsWith("/trips/t1/price-alerts")) return alerts === "error" ? new Response("{}", { status: 500 }) : alerts === "slow" ? (new Promise(() => {}) as never) : Response.json(alerts)
  if (u.endsWith("/trips/t1/routes") && m === "GET") return Response.json([route])
  if (u.includes("/routes/r1/fares")) return Response.json({ items: [fare], next_cursor: null, has_more: false })
  if (u.includes("/flights/summary")) return Response.json([{ route_id: "r1", cheapest: fare, last_checked_at: now, fare_count: 1, chosen: null, chosen_latest: null }])
  if (u.includes("/flights/best")) return Response.json([fare])
  if (u.includes("/price-history")) return Response.json({ currency: "USD", google: [], points: [] })
  if (u.includes("/date-grid")) return Response.json([])
  return undefined
}
const detail = () => show(<FareDetail />, "/trips/:id/flights/:routeId/fares/:fareId", "/trips/t1/flights/r1/fares/f1")
const list = () => show(<Flights />, "/trips/:id/flights", "/trips/t1/flights")
const AMOUNT = "Alert me when the lowest fare is below"

beforeEach(() => reset("free"))
afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

test("the alert switch on Fare detail is off, and turning it on opens the sheet; Save creates the alert", async () => {
  let made = false
  const f = mockApi(api({ more: (u, i) => (u.endsWith("/routes/r1/price-alerts") && i?.method === "POST" ? ((made = true), Response.json(alert(), { status: 201 })) : undefined) }))
  detail()
  const sw = await screen.findByRole("switch", { name: "Alert me when it drops" })
  expect(sw).toHaveAttribute("aria-checked", "false")
  fireEvent.click(sw)
  const sheet = await screen.findByRole("group", { name: "Price alert" })
  fireEvent.change(within(sheet).getByLabelText(AMOUNT), { target: { value: "400.00" } })
  fireEvent.click(within(sheet).getByRole("button", { name: "Save alert" }))
  await waitFor(() => expect(made).toBe(true))
  expect(bodyOf(f, "/routes/r1/price-alerts")).toEqual({ target_price: { amount_minor: 40000, currency: "USD" }, notify: { push: true, email: false } })
  await waitFor(() => expect(screen.queryByRole("group", { name: "Price alert" })).not.toBeInTheDocument())
})

test("a bad amount is refused and nothing is sent", async () => {
  const f = mockApi(api())
  detail()
  fireEvent.click(await screen.findByRole("switch", { name: "Alert me when it drops" }))
  const sheet = await screen.findByRole("group", { name: "Price alert" })
  fireEvent.change(within(sheet).getByLabelText(AMOUNT), { target: { value: "abc" } })
  fireEvent.click(within(sheet).getByRole("button", { name: "Save alert" }))
  expect(await within(sheet).findByText("Enter the amount as a number, like 400.00.")).toBeInTheDocument()
  expect(f.mock.calls.some(([, i]) => (i as RequestInit | undefined)?.method === "POST")).toBe(false)
})

test("with an alert the switch is on and shows the target; the switch turns it off, Edit then Delete removes it", async () => {
  const f = mockApi(
    api({
      alerts: [alert()],
      more: (u, i) => (u.endsWith("/price-alerts/a1") ? (i?.method === "DELETE" ? new Response(null, { status: 204 }) : Response.json(alert({ active: false }))) : undefined),
    }),
  )
  detail()
  const sw = await screen.findByRole("switch", { name: "Alert me when it drops" })
  await waitFor(() => expect(sw).toHaveAttribute("aria-checked", "true"))
  expect(screen.getByText("Below $400")).toBeInTheDocument()
  fireEvent.click(sw)
  await waitFor(() => expect(bodyOf(f, "/price-alerts/a1")).toEqual({ active: false }))
  fireEvent.click(screen.getByRole("button", { name: "Edit alert" }))
  const sheet = await screen.findByRole("group", { name: "Price alert" })
  expect(within(sheet).getByLabelText(AMOUNT)).toHaveValue("400.00")
  fireEvent.click(within(sheet).getByRole("button", { name: "Delete alert" }))
  await waitFor(() => expect(f.mock.calls.some(([u, i]) => String(u).endsWith("/price-alerts/a1") && (i as RequestInit).method === "DELETE")).toBe(true))
})

const limit = (trigger: string) => (u: string, i?: RequestInit) =>
  u.endsWith("/routes/r1/price-alerts") && i?.method === "POST" ? Response.json({ code: "limit_reached", detail: "You can have 3 price alerts on your plan.", paywall: { trigger } }, { status: 402 }) : undefined
const trySave = async () => {
  fireEvent.click(await screen.findByRole("switch", { name: "Alert me when it drops" }))
  const sheet = await screen.findByRole("group", { name: "Price alert" })
  fireEvent.change(within(sheet).getByLabelText(AMOUNT), { target: { value: "400" } })
  fireEvent.click(within(sheet).getByRole("button", { name: "Save alert" }))
  return sheet
}

test("the limit error on Free shows the upgrade path and the free path, with no dashes", async () => {
  mockApi(api({ more: limit("alert_limit") }))
  detail()
  const sheet = await trySave()
  const msg = await within(sheet).findByRole("alert")
  expect(msg).toHaveTextContent("Free plans include 1 price alert.")
  expect(msg.textContent).not.toMatch(new RegExp(String.fromCharCode(91, 0x2013, 0x2014, 93)))
  expect(within(sheet).getByRole("link", { name: "See plans" })).toHaveAttribute("href", "/account")
  expect(within(sheet).getByRole("button", { name: "Keep my one alert" })).toBeInTheDocument()
})

test("a limit on Plus shows the server message with no upsell", async () => {
  mockApi(api({ tier: "plus", more: limit("alert_limit") }))
  detail()
  const sheet = await trySave()
  expect(await within(sheet).findByRole("alert")).toHaveTextContent("You can have 3 price alerts on your plan.")
  expect(within(sheet).queryByRole("link", { name: "See plans" })).not.toBeInTheDocument()
  expect(within(sheet).queryByRole("button", { name: "Keep my one alert" })).not.toBeInTheDocument()
})

test("a 409 says you already have an alert on this route", async () => {
  mockApi(api({ more: (u, i) => (u.endsWith("/routes/r1/price-alerts") && i?.method === "POST" ? Response.json({ code: "state_conflict" }, { status: 409 }) : undefined) }))
  detail()
  const sheet = await trySave()
  expect(await within(sheet).findByRole("alert")).toHaveTextContent("You already have a price alert on this route. Change that one instead.")
})

test("Save records fare_alert_created with kind cached", async () => {
  const seen: { event: string; props: Record<string, unknown> }[] = []
  const on = (e: Event) => seen.push((e as CustomEvent).detail)
  window.addEventListener("hermi:event", on)
  mockApi(api({ more: (u, i) => (u.endsWith("/routes/r1/price-alerts") && i?.method === "POST" ? Response.json(alert(), { status: 201 }) : undefined) }))
  detail()
  await trySave()
  await waitFor(() => expect(seen.find((e) => e.event === "fare_alert_created")?.props).toEqual({ kind: "cached" }))
  window.removeEventListener("hermi:event", on)
})

test("Edit then Save sends the new target in a PATCH", async () => {
  const f = mockApi(api({ alerts: [alert()], more: (u, i) => (u.endsWith("/price-alerts/a1") && i?.method === "PATCH" ? Response.json(alert()) : undefined) }))
  detail()
  fireEvent.click(await screen.findByRole("button", { name: "Edit alert" }))
  const sheet = await screen.findByRole("group", { name: "Price alert" })
  fireEvent.change(within(sheet).getByLabelText(AMOUNT), { target: { value: "350.50" } })
  fireEvent.click(within(sheet).getByRole("button", { name: "Save alert" }))
  await waitFor(() => expect(bodyOf(f, "/price-alerts/a1")).toEqual({ target_price: { amount_minor: 35050, currency: "USD" }, notify: { push: true, email: false } }))
})

test("a failed toggle says it could not save", async () => {
  mockApi(api({ alerts: [alert()], more: (u, i) => (u.endsWith("/price-alerts/a1") && i?.method === "PATCH" ? new Response("{}", { status: 500 }) : undefined) }))
  detail()
  const sw = await screen.findByRole("switch", { name: "Alert me when it drops" })
  await waitFor(() => expect(sw).toBeEnabled())
  fireEvent.click(sw)
  expect(await screen.findByText("We could not save that alert. Try again.")).toBeInTheDocument()
})

test("the switch waits for the alerts and shows an error with Try again when they fail", async () => {
  mockApi(api({ alerts: "error" }))
  detail()
  expect(await screen.findByRole("switch", { name: "Alert me when it drops" })).toBeDisabled()
  expect(await screen.findByText("We could not load alerts. Try again.", {}, { timeout: 3000 })).toBeInTheDocument()
})

test("a viewer sees no alert controls and offline disables the switch", async () => {
  mockApi(api({ role: "viewer" }))
  const a = detail()
  await screen.findByText("You can view this fare. Ask an editor to choose it.")
  expect(screen.queryByRole("switch")).not.toBeInTheDocument()
  a.unmount()
  reset("free")
  mockApi(api())
  vi.spyOn(navigator, "onLine", "get").mockReturnValue(false)
  detail()
  expect(await screen.findByRole("switch", { name: "Alert me when it drops" })).toBeDisabled()
})

test("the alert list on Flights shows loading, empty, error with retry, and existing alerts", async () => {
  mockApi(api({ alerts: "slow" }))
  const a = list()
  expect(await screen.findByText("Loading alerts")).toBeInTheDocument()
  a.unmount()
  reset("free")
  mockApi(api())
  const b = list()
  expect(await screen.findByText("No price alerts yet. Turn on the alert on a route to get one.")).toBeInTheDocument()
  b.unmount()
  reset("free")
  mockApi(api({ alerts: "error" }))
  const c = list()
  expect((await screen.findAllByText("We could not load alerts. Try again.", {}, { timeout: 3000 })).length).toBeGreaterThan(0)
  expect(screen.getAllByRole("button", { name: "Try again" }).length).toBeGreaterThan(0)
  c.unmount()
  reset("free")
  mockApi(api({ alerts: [alert()] }))
  list()
  const item = await screen.findByRole("listitem", { name: /JFK to LIS/ })
  expect(item).toHaveTextContent("Below $400")
  expect(item).toHaveTextContent("On")
})
