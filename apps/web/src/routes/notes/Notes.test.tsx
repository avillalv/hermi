import { cleanup, fireEvent, screen, waitFor, within } from "@testing-library/react"
import { afterEach, beforeEach, expect, test, vi } from "vitest"
import { bodyOf, mockApi, reset, show, type Handler } from "../onboarding/testing"
import { Notes } from "./Notes"

const trip = (role = "owner") => ({ id: "t1", version: 1, name: "La Fortuna", status: "planning", start_date: null, end_date: null, home_currency: "USD", my_role: role, destinations: [], travelers: [] })
const now = new Date().toISOString()
const old = new Date(Date.now() - 40 * 86_400_000).toISOString()
const note = (id: string, over: Record<string, unknown> = {}) => ({
  id, trip_id: "t1", kind: "user", title: "", body: "Book the volcano tour early", pinned: false, is_private: false, day: null, item_id: null, version: 1,
  author: { id: "u1", display_name: "Ana" }, run_id: null, sources: [], checked_at: now, stale: false, created_at: now, updated_at: now, ...over,
})
const NOTES = () => [
  note("n1", { body: "Ask about the shuttle", created_at: "2027-01-01T00:00:00Z" }),
  note("n2", { body: "My budget thoughts", is_private: true, created_at: "2027-01-03T00:00:00Z" }),
  note("n3", { kind: "agent", title: "Hot springs hours", body: "Open 8 to 10", author: null, checked_at: old, stale: true, sources: [{ url: "https://springs.example.com/hours", title: "Hours", fetched_at: old, site: "springs.example.com" }] }),
]
const api = (role = "owner", items: unknown[] = NOTES(), more?: Handler): Handler => (u, i) => {
  const m = i?.method ?? "GET"
  const r = more?.(u, i)
  if (r) return r
  if (u.endsWith("/v1/me")) return Response.json({ id: "u1" })
  if (u.endsWith("/v1/trips/t1") && m === "GET") return Response.json(trip(role))
  if (u.includes("/trips/t1/notes") && m === "GET") return Response.json({ items, has_more: false, next_cursor: null })
  return undefined
}
const open = () => show(<Notes />, "/trips/:id/notes", "/trips/t1/notes")

beforeEach(() => reset("free"))
afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

test("loading shows line skeletons", async () => {
  mockApi(() => new Promise(() => {}) as never)
  const { container } = open()
  expect(await screen.findByRole("status", { name: "Loading" })).toBeInTheDocument()
  expect(container.querySelectorAll(".state-skel--line")).toHaveLength(3)
})

test("error shows the server message", async () => {
  mockApi(() => new Response("{}", { status: 500 }))
  open()
  expect(await screen.findByRole("alert", {}, { timeout: 3000 })).toHaveTextContent("We could not load notes. Pull down to try again.")
})

test("empty offline has no Add a note action", async () => {
  vi.spyOn(navigator, "onLine", "get").mockReturnValue(false)
  mockApi(api("owner", []))
  open()
  expect(await screen.findByText("No notes yet")).toBeInTheDocument()
  expect(screen.queryByRole("button", { name: "Add a note" })).not.toBeInTheDocument()
})

test("empty shows the copy and an Add a note button", async () => {
  mockApi(api("owner", []))
  open()
  expect(await screen.findByText("No notes yet")).toBeInTheDocument()
  expect(screen.getByText("Write down what you learn. Anything an AI finds is saved here with its source.")).toBeInTheDocument()
  expect(screen.getAllByRole("button", { name: "Add a note" }).length).toBeGreaterThan(0)
})

test("the list is newest first, shows author and a Private label with the lock", async () => {
  mockApi(api())
  open()
  const items = await screen.findAllByRole("article")
  expect(items).toHaveLength(2)
  expect(items[0]).toHaveTextContent("My budget thoughts")
  expect(within(items[0]).getByText("Private")).toBeInTheDocument()
  expect(within(items[0]).getByText("By Ana")).toBeInTheDocument()
  expect(within(items[1]).queryByText("Private")).toBeNull()
  expect(within(items[1]).getByText("Whole trip")).toBeInTheDocument()
})

test("Found by AI groups findings with a source chip and shows the excerpt on tap", async () => {
  const f = mockApi(api("owner", NOTES(), (u) => (u.includes("/notes/n3/evidence") ? Response.json({ note_id: "n3", run_id: null, sources: [], excerpt: "Open daily 8 to 10", checked_at: old, stale: true, stale_after_days: 14 }) : undefined)))
  open()
  fireEvent.click(await screen.findByRole("tab", { name: "Found by AI" }))
  expect(await screen.findByText("Hot springs hours")).toBeInTheDocument()
  expect(screen.getByText(/May be out of date/)).toBeInTheDocument()
  expect(screen.getByRole("link", { name: /springs\.example\.com/ })).toHaveAttribute("href", "https://springs.example.com/hours")
  fireEvent.click(screen.getByRole("button", { name: /Show the excerpt/ }))
  expect(await screen.findByText("Open daily 8 to 10")).toBeInTheDocument()
  expect(f.mock.calls.some(([u]) => String(u).includes("/notes/n3/evidence"))).toBe(true)
})

