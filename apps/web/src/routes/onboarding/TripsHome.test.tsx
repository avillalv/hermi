import { fireEvent, screen, waitFor } from "@testing-library/react"
import { afterEach, beforeEach, expect, test, vi } from "vitest"
import { TripsHome } from "./TripsHome"
import { ONBOARDED_KEY } from "./trips"
import { mockApi, reset, show } from "./testing"

const trip = { id: "t1", name: "Lisbon, March", status: "planning", start_date: "2027-03-12", end_date: "2027-03-19", destinations_label: "Lisbon, Portugal", member_count: 2 }
const page = (items: unknown[]) => Response.json({ items, next_cursor: null, has_more: false })

beforeEach(() => reset("free"))
afterEach(() => {
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

test("lists trips with name, places and dates", async () => {
  mockApi((u) => (u.endsWith("/v1/trips") ? page([trip]) : undefined))
  show(<TripsHome />, "/")
  expect(await screen.findByText("Lisbon, March")).toBeInTheDocument()
  expect(screen.getByText(/Lisbon, Portugal/)).toBeInTheDocument()
  expect(screen.queryByText("No trips yet")).not.toBeInTheDocument()
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
