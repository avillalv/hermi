import { fireEvent, screen, waitFor, within } from "@testing-library/react"
import { afterEach, beforeEach, expect, test, vi } from "vitest"
import { TripsHome } from "./TripsHome"
import { ONBOARDED_KEY } from "../onboarding/trips"
import { mockApi, reset, show } from "../onboarding/testing"

const trip = { id: "t1", name: "Lisbon, March", status: "planning", start_date: "2027-03-12", end_date: "2027-03-19", destinations_label: "Lisbon, Portugal", member_count: 2, my_role: "owner" }
const page = (items: unknown[]) => Response.json({ items, next_cursor: null, has_more: false })

beforeEach(() => reset("free"))
afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

test("loading shows a status, then the empty state with a New trip link", async () => {
  mockApi((u) => (u.endsWith("/v1/trips") ? page([]) : undefined))
  show(<TripsHome />, "/")
  expect(screen.getByRole("heading", { level: 1, name: "Trips" })).toBeInTheDocument()
  expect(screen.getByText("Loading your trips")).toBeInTheDocument()
  expect(await screen.findByRole("heading", { name: "No trips yet" })).toBeInTheDocument()
  expect(screen.getByText("Start with a place and a few dates. You can change everything later.")).toBeInTheDocument()
  fireEvent.click(screen.getAllByRole("link", { name: "New trip" })[0])
  await waitFor(() => expect(screen.getByTestId("where")).toHaveTextContent("/trips/new"))
})

const at = (iso: string) => vi.useFakeTimers({ toFake: ["Date"], now: new Date(`${iso}T12:00:00`) })
const mk = (id: string, name: string, over: Record<string, unknown> = {}) => ({ ...trip, id, name, ...over })

test("a trip card is one link with a combined label, the name as a heading and the status", async () => {
  at("2027-01-01")
  mockApi((u) => (u.endsWith("/v1/trips") ? page([trip]) : undefined))
  show(<TripsHome />, "/")
  const card = await screen.findByRole("link", { name: /^Lisbon, March, Mar 12 to 19, 2027, 2 travelers, Planning$/ })
  expect(card).toHaveAttribute("href", "/trips/t1")
  expect(screen.getByRole("heading", { level: 3, name: "Lisbon, March" })).toBeInTheDocument()
  expect(within(card).getByText("Planning")).toBeInTheDocument()
  expect(within(card).getByText(/In 2 months/)).toBeInTheDocument()
  expect(screen.queryByText("No trips yet")).not.toBeInTheDocument()
})

test("trips are grouped into In progress, Upcoming, Shared with me and Past, sorted by date", async () => {
  at("2027-03-15")
  const items = [
    mk("p1", "Old one", { status: "done", start_date: "2026-08-14", end_date: "2026-08-18" }),
    mk("p2", "Newer past", { status: "archived", start_date: "2026-12-01", end_date: "2026-12-05" }),
    mk("u2", "Later", { start_date: "2027-09-01", end_date: "2027-09-08" }),
    mk("u1", "Sooner", { start_date: "2027-06-01", end_date: "2027-06-08" }),
    mk("u0", "Undated", { start_date: null, end_date: null }),
    mk("n1", "Right now", { start_date: "2027-03-12", end_date: "2027-03-19", status: "booked" }),
    mk("s1", "Friend trip", { my_role: "viewer", start_date: "2027-07-01", end_date: "2027-07-05" }),
  ]
  mockApi((u) => (u.endsWith("/v1/trips") ? page(items) : undefined))
  show(<TripsHome />, "/")
  await screen.findByText("Right now")
  const names = (h: string) => within(screen.getByRole("region", { name: h })).getAllByRole("heading", { level: 3 }).map((x) => x.textContent)
  expect(names("In progress")).toEqual(["Right now"])
  expect(names("Upcoming")).toEqual(["Sooner", "Later", "Undated"])
  expect(names("Shared with me")).toEqual(["Friend trip"])
  expect(names("Past")).toEqual(["Newer past", "Old one"])
  const now = screen.getByRole("link", { name: /Right now.*Happening now/ })
  expect(within(now).getByText("Happening now")).toBeInTheDocument()
  expect(within(now).getByText("Day 4 of 8")).toBeInTheDocument()
})

test("a section with no trips is not shown", async () => {
  at("2027-01-01")
  mockApi((u) => (u.endsWith("/v1/trips") ? page([trip]) : undefined))
  show(<TripsHome />, "/")
  await screen.findByText("Lisbon, March")
  expect(screen.getByRole("region", { name: "Upcoming" })).toBeInTheDocument()
  for (const h of ["In progress", "Past", "Shared with me"]) expect(screen.queryByRole("region", { name: h })).not.toBeInTheDocument()
})

test("a trip without dates says so", async () => {
  mockApi((u) => (u.endsWith("/v1/trips") ? page([mk("u0", "Undated", { start_date: null, end_date: null })]) : undefined))
  show(<TripsHome />, "/")
  expect(await screen.findByRole("link", { name: /^Undated, No dates yet, 2 travelers, Planning$/ })).toBeInTheDocument()
})

test("a load error shows the message and Try again reloads", async () => {
  let n = 0
  const f = mockApi((u) => (u.endsWith("/v1/trips") ? (n++ < 2 ? new Response("{}", { status: 500 }) : page([trip])) : undefined))
  show(<TripsHome />, "/")
  expect(await screen.findByRole("alert", {}, { timeout: 3000 })).toHaveTextContent("We could not load your trips. Try again.")
  fireEvent.click(screen.getByRole("button", { name: "Try again" }))
  expect(await screen.findByText("Lisbon, March")).toBeInTheDocument()
  expect(f).toHaveBeenCalledTimes(3)
})

test("offline shows the offline banner", async () => {
  vi.spyOn(navigator, "onLine", "get").mockReturnValue(false)
  mockApi((u) => (u.endsWith("/v1/trips") ? page([trip]) : undefined))
  show(<TripsHome />, "/")
  expect(screen.getByRole("status")).toHaveTextContent("You are offline. Showing your saved trips.")
})

const me = (status: number) => (u: string) =>
  u.endsWith("/v1/me") ? new Response("{}", { status }) : u.endsWith("/v1/trips") ? page([]) : undefined

test("a new real-provider sign-in (GET /me is 401) is sent to onboarding", async () => {
  reset()
  mockApi(me(401))
  show(<TripsHome />, "/")
  await waitFor(() => expect(screen.getByText("elsewhere")).toBeInTheDocument())
  expect(screen.getByTestId("where")).toHaveTextContent("/onboarding")
})

test("an existing real-provider user (GET /me is 200) stays on Trips and is not asked again", async () => {
  reset()
  mockApi(me(200))
  show(<TripsHome />, "/")
  expect(await screen.findByRole("heading", { name: "No trips yet" })).toBeInTheDocument()
  expect(screen.getByTestId("where")).toHaveTextContent(/^\/$/)
  expect(sessionStorage.getItem(ONBOARDED_KEY)).toBe("1")
})

test("loading shows three skeleton cards", () => {
  mockApi(() => new Promise(() => {}) as never)
  const { container } = show(<TripsHome />, "/")
  expect(container.querySelectorAll(".trips__skel")).toHaveLength(3)
})
