import { fireEvent, screen, waitFor } from "@testing-library/react"
import { afterEach, beforeEach, expect, test, vi } from "vitest"
import { mockApi, reset, show } from "../onboarding/testing"
import type { Item } from "./api"
import { capEnd, dropChange } from "./CalendarView"

// Drag cannot run in jsdom, so FullCalendar is replaced by a stub that fires the same onChange the real grid's eventDrop does.
vi.mock("./CalendarGrid", () => ({
  default: ({ items, onChange }: { items: Item[]; onChange: (i: Item, c: { day: string; start_time: string; end_time: null }) => Promise<boolean> }) => (
    <button onClick={() => void onChange(items[0], { day: "2027-03-13", start_time: "20:00:00", end_time: null }).then((ok) => document.body.setAttribute("data-reverted", String(!ok)))}>drop</button>
  ),
}))
import { Plan } from "./Plan"

const item = { id: "i3", trip_id: "t1", title: "Dinner", day: "2027-03-13", start_time: "19:00:00", end_time: null, category: "food", status: "idea", notes: "", sort_order: 1, version: 3, added_by: null }
const trip = { id: "t1", version: 1, name: "Lisbon", status: "planning", start_date: "2027-03-12", end_date: "2027-03-14", home_currency: "USD", my_role: "owner", destinations: [], travelers: [] }
const day = { day: "2027-03-13", title: "", notes: "", destination_id: null, destination_name: null, timezone: null, in_trip: true, item_count: 1, version: 0, first: null, last: null }
const run = (patch: Response) =>
  mockApi((u, i) => {
    if (u.endsWith("/items/i3") && i?.method === "PATCH") return patch
    if (u.endsWith("/v1/trips/t1")) return Response.json(trip)
    if (u.endsWith("/trips/t1/days")) return Response.json([day])
    if (u.includes("/trips/t1/items")) return Response.json({ items: [item], next_cursor: null, has_more: false })
  })
const drop = async () => {
  show(<Plan />, "/trips/:id/plan", "/trips/t1/plan")
  fireEvent.click(await screen.findByRole("tab", { name: "Calendar" }))
  fireEvent.click(await screen.findByRole("button", { name: "drop" }))
}

beforeEach(() => (reset("free"), document.body.removeAttribute("data-reverted")))
afterEach(() => vi.restoreAllMocks())

test("a dropped block patches with the version and logs the drag method", async () => {
  const seen: { event: string; props: Record<string, unknown> }[] = []
  window.addEventListener("hermi:event", (e) => seen.push((e as CustomEvent).detail), { once: false })
  const f = run(Response.json({ ...item, version: 4 }))
  await drop()
  await waitFor(() => expect(document.body.getAttribute("data-reverted")).toBe("false"))
  const call = f.mock.calls.find(([u, i]) => String(u).endsWith("/items/i3") && (i as RequestInit).method === "PATCH")!
  expect(JSON.parse(String((call[1] as RequestInit).body))).toEqual({ day: "2027-03-13", start_time: "20:00:00", version: 3 })
  expect(seen.find((e) => e.event === "itinerary_item_moved")?.props).toEqual({ method: "drag" })
})

test("a dropped block that hits a 409 reports false so the grid reverts it, and shows the conflict sheet", async () => {
  run(Response.json({ code: "version_conflict", current: { ...item, version: 7 } }, { status: 409 }))
  await drop()
  await waitFor(() => expect(document.body.getAttribute("data-reverted")).toBe("true"))
  expect(await screen.findByRole("dialog", { name: "Someone changed this while you were editing." })).toBeInTheDocument()
})

test("a failed drop save reports false so the grid reverts it", async () => {
  run(new Response("{}", { status: 500 }))
  await drop()
  await waitFor(() => expect(document.body.getAttribute("data-reverted")).toBe("true"))
})

test("capEnd keeps an end inside the day", () => {
  expect(capEnd("23:00:00", "01:30:00")).toBe("23:59:00")
  expect(capEnd("19:00:00", "21:30:00")).toBe("21:30:00")
  expect(capEnd("19:00:00", null)).toBeNull()
})

test("dropChange reads the calendar strings and caps a dragged end at midnight", () => {
  const timed = { end_time: "21:30:00" } as Item
  expect(dropChange(timed, "2027-03-13T23:30:00Z", "2027-03-14T02:00:00Z", false)).toEqual({ day: "2027-03-13", start_time: "23:30:00", end_time: "23:59:00" })
  expect(dropChange({ end_time: null } as Item, "2027-03-13T20:00:00Z", "2027-03-13T21:00:00Z", false).end_time).toBeNull()
  expect(dropChange(timed, "2027-03-13", "", true)).toEqual({ day: "2027-03-13", start_time: null, end_time: null })
})
