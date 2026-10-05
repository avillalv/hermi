import { fireEvent, screen, waitFor, within } from "@testing-library/react"
import { afterEach, beforeEach, expect, test, vi } from "vitest"
import { bodyOf, mockApi, reset, show, type Handler } from "../onboarding/testing"
import { Plan } from "./Plan"

const person = (id: string, name: string) => ({ id, name, color: "#000", home_airports: [], linked_user_id: null, is_me: false })
const trip = (over: Record<string, unknown> = {}) => ({
  id: "t1", version: 1, name: "Lisbon", status: "planning", start_date: "2027-03-12", end_date: "2027-03-14", home_currency: "USD",
  my_role: "owner", destinations: [], travelers: [], ...over,
})
const day = (d: string, n = 0) => ({ day: d, title: "", notes: "", destination_id: null, destination_name: null, timezone: null, in_trip: true, item_count: n, version: 0, first: null, last: null })
const item = (id: string, title: string, over: Record<string, unknown> = {}) => ({
  id, trip_id: "t1", title, day: "2027-03-12", start_time: null, end_time: null, category: "sights", status: "idea", location_name: null, address: null,
  lat: null, lon: null, url: null, notes: "", cost: null, sort_order: 1, version: 1, source: "manual", bookable: false,
  added_by: { id: "u1", display_name: "Ana" }, created_at: "2027-01-01T00:00:00Z", updated_at: "2027-01-01T00:00:00Z", ...over,
})
const DAYS = [day("2027-03-12", 2), day("2027-03-13", 3), day("2027-03-14")]
const ITEMS = () => [
  item("i1", "Museum", { sort_order: 1 }),
  item("i2", "Lunch", { category: "food", sort_order: 2 }),
  item("i3", "Dinner", { day: "2027-03-13", category: "food", start_time: "19:00:00" }),
  item("i5", "Show", { day: "2027-03-13", category: "nightlife", start_time: "21:00:00", sort_order: 2 }),
  item("i4", "Fado night", { day: null, category: "nightlife" }),
]

type Over = { role?: string; days?: unknown[]; items?: unknown[]; trip?: Record<string, unknown>; more?: Handler }
const api = ({ role = "owner", days = DAYS, items = ITEMS(), trip: tr = {}, more }: Over = {}): Handler =>
  (u, i) => {
    const m = i?.method ?? "GET"
    const r = more?.(u, i)
    if (r) return r
    if (u.endsWith("/v1/trips/t1") && m === "GET") return Response.json(trip({ my_role: role, ...tr }))
    if (u.endsWith("/trips/t1/days") && m === "GET") return Response.json(days)
    if (u.includes("/trips/t1/items") && m === "GET") return Response.json({ items, next_cursor: null, has_more: false })
    return undefined
  }
const open = () => show(<Plan />, "/trips/:id/plan", "/trips/t1/plan")
const calls = (f: ReturnType<typeof mockApi>, method: string, part: string) =>
  f.mock.calls.filter(([u, i]) => String(u).includes(part) && ((i as RequestInit | undefined)?.method ?? "GET") === method)
const isMove = (id: string) => (u: string, i?: RequestInit) => u.endsWith(`/items/${id}/move`) && i?.method === "POST"
const openMove = async (title: string) => {
  fireEvent.click(await screen.findByRole("button", { name: `Move ${title}` }))
  return screen.findByRole("dialog", { name: `Move ${title}` })
}
const events = () => {
  const seen: { event: string; props: Record<string, unknown> }[] = []
  const on = (e: Event) => seen.push((e as CustomEvent).detail)
  window.addEventListener("hermi:event", on)
  return { seen, stop: () => window.removeEventListener("hermi:event", on) }
}

beforeEach(() => reset("free"))
afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

test("loading shows skeleton rows", () => {
  mockApi(() => new Promise(() => {}) as never)
  const { container } = open()
  expect(container.querySelectorAll(".plan__skel").length).toBeGreaterThanOrEqual(2)
  expect(screen.getByText("Loading your plan")).toBeInTheDocument()
})

