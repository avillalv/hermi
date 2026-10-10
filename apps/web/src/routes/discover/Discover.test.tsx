import { fireEvent, screen, waitFor, within } from "@testing-library/react"
import { afterEach, beforeEach, expect, test, vi } from "vitest"
import { authStore } from "../auth/authStore"
import { mockApi, reset, show } from "../onboarding/testing"
import { Discover } from "./Discover"
import { GuestHome } from "../../features/guest/GuestHome"
import { GUEST_KEY, readGuest, reloadGuest } from "../../features/guest/store"
import { SampleView } from "./SampleView"

const card = (slug: string, title: string, tags: string[]) => ({ slug, title, destination_name: "Lisbon", days: 5, summary: "s", tags, suits: "Food lovers", cover: null })
const sample = {
  slug: "lisbon-5-days",
  title: "Lisbon in 5 days",
  summary: "Tiles and tram rides.",
  updated_at: "2026-09-12T10:00:00Z",
  presentation: {
    trip: { name: "Lisbon in 5 days", destinations: [{ name: "Lisbon" }] },
    days: [
      {
        day: "2027-03-12",
        title: "Alfama",
        destination_name: "Lisbon",
        items: [
          { id: "i1", start_time: "10:00:00", title: "Castelo walk", category: "activity", location_name: "Alfama", estimated_cost_minor: 1500, cost_currency: "EUR", check_url: "https://www.lisboa.pt/x", checked_at: "2026-09-12T09:00:00Z" },
        ],
      },
    ],
    flights: [{ id: "f1", price: 999 }],
    stays: [{ id: "s1", title: "Casa Azul", price_total_minor: 42000, currency: "EUR" }],
  },
}
const json = (b: unknown, status = 200) => Response.json(b, { status })
const list = (items: unknown[]) => json({ items, next_cursor: null, has_more: false })
const open = () => show(<SampleView />, "/discover/:slug", "/discover/lisbon-5-days")

beforeEach(() => {
  reset("free")
  localStorage.clear()
  reloadGuest()
})
afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

test("the gallery lists the fixed samples and filters by a chip, with no search and no partner cards", async () => {
  const f = mockApi((u) => (u.includes("/v1/public/sample-trips") ? list([card("lisbon-5-days", "Lisbon in 5 days", ["city"])]) : undefined))
  show(<Discover />, "/discover")
  expect(screen.getByRole("heading", { level: 1, name: "Discover" })).toBeInTheDocument()
  const link = await screen.findByRole("link", { name: /Lisbon in 5 days/ })
  expect(link).toHaveAttribute("href", "/discover/lisbon-5-days")
  expect(screen.queryByRole("searchbox")).not.toBeInTheDocument()
  expect(screen.getByRole("button", { name: "All" })).toHaveAttribute("aria-pressed", "true")
  fireEvent.click(screen.getByRole("button", { name: "Food" }))
  await waitFor(() => expect(f.mock.calls.some(([u]) => String(u).includes("tag=food"))).toBe(true))
  expect(screen.getByRole("button", { name: "Food" })).toHaveAttribute("aria-pressed", "true")
})

test("a guest finds the gallery without signing in", async () => {
  authStore.signOut()
  mockApi((u) => (u.includes("/v1/public/sample-trips") ? list([card("a", "Lisbon in 5 days", [])]) : undefined))
  show(<Discover />, "/discover")
  expect(await screen.findByRole("link", { name: /Lisbon in 5 days/ })).toBeInTheDocument()
})

test("the empty state says so and offers Try again", async () => {
  mockApi((u) => (u.includes("/v1/public/sample-trips") ? list([]) : undefined))
  show(<Discover />, "/discover")
  expect(await screen.findByRole("heading", { name: "No examples yet" })).toBeInTheDocument()
  expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument()
})

test("the error state says so and offers Try again", async () => {
  mockApi((u) => (u.includes("/v1/public/sample-trips") ? json({}, 500) : undefined))
  show(<Discover />, "/discover")
  expect(await screen.findByText("We could not load examples. Pull down to try again.")).toBeInTheDocument()
  expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument()
})

test("a sample opens read-only with dated facts, an evidence label and no flights", async () => {
  mockApi((u) => (u.endsWith("/public/sample-trips/lisbon-5-days") ? json(sample) : undefined))
  open()
  expect(await screen.findByRole("heading", { level: 1, name: "Lisbon in 5 days" })).toBeInTheDocument()
  expect(screen.getByText("Sample trip. Prices and facts are dated and may have changed.")).toBeInTheDocument()
  expect(screen.getByRole("heading", { level: 2, name: /Alfama/ })).toBeInTheDocument()
  expect(screen.getByText(/Example price .*15.*, checked Sep 12, 2026/)).toBeInTheDocument()
  expect(screen.getByRole("link", { name: /Found on lisboa.pt, checked 12 Sep/ })).toBeInTheDocument()
  expect(screen.getByText("Casa Azul")).toBeInTheDocument()
  expect(screen.queryByText(/999/)).not.toBeInTheDocument()
  expect(screen.queryByRole("textbox")).not.toBeInTheDocument()
  expect(screen.getByRole("button", { name: "Use this plan" })).toBeInTheDocument()
})

