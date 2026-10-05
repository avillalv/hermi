import { fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import { afterEach, beforeEach, expect, test, vi } from "vitest"
import { mockApi, reset, type Handler } from "../onboarding/testing"
import { __resetAnalytics } from "../../lib/analytics"
import { AddActivity } from "./AddActivity"

const DAYS = [{ day: "2027-05-01", n: 1 }, { day: "2027-05-02", n: 2 }]
const BELEM = { provider: "geoapify", id: "geoapify:fixture-belem", name: "Belem Tower", category: "sights", kinds: ["tourism.sights"], address: "Av. Brasilia, Lisbon", lat: 38.6916, lon: -9.216, distance_m: null, website: "https://example.org/belem", opening_hours: "Tu-Su 10:00-17:30", has_details: true }
const RAMEN = { ...BELEM, id: "geoapify:fixture-ramen", name: "Ramen Alfama", category: "food", address: "Rua de S. Pedro 5, Lisbon", website: null, opening_hours: null, has_details: false }
const found = (places: unknown[] = [BELEM, RAMEN], sorted_by = "relevance") => Response.json({ places, cached: false, sorted_by, attribution: "Powered by Geoapify, © OpenStreetMap contributors" })
const problem = (status: number, code: string) => Response.json({ code, detail: code, title: code }, { status })
const saved = (name = "Museu do Azulejo", id = "geoapify:fixture-museu") => ({
  id: "s1", note: null, created_at: "2027-01-01T00:00:00Z", added_by: null,
  place: { provider: "geoapify", id, name, category: "museum", kinds: [], address: "Rua da Madre de Deus 4", lat: 38.7253, lon: -9.1137, website: null, has_details: false },
})
const WIKI = { title: "Belem Tower", extract: "The Belem Tower is a fortified tower in Lisbon.", url: "https://en.wikipedia.org/wiki/Belem_Tower", image_url: null, attribution: "Text from Wikipedia, CC BY-SA 4.0" }

type Over = { search?: () => Response | Promise<Response>; savedItems?: unknown[] }
const api = ({ search = () => found(), savedItems = [] }: Over = {}): Handler => (u, i) => {
  const m = i?.method ?? "GET"
  u = u.split("?")[0]
  if (u.includes("/v1/places/search")) return search()
  if (u.includes("/v1/places/geoapify")) return Response.json({ ...BELEM, wiki: WIKI, attribution: "Powered by Geoapify, © OpenStreetMap contributors" })
  if (u.endsWith("/trips/t1/saved-places") && m === "GET") return Response.json({ items: savedItems, next_cursor: null, has_more: false })
  if (u.endsWith("/trips/t1/saved-places") && m === "POST") return Response.json(saved(), { status: 201 })
  if (u.includes("/trips/t1/saved-places/") && m === "DELETE") return new Response(null, { status: 204 })
  if (u.endsWith("/trips/t1/items") && m === "POST") return Response.json({ id: "n1" }, { status: 201 })
  return undefined
}
type Props = Partial<Parameters<typeof AddActivity>[0]>
const open = (props: Props = {}) => {
  const fns = { onClose: vi.fn(), onCustom: vi.fn(), onAdded: vi.fn() }
  render(<AddActivity tripId="t1" days={DAYS} start="2027-05-02" destination={{ id: "d1", lat: 38.72, lon: -9.14 }} canWrite online {...fns} {...props} />)
  return fns
}
const search = (text = "belem") => {
  fireEvent.change(screen.getByRole("searchbox", { name: "Search places" }), { target: { value: text } })
  fireEvent.click(screen.getByRole("button", { name: "Search" }))
}
const sent = (f: ReturnType<typeof mockApi>, match: (u: string, m: string) => boolean) => f.mock.calls.find(([u, i]) => match(String(u), (i as RequestInit | undefined)?.method ?? "GET"))
const bodyOf = (f: ReturnType<typeof mockApi>, match: (u: string, m: string) => boolean) => {
  const c = sent(f, match)
  return c ? JSON.parse(String((c[1] as RequestInit).body)) : undefined
}
const searchUrl = (f: ReturnType<typeof mockApi>) => new URL(String(sent(f, (u) => u.includes("/places/search"))![0]))

beforeEach(() => reset("free"))
afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

test("the sheet opens with search, category chips, a Custom item row and the attribution", () => {
  mockApi(api())
  open()
  expect(screen.getByRole("dialog", { name: "Add an item" })).toBeInTheDocument()
  expect(screen.getByRole("searchbox", { name: "Search places" })).toBeInTheDocument()
  for (const c of ["Sights", "Museums", "Food", "Outdoors", "Nightlife", "Shopping"]) expect(screen.getByRole("button", { name: c })).toBeInTheDocument()
  expect(screen.getByRole("button", { name: "Custom item" })).toBeInTheDocument()
  expect(screen.getByText(/© OpenStreetMap contributors/)).toBeInTheDocument()
})

test("Custom item hands over to the manual form", () => {
  mockApi(api())
  const { onCustom } = open()
  fireEvent.click(screen.getByRole("button", { name: "Custom item" }))
  expect(onCustom).toHaveBeenCalled()
})

test("search: loading rows, then results in a listbox with the sort label, and the query uses the destination", async () => {
  let release: (r: Response) => void = () => {}
  const f = mockApi(api({ search: () => new Promise<Response>((r) => (release = r)) }))
  open()
  search()
  await waitFor(() => expect(document.querySelectorAll(".places__skel").length).toBeGreaterThanOrEqual(2))
  release(found())
  const list = await screen.findByRole("listbox", { name: "Results" })
  expect(within(list).getAllByRole("option")).toHaveLength(2)
  expect(screen.getByText("Sorted by relevance, then distance")).toBeInTheDocument()
  expect(Object.fromEntries(searchUrl(f).searchParams)).toMatchObject({ q: "belem", destination_id: "d1", trip_id: "t1" })
})

test("a category chip searches that kind by itself", async () => {
  const f = mockApi(api())
  open()
  fireEvent.click(screen.getByRole("button", { name: "Food" }))
  await screen.findByRole("listbox", { name: "Results" })
  expect(searchUrl(f).searchParams.get("category")).toBe("restaurants")
  expect(searchUrl(f).searchParams.get("q")).toBeNull()
})

test("empty: no results says what to do", async () => {
  mockApi(api({ search: () => found([]) }))
  open()
  search("zzzz")
  expect(await screen.findByText("No results. Try a different name, or add it yourself.")).toBeInTheDocument()
})

test("error: the provider is down, so the message offers Add by hand", async () => {
  mockApi(api({ search: () => problem(503, "provider_unavailable") }))
  const { onCustom } = open()
  search()
  expect(await screen.findByRole("alert")).toHaveTextContent("Place search is not working right now. Add it by hand and we will match it later.")
  fireEvent.click(screen.getByRole("button", { name: "Add by hand" }))
  expect(onCustom).toHaveBeenCalled()
})

test("rate limit: a 429 asks the person to wait a moment", async () => {
  mockApi(api({ search: () => problem(429, "rate_limited") }))
  open()
  search()
  expect(await screen.findByRole("alert")).toHaveTextContent("You are doing that too fast. Try again in a moment.")
})

test("quota reached: the daily message, Add by hand, and saved places still work", async () => {
  mockApi(api({ search: () => problem(429, "quota_exceeded"), savedItems: [saved()] }))
  open()
  search()
  expect(await screen.findByRole("alert")).toHaveTextContent("You have reached today's place searches. Saved places still work. Searches reset at midnight.")
  expect(screen.getByRole("button", { name: "Add by hand" })).toBeInTheDocument()
  expect(await screen.findByRole("button", { name: /^Museu do Azulejo/ })).toBeInTheDocument()
})

test("a trip with no destination asks for one instead of searching", () => {
  const f = mockApi(api())
  open({ destination: null })
  search()
  expect(screen.getByRole("alert")).toHaveTextContent("Add a destination to this trip to search places.")
  expect(sent(f, (u) => u.includes("/places/search"))).toBeUndefined()
})

test("offline: search is disabled with a reason", () => {
  mockApi(api())
  open({ online: false })
  expect(screen.getByRole("button", { name: "Search" })).toBeDisabled()
  expect(screen.getByRole("status")).toHaveTextContent("Offline. Place search needs a connection.")
})

test("a result opens a detail with the Wikipedia summary and its attribution, and Add posts the item to the chosen day", async () => {
  const f = mockApi(api())
  const { onAdded } = open()
  search()
  fireEvent.click(await screen.findByRole("option", { name: /Belem Tower/ }))
  expect(await screen.findByText("The Belem Tower is a fortified tower in Lisbon.")).toBeInTheDocument()
  expect(screen.getByText("Text from Wikipedia, CC BY-SA 4.0")).toBeInTheDocument()
  expect(screen.getByText("Tu-Su 10:00-17:30")).toBeInTheDocument()
  expect(screen.getByRole("link", { name: /Open in Apple Maps/ })).toHaveAttribute("href", expect.stringContaining("maps.apple.com"))
  expect(screen.getByRole("link", { name: /Open in Google Maps/ })).toHaveAttribute("href", expect.stringContaining("google.com/maps"))
  fireEvent.change(screen.getByLabelText("Day"), { target: { value: "2027-05-01" } })
  fireEvent.change(screen.getByLabelText("Start time"), { target: { value: "10:30" } })
  fireEvent.click(screen.getByRole("button", { name: "Add Belem Tower to Day 1" }))
  await waitFor(() => expect(onAdded).toHaveBeenCalledWith("2027-05-01", "Belem Tower"))
  expect(bodyOf(f, (u, m) => u.endsWith("/trips/t1/items") && m === "POST")).toMatchObject({
    title: "Belem Tower", category: "sights", day: "2027-05-01", start_time: "10:30:00", lat: 38.6916, lon: -9.216, location_name: "Belem Tower",
    place: { provider: "geoapify", id: "fixture-belem" },
  })
})

test("Save to ideas posts the place id and confirms", async () => {
  const f = mockApi(api())
  open()
  search()
  fireEvent.click(await screen.findByRole("option", { name: /Ramen Alfama/ }))
  fireEvent.click(await screen.findByRole("button", { name: "Save Ramen Alfama to ideas" }))
  expect(await screen.findByText("Saved to ideas.")).toBeInTheDocument()
  expect(bodyOf(f, (u, m) => u.endsWith("/saved-places") && m === "POST")).toEqual({ place_id: "geoapify:fixture-ramen" })
})

test("the ideas list shows saved places and removes one", async () => {
  const f = mockApi(api({ savedItems: [saved()] }))
  open()
  expect(screen.getByRole("heading", { name: "Your ideas" })).toBeInTheDocument()
  fireEvent.click(await screen.findByRole("button", { name: "Remove Museu do Azulejo from ideas" }))
  await waitFor(() => expect(sent(f, (u, m) => u.endsWith("/saved-places/s1") && m === "DELETE")).toBeDefined())
})

test("a saved idea opens its detail so it can be added to a day", async () => {
  const f = mockApi(api({ savedItems: [saved()] }))
  const { onAdded } = open()
  fireEvent.click(await screen.findByRole("button", { name: /^Museu do Azulejo/ }))
  fireEvent.click(await screen.findByRole("button", { name: "Add Museu do Azulejo to Day 2" }))
  await waitFor(() => expect(onAdded).toHaveBeenCalledWith("2027-05-02", "Museu do Azulejo"))
  expect(bodyOf(f, (u, m) => u.endsWith("/trips/t1/items") && m === "POST")).toMatchObject({ category: "museum", place: { provider: "geoapify", id: "fixture-museu" } })
})

test("an empty ideas list says so", async () => {
  mockApi(api())
  open()
  expect(await screen.findByText("Nothing saved yet. Search for a place and tap Save to ideas.")).toBeInTheDocument()
})

test("a viewer cannot add: the Add button is disabled", async () => {
  mockApi(api())
  open({ canWrite: false })
  search()
  fireEvent.click(await screen.findByRole("option", { name: /Belem Tower/ }))
  expect(await screen.findByRole("button", { name: "Add Belem Tower to Day 2" })).toBeDisabled()
})

test("two place adds fire itinerary_item_added each time and first_itinerary_item_added once", async () => {
  localStorage.clear()
  __resetAnalytics()
  const seen: string[] = []
  const on = (e: Event) => seen.push((e as CustomEvent).detail.event)
  window.addEventListener("hermi:event", on)
  const f = mockApi(api())
  const { onAdded } = open()
  search()
  fireEvent.click(await screen.findByRole("option", { name: /Belem Tower/ }))
  const add = await screen.findByRole("button", { name: /^Add Belem Tower to/ })
  fireEvent.click(add)
  await waitFor(() => expect(onAdded).toHaveBeenCalledTimes(1))
  fireEvent.click(screen.getByRole("button", { name: /^Add Belem Tower to/ }))
  await waitFor(() => expect(onAdded).toHaveBeenCalledTimes(2))
  expect(f.mock.calls.filter(([u, i]) => String(u).endsWith("/trips/t1/items") && (i as RequestInit | undefined)?.method === "POST")).toHaveLength(2)
  expect(seen.filter((n) => n === "itinerary_item_added")).toHaveLength(2)
  expect(seen.filter((n) => n === "first_itinerary_item_added")).toHaveLength(1)
  window.removeEventListener("hermi:event", on)
})