test("error: a failed load shows the message and a retry", async () => {
  mockApi(() => new Response("{}", { status: 500 }))
  open()
  expect(await screen.findByRole("alert", {}, { timeout: 3000 })).toHaveTextContent("We could not load your plan. Try again.")
  expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument()
})

test("empty trip says nothing is planned and offers Add a place", async () => {
  mockApi(api({ days: [], items: [], trip: { start_date: null, end_date: null } }))
  open()
  expect(await screen.findByText("Nothing planned yet")).toBeInTheDocument()
  expect(screen.getByText("Add a place to start.")).toBeInTheDocument()
  expect(screen.getByRole("button", { name: "Add a place" })).toBeEnabled()
})

test("day strip is a tablist; the first day shows its stops on the kit timeline and an empty day says Free day", async () => {
  mockApi(api())
  const { container } = open()
  const strip = await screen.findByRole("tablist", { name: "Days" })
  const tabs = within(strip).getAllByRole("tab")
  expect(tabs.map((x) => x.textContent)).toEqual(["D1", "D2", "D3", "Ideas"])
  expect(tabs[0]).toHaveAttribute("aria-selected", "true")
  const list = screen.getByRole("list", { name: "Day 1" })
  expect(list).toHaveClass("h-timeline")
  expect(within(list).getAllByRole("heading", { level: 3 }).map((x) => x.textContent)).toEqual(["Museum", "Lunch"])
  expect(container.querySelector(".h-timeline__row--culture .h-timeline__node")).toHaveTextContent("1")
  expect(container.querySelector(".h-timeline__spine")).toBeInTheDocument()
  expect(container.querySelector(".h-ticket--side")).toBeInTheDocument()
  fireEvent.click(tabs[1])
  expect(within(await screen.findByRole("list", { name: "Day 2" })).getByText("7:00")).toBeInTheDocument()
  fireEvent.click(tabs[2])
  expect(await screen.findByText("Free day")).toBeInTheDocument()
  fireEvent.click(tabs[3])
  expect(await screen.findByText("Fado night")).toBeInTheDocument()
})

test("the day strip is a real tab widget: roving tabindex, arrow keys, Home and End, and a labelled panel", async () => {
  mockApi(api())
  open()
  const strip = await screen.findByRole("tablist", { name: "Days" })
  const tabs = within(strip).getAllByRole("tab")
  expect(tabs.map((x) => x.tabIndex)).toEqual([0, -1, -1, -1])
  const panel = screen.getByRole("tabpanel")
  expect(panel).toHaveAttribute("aria-labelledby", tabs[0].id)
  expect(tabs[0]).toHaveAttribute("aria-controls", panel.id)
  fireEvent.keyDown(tabs[0], { key: "ArrowRight" })
  await waitFor(() => expect(tabs[1]).toHaveAttribute("aria-selected", "true"))
  expect(tabs.map((x) => x.tabIndex)).toEqual([-1, 0, -1, -1])
  expect(tabs[1]).toHaveFocus()
  expect(screen.getByRole("tabpanel")).toHaveAttribute("aria-labelledby", tabs[1].id)
  fireEvent.keyDown(tabs[1], { key: "End" })
  await waitFor(() => expect(tabs[3]).toHaveAttribute("aria-selected", "true"))
  fireEvent.keyDown(tabs[3], { key: "ArrowRight" })
  await waitFor(() => expect(tabs[0]).toHaveAttribute("aria-selected", "true"))
  fireEvent.keyDown(tabs[0], { key: "ArrowLeft" })
  await waitFor(() => expect(tabs[3]).toHaveAttribute("aria-selected", "true"))
  fireEvent.keyDown(tabs[3], { key: "Home" })
  await waitFor(() => expect(tabs[0]).toHaveAttribute("aria-selected", "true"))
})

test("Added by shows on the stub only when the trip has two or more travelers", async () => {
  mockApi(api())
  const solo = open()
  await screen.findByText("Museum")
  expect(screen.queryByText("Added by")).not.toBeInTheDocument()
  solo.unmount()
  reset("free")
  mockApi(api({ trip: { travelers: [person("p1", "Ana"), person("p2", "Leo")] } }))
  open()
  expect((await screen.findAllByText("Added by")).length).toBe(2)
  expect(screen.getAllByText("Ana").length).toBeGreaterThan(0)
})

