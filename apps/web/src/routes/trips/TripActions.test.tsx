import { fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import { MemoryRouter, Route, Routes, useLocation } from "react-router"
import { afterEach, beforeEach, expect, test, vi } from "vitest"
import { mockApi, reset, show } from "../onboarding/testing"
import { TripOverview } from "./TripOverview"
import { TripsHome } from "./TripsHome"

const row = (over: Record<string, unknown> = {}) => ({ id: "t1", version: 2, name: "Lisbon, March", status: "planning", start_date: "2027-03-12", end_date: "2027-03-19", destinations_label: "Lisbon", member_count: 1, my_role: "owner", ...over })
const page = (items: unknown[]) => Response.json({ items, next_cursor: null, has_more: false })
const full = (over: Record<string, unknown> = {}) => ({ ...row(), home_currency: "USD", destinations: [], ...over })

beforeEach(() => reset("free"))
afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

const isGet = (i?: RequestInit) => !i?.method || i.method === "GET"
const call = (f: ReturnType<typeof mockApi>, method: string, suffix: string) =>
  f.mock.calls.find(([u, i]) => String(u).endsWith(suffix) && (i as RequestInit | undefined)?.method === method)
const bodyJson = (c: unknown[] | undefined) => JSON.parse(String((c![1] as RequestInit).body))

test("Trips home: an owner archives a past trip, then duplicates it into a new trip that appears in Trips (smoke 26)", async () => {
  vi.useFakeTimers({ toFake: ["Date"], now: new Date("2027-06-01T12:00:00") })
  let items = [row({ status: "done", start_date: "2027-03-12", end_date: "2027-03-19" })]
  const f = mockApi((u, init) => {
    if (u.endsWith("/v1/trips") && isGet(init)) return page(items)
    if (u.endsWith("/v1/trips/t1") && init?.method === "PATCH") {
      items = [{ ...items[0], status: "archived" }]
      return Response.json(full({ status: "archived" }))
    }
    if (u.endsWith("/v1/trips/t1/duplicate")) {
      items = [...items, row({ id: "t2", name: "Lisbon, March (copy)", start_date: null, end_date: null })]
      return Response.json(full({ id: "t2" }), { status: 201 })
    }
  })
  show(<TripsHome />, "/")
  fireEvent.click(await screen.findByRole("button", { name: "Actions for Lisbon, March" }))
  fireEvent.click(screen.getByRole("button", { name: "Archive" }))
  expect(await screen.findByRole("status")).toHaveTextContent("Archived Lisbon, March.")
  expect(bodyJson(call(f, "PATCH", "/v1/trips/t1"))).toEqual({ status: "archived", version: 2 })
  fireEvent.click(await screen.findByRole("button", { name: "Duplicate" }))
  expect(await screen.findByText("Lisbon, March (copy)")).toBeInTheDocument()
  expect(call(f, "POST", "/v1/trips/t1/duplicate")).toBeDefined()
})

test("an archived trip can be unarchived, and the Free limit shows the archive-first message", async () => {
  let status = 402
  const f = mockApi((u, init) => {
    if (u.endsWith("/v1/trips") && isGet(init)) return page([row({ status: "archived" })])
    if (init?.method === "PATCH") return status === 402 ? new Response("{}", { status }) : Response.json(full())
  })
  show(<TripsHome />, "/")
  fireEvent.click(await screen.findByRole("button", { name: "Actions for Lisbon, March" }))
  fireEvent.click(screen.getByRole("button", { name: "Unarchive" }))
  expect(await screen.findByRole("alert")).toHaveTextContent("You have 2 active trips. Archive one to make room, or upgrade.")
  expect(bodyJson(call(f, "PATCH", "/v1/trips/t1"))).toEqual({ status: "planning", version: 2 })
  status = 200
  fireEvent.click(screen.getByRole("button", { name: "Unarchive" }))
  expect(await screen.findByRole("status")).toHaveTextContent("Moved Lisbon, March back to your trips.")
})

test("move to trash shows an undo, and Undo restores the trip", async () => {
  let items = [row()]
  const f = mockApi((u, init) => {
    if (u.endsWith("/v1/trips") && isGet(init)) return page(items)
    if (u.endsWith("/v1/trips/t1") && init?.method === "DELETE") {
      items = []
      return new Response(null, { status: 204 })
    }
    if (u.endsWith("/v1/trips/t1/restore")) {
      items = [row()]
      return Response.json(full())
    }
  })
  show(<TripsHome />, "/")
  fireEvent.click(await screen.findByRole("button", { name: "Actions for Lisbon, March" }))
  fireEvent.click(screen.getByRole("button", { name: "Move to trash" }))
  expect(await screen.findByRole("status")).toHaveTextContent("Moved Lisbon, March to trash. You can restore it for 30 days.")
  expect(screen.queryByRole("link", { name: /Lisbon, March/ })).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole("button", { name: "Undo" }))
  expect(await screen.findByRole("link", { name: /Lisbon, March/ })).toBeInTheDocument()
  expect(call(f, "POST", "/v1/trips/t1/restore")).toBeDefined()
})

