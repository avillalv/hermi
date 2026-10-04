import { describe, expect, it } from 'vitest'
import { distanceKm, distanceSummary } from './geo'

describe('distanceKm', () => {
  it('measures great-circle distance', () => {
    expect(distanceKm({ lat: 0, lon: 0 }, { lat: 0, lon: 1 })).toBeCloseTo(111.19, 1)
    // Kyoto Station to Kiyomizu-dera is about 2.6 km as the crow flies.
    expect(distanceKm({ lat: 34.9858, lon: 135.7588 }, { lat: 34.9949, lon: 135.785 })).toBeCloseTo(2.6, 0)
  })
})

describe('distanceSummary', () => {
  it('gives the average and nearest distance, or nothing without points', () => {
    const from = { lat: 0, lon: 0 }
    const summary = distanceSummary(from, [
      { lat: 0, lon: 1 },
      { lat: 0, lon: 3 },
    ])
    expect(summary?.average).toBeCloseTo(222.39, 1)
    expect(summary?.nearest).toBeCloseTo(111.19, 1)
    expect(distanceSummary(from, [])).toBeNull()
  })
})