test("Move opens one sheet with Move up, Move down and Move to day; the ends are disabled", async () => {
  mockApi(api())
  open()
  const first = await openMove("Museum")
  expect(within(first).getByRole("button", { name: "Move up, Museum" })).toBeDisabled()
  expect(within(first).getByRole("button", { name: "Move down, Museum" })).toBeEnabled()
  expect(within(first).getByLabelText("Move to day, Museum")).toBeEnabled()
  fireEvent.keyDown(first, { key: "Escape" })
  await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument())
  const last = await openMove("Lunch")
  expect(within(last).getByRole("button", { name: "Move down, Lunch" })).toBeDisabled()
  expect(within(last).getByRole("button", { name: "Move up, Lunch" })).toBeEnabled()
})

test("Move down posts the version and a before id, and after the refetch the list shows the new visible order", async () => {
  const rows = ITEMS()
  const f = mockApi(
    api({
      items: rows,
      more: (u, i) => {
        if (!isMove("i1")(u, i)) return undefined
        rows[0] = { ...rows[0], sort_order: 3, version: 2 }
        return Response.json([rows[0]])
      },
    }),
  )
  open()
  const sheet = await openMove("Museum")
  fireEvent.click(within(sheet).getByRole("button", { name: "Move down, Museum" }))
  await waitFor(() => expect(calls(f, "POST", "/items/i1/move")).toHaveLength(1))
  expect(bodyOf(f, "/items/i1/move")).toEqual({ day: "2027-03-12", before_id: null, version: 1 })
  await waitFor(() => expect(within(screen.getByRole("list", { name: "Day 1" })).getAllByRole("heading", { level: 3 }).map((h) => h.textContent)).toEqual(["Lunch", "Museum"]))
  await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument())
})

test("Move up sends the neighbor as the before id", async () => {
  const f = mockApi(api({ more: (u, i) => (isMove("i2")(u, i) ? Response.json([]) : undefined) }))
  open()
  fireEvent.click(within(await openMove("Lunch")).getByRole("button", { name: "Move up, Lunch" }))
  await waitFor(() => expect(calls(f, "POST", "/items/i2/move")).toHaveLength(1))
  expect(bodyOf(f, "/items/i2/move")).toEqual({ day: "2027-03-12", before_id: "i1", version: 1 })
})

test("a timed item beside one with a different start time cannot be moved up or down, and says why; Move to day still works", async () => {
  const f = mockApi(api({ more: (u, i) => (isMove("i5")(u, i) ? Response.json([]) : undefined) }))
  open()
  fireEvent.click(await screen.findByRole("tab", { name: /Day 2/ }))
  const sheet = await openMove("Show")
  expect(within(sheet).getByRole("button", { name: "Move up, Show" })).toBeDisabled()
  expect(within(sheet).getByRole("button", { name: "Move down, Show" })).toBeDisabled()
  expect(within(sheet).getByText(/different start times stay in time order/)).toBeInTheDocument()
  fireEvent.change(within(sheet).getByLabelText("Move to day, Show"), { target: { value: "2027-03-14" } })
  await waitFor(() => expect(calls(f, "POST", "/items/i5/move")).toHaveLength(1))
  expect(bodyOf(f, "/items/i5/move")).toEqual({ day: "2027-03-14", before_id: null, version: 1 })
})

test("dropping a timed item before one with a different start time is refused with a note and sends nothing", async () => {
  const f = mockApi(api())
  open()
  fireEvent.click(await screen.findByRole("tab", { name: /Day 2/ }))
  await screen.findByText("Show")
  const rows = screen.getAllByRole("listitem")
  const dt = { setData: vi.fn(), effectAllowed: "", dropEffect: "" }
  fireEvent.dragStart(rows[1], { dataTransfer: dt })
  fireEvent.dragOver(rows[0], { dataTransfer: dt })
  fireEvent.drop(rows[0], { dataTransfer: dt })
  expect(await screen.findByRole("alert")).toHaveTextContent("That item has a different start time, so it stays in time order.")
  expect(calls(f, "POST", "/move")).toHaveLength(0)
})