test("a failed action shows an alert", async () => {
  mockApi((u, init) => (u.endsWith("/v1/trips") && isGet(init) ? page([row()]) : new Response("{}", { status: 500 })))
  show(<TripsHome />, "/")
  fireEvent.click(await screen.findByRole("button", { name: "Actions for Lisbon, March" }))
  fireEvent.click(screen.getByRole("button", { name: "Duplicate" }))
  expect(await screen.findByRole("alert")).toHaveTextContent("That did not work. Try again.")
})

test("Trips home: a shared trip has no actions button", async () => {
  mockApi((u) => (u.endsWith("/v1/trips") ? page([row({ my_role: "viewer" }), row({ id: "t3", name: "Mine" })]) : undefined))
  show(<TripsHome />, "/")
  await screen.findByText("Mine")
  expect(screen.getAllByRole("button", { name: /^Actions for/ })).toHaveLength(1)
})

test("Overview: the owner sees Trip actions with Edit; trash goes back to Trips", async () => {
  mockApi((u, init) => {
    if (u.endsWith("/v1/trips/t1") && isGet(init)) return Response.json(full())
    if (u.endsWith("/v1/trips/t1") && init?.method === "DELETE") return new Response(null, { status: 204 })
    if (u.endsWith("/v1/trips")) return page([])
  })
  show(<TripOverview />, "/trips/:id", "/trips/t1")
  fireEvent.click(await screen.findByRole("button", { name: "Trip actions" }))
  expect(screen.getByRole("link", { name: "Edit trip" })).toHaveAttribute("href", "/trips/t1/edit")
  fireEvent.click(screen.getByRole("button", { name: "Move to trash" }))
  await waitFor(() => expect(screen.getByTestId("where")).toHaveTextContent(/^\/$/))
})

test("Overview: viewers get no owner actions", async () => {
  mockApi((u) => (u.endsWith("/v1/trips/t1") ? Response.json(full({ my_role: "viewer" })) : undefined))
  show(<TripOverview />, "/trips/:id", "/trips/t1")
  await screen.findByRole("heading", { level: 1, name: "Lisbon, March" })
  expect(screen.queryByRole("button", { name: "Trip actions" })).not.toBeInTheDocument()
  expect(within(screen.getByRole("main")).queryByRole("link", { name: "Edit trip" })).not.toBeInTheDocument()
})

test("Overview shows the destination time zone", async () => {
  const d = { id: "d1", position: 0, name: "Lisbon", region: null, country: "Portugal", timezone: "Europe/Lisbon" }
  mockApi((u) => (u.endsWith("/v1/trips/t1") ? Response.json(full({ destinations: [d] })) : undefined))
  show(<TripOverview />, "/trips/:id", "/trips/t1")
  expect(await screen.findByText("Europe/Lisbon")).toBeInTheDocument()
})

test("arriving from a trashed trip shows Undo once, then clears it from history", async () => {
  mockApi((u) => (u.endsWith("/v1/trips") ? page([]) : undefined))
  const State = () => <p data-testid="state">{JSON.stringify(useLocation().state)}</p>
  render(
    <MemoryRouter initialEntries={[{ pathname: "/", state: { trashed: { id: "t1", name: "Lisbon, March" } } }]}>
      <Routes>
        <Route path="/" element={<><TripsHome /><State /></>} />
      </Routes>
    </MemoryRouter>,
  )
  expect(await screen.findByRole("status")).toHaveTextContent("Moved Lisbon, March to trash.")
  await waitFor(() => expect(screen.getByTestId("state")).toHaveTextContent("null"))
  expect(screen.getByRole("button", { name: "Undo" })).toBeInTheDocument()
})

test("Trips home: an editor on a shared trip gets Edit trip only", async () => {
  mockApi((u) => (u.endsWith("/v1/trips") ? page([row({ my_role: "editor" })]) : undefined))
  show(<TripsHome />, "/")
  fireEvent.click(await screen.findByRole("button", { name: "Actions for Lisbon, March" }))
  expect(screen.getByRole("link", { name: "Edit trip" })).toHaveAttribute("href", "/trips/t1/edit")
  for (const n of ["Archive", "Duplicate", "Move to trash"]) expect(screen.queryByRole("button", { name: n })).not.toBeInTheDocument()
})
