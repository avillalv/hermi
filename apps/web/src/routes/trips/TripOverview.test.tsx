import { fireEvent, screen, within } from "@testing-library/react"
import { afterEach, beforeEach, expect, test, vi } from "vitest"
import { queryClient } from "../../lib/queryClient"
import { mockApi, reset, show } from "../onboarding/testing"
vi.mock("../../components/sync-indicator/SyncIndicator", () => ({ SyncIndicator: () => null }))
import { TripOverview } from "./TripOverview"

const tokyo = { id: "d1", position: 0, name: "Tokyo", region: null, country: "Japan", timezone: "Asia/Tokyo" }
const trip = {
  id: "t1",
  name: "Japan in spring",
  status: "planning",
  start_date: "2027-03-12",
  end_date: "2027-03-19",
  home_currency: "USD",
  my_role: "owner",
  destinations: [tokyo],
}
const route = (t: unknown, status = 200) => (u: string) => (u.endsWith("/v1/trips/t1") ? Response.json(t, { status }) : undefined)
const open = () => show(<TripOverview />, "/trips/:id", "/trips/t1")
// 12:00 UTC on 15 March: day 4 of 8 for the trip, 9 PM in Tokyo.
const now = (iso = "2027-03-15T12:00:00Z") => vi.useFakeTimers({ toFake: ["Date"], now: new Date(iso) })

beforeEach(() => reset("free"))
afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

test("loading shows a status and a skeleton block", async () => {
  mockApi(() => new Promise(() => {}) as never)
  const { container } = open()
  expect(await screen.findByRole("status", { name: "Loading" })).toBeInTheDocument()
  expect(container.querySelectorAll(".state-card")).toHaveLength(5)
})

test("the hero pass names the trip as the one h1, with dates, nights and the status stub", async () => {
  now("2027-01-01T12:00:00Z")
  mockApi(route(trip))
  open()
  expect(await screen.findByRole("heading", { level: 1, name: "Japan in spring" })).toBeInTheDocument()
  expect(screen.getByText("Mar 12 to 19, 2027")).toBeInTheDocument()
  expect(screen.getByText("Tokyo")).toBeInTheDocument()
  expect(screen.getByText("Planning")).toBeInTheDocument()
  expect(screen.getByText(/In 2 months/)).toBeInTheDocument()
  expect(within(screen.getByRole("main")).getByRole("link", { name: "Trips" })).toHaveAttribute("href", "/")
  expect(screen.queryByRole("region", { name: "Happening now" })).not.toBeInTheDocument()
})

test("Happening now shows during the trip dates: day, local time at the destination and an empty today", async () => {
  now()
  mockApi(route(trip))
  open()
  const card = await screen.findByRole("region", { name: "Happening now" })
  expect(within(card).getByText("Day 4 of 8")).toBeInTheDocument()
  expect(within(card).getByText("Local time in Tokyo")).toBeInTheDocument()
  expect(within(card).getByText(/9:00\s?PM/)).toBeInTheDocument()
  expect(within(card).getByText("Nothing planned for today")).toBeInTheDocument()
  expect(within(card).getByRole("link", { name: "Plan today" })).toHaveAttribute("href", "/trips/t1/plan")
  // it sits above Next steps
  const regions = screen.getAllByRole("region").map((r) => r.getAttribute("aria-labelledby") && r.textContent)
  expect(regions[0]).toMatch(/^Happening now/)
})

test("Happening now has no local time when the destination has no time zone", async () => {
  now()
  mockApi(route({ ...trip, destinations: [{ ...tokyo, timezone: null }] }))
  open()
  const card = await screen.findByRole("region", { name: "Happening now" })
  expect(within(card).queryByText(/Local time/)).not.toBeInTheDocument()
})

test.each([
  ["a past trip", { start_date: "2026-03-12", end_date: "2026-03-19" }],
  ["an archived trip", { status: "archived" }],
])("%s does not show Happening now", async (_, over) => {
  now()
  mockApi(route({ ...trip, ...over }))
  open()
  await screen.findByRole("heading", { level: 1 })
  expect(screen.queryByRole("region", { name: "Happening now" })).not.toBeInTheDocument()
})

