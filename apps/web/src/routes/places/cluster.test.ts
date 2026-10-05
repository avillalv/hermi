import { expect, test } from "vitest"
import { boundsOf, clusteredSource, SOURCE_ID, type MapPoint } from "./cluster"

const many = (n: number): MapPoint[] =>
  Array.from({ length: n }, (_, i) => ({ id: `p${i}`, title: `Stop ${i}`, n: (i % 9) + 1, group: "culture", day: "2027-05-01", lat: 38.7 + (i % 20) * 0.001, lon: -9.14 + Math.floor(i / 20) * 0.001 }))

test("200 markers go through one clustered GeoJSON source", () => {
  const src = clusteredSource(many(200))
  expect(SOURCE_ID).toBe("places")
  expect(src.type).toBe("geojson")
  expect(src.cluster).toBe(true)
  expect(src.clusterRadius).toBeGreaterThan(0)
  expect(src.clusterMaxZoom).toBeLessThan(18)
  expect(src.data.features).toHaveLength(200)
})

test("features are [lon, lat] points that carry the id, number and group", () => {
  const f = clusteredSource([{ id: "a", title: "Belem", n: 2, group: "food", day: null, lat: 38.69, lon: -9.21 }]).data.features[0]
  expect(f.geometry).toEqual({ type: "Point", coordinates: [-9.21, 38.69] })
  expect(f.properties).toMatchObject({ id: "a", n: 2, group: "food" })
})

test("bounds cover every point, and are null with none", () => {
  expect(boundsOf([])).toBeNull()
  expect(boundsOf(many(200))).toEqual([[-9.14, 38.7], [-9.14 + 9 * 0.001, 38.7 + 19 * 0.001]])
})
