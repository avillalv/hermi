import { fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import { afterEach, beforeEach, expect, test, vi } from "vitest"
import type { Item } from "../itinerary/api"
import { PlacesMap } from "./PlacesMap"

const ml = vi.hoisted(() => ({ sources: [] as { id: string; spec: { cluster?: boolean; data: { features: unknown[] } } }[], fail: false, removed: 0 }))
vi.mock("maplibre-gl", () => {
  class Map {
    constructor() {
      if (ml.fail) throw new Error("WebGL is not available")
    }
    on() { return this }
    once(event: string, cb: () => void) { if (event === "load") queueMicrotask(cb); return this }
    addSource(id: string, spec: { cluster?: boolean; data: { features: unknown[] } }) { ml.sources.push({ id, spec }) }
    addLayer() {}
    getSource() { return undefined }
    fitBounds() {}
    flyTo() {}
    getZoom() { return 10 }
    easeTo() {}
    querySourceFeatures() { return [] }
    remove() { ml.removed += 1 }
  }
  class Marker {
    setLngLat() { return this }
    addTo() { return this }
    remove() {}
  }
  return { default: { Map, Marker }, Map, Marker }
})

const DAYS = [{ day: "2027-05-01", n: 1 }, { day: "2027-05-02", n: 2 }]
const item = (id: string, title: string, over: Partial<Item> = {}): Item => ({
  id, trip_id: "t1", title, day: "2027-05-01", start_time: null, end_time: null, category: "sights", status: "idea", notes: "", sort_order: 1, version: 1, added_by: null,
  lat: 38.7, lon: -9.14, address: null, ...over,
}) as Item
const ITEMS = [
  item("a", "Belem Tower", { sort_order: 1, address: "Av. Brasilia" }),
  item("b", "Ramen Alfama", { sort_order: 2, category: "food" }),
  item("c", "Museu do Azulejo", { day: "2027-05-02", category: "museum" }),
  item("d", "No coordinates", { lat: null, lon: null }),
  item("e", "Fado night", { day: null, category: "nightlife" }),
]
const events = () => {
  const seen: { event: string; props: Record<string, unknown> }[] = []
  const on = (e: Event) => seen.push((e as CustomEvent).detail)
  window.addEventListener("hermi:event", on)
  return { seen, stop: () => window.removeEventListener("hermi:event", on) }
}

beforeEach(() => {
  ml.sources.length = 0
  ml.fail = false
  ml.removed = 0
})
afterEach(() => vi.restoreAllMocks())

test("empty: nothing with coordinates on a day says so", () => {
  render(<PlacesMap items={[item("d", "x", { lat: null, lon: null })]} days={DAYS} online />)
  expect(screen.getByText("No places on the map yet. Add a place to a day.")).toBeInTheDocument()
})

test("the list shows every mapped stop with its number in the day, and leaves out stops with no coordinates or no day", () => {
  render(<PlacesMap items={ITEMS} days={DAYS} online />)
  const rows = screen.getAllByRole("button", { name: /Belem Tower|Ramen Alfama|Museu do Azulejo/ })
  expect(rows).toHaveLength(3)
  expect(within(rows[1]).getByText("2")).toBeInTheDocument()
  expect(screen.queryByText("No coordinates")).not.toBeInTheDocument()
  expect(screen.queryByText("Fado night")).not.toBeInTheDocument()
})

test("the day filter has All and each day, and narrows the list", () => {
  render(<PlacesMap items={ITEMS} days={DAYS} online />)
  expect(screen.getByRole("tab", { name: "All" })).toHaveAttribute("aria-selected", "true")
  fireEvent.click(screen.getByRole("tab", { name: "D2" }))
  expect(screen.getByRole("tab", { name: "D2" })).toHaveAttribute("aria-selected", "true")
  expect(screen.getByRole("button", { name: /Museu do Azulejo/ })).toBeInTheDocument()
  expect(screen.queryByRole("button", { name: /Belem Tower/ })).not.toBeInTheDocument()
})

test("a selected row drives the Apple Maps and Google Maps handoff, built from coordinates and name", () => {
  const { seen, stop } = events()
  render(<PlacesMap items={ITEMS} days={DAYS} online />)
  fireEvent.click(screen.getByRole("button", { name: /Ramen Alfama/ }))
  expect(screen.getByRole("button", { name: /Ramen Alfama/ })).toHaveAttribute("aria-current", "true")
  const apple = screen.getByRole("link", { name: "Open in Apple Maps" })
  expect(new URL(apple.getAttribute("href")!).searchParams.get("q")).toBe("Ramen Alfama")
  const google = screen.getByRole("link", { name: "Open in Google Maps" })
  expect(new URL(google.getAttribute("href")!).searchParams.get("query")).toBe("38.7,-9.14")
  fireEvent.click(apple)
  expect(seen.some((e) => e.event === "maps_handoff" && e.props.app === "apple")).toBe(true)
  stop()
})

test("200 markers go into one clustered source", async () => {
  const many = Array.from({ length: 200 }, (_, i) => item(`m${i}`, `Stop ${i}`, { sort_order: i, lat: 38.7 + i * 0.0005, lon: -9.14 + i * 0.0005 }))
  render(<PlacesMap items={many} days={DAYS} online />)
  await waitFor(() => expect(ml.sources).toHaveLength(1))
  expect(ml.sources[0].id).toBe("places")
  expect(ml.sources[0].spec.cluster).toBe(true)
  expect(ml.sources[0].spec.data.features).toHaveLength(200)
})

test("the map is removed when the view closes", async () => {
  const { unmount } = render(<PlacesMap items={ITEMS} days={DAYS} online />)
  await waitFor(() => expect(ml.sources).toHaveLength(1))
  unmount()
  expect(ml.removed).toBe(1)
})

test("list fallback: when the map cannot start, the same places show as a list with Try again", async () => {
  ml.fail = true
  render(<PlacesMap items={ITEMS} days={DAYS} online />)
  expect(await screen.findByRole("alert")).toHaveTextContent("The map did not load. Try again.")
  expect(screen.getAllByRole("button", { name: /Belem Tower|Ramen Alfama|Museu do Azulejo/ })).toHaveLength(3)
  ml.fail = false
  fireEvent.click(screen.getByRole("button", { name: "Try again" }))
  await waitFor(() => expect(ml.sources).toHaveLength(1))
  expect(screen.queryByRole("alert")).not.toBeInTheDocument()
})

test("offline: no map is started and the list is below the message", () => {
  render(<PlacesMap items={ITEMS} days={DAYS} online={false} />)
  expect(screen.getByRole("status")).toHaveTextContent("Maps need a connection. Your list is below.")
  expect(ml.sources).toHaveLength(0)
  expect(screen.getAllByRole("button", { name: /Belem Tower|Ramen Alfama|Museu do Azulejo/ })).toHaveLength(3)
})

test("the OpenStreetMap attribution stays visible", () => {
  render(<PlacesMap items={ITEMS} days={DAYS} online />)
  expect(screen.getByText("Map data © OpenStreetMap contributors")).toBeInTheDocument()
})