test("Next steps come from missing data and link to where each is fixed", async () => {
  now("2027-01-01T12:00:00Z")
  mockApi(route({ ...trip, start_date: null, end_date: null, destinations: [] }))
  open()
  const steps = await screen.findByRole("region", { name: "Next steps" })
  expect(within(steps).getByRole("link", { name: "Pick your dates" })).toHaveAttribute("href", "/trips/t1/edit")
  expect(within(steps).getByRole("link", { name: "Add a destination" })).toBeInTheDocument()
  expect(within(steps).queryByRole("link", { name: "Plan your first day" })).not.toBeInTheDocument()
  expect(screen.getByText("No destination yet")).toBeInTheDocument()
  expect(screen.getByText("No dates yet")).toBeInTheDocument()
})

test("with dates and a destination the next step is to plan the first day", async () => {
  now("2027-01-01T12:00:00Z")
  mockApi(route(trip))
  open()
  const steps = await screen.findByRole("region", { name: "Next steps" })
  expect(within(steps).getAllByRole("link")).toHaveLength(1)
  expect(within(steps).getByRole("link", { name: "Plan your first day" })).toHaveAttribute("href", "/trips/t1/plan")
})

test("a viewer does not see Next steps", async () => {
  now("2027-01-01T12:00:00Z")
  mockApi(route({ ...trip, my_role: "viewer" }))
  open()
  await screen.findByRole("heading", { level: 1 })
  expect(screen.queryByRole("region", { name: "Next steps" })).not.toBeInTheDocument()
})

test("a load error shows a block retry that reloads", async () => {
  let n = 0
  const f = mockApi((u) => (u.endsWith("/v1/trips/t1") ? (n++ < 2 ? new Response("{}", { status: 500 }) : Response.json(trip)) : undefined))
  open()
  expect(await screen.findByRole("alert", {}, { timeout: 3000 })).toHaveTextContent("We could not load this trip. Try again.")
  fireEvent.click(screen.getByRole("button", { name: "Try again" }))
  expect(await screen.findByRole("heading", { level: 1, name: "Japan in spring" })).toBeInTheDocument()
  expect(f.mock.calls.filter(([u]) => String(u).endsWith("/v1/trips/t1"))).toHaveLength(3)
})

test("a missing trip says so, without a retry", async () => {
  mockApi(route({}, 404))
  open()
  expect(await screen.findByRole("alert")).toHaveTextContent("This trip is not available.")
  expect(screen.queryByRole("button", { name: "Try again" })).not.toBeInTheDocument()
  expect(within(screen.getByRole("main")).getByRole("link", { name: "Trips" })).toBeInTheDocument()
})

test("offline shows the saved-trip banner", async () => {
  vi.spyOn(navigator, "onLine", "get").mockReturnValue(false)
  mockApi(route(trip))
  open()
  expect(screen.getByRole("status")).toHaveTextContent("You are offline. Showing your saved trip.")
})

test("Plan with AI opens the AI sheet route for every role", async () => {
  mockApi(route({ ...trip, my_role: "viewer" }))
  open()
  const link = await screen.findByRole("link", { name: "Plan with AI" })
  expect(link).toHaveAttribute("href", "/trips/t1/ai")
})

test("the deep run entry card shows for an editor and not for a viewer", async () => {
  const taster = { used: false, used_at: null, run_id: null, available: true, credits: 40 }
  const withTaster = (t: object) => (u: string) => (u.endsWith("/v1/me/agent-taster") ? Response.json(taster) : route(t)(u))
  mockApi(withTaster({ ...trip, my_role: "editor" }))
  const { unmount } = open()
  expect(await screen.findByRole("heading", { name: "Try a deep run, free once" })).toBeInTheDocument()
  unmount()
  queryClient.clear() // the cached trip is the editor one
  mockApi(withTaster({ ...trip, my_role: "viewer" }))
  open()
  await screen.findByRole("heading", { level: 1 })
  expect(screen.queryByRole("heading", { name: "Try a deep run, free once" })).toBeNull()
})
