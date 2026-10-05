import type { Map as MlMap, Marker as MlMarker, GeoJSONSource, StyleSpecification } from "maplibre-gl"
import { boundsOf, clusteredSource, SOURCE_ID, toCollection, type MapPoint } from "./cluster"

// shortcut: the public OpenStreetMap tile server, which its usage policy limits to light use. Upgrade: a tile host with a style URL
// before launch (no CSP exists yet; when one is added it must allow the tile host). Tiles load in the browser; the server fetches nothing.
export const MAP_STYLE: StyleSpecification = {
  version: 8,
  sources: { osm: { type: "raster", tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"], tileSize: 256, maxzoom: 19 } },
  layers: [{ id: "osm", type: "raster", source: "osm" }],
}

const LOAD_MS = 12_000

export type MapHandle = {
  /** Replace the points and frame them. */
  update(points: MapPoint[]): void
  select(id: string | null): void
  fly(p: Pick<MapPoint, "lat" | "lon">): void
  destroy(): void
}

const el = (tag: string, cls: string, text?: string) => {
  const e = document.createElement(tag)
  e.className = cls
  if (text !== undefined) e.textContent = text
  return e
}

/**
 * Mounts a MapLibre map in `host`. Rejects when the map cannot start (no WebGL, style or first render failing, offline), so the screen
 * falls back to its list. Pins and cluster badges are HTML markers (the kit's `h-pin`) synced from the clustered source, so no glyph
 * server is needed. Only the pins and clusters in view exist, which keeps 200 markers smooth.
 */
export async function mountMap(host: HTMLElement, onPick: (id: string) => void): Promise<MapHandle> {
  const mod = await import("maplibre-gl")
  await import("maplibre-gl/dist/maplibre-gl.css")
  const lib = mod.default ?? mod
  const map: MlMap = new lib.Map({ container: host, style: MAP_STYLE, center: [0, 20], zoom: 1, attributionControl: false })
  try {
    await new Promise<void>((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error("The map took too long to load.")), LOAD_MS)
      map.once("load", () => (clearTimeout(timer), resolve()))
      map.once("error", (e: { error?: Error }) => (clearTimeout(timer), reject(e.error ?? new Error("The map did not load."))))
    })
  } catch (e) {
    map.remove()
    throw e
  }

  let selected: string | null = null
  const shown = new Map<string, { marker: MlMarker; node: HTMLElement; id?: string }>()
  const paint = () => {
    for (const s of shown.values()) if (s.id) s.node.classList.toggle("places__pin--on", s.id === selected)
  }
  const sync = () => {
    const seen = new Set<string>()
    for (const f of map.querySourceFeatures(SOURCE_ID)) {
      const p = f.properties as { cluster?: boolean; cluster_id?: number; point_count?: number; id?: string; n?: number; group?: string; title?: string }
      const key = p.cluster ? `c${p.cluster_id}` : `p${p.id}`
      if (seen.has(key)) continue
      seen.add(key)
      if (shown.has(key)) continue
      const at = (f.geometry as unknown as { coordinates: [number, number] }).coordinates
      let node: HTMLElement
      if (p.cluster) {
        node = el("button", "places__cluster", String(p.point_count))
        node.setAttribute("aria-label", `${p.point_count} places`)
        node.addEventListener("click", () => {
          const src = map.getSource(SOURCE_ID) as GeoJSONSource
          void src.getClusterExpansionZoom(p.cluster_id as number).then((zoom) => map.easeTo({ center: at, zoom }))
        })
      } else {
        node = el("button", `h-pin h-pin--num h-pin--${p.group ?? "neutral"} places__pin`, String(p.n))
        node.setAttribute("aria-label", `${p.n}, ${p.title ?? ""}`)
        node.addEventListener("click", () => onPick(p.id as string))
      }
      node.setAttribute("tabindex", "-1") // the list below is the keyboard route; every pin has a row
      node.setAttribute("type", "button")
      shown.set(key, { marker: new lib.Marker({ element: node }).setLngLat(at).addTo(map), node, id: p.cluster ? undefined : p.id })
    }
    for (const [key, s] of shown) {
      if (seen.has(key)) continue
      s.marker.remove()
      shown.delete(key)
    }
    paint()
  }
  map.on("sourcedata", (e) => e.sourceId === SOURCE_ID && e.isSourceLoaded && sync())
  map.on("moveend", sync)

  return {
    update(points) {
      const source = map.getSource(SOURCE_ID) as GeoJSONSource | undefined
      if (source) source.setData(toCollection(points) as never)
      else {
        map.addSource(SOURCE_ID, clusteredSource(points) as never)
        // A source loads only while a layer reads it; this one draws nothing and keeps the clustered data flowing to the markers.
        map.addLayer({ id: "places-data", type: "circle", source: SOURCE_ID, paint: { "circle-radius": 1, "circle-opacity": 0 } })
      }
      for (const s of shown.values()) s.marker.remove()
      shown.clear()
      const b = boundsOf(points)
      if (b) map.fitBounds(b, { padding: 48, maxZoom: 15, duration: 0 })
    },
    select(id) {
      selected = id
      paint()
    },
    fly: (p) => map.flyTo({ center: [p.lon, p.lat], zoom: Math.max(map.getZoom(), 15) }),
    destroy() {
      for (const s of shown.values()) s.marker.remove()
      shown.clear()
      map.remove()
    },
  }
}