test("a stale finding shows the chip and Recheck for an owner, the chip only for a viewer", async () => {
  mockApi(api("owner"))
  open()
  fireEvent.click(await screen.findByRole("tab", { name: "Found by AI" }))
  expect(await screen.findByText(/May be out of date/)).toBeInTheDocument()
  expect(screen.getByRole("button", { name: "Recheck: Hot springs hours" })).toBeInTheDocument()
  cleanup()
  reset("free")
  mockApi(api("viewer"))
  open()
  fireEvent.click(await screen.findByRole("tab", { name: "Found by AI" }))
  expect(await screen.findByText(/May be out of date/)).toBeInTheDocument()
  expect(screen.queryByRole("button", { name: /^Recheck/ })).toBeNull()
})

test("adding a note posts the text, private flag and source", async () => {
  const f = mockApi(api("owner", [], (u, i) => (u.includes("/trips/t1/notes") && i?.method === "POST" ? Response.json(note("n9"), { status: 201 }) : undefined)))
  open()
  fireEvent.click((await screen.findAllByRole("button", { name: "Add a note" }))[0])
  const dlg = await screen.findByRole("dialog")
  fireEvent.change(within(dlg).getByLabelText("Note"), { target: { value: "See https://example.com/tour" } })
  fireEvent.change(within(dlg).getByLabelText("Source link (optional)"), { target: { value: "https://example.com/tour" } })
  fireEvent.click(within(dlg).getByRole("checkbox", { name: /Private/ }))
  fireEvent.click(within(dlg).getByRole("button", { name: "Save note" }))
  await waitFor(() => expect(bodyOf(f, "/trips/t1/notes")).toBeDefined())
  expect(bodyOf(f, "/trips/t1/notes")).toMatchObject({ body: "See https://example.com/tour", source_url: "https://example.com/tour", is_private: true })
})

test("an empty note is refused", async () => {
  mockApi(api("owner", []))
  open()
  fireEvent.click((await screen.findAllByRole("button", { name: "Add a note" }))[0])
  fireEvent.click(within(await screen.findByRole("dialog")).getByRole("button", { name: "Save note" }))
  expect(await screen.findByText("Write a note first.")).toBeInTheDocument()
})

test("a viewer reads notes and has no add, pin or delete controls", async () => {
  mockApi(api("viewer"))
  open()
  await screen.findAllByRole("article")
  expect(screen.queryByRole("button", { name: /Add a note/ })).toBeNull()
  expect(screen.queryByRole("button", { name: /Pin note|Delete note/ })).toBeNull()
  expect(screen.getByText(/You can read notes/)).toBeInTheDocument()
})

test("pin sends a patch with the version", async () => {
  const f = mockApi(api("owner", NOTES(), (u, i) => (u.endsWith("/notes/n2") && i?.method === "PATCH" ? Response.json(note("n2", { pinned: true })) : undefined)))
  open()
  fireEvent.click((await screen.findAllByRole("button", { name: /Pin note/ }))[0])
  await waitFor(() => expect(bodyOf(f, "/notes/n2")).toMatchObject({ pinned: true, version: 1 }))
})

test("offline: a neutral status shows, adding is off and loaded notes still render", async () => {
  mockApi(api())
  vi.spyOn(navigator, "onLine", "get").mockReturnValue(false)
  open()
  await screen.findAllByRole("article")
  const s = screen.getByRole("status")
  expect(s).toHaveTextContent("You are offline. Notes load again when you are back online.")
  expect(s).not.toHaveClass("h-input__error")
  expect(screen.getAllByRole("button", { name: "Add a note" }).every((b) => (b as HTMLButtonElement).disabled)).toBe(true)
  expect(screen.getByText("My budget thoughts")).toBeInTheDocument()
})

test("delete asks first: Cancel sends nothing, confirming sends one DELETE", async () => {
  const f = mockApi(api("owner", NOTES(), (u, i) => (u.endsWith("/notes/n2") && i?.method === "DELETE" ? new Response(null, { status: 204 }) : undefined)))
  const deletes = () => f.mock.calls.filter(([, i]) => (i as RequestInit | undefined)?.method === "DELETE").length
  open()
  fireEvent.click((await screen.findAllByRole("button", { name: /Delete note/ }))[0])
  const dlg = await screen.findByRole("dialog", { name: "Delete this note?" })
  fireEvent.click(within(dlg).getByRole("button", { name: "Cancel" }))
  expect(deletes()).toBe(0)
  fireEvent.click((await screen.findAllByRole("button", { name: /Delete note/ }))[0])
  fireEvent.click(within(await screen.findByRole("dialog")).getByRole("button", { name: "Delete note" }))
  await waitFor(() => expect(deletes()).toBe(1))
})

test("only the author or the owner can pin or delete", async () => {
  const other = note("n5", { body: "From Leo", author: { id: "u2", display_name: "Leo" } })
  mockApi(api("editor", [other]))
  open()
  await screen.findAllByRole("article")
  expect(screen.queryByRole("button", { name: /Pin note|Delete note/ })).toBeNull()
  cleanup()
  mockApi(api("owner", [other]))
  open()
  expect(await screen.findByRole("button", { name: /Pin note/ })).toBeInTheDocument()
})

test("a user note with an old source never shows the stale chip", async () => {
  mockApi(api("owner", [note("n6", { checked_at: old, stale: true, sources: [{ url: "https://x.example.com", title: null, fetched_at: old, site: "x.example.com" }] })]))
  open()
  await screen.findAllByRole("article")
  expect(screen.queryByText(/May be out of date/)).toBeNull()
})