test("a sample that fails to load says so and offers Try again", async () => {
  mockApi(() => json({}, 500))
  open()
  expect(await screen.findByText("We could not load this sample. Try again.")).toBeInTheDocument()
  expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument()
})

test("Use this plan copies the sample and opens the new trip", async () => {
  const f = mockApi((u, init) => {
    if (u.endsWith("/public/sample-trips/lisbon-5-days/copy") && init?.method === "POST") return json({ id: "new-trip", name: "Lisbon in 5 days" }, 201)
    if (u.endsWith("/public/sample-trips/lisbon-5-days")) return json(sample)
  })
  open()
  fireEvent.click(await screen.findByRole("button", { name: "Use this plan" }))
  await waitFor(() => expect(screen.getByTestId("where")).toHaveTextContent("/trips/new-trip"))
  const post = f.mock.calls.find(([u]) => String(u).endsWith("/copy"))!
  expect(new Headers((post[1] as RequestInit).headers).get("Idempotency-Key")).toBeTruthy()
})

test("a 402 limit_reached on Free shows the third_trip paywall", async () => {
  mockApi((u, init) => {
    if (init?.method === "POST") return json({ code: "limit_reached" }, 402)
    if (u.endsWith("/public/sample-trips/lisbon-5-days")) return json(sample)
  })
  open()
  fireEvent.click(await screen.findByRole("button", { name: "Use this plan" }))
  const dialog = await screen.findByRole("dialog", { name: "Two trips are active" })
  expect(dialog.contains(document.activeElement)).toBe(true)
  expect(within(dialog).getByRole("link", { name: "Archive a trip" })).toHaveAttribute("href", "/")
  fireEvent.keyDown(dialog, { key: "Escape" })
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
})

test("a guest builds the local guest trip with no server write", async () => {
  authStore.signOut()
  const f = mockApi((u) => (u.endsWith("/public/sample-trips/lisbon-5-days") ? json(sample) : undefined))
  open()
  fireEvent.click(await screen.findByRole("button", { name: "Use this plan" }))
  await waitFor(() => expect(screen.getByTestId("where")).toHaveTextContent("/guest-trip"))
  expect(f.mock.calls.some(([, i]) => (i as RequestInit | undefined)?.method === "POST")).toBe(false)
  expect(JSON.parse(localStorage.getItem(GUEST_KEY) ?? "{}").trip.name).toBe("Lisbon in 5 days")
  expect(readGuest()?.trip.items.map((i) => i.title)).toEqual(["Castelo walk"])
})

test("a guest who already has a guest trip sees the one trip limit", async () => {
  authStore.signOut()
  localStorage.setItem("hermi.guestTrip", JSON.stringify({ saved_at: "2026-10-01T00:00:00Z", sample }))
  reloadGuest()
  mockApi((u) => (u.endsWith("/public/sample-trips/lisbon-5-days") ? json(sample) : undefined))
  open()
  fireEvent.click(await screen.findByRole("button", { name: "Use this plan" }))
  expect(await screen.findByText("Guests can plan one trip. Create a free account to add more.")).toBeInTheDocument()
})

test("the guest trip page offers to create a trip when empty, and shows the migrated plan otherwise", () => {
  authStore.signOut()
  const { unmount } = show(<GuestHome />, "/guest-trip")
  expect(screen.getByRole("heading", { level: 1, name: "Plan a trip" })).toBeInTheDocument()
  unmount()
  localStorage.setItem("hermi.guestTrip", JSON.stringify({ saved_at: "2026-10-01T00:00:00Z", sample }))
  reloadGuest()
  show(<GuestHome />, "/guest-trip")
  expect(screen.getByRole("heading", { level: 1, name: "Lisbon in 5 days" })).toBeInTheDocument()
  expect(screen.getByText("Castelo walk")).toBeInTheDocument()
})

test("loading shows card skeletons", async () => {
  mockApi(() => new Promise<Response>(() => {}) as unknown as Response)
  show(<Discover />, "/discover")
  expect(await screen.findByRole("status", { name: "Loading" })).toBeInTheDocument()
})

test("offline and signed in: the offline line shows and Use this plan is disabled", async () => {
  mockApi((u) => (u.endsWith("/public/sample-trips/lisbon-5-days") ? json(sample) : undefined))
  vi.spyOn(navigator, "onLine", "get").mockReturnValue(false)
  open()
  const btn = await screen.findByRole("button", { name: "Use this plan" })
  expect(btn).toBeDisabled()
  expect(screen.getByText("You are offline. Connect to use this plan.")).toBeInTheDocument()
})

test("offline guest keeps Use this plan enabled", async () => {
  authStore.signOut()
  mockApi((u) => (u.endsWith("/public/sample-trips/lisbon-5-days") ? json(sample) : undefined))
  vi.spyOn(navigator, "onLine", "get").mockReturnValue(false)
  open()
  expect(await screen.findByRole("button", { name: "Use this plan" })).toBeEnabled()
})

test("a damaged guest trip in storage is ignored", () => {
  authStore.signOut()
  localStorage.setItem("hermi.guestTrip", JSON.stringify({ sample: { title: "x" } }))
  reloadGuest()
  show(<GuestHome />, "/guest-trip")
  expect(screen.getByRole("heading", { level: 1, name: "Plan a trip" })).toBeInTheDocument()
})
