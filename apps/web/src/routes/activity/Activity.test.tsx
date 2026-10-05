import { fireEvent, screen, waitFor, within } from "@testing-library/react"
import { afterEach, beforeEach, expect, test, vi } from "vitest"
import { Activity } from "./Activity"
import { mockApi, reset, show } from "../onboarding/testing"
import { authStore } from "../auth/authStore"

const trip = (id: string, name: string) => ({ id, name, status: "planning", start_date: null, end_date: null, destinations_label: "", member_count: 2, my_role: "owner" })
const page = (items: unknown[]) => Response.json({ items, next_cursor: null, has_more: false })
const item = (summary: string, at: string, actor: { id: string | null; display_name: string }, entity_type = "stop") => ({ verb: "added", entity_type, entity_id: "e1", summary, at, actor })

const feeds = (a: unknown[], b: unknown[] = []) => (u: string) => {
  if (u.endsWith("/v1/trips")) return page([trip("t1", "Lisbon"), trip("t2", "Rome")])
  if (u.includes("/trips/t1/activity")) return page(a)
  if (u.includes("/trips/t2/activity")) return page(b)
}

beforeEach(() => reset("free"))
afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

test("loading shows a status, then the empty state", async () => {
  mockApi(feeds([]))
  show(<Activity />, "/activity")
  expect(screen.getByRole("heading", { level: 1, name: "Activity" })).toBeInTheDocument()
  expect(screen.getByText("Loading activity")).toBeInTheDocument()
  expect(await screen.findByRole("heading", { name: "Nothing new" })).toBeInTheDocument()
  expect(screen.getByText("Price alerts, changes from your group and finished AI runs show up here.")).toBeInTheDocument()
})

test("error shows a retry that reloads", async () => {
  let fail = true
  mockApi((u) => (fail && u.endsWith("/v1/trips") ? new Response("{}", { status: 500 }) : feeds([])(u)))
  show(<Activity />, "/activity")
  expect(await screen.findByRole("alert", {}, { timeout: 3000 })).toHaveTextContent("We could not load activity.")
  fail = false
  fireEvent.click(screen.getByRole("button", { name: "Try again" }))
  expect(await screen.findByRole("heading", { name: "Nothing new" })).toBeInTheDocument()
})

test("rows merge across trips, newest first, grouped by day, one link each, deleted user named", async () => {
  const now = new Date().toISOString()
  const old = new Date(Date.now() - 3 * 86_400_000).toISOString()
  mockApi(feeds([item("added Cafe", old, { id: "u1", display_name: "Ana" })], [item("added Colosseum", now, { id: null, display_name: "Deleted user" })]))
  show(<Activity />, "/activity")
  const list = await screen.findByRole("list", { name: "Activity" })
    const items = within(list).getAllByRole("link")
  expect(items).toHaveLength(2)
  expect(items[0]).toHaveTextContent("Deleted user added Colosseum")
  expect(items[0]).toHaveTextContent("Rome")
  expect(items[1]).toHaveTextContent("Ana added Cafe")
  expect(screen.getAllByRole("heading", { level: 2 })).toHaveLength(2)
  expect(screen.getByRole("heading", { level: 2, name: "Today" })).toBeInTheDocument()
  expect(items.find((l) => /Colosseum/.test(l.textContent ?? ""))).toHaveAttribute("href", "/trips/t2")
})

test("a member change links to the group screen", async () => {
  mockApi(feeds([item("joined", new Date().toISOString(), { id: "u1", display_name: "Ana" }, "member")]))
  show(<Activity />, "/activity")
  expect(await screen.findByRole("link", { name: /Ana joined/ })).toHaveAttribute("href", "/trips/t1/group")
})

test("filters: Alerts and AI are empty, All and Group show items", async () => {
  mockApi(feeds([item("added Cafe", new Date().toISOString(), { id: "u1", display_name: "Ana" })]))
  show(<Activity />, "/activity")
  await screen.findByRole("link", { name: /Ana added Cafe/ })
  expect(screen.getByRole("tab", { name: "All" })).toHaveAttribute("aria-selected", "true")
  fireEvent.click(screen.getByRole("tab", { name: "Alerts" }))
  expect(screen.getByRole("tab", { name: "Alerts" })).toHaveAttribute("aria-selected", "true")
  expect(screen.getByRole("heading", { name: "Nothing new" })).toBeInTheDocument()
  fireEvent.click(screen.getByRole("tab", { name: "AI" }))
  expect(screen.queryByRole("link", { name: /Ana/ })).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole("tab", { name: "Group" }))
  expect(screen.getByRole("link", { name: /Ana added Cafe/ })).toBeInTheDocument()
})

test("a guest sees the sign in prompt and no calls are made", async () => {
  authStore.signOut()
  const f = mockApi(feeds([]))
  show(<Activity />, "/activity")
  expect(screen.getByText("Sign in to get alerts and see changes from your group.")).toBeInTheDocument()
  fireEvent.click(screen.getByRole("link", { name: "Sign in" }))
  await waitFor(() => expect(screen.getByTestId("where")).toHaveTextContent("/sign-in"))
  expect(f).not.toHaveBeenCalled()
})

test("offline shows the saved activity banner and no skeleton", () => {
  vi.spyOn(navigator, "onLine", "get").mockReturnValue(false)
  mockApi(feeds([]))
  show(<Activity />, "/activity")
  expect(screen.getByRole("status")).toHaveTextContent("You are offline. Showing your saved activity.")
  expect(screen.queryByText("Loading activity")).not.toBeInTheDocument()
})

test("a new item appears after the poll interval", async () => {
  vi.useFakeTimers({ shouldAdvanceTime: true })
  let items = [item("added Cafe", new Date().toISOString(), { id: "u1", display_name: "Ana" })]
  mockApi((u) => feeds(items)(u))
  show(<Activity />, "/activity")
  await screen.findByRole("link", { name: /Ana added Cafe/ })
  items = [item("added Museum", new Date().toISOString(), { id: "u2", display_name: "Bo" }), ...items]
  await vi.advanceTimersByTimeAsync(15_000)
  expect(await screen.findByRole("link", { name: /Bo added Museum/ })).toBeInTheDocument()
  vi.useRealTimers()
})

test("events: viewed and item opened carry their props", async () => {
  const seen: { event: string; props: Record<string, unknown> }[] = []
  const on = (e: Event) => seen.push((e as CustomEvent).detail)
  window.addEventListener("hermi:event", on)
  mockApi(feeds([item("added Cafe", new Date().toISOString(), { id: "u1", display_name: "Ana" })]))
  show(<Activity />, "/activity")
  fireEvent.click(await screen.findByRole("link", { name: /Ana added Cafe/ }))
  window.removeEventListener("hermi:event", on)
  expect(seen).toContainEqual({ event: "activity_viewed", props: { unread_bucket: "none" } })
  expect(seen).toContainEqual({ event: "activity_item_opened", props: { kind: "change" } })
})
