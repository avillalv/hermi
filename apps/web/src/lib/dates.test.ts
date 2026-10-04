import { describe, expect, it } from 'vitest'
import { daysBetween, formatDateRange, parseDate, timingLabel, tripLengthDays, tripTiming } from './dates'
import { offsetFromViewer, utcOffsetMinutes } from './timezones'

describe('trip dates', () => {
  it('parses calendar days without shifting across time zones', () => {
    const date = parseDate('2026-11-05')
    expect([date.getFullYear(), date.getMonth(), date.getDate()]).toEqual([2026, 10, 5])
  })

  it('counts both the first and last day of a trip', () => {
    expect(tripLengthDays('2026-11-05', '2026-11-15')).toBe(11)
    expect(tripLengthDays('2026-11-05', '2026-11-05')).toBe(1)
    expect(daysBetween(parseDate('2026-03-07'), parseDate('2026-03-09'))).toBe(2) // across a DST change
  })

  it('describes where today falls relative to the trip', () => {
    const today = parseDate('2026-11-01')
    expect(timingLabel(tripTiming('2026-11-05', '2026-11-15', today))).toBe('In 4 days')
    expect(timingLabel(tripTiming('2026-11-02', '2026-11-15', today))).toBe('Tomorrow')
    expect(timingLabel(tripTiming('2026-10-30', '2026-11-05', today))).toBe('Day 3 of 7')
    expect(timingLabel(tripTiming('2026-10-01', '2026-10-10', today))).toBe('Ended 22 days ago')
    expect(timingLabel(tripTiming('2027-04-01', '2027-04-10', today))).toBe('In 5 months')
  })
})

describe('time zones', () => {
  it('reads UTC offsets, including half hours', () => {
    const at = new Date('2026-01-15T12:00:00Z')
    expect(utcOffsetMinutes('Asia/Tokyo', at)).toBe(540)
    expect(utcOffsetMinutes('Asia/Kolkata', at)).toBe(330)
    expect(utcOffsetMinutes('UTC', at)).toBe(0)
  })

  it('phrases the difference from the viewer', () => {
    const at = new Date('2026-01-15T12:00:00Z')
    const newYork = -300
    expect(offsetFromViewer('Asia/Tokyo', at, newYork)).toBe('14 hours ahead of you')
    expect(offsetFromViewer('America/Chicago', at, newYork)).toBe('1 hour behind you')
    expect(offsetFromViewer('Asia/Kolkata', at, newYork)).toBe('10.5 hours ahead of you')
    expect(offsetFromViewer('America/New_York', at, newYork)).toBe('Same time as you')
  })
})

describe('formatDateRange', () => {
  it('uses "to" instead of a dash, in every shape of range', () => {
    const cases: [string, string, RegExp][] = [
      ['2026-11-05', '2026-11-15', /^Nov 5 to 15, 2026$/],
      ['2026-11-28', '2026-12-04', /^Nov 28 to Dec 4, 2026$/],
      ['2026-12-28', '2027-01-03', /^Dec 28, 2026 to Jan 3, 2027$/],
    ]
    for (const [a, b, want] of cases) {
      const out = formatDateRange(a, b)
      expect(out).toMatch(want)
      expect(out).not.toMatch(/[\u2013\u2014]/)
    }
  })
})