test("Move to day sends the new day and logs move_to_sheet", async () => {
  const ev = events()
  const f = mockApi(api({ more: (u, i) => (isMove("i2")(u, i) ? Response.json([]) : undefined) }))
  open()
  const sheet = await openMove("Lunch")
  fireEvent.change(within(sheet).getByLabelText("Move to day, Lunch"), { target: { value: "2027-03-13" } })
  await waitFor(() => expect(calls(f, "POST", "/items/i2/move")).toHaveLength(1))
  expect(bodyOf(f, "/items/i2/move")).toEqual({ day: "2027-03-13", before_id: null, version: 1 })
  await waitFor(() => expect(ev.seen.some((e) => e.event === "itinerary_item_moved" && e.props.method === "move_to_sheet")).toBe(true))
  ev.stop()
})

test("drag and drop between same-time stops moves before the target and logs drag; dropping on a day chip moves to that day", async () => {
  const ev = events()
  const f = mockApi(api({ more: (u, i) => (u.includes("/move") && i?.method === "POST" ? Response.json([]) : undefined) }))
  open()
  await screen.findByText("Lunch")
  const rows = screen.getAllByRole("listitem")
  const dt = { setData: vi.fn(), effectAllowed: "", dropEffect: "" }
  fireEvent.dragStart(rows[1], { dataTransfer: dt })
  fireEvent.dragOver(rows[0], { dataTransfer: dt })
  fireEvent.drop(rows[0], { dataTransfer: dt })
  await waitFor(() => expect(calls(f, "POST", "/items/i2/move")).toHaveLength(1))
  expect(bodyOf(f, "/items/i2/move")).toEqual({ day: "2027-03-12", before_id: "i1", version: 1 })
  await waitFor(() => expect(screen.getByRole("button", { name: "Move Lunch" })).toBeEnabled())
  fireEvent.dragStart(rows[0], { dataTransfer: dt })
  fireEvent.drop(screen.getByRole("tab", { name: /Day 3/ }), { dataTransfer: dt })
  await waitFor(() => expect(calls(f, "POST", "/items/i1/move")).toHaveLength(1))
  expect(bodyOf(f, "/items/i1/move")).toEqual({ day: "2027-03-14", before_id: null, version: 1 })
  expect(ev.seen.filter((e) => e.event === "itinerary_item_moved").map((e) => e.props.method)).toEqual(["drag", "drag"])
  ev.stop()
})

test("Move up logs the actions method", async () => {
  const ev = events()
  mockApi(api({ more: (u, i) => (isMove("i2")(u, i) ? Response.json([]) : undefined) }))
  open()
  fireEvent.click(within(await openMove("Lunch")).getByRole("button", { name: "Move up, Lunch" }))
  await waitFor(() => expect(ev.seen.some((e) => e.event === "itinerary_item_moved" && e.props.method === "actions")).toBe(true))
  ev.stop()
})

test("viewer: items show, every write control is gone", async () => {
  mockApi(api({ role: "viewer" }))
  open()
  expect(await screen.findByText("Museum")).toBeInTheDocument()
  expect(screen.queryByRole("button", { name: /Move/ })).not.toBeInTheDocument()
  expect(screen.queryByRole("button", { name: "Add item" })).not.toBeInTheDocument()
  expect(screen.getByText("You can read this plan. Only editors can change it.")).toBeInTheDocument()
  expect(screen.getAllByRole("listitem")[0]).toHaveAttribute("draggable", "false")
  expect(screen.getByRole("button", { name: "Download calendar file" })).toBeEnabled()
})

