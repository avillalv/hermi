/** The map's data: one clustered GeoJSON source, so 200 markers stay smooth (05 6.14). MapLibre does the clustering; nothing else is needed. */
export type MapPoint = { id: string; title: string; n: number; group: string; day: string | null; lat: number; lon: number }

export const SOURCE_ID = "places"
const CLUSTER = { cluster: true, clusterRadius: 50, clusterMaxZoom: 14 } as const

export type PointFeature = { type: "Feature"; geometry: { type: "Point"; coordinates: [number, number] }; properties: { id: string; n: number; group: string; title: string } }
export type PointCollection = { type: "FeatureCollection"; features: PointFeature[] }

export const toCollection = (points: MapPoint[]): PointCollection => ({
  type: "FeatureCollection",
  features: points.map((p) => ({ type: "Feature", geometry: { type: "Point", coordinates: [p.lon, p.lat] }, properties: { id: p.id, n: p.n, group: p.group, title: p.title } })),
})

export const clusteredSource = (points: MapPoint[]) => ({ type: "geojson" as const, data: toCollection(points), ...CLUSTER })

/** [[west, south], [east, north]] around the points, or null with none. */
export function boundsOf(points: MapPoint[]): [[number, number], [number, number]] | null {
  if (points.length === 0) return null
  const lons = points.map((p) => p.lon)
  const lats = points.map((p) => p.lat)
  return [[Math.min(...lons), Math.min(...lats)], [Math.max(...lons), Math.max(...lats)]]
}
