import { expect, test } from "vitest"
import { appleMapsUrl, googleMapsUrl } from "./handoff"

const belem = { name: "Belem Tower & Fort", lat: 38.6916, lon: -9.216 }

test("Apple Maps link is built from the coordinates and the name only", () => {
  const u = new URL(appleMapsUrl(belem))
  expect(u.origin + u.pathname).toBe("https://maps.apple.com/")
  expect(u.searchParams.get("ll")).toBe("38.6916,-9.216")
  expect(u.searchParams.get("q")).toBe("Belem Tower & Fort")
  expect([...u.searchParams.keys()].sort()).toEqual(["ll", "q"])
})

test("Google Maps link is built from the coordinates and the name only", () => {
  const u = new URL(googleMapsUrl(belem))
  expect(u.origin + u.pathname).toBe("https://www.google.com/maps/search/")
  expect(u.searchParams.get("api")).toBe("1")
  expect(u.searchParams.get("query")).toBe("38.6916,-9.216")
  expect([...u.searchParams.keys()].sort()).toEqual(["api", "query"])
})

test("a place with no coordinates falls back to its name", () => {
  expect(new URL(appleMapsUrl({ name: "Cafe A Brasileira", lat: null, lon: null })).searchParams.get("q")).toBe("Cafe A Brasileira")
  expect(new URL(googleMapsUrl({ name: "Cafe A Brasileira", lat: null, lon: null })).searchParams.get("query")).toBe("Cafe A Brasileira")
})

test("handoff links never point at a booking site", () => {
  for (const url of [appleMapsUrl(belem), googleMapsUrl(belem)]) expect(url).not.toMatch(/airbnb|vrbo|booking\.com/i)
})