test("a server 403 on a move says only editors can change the plan", async () => {
  mockApi(api({ more: (u, i) => (u.includes("/move") && i?.method === "POST" ? new Response("{}", { status: 403 }) : undefined) }))
  open()
  fireEvent.click(within(await openMove("Museum")).getByRole("button", { name: "Move down, Museum" }))
  expect(await screen.findByRole("alert")).toHaveTextContent("Only editors can change this plan.")
})

test("offline: a banner shows and Move and Add are disabled", async () => {
  mockApi(api())
  const spy = vi.spyOn(navigator, "onLine", "get").mockReturnValue(false)
  open()
  expect(await screen.findByRole("status")).toHaveTextContent("Offline. You can read your plan. Reconnect to rearrange.")
  await screen.findByText("Museum")
  expect(screen.getByRole("button", { name: "Move Museum" })).toBeDisabled()
  expect(screen.getByRole("button", { name: "Add item" })).toBeDisabled()
  spy.mockRestore()
})

const conflictOn = (theirs: Record<string, unknown>, n = { v: 0 }) => (u: string, i?: RequestInit) => {
  if (!isMove("i1")(u, i)) return undefined
  n.v += 1
  return n.v === 1 ? Response.json({ type: "x", status: 409, code: "version_conflict", detail: "Someone else changed this.", current: theirs }, { status: 409 }) : Response.json([])
}

test("conflict: a 409 opens the sheet with their version; Keep mine retries with the latest version and logs keep_mine", async () => {
  const ev = events()
  const f = mockApi(api({ more: conflictOn(item("i1", "Museum (renamed)", { version: 4 })) }))
  open()
  fireEvent.click(within(await openMove("Museum")).getByRole("button", { name: "Move down, Museum" }))
  const sheet = await screen.findByRole("dialog", { name: "Someone changed this while you were editing." })
  expect(within(sheet).getByText("Museum (renamed)")).toBeInTheDocument()
  expect(within(sheet).getByText("Move to Day 1")).toBeInTheDocument()
  expect(ev.seen.some((e) => e.event === "edit_conflict_shown")).toBe(false)
  fireEvent.click(within(sheet).getByRole("button", { name: "Keep mine" }))
  await waitFor(() => expect(calls(f, "POST", "/items/i1/move")).toHaveLength(2))
  expect(JSON.parse(String((calls(f, "POST", "/items/i1/move")[1][1] as RequestInit).body))).toMatchObject({ version: 4 })
  await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument())
  expect(ev.seen.filter((e) => e.event === "edit_conflict_shown").map((e) => e.props.resolution)).toEqual(["keep_mine"])
  ev.stop()
})

test("a 409 with no latest row shows the move failure, not the conflict sheet", async () => {
  mockApi(api({ more: (u, i) => (isMove("i1")(u, i) ? Response.json({ code: "version_conflict" }, { status: 409 }) : undefined) }))
  open()
  fireEvent.click(within(await openMove("Museum")).getByRole("button", { name: "Move down, Museum" }))
  expect(await screen.findByRole("alert")).toHaveTextContent("That change did not save. Try again.")
  expect(screen.queryByRole("dialog", { name: "Someone changed this while you were editing." })).not.toBeInTheDocument()
})

test("an Add to day row ends the timeline and opens the add form on that day", async () => {
  mockApi(api())
  const { container } = open()
  fireEvent.click(await screen.findByRole("button", { name: "Add to day 1" }))
  expect(container.querySelector(".h-timeline__row--link-end")).toBeInTheDocument()
  expect(within(await screen.findByRole("dialog", { name: "Add an item" })).getByLabelText("Day")).toHaveValue("2027-03-12")
})

test("conflict: Use theirs sends nothing more and logs use_theirs", async () => {
  const ev = events()
  const f = mockApi(api({ more: conflictOn(item("i1", "Museum", { version: 2 })) }))
  open()
  fireEvent.click(within(await openMove("Museum")).getByRole("button", { name: "Move down, Museum" }))
  fireEvent.click(within(await screen.findByRole("dialog", { name: "Someone changed this while you were editing." })).getByRole("button", { name: "Use theirs" }))
  await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument())
  expect(calls(f, "POST", "/items/i1/move")).toHaveLength(1)
  expect(ev.seen.filter((e) => e.event === "edit_conflict_shown").map((e) => e.props.resolution)).toEqual(["use_theirs"])
  ev.stop()
})

