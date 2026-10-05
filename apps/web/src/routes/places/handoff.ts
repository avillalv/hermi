/** "Open in Apple Maps" and "Open in Google Maps" links (05 6.14). Built from coordinates and the name only: nothing is fetched and nothing else is sent. */
type Spot = { name: string; lat: number | null; lon: number | null }

const at = (s: Spot) => (s.lat !== null && s.lon !== null ? `${s.lat},${s.lon}` : null)

export function appleMapsUrl(s: Spot): string {
  const q = new URLSearchParams()
  const ll = at(s)
  if (ll) q.set("ll", ll)
  q.set("q", s.name)
  return `https://maps.apple.com/?${q}`
}

export function googleMapsUrl(s: Spot): string {
  const q = new URLSearchParams({ api: "1", query: at(s) ?? s.name })
  return `https://www.google.com/maps/search/?${q}`
}
