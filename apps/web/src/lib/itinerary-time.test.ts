import { describe, expect, it } from 'vitest'
import { addDays, eventRange, formatTimeRange, fromCalendar, suggestStart } from './itinerary-time'

const on = (start_time: string | null, end_time: string | null) => ({ day: '2026-11-05', start_time, end_time })

describe('calendar times', () => {
  it('places timed, open-ended, and any-time activities', () => {
    expect(eventRange(on('10:00:00', '12:30:00'))).toEqual({
      start: '2026-11-05T10:00:00',
      end: '2026-11-05T12:30:00',
      allDay: false,
    })
    expect(eventRange(on('10:00:00', null))).toEqual({ start: '2026-11-05T10:00:00', allDay: false })
    expect(eventRange(on(null, null))).toEqual({ start: '2026-11-05', allDay: true })
  })

  it('runs late evenings into the next day', () => {
    expect(eventRange(on('22:00:00', '01:30:00')).end).toBe('2026-11-06T01:30:00')
    expect(addDays('2026-12-31', 1)).toBe('2027-01-01')
  })

  it('reads the calendar back as wall-clock times', () => {
    expect(fromCalendar('2026-11-05T14:00:00Z', '2026-11-05T15:30:00Z', false)).toEqual({
      day: '2026-11-05',
      start_time: '14:00:00',
      end_time: '15:30:00',
    })
    expect(fromCalendar('2026-11-05T23:00:00Z', '2026-11-06T00:30:00Z', false).end_time).toBe('00:30:00')
    expect(fromCalendar('2026-11-05', null, true)).toEqual({ day: '2026-11-05', start_time: null, end_time: null })
  })

  it('suggests starting after the day’s last plan', () => {
    expect(suggestStart([])).toBe('10:00:00')
    expect(suggestStart([on('09:00:00', '11:10:00'), on('13:00:00', null)])).toBe('14:00:00')
    expect(suggestStart([on(null, null)])).toBe('10:00:00')
    // Nothing sensible is left once the day runs to midnight.
    expect(suggestStart([on('21:00:00', '00:30:00')])).toBe('10:00:00')
  })

  it('describes ranges, including ones that end after midnight', () => {
    expect(formatTimeRange(null, null)).toBe('Any time')
    const plain = formatTimeRange('09:00:00', '10:30:00')
    expect(plain).not.toMatch(/[\u2013\u2014]/)
    expect(plain).toMatch(/ to /)
    expect(formatTimeRange('22:00:00', '01:30:00')).toMatch(/\(next day\)$/)
  })
})