test("conflict: Escape dismisses the sheet and logs dismissed", async () => {
  const ev = events()
  mockApi(api({ more: conflictOn(item("i1", "Museum", { version: 2 })) }))
  open()
  fireEvent.click(within(await openMove("Museum")).getByRole("button", { name: "Move down, Museum" }))
  fireEvent.keyDown(await screen.findByRole("dialog", { name: "Someone changed this while you were editing." }), { key: "Escape" })
  await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument())
  expect(ev.seen.filter((e) => e.event === "edit_conflict_shown").map((e) => e.props.resolution)).toEqual(["dismissed"])
  ev.stop()
})

test("add item by hand: the title is required, then the item posts with category, day and time", async () => {
  const f = mockApi(api({ more: (u, i) => (u.endsWith("/trips/t1/items") && i?.method === "POST" ? Response.json(item("n1", "Castle"), { status: 201 }) : undefined) }))
  open()
  await screen.findByText("Museum")
  fireEvent.click(screen.getByRole("button", { name: "Add item" }))
  const sheet = await screen.findByRole("dialog", { name: "Add an item" })
  fireEvent.click(within(sheet).getByRole("button", { name: "Add to plan" }))
  expect(await within(sheet).findByText("Give it a title.")).toBeInTheDocument()
  expect(calls(f, "POST", "/trips/t1/items")).toHaveLength(0)
  fireEvent.change(within(sheet).getByLabelText("Title"), { target: { value: "Castle" } })
  fireEvent.change(within(sheet).getByLabelText("Category"), { target: { value: "sights" } })
  fireEvent.change(within(sheet).getByLabelText("Day"), { target: { value: "2027-03-13" } })
  fireEvent.change(within(sheet).getByLabelText("Start time"), { target: { value: "14:30" } })
  fireEvent.click(within(sheet).getByRole("button", { name: "Add to plan" }))
  await waitFor(() => expect(calls(f, "POST", "/trips/t1/items")).toHaveLength(1))
  expect(bodyOf(f, "/trips/t1/items")).toEqual({ title: "Castle", category: "sights", day: "2027-03-13", start_time: "14:30:00" })
  await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument())
})

test("add item: a server failure keeps the sheet open with an error", async () => {
  mockApi(api({ more: (u, i) => (u.endsWith("/trips/t1/items") && i?.method === "POST" ? new Response("{}", { status: 500 }) : undefined) }))
  open()
  await screen.findByText("Museum")
  fireEvent.click(screen.getByRole("button", { name: "Add item" }))
  const sheet = await screen.findByRole("dialog")
  fireEvent.change(within(sheet).getByLabelText("Title"), { target: { value: "Castle" } })
  fireEvent.click(within(sheet).getByRole("button", { name: "Add to plan" }))
  expect(await within(sheet).findByRole("alert")).toHaveTextContent("We could not add that. Try again.")
})

test("Download calendar file fetches the ICS with the bearer token and saves it", async () => {
  const f = mockApi(
    api({ more: (u) => (u.endsWith("/trips/t1/itinerary.ics") ? new Response("BEGIN:VCALENDAR\r\nEND:VCALENDAR\r\n", { headers: { "content-type": "text/calendar", "content-disposition": 'attachment; filename="lisbon.ics"' } }) : undefined) }),
  )
  const make = vi.fn(() => "blob:x")
  vi.stubGlobal("URL", Object.assign(URL, { createObjectURL: make, revokeObjectURL: vi.fn() }))
  const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {})
  open()
  await screen.findByText("Museum")
  fireEvent.click(screen.getByRole("button", { name: "Download calendar file" }))
  await waitFor(() => expect(click).toHaveBeenCalled())
  const call = calls(f, "GET", "/itinerary.ics")[0]
  expect(new Headers((call[1] as RequestInit).headers).get("Authorization")).toBe("Bearer tok")
  expect(make).toHaveBeenCalled()
})
